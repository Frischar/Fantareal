from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field


def get_resource_dir() -> Path:
    bundle_dir = getattr(sys, "_MEIPASS", "")
    if bundle_dir:
        return Path(bundle_dir)
    return Path(__file__).resolve().parent


RESOURCE_DIR = get_resource_dir()
APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
STATIC_DIR = RESOURCE_DIR / "static"
TEMPLATES_DIR = RESOURCE_DIR / "templates"
SETTINGS_PATH = DATA_DIR / "settings.json"
WORKSPACE_PATH = DATA_DIR / "workspace.json"

SOURCE_MODE_OPTIONS = [
    {"value": "mixed", "label": "混合素材", "hint": "设定、剧情、角色、地点混在一起时使用。"},
    {"value": "setting", "label": "设定文档", "hint": "偏世界观、规则、术语、背景介绍。"},
    {"value": "plot", "label": "剧情提纲", "hint": "偏事件链、阶段变化、长期状态。"},
    {"value": "character", "label": "角色资料", "hint": "偏人物、关系、身份、禁忌与习惯。"},
    {"value": "location", "label": "地点资料", "hint": "偏地区、场景、机构、地图锚点。"},
    {"value": "rules", "label": "规则系统", "hint": "偏能力、机制、限制条件、世界规则。"},
]

FOCUS_MODE_OPTIONS = [
    {"value": "balanced", "label": "平衡抽取", "hint": "兼顾可读性、检索命中和设定完整度。"},
    {"value": "retrieval", "label": "检索优先", "hint": "更短 trigger，更强调高命中率和模块拆分。"},
    {"value": "rich", "label": "设定完整", "hint": "允许更完整的正文，适合厚设定项目。"},
    {"value": "player_friendly", "label": "玩家友好", "hint": "更重视场景理解、行为约束和关系提示。"},
]

STARTER_SNIPPETS = [
    {
        "label": "角色模板",
        "content": "角色名：\n身份定位：\n性格关键词：\n核心关系：\n禁忌与底线：\n长期会影响剧情的设定：",
    },
    {
        "label": "地点模板",
        "content": "地点名：\n地点类型：\n地标与功能：\n常驻势力：\n特殊规则：\n在剧情中的长期作用：",
    },
    {
        "label": "势力模板",
        "content": "势力名：\n目标：\n阵营立场：\n核心成员：\n控制范围：\n与其他势力的关系：",
    },
    {
        "label": "剧情阶段模板",
        "content": "阶段名：\n阶段前提：\n当前矛盾：\n角色关系变化：\n阶段规则：\n阶段结束条件：",
    },
]

DEFAULT_WORLDBOOK_SETTINGS = {
    "enabled": True,
    "debug_enabled": False,
    "max_hits": 5,
    "default_case_sensitive": False,
    "default_whole_word": False,
    "default_match_mode": "any",
    "default_secondary_mode": "all",
}

DEFAULT_SYSTEM_PROMPT = """
# Role
你是一个顶级的故事世界构建专家和数据结构化解析引擎。你的任务是阅读用户提供的长篇自然语言文本（包含世界观、人物、地点、物品、历史等设定），并将其拆解、提炼为严谨的「世界书（Worldbook）」JSON 格式。

# Task
1. **实体识别与拆解**：从用户的文本中识别出所有独立的概念（如：特定角色、地点、组织名称、魔法/科技设定、重要事件等）。
2. **内容精炼**：将每个概念的相关描述提炼为高信息密度的文本（作为 `content`），去掉冗余的口语化表达，确保适合作为 AI 的背景上下文。
3. **格式化输出**：将提取出的数据严格按照指定的 JSON 结构进行组装。

# Extraction Rules
- **id**: 必须为唯一的字符串，格式为 `worldbook-[13位时间戳]-[5位随机小写字母和数字]`（例如：`worldbook-1776759884726-awz66`）。
- **title**: 该设定的名称（如“魔法学院”、“艾莉丝”）。
- **trigger**: 触发该设定的核心关键词，通常与 title 相同。如果有多个同义词或别名，请用英文逗号分隔。
- **secondary_trigger**: 次要触发词，若没有则留空字符串 `""`。
- **content**: 设定的具体描述。
- **priority**: 默认填 `100`。如果是非常核心的世界基底设定，可以设为 `101` 或更高。
- **enabled**: 始终为 `true`。
- **case_sensitive** & **whole_word**: 始终为 `false`。
- **match_mode**: 默认填 `"any"`。
- **secondary_mode**: 默认填 `"all"`。
- **comment**: 简短的一句话分类（如“人物设定”、“地理位置”），方便人类阅读。

# Output Format
你必须**且只能**输出一个合法的 JSON 对象，不要包含任何 Markdown 代码块修饰符（如 ```json），也不要包含任何多余的解释文字。JSON 的根结构必须如下：

{
  "entries": [
    // 提取的词条对象列表
  ],
  "settings": {
    "debug_enabled": false,
    "default_case_sensitive": false,
    "default_match_mode": "any",
    "default_secondary_mode": "all",
    "default_whole_word": false,
    "enabled": true,
    "max_hits": 5
  }
}
""".strip()

DEFAULT_SETTINGS = {
    "base_url": "",
    "api_key": "",
    "model": "",
    "temperature": 0.35,
    "request_timeout": 120,
    "system_prompt": DEFAULT_SYSTEM_PROMPT,
    "generation": {
        "source_mode": "mixed",
        "focus_mode": "balanced",
        "target_entry_count": 8,
        "extra_requirements": "",
    },
    "appearance": {
        "background_image": "",
        "background_overlay": 0.46,
        "panel_opacity": 0.88,
        "blur_strength": 18,
        "accent_color": "#5ec2a8",
    },
}

HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})$")


class GenerationSettingsPayload(BaseModel):
    source_mode: str = "mixed"
    focus_mode: str = "balanced"
    target_entry_count: int = Field(default=8)
    extra_requirements: str = ""


class AppearanceSettingsPayload(BaseModel):
    background_image: str = ""
    background_overlay: float = Field(default=0.46)
    panel_opacity: float = Field(default=0.88)
    blur_strength: int = Field(default=18)
    accent_color: str = "#5ec2a8"


class SettingsPayload(BaseModel):
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    temperature: float = Field(default=0.35)
    request_timeout: int = Field(default=120)
    system_prompt: str = ""
    generation: GenerationSettingsPayload = Field(default_factory=GenerationSettingsPayload)
    appearance: AppearanceSettingsPayload = Field(default_factory=AppearanceSettingsPayload)


class WorkspacePayload(BaseModel):
    project_name: str = ""
    source_text: str = ""
    raw_output: str = ""


class GeneratePayload(SettingsPayload):
    project_name: str = ""
    source_text: str = ""
    raw_output: str = ""
    store: dict[str, Any] | None = None


class PreviewPayload(BaseModel):
    raw_output: str = ""


def ensure_data_files() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not SETTINGS_PATH.exists():
        write_json(SETTINGS_PATH, DEFAULT_SETTINGS)
    if not WORKSPACE_PATH.exists():
        write_json(WORKSPACE_PATH, default_workspace())


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def default_worldbook_store() -> dict[str, Any]:
    return {"settings": dict(DEFAULT_WORLDBOOK_SETTINGS), "entries": []}


def default_workspace() -> dict[str, Any]:
    return {
        "project_name": "",
        "source_text": "",
        "raw_output": "",
        "generated_at": "",
        "store": default_worldbook_store(),
    }


def clamp_float(value: Any, minimum: float, maximum: float, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def clamp_int(value: Any, minimum: int, maximum: int, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def sanitize_color(value: Any, default: str) -> str:
    text = str(value or "").strip()
    return text if HEX_COLOR_RE.fullmatch(text) else default


def sanitize_generation_settings(raw: Any) -> dict[str, Any]:
    settings = dict(DEFAULT_SETTINGS["generation"])
    data = raw if isinstance(raw, dict) else {}
    settings["source_mode"] = str(data.get("source_mode", settings["source_mode"])).strip().lower()
    if settings["source_mode"] not in {item["value"] for item in SOURCE_MODE_OPTIONS}:
        settings["source_mode"] = DEFAULT_SETTINGS["generation"]["source_mode"]
    settings["focus_mode"] = str(data.get("focus_mode", settings["focus_mode"])).strip().lower()
    if settings["focus_mode"] not in {item["value"] for item in FOCUS_MODE_OPTIONS}:
        settings["focus_mode"] = DEFAULT_SETTINGS["generation"]["focus_mode"]
    settings["target_entry_count"] = clamp_int(
        data.get("target_entry_count"),
        1,
        60,
        DEFAULT_SETTINGS["generation"]["target_entry_count"],
    )
    settings["extra_requirements"] = str(data.get("extra_requirements", "")).strip()
    return settings


def sanitize_appearance_settings(raw: Any) -> dict[str, Any]:
    settings = dict(DEFAULT_SETTINGS["appearance"])
    data = raw if isinstance(raw, dict) else {}
    settings["background_image"] = str(data.get("background_image", "")).strip()
    settings["background_overlay"] = clamp_float(
        data.get("background_overlay"),
        0.0,
        0.92,
        DEFAULT_SETTINGS["appearance"]["background_overlay"],
    )
    settings["panel_opacity"] = clamp_float(
        data.get("panel_opacity"),
        0.5,
        0.98,
        DEFAULT_SETTINGS["appearance"]["panel_opacity"],
    )
    settings["blur_strength"] = clamp_int(
        data.get("blur_strength"),
        0,
        40,
        DEFAULT_SETTINGS["appearance"]["blur_strength"],
    )
    settings["accent_color"] = sanitize_color(
        data.get("accent_color"),
        DEFAULT_SETTINGS["appearance"]["accent_color"],
    )
    return settings


def sanitize_settings(raw: Any) -> dict[str, Any]:
    data = dict(DEFAULT_SETTINGS)
    if not isinstance(raw, dict):
        return data

    data["base_url"] = str(raw.get("base_url", "")).strip()
    data["api_key"] = str(raw.get("api_key", "")).strip()
    data["model"] = str(raw.get("model", "")).strip()
    data["temperature"] = clamp_float(raw.get("temperature"), 0.0, 2.0, DEFAULT_SETTINGS["temperature"])
    data["request_timeout"] = clamp_int(raw.get("request_timeout"), 10, 600, DEFAULT_SETTINGS["request_timeout"])
    data["system_prompt"] = str(raw.get("system_prompt", "")).strip() or DEFAULT_SYSTEM_PROMPT

    generation_raw = raw.get("generation", {})
    if not isinstance(generation_raw, dict):
        generation_raw = {
            "source_mode": raw.get("source_mode"),
            "focus_mode": raw.get("focus_mode"),
            "target_entry_count": raw.get("target_entry_count"),
            "extra_requirements": raw.get("extra_requirements"),
        }
    data["generation"] = sanitize_generation_settings(generation_raw)

    appearance_raw = raw.get("appearance", {})
    if not isinstance(appearance_raw, dict):
        appearance_raw = {
            "background_image": raw.get("background_image"),
            "background_overlay": raw.get("background_overlay"),
            "panel_opacity": raw.get("panel_opacity"),
            "blur_strength": raw.get("blur_strength"),
            "accent_color": raw.get("accent_color"),
        }
    data["appearance"] = sanitize_appearance_settings(appearance_raw)
    return data


def sanitize_worldbook_settings(raw: Any) -> dict[str, Any]:
    settings = dict(DEFAULT_WORLDBOOK_SETTINGS)
    data = raw if isinstance(raw, dict) else {}
    settings["enabled"] = bool(data.get("enabled", settings["enabled"]))
    settings["debug_enabled"] = bool(data.get("debug_enabled", settings["debug_enabled"]))
    settings["max_hits"] = clamp_int(data.get("max_hits"), 1, 20, settings["max_hits"])
    settings["default_case_sensitive"] = bool(data.get("default_case_sensitive", settings["default_case_sensitive"]))
    settings["default_whole_word"] = bool(data.get("default_whole_word", settings["default_whole_word"]))

    match_mode = str(data.get("default_match_mode", settings["default_match_mode"])).strip().lower()
    settings["default_match_mode"] = match_mode if match_mode in {"any", "all"} else "any"

    secondary_mode = str(data.get("default_secondary_mode", settings["default_secondary_mode"])).strip().lower()
    settings["default_secondary_mode"] = secondary_mode if secondary_mode in {"any", "all"} else "all"
    return settings


def sanitize_worldbook_entry(raw: Any, *, index: int, settings: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    trigger = str(raw.get("trigger", "")).strip()
    content = str(raw.get("content", "")).strip()
    if not trigger or not content:
        return None

    match_mode = str(raw.get("match_mode", settings["default_match_mode"])).strip().lower()
    secondary_mode = str(raw.get("secondary_mode", settings["default_secondary_mode"])).strip().lower()
    return {
        "id": str(raw.get("id", "")).strip() or f"worldbook-{index}",
        "title": str(raw.get("title", "")).strip() or f"词条 {index}",
        "trigger": trigger,
        "secondary_trigger": str(raw.get("secondary_trigger", "")).strip(),
        "content": content,
        "enabled": bool(raw.get("enabled", True)),
        "priority": clamp_int(raw.get("priority"), 0, 9999, 100),
        "case_sensitive": bool(raw.get("case_sensitive", settings["default_case_sensitive"])),
        "whole_word": bool(raw.get("whole_word", settings["default_whole_word"])),
        "match_mode": match_mode if match_mode in {"any", "all"} else settings["default_match_mode"],
        "secondary_mode": secondary_mode if secondary_mode in {"any", "all"} else settings["default_secondary_mode"],
        "comment": str(raw.get("comment", "")).strip(),
    }


def sanitize_worldbook_store(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict) and ("settings" in raw or "entries" in raw):
        settings = sanitize_worldbook_settings(raw.get("settings", {}))
        raw_entries = raw.get("entries", [])
    elif isinstance(raw, dict) and "items" in raw:
        settings = sanitize_worldbook_settings(raw.get("settings", {}))
        raw_entries = raw.get("items", [])
    elif isinstance(raw, dict) and "trigger" in raw and "content" in raw:
        settings = sanitize_worldbook_settings({})
        raw_entries = [raw]
    elif isinstance(raw, list):
        settings = sanitize_worldbook_settings({})
        raw_entries = raw
    else:
        return default_worldbook_store()

    entries: list[dict[str, Any]] = []
    if isinstance(raw_entries, list):
        for index, item in enumerate(raw_entries, start=1):
            cleaned = sanitize_worldbook_entry(item, index=index, settings=settings)
            if cleaned:
                entries.append(cleaned)
    return {"settings": settings, "entries": entries}


def dump_worldbook_store(store: Any) -> str:
    normalized = sanitize_worldbook_store(store)
    ordered_store = {
        "settings": normalized["settings"],
        "entries": normalized["entries"],
    }
    return json.dumps(ordered_store, ensure_ascii=False, indent=2)


def build_entry_signature(entry: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(entry.get("title", "")).strip().lower(),
        str(entry.get("trigger", "")).strip().lower(),
        str(entry.get("secondary_trigger", "")).strip().lower(),
        str(entry.get("content", "")).strip().lower(),
    )


def ensure_unique_entry_id(entry_id: Any, used_ids: set[str], *, index: int) -> str:
    base_id = str(entry_id or "").strip() or f"worldbook-merged-{int(datetime.now().timestamp() * 1000)}-{index}"
    candidate = base_id
    suffix = 2
    while candidate in used_ids:
        candidate = f"{base_id}-{suffix}"
        suffix += 1
    used_ids.add(candidate)
    return candidate


def merge_worldbook_stores(current_store: Any, generated_store: Any) -> tuple[dict[str, Any], dict[str, int]]:
    existing = sanitize_worldbook_store(current_store)
    incoming = sanitize_worldbook_store(generated_store)
    merged_settings = sanitize_worldbook_settings({**incoming["settings"], **existing["settings"]})
    merged_entries: list[dict[str, Any]] = []
    used_ids: set[str] = set()
    known_signatures: set[tuple[str, str, str, str]] = set()

    for index, entry in enumerate(existing["entries"], start=1):
        copied = dict(entry)
        copied["id"] = ensure_unique_entry_id(copied.get("id"), used_ids, index=index)
        merged_entries.append(copied)
        known_signatures.add(build_entry_signature(copied))

    appended_count = 0
    skipped_duplicates = 0
    for index, entry in enumerate(incoming["entries"], start=1):
        signature = build_entry_signature(entry)
        if signature in known_signatures:
            skipped_duplicates += 1
            continue
        copied = dict(entry)
        copied["id"] = ensure_unique_entry_id(copied.get("id"), used_ids, index=len(merged_entries) + index)
        merged_entries.append(copied)
        known_signatures.add(signature)
        appended_count += 1

    return {
        "settings": merged_settings,
        "entries": merged_entries,
    }, {
        "existing_count": len(existing["entries"]),
        "generated_count": len(incoming["entries"]),
        "appended_count": appended_count,
        "skipped_duplicates": skipped_duplicates,
    }


def sanitize_workspace(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return default_workspace()
    store = sanitize_worldbook_store(raw.get("store", {}))
    raw_output = str(raw.get("raw_output", "")).strip()
    if not raw_output and store["entries"]:
        raw_output = dump_worldbook_store(store)
    return {
        "project_name": str(raw.get("project_name", "")).strip(),
        "source_text": str(raw.get("source_text", "")).strip(),
        "raw_output": raw_output,
        "generated_at": str(raw.get("generated_at", "")).strip(),
        "store": store,
    }


def get_settings() -> dict[str, Any]:
    return sanitize_settings(read_json(SETTINGS_PATH, DEFAULT_SETTINGS))


def save_settings(payload: dict[str, Any]) -> dict[str, Any]:
    settings = sanitize_settings(payload)
    write_json(SETTINGS_PATH, settings)
    return settings


def get_workspace() -> dict[str, Any]:
    return sanitize_workspace(read_json(WORKSPACE_PATH, default_workspace()))


def save_workspace(payload: dict[str, Any]) -> dict[str, Any]:
    workspace = sanitize_workspace(payload)
    write_json(WORKSPACE_PATH, workspace)
    return workspace


def build_api_url(base_url: str, endpoint: str) -> str:
    trimmed = str(base_url or "").strip().rstrip("/")
    if not trimmed:
        raise HTTPException(status_code=400, detail="请先填写 API URL。")
    if trimmed.endswith(f"/{endpoint}"):
        return trimmed
    return f"{trimmed}/{endpoint}"


def build_headers(api_key: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if str(api_key or "").strip():
        headers["Authorization"] = f"Bearer {api_key.strip()}"
    return headers


def extract_json_text(raw_text: str) -> str:
    text = str(raw_text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="当前没有可解析的输出。")
    if text.startswith("```"):
        text = text.strip("`")
        if "\n" in text:
            text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    for start_char, end_char in (("{", "}"), ("[", "]")):
        start = text.find(start_char)
        end = text.rfind(end_char)
        if start != -1 and end != -1 and end > start:
            return text[start : end + 1]
    return text


def parse_store_from_text(raw_text: str) -> dict[str, Any]:
    candidate = extract_json_text(raw_text)
    try:
        parsed = json.loads(candidate)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="输出内容不是合法 JSON，暂时无法预览。") from exc
    return sanitize_worldbook_store(parsed)


def try_parse_store_from_text(raw_text: str) -> tuple[dict[str, Any] | None, str]:
    try:
        return parse_store_from_text(raw_text), ""
    except HTTPException as exc:
        return None, str(exc.detail)


def summarize_store(store: dict[str, Any]) -> dict[str, int]:
    entries = store.get("entries", []) if isinstance(store, dict) else []
    enabled_count = sum(1 for item in entries if item.get("enabled", True))
    return {
        "entry_count": len(entries),
        "enabled_count": enabled_count,
        "disabled_count": max(0, len(entries) - enabled_count),
    }


async def probe_models_endpoint(settings: dict[str, Any]) -> dict[str, Any]:
    url = build_api_url(settings["base_url"], "models")
    result = {"ok": False, "models": [], "detail": ""}
    try:
        async with httpx.AsyncClient(timeout=float(settings["request_timeout"])) as client:
            response = await client.get(url, headers=build_headers(settings["api_key"]))
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text.strip()[:500] if exc.response is not None else str(exc)
        result["detail"] = f"/models 请求失败：{detail}"
        return result
    except httpx.HTTPError as exc:
        result["detail"] = f"/models 请求失败：{exc}"
        return result

    result["ok"] = True
    try:
        payload = response.json()
    except ValueError:
        result["detail"] = "/models 返回的不是合法 JSON。"
        return result

    raw_items = payload.get("data", []) if isinstance(payload, dict) else []
    models: list[str] = []
    if isinstance(raw_items, list):
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            model_id = str(item.get("id", "")).strip()
            if model_id:
                models.append(model_id)
    result["models"] = models
    if not models:
        result["detail"] = "/models 可访问，但没有返回可用模型列表。"
    return result


async def request_chat_completion(settings: dict[str, Any], messages: list[dict[str, str]], *, model_override: str = "") -> str:
    model_name = str(model_override or settings["model"]).strip()
    if not settings["base_url"]:
        raise HTTPException(status_code=400, detail="请先填写 API URL。")
    if not model_name:
        raise HTTPException(status_code=400, detail="请先填写模型名，或先检测服务读取模型列表。")

    url = build_api_url(settings["base_url"], "chat/completions")
    payload = {
        "model": model_name,
        "temperature": settings["temperature"],
        "messages": messages,
    }
    try:
        async with httpx.AsyncClient(timeout=float(settings["request_timeout"])) as client:
            response = await client.post(url, headers=build_headers(settings["api_key"]), json=payload)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text.strip()[:500] if exc.response is not None else str(exc)
        raise HTTPException(status_code=502, detail=f"云端 API 请求失败：{detail}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"云端 API 请求失败：{exc}") from exc

    try:
        data = response.json()
        return str(data["choices"][0]["message"]["content"]).strip()
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise HTTPException(status_code=502, detail="模型返回格式不合法，无法读取内容。") from exc


def build_generation_messages(source_text: str, settings: dict[str, Any]) -> list[dict[str, str]]:
    generation = settings["generation"]
    source_mode_labels = {item["value"]: item["label"] for item in SOURCE_MODE_OPTIONS}
    focus_mode_labels = {item["value"]: item["label"] for item in FOCUS_MODE_OPTIONS}

    mode_hint_map = {
        "mixed": "素材是混合的，请主动拆开不同概念，按地点、角色、组织、规则、阶段分别建词条。",
        "setting": "素材偏设定文档，请优先抽取名词解释、世界规则、组织、地点和长期背景。",
        "plot": "素材偏剧情提纲，请优先抽取长期状态、阶段条件、关系变化和会持续生效的背景。",
        "character": "素材偏角色资料，请优先抽取身份、关系、偏好、禁忌、立场和会影响行为的长期设定。",
        "location": "素材偏地点资料，请优先抽取地区特征、功能、势力归属、常驻角色和场景规则。",
        "rules": "素材偏规则系统，请优先抽取能力定义、使用限制、代价、例外和世界机制。",
    }
    focus_hint_map = {
        "balanced": "保持模块清晰，既要方便检索，也要保留足够的正文信息。",
        "retrieval": "更强调 trigger 简洁、别名完整、词条拆分细一些，方便后续命中。",
        "rich": "允许正文更完整，但仍要避免把多个主题塞进同一条词条。",
        "player_friendly": "更强调帮助模型理解角色行为、场景氛围、关系状态和玩家可能关心的设定。",
    }

    target_count = generation["target_entry_count"]
    extra_requirements = generation["extra_requirements"].strip()
    extra_section = f"\n额外要求：\n{extra_requirements}\n" if extra_requirements else ""

    instructions = f"""
请把下面的素材整理成 Xuqi 风格世界书 JSON。

当前生成模式：
- 素材类型：{source_mode_labels[generation["source_mode"]]}
- 处理重点：{focus_mode_labels[generation["focus_mode"]]}
- 目标条数：尽量靠近 {target_count} 条，但可以根据素材质量增减，不要凑数。

模式补充说明：
- {mode_hint_map[generation["source_mode"]]}
- {focus_hint_map[generation["focus_mode"]]}
{extra_section}
你输出时请遵守以下规则：
1. 只保留长期有效、可复用、可检索的信息。
2. 不要把一次性台词、短期镜头、单次对话原封不动塞进词条。
4. trigger ???????????????????????????????
5. secondary_trigger ???????????????
6. content ?????????????????????????????
7. comment ?????????????????????????????
8. ???????????????????

?????
1. ??? JSON???? Markdown?
2. ????????
{{
  "entries": [
    // ?????????
  ],
  "settings": {{
    "debug_enabled": false,
    "default_case_sensitive": false,
    "default_match_mode": "any",
    "default_secondary_mode": "all",
    "default_whole_word": false,
    "enabled": true,
    "max_hits": 5
  }}
}}
3. ???????

???????
{source_text}
""".strip()
    return [
        {"role": "system", "content": settings["system_prompt"]},
        {"role": "user", "content": instructions},
    ]


app = FastAPI(title="世界书生成器", version="0.5.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@app.on_event("startup")
async def startup_event() -> None:
    ensure_data_files()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    ensure_data_files()
    settings = get_settings()
    workspace = get_workspace()
    root_path = (request.scope.get("root_path") or "").rstrip("/")
    stylesheet_url = f"{root_path}/static/styles.css" if root_path else "/static/styles.css"
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "initial_settings": settings,
            "initial_workspace": workspace,
            "initial_summary": summarize_store(workspace["store"]),
            "source_mode_options": SOURCE_MODE_OPTIONS,
            "focus_mode_options": FOCUS_MODE_OPTIONS,
            "starter_snippets": STARTER_SNIPPETS,
            "default_system_prompt": DEFAULT_SYSTEM_PROMPT,
            "api_base_path": root_path,
            "static_stylesheet_url": stylesheet_url,
        },
    )


@app.get("/api/settings")
async def api_get_settings() -> dict[str, Any]:
    ensure_data_files()
    return {"settings": get_settings()}


@app.post("/api/settings")
async def api_save_settings(payload: SettingsPayload) -> dict[str, Any]:
    settings = save_settings(payload.model_dump())
    return {"ok": True, "settings": settings}


@app.get("/api/workspace")
async def api_get_workspace() -> dict[str, Any]:
    ensure_data_files()
    workspace = get_workspace()
    return {"workspace": workspace, "summary": summarize_store(workspace["store"])}


@app.post("/api/workspace/save")
async def api_save_workspace(payload: WorkspacePayload) -> dict[str, Any]:
    existing = get_workspace()
    raw_output = str(payload.raw_output or "")
    store = existing["store"]
    warnings: list[str] = []

    if raw_output.strip():
        parsed_store, error_message = try_parse_store_from_text(raw_output)
        if parsed_store is not None:
            store = parsed_store
        elif error_message:
            warnings.append(f"草稿已保存，但当前 JSON 还没整理完整：{error_message}")
    else:
        store = default_worldbook_store()

    workspace = save_workspace(
        {
            "project_name": payload.project_name,
            "source_text": payload.source_text,
            "raw_output": raw_output,
            "generated_at": existing.get("generated_at", ""),
            "store": store,
        }
    )
    return {
        "ok": True,
        "workspace": workspace,
        "summary": summarize_store(store),
        "warnings": warnings,
    }


@app.post("/api/workspace/preview")
async def api_preview_workspace(payload: PreviewPayload) -> dict[str, Any]:
    store = parse_store_from_text(payload.raw_output)
    return {"ok": True, "store": store, "summary": summarize_store(store)}


@app.post("/api/detect-service")
async def api_detect_service(payload: SettingsPayload) -> dict[str, Any]:
    settings = save_settings(payload.model_dump())
    model_probe = await probe_models_endpoint(settings)
    models = model_probe["models"]

    selected_model = settings["model"]
    warnings: list[str] = []
    if model_probe["detail"]:
        warnings.append(model_probe["detail"])
    if not selected_model and models:
        selected_model = models[0]
        warnings.append(f"未手动填写模型名，已使用检测到的第一个模型：{selected_model}")
    elif not selected_model:
        warnings.append("当前没有填写模型名，请手动填写模型，或确认 /models 能返回可用模型。")

    chat_ok = False
    reply = ""
    if selected_model:
        try:
            reply = await request_chat_completion(
                settings,
                [
                    {"role": "system", "content": "你是连接测试助手，只回复 OK。"},
                    {"role": "user", "content": "请确认服务可用。"},
                ],
                model_override=selected_model,
            )
            chat_ok = True
        except HTTPException as exc:
            warnings.append(str(exc.detail))

    return {
        "ok": True,
        "service": {
            "base_url": settings["base_url"],
            "models_endpoint_ok": bool(model_probe["ok"]),
            "chat_endpoint_ok": chat_ok,
            "selected_model": selected_model,
            "models": models,
            "reply": reply,
            "warnings": warnings,
        },
    }


@app.post("/api/generate")
async def api_generate(payload: GeneratePayload) -> dict[str, Any]:
    source_text = str(payload.source_text or "").strip()
    if not source_text:
        raise HTTPException(status_code=400, detail="请先输入原始素材。")

    settings = save_settings(payload.model_dump())
    current_store, _ = try_parse_store_from_text(payload.raw_output)
    if current_store is None:
        current_store = sanitize_worldbook_store(payload.store or {})
    raw_model_output = await request_chat_completion(settings, build_generation_messages(source_text, settings))
    generated_store = parse_store_from_text(raw_model_output)
    store, merge_summary = merge_worldbook_stores(current_store, generated_store)
    output_json = dump_worldbook_store(store)
    workspace = save_workspace(
        {
            "project_name": payload.project_name,
            "source_text": source_text,
            "raw_output": output_json,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "store": store,
        }
    )
    return {
        "ok": True,
        "output_json": output_json,
        "raw_model_output": raw_model_output,
        "store": store,
        "workspace": workspace,
        "summary": summarize_store(store),
        "merge_summary": merge_summary,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="127.0.0.1", port=8017, reload=True)
