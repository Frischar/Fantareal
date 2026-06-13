from __future__ import annotations

"""auto-saga mod 后端 — 自动叙事模式（v0.2.0）

旁观式玩法的服务端：每点一次 Next，后端推进一回合：
  1) GM/旁白推进环境与事件；
  2) 逐个在场角色按人设卡性格 + 信任 + 是否被点名 + 随机性 判定是否发言。

设计原则：自包含、零侵入。
  - 独立 FastAPI 子应用，沿用 Fantareal 的 mod 后端约定（app = FastAPI(...)，挂 /static）。
  - 运行时状态写项目级 data/auto_saga/，不随 mod 目录替换丢失。
  - LLM 调用复用 Fantareal 全局设置；无 Key 时用本地 mock 回退，且 API Key 不暴露到前端。

关联 Issue #4。
"""

import json
import os
import random
import re
import sys
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field


def get_resource_dir() -> Path:
    bundle_dir = getattr(sys, "_MEIPASS", "")
    if bundle_dir:
        return Path(bundle_dir)
    return Path(__file__).resolve().parent


APP_DIR = Path(__file__).resolve().parent
RESOURCE_DIR = get_resource_dir()
PROJECT_ROOT = APP_DIR.parent.parent if APP_DIR.parent.name.lower() == "mods" else APP_DIR.parent
DATA_DIR = PROJECT_ROOT / "data" / "auto_saga"
STATE_PATH = DATA_DIR / "state.json"
MAIN_SETTINGS_PATH = PROJECT_ROOT / "data" / "settings.json"
MAIN_CURRENT_CARD_PATH = PROJECT_ROOT / "data" / "current_role_card.json"
STATIC_DIR = RESOURCE_DIR / "static"
TEMPLATES_DIR = RESOURCE_DIR / "templates"

DEFAULT_STATE: dict[str, Any] = {
    "session_id": "",
    "session_seed": 0,
    "event_theme": "",
    "session_started_at": "",
    "turn": 0,
    "env": {"time": "第一幕", "place": "世界入口", "weather": "平静"},
    "characters": [],          # [{name, persona, trust, addressed}]
    "events": [],              # ["..."]
    "history": [],             # [{role, name, text}]
    "choices": [],
    "settings": {
        "enabled": False,
        "interval_sec": 30,
        "auto_interact": False,
        "observer_mode": False,
        "show_silent": False,
    },
}

EVENT_THEMES = (
    "daily_interruption",
    "relationship_shift",
    "unexpected_request",
    "environmental_change",
    "private_clue",
    "visitor_arrival",
    "misplaced_object",
    "shared_memory",
)

# ---- 性格 → 发言倾向权重 ----------------------------------------------------
TALKATIVE = ("健谈", "热情", "话痨", "外向", "活泼", "开朗")
SILENT = ("沉默", "寡言", "高冷", "冷淡", "内向", "沉稳")
WARY = ("多疑", "谨慎", "警惕", "犹豫")


def clone(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False))


def new_session_state(previous: dict[str, Any] | None = None) -> dict[str, Any]:
    state = clone(DEFAULT_STATE)
    source = previous if isinstance(previous, dict) else {}
    if isinstance(source.get("settings"), dict):
        state["settings"].update(source["settings"])
    if isinstance(source.get("characters"), list):
        state["characters"] = clone(source["characters"])
    if isinstance(source.get("env"), dict):
        state["env"].update(source["env"])
    rng = random.SystemRandom()
    state["session_id"] = uuid.uuid4().hex
    state["session_seed"] = rng.randrange(1, 2_147_483_647)
    state["event_theme"] = rng.choice(EVENT_THEMES)
    state["session_started_at"] = now_string()
    return state


def history_message(role: str, name: str, text: str, message_id: str = "") -> dict[str, Any]:
    return {
        "id": message_id or uuid.uuid4().hex,
        "role": role,
        "name": name,
        "text": text,
        "created_at": now_string(),
    }


def visible_message_text(value: Any) -> str:
    text = str(value or "")
    for tag in ("think", "thinking", "thought", "thoughts", "reason", "reasoning", "analysis"):
        text = re.sub(
            rf"<\s*{tag}\b[^>]*>[\s\S]*?</\s*{tag}\s*>",
            "",
            text,
            flags=re.IGNORECASE,
        )
    return text.strip()


def character_persona_text(raw: dict[str, Any]) -> str:
    parts = []
    for key, label in (
        ("description", "角色描述"),
        ("personality", "性格"),
        ("scenario", "场景"),
        ("creator_notes", "补充设定"),
    ):
        value = str(raw.get(key) or "").strip()
        if value:
            parts.append(f"{label}：{value}")
    return "\n".join(parts)


def current_card_characters() -> list[dict[str, Any]]:
    try:
        payload = json.loads(MAIN_CURRENT_CARD_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        payload = {}
    raw = payload.get("raw") if isinstance(payload, dict) and isinstance(payload.get("raw"), dict) else {}
    characters: list[dict[str, Any]] = []
    seen: set[str] = set()

    def append_character(name: Any, source: dict[str, Any]) -> None:
        display_name = str(name or "").strip()
        key = display_name.casefold()
        if not display_name or key in seen:
            return
        persona = character_persona_text(source)
        if not persona:
            return
        seen.add(key)
        characters.append({
            "name": display_name,
            "persona": persona,
            "trust": 50.0,
            "addressed": False,
        })

    append_character(raw.get("name"), raw)
    personas = raw.get("personas")
    items = personas.items() if isinstance(personas, dict) else enumerate(personas, start=1) if isinstance(personas, list) else []
    for key, persona in items:
        if isinstance(persona, dict):
            append_character(persona.get("name") or key, persona)
    return characters


def role_card_characters(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    candidate = payload
    if isinstance(payload.get("raw"), dict):
        candidate = payload["raw"]
    if isinstance(candidate.get("data"), dict):
        candidate = candidate["data"]
    if not isinstance(candidate, dict):
        return []

    characters: list[dict[str, Any]] = []
    seen: set[str] = set()

    def append_character(name: Any, source: dict[str, Any]) -> None:
        display_name = str(name or "").strip()
        key = display_name.casefold()
        persona = character_persona_text(source)
        if not display_name or not persona or key in seen:
            return
        seen.add(key)
        characters.append({
            "name": display_name,
            "persona": persona,
            "trust": 50.0,
            "addressed": False,
        })

    append_character(candidate.get("name"), candidate)
    personas = candidate.get("personas")
    items = personas.items() if isinstance(personas, dict) else enumerate(personas, start=1) if isinstance(personas, list) else []
    for key, persona in items:
        if isinstance(persona, dict):
            append_character(persona.get("name") or key, persona)
    return characters


def merge_characters(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged = [clone(item) for item in existing if isinstance(item, dict)]
    indexes = {
        str(item.get("name") or "").strip().casefold(): index
        for index, item in enumerate(merged)
        if str(item.get("name") or "").strip()
    }
    for item in incoming:
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        normalized = {
            "name": name,
            "persona": str(item.get("persona") or "").strip(),
            "trust": float(item.get("trust", 50)),
            "addressed": bool(item.get("addressed", False)),
        }
        key = name.casefold()
        if key in indexes:
            previous = merged[indexes[key]]
            normalized["trust"] = float(previous.get("trust", normalized["trust"]))
            normalized["addressed"] = bool(previous.get("addressed", normalized["addressed"]))
            if not normalized["persona"]:
                normalized["persona"] = str(previous.get("persona") or "")
            merged[indexes[key]] = normalized
        else:
            indexes[key] = len(merged)
            merged.append(normalized)
    return merged


def read_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        state = new_session_state()
        write_state(state)
        return state
    try:
        payload = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return clone(DEFAULT_STATE)
    if not isinstance(payload, dict):
        return new_session_state()
    merged = clone(DEFAULT_STATE)
    merged.update(payload)
    settings = clone(DEFAULT_STATE["settings"])
    if isinstance(payload.get("settings"), dict):
        settings.update(payload["settings"])
    settings["enabled"] = bool(settings.get("enabled", False))
    settings["interval_sec"] = 30
    settings["auto_interact"] = bool(settings.get("auto_interact", False))
    settings["observer_mode"] = bool(settings.get("observer_mode", False))
    settings["show_silent"] = bool(settings.get("show_silent", False))
    merged["settings"] = settings
    changed = False
    if not str(merged.get("session_id") or "").strip():
        merged["session_id"] = uuid.uuid4().hex
        merged["session_seed"] = random.SystemRandom().randrange(1, 2_147_483_647)
        merged["event_theme"] = random.SystemRandom().choice(EVENT_THEMES)
        merged["session_started_at"] = now_string()
        changed = True
    for item in merged.get("history", []):
        if not isinstance(item, dict):
            continue
        if not str(item.get("id") or "").strip():
            item["id"] = uuid.uuid4().hex
            changed = True
        if not str(item.get("created_at") or "").strip():
            item["created_at"] = now_string()
            changed = True
    if changed:
        write_state(merged)
    return merged


def write_state(payload: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def now_string() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def speak_probability(persona: str, *, trust: float = 50.0, addressed: bool = False) -> float:
    """角色「是否发言」的概率（与前端 willSpeak 保持一致的启发式）。"""
    text = str(persona or "")
    p = 0.55
    if any(k in text for k in SILENT):
        p -= 0.25
    if any(k in text for k in TALKATIVE):
        p += 0.25
    if any(k in text for k in WARY):
        p -= 0.10
    if addressed:
        p += 0.40
    p += (float(trust) - 50.0) / 200.0
    return max(0.05, min(0.95, p))


def will_speak(persona: str, *, trust: float = 50.0, addressed: bool = False,
               rng: random.Random | None = None) -> bool:
    r = rng or random
    return r.random() < speak_probability(persona, trust=trust, addressed=addressed)


# ---- LLM 调用（直接复用 Fantareal 全局设置）-----------------------------------
def read_main_llm_config() -> dict[str, Any]:
    try:
        settings = json.loads(MAIN_SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        settings = {}
    if not isinstance(settings, dict):
        settings = {}
    return {
        "base_url": str(settings.get("llm_base_url") or os.environ.get("LLM_BASE_URL") or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1").strip(),
        "api_key": str(settings.get("llm_api_key") or os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY") or "").strip(),
        "model": str(settings.get("llm_model") or os.environ.get("LLM_MODEL") or "gpt-4o-mini").strip(),
        "temperature": max(0.0, min(2.0, float(settings.get("temperature") or 0.9))),
        "request_timeout": max(10, min(600, int(settings.get("request_timeout") or 120))),
    }


def public_state(state: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = clone(state or read_state())
    config = read_main_llm_config()
    payload["model_config"] = {
        "configured": bool(config["api_key"] and config["model"]),
        "model": config["model"],
        "base_url": config["base_url"],
    }
    return payload


def call_llm(system: str, user: str) -> str | None:
    config = read_main_llm_config()
    if not config["api_key"] or not config["model"]:
        return None
    body = json.dumps({
        "model": config["model"],
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": config["temperature"],
    }).encode("utf-8")
    req = urllib.request.Request(
        config["base_url"].rstrip("/") + "/chat/completions",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + config["api_key"]},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=config["request_timeout"]) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]
    except Exception:
        return None


def parse_json_object(text: str | None) -> dict[str, Any]:
    value = str(text or "").strip()
    if not value:
        return {}
    if value.startswith("```"):
        value = value.split("\n", 1)[-1]
        value = value.rsplit("```", 1)[0].strip()
    try:
        payload = json.loads(value)
    except ValueError:
        start = value.find("{")
        end = value.rfind("}")
        if start < 0 or end <= start:
            return {}
        try:
            payload = json.loads(value[start:end + 1])
        except ValueError:
            return {}
    return payload if isinstance(payload, dict) else {}


# ---- 本地 mock 回退（无 Key 也能体验完整回合循环）----------------------------
MOCK_NARRATION = [
    "夜色渐沉，远处传来不明的圣响。空气里有一丝异样的气息。",
    "风掠过遗迹，尘土中隐隐浮现古老的纹路。有人的呼吸变得谨慎。",
    "一道微光从废墟深处亮起，似乎在回应某种呼唤。",
    "天色微亮，雾气渐散。道路在脚下延伸向未知。",
]
MOCK_LINES = [
    "*环顾四周*“这里不对劲。”",
    "“谁在那里？”*厕手按上剑柄*",
    "“先别冲动，我们需要更多线索。”",
    "*沉默片刻*“……跟上。”",
]


def mock_narration(turn: int) -> str:
    return MOCK_NARRATION[turn % len(MOCK_NARRATION)]


def mock_line(idx: int) -> str:
    return MOCK_LINES[idx % len(MOCK_LINES)]


def mock_choices(turn: int) -> list[dict[str, str]]:
    sets = [
        [
            {"label": "靠近那道微光", "intent": "主动调查异常源头"},
            {"label": "先观察四周", "intent": "谨慎收集环境线索"},
            {"label": "询问身边的角色", "intent": "优先交流并确认对方判断"},
        ],
        [
            {"label": "顺着声音前进", "intent": "追踪刚刚出现的动静"},
            {"label": "停下整理线索", "intent": "回顾当前信息并寻找矛盾"},
            {"label": "改变前进方向", "intent": "避开风险并探索另一条路线"},
        ],
    ]
    return clone(sets[turn % len(sets)])


# ---- prompt 组装 ----------------------------------------------------------------
def recent_history_text(
    state: dict[str, Any],
    limit: int = 10,
    external_history: list[dict[str, Any]] | None = None,
) -> str:
    rows = []
    for item in (external_history or [])[-limit:]:
        role = str(item.get("role") or "未知")
        text = visible_message_text(item.get("content") or item.get("text"))
        if text:
            rows.append(f"{role}：{text}")
    for item in state.get("history", [])[-limit:]:
        name = str(item.get("name") or item.get("role") or "未知")
        text = visible_message_text(item.get("text"))
        if text:
            rows.append(f"{name}：{text}")
    return "\n".join(rows) or "尚无历史，作为故事开端。"


def cast_text(state: dict[str, Any]) -> str:
    rows = []
    for char in state.get("characters", []):
        rows.append(f"角色名：{char.get('name')}\n人设：{char.get('persona', '')}")
    return "\n\n".join(rows) or "暂无角色资料。"


def gm_system(state: dict[str, Any]) -> str:
    env = state.get("env", {})
    return (
        f"Session seed: {state.get('session_seed')}; opening event theme: {state.get('event_theme')}. "
        "你是沉浸式角色扮演故事的旁白与事件导演。"
        "玩家可以全程保持沉默并作为旁观者。玩家未行动时，让事件由角色自身目标、角色关系和现场变化推动。"
        "必须根据角色人设、场景和最近剧情生成一个自然但具有随机性的事件，不能使用与设定无关的通用遗迹模板。"
        "事件可以是日常插曲、关系变化、环境异动、人物需求、秘密线索或轻度危机；避免无缘由升级为世界毁灭。"
        "旁白只描述环境、事件和可观察结果，不替角色说话。"
        "同时生成三个给玩家的行动选项：一个主动、一个谨慎、一个偏交流或情感方向，三项必须真正不同。"
        "严格输出 JSON，不要代码块："
        '{"narration":"2-4句中文旁白","event":"一句事件摘要",'
        '"choices":[{"label":"选项短句","intent":"行动含义"},'
        '{"label":"选项短句","intent":"行动含义"},{"label":"选项短句","intent":"行动含义"}]}。'
        f"当前环境：时间={env.get('time')}，地点={env.get('place')}，天气={env.get('weather')}。"
    )


def char_system(char: dict[str, Any], state: dict[str, Any]) -> str:
    env = state.get("env", {})
    return (
        f"你扮演角色「{char.get('name')}」。人设：{char.get('persona', '')}。"
        "以第一人称自主行动与说话，符合性格。动作用 *斜体*，对话用引号。只输出 1-3 句。"
        f"场景：{env.get('place')}，{env.get('time')}。"
    )


def generate_event(
    state: dict[str, Any],
    player_choice: str,
    external_history: list[dict[str, Any]] | None = None,
) -> tuple[str, str, list[dict[str, str]]]:
    choice_line = player_choice.strip() or (
        "玩家保持沉默，只旁观角色互动。不要等待或追问玩家，"
        "让角色主动发起话题、行动、合作或冲突。"
    )
    user = (
        f"Random turn marker: {uuid.uuid4().hex}.\n"
        f"参与角色资料：\n{cast_text(state)}\n\n"
        f"最近剧情：\n{recent_history_text(state, external_history=external_history)}\n\n"
        f"玩家本回合状态：{choice_line}\n"
        "生成下一段事件旁白和三个后续选项。"
        "玩家沉默时，旁白必须提供能让多个角色互相回应的具体契机，不能把问题抛回给玩家。"
        "不要重复最近已经发生的事件。"
    )
    payload = parse_json_object(call_llm(gm_system(state), user))
    random_index = int(state.get("turn", 0)) + int(state.get("session_seed", 0))
    narration = str(payload.get("narration") or "").strip() or mock_narration(random_index)
    event = str(payload.get("event") or narration[:80]).strip()
    choices: list[dict[str, str]] = []
    for item in payload.get("choices", []) if isinstance(payload.get("choices"), list) else []:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()[:40]
        intent = str(item.get("intent") or label).strip()[:100]
        if label:
            choices.append({"label": label, "intent": intent})
    if len(choices) != 3:
        choices = mock_choices(random_index)
    return narration, event, choices


# ---- API ---------------------------------------------------------------------------
app = FastAPI(title="Fantareal Auto Saga Mod")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class CharactersPayload(BaseModel):
    characters: list[dict[str, Any]] = Field(default_factory=list)
    env: dict[str, Any] | None = None


class SettingsPayload(BaseModel):
    enabled: bool | None = None
    interval_sec: int | None = None
    auto_interact: bool | None = None
    observer_mode: bool | None = None
    show_silent: bool | None = None


class NextPayload(BaseModel):
    choice: str = ""
    choice_message_id: str = ""
    recent_history: list[dict[str, Any]] = Field(default_factory=list)


class CardImportPayload(BaseModel):
    raw_json: str


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        {"state": public_state()},
    )


@app.get("/api/state")
def get_state() -> dict[str, Any]:
    return public_state()


@app.get("/api/current-card-characters")
def get_current_card_characters() -> dict[str, Any]:
    return {"characters": current_card_characters()}


@app.post("/api/characters/import-card")
def import_card_characters(payload: CardImportPayload) -> dict[str, Any]:
    try:
        raw = json.loads(payload.raw_json)
    except ValueError:
        return {"ok": False, "error": "角色卡不是有效的 JSON。"}
    characters = role_card_characters(raw)
    if not characters:
        return {"ok": False, "error": "没有从角色卡中读取到有效角色。"}
    state = read_state()
    state["characters"] = merge_characters(state.get("characters", []), characters)
    write_state(state)
    result = public_state(state)
    result["ok"] = True
    result["imported_count"] = len(characters)
    return result


@app.post("/api/characters")
def set_characters(payload: CharactersPayload) -> dict[str, Any]:
    state = read_state()
    chars = []
    for c in payload.characters:
        chars.append({
            "name": str(c.get("name") or "角色").strip(),
            "persona": str(c.get("persona") or "").strip(),
            "trust": float(c.get("trust", 50)),
            "addressed": bool(c.get("addressed", False)),
        })
    state["characters"] = chars
    if payload.env:
        state["env"].update(payload.env)
    write_state(state)
    return public_state(state)


@app.post("/api/settings")
def set_settings(payload: SettingsPayload) -> dict[str, Any]:
    state = read_state()
    if payload.enabled is not None:
        state["settings"]["enabled"] = bool(payload.enabled)
    if payload.interval_sec is not None:
        state["settings"]["interval_sec"] = 30
    if payload.auto_interact is not None:
        state["settings"]["auto_interact"] = bool(payload.auto_interact)
    if payload.observer_mode is not None:
        state["settings"]["observer_mode"] = bool(payload.observer_mode)
    if payload.show_silent is not None:
        state["settings"]["show_silent"] = bool(payload.show_silent)
    write_state(state)
    return public_state(state)


@app.post("/api/reset")
def reset_state() -> dict[str, Any]:
    state = new_session_state(read_state())
    write_state(state)
    return public_state(state)


@app.post("/api/characters/merge")
def merge_character_list(payload: CharactersPayload) -> dict[str, Any]:
    state = read_state()
    state["characters"] = merge_characters(state.get("characters", []), payload.characters)
    if payload.env:
        state["env"].update(payload.env)
    write_state(state)
    return public_state(state)


@app.post("/api/session/end")
def end_session() -> dict[str, Any]:
    previous = read_state()
    state = new_session_state(previous)
    write_state(state)
    return {
        "ok": True,
        "previous_session_id": previous.get("session_id"),
        "state": public_state(state),
    }


@app.post("/api/next")
def advance_turn(payload: NextPayload) -> dict[str, Any]:
    """推进一回合：旁白 + 逐角色自主判定是否发言。"""
    state = read_state()
    state["turn"] = int(state.get("turn", 0)) + 1
    messages: list[dict[str, Any]] = []
    player_choice = payload.choice.strip()
    if player_choice:
        state["history"].append({"role": "user", "name": "玩家选择", "text": player_choice})

    # 1) GM / 旁白
    narration, event_summary, choices = generate_event(state, player_choice, payload.recent_history)
    messages.append({"role": "gm", "name": "旁白", "text": narration})
    state["history"].append({"role": "gm", "name": "旁白", "text": narration})
    state["events"].append(f"第 {state['turn']} 回合：{event_summary}")

    # 2) 逐角色自主判定
    spoke_any = False
    characters = state.get("characters", [])
    speaking_flags = [
        will_speak(
            char.get("persona", ""),
            trust=float(char.get("trust", 50)),
            addressed=bool(char.get("addressed", False)),
        )
        for char in characters
    ]
    if characters and not any(speaking_flags):
        speaking_flags[0] = True
    if not player_choice and len(characters) > 1:
        desired_speakers = min(len(characters), max(2, sum(speaking_flags)))
        for index in range(len(speaking_flags)):
            if sum(speaking_flags) >= desired_speakers:
                break
            speaking_flags[index] = True
    generated_exchange: list[str] = []
    for idx, char in enumerate(characters):
        if speaking_flags[idx]:
            spoke_any = True
            character_input = (
                f"刚发生的事件：{narration}\n"
                f"玩家状态：{player_choice or '保持沉默，仅旁观角色互动'}\n"
                f"最近剧情：\n{recent_history_text(state, 8, payload.recent_history)}\n"
                f"本回合其他角色已经说过或做过：\n{chr(10).join(generated_exchange) or '暂无'}\n"
                "让该角色依据自身人设主动行动或说话。玩家沉默时，优先回应其他角色、"
                "向其他角色发起交流，或推动角色之间的关系与矛盾。"
                "不要强迫玩家回答，也不要替玩家说话。"
            )
            raw_line = call_llm(char_system(char, state), character_input)
            line = visible_message_text(raw_line) or mock_line(idx + state["turn"])
            messages.append({"role": "char", "name": char.get("name"), "text": line})
            state["history"].append({"role": "char", "name": char.get("name"), "text": line})
            generated_exchange.append(f"{char.get('name')}：{line}")
            char["addressed"] = False
        else:
            messages.append({"role": "silent", "name": char.get("name"),
                             "text": f"*{char.get('name')}沉默不语。*"})

    if state.get("characters") and not spoke_any:
        state["events"].append(f"第 {state['turn']} 回合：全场沉默。")

    # 限制历史/事件长度
    for item in state["history"]:
        if isinstance(item, dict) and not str(item.get("id") or "").strip():
            item["id"] = uuid.uuid4().hex
            item["created_at"] = str(item.get("created_at") or now_string())
    if player_choice and payload.choice_message_id.strip():
        for item in reversed(state["history"]):
            if item.get("role") == "user" and item.get("text") == player_choice:
                item["id"] = payload.choice_message_id.strip()
                break
    for message in messages:
        for item in reversed(state["history"]):
            if (
                item.get("role") == message.get("role")
                and item.get("name") == message.get("name")
                and item.get("text") == message.get("text")
            ):
                message["id"] = item["id"]
                message["created_at"] = item["created_at"]
                break

    state["history"] = state["history"][-200:]
    state["events"] = state["events"][-50:]
    observer_mode = bool(state.get("settings", {}).get("observer_mode", False))
    visible_choices = [] if observer_mode else choices
    state["choices"] = visible_choices
    write_state(state)

    return {
        "turn": state["turn"],
        "messages": messages,
        "env": state["env"],
        "events": state["events"][-10:],
        "choices": visible_choices,
        "observer_mode": observer_mode,
        "llm": bool(read_main_llm_config()["api_key"]),
    }
