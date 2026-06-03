from __future__ import annotations

import asyncio
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any
from urllib.parse import quote
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field


APP_DIR = Path(__file__).resolve().parent
RESOURCE_DIR = APP_DIR
PROJECT_ROOT = APP_DIR.parent.parent if APP_DIR.parent.name.lower() == "mods" else APP_DIR.parent
DATA_DIR = PROJECT_ROOT / "data" / "mobile_chat"
SETTINGS_PATH = DATA_DIR / "settings.json"
GROUPS_PATH = DATA_DIR / "groups.json"
ROLE_PROFILES_PATH = DATA_DIR / "role_profiles.json"
AUTOMATION_STATE_PATH = DATA_DIR / "automation_state.json"
PROMPT_BLOCKS_PATH = DATA_DIR / "prompt_blocks.json"
APP_REGISTRY_PATH = DATA_DIR / "app_registry.json"
CHANNELS_PATH = DATA_DIR / "channels.json"
NOTIFICATIONS_PATH = DATA_DIR / "notifications.json"
PHONE_CALLS_PATH = DATA_DIR / "phone_calls.json"
GENERATION_STATE_PATH = DATA_DIR / "generation_state.json"
MESSAGES_DIR = DATA_DIR / "messages"
EVENTS_DIR = DATA_DIR / "events"
MAIN_SETTINGS_PATH = PROJECT_ROOT / "data" / "settings.json"
ROUTE_FORWARDING_PATH = PROJECT_ROOT / "data" / "route_forwarding.json"
CURRENT_ROLE_CARD_PATH = PROJECT_ROOT / "data" / "current_role_card.json"
USER_PROFILE_PATH = PROJECT_ROOT / "data" / "user_profile.json"
STATIC_DIR = RESOURCE_DIR / "static"
TEMPLATES_DIR = RESOURCE_DIR / "templates"
PROMPT_PATH = RESOURCE_DIR / "prompts" / "mobile_chat_prompt.txt"

DEFAULT_STICKER_IDS = ("happy", "sweat", "stare", "shy", "heart", "cry")
STICKER_IDS = set(DEFAULT_STICKER_IDS)
CUSTOM_STICKER_PACKS = {
    "katishiya": {
        "label": "卡提希娅",
        "directory": PROJECT_ROOT / "卡提希娅",
    }
}
MAX_CUSTOM_STICKERS_PER_PACK = 160
MESSAGE_TYPES = {"text", "sticker", "system", "error"}
MESSAGE_SOURCES = {"user", "ai", "system"}
GROUP_ID_RE = re.compile(r"^group_[a-z0-9_-]{6,80}$")
SAFE_ID_RE = re.compile(r"[^a-z0-9_-]+")
STORAGE_LOCK = RLock()
GROUP_ASYNC_LOCKS: dict[str, asyncio.Lock] = {}

DEFAULT_UI_SETTINGS = {
    "show_floating_button": True,
    "remember_position": True,
    "floating_position": {"right": 28, "bottom": 150},
    "panel_position": {"right": 28, "bottom": 92},
}
DEFAULT_GENERATION_SETTINGS = {
    "model_source": "main",
    "reply_count": "1-2",
    "max_tokens": 500,
    "recent_message_limit": 30,
    "allow_role_to_role_reply": True,
}
DEFAULT_AUTO_BEHAVIOR_SETTINGS = {
    "enabled": False,
    "idle_seconds": 90,
    "interval_seconds": 120,
    "max_rounds_per_session": 3,
    "max_generations_per_hour": 6,
    "active_group_only": True,
}
DEFAULT_STICKERS_SETTINGS = {
    "default_pack": "default",
    "inject_catalog": True,
}
DEFAULT_ROLES_SETTINGS = {
    "profile_overrides_enabled": True,
}
DEFAULT_GROUPS_SETTINGS = {
    "inherit_global_defaults": True,
}
DEFAULT_PROMPT_SETTINGS = {
    "preset": "default",
    "editable_blocks": True,
    "use_block_prompt": False,
    "last_preview_channel": "group_chat",
}
DEFAULT_SETTINGS = {
    "schema_version": 2,
    "enabled": True,
    "show_floating_button": DEFAULT_UI_SETTINGS["show_floating_button"],
    "remember_position": DEFAULT_UI_SETTINGS["remember_position"],
    "floating_position": DEFAULT_UI_SETTINGS["floating_position"],
    "panel_position": DEFAULT_UI_SETTINGS["panel_position"],
    "model_source": DEFAULT_GENERATION_SETTINGS["model_source"],
    "reply_count": DEFAULT_GENERATION_SETTINGS["reply_count"],
    "max_tokens": DEFAULT_GENERATION_SETTINGS["max_tokens"],
    "recent_message_limit": DEFAULT_GENERATION_SETTINGS["recent_message_limit"],
    "allow_role_to_role_reply": DEFAULT_GENERATION_SETTINGS["allow_role_to_role_reply"],
    "allow_auto_interject": DEFAULT_AUTO_BEHAVIOR_SETTINGS["enabled"],
    "sticker_pack": DEFAULT_STICKERS_SETTINGS["default_pack"],
    "ui": DEFAULT_UI_SETTINGS,
    "generation": DEFAULT_GENERATION_SETTINGS,
    "auto_behavior": DEFAULT_AUTO_BEHAVIOR_SETTINGS,
    "stickers": DEFAULT_STICKERS_SETTINGS,
    "roles": DEFAULT_ROLES_SETTINGS,
    "groups": DEFAULT_GROUPS_SETTINGS,
    "prompt": DEFAULT_PROMPT_SETTINGS,
}
DEFAULT_ROLE_PROFILES = {
    "schema_version": 1,
    "roles": [],
}
DEFAULT_AUTOMATION_STATE = {
    "schema_version": 1,
    "paused": False,
    "paused_at": "",
    "last_test_at": "",
    "last_test_group_id": "",
}
DEFAULT_PROMPT_BLOCKS = {
    "schema_version": 1,
    "updated_at": "",
    "blocks": [
        {
            "block_id": "base_contract",
            "label": "Base Contract",
            "order": 10,
            "enabled": True,
            "locked": False,
            "scope": ["group_chat", "feed", "forum", "notification", "mail", "diary", "calendar", "phone"],
            "content": (
                "You are running Fantareal Mobile Chat, an isolated in-world phone plugin. "
                "Use the provided character, world and recent plugin-only context. "
                "Do not write to, rewrite, or assume changes to the main chat transcript."
            ),
        },
        {
            "block_id": "role_context",
            "label": "Role Context",
            "order": 20,
            "enabled": True,
            "locked": False,
            "scope": ["group_chat", "feed", "forum", "notification", "mail", "diary", "calendar", "phone"],
            "content": (
                "Characters should act according to their profile summaries, chat styles, aliases, status, "
                "the current channel, and the recent plugin-only events."
            ),
        },
        {
            "block_id": "channel_behavior",
            "label": "Channel Behavior",
            "order": 30,
            "enabled": True,
            "locked": False,
            "scope": ["feed", "forum", "notification", "mail", "diary", "calendar", "phone"],
            "content": (
                "For app channels, generate compact believable content around the current characters, "
                "world context and ongoing situation. Keep it suitable for a phone app UI."
            ),
        },
        {
            "block_id": "sticker_contract",
            "label": "Sticker Contract",
            "order": 40,
            "enabled": True,
            "locked": False,
            "scope": ["group_chat"],
            "content": (
                "When sending stickers, use only sticker ids from available_stickers. "
                "Choose stickers by label, tags and character mood."
            ),
        },
        {
            "block_id": "json_output",
            "label": "JSON Output",
            "order": 90,
            "enabled": True,
            "locked": True,
            "scope": ["group_chat", "feed", "forum", "notification", "mail", "diary", "calendar", "phone"],
            "content": "Return valid JSON only. Do not include markdown fences or explanations.",
        },
    ],
}
DEFAULT_APP_REGISTRY = {
    "schema_version": 1,
    "apps": [
        {"app_id": "group_chat", "label": "口袋群聊", "subtitle": "角色卡群聊", "icon": "message", "page": "groups", "order": 10, "enabled": True, "stage": "v1.3"},
        {"app_id": "settings", "label": "详细设置", "subtitle": "偏好与模型", "icon": "settings", "page": "settings", "order": 20, "enabled": True, "stage": "v1.3"},
        {"app_id": "stickers", "label": "贴纸包", "subtitle": "内置资源", "icon": "smile", "page": "stickers", "order": 30, "enabled": True, "stage": "v1.3"},
        {"app_id": "feed", "label": "动态", "subtitle": "角色近况", "icon": "spark", "page": "channel-feed_main", "order": 40, "enabled": True, "stage": "v1.7"},
        {"app_id": "forum", "label": "论坛", "subtitle": "世界讨论板", "icon": "forum", "page": "channel-forum_main", "order": 50, "enabled": True, "stage": "v1.7"},
        {"app_id": "notifications", "label": "通知", "subtitle": "系统与角色提醒", "icon": "bell", "page": "notifications", "order": 60, "enabled": True, "stage": "v1.7"},
        {"app_id": "phone", "label": "电话", "subtitle": "模拟通话 RP", "icon": "phone", "page": "phone", "order": 70, "enabled": True, "stage": "v1.8"},
        {"app_id": "mail", "label": "邮箱", "subtitle": "角色邮件", "icon": "mail", "page": "channel-mail_inbox", "order": 80, "enabled": True, "stage": "v1.8"},
        {"app_id": "diary", "label": "日记", "subtitle": "角色碎片记录", "icon": "diary", "page": "channel-diary_main", "order": 90, "enabled": True, "stage": "v1.8"},
        {"app_id": "calendar", "label": "日程", "subtitle": "事件安排", "icon": "calendar", "page": "channel-calendar_main", "order": 100, "enabled": True, "stage": "v1.8"},
    ],
}
DEFAULT_CHANNELS = {
    "schema_version": 1,
    "channels": [
        {"channel_id": "feed_main", "type": "feed", "label": "动态", "description": "角色围绕当前世界观发布的近况。", "seed_count": 5, "enabled": True},
        {"channel_id": "forum_main", "type": "forum", "label": "论坛", "description": "角色和世界内路人讨论事件的帖子。", "seed_count": 5, "enabled": True},
        {"channel_id": "mail_inbox", "type": "mail", "label": "邮箱", "description": "角色发来的邮件和系统邮件。", "seed_count": 4, "enabled": True},
        {"channel_id": "diary_main", "type": "diary", "label": "日记", "description": "角色或用户视角的碎片记录。", "seed_count": 4, "enabled": True},
        {"channel_id": "calendar_main", "type": "calendar", "label": "日程", "description": "接下来可能发生的事件安排。", "seed_count": 4, "enabled": True},
    ],
}
DEFAULT_NOTIFICATIONS = {
    "schema_version": 1,
    "items": [],
}
DEFAULT_PHONE_CALLS = {
    "schema_version": 1,
    "sessions": [],
}
DEFAULT_GENERATION_STATE = {
    "schema_version": 1,
    "active_jobs": {},
    "last_jobs": [],
}
CHANNEL_TYPES = {"group_chat", "feed", "forum", "notification", "mail", "diary", "calendar", "phone"}
CHANNEL_EVENT_TYPES = {"post", "thread", "reply", "notice", "mail", "diary", "calendar", "call_line", "system"}


class SettingsPayload(BaseModel):
    schema_version: int | None = None
    enabled: bool | None = None
    show_floating_button: bool | None = None
    remember_position: bool | None = None
    floating_position: dict[str, Any] | None = None
    panel_position: dict[str, Any] | None = None
    model_source: str | None = None
    reply_count: str | None = None
    max_tokens: int | None = None
    recent_message_limit: int | None = None
    allow_role_to_role_reply: bool | None = None
    allow_auto_interject: bool | None = None
    sticker_pack: str | None = None
    ui: dict[str, Any] | None = None
    generation: dict[str, Any] | None = None
    auto_behavior: dict[str, Any] | None = None
    stickers: dict[str, Any] | None = None
    roles: dict[str, Any] | None = None
    groups: dict[str, Any] | None = None
    prompt: dict[str, Any] | None = None


class GroupCreatePayload(BaseModel):
    name: str = Field(default="", max_length=80)
    description: str = Field(default="", max_length=500)
    members: list[dict[str, Any]] = Field(default_factory=list)
    allow_role_to_role_reply: bool | None = None
    allow_auto_interject: bool | None = None
    reply_count: str | None = None
    sticker_pack: str | None = None


class GroupPatchPayload(BaseModel):
    name: str | None = Field(default=None, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    members: list[dict[str, Any]] | None = None
    allow_role_to_role_reply: bool | None = None
    allow_auto_interject: bool | None = None
    reply_count: str | None = None
    sticker_pack: str | None = None


class MessageCreatePayload(BaseModel):
    content: str = Field(default="", max_length=500)
    type: str = "text"


class GeneratePayload(BaseModel):
    group_id: str
    user_message: str = Field(default="", max_length=500)


class ContinuePayload(BaseModel):
    group_id: str


class RoleProfilePayload(BaseModel):
    role_id: str | None = Field(default=None, max_length=120)
    display_name: str = Field(default="", max_length=80)
    source: str | None = Field(default=None, max_length=40)
    source_ref: str | None = Field(default=None, max_length=240)
    aliases: list[Any] | None = None
    avatar: str | None = Field(default=None, max_length=500)
    summary: str | None = Field(default=None, max_length=500)
    status: str | None = Field(default=None, max_length=80)
    chat_style: str | None = Field(default=None, max_length=500)
    sticker_preferences: dict[str, Any] | None = None
    auto_speak_weight: float | None = None
    enabled: bool | None = None


class RoleProfilePatchPayload(BaseModel):
    display_name: str | None = Field(default=None, max_length=80)
    source: str | None = Field(default=None, max_length=40)
    source_ref: str | None = Field(default=None, max_length=240)
    aliases: list[Any] | None = None
    avatar: str | None = Field(default=None, max_length=500)
    summary: str | None = Field(default=None, max_length=500)
    status: str | None = Field(default=None, max_length=80)
    chat_style: str | None = Field(default=None, max_length=500)
    sticker_preferences: dict[str, Any] | None = None
    auto_speak_weight: float | None = None
    enabled: bool | None = None


class StickerManifestPayload(BaseModel):
    stickers: Any = Field(default_factory=list)


class AutomationPayload(BaseModel):
    enabled: bool | None = None
    idle_seconds: int | None = None
    interval_seconds: int | None = None
    max_rounds_per_session: int | None = None
    max_generations_per_hour: int | None = None
    active_group_only: bool | None = None


class AutomationTestPayload(BaseModel):
    group_id: str


class PromptBlocksPayload(BaseModel):
    blocks: Any = Field(default_factory=list)


class AppRegistryPayload(BaseModel):
    apps: Any = Field(default_factory=list)


class ChannelEventPayload(BaseModel):
    title: str | None = Field(default=None, max_length=120)
    content: str = Field(default="", max_length=2000)
    event_type: str | None = Field(default=None, max_length=40)
    author_id: str | None = Field(default=None, max_length=120)
    author_name: str | None = Field(default=None, max_length=80)
    tags: list[Any] | None = None
    metadata: dict[str, Any] | None = None


class ChannelSeedPayload(BaseModel):
    channel_id: str = ""
    count: int | None = None
    force: bool | None = None


class NotificationPatchPayload(BaseModel):
    read: bool | None = None


class PhoneCallPayload(BaseModel):
    role_id: str
    user_line: str | None = Field(default="", max_length=500)
    session_id: str | None = Field(default=None, max_length=120)


app = FastAPI(title="Fantareal Mobile Chat Mod")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def clone_default(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False))


def compact_text(value: Any, limit: int = 500) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def clamp_int(value: Any, minimum: int, maximum: int, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


def clamp_float(value: Any, minimum: float, maximum: float, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


def is_safe_png_filename(filename: Any) -> bool:
    name = str(filename or "").strip()
    if not name or len(name) > 160 or name.startswith("."):
        return False
    if Path(name).name != name:
        return False
    return name.lower().endswith(".png")


def custom_sticker_path(pack_id: str, filename: str, require_exists: bool = True) -> Path | None:
    pack = CUSTOM_STICKER_PACKS.get(compact_text(pack_id, 80))
    if not pack or not is_safe_png_filename(filename):
        return None
    directory = pack["directory"]
    path = directory / filename
    try:
        resolved_dir = directory.resolve(strict=False)
        resolved_path = path.resolve(strict=False)
    except OSError:
        return None
    if resolved_dir != resolved_path.parent:
        return None
    if require_exists and (not resolved_path.is_file() or resolved_path.suffix.lower() != ".png"):
        return None
    return resolved_path


def custom_sticker_sort_key(path: Path) -> tuple[int, int | str]:
    stem = path.stem
    return (0, int(stem)) if stem.isdigit() else (1, path.name.casefold())


def custom_sticker_files(pack_id: str) -> list[Path]:
    pack = CUSTOM_STICKER_PACKS.get(pack_id)
    if not pack:
        return []
    directory = pack["directory"]
    if not directory.is_dir():
        return []
    files = [
        path
        for path in directory.iterdir()
        if path.is_file() and is_safe_png_filename(path.name)
    ]
    return sorted(files, key=custom_sticker_sort_key)[:MAX_CUSTOM_STICKERS_PER_PACK]


def sticker_tags(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    tags: list[str] = []
    seen: set[str] = set()
    for item in value:
        tag = normalize_id(item)
        if not tag or tag in seen:
            continue
        seen.add(tag)
        tags.append(tag)
        if len(tags) >= 12:
            break
    return tags


def custom_sticker_manifest(pack_id: str) -> dict[str, dict[str, Any]]:
    pack = CUSTOM_STICKER_PACKS.get(pack_id)
    if not pack:
        return {}
    manifest_path = pack["directory"] / "manifest.json"
    payload = read_json(manifest_path, {})
    if not isinstance(payload, dict):
        return {}
    raw_rows = payload.get("stickers", payload)
    rows: dict[str, Any] = {}
    if isinstance(raw_rows, dict):
        rows = raw_rows
    elif isinstance(raw_rows, list):
        rows = {
            item.get("file", item.get("filename", "")): item
            for item in raw_rows
            if isinstance(item, dict)
        }
    result: dict[str, dict[str, Any]] = {}
    for filename, meta in rows.items():
        if not is_safe_png_filename(filename) or not isinstance(meta, dict):
            continue
        result[str(filename)] = {
            "label": compact_text(meta.get("label") or Path(str(filename)).stem, 80),
            "tags": sticker_tags(meta.get("tags")),
            "description": compact_text(meta.get("description") or meta.get("prompt"), 120),
        }
    return result


def is_valid_sticker_id(sticker_id: Any, require_exists: bool = False) -> bool:
    value = compact_text(sticker_id, 220)
    if value in STICKER_IDS:
        return True
    if ":" not in value:
        return False
    pack_id, filename = value.split(":", 1)
    return custom_sticker_path(pack_id, filename, require_exists=require_exists) is not None


def sticker_catalog() -> list[dict[str, Any]]:
    stickers: list[dict[str, Any]] = [
        {
            "id": sticker_id,
            "type": "builtin",
            "pack_id": "default",
            "pack_label": "默认",
            "label": sticker_id,
            "tags": [sticker_id],
            "description": "",
        }
        for sticker_id in DEFAULT_STICKER_IDS
    ]
    for pack_id, pack in CUSTOM_STICKER_PACKS.items():
        manifest = custom_sticker_manifest(pack_id)
        for path in custom_sticker_files(pack_id):
            meta = manifest.get(path.name, {})
            stickers.append(
                {
                    "id": f"{pack_id}:{path.name}",
                    "type": "image",
                    "pack_id": pack_id,
                    "pack_label": pack["label"],
                    "label": compact_text(meta.get("label"), 80) or path.stem,
                    "tags": meta.get("tags", []),
                    "description": compact_text(meta.get("description"), 120),
                    "filename": path.name,
                    "url_path": f"/stickers/{pack_id}/{quote(path.name)}",
                }
            )
    return stickers


def sticker_pack_summaries() -> list[dict[str, Any]]:
    packs = [
        {
            "pack_id": "default",
            "label": "默认",
            "type": "builtin",
            "count": len(DEFAULT_STICKER_IDS),
            "manifest_editable": False,
            "directory": "",
        }
    ]
    for pack_id, pack in CUSTOM_STICKER_PACKS.items():
        files = custom_sticker_files(pack_id)
        manifest = custom_sticker_manifest(pack_id)
        packs.append(
            {
                "pack_id": pack_id,
                "label": pack["label"],
                "type": "image",
                "count": len(files),
                "manifest_count": len(manifest),
                "manifest_editable": True,
                "directory": str(pack["directory"]),
            }
        )
    return packs


def sticker_manifest_rows(pack_id: str) -> list[dict[str, Any]]:
    if pack_id not in CUSTOM_STICKER_PACKS:
        raise HTTPException(status_code=404, detail="表情包不存在。")
    manifest = custom_sticker_manifest(pack_id)
    rows: list[dict[str, Any]] = []
    for path in custom_sticker_files(pack_id):
        meta = manifest.get(path.name, {})
        rows.append(
            {
                "filename": path.name,
                "id": f"{pack_id}:{path.name}",
                "label": compact_text(meta.get("label"), 80) or path.stem,
                "tags": meta.get("tags", []),
                "description": compact_text(meta.get("description"), 120),
                "url_path": f"/stickers/{pack_id}/{quote(path.name)}",
            }
        )
    return rows


def sanitize_manifest_rows(value: Any) -> list[dict[str, Any]]:
    raw_rows = value
    if isinstance(value, dict):
        raw_rows = [
            {"filename": filename, **meta}
            for filename, meta in value.items()
            if isinstance(meta, dict)
        ]
    if not isinstance(raw_rows, list):
        raw_rows = []
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw_rows:
        if not isinstance(item, dict):
            continue
        filename = compact_text(item.get("filename") or item.get("file"), 160)
        if not is_safe_png_filename(filename) or filename in seen:
            continue
        seen.add(filename)
        rows.append(
            {
                "file": filename,
                "label": compact_text(item.get("label") or Path(filename).stem, 80),
                "tags": sticker_tags(item.get("tags")),
                "description": compact_text(item.get("description") or item.get("prompt"), 120),
            }
        )
    return rows


def save_sticker_manifest(pack_id: str, rows: list[dict[str, Any]]) -> None:
    pack = CUSTOM_STICKER_PACKS.get(pack_id)
    if not pack:
        raise HTTPException(status_code=404, detail="表情包不存在。")
    existing_files = {path.name for path in custom_sticker_files(pack_id)}
    sanitized = [row for row in sanitize_manifest_rows(rows) if row["file"] in existing_files]
    payload = {
        "schema_version": 1,
        "updated_at": now_iso(),
        "stickers": sanitized,
    }
    write_json(pack["directory"] / "manifest.json", payload)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def normalize_id(value: Any, fallback: str = "") -> str:
    raw = compact_text(value, 120).lower().replace(" ", "_")
    normalized = SAFE_ID_RE.sub("_", raw).strip("_")
    return normalized[:80] or fallback


def make_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def _read_json_unlocked(path: Path, default: Any) -> Any:
    if not path.exists():
        return clone_default(default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return clone_default(default)


def read_json(path: Path, default: Any) -> Any:
    with STORAGE_LOCK:
        return _read_json_unlocked(path, default)


def _write_json_unlocked(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise HTTPException(status_code=500, detail="小手机数据写入失败，请检查磁盘空间或目录权限。") from exc


def write_json(path: Path, payload: Any) -> None:
    with STORAGE_LOCK:
        _write_json_unlocked(path, payload)


def ensure_runtime_data() -> None:
    with STORAGE_LOCK:
        MESSAGES_DIR.mkdir(parents=True, exist_ok=True)
        EVENTS_DIR.mkdir(parents=True, exist_ok=True)
        if not SETTINGS_PATH.exists():
            _write_json_unlocked(SETTINGS_PATH, DEFAULT_SETTINGS)
        if not GROUPS_PATH.exists():
            _write_json_unlocked(GROUPS_PATH, [])
        if not ROLE_PROFILES_PATH.exists():
            _write_json_unlocked(ROLE_PROFILES_PATH, DEFAULT_ROLE_PROFILES)
        if not AUTOMATION_STATE_PATH.exists():
            _write_json_unlocked(AUTOMATION_STATE_PATH, DEFAULT_AUTOMATION_STATE)
        if not PROMPT_BLOCKS_PATH.exists():
            _write_json_unlocked(PROMPT_BLOCKS_PATH, DEFAULT_PROMPT_BLOCKS)
        if not APP_REGISTRY_PATH.exists():
            _write_json_unlocked(APP_REGISTRY_PATH, DEFAULT_APP_REGISTRY)
        if not CHANNELS_PATH.exists():
            _write_json_unlocked(CHANNELS_PATH, DEFAULT_CHANNELS)
        if not NOTIFICATIONS_PATH.exists():
            _write_json_unlocked(NOTIFICATIONS_PATH, DEFAULT_NOTIFICATIONS)
        if not PHONE_CALLS_PATH.exists():
            _write_json_unlocked(PHONE_CALLS_PATH, DEFAULT_PHONE_CALLS)
        if not GENERATION_STATE_PATH.exists():
            _write_json_unlocked(GENERATION_STATE_PATH, DEFAULT_GENERATION_STATE)


def sanitize_position(raw: Any, default: dict[str, int]) -> dict[str, int]:
    source = raw if isinstance(raw, dict) else {}
    return {
        "right": clamp_int(source.get("right"), 0, 10000, default["right"]),
        "bottom": clamp_int(source.get("bottom"), 0, 10000, default["bottom"]),
    }


def section_source(raw: dict[str, Any], key: str) -> dict[str, Any]:
    value = raw.get(key)
    return value if isinstance(value, dict) else {}


def pick_section_value(source: dict[str, Any], section: dict[str, Any], key: str, default: Any) -> Any:
    if key in source:
        return source.get(key)
    if key in section:
        return section.get(key)
    return default


def sanitize_auto_behavior(raw: Any, legacy_enabled: bool) -> dict[str, Any]:
    source = raw if isinstance(raw, dict) else {}
    return {
        "enabled": bool(source.get("enabled", legacy_enabled)),
        "idle_seconds": clamp_int(source.get("idle_seconds"), 15, 3600, DEFAULT_AUTO_BEHAVIOR_SETTINGS["idle_seconds"]),
        "interval_seconds": clamp_int(source.get("interval_seconds"), 15, 3600, DEFAULT_AUTO_BEHAVIOR_SETTINGS["interval_seconds"]),
        "max_rounds_per_session": clamp_int(source.get("max_rounds_per_session"), 1, 20, DEFAULT_AUTO_BEHAVIOR_SETTINGS["max_rounds_per_session"]),
        "max_generations_per_hour": clamp_int(source.get("max_generations_per_hour"), 1, 60, DEFAULT_AUTO_BEHAVIOR_SETTINGS["max_generations_per_hour"]),
        "active_group_only": bool(source.get("active_group_only", DEFAULT_AUTO_BEHAVIOR_SETTINGS["active_group_only"])),
    }


def sanitize_settings(raw: Any) -> dict[str, Any]:
    source = raw if isinstance(raw, dict) else {}
    settings = clone_default(DEFAULT_SETTINGS)
    ui_source = section_source(source, "ui")
    generation_source = section_source(source, "generation")
    auto_source = section_source(source, "auto_behavior")
    stickers_source = section_source(source, "stickers")
    roles_source = section_source(source, "roles")
    groups_source = section_source(source, "groups")
    prompt_source = section_source(source, "prompt")

    settings["schema_version"] = 2
    settings["enabled"] = bool(source.get("enabled", DEFAULT_SETTINGS["enabled"]))
    settings["show_floating_button"] = bool(pick_section_value(source, ui_source, "show_floating_button", DEFAULT_UI_SETTINGS["show_floating_button"]))
    settings["remember_position"] = bool(pick_section_value(source, ui_source, "remember_position", DEFAULT_UI_SETTINGS["remember_position"]))
    settings["floating_position"] = sanitize_position(
        pick_section_value(source, ui_source, "floating_position", DEFAULT_UI_SETTINGS["floating_position"]),
        DEFAULT_UI_SETTINGS["floating_position"],
    )
    settings["panel_position"] = sanitize_position(
        pick_section_value(source, ui_source, "panel_position", DEFAULT_UI_SETTINGS["panel_position"]),
        DEFAULT_UI_SETTINGS["panel_position"],
    )
    settings["model_source"] = "main"
    raw_reply_count = pick_section_value(source, generation_source, "reply_count", DEFAULT_GENERATION_SETTINGS["reply_count"])
    settings["reply_count"] = "1-2" if str(raw_reply_count).strip() != "1" else "1"
    settings["max_tokens"] = clamp_int(
        pick_section_value(source, generation_source, "max_tokens", DEFAULT_GENERATION_SETTINGS["max_tokens"]),
        64,
        1200,
        DEFAULT_GENERATION_SETTINGS["max_tokens"],
    )
    settings["recent_message_limit"] = clamp_int(
        pick_section_value(source, generation_source, "recent_message_limit", DEFAULT_GENERATION_SETTINGS["recent_message_limit"]),
        1,
        80,
        DEFAULT_GENERATION_SETTINGS["recent_message_limit"],
    )
    settings["allow_role_to_role_reply"] = bool(
        pick_section_value(source, generation_source, "allow_role_to_role_reply", DEFAULT_GENERATION_SETTINGS["allow_role_to_role_reply"])
    )
    legacy_auto_enabled = bool(source.get("allow_auto_interject", auto_source.get("enabled", DEFAULT_AUTO_BEHAVIOR_SETTINGS["enabled"])))
    auto_behavior = sanitize_auto_behavior(auto_source, legacy_auto_enabled)
    settings["allow_auto_interject"] = auto_behavior["enabled"]
    settings["sticker_pack"] = "default"
    settings["ui"] = {
        "show_floating_button": settings["show_floating_button"],
        "remember_position": settings["remember_position"],
        "floating_position": settings["floating_position"],
        "panel_position": settings["panel_position"],
    }
    settings["generation"] = {
        "model_source": settings["model_source"],
        "reply_count": settings["reply_count"],
        "max_tokens": settings["max_tokens"],
        "recent_message_limit": settings["recent_message_limit"],
        "allow_role_to_role_reply": settings["allow_role_to_role_reply"],
    }
    settings["auto_behavior"] = auto_behavior
    settings["stickers"] = {
        "default_pack": "default",
        "inject_catalog": bool(stickers_source.get("inject_catalog", DEFAULT_STICKERS_SETTINGS["inject_catalog"])),
    }
    settings["roles"] = {
        "profile_overrides_enabled": bool(roles_source.get("profile_overrides_enabled", DEFAULT_ROLES_SETTINGS["profile_overrides_enabled"])),
    }
    settings["groups"] = {
        "inherit_global_defaults": bool(groups_source.get("inherit_global_defaults", DEFAULT_GROUPS_SETTINGS["inherit_global_defaults"])),
    }
    settings["prompt"] = {
        "preset": "default",
        "editable_blocks": bool(prompt_source.get("editable_blocks", DEFAULT_PROMPT_SETTINGS["editable_blocks"])),
        "use_block_prompt": bool(prompt_source.get("use_block_prompt", DEFAULT_PROMPT_SETTINGS["use_block_prompt"])),
        "last_preview_channel": compact_text(prompt_source.get("last_preview_channel", DEFAULT_PROMPT_SETTINGS["last_preview_channel"]), 40)
        or DEFAULT_PROMPT_SETTINGS["last_preview_channel"],
    }
    return settings


def get_settings() -> dict[str, Any]:
    ensure_runtime_data()
    settings = sanitize_settings(read_json(SETTINGS_PATH, DEFAULT_SETTINGS))
    if settings != read_json(SETTINGS_PATH, DEFAULT_SETTINGS):
        write_json(SETTINGS_PATH, settings)
    return settings


def sanitize_automation_state(raw: Any) -> dict[str, Any]:
    source = raw if isinstance(raw, dict) else {}
    return {
        "schema_version": 1,
        "paused": bool(source.get("paused", DEFAULT_AUTOMATION_STATE["paused"])),
        "paused_at": compact_text(source.get("paused_at"), 80),
        "last_test_at": compact_text(source.get("last_test_at"), 80),
        "last_test_group_id": compact_text(source.get("last_test_group_id"), 100),
    }


def get_automation_state() -> dict[str, Any]:
    ensure_runtime_data()
    state = sanitize_automation_state(read_json(AUTOMATION_STATE_PATH, DEFAULT_AUTOMATION_STATE))
    if state != read_json(AUTOMATION_STATE_PATH, DEFAULT_AUTOMATION_STATE):
        write_json(AUTOMATION_STATE_PATH, state)
    return state


def save_automation_state(state: dict[str, Any]) -> dict[str, Any]:
    sanitized = sanitize_automation_state(state)
    write_json(AUTOMATION_STATE_PATH, sanitized)
    return sanitized


def update_auto_behavior(updates: dict[str, Any]) -> dict[str, Any]:
    current = get_settings()
    merged_auto = sanitize_auto_behavior({**current["auto_behavior"], **updates}, bool(current["allow_auto_interject"]))
    merged = merge_settings_update(current, {"auto_behavior": merged_auto, "allow_auto_interject": merged_auto["enabled"]})
    settings = sanitize_settings(merged)
    write_json(SETTINGS_PATH, settings)
    if merged_auto["enabled"]:
        save_automation_state({**get_automation_state(), "paused": False, "paused_at": ""})
    return settings


def sanitize_prompt_block(raw: Any, index: int = 0) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    block_id = normalize_id(raw.get("block_id") or raw.get("id"), f"block_{index + 1}")
    content = compact_text(raw.get("content"), 4000)
    if not block_id or not content:
        return None
    raw_scope = raw.get("scope")
    scope = [compact_text(item, 40) for item in raw_scope] if isinstance(raw_scope, list) else ["group_chat"]
    scope = [item for item in scope if item in CHANNEL_TYPES]
    return {
        "block_id": block_id,
        "label": compact_text(raw.get("label"), 80) or block_id,
        "order": clamp_int(raw.get("order"), 0, 10000, (index + 1) * 10),
        "enabled": bool(raw.get("enabled", True)),
        "locked": bool(raw.get("locked", False)),
        "scope": scope or ["group_chat"],
        "content": content,
    }


def sanitize_prompt_blocks(raw: Any) -> dict[str, Any]:
    source = raw if isinstance(raw, dict) else {}
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(source.get("blocks") if isinstance(source.get("blocks"), list) else DEFAULT_PROMPT_BLOCKS["blocks"]):
        block = sanitize_prompt_block(item, index)
        if block:
            rows.append(block)
    if not any(item["block_id"] == "json_output" for item in rows):
        rows.append(clone_default(DEFAULT_PROMPT_BLOCKS["blocks"][-1]))
    rows.sort(key=lambda item: (item["order"], item["block_id"]))
    return {
        "schema_version": 1,
        "updated_at": compact_text(source.get("updated_at"), 80),
        "blocks": rows,
    }


def get_prompt_blocks() -> dict[str, Any]:
    ensure_runtime_data()
    payload = sanitize_prompt_blocks(read_json(PROMPT_BLOCKS_PATH, DEFAULT_PROMPT_BLOCKS))
    if payload != read_json(PROMPT_BLOCKS_PATH, DEFAULT_PROMPT_BLOCKS):
        write_json(PROMPT_BLOCKS_PATH, payload)
    return payload


def save_prompt_blocks(blocks: Any) -> dict[str, Any]:
    payload = sanitize_prompt_blocks({"updated_at": now_iso(), "blocks": blocks})
    write_json(PROMPT_BLOCKS_PATH, payload)
    return payload


def prompt_blocks_for_scope(scope: str) -> list[dict[str, Any]]:
    target = compact_text(scope, 40) or "group_chat"
    return [
        item
        for item in get_prompt_blocks()["blocks"]
        if item.get("enabled") and (target in item.get("scope", []) or "*" in item.get("scope", []))
    ]


def assembled_prompt_text(scope: str) -> str:
    blocks = prompt_blocks_for_scope(scope)
    return "\n\n".join(item["content"] for item in blocks).strip()


def channel_schema_catalog() -> list[dict[str, Any]]:
    return [
        {
            "type": "group_chat",
            "root": "messages",
            "required_fields": ["speaker", "type", "content"],
            "event_types": ["text", "sticker"],
            "notes": "Used by pocket group chat. This remains plugin-only and does not write to the main chat.",
        },
        {
            "type": "feed",
            "root": "events",
            "required_fields": ["event_type", "title", "content", "author_name"],
            "event_types": ["post"],
            "notes": "Short social feed posts around characters and world context.",
        },
        {
            "type": "forum",
            "root": "events",
            "required_fields": ["event_type", "title", "content", "author_name"],
            "event_types": ["thread", "reply"],
            "notes": "Forum thread cards and compact replies.",
        },
        {
            "type": "notification",
            "root": "notifications",
            "required_fields": ["title", "content", "source"],
            "event_types": ["notice"],
            "notes": "Aggregated phone notifications.",
        },
        {
            "type": "mail",
            "root": "events",
            "required_fields": ["event_type", "title", "content", "author_name"],
            "event_types": ["mail"],
            "notes": "In-world mail messages.",
        },
        {
            "type": "diary",
            "root": "events",
            "required_fields": ["event_type", "title", "content", "author_name"],
            "event_types": ["diary"],
            "notes": "Diary or fragment records.",
        },
        {
            "type": "calendar",
            "root": "events",
            "required_fields": ["event_type", "title", "content", "author_name"],
            "event_types": ["calendar"],
            "notes": "Upcoming phone calendar entries.",
        },
        {
            "type": "phone",
            "root": "lines",
            "required_fields": ["speaker", "content"],
            "event_types": ["call_line"],
            "notes": "Simulated call RP. Lines are stored inside mobile_chat phone sessions only.",
        },
    ]


def prompt_preview_payload(scope: str = "group_chat", group_id: str = "") -> dict[str, Any]:
    target_scope = compact_text(scope, 40) or "group_chat"
    if target_scope not in CHANNEL_TYPES:
        target_scope = "group_chat"
    group: dict[str, Any] | None = None
    if group_id:
        try:
            group = get_group_or_404(group_id)
        except HTTPException:
            group = None
    blocks = prompt_blocks_for_scope(target_scope)
    context: dict[str, Any] = {
        "scope": target_scope,
        "settings": get_settings().get("prompt", {}),
        "block_count": len(blocks),
        "role_count": len(get_role_profiles(include_disabled=False)),
        "sticker_count": len(sticker_catalog()),
    }
    if group:
        context["group"] = {
            "group_id": group["group_id"],
            "name": group["name"],
            "members": group["members"],
            "recent_messages": get_messages(group["group_id"])[-5:],
        }
    return {
        "ok": True,
        "scope": target_scope,
        "blocks": blocks,
        "assembled_prompt": assembled_prompt_text(target_scope),
        "context_preview": context,
        "schemas": [item for item in channel_schema_catalog() if item["type"] == target_scope],
    }


def sanitize_generation_state(raw: Any) -> dict[str, Any]:
    source = raw if isinstance(raw, dict) else {}
    active = source.get("active_jobs") if isinstance(source.get("active_jobs"), dict) else {}
    last = source.get("last_jobs") if isinstance(source.get("last_jobs"), list) else []
    sanitized_active: dict[str, dict[str, str]] = {}
    for key, value in active.items():
        if not isinstance(value, dict):
            continue
        safe_key = compact_text(key, 180)
        if not safe_key:
            continue
        sanitized_active[safe_key] = {
            "job_id": compact_text(value.get("job_id"), 120),
            "kind": compact_text(value.get("kind"), 80),
            "target_id": compact_text(value.get("target_id"), 120),
            "started_at": compact_text(value.get("started_at"), 80),
        }
    sanitized_last: list[dict[str, str]] = []
    for item in last[:30]:
        if not isinstance(item, dict):
            continue
        sanitized_last.append(
            {
                "job_id": compact_text(item.get("job_id"), 120),
                "kind": compact_text(item.get("kind"), 80),
                "target_id": compact_text(item.get("target_id"), 120),
                "started_at": compact_text(item.get("started_at"), 80),
                "finished_at": compact_text(item.get("finished_at"), 80),
                "status": compact_text(item.get("status"), 40),
                "error": compact_text(item.get("error"), 240),
            }
        )
    return {"schema_version": 1, "active_jobs": sanitized_active, "last_jobs": sanitized_last}


def get_generation_state() -> dict[str, Any]:
    ensure_runtime_data()
    payload = sanitize_generation_state(read_json(GENERATION_STATE_PATH, DEFAULT_GENERATION_STATE))
    if payload != read_json(GENERATION_STATE_PATH, DEFAULT_GENERATION_STATE):
        write_json(GENERATION_STATE_PATH, payload)
    return payload


def save_generation_state(state: dict[str, Any]) -> dict[str, Any]:
    payload = sanitize_generation_state(state)
    write_json(GENERATION_STATE_PATH, payload)
    return payload


def begin_generation_job(kind: str, target_id: str) -> dict[str, str]:
    safe_kind = compact_text(kind, 80) or "unknown"
    safe_target = compact_text(target_id, 120) or "default"
    key = f"{safe_kind}:{safe_target}"
    state = get_generation_state()
    if key in state["active_jobs"]:
        raise HTTPException(status_code=409, detail="A generation task is already running for this target.")
    job = {
        "job_id": make_id("job"),
        "kind": safe_kind,
        "target_id": safe_target,
        "started_at": now_iso(),
    }
    state["active_jobs"][key] = job
    save_generation_state(state)
    return job


def finish_generation_job(job: dict[str, str], status: str, error: str = "") -> None:
    state = get_generation_state()
    active = state["active_jobs"]
    for key, value in list(active.items()):
        if value.get("job_id") == job.get("job_id"):
            active.pop(key, None)
    state["last_jobs"] = [
        {
            **job,
            "finished_at": now_iso(),
            "status": compact_text(status, 40) or "unknown",
            "error": compact_text(error, 240),
        },
        *state.get("last_jobs", []),
    ][:30]
    save_generation_state(state)


def merge_settings_update(current: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    merged = {**current, **updates}
    for key in ("ui", "generation", "auto_behavior", "stickers", "roles", "groups", "prompt"):
        if isinstance(current.get(key), dict) and isinstance(updates.get(key), dict):
            merged[key] = {**current[key], **updates[key]}
    ui = updates.get("ui") if isinstance(updates.get("ui"), dict) else {}
    generation = updates.get("generation") if isinstance(updates.get("generation"), dict) else {}
    auto_behavior = updates.get("auto_behavior") if isinstance(updates.get("auto_behavior"), dict) else {}
    if ui:
        for key in ("show_floating_button", "remember_position", "floating_position", "panel_position"):
            if key in ui and key not in updates:
                merged[key] = ui[key]
    if generation:
        for key in ("reply_count", "max_tokens", "recent_message_limit", "allow_role_to_role_reply"):
            if key in generation and key not in updates:
                merged[key] = generation[key]
    if "enabled" in auto_behavior and "allow_auto_interject" not in updates:
        merged["allow_auto_interject"] = auto_behavior["enabled"]
    if "allow_auto_interject" in updates and not auto_behavior and isinstance(merged.get("auto_behavior"), dict):
        merged["auto_behavior"] = {**merged["auto_behavior"], "enabled": updates["allow_auto_interject"]}
    return merged


def safe_avatar(value: Any) -> str:
    text = compact_text(value, 500)
    return text if text.startswith("/") else ""


def role_name_key(value: Any) -> str:
    return compact_text(value, 120).casefold()


def sanitize_member(raw: Any, index: int = 0) -> dict[str, str] | None:
    if not isinstance(raw, dict):
        return None
    member_type = "user" if str(raw.get("type", "")).strip().lower() == "user" else "character"
    name = compact_text(raw.get("name"), 80)
    if not name:
        return None
    fallback = "user" if member_type == "user" else f"role_{index + 1}"
    role_id = normalize_id(raw.get("role_id") or raw.get("id"), fallback)
    if member_type == "user":
        role_id = "user"
    return {
        "role_id": role_id,
        "name": name,
        "type": member_type,
        "summary": compact_text(raw.get("summary"), 360),
        "avatar": safe_avatar(raw.get("avatar")),
    }


def current_user_member() -> dict[str, str]:
    profile = read_json(USER_PROFILE_PATH, {})
    if not isinstance(profile, dict):
        profile = {}
    name = compact_text(profile.get("display_name") or profile.get("nickname"), 80) or "我"
    return {
        "role_id": "user",
        "name": name,
        "type": "user",
        "summary": "当前用户",
        "avatar": safe_avatar(profile.get("avatar_url")),
    }


def sanitize_aliases(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    aliases: list[str] = []
    seen: set[str] = set()
    for item in value:
        alias = compact_text(item, 40)
        key = role_name_key(alias)
        if not alias or key in seen:
            continue
        seen.add(key)
        aliases.append(alias)
        if len(aliases) >= 8:
            break
    return aliases


def sanitize_sticker_preferences(value: Any) -> dict[str, Any]:
    source = value if isinstance(value, dict) else {}
    default_pack = compact_text(source.get("default_pack"), 80) or DEFAULT_STICKERS_SETTINGS["default_pack"]
    if default_pack != "default" and default_pack not in CUSTOM_STICKER_PACKS:
        default_pack = DEFAULT_STICKERS_SETTINGS["default_pack"]
    return {
        "default_pack": default_pack,
        "preferred_tags": sticker_tags(source.get("preferred_tags")),
        "blocked_tags": sticker_tags(source.get("blocked_tags")),
    }


def sanitize_role_profile(raw: Any, index: int = 0) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    display_name = compact_text(raw.get("display_name") or raw.get("name"), 80)
    if not display_name:
        return None
    fallback_id = normalize_id(display_name, f"role_profile_{index + 1}")
    role_id = normalize_id(raw.get("role_id") or raw.get("id"), fallback_id)
    if role_id == "user":
        return None
    source = normalize_id(raw.get("source"), "manual")
    if source not in {"manual", "current_card", "group_import"}:
        source = "manual"
    auto_weight = clamp_float(raw.get("auto_speak_weight"), 0.0, 10.0, 1.0)
    return {
        "role_id": role_id,
        "display_name": display_name,
        "source": source,
        "source_ref": compact_text(raw.get("source_ref"), 240),
        "aliases": sanitize_aliases(raw.get("aliases")),
        "avatar": safe_avatar(raw.get("avatar")),
        "summary": compact_text(raw.get("summary"), 500),
        "status": compact_text(raw.get("status"), 80) or "online",
        "chat_style": compact_text(raw.get("chat_style"), 500),
        "sticker_preferences": sanitize_sticker_preferences(raw.get("sticker_preferences")),
        "auto_speak_weight": auto_weight,
        "enabled": raw.get("enabled") is not False,
        "created_at": compact_text(raw.get("created_at"), 80) or now_iso(),
        "updated_at": compact_text(raw.get("updated_at"), 80) or now_iso(),
    }


def get_role_profiles(*, include_disabled: bool = True) -> list[dict[str, Any]]:
    ensure_runtime_data()
    stored = read_json(ROLE_PROFILES_PATH, DEFAULT_ROLE_PROFILES)
    rows = stored.get("roles", []) if isinstance(stored, dict) else stored
    if not isinstance(rows, list):
        rows = []
    profiles = [profile for index, item in enumerate(rows) if (profile := sanitize_role_profile(item, index)) is not None]
    if not include_disabled:
        profiles = [profile for profile in profiles if profile["enabled"]]
    return sorted(profiles, key=lambda item: (not item["enabled"], item["display_name"].casefold(), item["role_id"]))


def save_role_profiles(profiles: list[dict[str, Any]]) -> None:
    sanitized = [profile for index, item in enumerate(profiles) if (profile := sanitize_role_profile(item, index)) is not None]
    write_json(ROLE_PROFILES_PATH, {"schema_version": 1, "roles": sanitized})


def role_profile_to_member(profile: dict[str, Any]) -> dict[str, str]:
    return {
        "role_id": profile["role_id"],
        "name": profile["display_name"],
        "type": "character",
        "summary": compact_text(profile.get("summary"), 360),
        "avatar": safe_avatar(profile.get("avatar")),
    }


def merge_profile_update(existing: dict[str, Any] | None, updates: dict[str, Any], *, preserve_manual: bool = False) -> dict[str, Any]:
    now = now_iso()
    base = existing or {
        "role_id": updates.get("role_id"),
        "display_name": updates.get("display_name"),
        "source": updates.get("source", "manual"),
        "created_at": now,
    }
    merged = {**base, **updates, "updated_at": now}
    if existing and preserve_manual:
        for key in ("summary", "chat_style", "aliases", "avatar", "sticker_preferences", "auto_speak_weight", "enabled"):
            if existing.get(key) not in ("", [], None) and key in updates:
                merged[key] = existing[key]
    if existing and existing.get("created_at"):
        merged["created_at"] = existing["created_at"]
    return merged


def available_role_members() -> dict[str, Any]:
    profiles = get_role_profiles(include_disabled=False)
    members = [role_profile_to_member(profile) for profile in profiles]
    seen = {item["role_id"] for item in members}
    current = extract_current_card_roles()
    for role in current.get("roles", []):
        if role.get("role_id") in seen:
            continue
        members.append(role)
        seen.add(role.get("role_id"))
    members.sort(key=lambda item: item["name"].casefold())
    return {"ok": True, "roles": members, "profiles": profiles, "user": current_user_member()}


def profile_lookup() -> dict[str, dict[str, Any]]:
    return {profile["role_id"]: profile for profile in get_role_profiles(include_disabled=False)}


def enriched_member_for_prompt(member: dict[str, Any], profiles: dict[str, dict[str, Any]]) -> dict[str, Any]:
    row: dict[str, Any] = {
        "role_id": member["role_id"],
        "name": member["name"],
        "type": member["type"],
        "summary": compact_text(member.get("summary"), 360),
    }
    profile = profiles.get(member["role_id"])
    if profile and member["type"] == "character":
        row["summary"] = compact_text(member.get("summary") or profile.get("summary"), 500)
        row["chat_style"] = compact_text(profile.get("chat_style"), 500)
        row["aliases"] = profile.get("aliases", [])
        row["status"] = compact_text(profile.get("status"), 80)
        row["sticker_preferences"] = profile.get("sticker_preferences", {})
        row["auto_speak_weight"] = profile.get("auto_speak_weight", 1.0)
    return row


def sanitize_members(raw: Any, *, ensure_user: bool = True) -> list[dict[str, str]]:
    candidates = raw if isinstance(raw, list) else []
    members: list[dict[str, str]] = []
    seen_names: set[str] = set()
    for index, item in enumerate(candidates):
        member = sanitize_member(item, index)
        if not member:
            continue
        key = role_name_key(member["name"])
        if not key or key in seen_names:
            continue
        if member["type"] == "user":
            members = [existing for existing in members if existing["type"] != "user"]
        members.append(member)
        seen_names.add(key)
    if ensure_user and not any(item["type"] == "user" for item in members):
        members.append(current_user_member())
    return members


def summarize_persona(raw: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("description", "personality", "scenario", "creator_notes"):
        text = compact_text(raw.get(key), 180)
        if text:
            parts.append(text)
        if len("；".join(parts)) >= 340:
            break
    return compact_text("；".join(parts), 360)


def extract_current_card_roles() -> dict[str, Any]:
    payload = read_json(CURRENT_ROLE_CARD_PATH, {})
    if not isinstance(payload, dict):
        payload = {}
    raw = payload.get("raw") if isinstance(payload.get("raw"), dict) else {}
    source_name = compact_text(payload.get("source_name"), 240)
    roles: list[dict[str, str]] = []
    role_indexes: dict[str, int] = {}

    def upsert(candidate: dict[str, Any], index: int) -> None:
        member = sanitize_member(candidate, index)
        if not member or member["type"] != "character":
            return
        key = role_name_key(member["name"])
        if not key:
            return
        if key in role_indexes:
            existing = roles[role_indexes[key]]
            if not existing["summary"] and member["summary"]:
                existing["summary"] = member["summary"]
            if existing["role_id"].startswith("role_") and not member["role_id"].startswith("role_"):
                existing["role_id"] = member["role_id"]
            return
        role_indexes[key] = len(roles)
        roles.append(member)

    state_journal = raw.get("stateJournal") if isinstance(raw.get("stateJournal"), dict) else {}
    state_roles = state_journal.get("roles") if isinstance(state_journal.get("roles"), list) else []
    for index, item in enumerate(state_roles):
        if not isinstance(item, dict) or item.get("enabled") is False:
            continue
        upsert(
            {
                "role_id": item.get("role_id") or item.get("id"),
                "name": item.get("role_name") or item.get("name"),
                "summary": item.get("summary") or "",
                "type": "character",
            },
            index,
        )

    personas = raw.get("personas")
    if isinstance(personas, dict):
        persona_items = list(personas.items())
    elif isinstance(personas, list):
        persona_items = [(str(index), item) for index, item in enumerate(personas, start=1)]
    else:
        persona_items = []
    for index, (persona_key, persona) in enumerate(persona_items):
        if not isinstance(persona, dict):
            continue
        explicit_name = compact_text(persona.get("name"), 80)
        persona_summary = summarize_persona(persona)
        if explicit_name == compact_text(persona_key, 80) and explicit_name.isdecimal() and not persona_summary:
            continue
        name = explicit_name or compact_text(persona_key, 80)
        upsert(
            {
                "role_id": persona.get("role_id") or persona.get("id") or normalize_id(name, f"role_{index + 1}"),
                "name": name,
                "summary": persona_summary,
                "avatar": persona.get("avatar") or persona.get("avatar_url") or "",
                "type": "character",
            },
            index,
        )

    main_name = compact_text(raw.get("name"), 80)
    if not roles and main_name:
        upsert(
            {
                "role_id": raw.get("role_id") or raw.get("id") or normalize_id(main_name, "main_role"),
                "name": main_name,
                "summary": summarize_persona(raw),
                "type": "character",
            },
            0,
        )
    return {"ok": True, "source_name": source_name, "roles": roles, "user": current_user_member()}


def current_card_profiles() -> list[dict[str, Any]]:
    current = extract_current_card_roles()
    source_ref = compact_text(current.get("source_name"), 240)
    profiles: list[dict[str, Any]] = []
    for role in current.get("roles", []):
        profile = sanitize_role_profile(
            {
                "role_id": role.get("role_id"),
                "display_name": role.get("name"),
                "source": "current_card",
                "source_ref": source_ref,
                "summary": role.get("summary"),
                "avatar": role.get("avatar"),
                "enabled": True,
            }
        )
        if profile:
            profiles.append(profile)
    return profiles


def sync_current_card_profiles() -> list[dict[str, Any]]:
    incoming = current_card_profiles()
    profiles = get_role_profiles(include_disabled=True)
    index_by_id = {profile["role_id"]: index for index, profile in enumerate(profiles)}
    for profile in incoming:
        index = index_by_id.get(profile["role_id"])
        if index is None:
            profiles.append(profile)
            index_by_id[profile["role_id"]] = len(profiles) - 1
            continue
        profiles[index] = merge_profile_update(profiles[index], profile, preserve_manual=True)
    save_role_profiles(profiles)
    return get_role_profiles(include_disabled=True)


def import_group_members_to_profiles() -> list[dict[str, Any]]:
    profiles = get_role_profiles(include_disabled=True)
    index_by_id = {profile["role_id"]: index for index, profile in enumerate(profiles)}
    for group in get_groups():
        for member in group.get("members", []):
            if member.get("type") != "character":
                continue
            profile = sanitize_role_profile(
                {
                    "role_id": member.get("role_id"),
                    "display_name": member.get("name"),
                    "source": "group_import",
                    "source_ref": group.get("group_id"),
                    "summary": member.get("summary"),
                    "avatar": member.get("avatar"),
                    "enabled": True,
                }
            )
            if not profile:
                continue
            index = index_by_id.get(profile["role_id"])
            if index is None:
                profiles.append(profile)
                index_by_id[profile["role_id"]] = len(profiles) - 1
            else:
                profiles[index] = merge_profile_update(profiles[index], profile, preserve_manual=True)
    save_role_profiles(profiles)
    return get_role_profiles(include_disabled=True)


def validate_group_id(value: Any) -> str:
    group_id = compact_text(value, 100).lower()
    if not GROUP_ID_RE.fullmatch(group_id):
        raise HTTPException(status_code=400, detail="群聊 ID 格式错误。")
    return group_id


def messages_path(group_id: str) -> Path:
    safe_group_id = validate_group_id(group_id)
    target = (MESSAGES_DIR / f"{safe_group_id}.json").resolve()
    if target.parent != MESSAGES_DIR.resolve():
        raise HTTPException(status_code=400, detail="群聊 ID 路径错误。")
    return target


def sanitize_group(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    try:
        group_id = validate_group_id(raw.get("group_id"))
    except HTTPException:
        return None
    name = compact_text(raw.get("name"), 80)
    if not name:
        return None
    settings = get_settings()
    return {
        "group_id": group_id,
        "name": name,
        "description": compact_text(raw.get("description"), 500),
        "members": sanitize_members(raw.get("members")),
        "allow_role_to_role_reply": bool(raw.get("allow_role_to_role_reply", settings["allow_role_to_role_reply"])),
        "allow_auto_interject": bool(raw.get("allow_auto_interject", settings["allow_auto_interject"])),
        "reply_count": "1" if str(raw.get("reply_count", settings["reply_count"])).strip() == "1" else "1-2",
        "sticker_pack": "default",
        "created_at": compact_text(raw.get("created_at"), 80) or now_iso(),
        "updated_at": compact_text(raw.get("updated_at"), 80) or now_iso(),
    }


def get_groups() -> list[dict[str, Any]]:
    ensure_runtime_data()
    stored = read_json(GROUPS_PATH, [])
    rows = stored.get("groups", []) if isinstance(stored, dict) else stored
    if not isinstance(rows, list):
        rows = []
    groups = [group for item in rows if (group := sanitize_group(item)) is not None]
    return sorted(groups, key=lambda item: item["updated_at"], reverse=True)


def save_groups(groups: list[dict[str, Any]]) -> None:
    write_json(GROUPS_PATH, groups)


def get_group_or_404(group_id: str) -> dict[str, Any]:
    safe_group_id = validate_group_id(group_id)
    for group in get_groups():
        if group["group_id"] == safe_group_id:
            return group
    raise HTTPException(status_code=404, detail="群聊不存在。")


def sanitize_message(raw: Any) -> dict[str, str] | None:
    if not isinstance(raw, dict):
        return None
    message_type = compact_text(raw.get("type"), 20).lower()
    if message_type not in MESSAGE_TYPES:
        return None
    content = compact_text(raw.get("content"), 500)
    if not content:
        return None
    if message_type == "sticker" and not is_valid_sticker_id(content):
        return None
    source = compact_text(raw.get("source"), 20).lower()
    if source not in MESSAGE_SOURCES:
        source = "system"
    return {
        "message_id": normalize_id(raw.get("message_id"), make_id("msg")),
        "speaker_id": normalize_id(raw.get("speaker_id"), "system"),
        "speaker_name": compact_text(raw.get("speaker_name"), 80) or "系统",
        "type": message_type,
        "content": content,
        "created_at": compact_text(raw.get("created_at"), 80) or now_iso(),
        "source": source,
    }


def get_messages(group_id: str) -> list[dict[str, str]]:
    get_group_or_404(group_id)
    rows = read_json(messages_path(group_id), [])
    if not isinstance(rows, list):
        rows = []
    return [message for item in rows if (message := sanitize_message(item)) is not None]


def append_group_messages(group_id: str, entries: list[dict[str, Any]]) -> list[dict[str, str]]:
    safe_group_id = validate_group_id(group_id)
    get_group_or_404(safe_group_id)
    with STORAGE_LOCK:
        path = messages_path(safe_group_id)
        rows = _read_json_unlocked(path, [])
        if not isinstance(rows, list):
            rows = []
        sanitized_entries = [message for item in entries if (message := sanitize_message(item)) is not None]
        rows.extend(sanitized_entries)
        _write_json_unlocked(path, rows)
    return sanitized_entries


def sanitize_app_entry(raw: Any, index: int = 0) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    app_id = normalize_id(raw.get("app_id") or raw.get("id"), f"app_{index + 1}")
    label = compact_text(raw.get("label"), 40)
    page = compact_text(raw.get("page"), 80)
    if not app_id or not label or not page:
        return None
    return {
        "app_id": app_id,
        "label": label,
        "subtitle": compact_text(raw.get("subtitle"), 80),
        "icon": normalize_id(raw.get("icon"), "message"),
        "page": page,
        "order": clamp_int(raw.get("order"), 0, 10000, (index + 1) * 10),
        "enabled": bool(raw.get("enabled", True)),
        "stage": compact_text(raw.get("stage"), 20),
    }


def sanitize_app_registry(raw: Any) -> dict[str, Any]:
    source = raw if isinstance(raw, dict) else {}
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    source_rows = source.get("apps") if isinstance(source.get("apps"), list) else DEFAULT_APP_REGISTRY["apps"]
    default_by_id = {item["app_id"]: item for item in DEFAULT_APP_REGISTRY["apps"]}
    for index, item in enumerate(source_rows):
        app_entry = sanitize_app_entry(item, index)
        if not app_entry or app_entry["app_id"] in seen:
            continue
        merged = {**default_by_id.get(app_entry["app_id"], {}), **app_entry}
        seen.add(merged["app_id"])
        rows.append(merged)
    for item in DEFAULT_APP_REGISTRY["apps"]:
        if item["app_id"] not in seen:
            rows.append(clone_default(item))
    rows.sort(key=lambda item: (item["order"], item["app_id"]))
    return {"schema_version": 1, "apps": rows}


def get_app_registry(*, include_disabled: bool = True) -> dict[str, Any]:
    ensure_runtime_data()
    registry = sanitize_app_registry(read_json(APP_REGISTRY_PATH, DEFAULT_APP_REGISTRY))
    if registry != read_json(APP_REGISTRY_PATH, DEFAULT_APP_REGISTRY):
        write_json(APP_REGISTRY_PATH, registry)
    apps = registry["apps"] if include_disabled else [item for item in registry["apps"] if item["enabled"]]
    return {"schema_version": 1, "apps": apps}


def save_app_registry(apps: Any) -> dict[str, Any]:
    registry = sanitize_app_registry({"apps": apps})
    write_json(APP_REGISTRY_PATH, registry)
    return registry


def sanitize_channel(raw: Any, index: int = 0) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    channel_id = normalize_id(raw.get("channel_id") or raw.get("id"), f"channel_{index + 1}")
    channel_type = normalize_id(raw.get("type"), "feed")
    if channel_type not in CHANNEL_TYPES or channel_type == "group_chat":
        channel_type = "feed"
    label = compact_text(raw.get("label"), 60) or channel_id
    return {
        "channel_id": channel_id,
        "type": channel_type,
        "label": label,
        "description": compact_text(raw.get("description"), 500),
        "seed_count": clamp_int(raw.get("seed_count"), 1, 20, 5),
        "enabled": bool(raw.get("enabled", True)),
    }


def sanitize_channels(raw: Any) -> dict[str, Any]:
    source = raw if isinstance(raw, dict) else {}
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    source_rows = source.get("channels") if isinstance(source.get("channels"), list) else DEFAULT_CHANNELS["channels"]
    default_by_id = {item["channel_id"]: item for item in DEFAULT_CHANNELS["channels"]}
    for index, item in enumerate(source_rows):
        channel = sanitize_channel(item, index)
        if not channel or channel["channel_id"] in seen:
            continue
        rows.append({**default_by_id.get(channel["channel_id"], {}), **channel})
        seen.add(channel["channel_id"])
    for item in DEFAULT_CHANNELS["channels"]:
        if item["channel_id"] not in seen:
            rows.append(clone_default(item))
    return {"schema_version": 1, "channels": rows}


def get_channels(*, include_disabled: bool = True) -> list[dict[str, Any]]:
    ensure_runtime_data()
    payload = sanitize_channels(read_json(CHANNELS_PATH, DEFAULT_CHANNELS))
    if payload != read_json(CHANNELS_PATH, DEFAULT_CHANNELS):
        write_json(CHANNELS_PATH, payload)
    rows = payload["channels"] if include_disabled else [item for item in payload["channels"] if item["enabled"]]
    return sorted(rows, key=lambda item: item["channel_id"])


def get_channel_or_404(channel_id: str) -> dict[str, Any]:
    safe_channel_id = normalize_id(channel_id)
    channel = next((item for item in get_channels(include_disabled=True) if item["channel_id"] == safe_channel_id), None)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found.")
    return channel


def channel_events_path(channel_id: str) -> Path:
    safe_channel_id = normalize_id(channel_id)
    if not safe_channel_id:
        raise HTTPException(status_code=400, detail="Invalid channel id.")
    return EVENTS_DIR / f"{safe_channel_id}.json"


def sanitize_event_tags(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    tags: list[str] = []
    seen: set[str] = set()
    for item in value:
        tag = normalize_id(item)
        if not tag or tag in seen:
            continue
        tags.append(tag)
        seen.add(tag)
        if len(tags) >= 12:
            break
    return tags


def sanitize_channel_event(raw: Any, channel: dict[str, Any], index: int = 0) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    content = compact_text(raw.get("content") or raw.get("body"), 2000)
    if not content:
        return None
    event_type = normalize_id(raw.get("event_type") or raw.get("type"), channel["type"])
    if event_type not in CHANNEL_EVENT_TYPES:
        event_type = {"feed": "post", "forum": "thread", "mail": "mail", "diary": "diary", "calendar": "calendar"}.get(channel["type"], "post")
    metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    return {
        "event_id": normalize_id(raw.get("event_id") or raw.get("id"), f"evt_{uuid4().hex[:12]}"),
        "channel_id": channel["channel_id"],
        "channel_type": channel["type"],
        "event_type": event_type,
        "title": compact_text(raw.get("title"), 120) or channel["label"],
        "content": content,
        "author_id": normalize_id(raw.get("author_id") or raw.get("speaker_id"), "system"),
        "author_name": compact_text(raw.get("author_name") or raw.get("speaker_name") or raw.get("author"), 80) or "System",
        "source": normalize_id(raw.get("source"), "ai"),
        "tags": sanitize_event_tags(raw.get("tags")),
        "metadata": {compact_text(key, 40): compact_text(value, 500) for key, value in metadata.items() if compact_text(key, 40)},
        "created_at": compact_text(raw.get("created_at"), 80) or now_iso(),
        "updated_at": compact_text(raw.get("updated_at"), 80) or compact_text(raw.get("created_at"), 80) or now_iso(),
    }


def get_channel_events(channel_id: str) -> list[dict[str, Any]]:
    channel = get_channel_or_404(channel_id)
    rows = read_json(channel_events_path(channel["channel_id"]), [])
    if not isinstance(rows, list):
        rows = []
    events = [event for index, item in enumerate(rows) if (event := sanitize_channel_event(item, channel, index)) is not None]
    return sorted(events, key=lambda item: item["created_at"], reverse=True)


def append_channel_events(channel_id: str, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    channel = get_channel_or_404(channel_id)
    existing = get_channel_events(channel["channel_id"])
    sanitized = [event for index, item in enumerate(entries) if (event := sanitize_channel_event(item, channel, index)) is not None]
    if not sanitized:
        return []
    merged = sorted([*sanitized, *existing], key=lambda item: item["created_at"], reverse=True)[:500]
    write_json(channel_events_path(channel["channel_id"]), merged)
    return sanitized


def summarize_mobile_context() -> dict[str, Any]:
    roles = get_role_profiles(include_disabled=False)[:20]
    groups = get_groups()[:20]
    return {
        "roles": [
            {
                "role_id": item["role_id"],
                "display_name": item["display_name"],
                "summary": item.get("summary", ""),
                "status": item.get("status", ""),
                "chat_style": item.get("chat_style", ""),
            }
            for item in roles
        ],
        "groups": [
            {
                "group_id": item["group_id"],
                "name": item["name"],
                "description": item.get("description", ""),
                "members": [member["name"] for member in item.get("members", []) if member.get("type") == "character"],
            }
            for item in groups
        ],
        "recent_channel_events": {
            channel["channel_id"]: [
                {"title": event["title"], "author_name": event["author_name"], "content": event["content"][:160]}
                for event in get_channel_events(channel["channel_id"])[:5]
            ]
            for channel in get_channels(include_disabled=False)
        },
    }


def build_channel_seed_messages(channel: dict[str, Any], count: int) -> list[dict[str, str]]:
    schema = next((item for item in channel_schema_catalog() if item["type"] == channel["type"]), {})
    context = {
        "channel": channel,
        "count": count,
        "schema": schema,
        "mobile_context": summarize_mobile_context(),
    }
    system_text = assembled_prompt_text(channel["type"]) or system_prompt_text()
    user_text = (
        "Generate seed content for this mobile app channel. "
        "Return JSON only in the form {\"events\":[...]}. "
        "Each event must include title, content, author_name, event_type, tags and metadata.\n"
        + json.dumps(context, ensure_ascii=False, indent=2)
    )
    return [{"role": "system", "content": system_text}, {"role": "user", "content": user_text}]


def parse_channel_seed_events(raw: str, channel: dict[str, Any], count: int) -> list[dict[str, Any]]:
    cleaned = strip_json_fence(raw)
    payload: Any = None
    for candidate in (cleaned, cleaned[cleaned.find("{") : cleaned.rfind("}") + 1] if "{" in cleaned and "}" in cleaned else ""):
        if not candidate:
            continue
        try:
            payload = json.loads(candidate)
            break
        except ValueError:
            continue
    raw_events = payload.get("events", []) if isinstance(payload, dict) else []
    if not isinstance(raw_events, list):
        raw_events = []
    events = [event for index, item in enumerate(raw_events[:count]) if (event := sanitize_channel_event(item, channel, index)) is not None]
    if events:
        return events
    fallback = {
        "event_type": {"feed": "post", "forum": "thread", "mail": "mail", "diary": "diary", "calendar": "calendar"}.get(channel["type"], "post"),
        "title": f"{channel['label']} seed",
        "content": compact_text(cleaned, 500) or "Seed content generated, but the model did not return the expected schema.",
        "author_name": "System",
        "source": "system",
        "tags": ["fallback"],
    }
    event = sanitize_channel_event(fallback, channel, 0)
    return [event] if event else []


def sanitize_notification(raw: Any, index: int = 0) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    title = compact_text(raw.get("title"), 120)
    content = compact_text(raw.get("content"), 500)
    if not title and not content:
        return None
    return {
        "notification_id": normalize_id(raw.get("notification_id") or raw.get("id"), f"ntf_{uuid4().hex[:12]}"),
        "title": title or "Notification",
        "content": content,
        "source": normalize_id(raw.get("source"), "system"),
        "channel_id": normalize_id(raw.get("channel_id"), ""),
        "event_id": normalize_id(raw.get("event_id"), ""),
        "read": bool(raw.get("read", False)),
        "created_at": compact_text(raw.get("created_at"), 80) or now_iso(),
    }


def get_notifications() -> list[dict[str, Any]]:
    ensure_runtime_data()
    payload = read_json(NOTIFICATIONS_PATH, DEFAULT_NOTIFICATIONS)
    rows = payload.get("items", []) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        rows = []
    return sorted(
        [item for index, row in enumerate(rows) if (item := sanitize_notification(row, index)) is not None],
        key=lambda item: item["created_at"],
        reverse=True,
    )


def save_notifications(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sanitized = [item for index, row in enumerate(items) if (item := sanitize_notification(row, index)) is not None]
    write_json(NOTIFICATIONS_PATH, {"schema_version": 1, "items": sanitized[:300]})
    return sanitized[:300]


def add_notification(title: str, content: str, *, source: str = "system", channel_id: str = "", event_id: str = "") -> dict[str, Any] | None:
    notification = sanitize_notification(
        {
            "title": title,
            "content": content,
            "source": source,
            "channel_id": channel_id,
            "event_id": event_id,
            "read": False,
            "created_at": now_iso(),
        }
    )
    if not notification:
        return None
    save_notifications([notification, *get_notifications()])
    return notification


def notification_from_event(event: dict[str, Any]) -> dict[str, Any] | None:
    return add_notification(
        event["title"],
        f"{event['author_name']}: {event['content'][:180]}",
        source=event.get("source", "ai"),
        channel_id=event["channel_id"],
        event_id=event["event_id"],
    )


def sanitize_phone_line(raw: Any, index: int = 0) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    content = compact_text(raw.get("content") or raw.get("line"), 500)
    if not content:
        return None
    speaker = compact_text(raw.get("speaker") or raw.get("speaker_name"), 80) or "Unknown"
    return {
        "line_id": normalize_id(raw.get("line_id") or raw.get("id"), f"line_{uuid4().hex[:12]}"),
        "speaker": speaker,
        "speaker_id": normalize_id(raw.get("speaker_id"), ""),
        "content": content,
        "mood": normalize_id(raw.get("mood"), ""),
        "created_at": compact_text(raw.get("created_at"), 80) or now_iso(),
        "source": normalize_id(raw.get("source"), "ai"),
    }


def sanitize_phone_session(raw: Any, index: int = 0) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    role_id = normalize_id(raw.get("role_id"), "")
    if not role_id:
        return None
    raw_lines = raw.get("lines") if isinstance(raw.get("lines"), list) else []
    lines = [line for line_index, item in enumerate(raw_lines) if (line := sanitize_phone_line(item, line_index)) is not None]
    return {
        "session_id": normalize_id(raw.get("session_id") or raw.get("id"), f"call_{uuid4().hex[:12]}"),
        "role_id": role_id,
        "role_name": compact_text(raw.get("role_name"), 80) or role_id,
        "status": normalize_id(raw.get("status"), "ongoing"),
        "started_at": compact_text(raw.get("started_at"), 80) or now_iso(),
        "updated_at": compact_text(raw.get("updated_at"), 80) or now_iso(),
        "lines": lines[-120:],
    }


def get_phone_sessions() -> list[dict[str, Any]]:
    ensure_runtime_data()
    payload = read_json(PHONE_CALLS_PATH, DEFAULT_PHONE_CALLS)
    rows = payload.get("sessions", []) if isinstance(payload, dict) else []
    if not isinstance(rows, list):
        rows = []
    return sorted(
        [item for index, row in enumerate(rows) if (item := sanitize_phone_session(row, index)) is not None],
        key=lambda item: item["updated_at"],
        reverse=True,
    )


def save_phone_sessions(sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sanitized = [item for index, row in enumerate(sessions) if (item := sanitize_phone_session(row, index)) is not None]
    write_json(PHONE_CALLS_PATH, {"schema_version": 1, "sessions": sanitized[:80]})
    return sanitized[:80]


def get_phone_role_or_404(role_id: str) -> dict[str, Any]:
    safe_role_id = normalize_id(role_id)
    role = next((item for item in get_role_profiles(include_disabled=False) if item["role_id"] == safe_role_id), None)
    if not role:
        raise HTTPException(status_code=404, detail="Phone role not found.")
    return role


def build_phone_call_messages(role: dict[str, Any], session: dict[str, Any], user_line: str) -> list[dict[str, str]]:
    context = {
        "role": {
            "role_id": role["role_id"],
            "display_name": role["display_name"],
            "summary": role.get("summary", ""),
            "status": role.get("status", ""),
            "chat_style": role.get("chat_style", ""),
        },
        "recent_lines": session.get("lines", [])[-20:],
        "user_line": user_line,
        "output_schema": {
            "lines": [{"speaker": role["display_name"], "content": "short phone line", "mood": "soft"}],
            "call_state": "ongoing",
        },
    }
    system_text = assembled_prompt_text("phone") or system_prompt_text()
    user_text = (
        "Continue a simulated phone call with the target role. "
        "Return JSON only with lines and call_state. Keep each line compact.\n"
        + json.dumps(context, ensure_ascii=False, indent=2)
    )
    return [{"role": "system", "content": system_text}, {"role": "user", "content": user_text}]


def parse_phone_lines(raw: str, role: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    cleaned = strip_json_fence(raw)
    payload: Any = None
    for candidate in (cleaned, cleaned[cleaned.find("{") : cleaned.rfind("}") + 1] if "{" in cleaned and "}" in cleaned else ""):
        if not candidate:
            continue
        try:
            payload = json.loads(candidate)
            break
        except ValueError:
            continue
    raw_lines = payload.get("lines", []) if isinstance(payload, dict) else []
    if not isinstance(raw_lines, list):
        raw_lines = []
    lines: list[dict[str, Any]] = []
    for index, item in enumerate(raw_lines[:4]):
        if not isinstance(item, dict):
            continue
        item = {**item, "speaker": item.get("speaker") or role["display_name"], "speaker_id": role["role_id"], "source": "ai"}
        line = sanitize_phone_line(item, index)
        if line:
            lines.append(line)
    if not lines:
        fallback = sanitize_phone_line(
            {
                "speaker": role["display_name"],
                "speaker_id": role["role_id"],
                "content": compact_text(cleaned, 500) or "...",
                "source": "ai",
            }
        )
        if fallback:
            lines.append(fallback)
    call_state = normalize_id(payload.get("call_state") if isinstance(payload, dict) else "", "ongoing")
    if call_state not in {"ongoing", "ended", "missed"}:
        call_state = "ongoing"
    return lines, call_state


def user_message_for(group: dict[str, Any], content: str, message_type: str = "text") -> dict[str, Any]:
    user = next((item for item in group["members"] if item["type"] == "user"), current_user_member())
    return {
        "message_id": make_id("msg"),
        "speaker_id": "user",
        "speaker_name": user["name"],
        "type": message_type,
        "content": content,
        "created_at": now_iso(),
        "source": "user",
    }


def read_route_forwarding_fallback() -> dict[str, str]:
    payload = read_json(ROUTE_FORWARDING_PATH, {})
    if not isinstance(payload, dict) or not payload.get("enabled"):
        return {"base_url": "", "api_key": "", "model": ""}
    providers = [
        item
        for item in payload.get("providers", [])
        if isinstance(item, dict) and item.get("enabled", True) and compact_text(item.get("base_url"), 500)
    ]
    providers.sort(key=lambda item: (clamp_int(item.get("priority"), 1, 999, 999), compact_text(item.get("name"), 80)))
    if not providers:
        return {"base_url": "", "api_key": "", "model": ""}
    provider = providers[0]
    keys = provider.get("keys") if isinstance(provider.get("keys"), list) else []
    return {
        "base_url": compact_text(provider.get("base_url"), 500),
        "api_key": compact_text(keys[0] if keys else provider.get("api_key"), 500),
        "model": compact_text(provider.get("model"), 160),
    }


def read_main_llm_config() -> dict[str, Any]:
    settings = read_json(MAIN_SETTINGS_PATH, {})
    if not isinstance(settings, dict):
        settings = {}
    route_fallback = read_route_forwarding_fallback()
    return {
        "base_url": compact_text(settings.get("llm_base_url") or route_fallback["base_url"] or os.getenv("LLM_BASE_URL"), 500),
        "api_key": compact_text(settings.get("llm_api_key") or route_fallback["api_key"] or os.getenv("LLM_API_KEY"), 500),
        "model": compact_text(settings.get("llm_model") or route_fallback["model"] or os.getenv("LLM_MODEL"), 160),
        "temperature": clamp_float(settings.get("temperature"), 0.0, 2.0, 0.85),
        "request_timeout": clamp_int(settings.get("request_timeout") or os.getenv("LLM_REQUEST_TIMEOUT"), 10, 600, 120),
    }


def build_api_url(base_url: str, endpoint: str) -> str:
    clean_base = compact_text(base_url, 500).rstrip("/")
    clean_endpoint = endpoint.strip("/")
    if not clean_base:
        return ""
    if clean_base.endswith(f"/{clean_endpoint}") or clean_base.endswith(clean_endpoint):
        return clean_base
    return f"{clean_base}/{clean_endpoint}"


async def call_chat_model(messages: list[dict[str, str]], *, max_tokens: int, temperature: float) -> str:
    config = read_main_llm_config()
    url = build_api_url(config["base_url"], "chat/completions")
    if not url:
        raise HTTPException(status_code=400, detail="请先配置聊天模型 API URL。")
    if not config["model"]:
        raise HTTPException(status_code=400, detail="请先配置聊天模型名称。")
    headers = {"Content-Type": "application/json"}
    if config["api_key"]:
        headers["Authorization"] = f"Bearer {config['api_key']}"
    payload = {
        "model": config["model"],
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=float(config["request_timeout"])) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code if exc.response is not None else 502
        raise HTTPException(status_code=502, detail=f"模型服务返回 HTTP {status_code}。") from exc
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="模型服务响应超时，请稍后重试。") from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="无法连接聊天模型服务，请检查网络与 API 地址。") from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="模型服务返回的不是合法 JSON。") from exc
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(status_code=502, detail="模型服务返回格式不兼容 Chat Completions。") from exc
    text = str(content or "").strip()
    if not text:
        raise HTTPException(status_code=502, detail="模型没有返回内容。")
    return text


def system_prompt_text() -> str:
    try:
        settings = get_settings()
        if settings.get("prompt", {}).get("use_block_prompt"):
            assembled = assembled_prompt_text("group_chat")
            if assembled:
                return assembled
    except Exception:
        pass
    try:
        return PROMPT_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        return "你正在模拟即时聊天群。只返回 JSON 对象，根字段为 messages。"


def sticker_prompt_catalog() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for sticker in sticker_catalog()[:120]:
        item: dict[str, Any] = {
            "id": sticker["id"],
            "label": sticker.get("label", sticker["id"]),
            "pack": sticker.get("pack_label", ""),
        }
        if sticker.get("tags"):
            item["tags"] = sticker["tags"]
        if sticker.get("description"):
            item["description"] = sticker["description"]
        rows.append(item)
    return rows


def build_mobile_model_messages(
    group: dict[str, Any],
    recent_messages: list[dict[str, str]],
    user_message: str,
    *,
    generation_mode: str = "user_message",
) -> list[dict[str, str]]:
    settings = get_settings()
    profiles = profile_lookup() if settings.get("roles", {}).get("profile_overrides_enabled", True) else {}
    mode_instruction = (
        "用户刚刚发言。请根据用户消息自然回复。"
        if generation_mode == "user_message"
        else "用户本轮没有发言。请让群聊中的角色基于最近对话自然继续聊一轮，不要替用户说话，不要推进过多剧情。"
    )
    context = {
        "group_name": group["name"],
        "group_description": group["description"],
        "members": [
            enriched_member_for_prompt(item, profiles)
            for item in group["members"]
        ],
        "recent_messages": [
            {
                "speaker": item["speaker_name"],
                "type": item["type"],
                "content": item["content"],
            }
            for item in recent_messages[-settings["recent_message_limit"] :]
            if item["type"] in {"text", "sticker"}
        ],
        "current_user_message": user_message,
        "generation_mode": generation_mode,
        "mode_instruction": mode_instruction,
        "reply_count": group["reply_count"],
        "allow_role_to_role_reply": group["allow_role_to_role_reply"],
        "allow_auto_interject": group["allow_auto_interject"],
        "available_stickers": sticker_prompt_catalog(),
    }
    return [
        {"role": "system", "content": system_prompt_text()},
        {
            "role": "user",
            "content": "请根据以下群聊上下文生成本轮回复，只返回 JSON：\n" + json.dumps(context, ensure_ascii=False, indent=2),
        },
    ]


def strip_json_fence(text: str) -> str:
    raw = str(text or "").strip()
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, re.IGNORECASE)
    return fenced.group(1).strip() if fenced else raw


def first_ai_member(group: dict[str, Any]) -> dict[str, str] | None:
    return next((item for item in group["members"] if item["type"] == "character"), None)


def parse_model_mobile_messages(raw: str, group: dict[str, Any]) -> list[dict[str, Any]]:
    cleaned = strip_json_fence(raw)
    payload: Any = None
    parse_failed = False
    for candidate in (cleaned, cleaned[cleaned.find("{") : cleaned.rfind("}") + 1] if "{" in cleaned and "}" in cleaned else ""):
        if not candidate:
            continue
        try:
            payload = json.loads(candidate)
            break
        except ValueError:
            continue
    if payload is None:
        parse_failed = True
    raw_messages = payload.get("messages", []) if isinstance(payload, dict) else []
    if not isinstance(raw_messages, list):
        raw_messages = []
    ai_members = [item for item in group["members"] if item["type"] == "character"]
    by_name = {role_name_key(item["name"]): item for item in ai_members}
    by_id = {item["role_id"]: item for item in ai_members}
    parsed: list[dict[str, Any]] = []
    reply_limit = 1 if group["reply_count"] == "1" else 2
    for item in raw_messages:
        if not isinstance(item, dict):
            continue
        speaker_value = compact_text(item.get("speaker") or item.get("speaker_name") or item.get("speaker_id"), 80)
        member = by_name.get(role_name_key(speaker_value)) or by_id.get(normalize_id(speaker_value))
        message_type = compact_text(item.get("type"), 20).lower()
        content = compact_text(item.get("content"), 280)
        if not member or message_type not in {"text", "sticker"} or not content:
            continue
        if message_type == "sticker" and not is_valid_sticker_id(content, require_exists=True):
            continue
        parsed.append(
            {
                "message_id": make_id("msg"),
                "speaker_id": member["role_id"],
                "speaker_name": member["name"],
                "type": message_type,
                "content": content,
                "created_at": now_iso(),
                "source": "ai",
            }
        )
        if len(parsed) >= reply_limit:
            break
    fallback_member = first_ai_member(group)
    if not parsed and fallback_member:
        fallback_text = compact_text(cleaned if parse_failed else "我看到了。", 280) or "我看到了。"
        parsed.append(
            {
                "message_id": make_id("msg"),
                "speaker_id": fallback_member["role_id"],
                "speaker_name": fallback_member["name"],
                "type": "text",
                "content": fallback_text,
                "created_at": now_iso(),
                "source": "ai",
            }
        )
    return parsed


def group_async_lock(group_id: str) -> asyncio.Lock:
    safe_group_id = validate_group_id(group_id)
    with STORAGE_LOCK:
        return GROUP_ASYNC_LOCKS.setdefault(safe_group_id, asyncio.Lock())


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    ensure_runtime_data()
    return templates.TemplateResponse(request, "index.html", {"settings": get_settings()})


@app.get("/api/settings")
async def api_get_settings() -> dict[str, Any]:
    settings = clone_default(get_settings())
    automation_state = get_automation_state()
    settings["auto_behavior"] = {**settings.get("auto_behavior", {}), "paused": automation_state["paused"]}
    return {"ok": True, "settings": settings}


@app.get("/api/stickers")
async def api_get_stickers() -> dict[str, Any]:
    return {"ok": True, "packs": sticker_pack_summaries(), "stickers": sticker_catalog()}


@app.get("/api/stickers/{pack_id}/{filename}")
async def api_get_sticker_image(pack_id: str, filename: str) -> FileResponse:
    path = custom_sticker_path(pack_id, filename, require_exists=True)
    if not path:
        raise HTTPException(status_code=404, detail="贴纸图片不存在。")
    return FileResponse(path, media_type="image/png")


@app.get("/api/admin/sticker-packs")
async def api_admin_sticker_packs() -> dict[str, Any]:
    return {"ok": True, "packs": sticker_pack_summaries(), "stickers": sticker_catalog()}


@app.get("/api/admin/sticker-packs/{pack_id}/manifest")
async def api_admin_get_sticker_manifest(pack_id: str) -> dict[str, Any]:
    return {"ok": True, "pack_id": compact_text(pack_id, 80), "stickers": sticker_manifest_rows(compact_text(pack_id, 80))}


@app.put("/api/admin/sticker-packs/{pack_id}/manifest")
async def api_admin_save_sticker_manifest(pack_id: str, payload: StickerManifestPayload) -> dict[str, Any]:
    safe_pack_id = compact_text(pack_id, 80)
    save_sticker_manifest(safe_pack_id, payload.stickers)
    return {"ok": True, "pack_id": safe_pack_id, "stickers": sticker_manifest_rows(safe_pack_id)}


@app.post("/api/admin/sticker-packs/{pack_id}/scan")
async def api_admin_scan_sticker_pack(pack_id: str) -> dict[str, Any]:
    safe_pack_id = compact_text(pack_id, 80)
    return {"ok": True, "pack_id": safe_pack_id, "stickers": sticker_manifest_rows(safe_pack_id)}


@app.post("/api/settings")
async def api_save_settings(payload: SettingsPayload) -> dict[str, Any]:
    merged = merge_settings_update(get_settings(), payload.model_dump(exclude_none=True))
    settings = sanitize_settings(merged)
    write_json(SETTINGS_PATH, settings)
    if settings["allow_auto_interject"]:
        save_automation_state({**get_automation_state(), "paused": False, "paused_at": ""})
    return {"ok": True, "settings": settings}


@app.get("/api/admin/automation")
async def api_admin_automation() -> dict[str, Any]:
    settings = get_settings()
    return {
        "ok": True,
        "auto_behavior": settings["auto_behavior"],
        "allow_auto_interject": settings["allow_auto_interject"],
        "state": get_automation_state(),
        "groups": get_groups(),
    }


@app.patch("/api/admin/automation")
async def api_admin_patch_automation(payload: AutomationPayload) -> dict[str, Any]:
    updates = payload.model_dump(exclude_none=True)
    settings = update_auto_behavior(updates)
    return {"ok": True, "auto_behavior": settings["auto_behavior"], "state": get_automation_state()}


@app.post("/api/admin/automation/pause-all")
async def api_admin_pause_automation() -> dict[str, Any]:
    settings = update_auto_behavior({"enabled": False})
    state = save_automation_state({**get_automation_state(), "paused": True, "paused_at": now_iso()})
    return {"ok": True, "auto_behavior": settings["auto_behavior"], "state": state}


@app.post("/api/admin/automation/test-once", response_model=None)
async def api_admin_test_automation(payload: AutomationTestPayload) -> JSONResponse | dict[str, Any]:
    safe_group_id = validate_group_id(payload.group_id)
    state = save_automation_state({**get_automation_state(), "last_test_at": now_iso(), "last_test_group_id": safe_group_id})
    result = await api_continue(ContinuePayload(group_id=safe_group_id))
    if isinstance(result, JSONResponse):
        return result
    return {"ok": True, "state": state, "messages": result.get("messages", [])}


@app.get("/api/current-card-roles")
async def api_current_card_roles() -> dict[str, Any]:
    return extract_current_card_roles()


@app.get("/api/roles")
async def api_get_available_roles() -> dict[str, Any]:
    return available_role_members()


@app.get("/api/admin/roles")
async def api_admin_roles() -> dict[str, Any]:
    return {"ok": True, "roles": get_role_profiles(include_disabled=True), "available": available_role_members()["roles"], "user": current_user_member()}


@app.post("/api/admin/roles")
async def api_create_role(payload: RoleProfilePayload) -> dict[str, Any]:
    raw = payload.model_dump(exclude_none=True)
    profile = sanitize_role_profile({**raw, "source": raw.get("source") or "manual", "enabled": raw.get("enabled", True)})
    if not profile:
        raise HTTPException(status_code=400, detail="请填写角色名称。")
    profiles = get_role_profiles(include_disabled=True)
    if any(item["role_id"] == profile["role_id"] for item in profiles):
        raise HTTPException(status_code=409, detail="角色 ID 已存在，请换一个名称或 ID。")
    profiles.append(profile)
    save_role_profiles(profiles)
    return {"ok": True, "role": profile, "roles": get_role_profiles(include_disabled=True)}


@app.patch("/api/admin/roles/{role_id}")
async def api_patch_role(role_id: str, payload: RoleProfilePatchPayload) -> dict[str, Any]:
    safe_role_id = normalize_id(role_id)
    if not safe_role_id:
        raise HTTPException(status_code=400, detail="角色 ID 格式错误。")
    profiles = get_role_profiles(include_disabled=True)
    index = next((idx for idx, item in enumerate(profiles) if item["role_id"] == safe_role_id), None)
    if index is None:
        raise HTTPException(status_code=404, detail="角色不存在。")
    updates = payload.model_dump(exclude_none=True)
    merged = merge_profile_update(profiles[index], updates)
    sanitized = sanitize_role_profile({**merged, "role_id": safe_role_id})
    if not sanitized:
        raise HTTPException(status_code=400, detail="角色资料格式错误。")
    profiles[index] = sanitized
    save_role_profiles(profiles)
    return {"ok": True, "role": sanitized, "roles": get_role_profiles(include_disabled=True)}


@app.delete("/api/admin/roles/{role_id}")
async def api_disable_role(role_id: str) -> dict[str, Any]:
    safe_role_id = normalize_id(role_id)
    profiles = get_role_profiles(include_disabled=True)
    index = next((idx for idx, item in enumerate(profiles) if item["role_id"] == safe_role_id), None)
    if index is None:
        raise HTTPException(status_code=404, detail="角色不存在。")
    profiles[index] = {**profiles[index], "enabled": False, "updated_at": now_iso()}
    save_role_profiles(profiles)
    return {"ok": True, "role": profiles[index], "roles": get_role_profiles(include_disabled=True)}


@app.post("/api/admin/roles/sync-current-card")
async def api_sync_current_card_roles() -> dict[str, Any]:
    return {"ok": True, "roles": sync_current_card_profiles()}


@app.post("/api/admin/roles/import-from-groups")
async def api_import_group_roles() -> dict[str, Any]:
    return {"ok": True, "roles": import_group_members_to_profiles()}


@app.get("/api/groups")
async def api_get_groups() -> dict[str, Any]:
    return {"ok": True, "groups": get_groups()}


@app.post("/api/groups")
async def api_create_group(payload: GroupCreatePayload) -> dict[str, Any]:
    name = compact_text(payload.name, 80)
    if not name:
        raise HTTPException(status_code=400, detail="请填写群聊名称。")
    members = sanitize_members(payload.members)
    if not any(item["type"] == "character" for item in members):
        raise HTTPException(status_code=400, detail="请至少选择一个角色。")
    settings = get_settings()
    group = sanitize_group(
        {
            "group_id": make_id("group"),
            "name": name,
            "description": payload.description,
            "members": members,
            "allow_role_to_role_reply": payload.allow_role_to_role_reply if payload.allow_role_to_role_reply is not None else settings["allow_role_to_role_reply"],
            "allow_auto_interject": payload.allow_auto_interject if payload.allow_auto_interject is not None else settings["allow_auto_interject"],
            "reply_count": payload.reply_count or settings["reply_count"],
            "sticker_pack": payload.sticker_pack or settings["sticker_pack"],
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
    )
    if not group:
        raise HTTPException(status_code=400, detail="群聊数据格式错误。")
    with STORAGE_LOCK:
        groups = get_groups()
        groups.append(group)
        save_groups(groups)
        _write_json_unlocked(messages_path(group["group_id"]), [])
    return {"ok": True, "group": group}


@app.delete("/api/groups")
async def api_clear_groups() -> dict[str, Any]:
    with STORAGE_LOCK:
        groups = get_groups()
        for group in groups:
            messages_path(group["group_id"]).unlink(missing_ok=True)
        save_groups([])
    return {"ok": True, "deleted": len(groups)}


@app.get("/api/groups/{group_id}")
async def api_get_group(group_id: str) -> dict[str, Any]:
    return {"ok": True, "group": get_group_or_404(group_id)}


@app.patch("/api/groups/{group_id}")
async def api_patch_group(group_id: str, payload: GroupPatchPayload) -> dict[str, Any]:
    safe_group_id = validate_group_id(group_id)
    updates = payload.model_dump(exclude_none=True)
    with STORAGE_LOCK:
        groups = get_groups()
        index = next((idx for idx, item in enumerate(groups) if item["group_id"] == safe_group_id), None)
        if index is None:
            raise HTTPException(status_code=404, detail="群聊不存在。")
        merged = {**groups[index], **updates, "group_id": safe_group_id, "updated_at": now_iso()}
        if "members" in updates:
            merged["members"] = sanitize_members(updates["members"])
        group = sanitize_group(merged)
        if not group or not any(item["type"] == "character" for item in group["members"]):
            raise HTTPException(status_code=400, detail="群聊至少需要一个角色。")
        groups[index] = group
        save_groups(groups)
    return {"ok": True, "group": group}


@app.delete("/api/groups/{group_id}")
async def api_delete_group(group_id: str) -> dict[str, Any]:
    safe_group_id = validate_group_id(group_id)
    with STORAGE_LOCK:
        groups = get_groups()
        remaining = [item for item in groups if item["group_id"] != safe_group_id]
        if len(remaining) == len(groups):
            raise HTTPException(status_code=404, detail="群聊不存在。")
        save_groups(remaining)
        messages_path(safe_group_id).unlink(missing_ok=True)
    return {"ok": True}


@app.get("/api/groups/{group_id}/messages")
async def api_get_messages(group_id: str) -> dict[str, Any]:
    return {"ok": True, "messages": get_messages(group_id)}


@app.post("/api/groups/{group_id}/messages")
async def api_post_message(group_id: str, payload: MessageCreatePayload) -> dict[str, Any]:
    group = get_group_or_404(group_id)
    message_type = compact_text(payload.type, 20).lower()
    content = compact_text(payload.content, 500)
    if message_type not in {"text", "sticker"}:
        raise HTTPException(status_code=400, detail="消息类型仅支持 text 或 sticker。")
    if not content:
        raise HTTPException(status_code=400, detail="消息不能为空。")
    if message_type == "sticker" and not is_valid_sticker_id(content, require_exists=True):
        raise HTTPException(status_code=400, detail="贴纸 ID 不在可用列表中。")
    message = user_message_for(group, content, message_type)
    stored = append_group_messages(group["group_id"], [message])
    return {"ok": True, "message": stored[0]}


@app.delete("/api/groups/{group_id}/messages")
async def api_delete_messages(group_id: str) -> dict[str, Any]:
    group = get_group_or_404(group_id)
    write_json(messages_path(group["group_id"]), [])
    return {"ok": True}


@app.post("/api/generate", response_model=None)
async def api_generate(payload: GeneratePayload) -> JSONResponse | dict[str, Any]:
    safe_group_id = validate_group_id(payload.group_id)
    user_text = compact_text(payload.user_message, 500)
    if not user_text:
        raise HTTPException(status_code=400, detail="消息不能为空。")
    job = begin_generation_job("group_chat", safe_group_id)
    async with group_async_lock(safe_group_id):
        group = get_group_or_404(safe_group_id)
        recent = get_messages(safe_group_id)
        user_message = append_group_messages(safe_group_id, [user_message_for(group, user_text)])[0]
        model_messages = build_mobile_model_messages(group, recent, user_text)
        settings = get_settings()
        try:
            raw_reply = await call_chat_model(
                model_messages,
                max_tokens=settings["max_tokens"],
                temperature=read_main_llm_config()["temperature"],
            )
        except HTTPException as exc:
            error_message = {
                "message_id": make_id("msg"),
                "speaker_id": "system",
                "speaker_name": "系统",
                "type": "error",
                "content": compact_text(exc.detail, 240) or "模型生成失败，请稍后重试。",
                "created_at": now_iso(),
                "source": "system",
            }
            stored_error = append_group_messages(safe_group_id, [error_message])
            finish_generation_job(job, "error", compact_text(exc.detail, 240))
            return JSONResponse(
                status_code=exc.status_code,
                content={"ok": False, "user_message": user_message, "messages": stored_error, "error": error_message["content"]},
            )
        ai_messages = parse_model_mobile_messages(raw_reply, group)
        stored_messages = append_group_messages(safe_group_id, ai_messages)
        finish_generation_job(job, "success")
        return {"ok": True, "user_message": user_message, "messages": stored_messages}


@app.post("/api/continue", response_model=None)
async def api_continue(payload: ContinuePayload) -> JSONResponse | dict[str, Any]:
    safe_group_id = validate_group_id(payload.group_id)
    job = begin_generation_job("group_chat", safe_group_id)
    async with group_async_lock(safe_group_id):
        group = get_group_or_404(safe_group_id)
        recent = get_messages(safe_group_id)
        model_messages = build_mobile_model_messages(group, recent, "", generation_mode="role_continue")
        settings = get_settings()
        try:
            raw_reply = await call_chat_model(
                model_messages,
                max_tokens=settings["max_tokens"],
                temperature=read_main_llm_config()["temperature"],
            )
        except HTTPException as exc:
            error_message = {
                "message_id": make_id("msg"),
                "speaker_id": "system",
                "speaker_name": "系统",
                "type": "error",
                "content": compact_text(exc.detail, 240) or "角色续聊失败，请稍后重试。",
                "created_at": now_iso(),
                "source": "system",
            }
            stored_error = append_group_messages(safe_group_id, [error_message])
            finish_generation_job(job, "error", compact_text(exc.detail, 240))
            return JSONResponse(
                status_code=exc.status_code,
                content={"ok": False, "messages": stored_error, "error": error_message["content"]},
            )
        ai_messages = parse_model_mobile_messages(raw_reply, group)
        stored_messages = append_group_messages(safe_group_id, ai_messages)
        finish_generation_job(job, "success")
        return {"ok": True, "messages": stored_messages}


@app.get("/api/admin/prompt-blocks")
async def api_admin_prompt_blocks() -> dict[str, Any]:
    return {"ok": True, **get_prompt_blocks()}


@app.put("/api/admin/prompt-blocks")
async def api_admin_save_prompt_blocks(payload: PromptBlocksPayload) -> dict[str, Any]:
    return {"ok": True, **save_prompt_blocks(payload.blocks)}


@app.post("/api/admin/prompt-blocks/reset")
async def api_admin_reset_prompt_blocks() -> dict[str, Any]:
    write_json(PROMPT_BLOCKS_PATH, DEFAULT_PROMPT_BLOCKS)
    return {"ok": True, **get_prompt_blocks()}


@app.get("/api/admin/prompt-preview")
async def api_admin_prompt_preview(scope: str = "group_chat", group_id: str = "") -> dict[str, Any]:
    settings = merge_settings_update(get_settings(), {"prompt": {"last_preview_channel": scope}})
    write_json(SETTINGS_PATH, sanitize_settings(settings))
    return prompt_preview_payload(scope, group_id)


@app.get("/api/admin/channel-schemas")
async def api_admin_channel_schemas() -> dict[str, Any]:
    return {"ok": True, "schemas": channel_schema_catalog()}


@app.get("/api/admin/generation-guard")
async def api_admin_generation_guard() -> dict[str, Any]:
    return {"ok": True, "state": get_generation_state()}


@app.post("/api/admin/generation-guard/reset")
async def api_admin_reset_generation_guard() -> dict[str, Any]:
    write_json(GENERATION_STATE_PATH, DEFAULT_GENERATION_STATE)
    return {"ok": True, "state": get_generation_state()}


@app.get("/api/admin/diagnostics")
async def api_admin_diagnostics() -> dict[str, Any]:
    return {"ok": True, "diagnostics": admin_diagnostics()}


@app.get("/api/apps")
async def api_apps() -> dict[str, Any]:
    return {"ok": True, **get_app_registry(include_disabled=False)}


@app.get("/api/admin/apps")
async def api_admin_apps() -> dict[str, Any]:
    return {"ok": True, **get_app_registry(include_disabled=True)}


@app.put("/api/admin/apps")
async def api_admin_save_apps(payload: AppRegistryPayload) -> dict[str, Any]:
    return {"ok": True, **save_app_registry(payload.apps)}


@app.post("/api/admin/apps/reset")
async def api_admin_reset_apps() -> dict[str, Any]:
    write_json(APP_REGISTRY_PATH, DEFAULT_APP_REGISTRY)
    return {"ok": True, **get_app_registry(include_disabled=True)}


@app.get("/api/channels")
async def api_channels() -> dict[str, Any]:
    return {"ok": True, "channels": get_channels(include_disabled=False)}


@app.get("/api/admin/channels")
async def api_admin_channels() -> dict[str, Any]:
    return {"ok": True, "channels": get_channels(include_disabled=True), "schemas": channel_schema_catalog()}


@app.get("/api/channels/{channel_id}/events")
async def api_channel_events(channel_id: str) -> dict[str, Any]:
    channel = get_channel_or_404(channel_id)
    return {"ok": True, "channel": channel, "events": get_channel_events(channel["channel_id"])}


@app.post("/api/channels/{channel_id}/events")
async def api_create_channel_event(channel_id: str, payload: ChannelEventPayload) -> dict[str, Any]:
    channel = get_channel_or_404(channel_id)
    event = {
        "title": payload.title,
        "content": payload.content,
        "event_type": payload.event_type,
        "author_id": payload.author_id,
        "author_name": payload.author_name,
        "tags": payload.tags,
        "metadata": payload.metadata,
        "source": "user",
    }
    stored = append_channel_events(channel["channel_id"], [event])
    if not stored:
        raise HTTPException(status_code=400, detail="Event content is empty.")
    notification_from_event(stored[0])
    return {"ok": True, "event": stored[0]}


async def run_channel_seed(channel: dict[str, Any], count: int) -> dict[str, Any]:
    job = begin_generation_job(f"channel_{channel['type']}", channel["channel_id"])
    try:
        raw_reply = await call_chat_model(
            build_channel_seed_messages(channel, count),
            max_tokens=get_settings()["max_tokens"],
            temperature=read_main_llm_config()["temperature"],
        )
    except HTTPException as exc:
        finish_generation_job(job, "error", compact_text(exc.detail, 240))
        raise
    events = parse_channel_seed_events(raw_reply, channel, count)
    stored = append_channel_events(channel["channel_id"], events)
    for event in stored:
        notification_from_event(event)
    finish_generation_job(job, "success")
    return {"ok": True, "channel": channel, "events": stored, "raw_count": len(events)}


@app.post("/api/channels/{channel_id}/seed", response_model=None)
async def api_seed_channel(channel_id: str, payload: ChannelSeedPayload | None = None) -> JSONResponse | dict[str, Any]:
    channel = get_channel_or_404(channel_id)
    count = clamp_int(payload.count if payload else None, 1, 20, channel["seed_count"])
    try:
        return await run_channel_seed(channel, count)
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"ok": False, "error": compact_text(exc.detail, 240)})


@app.post("/api/admin/seed-channel", response_model=None)
async def api_admin_seed_channel(payload: ChannelSeedPayload) -> JSONResponse | dict[str, Any]:
    channel = get_channel_or_404(payload.channel_id)
    existing = get_channel_events(channel["channel_id"])
    if existing and not payload.force:
        return {"ok": True, "channel": channel, "events": existing[: channel["seed_count"]], "skipped": True}
    count = clamp_int(payload.count, 1, 20, channel["seed_count"])
    try:
        return await run_channel_seed(channel, count)
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"ok": False, "error": compact_text(exc.detail, 240)})


@app.get("/api/notifications")
async def api_notifications() -> dict[str, Any]:
    items = get_notifications()
    return {"ok": True, "notifications": items, "unread_count": len([item for item in items if not item["read"]])}


@app.patch("/api/notifications/{notification_id}")
async def api_patch_notification(notification_id: str, payload: NotificationPatchPayload) -> dict[str, Any]:
    safe_id = normalize_id(notification_id)
    rows = get_notifications()
    changed = False
    for item in rows:
        if item["notification_id"] == safe_id:
            if payload.read is not None:
                item["read"] = bool(payload.read)
                changed = True
    if not changed:
        raise HTTPException(status_code=404, detail="Notification not found.")
    save_notifications(rows)
    return {"ok": True, "notifications": get_notifications()}


@app.post("/api/notifications/read-all")
async def api_notifications_read_all() -> dict[str, Any]:
    rows = get_notifications()
    for item in rows:
        item["read"] = True
    save_notifications(rows)
    return {"ok": True, "notifications": get_notifications(), "unread_count": 0}


@app.get("/api/phone/sessions")
async def api_phone_sessions() -> dict[str, Any]:
    return {"ok": True, "sessions": get_phone_sessions(), "roles": get_role_profiles(include_disabled=False)}


@app.post("/api/phone/call", response_model=None)
async def api_phone_call(payload: PhoneCallPayload) -> JSONResponse | dict[str, Any]:
    role = get_phone_role_or_404(payload.role_id)
    sessions = get_phone_sessions()
    session = next((item for item in sessions if item["session_id"] == normalize_id(payload.session_id or "")), None)
    if not session:
        session = {
            "session_id": make_id("call"),
            "role_id": role["role_id"],
            "role_name": role["display_name"],
            "status": "ongoing",
            "started_at": now_iso(),
            "updated_at": now_iso(),
            "lines": [],
        }
    user_line = compact_text(payload.user_line, 500)
    if user_line:
        session["lines"].append(
            {
                "line_id": make_id("line"),
                "speaker": current_user_member()["name"],
                "speaker_id": "user",
                "content": user_line,
                "created_at": now_iso(),
                "source": "user",
            }
        )
    job = begin_generation_job("phone", session["session_id"])
    try:
        raw_reply = await call_chat_model(
            build_phone_call_messages(role, session, user_line),
            max_tokens=min(get_settings()["max_tokens"], 600),
            temperature=read_main_llm_config()["temperature"],
        )
    except HTTPException as exc:
        finish_generation_job(job, "error", compact_text(exc.detail, 240))
        return JSONResponse(status_code=exc.status_code, content={"ok": False, "error": compact_text(exc.detail, 240), "session": session})
    lines, call_state = parse_phone_lines(raw_reply, role)
    session["lines"].extend(lines)
    session["status"] = call_state
    session["updated_at"] = now_iso()
    remaining = [item for item in sessions if item["session_id"] != session["session_id"]]
    saved = save_phone_sessions([session, *remaining])
    finish_generation_job(job, "success")
    if lines:
        add_notification("Phone", f"{role['display_name']}: {lines[-1]['content'][:160]}", source="phone")
    return {"ok": True, "session": saved[0], "lines": lines}


@app.get("/api/export")
async def api_export() -> JSONResponse:
    groups = get_groups()
    payload = {
        "exported_at": now_iso(),
        "settings": get_settings(),
        "role_profiles": get_role_profiles(include_disabled=True),
        "automation_state": get_automation_state(),
        "prompt_blocks": get_prompt_blocks(),
        "app_registry": get_app_registry(include_disabled=True),
        "channels": get_channels(include_disabled=True),
        "channel_events": {channel["channel_id"]: get_channel_events(channel["channel_id"]) for channel in get_channels(include_disabled=True)},
        "notifications": get_notifications(),
        "phone_sessions": get_phone_sessions(),
        "generation_state": get_generation_state(),
        "sticker_packs": sticker_pack_summaries(),
        "groups": groups,
        "messages": {group["group_id"]: get_messages(group["group_id"]) for group in groups},
    }
    return JSONResponse(
        content=payload,
        headers={"Content-Disposition": 'attachment; filename="fantareal-mobile-chat-export.json"'},
    )


def admin_model_status() -> dict[str, Any]:
    config = read_main_llm_config()
    api_url = build_api_url(config["base_url"], "chat/completions")
    return {
        "configured": bool(api_url and config["model"]),
        "base_url_configured": bool(api_url),
        "api_key_configured": bool(config["api_key"]),
        "model": config["model"],
        "temperature": config["temperature"],
        "request_timeout": config["request_timeout"],
    }


def admin_latest_error(groups: list[dict[str, Any]]) -> dict[str, str] | None:
    latest: dict[str, str] | None = None
    for group in groups:
        for message in get_messages(group["group_id"]):
            if message.get("type") != "error":
                continue
            row = {
                "group_id": group["group_id"],
                "group_name": group["name"],
                "content": compact_text(message.get("content"), 240),
                "created_at": compact_text(message.get("created_at"), 80),
            }
            if latest is None or row["created_at"] > latest.get("created_at", ""):
                latest = row
    return latest


def admin_diagnostics() -> dict[str, Any]:
    channels = get_channels(include_disabled=True)
    notifications = get_notifications()
    phone_sessions = get_phone_sessions()
    generation_state = get_generation_state()
    expected_files = {
        "settings": SETTINGS_PATH,
        "groups": GROUPS_PATH,
        "roles": ROLE_PROFILES_PATH,
        "automation": AUTOMATION_STATE_PATH,
        "prompt_blocks": PROMPT_BLOCKS_PATH,
        "app_registry": APP_REGISTRY_PATH,
        "channels": CHANNELS_PATH,
        "notifications": NOTIFICATIONS_PATH,
        "phone_calls": PHONE_CALLS_PATH,
        "generation_state": GENERATION_STATE_PATH,
    }
    try:
        data_dir_label = str(DATA_DIR.relative_to(PROJECT_ROOT))
    except ValueError:
        data_dir_label = str(DATA_DIR)
    return {
        "data_dir": data_dir_label,
        "files": {key: path.exists() for key, path in expected_files.items()},
        "events_dir_exists": EVENTS_DIR.exists(),
        "channel_event_counts": {channel["channel_id"]: len(get_channel_events(channel["channel_id"])) for channel in channels},
        "notification_count": len(notifications),
        "unread_notification_count": len([item for item in notifications if not item["read"]]),
        "phone_session_count": len(phone_sessions),
        "active_generation_jobs": len(generation_state["active_jobs"]),
        "last_generation_jobs": generation_state["last_jobs"][:5],
        "isolation": {
            "writes_main_chat": False,
            "writes_role_card": False,
            "writes_worldbook": False,
            "plugin_data_root": "data/mobile_chat",
        },
    }


@app.get("/api/admin/summary")
async def api_admin_summary() -> dict[str, Any]:
    groups = get_groups()
    roles = get_role_profiles(include_disabled=True)
    stickers = sticker_catalog()
    message_count = sum(len(get_messages(group["group_id"])) for group in groups)
    channels = get_channels(include_disabled=True)
    return {
        "ok": True,
        "settings": get_settings(),
        "group_count": len(groups),
        "message_count": message_count,
        "role_count": len(roles),
        "sticker_count": len(stickers),
        "sticker_pack_count": len(sticker_pack_summaries()),
        "app_count": len(get_app_registry(include_disabled=True)["apps"]),
        "channel_count": len(channels),
        "channel_event_count": sum(len(get_channel_events(channel["channel_id"])) for channel in channels),
        "notification_count": len(get_notifications()),
        "phone_session_count": len(get_phone_sessions()),
        "model_status": admin_model_status(),
        "latest_error": admin_latest_error(groups),
        "generation_state": get_generation_state(),
        "diagnostics": admin_diagnostics(),
        "data_dir": "data/mobile_chat",
    }
