from __future__ import annotations

"""auto-saga mod 后端 — 自动叙事模式（v0.2.0）

旁观式玩法的服务端：每点一次 Next，后端推进一回合：
  1) GM/旁白推进环境与事件；
  2) 逐个在场角色按人设卡性格 + 信任 + 是否被点名 + 随机性 判定是否发言。

设计原则：自包含、零侵入。
  - 独立 FastAPI 子应用，沿用 status panel 的 mod 后端约定（app = FastAPI(...)，挂 /static）。
  - 运行时状态写项目级 data/auto_saga/，不随 mod 目录替换丢失。
  - LLM 调用优先读环境变量（OPENAI_API_KEY / LLM_API_KEY 等）；无 Key 时用本地 mock 回退，
    保证离线可试玩，且 API Key 不暴露到前端。

关联 Issue #4。
"""

import json
import os
import random
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
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
STATIC_DIR = RESOURCE_DIR / "static"

DEFAULT_STATE: dict[str, Any] = {
    "turn": 0,
    "env": {"time": "第一幕", "place": "世界入口", "weather": "平静"},
    "characters": [],          # [{name, persona, trust, addressed}]
    "events": [],              # ["..."]
    "history": [],             # [{role, name, text}]
    "settings": {"interval_sec": 6},
}

# ---- 性格 → 发言倾向权重 ----------------------------------------------------
TALKATIVE = ("健谈", "热情", "话痨", "外向", "活泼", "开朗")
SILENT = ("沉默", "寡言", "高冷", "冷淡", "内向", "沉稳")
WARY = ("多疑", "谨慎", "警惕", "犹豫")


def clone(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False))


def read_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return clone(DEFAULT_STATE)
    try:
        payload = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return clone(DEFAULT_STATE)
    if not isinstance(payload, dict):
        return clone(DEFAULT_STATE)
    merged = clone(DEFAULT_STATE)
    merged.update(payload)
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


# ---- LLM 调用（Key 仅在后端环境变量，不暴露前端）------------------------------
def _llm_key() -> str:
    for name in ("AUTO_SAGA_API_KEY", "LLM_API_KEY", "OPENAI_API_KEY"):
        val = os.environ.get(name)
        if val:
            return val
    return ""


def call_llm(system: str, user: str) -> str | None:
    key = _llm_key()
    if not key:
        return None
    base = os.environ.get("LLM_BASE_URL") or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"
    model = os.environ.get("LLM_MODEL") or "gpt-4o-mini"
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.9,
    }).encode("utf-8")
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]
    except Exception:
        return None


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


# ---- prompt 组装 ----------------------------------------------------------------
def gm_system(state: dict[str, Any]) -> str:
    env = state.get("env", {})
    return (
        "你是一款文字冒险游戏的「旁白/GM」。用简洁沉浸的中文推进环境与事件，不替角色说话。"
        "可用 Markdown；涉及数值/概率时可用行内数学公式如 $p=0.5$。只输出 1-3 句。"
        f"当前：时间={env.get('time')} 地点={env.get('place')} 天气={env.get('weather')}。"
    )


def char_system(char: dict[str, Any], state: dict[str, Any]) -> str:
    env = state.get("env", {})
    return (
        f"你扮演角色「{char.get('name')}」。人设：{char.get('persona', '')}。"
        "以第一人称自主行动与说话，符合性格。动作用 *斜体*，对话用引号。只输出 1-3 句。"
        f"场景：{env.get('place')}，{env.get('time')}。"
    )


# ---- API ---------------------------------------------------------------------------
app = FastAPI(title="Fantareal Auto Saga Mod")

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class CharactersPayload(BaseModel):
    characters: list[dict[str, Any]] = Field(default_factory=list)
    env: dict[str, Any] | None = None


class SettingsPayload(BaseModel):
    interval_sec: int | None = None


@app.get("/api/state")
def get_state() -> dict[str, Any]:
    return read_state()


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
    return state


@app.post("/api/settings")
def set_settings(payload: SettingsPayload) -> dict[str, Any]:
    state = read_state()
    if payload.interval_sec is not None:
        state["settings"]["interval_sec"] = max(2, min(60, int(payload.interval_sec)))
    write_state(state)
    return state


@app.post("/api/reset")
def reset_state() -> dict[str, Any]:
    state = clone(DEFAULT_STATE)
    write_state(state)
    return state


@app.post("/api/next")
def advance_turn() -> dict[str, Any]:
    """推进一回合：旁白 + 逐角色自主判定是否发言。"""
    state = read_state()
    state["turn"] = int(state.get("turn", 0)) + 1
    messages: list[dict[str, Any]] = []

    # 1) GM / 旁白
    narration = call_llm(gm_system(state), "推进下一刻的场景。") or mock_narration(state["turn"])
    messages.append({"role": "gm", "name": "旁白", "text": narration})
    state["history"].append({"role": "gm", "name": "旁白", "text": narration})

    # 2) 逐角色自主判定
    spoke_any = False
    for idx, char in enumerate(state.get("characters", [])):
        addressed = bool(char.get("addressed", False))
        if will_speak(char.get("persona", ""), trust=float(char.get("trust", 50)), addressed=addressed):
            spoke_any = True
            line = call_llm(char_system(char, state), narration) or mock_line(idx + state["turn"])
            messages.append({"role": "char", "name": char.get("name"), "text": line})
            state["history"].append({"role": "char", "name": char.get("name"), "text": line})
            char["addressed"] = False
        else:
            messages.append({"role": "silent", "name": char.get("name"),
                             "text": f"*{char.get('name')}沉默不语。*"})

    if state.get("characters") and not spoke_any:
        state["events"].append(f"第 {state['turn']} 回合：全场沉默。")

    # 限制历史/事件长度
    state["history"] = state["history"][-200:]
    state["events"] = state["events"][-50:]
    write_state(state)

    return {
        "turn": state["turn"],
        "messages": messages,
        "env": state["env"],
        "events": state["events"][-10:],
        "llm": bool(_llm_key()),
    }
