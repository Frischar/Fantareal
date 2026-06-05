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
PARSER_DIAGNOSTICS_PATH = DATA_DIR / "parser_diagnostics.json"
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
REASONING_MODEL_HINTS = ("deepseek-v4", "deepseek-reasoner", "v4-pro", "reason", "r1", "o1", "o3", "o4")
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
DEFAULT_GENERATION_CONTROL_SETTINGS = {
    "paused": False,
    "hourly_limit": 24,
    "retry_limit": 1,
    "cost_notice": True,
    "app_enabled": {
        "group_chat": True,
        "feed": True,
        "forum": True,
        "mail": True,
        "diary": True,
        "calendar": True,
        "phone": True,
        "workbench": True,
    },
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
    "generation_control": DEFAULT_GENERATION_CONTROL_SETTINGS,
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
            "scope": ["group_chat", "feed", "forum", "notification", "mail", "diary", "calendar", "phone", "live"],
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
            "scope": ["group_chat", "feed", "forum", "notification", "mail", "diary", "calendar", "phone", "live"],
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
            "scope": ["feed", "forum", "notification", "mail", "diary", "calendar", "phone", "live"],
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
            "scope": ["group_chat", "feed", "forum", "notification", "mail", "diary", "calendar", "phone", "live"],
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
        {"app_id": "assist", "label": "辅助功能", "subtitle": "人物生成", "icon": "toolbox", "page": "assist", "order": 35, "enabled": True, "stage": "v4.0"},
        {"app_id": "feed", "label": "动态", "subtitle": "角色近况", "icon": "spark", "page": "channel-feed_main", "order": 40, "enabled": True, "stage": "v1.7"},
        {"app_id": "forum", "label": "论坛", "subtitle": "世界讨论板", "icon": "forum", "page": "channel-forum_main", "order": 50, "enabled": True, "stage": "v1.7"},
        {"app_id": "live", "label": "直播", "subtitle": "弹幕与醒目留言", "icon": "live", "page": "channel-live_main", "order": 55, "enabled": True, "stage": "v4.1"},
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
        {"channel_id": "live_main", "type": "live", "label": "直播", "description": "角色直播间、弹幕、醒目留言和贡献榜。", "seed_count": 4, "enabled": True},
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
CHANNEL_TYPES = {"group_chat", "feed", "forum", "notification", "mail", "diary", "calendar", "phone", "live"}
CHANNEL_EVENT_TYPES = {"post", "thread", "reply", "notice", "mail", "diary", "calendar", "call_line", "live", "system"}


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
    generation_control: dict[str, Any] | None = None


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
    identity: str | None = Field(default=None, max_length=160)
    appearance: str | None = Field(default=None, max_length=260)
    summary: str | None = Field(default=None, max_length=500)
    status: str | None = Field(default=None, max_length=80)
    chat_style: str | None = Field(default=None, max_length=500)
    suitable_apps: list[Any] | None = None
    blocked_apps: list[Any] | None = None
    generator_notes: str | None = Field(default=None, max_length=500)
    sticker_preferences: dict[str, Any] | None = None
    auto_speak_weight: float | None = None
    enabled: bool | None = None


class RoleProfilePatchPayload(BaseModel):
    display_name: str | None = Field(default=None, max_length=80)
    source: str | None = Field(default=None, max_length=40)
    source_ref: str | None = Field(default=None, max_length=240)
    aliases: list[Any] | None = None
    avatar: str | None = Field(default=None, max_length=500)
    identity: str | None = Field(default=None, max_length=160)
    appearance: str | None = Field(default=None, max_length=260)
    summary: str | None = Field(default=None, max_length=500)
    status: str | None = Field(default=None, max_length=80)
    chat_style: str | None = Field(default=None, max_length=500)
    suitable_apps: list[Any] | None = None
    blocked_apps: list[Any] | None = None
    generator_notes: str | None = Field(default=None, max_length=500)
    sticker_preferences: dict[str, Any] | None = None
    auto_speak_weight: float | None = None
    enabled: bool | None = None


class RoleGeneratorPayload(BaseModel):
    known_info: str | None = Field(default="", max_length=1000)
    overall_request: str | None = Field(default="", max_length=1000)
    real_name: str | None = Field(default="", max_length=80)
    nickname: str | None = Field(default="", max_length=80)
    identity: str | None = Field(default="", max_length=160)
    impression: str | None = Field(default="", max_length=300)
    hair_color: str | None = Field(default="", max_length=80)
    hairstyle: str | None = Field(default="", max_length=120)
    speech_style: str | None = Field(default="", max_length=240)
    suitable_apps: list[Any] | None = None
    blocked_apps: list[Any] | None = None
    count: int | None = None
    source: str | None = Field(default="role_generator", max_length=40)


class RoleGeneratorSavePayload(BaseModel):
    role: dict[str, Any] | None = None
    roles: list[Any] | None = None


class RoleEventExtractPayload(BaseModel):
    channel_ids: list[Any] | None = None
    limit: int | None = None


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


class ChannelInteractionPayload(BaseModel):
    title: str | None = Field(default=None, max_length=120)
    content: str = Field(default="", max_length=1200)


class ChannelReplyPayload(BaseModel):
    content: str = Field(default="", max_length=800)


class MailReplyPayload(BaseModel):
    content: str = Field(default="", max_length=1000)
    generate_reply: bool | None = True


class LiveMessagePayload(BaseModel):
    content: str = Field(default="", max_length=240)


class WorkbenchRoleDraftPayload(BaseModel):
    role_id: str | None = Field(default=None, max_length=120)
    display_name: str | None = Field(default=None, max_length=80)
    source: str | None = Field(default="current_card", max_length=40)


class WorkbenchGeneratePayload(BaseModel):
    scope: str = Field(default="feed", max_length=40)
    mode: str = Field(default="mock", max_length=20)
    channel_id: str | None = Field(default=None, max_length=120)
    role_id: str | None = Field(default=None, max_length=120)
    user_input: str | None = Field(default="", max_length=1000)
    save: bool | None = False


class NotificationPatchPayload(BaseModel):
    read: bool | None = None


class PhoneCallPayload(BaseModel):
    role_id: str
    user_line: str | None = Field(default="", max_length=500)
    session_id: str | None = Field(default=None, max_length=120)


class PhoneHangupPayload(BaseModel):
    session_id: str = Field(default="", max_length=120)


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
        return json.loads(path.read_text(encoding="utf-8-sig"))
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
        if not PARSER_DIAGNOSTICS_PATH.exists():
            _write_json_unlocked(PARSER_DIAGNOSTICS_PATH, {"schema_version": 1, "items": []})


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



def sanitize_generation_control(raw: Any) -> dict[str, Any]:
    source = raw if isinstance(raw, dict) else {}
    defaults = clone_default(DEFAULT_GENERATION_CONTROL_SETTINGS)
    app_source = source.get("app_enabled") if isinstance(source.get("app_enabled"), dict) else {}
    app_enabled = {
        key: bool(app_source.get(key, defaults["app_enabled"].get(key, True)))
        for key in defaults["app_enabled"]
    }
    return {
        "paused": bool(source.get("paused", defaults["paused"])),
        "hourly_limit": clamp_int(source.get("hourly_limit"), 1, 240, defaults["hourly_limit"]),
        "retry_limit": clamp_int(source.get("retry_limit"), 0, 5, defaults["retry_limit"]),
        "cost_notice": bool(source.get("cost_notice", defaults["cost_notice"])),
        "app_enabled": app_enabled,
    }


def generation_kind_scope(kind: str) -> str:
    safe = compact_text(kind, 80)
    if safe.startswith("channel_"):
        return safe.replace("channel_", "", 1).replace("_interaction", "")
    if safe == "group_chat":
        return "group_chat"
    if safe == "phone":
        return "phone"
    if safe.startswith("workbench"):
        return "workbench"
    return safe or "group_chat"


def assert_generation_allowed(kind: str) -> None:
    control = get_settings().get("generation_control", DEFAULT_GENERATION_CONTROL_SETTINGS)
    scope = generation_kind_scope(kind)
    if control.get("paused"):
        raise HTTPException(status_code=423, detail="Mobile chat generation is paused in admin settings.")
    if control.get("app_enabled", {}).get(scope, True) is False:
        raise HTTPException(status_code=423, detail=f"Generation for {scope} is disabled in admin settings.")
    hourly_limit = clamp_int(control.get("hourly_limit"), 1, 240, DEFAULT_GENERATION_CONTROL_SETTINGS["hourly_limit"])
    recent = [item for item in get_generation_state().get("last_jobs", []) if compact_text(item.get("finished_at"), 13) == compact_text(now_iso(), 13)]
    if len(recent) >= hourly_limit:
        raise HTTPException(status_code=429, detail="Mobile chat hourly generation budget has been reached.")


def generation_control_payload() -> dict[str, Any]:
    return {
        "settings": get_settings().get("generation_control", DEFAULT_GENERATION_CONTROL_SETTINGS),
        "state": get_generation_state(),
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
    generation_control_source = section_source(source, "generation_control")

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
    settings["generation_control"] = sanitize_generation_control(generation_control_source)
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
            "structured_metadata": {"replies": ["author_name", "content", "mood", "floor"]},
            "notes": "Forum thread cards. Thread events may include metadata.replies for compact floor replies.",
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
            "type": "live",
            "root": "events",
            "required_fields": ["event_type", "title", "content", "author_name"],
            "event_types": ["live"],
            "notes": "Live rooms with danmaku, highlight messages, inner thoughts and contributor boards.",
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
    assert_generation_allowed(safe_kind)
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
    for key in ("ui", "generation", "auto_behavior", "stickers", "roles", "groups", "prompt", "generation_control"):
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


def split_compact_values(value: Any, *, limit: int = 12, item_limit: int = 80) -> list[str]:
    source = value
    if isinstance(value, str):
        source = re.split(r"[,，、\n]+", value)
    if not isinstance(source, list):
        return []
    values: list[str] = []
    seen: set[str] = set()
    for item in source:
        text = compact_text(item, item_limit)
        key = role_name_key(text)
        if not text or key in seen:
            continue
        seen.add(key)
        values.append(text)
        if len(values) >= limit:
            break
    return values


def sanitize_role_app_scope(value: Any) -> list[str]:
    return split_compact_values(value, limit=12, item_limit=40)


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
    if source not in {"manual", "current_card", "group_import", "role_generator", "admin_role_generator", "event_extract", "admin_event_extract", "admin_workbench"}:
        source = "manual"
    auto_weight = clamp_float(raw.get("auto_speak_weight"), 0.0, 10.0, 1.0)
    return {
        "role_id": role_id,
        "display_name": display_name,
        "source": source,
        "source_ref": compact_text(raw.get("source_ref"), 240),
        "aliases": sanitize_aliases(raw.get("aliases")),
        "avatar": safe_avatar(raw.get("avatar")),
        "identity": compact_text(raw.get("identity"), 160),
        "appearance": compact_text(raw.get("appearance"), 260),
        "summary": compact_text(raw.get("summary"), 500),
        "status": compact_text(raw.get("status"), 80) or "online",
        "chat_style": compact_text(raw.get("chat_style"), 500),
        "suitable_apps": sanitize_role_app_scope(raw.get("suitable_apps")),
        "blocked_apps": sanitize_role_app_scope(raw.get("blocked_apps")),
        "generator_notes": compact_text(raw.get("generator_notes"), 500),
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


def role_generator_display_name(raw: dict[str, Any], index: int, count: int) -> str:
    base_name = (
        compact_text(raw.get("nickname"), 80)
        or compact_text(raw.get("real_name"), 80)
        or compact_text(raw.get("identity"), 80)
        or compact_text(raw.get("impression"), 80)
    )
    if not base_name:
        fallback_names = ["临时联系人", "论坛路人", "群聊旁观者", "邮件联系人", "日程相关人", "通知发信人", "电话那头的人", "日记线索人", "邻近住户", "店内熟人"]
        base_name = fallback_names[index % len(fallback_names)]
    if count <= 1:
        return base_name[:80]
    return compact_text(f"{base_name} {index + 1}", 80)


def role_generator_notes(raw: dict[str, Any]) -> str:
    rows = [
        ("已知信息", compact_text(raw.get("known_info"), 1000)),
        ("整体要求", compact_text(raw.get("overall_request"), 1000)),
        ("真实姓名", compact_text(raw.get("real_name"), 80)),
        ("网名/昵称", compact_text(raw.get("nickname"), 80)),
        ("身份", compact_text(raw.get("identity"), 160)),
        ("整体印象", compact_text(raw.get("impression"), 300)),
        ("发色", compact_text(raw.get("hair_color"), 80)),
        ("发型", compact_text(raw.get("hairstyle"), 120)),
        ("说话风格", compact_text(raw.get("speech_style"), 240)),
    ]
    return "；".join(f"{label}：{value}" for label, value in rows if value)[:500]


def role_generator_profile(raw: dict[str, Any], index: int, count: int) -> dict[str, Any]:
    display_name = role_generator_display_name(raw, index, count)
    source = normalize_id(raw.get("source"), "role_generator")
    if source not in {"role_generator", "admin_role_generator"}:
        source = "role_generator"
    real_name = compact_text(raw.get("real_name"), 80)
    nickname = compact_text(raw.get("nickname"), 80)
    identity = compact_text(raw.get("identity"), 160)
    impression = compact_text(raw.get("impression"), 300)
    known_info = compact_text(raw.get("known_info"), 1000)
    overall_request = compact_text(raw.get("overall_request"), 1000)
    hair_color = compact_text(raw.get("hair_color"), 80)
    hairstyle = compact_text(raw.get("hairstyle"), 120)
    speech_style = compact_text(raw.get("speech_style"), 240)
    appearance = "；".join(
        item for item in [
            f"发色：{hair_color}" if hair_color else "",
            f"发型：{hairstyle}" if hairstyle else "",
        ] if item
    )
    suitable_apps = sanitize_role_app_scope(raw.get("suitable_apps"))
    blocked_apps = sanitize_role_app_scope(raw.get("blocked_apps"))
    alias_candidates = [item for item in [real_name, nickname] if item and item != display_name]
    summary_parts = [
        identity,
        impression,
        known_info,
        f"整体要求：{overall_request}" if overall_request else "",
        appearance,
    ]
    summary = "；".join(part for part in summary_parts if part)
    style_parts = [
        speech_style,
        f"适合出现：{', '.join(suitable_apps)}" if suitable_apps else "",
        f"避免出现：{', '.join(blocked_apps)}" if blocked_apps else "",
    ]
    base_for_id = normalize_id(nickname or real_name or display_name)
    role_id = normalize_id(f"{base_for_id}_{index + 1}" if count > 1 and base_for_id else base_for_id, make_id("role_generator"))
    return sanitize_role_profile(
        {
            "role_id": role_id,
            "display_name": display_name,
            "source": source,
            "source_ref": "4.0 人物生成器",
            "aliases": alias_candidates,
            "identity": identity,
            "appearance": appearance,
            "summary": summary,
            "status": "online",
            "chat_style": "；".join(part for part in style_parts if part),
            "suitable_apps": suitable_apps,
            "blocked_apps": blocked_apps,
            "generator_notes": role_generator_notes(raw),
            "enabled": True,
            "auto_speak_weight": 1.0,
        },
        index,
    ) or {}


def generate_role_profiles(payload: RoleGeneratorPayload) -> list[dict[str, Any]]:
    raw = payload.model_dump()
    count = clamp_int(raw.get("count"), 1, 10, 1)
    drafts = [role_generator_profile(raw, index, count) for index in range(count)]
    return [draft for draft in drafts if draft]


def unique_role_id(base_role_id: str, existing_ids: set[str]) -> str:
    role_id = normalize_id(base_role_id, make_id("role_generator"))
    if role_id not in existing_ids:
        return role_id
    for suffix in range(2, 100):
        candidate = normalize_id(f"{role_id}_{suffix}", make_id("role_generator"))
        if candidate not in existing_ids:
            return candidate
    return make_id("role_generator")


def save_generated_role_profiles(raw_roles: list[Any], *, source: str = "role_generator") -> list[dict[str, Any]]:
    profiles = get_role_profiles(include_disabled=True)
    existing_ids = {item["role_id"] for item in profiles}
    saved: list[dict[str, Any]] = []
    for index, raw_role in enumerate(raw_roles):
        if not isinstance(raw_role, dict):
            continue
        profile = sanitize_role_profile({**raw_role, "source": raw_role.get("source") or source}, index)
        if not profile:
            continue
        profile["role_id"] = unique_role_id(profile["role_id"], existing_ids)
        profile["created_at"] = now_iso()
        profile["updated_at"] = profile["created_at"]
        existing_ids.add(profile["role_id"])
        profiles.append(profile)
        saved.append(profile)
    if not saved:
        raise HTTPException(status_code=400, detail="请先生成或填写可保存的人物草稿。")
    save_role_profiles(profiles)
    return saved


def decoded_metadata_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    text = compact_text(value, 2000)
    if not text or text[0] not in "[{":
        return value
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return value


def event_role_name_allowed(name: str) -> bool:
    text = compact_text(name, 80)
    if len(text) < 2:
        return False
    lowered = text.casefold()
    blocked = {
        "system",
        "user",
        "admin",
        "ai",
        "bot",
        "assistant",
        "我",
        "你",
        "他",
        "她",
        "ta",
        "用户",
        "系统",
        "小手机",
        "旁白",
        "主播",
        "观众",
        "路人",
        "版务",
        "管理员",
    }
    if lowered in blocked:
        return False
    if re.match(r"^(观众|user|guest|路人|匿名)[\s_-]*\d+$", text, re.IGNORECASE):
        return False
    return True


def event_role_split_names(value: Any) -> list[str]:
    if isinstance(value, list):
        raw_rows = value
    else:
        raw_rows = re.split(r"[,，、/|;；\n]+", compact_text(value, 500))
    names: list[str] = []
    seen: set[str] = set()
    for item in raw_rows:
        name = compact_text(item, 80)
        key = name.casefold()
        if event_role_name_allowed(name) and key not in seen:
            names.append(name)
            seen.add(key)
    return names


def event_role_source_label(channel: dict[str, Any], kind: str) -> str:
    labels = {
        "author": "内容作者",
        "reply": "楼层回复者",
        "mail_reply": "邮件联系人",
        "danmaku": "直播弹幕观众",
        "highlight": "醒目留言用户",
        "contributor": "直播贡献者",
        "related": "相关人物",
    }
    return f"{channel.get('label') or channel.get('type') or '事件'} · {labels.get(kind, kind)}"


def event_role_profile_from_candidate(candidate: dict[str, Any], index: int, source: str) -> dict[str, Any]:
    name = compact_text(candidate.get("name"), 80)
    apps = sorted(candidate.get("apps") or [])
    refs = list(candidate.get("refs") or [])[:6]
    snippets = list(candidate.get("snippets") or [])[:4]
    appearances = list(candidate.get("appearances") or [])[:3]
    identity = compact_text(candidate.get("identity"), 160) or "从小手机事件中提取的边缘角色候选"
    summary_parts = [
        f"出现 {candidate.get('count', 1)} 次",
        "；".join(snippets),
    ]
    summary = compact_text("；".join(part for part in summary_parts if part), 500)
    generator_notes = compact_text("；".join([*refs, *snippets]), 500)
    profile = sanitize_role_profile(
        {
            "role_id": normalize_id(name, f"event_role_{index + 1}"),
            "display_name": name,
            "source": source,
            "source_ref": compact_text(refs[0] if refs else "mobile_chat_events", 240),
            "aliases": [],
            "identity": identity,
            "appearance": "；".join(appearances),
            "summary": summary,
            "status": "online",
            "chat_style": "从既有小手机事件中提取，保存前建议补充说话风格。",
            "suitable_apps": apps,
            "blocked_apps": [],
            "generator_notes": generator_notes,
            "enabled": True,
            "auto_speak_weight": 1.0,
        },
        index,
    )
    return profile or {}


def extract_event_role_profiles(payload: RoleEventExtractPayload | None = None, *, source: str = "event_extract") -> list[dict[str, Any]]:
    payload = payload or RoleEventExtractPayload()
    limit = clamp_int(payload.limit, 1, 30, 12)
    requested_channels = {
        normalize_id(item)
        for item in (payload.channel_ids or [])
        if normalize_id(item)
    }
    existing_names = {role_name_key(item.get("display_name")) for item in get_role_profiles(include_disabled=True)}
    candidates: dict[str, dict[str, Any]] = {}

    def add_candidate(channel: dict[str, Any], event: dict[str, Any], name: Any, kind: str, content: Any = "") -> None:
        display_name = compact_text(name, 80)
        if not event_role_name_allowed(display_name):
            return
        key = role_name_key(display_name)
        if not key or key in existing_names:
            return
        row = candidates.setdefault(
            key,
            {
                "name": display_name,
                "count": 0,
                "apps": set(),
                "refs": [],
                "snippets": [],
                "appearances": [],
                "identity": event_role_source_label(channel, kind),
            },
        )
        row["count"] += 1
        row["apps"].add(channel.get("type") or channel.get("channel_id"))
        ref = compact_text(f"{channel.get('channel_id')}:{event.get('event_id')}:{kind}", 180)
        if ref and ref not in row["refs"]:
            row["refs"].append(ref)
        snippet_source = compact_text(content, 180) or compact_text(event.get("title") or event.get("content"), 180)
        if snippet_source and snippet_source not in row["snippets"]:
            row["snippets"].append(snippet_source)

    for channel in get_channels(include_disabled=False):
        if requested_channels and channel["channel_id"] not in requested_channels:
            continue
        for event in get_channel_events(channel["channel_id"])[:80]:
            add_candidate(channel, event, event.get("author_name"), "author", event.get("title") or event.get("content"))
            metadata = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
            for name in event_role_split_names(decoded_metadata_value(metadata.get("related_people"))):
                add_candidate(channel, event, name, "related", event.get("title") or event.get("content"))
            replies = decoded_metadata_value(metadata.get("replies"))
            if isinstance(replies, list):
                for reply in replies:
                    if isinstance(reply, dict):
                        kind = "mail_reply" if channel.get("type") == "mail" else "reply"
                        add_candidate(channel, event, reply.get("author_name") or reply.get("speaker_name") or reply.get("author"), kind, reply.get("content"))
            for key, kind in (("danmaku", "danmaku"), ("highlights", "highlight")):
                rows = decoded_metadata_value(metadata.get(key))
                if isinstance(rows, list):
                    for item in rows:
                        if isinstance(item, dict):
                            add_candidate(channel, event, item.get("author_name") or item.get("speaker_name") or item.get("author"), kind, item.get("content"))
            contributors = decoded_metadata_value(metadata.get("contributors"))
            if isinstance(contributors, list):
                for item in contributors:
                    if isinstance(item, dict):
                        add_candidate(channel, event, item.get("name") or item.get("author_name") or item.get("user"), "contributor", item.get("note") or item.get("amount"))

    sorted_candidates = sorted(
        candidates.values(),
        key=lambda item: (-int(item.get("count") or 0), compact_text(item.get("name"), 80).casefold()),
    )
    drafts = [event_role_profile_from_candidate(candidate, index, source) for index, candidate in enumerate(sorted_candidates[:limit])]
    return [draft for draft in drafts if draft]


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
        for key in (
            "summary",
            "chat_style",
            "aliases",
            "avatar",
            "identity",
            "appearance",
            "suitable_apps",
            "blocked_apps",
            "generator_notes",
            "sticker_preferences",
            "auto_speak_weight",
            "enabled",
        ):
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
        row["identity"] = compact_text(profile.get("identity"), 160)
        row["appearance"] = compact_text(profile.get("appearance"), 260)
        row["suitable_apps"] = profile.get("suitable_apps", [])
        row["blocked_apps"] = profile.get("blocked_apps", [])
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
        if isinstance(item, (dict, list)):
            continue
        tag = compact_text(item, 32).strip(" #,，;；")
        key = tag.casefold()
        if not tag or key in seen:
            continue
        tags.append(tag)
        seen.add(key)
        if len(tags) >= 12:
            break
    return tags


def sanitize_event_metadata(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    metadata: dict[str, Any] = {}
    for key, raw_value in value.items():
        safe_key = compact_text(key, 40)
        if not safe_key:
            continue
        if isinstance(raw_value, (dict, list)):
            metadata[safe_key] = compact_text(json.dumps(raw_value, ensure_ascii=False), 500)
        else:
            metadata[safe_key] = compact_text(raw_value, 500)
    return metadata


def date_only(value: Any, fallback: str | None = None) -> str:
    text = compact_text(value, 80)
    if re.match(r"^\d{4}-\d{2}-\d{2}", text):
        return text[:10]
    if text:
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            pass
    return (fallback or now_iso())[:10]


def normalize_author_type(value: Any, fallback: str = "role") -> str:
    raw = normalize_id(value, fallback)
    aliases = {
        "passerby": "bystander",
        "random": "bystander",
        "路人": "bystander",
        "moderator": "moderator",
        "mod": "moderator",
        "版主": "moderator",
        "system": "system",
        "user": "user",
        "role": "role",
        "character": "role",
    }
    return aliases.get(raw, raw if raw in {"role", "bystander", "moderator", "system", "user"} else fallback)


def sanitize_forum_replies(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    replies: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            continue
        content = compact_text(item.get("content") or item.get("body") or item.get("text"), 1000)
        if not content:
            continue
        replies.append(
            {
                "reply_id": normalize_id(item.get("reply_id") or item.get("id"), f"reply_{uuid4().hex[:12]}"),
                "floor": clamp_int(item.get("floor"), 1, 999, index + 1),
                "author_id": normalize_id(item.get("author_id") or item.get("speaker_id"), "system"),
                "author_name": compact_text(item.get("author_name") or item.get("speaker_name") or item.get("author"), 80) or "System",
                "author_type": normalize_author_type(item.get("author_type") or item.get("source_type"), "role"),
                "source": normalize_id(item.get("source"), "ai"),
                "content": content,
                "mood": normalize_id(item.get("mood"), ""),
                "created_at": compact_text(item.get("created_at"), 80) or now_iso(),
            }
        )
        if len(replies) >= 20:
            break
    return replies


def sanitize_mail_replies(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    replies: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        content = compact_text(item.get("content") or item.get("body") or item.get("text"), 1000)
        if not content:
            continue
        direction = normalize_id(item.get("direction"), "received")
        if direction not in {"sent", "received"}:
            direction = "received"
        replies.append(
            {
                "reply_id": normalize_id(item.get("reply_id") or item.get("id"), f"mail_reply_{uuid4().hex[:12]}"),
                "author_id": normalize_id(item.get("author_id") or item.get("speaker_id"), "system"),
                "author_name": compact_text(item.get("author_name") or item.get("speaker_name") or item.get("author"), 80) or "System",
                "direction": direction,
                "content": content,
                "mood": normalize_id(item.get("mood"), ""),
                "source": normalize_id(item.get("source"), "ai"),
                "created_at": compact_text(item.get("created_at"), 80) or now_iso(),
            }
        )
        if len(replies) >= 40:
            break
    return replies


def sanitize_live_messages(value: Any, *, limit: int = 80) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        content = compact_text(item.get("content") or item.get("body") or item.get("text"), 240)
        if not content:
            continue
        rows.append(
            {
                "message_id": normalize_id(item.get("message_id") or item.get("id"), f"live_msg_{uuid4().hex[:12]}"),
                "author_name": compact_text(item.get("author_name") or item.get("speaker_name") or item.get("author"), 80) or "观众",
                "author_type": normalize_author_type(item.get("author_type") or item.get("source_type"), "bystander"),
                "content": content,
                "mood": normalize_id(item.get("mood"), ""),
                "amount": compact_text(item.get("amount"), 40),
                "created_at": compact_text(item.get("created_at"), 80) or now_iso(),
            }
        )
        if len(rows) >= limit:
            break
    return rows


def sanitize_live_contributors(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        name = compact_text(item.get("name") or item.get("author_name") or item.get("user"), 80)
        if not name:
            continue
        rows.append(
            {
                "name": name,
                "amount": compact_text(item.get("amount") or item.get("score") or item.get("gift"), 40) or "1",
                "note": compact_text(item.get("note") or item.get("content"), 120),
            }
        )
        if len(rows) >= 12:
            break
    return rows


def sanitize_channel_event(raw: Any, channel: dict[str, Any], index: int = 0) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    content = compact_text(raw.get("content") or raw.get("body"), 2000)
    if not content:
        return None
    event_type = normalize_id(raw.get("event_type") or raw.get("type"), channel["type"])
    if event_type not in CHANNEL_EVENT_TYPES:
        event_type = {"feed": "post", "forum": "thread", "mail": "mail", "diary": "diary", "calendar": "calendar", "live": "live"}.get(channel["type"], "post")
    metadata_source = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    metadata = sanitize_event_metadata(metadata_source)
    if channel["type"] in {"feed", "forum"}:
        replies = sanitize_forum_replies(raw.get("replies") or metadata_source.get("replies"))
        if replies:
            metadata["replies"] = replies
    if channel["type"] == "mail":
        replies = sanitize_mail_replies(raw.get("replies") or metadata_source.get("replies"))
        if replies:
            metadata["replies"] = replies
    if channel["type"] == "calendar":
        metadata["date"] = date_only(metadata_source.get("date") or metadata_source.get("time") or raw.get("created_at"))
        if metadata_source.get("time"):
            metadata["time"] = compact_text(metadata_source.get("time"), 80)
    if channel["type"] == "diary":
        if metadata_source.get("mood"):
            metadata["mood"] = compact_text(metadata_source.get("mood"), 80)
        if metadata_source.get("related_people"):
            metadata["related_people"] = compact_text(metadata_source.get("related_people"), 240)
    if channel["type"] == "live":
        metadata["danmaku"] = sanitize_live_messages(raw.get("danmaku") or metadata_source.get("danmaku"), limit=80)
        metadata["highlights"] = sanitize_live_messages(raw.get("highlights") or metadata_source.get("highlights"), limit=12)
        metadata["contributors"] = sanitize_live_contributors(raw.get("contributors") or metadata_source.get("contributors"))
        metadata["viewers"] = compact_text(metadata_source.get("viewers") or raw.get("viewers"), 40) or str(900 + index * 137)
        metadata["fans"] = compact_text(metadata_source.get("fans") or raw.get("fans"), 40)
        metadata["live_status"] = compact_text(metadata_source.get("live_status") or raw.get("live_status"), 40) or "直播中"
        metadata["inner_thought"] = compact_text(metadata_source.get("inner_thought") or raw.get("inner_thought"), 500)
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
        "metadata": metadata,
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


def save_channel_events(channel_id: str, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    channel = get_channel_or_404(channel_id)
    sanitized = [event for index, item in enumerate(events) if (event := sanitize_channel_event(item, channel, index)) is not None]
    sanitized = sorted(sanitized, key=lambda item: item["created_at"], reverse=True)[:500]
    write_json(channel_events_path(channel["channel_id"]), sanitized)
    return sanitized


def update_channel_event(channel_id: str, event: dict[str, Any]) -> dict[str, Any]:
    channel = get_channel_or_404(channel_id)
    sanitized = sanitize_channel_event(event, channel, 0)
    if not sanitized:
        raise HTTPException(status_code=400, detail="Event content is empty.")
    events = get_channel_events(channel["channel_id"])
    changed = False
    merged: list[dict[str, Any]] = []
    for item in events:
        if item["event_id"] == sanitized["event_id"]:
            merged.append(sanitized)
            changed = True
        else:
            merged.append(item)
    if not changed:
        merged.append(sanitized)
    save_channel_events(channel["channel_id"], merged)
    return sanitized


def find_channel_event_or_404(channel_id: str, event_id: str) -> dict[str, Any]:
    safe_event_id = normalize_id(event_id)
    for event in get_channel_events(channel_id):
        if event["event_id"] == safe_event_id:
            return event
    raise HTTPException(status_code=404, detail="频道内容不存在。")


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
    content_limit = 280 if channel["type"] in {"diary", "live"} else 180 if channel["type"] in {"mail", "calendar"} else 140
    output_rules = [
        f"Generate exactly {count} event(s) for this mobile app channel.",
        "Return compact valid JSON only, with no markdown, no explanation, and no surrounding text.",
        "The root shape must be {\"events\":[...]} and each event must include title, content, author_name, event_type, tags and metadata.",
        f"Use 1-3 short text tags. Keep each title <= 24 Chinese characters and each content <= {content_limit} Chinese characters.",
        "Keep metadata small and JSON-serializable.",
    ]
    if channel["type"] == "forum":
        output_rules.append(
            "For each forum thread, put exactly 2 compact floor replies in metadata.replies; "
            "each reply must include author_name, author_type, source, content, mood and floor. "
            "Mix at least one bystander/random passerby reply with role/moderator replies; each reply content <= 70 Chinese characters."
        )
    if channel["type"] == "calendar":
        output_rules.append(
            "For every calendar event, metadata.date is required in YYYY-MM-DD format; "
            "metadata should also include time, location and participants when useful."
        )
    if channel["type"] == "diary":
        output_rules.append(
            "For diary events, write a richer diary fragment with clear paragraphs; "
            "metadata should include mood, related_people and role_id when known."
        )
    if channel["type"] == "live":
        output_rules.append(
            "For live events, event_type must be live. metadata must include live_status, viewers, fans, inner_thought, "
            "danmaku, highlights and contributors. danmaku/highlights are arrays of compact messages with author_name, author_type, content and mood; "
            "contributors is an array with name, amount and optional note."
        )
    user_text = (
        "\n".join(output_rules)
        + "\nContext JSON:\n"
        + json.dumps(context, ensure_ascii=False, separators=(",", ":"))
    )
    return [{"role": "system", "content": system_text}, {"role": "user", "content": user_text}]


def channel_seed_max_tokens(channel: dict[str, Any], count: int) -> int:
    configured = get_settings()["max_tokens"]
    safe_count = clamp_int(count, 1, 20, 1)
    baseline = 1100 if channel["type"] == "forum" else 1000
    per_event = 380 if channel["type"] == "forum" else 340
    recommended = min(4000, baseline + safe_count * per_event)
    return max(configured, recommended)


def build_channel_interaction_messages(channel: dict[str, Any], event: dict[str, Any], user_content: str, *, mode: str) -> list[dict[str, str]]:
    existing_replies = sanitize_forum_replies(event.get("metadata", {}).get("replies"))
    reply_word = "comments" if channel["type"] == "feed" else "floor replies"
    target_count = 3 if mode == "post" else 2
    context = {
        "channel": channel,
        "mode": mode,
        "event": {
            "title": event.get("title", ""),
            "content": event.get("content", ""),
            "author_name": event.get("author_name", ""),
            "tags": event.get("tags", []),
            "metadata": {"replies": existing_replies[-6:]},
        },
        "user_content": user_content,
        "mobile_context": summarize_mobile_context(),
    }
    system_text = assembled_prompt_text(channel["type"]) or system_prompt_text()
    source_rule = (
        "Generate exactly {count} compact character {reply_word}."
        if channel["type"] == "feed"
        else "Generate exactly {count} compact forum floor replies mixing roles, random bystanders and optionally a moderator/System voice."
    ).format(count=target_count, reply_word=reply_word)
    user_text = (
        f"The user just {'published this event' if mode == 'post' else 'replied to this event'} in the {channel['type']} app. "
        f"{source_rule}\n"
        "Return valid JSON only, root shape {\"replies\":[...]}. "
        "Each reply must include author_name, author_type, source, content, mood and floor. "
        "Keep each content <= 70 Chinese characters, in-character, varied, and directly responsive to the user's content. "
        "Valid author_type values: role, bystander, moderator, system. Bystanders must not be treated as saved character profiles. "
        "Do not mention system prompts or plugin internals.\n"
        "Context JSON:\n"
        + json.dumps(context, ensure_ascii=False, separators=(",", ":"))
    )
    return [{"role": "system", "content": system_text}, {"role": "user", "content": user_text}]


def parse_channel_interaction_replies(raw: str, channel: dict[str, Any], start_floor: int, count: int) -> list[dict[str, Any]]:
    raw_replies, parse_error = parse_model_json_output(
        raw,
        scope=f"channel_{channel['type']}_interaction",
        schema="replies",
        root_key="replies",
        target_id=channel["channel_id"],
    )
    if parse_error:
        return []
    if isinstance(raw_replies, dict):
        raw_replies = [raw_replies]
    if not isinstance(raw_replies, list):
        record_parser_diagnostic(f"channel_{channel['type']}_interaction", "replies", channel["channel_id"], "replies_not_list", raw)
        raw_replies = []
    prepared: list[dict[str, Any]] = []
    for offset, item in enumerate(raw_replies[:count]):
        if not isinstance(item, dict):
            continue
        prepared.append({**item, "floor": start_floor + offset})
    replies = sanitize_forum_replies(prepared)
    if replies:
        return replies
    record_parser_diagnostic(
        f"channel_{channel['type']}_interaction",
        "replies",
        channel["channel_id"],
        "no_valid_replies",
        raw,
    )
    fallback_content = "角色暂时没有接上话，可以稍后重试生成互动。"
    fallback = [{"floor": start_floor, "author_name": "System", "content": fallback_content, "mood": "fallback"}]
    return sanitize_forum_replies(fallback)


async def generate_channel_replies(channel: dict[str, Any], event: dict[str, Any], user_content: str, *, mode: str) -> list[dict[str, Any]]:
    existing = sanitize_forum_replies(event.get("metadata", {}).get("replies"))
    start_floor = len(existing) + 1
    count = 3 if mode == "post" else 2
    job = begin_generation_job(f"channel_{channel['type']}_interaction", channel["channel_id"])
    try:
        raw_reply = await call_chat_model(
            build_channel_interaction_messages(channel, event, user_content, mode=mode),
            max_tokens=min(1800, max(get_settings()["max_tokens"], 900)),
            temperature=read_main_llm_config()["temperature"],
        )
    except HTTPException as exc:
        finish_generation_job(job, "error", compact_text(exc.detail, 240))
        raise
    replies = parse_channel_interaction_replies(raw_reply, channel, start_floor, count)
    if not replies:
        finish_generation_job(job, "error", "parser_no_valid_replies")
        raise HTTPException(status_code=502, detail="模型返回内容无法解析，请查看后台 diagnostics。")
    finish_generation_job(job, "success")
    return replies


async def attach_generated_channel_replies(channel: dict[str, Any], event: dict[str, Any], user_content: str, *, mode: str) -> dict[str, Any]:
    replies = await generate_channel_replies(channel, event, user_content, mode=mode)
    metadata = dict(event.get("metadata") or {})
    existing = sanitize_forum_replies(metadata.get("replies"))
    metadata["replies"] = sanitize_forum_replies([*existing, *replies])
    event["metadata"] = metadata
    event["updated_at"] = now_iso()
    return update_channel_event(channel["channel_id"], event)


def build_mail_reply_messages(event: dict[str, Any], user_content: str) -> list[dict[str, str]]:
    context = {
        "mail": {
            "title": event.get("title", ""),
            "content": event.get("content", ""),
            "author_name": event.get("author_name", ""),
            "metadata": event.get("metadata", {}),
        },
        "user_reply": user_content,
        "mobile_context": summarize_mobile_context(),
        "output_schema": {
            "replies": [
                {
                    "author_name": event.get("author_name", "System"),
                    "direction": "received",
                    "content": "short reply mail content",
                    "mood": "calm",
                }
            ]
        },
    }
    system_text = assembled_prompt_text("mail") or system_prompt_text()
    user_text = (
        "Continue this in-world email thread after the user sends a reply. "
        "Return valid JSON only, root shape {\"replies\":[...]}. "
        "Generate exactly 1 received reply from the original sender or a relevant mail contact. "
        "Each reply must include author_name, direction, content and mood. Keep content <= 220 Chinese characters. "
        "Do not mention plugins, APIs, prompts, or JSON.\n"
        "Context JSON:\n"
        + json.dumps(context, ensure_ascii=False, separators=(",", ":"))
    )
    return [{"role": "system", "content": system_text}, {"role": "user", "content": user_text}]


def parse_mail_replies(raw: str, event: dict[str, Any]) -> list[dict[str, Any]]:
    raw_replies, parse_error = parse_model_json_output(
        raw,
        scope="mail_reply",
        schema="replies",
        root_key="replies",
        target_id=event["event_id"],
    )
    if parse_error:
        return []
    if isinstance(raw_replies, dict):
        raw_replies = [raw_replies]
    if not isinstance(raw_replies, list):
        record_parser_diagnostic("mail_reply", "replies", event["event_id"], "replies_not_list", raw)
        return []
    prepared = []
    for item in raw_replies[:1]:
        if not isinstance(item, dict):
            continue
        prepared.append(
            {
                **item,
                "direction": "received",
                "author_id": normalize_id(item.get("author_id") or event.get("author_id"), event.get("author_id") or "mail_sender"),
                "author_name": compact_text(item.get("author_name") or event.get("author_name"), 80) or "System",
                "source": "ai",
            }
        )
    replies = sanitize_mail_replies(prepared)
    if not replies:
        record_parser_diagnostic("mail_reply", "replies", event["event_id"], "no_valid_replies", raw)
    return replies


async def generate_mail_reply(event: dict[str, Any], user_content: str) -> list[dict[str, Any]]:
    job = begin_generation_job("mail_reply", event["event_id"])
    try:
        raw_reply = await call_chat_model(
            build_mail_reply_messages(event, user_content),
            max_tokens=min(1600, max(get_settings()["max_tokens"], 900)),
            temperature=read_main_llm_config()["temperature"],
        )
    except HTTPException as exc:
        finish_generation_job(job, "error", compact_text(exc.detail, 240))
        raise
    replies = parse_mail_replies(raw_reply, event)
    if not replies:
        finish_generation_job(job, "error", "parser_no_valid_replies")
        raise HTTPException(status_code=502, detail="模型返回邮件回复无法解析，请查看后台 diagnostics。")
    finish_generation_job(job, "success")
    return replies


def parse_channel_seed_events(raw: str, channel: dict[str, Any], count: int) -> list[dict[str, Any]]:
    raw_events, parse_error = parse_model_json_output(
        raw,
        scope=f"channel_{channel['type']}_seed",
        schema="events",
        root_key="events",
        target_id=channel["channel_id"],
    )
    if parse_error:
        return []
    if isinstance(raw_events, dict):
        raw_events = [raw_events]
    if not isinstance(raw_events, list):
        record_parser_diagnostic(f"channel_{channel['type']}_seed", "events", channel["channel_id"], "events_not_list", raw)
        raw_events = []
    events = [event for index, item in enumerate(raw_events[:count]) if (event := sanitize_channel_event(item, channel, index)) is not None]
    if events:
        return events
    record_parser_diagnostic(f"channel_{channel['type']}_seed", "events", channel["channel_id"], "no_valid_events", raw)
    return []


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
        "ended_by": normalize_id(raw.get("ended_by"), ""),
        "ended_at": compact_text(raw.get("ended_at"), 80),
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


def phone_role_candidates() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add_role(role_id: Any, name: Any, summary: Any = "", avatar: Any = "", chat_style: Any = "", status: Any = "") -> None:
        safe_id = normalize_id(role_id)
        display_name = compact_text(name, 80)
        if not safe_id or not display_name or safe_id in seen:
            return
        rows.append(
            {
                "role_id": safe_id,
                "display_name": display_name,
                "summary": compact_text(summary, 1000),
                "avatar": safe_avatar(avatar),
                "chat_style": compact_text(chat_style, 500),
                "status": compact_text(status, 300),
                "enabled": True,
            }
        )
        seen.add(safe_id)

    for profile in get_role_profiles(include_disabled=False):
        add_role(profile["role_id"], profile["display_name"], profile.get("summary"), profile.get("avatar"), profile.get("chat_style"), profile.get("status"))
    for member in available_role_members().get("roles", []):
        add_role(member.get("role_id"), member.get("name"), member.get("summary"), member.get("avatar"))
    for group in get_groups():
        for member in group.get("members", []):
            if member.get("type") == "character":
                add_role(member.get("role_id"), member.get("name"), member.get("summary"), member.get("avatar"))
    return sorted(rows, key=lambda item: item["display_name"].casefold())


def get_phone_role_or_404(role_id: str) -> dict[str, Any]:
    safe_role_id = normalize_id(role_id)
    role = next((item for item in phone_role_candidates() if item["role_id"] == safe_role_id), None)
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
        "Return JSON only with lines and call_state. Return 1-3 compact role lines when the role naturally continues speaking. "
        "If the role naturally ends the call, set call_state to ended and make the final line sound like a real phone goodbye.\n"
        + json.dumps(context, ensure_ascii=False, indent=2)
    )
    return [{"role": "system", "content": system_text}, {"role": "user", "content": user_text}]


def parse_phone_lines(raw: str, role: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    payload, parse_error = parse_model_json_output(
        raw,
        scope="phone",
        schema="lines",
        root_key="lines",
        target_id=role["role_id"],
    )
    if parse_error:
        return [], "ongoing"
    raw_lines = payload.get("lines", []) if isinstance(payload, dict) else payload
    if isinstance(raw_lines, dict):
        raw_lines = [raw_lines]
    if not isinstance(raw_lines, list):
        record_parser_diagnostic("phone", "lines", role["role_id"], "lines_not_list", raw)
        raw_lines = []
    lines: list[dict[str, Any]] = []
    for index, item in enumerate(raw_lines[:3]):
        if not isinstance(item, dict):
            continue
        item = {**item, "speaker": item.get("speaker") or role["display_name"], "speaker_id": role["role_id"], "source": "ai"}
        line = sanitize_phone_line(item, index)
        if line:
            lines.append(line)
    if not lines:
        record_parser_diagnostic("phone", "lines", role["role_id"], "no_valid_lines", raw)
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


def should_request_low_reasoning(model: str) -> bool:
    normalized = compact_text(model, 160).lower()
    return any(hint in normalized for hint in REASONING_MODEL_HINTS)


def chat_model_extra_payload(config: dict[str, Any]) -> dict[str, Any]:
    if should_request_low_reasoning(config.get("model", "")):
        return {"reasoning_effort": "low"}
    return {}


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
    payload.update(chat_model_extra_payload(config))
    try:
        async with httpx.AsyncClient(timeout=float(config["request_timeout"])) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code in {400, 422} and "reasoning_effort" in payload:
                retry_payload = dict(payload)
                retry_payload.pop("reasoning_effort", None)
                response = await client.post(url, headers=headers, json=retry_payload)
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
        message = data["choices"][0]["message"]
        content = message.get("content")
        reasoning_content = message.get("reasoning_content") or message.get("reasoning")
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(status_code=502, detail="模型服务返回格式不兼容 Chat Completions。") from exc
    text = str(content or "").strip()
    if not text:
        if reasoning_content:
            raise HTTPException(status_code=502, detail="模型只返回了推理内容，未返回可用正文；请重试或调高输出 token。")
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


def escape_json_string_newlines(text: str) -> str:
    result: list[str] = []
    in_string = False
    escaped = False
    for char in text:
        if escaped:
            result.append(char)
            escaped = False
            continue
        if char == "\\" and in_string:
            result.append(char)
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            result.append(char)
            continue
        if in_string and char in "\r\n":
            result.append("\\n")
            continue
        result.append(char)
    return "".join(result)


def json_text_candidates(text: str) -> list[str]:
    cleaned = strip_json_fence(text)
    candidates = [cleaned]
    if "{" in cleaned and "}" in cleaned:
        candidates.append(cleaned[cleaned.find("{") : cleaned.rfind("}") + 1])
    if "[" in cleaned and "]" in cleaned:
        candidates.append(cleaned[cleaned.find("[") : cleaned.rfind("]") + 1])
    rows: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        candidate = candidate.strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        rows.append(candidate)
    return rows


def loads_json_lenient(text: str) -> Any:
    for candidate in json_text_candidates(text):
        variants = [
            candidate,
            escape_json_string_newlines(candidate),
            re.sub(r",\s*([}\]])", r"\1", candidate),
            re.sub(r",\s*([}\]])", r"\1", escape_json_string_newlines(candidate)),
        ]
        for variant in variants:
            try:
                return json.loads(variant)
            except ValueError:
                continue
    return None



def parse_payload_shape(payload: Any, root_key: str) -> Any:
    if isinstance(payload, dict):
        for key in (root_key, "messages", "events", "replies", "lines", "items", "data", "result", "results"):
            value = payload.get(key)
            if value is not None:
                return value
        return payload
    return payload


def get_parser_diagnostics() -> list[dict[str, Any]]:
    ensure_runtime_data()
    payload = read_json(PARSER_DIAGNOSTICS_PATH, {"schema_version": 1, "items": []})
    rows = payload.get("items", []) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        rows = []
    sanitized: list[dict[str, Any]] = []
    for row in rows[:80]:
        if not isinstance(row, dict):
            continue
        sanitized.append(
            {
                "diagnostic_id": normalize_id(row.get("diagnostic_id"), f"parse_{uuid4().hex[:10]}"),
                "created_at": compact_text(row.get("created_at"), 80) or now_iso(),
                "scope": compact_text(row.get("scope"), 80),
                "schema": compact_text(row.get("schema"), 80),
                "target_id": compact_text(row.get("target_id"), 120),
                "reason": compact_text(row.get("reason"), 240),
                "raw_excerpt": compact_text(row.get("raw_excerpt"), 500),
            }
        )
    return sanitized


def record_parser_diagnostic(scope: str, schema: str, target_id: str, reason: str, raw: str) -> None:
    rows = get_parser_diagnostics()
    rows.insert(
        0,
        {
            "diagnostic_id": make_id("parse"),
            "created_at": now_iso(),
            "scope": compact_text(scope, 80),
            "schema": compact_text(schema, 80),
            "target_id": compact_text(target_id, 120),
            "reason": compact_text(reason, 240),
            "raw_excerpt": compact_text(strip_json_fence(raw), 500),
        },
    )
    write_json(PARSER_DIAGNOSTICS_PATH, {"schema_version": 1, "items": rows[:80]})


def parse_model_json_output(raw: str, *, scope: str, schema: str, root_key: str, target_id: str = "") -> tuple[Any, str]:
    cleaned = strip_json_fence(raw)
    payload = loads_json_lenient(cleaned)
    if payload is None:
        record_parser_diagnostic(scope, schema, target_id, "json_parse_failed", raw)
        return None, "json_parse_failed"
    shaped = parse_payload_shape(payload, root_key)
    return shaped, ""


def first_ai_member(group: dict[str, Any]) -> dict[str, str] | None:
    return next((item for item in group["members"] if item["type"] == "character"), None)


def parse_model_mobile_messages(raw: str, group: dict[str, Any]) -> list[dict[str, Any]]:
    raw_messages, parse_error = parse_model_json_output(
        raw,
        scope="group_chat",
        schema="messages",
        root_key="messages",
        target_id=group["group_id"],
    )
    if parse_error:
        return []
    if isinstance(raw_messages, dict):
        raw_messages = [raw_messages]
    if not isinstance(raw_messages, list):
        record_parser_diagnostic("group_chat", "messages", group["group_id"], "messages_not_list", raw)
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


@app.get("/chat", response_class=HTMLResponse)
async def chat_index(request: Request) -> HTMLResponse:
    ensure_runtime_data()
    return templates.TemplateResponse(request, "chat.html", {"settings": get_settings()})


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


@app.delete("/api/admin/roles/{role_id}/purge")
async def api_delete_role(role_id: str) -> dict[str, Any]:
    safe_role_id = normalize_id(role_id)
    profiles = get_role_profiles(include_disabled=True)
    next_profiles = [item for item in profiles if item["role_id"] != safe_role_id]
    if len(next_profiles) == len(profiles):
        raise HTTPException(status_code=404, detail="角色不存在。")
    save_role_profiles(next_profiles)
    return {"ok": True, "deleted_role_id": safe_role_id, "roles": get_role_profiles(include_disabled=True)}


@app.post("/api/admin/roles/sync-current-card")
async def api_sync_current_card_roles() -> dict[str, Any]:
    return {"ok": True, "roles": sync_current_card_profiles()}


@app.post("/api/admin/roles/import-from-groups")
async def api_import_group_roles() -> dict[str, Any]:
    return {"ok": True, "roles": import_group_members_to_profiles()}


@app.post("/api/role-generator/draft")
async def api_role_generator_draft(payload: RoleGeneratorPayload) -> dict[str, Any]:
    drafts = generate_role_profiles(payload)
    return {"ok": True, "draft": drafts[0] if drafts else None, "drafts": drafts}


@app.post("/api/admin/role-generator/draft")
async def api_admin_role_generator_draft(payload: RoleGeneratorPayload) -> dict[str, Any]:
    drafts = generate_role_profiles(RoleGeneratorPayload(**{**payload.model_dump(), "source": "admin_role_generator"}))
    return {"ok": True, "draft": drafts[0] if drafts else None, "drafts": drafts}


@app.post("/api/role-generator/extract-events")
async def api_role_generator_extract_events(payload: RoleEventExtractPayload | None = None) -> dict[str, Any]:
    drafts = extract_event_role_profiles(payload, source="event_extract")
    return {"ok": True, "draft": drafts[0] if drafts else None, "drafts": drafts}


@app.post("/api/admin/role-generator/extract-events")
async def api_admin_role_generator_extract_events(payload: RoleEventExtractPayload | None = None) -> dict[str, Any]:
    drafts = extract_event_role_profiles(payload, source="admin_event_extract")
    return {"ok": True, "draft": drafts[0] if drafts else None, "drafts": drafts}


@app.post("/api/role-generator/save")
async def api_role_generator_save(payload: RoleGeneratorSavePayload) -> dict[str, Any]:
    raw_roles = payload.roles if isinstance(payload.roles, list) else [payload.role]
    saved = save_generated_role_profiles(raw_roles, source="role_generator")
    return {"ok": True, "saved": saved, "roles": get_role_profiles(include_disabled=True), "available": available_role_members()["roles"]}


@app.post("/api/admin/role-generator/save")
async def api_admin_role_generator_save(payload: RoleGeneratorSavePayload) -> dict[str, Any]:
    raw_roles = payload.roles if isinstance(payload.roles, list) else [payload.role]
    saved = save_generated_role_profiles(raw_roles, source="admin_role_generator")
    return {"ok": True, "saved": saved, "roles": get_role_profiles(include_disabled=True), "available": available_role_members()["roles"]}


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
        if not ai_messages:
            error_message = {
                "message_id": make_id("msg"),
                "speaker_id": "system",
                "speaker_name": "系统",
                "type": "error",
                "content": "模型返回内容无法解析，请查看后台 diagnostics。",
                "created_at": now_iso(),
                "source": "system",
            }
            stored_error = append_group_messages(safe_group_id, [error_message])
            finish_generation_job(job, "error", "parser_no_valid_messages")
            return JSONResponse(status_code=502, content={"ok": False, "user_message": user_message, "messages": stored_error, "error": error_message["content"]})
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
        if not ai_messages:
            error_message = {
                "message_id": make_id("msg"),
                "speaker_id": "system",
                "speaker_name": "系统",
                "type": "error",
                "content": "模型返回内容无法解析，请查看后台 diagnostics。",
                "created_at": now_iso(),
                "source": "system",
            }
            stored_error = append_group_messages(safe_group_id, [error_message])
            finish_generation_job(job, "error", "parser_no_valid_messages")
            return JSONResponse(status_code=502, content={"ok": False, "messages": stored_error, "error": error_message["content"]})
        stored_messages = append_group_messages(safe_group_id, ai_messages)
        finish_generation_job(job, "success")
        return {"ok": True, "messages": stored_messages}


def model_status_deep() -> dict[str, Any]:
    config = read_main_llm_config()
    route = read_route_forwarding_fallback()
    return {
        "provider": "route_forwarding" if route.get("base_url") and route.get("base_url") == config.get("base_url") else "main_settings",
        "base_url": config.get("base_url", ""),
        "model": config.get("model", ""),
        "temperature": config.get("temperature"),
        "request_timeout": config.get("request_timeout"),
        "api_key_configured": bool(config.get("api_key")),
        "reasoning_effort": chat_model_extra_payload(config).get("reasoning_effort", "default"),
        "route_forwarding_available": bool(route.get("base_url")),
    }


def workbench_overview() -> dict[str, Any]:
    return {
        "model": model_status_deep(),
        "settings_generation": get_settings().get("generation", {}),
        "prompt_scopes": sorted(CHANNEL_TYPES),
        "schemas": channel_schema_catalog(),
        "recent_parser_diagnostics": get_parser_diagnostics()[:8],
        "generation_state": get_generation_state(),
    }


def role_draft_from_source(payload: WorkbenchRoleDraftPayload) -> dict[str, Any]:
    role_id = normalize_id(payload.role_id or "")
    display_name = compact_text(payload.display_name, 80)
    candidates = get_role_profiles(include_disabled=True)
    candidates.extend(current_card_profiles())
    selected = None
    if role_id:
        selected = next((item for item in candidates if normalize_id(item.get("role_id") or item.get("id")) == role_id), None)
    if not selected and display_name:
        selected = next((item for item in candidates if role_name_key(item.get("display_name") or item.get("name")) == role_name_key(display_name)), None)
    if not selected and candidates:
        selected = candidates[0]
    source_name = selected.get("display_name") or selected.get("name") if isinstance(selected, dict) else display_name
    source_summary = selected.get("summary") or selected.get("description") or selected.get("status") if isinstance(selected, dict) else ""
    draft = {
        "role_id": normalize_id(selected.get("role_id") or selected.get("id") or source_name, f"role_{uuid4().hex[:8]}") if isinstance(selected, dict) else normalize_id(source_name, f"role_{uuid4().hex[:8]}"),
        "display_name": compact_text(source_name, 80) or "未命名角色",
        "source": "workbench_draft",
        "source_ref": compact_text(payload.source, 120) or "current_card",
        "aliases": selected.get("aliases", []) if isinstance(selected, dict) and isinstance(selected.get("aliases"), list) else [],
        "avatar": selected.get("avatar", "") if isinstance(selected, dict) else "",
        "summary": compact_text(source_summary, 500) or "由工作台生成的角色草稿，请补充角色简介。",
        "status": compact_text(selected.get("status"), 80) if isinstance(selected, dict) else "",
        "chat_style": compact_text(selected.get("chat_style"), 500) if isinstance(selected, dict) else "语气自然，回应简洁，贴合角色设定。",
        "sticker_preferences": selected.get("sticker_preferences", {"preferred_tags": [], "blocked_tags": []}) if isinstance(selected, dict) else {"preferred_tags": [], "blocked_tags": []},
        "auto_speak_weight": clamp_float(selected.get("auto_speak_weight") if isinstance(selected, dict) else 1, 0.0, 5.0, 1.0),
        "enabled": True,
    }
    return sanitize_role_profile(draft, 0) or draft


def build_workbench_mock_payload(scope: str, user_input: str) -> dict[str, Any]:
    now = now_iso()
    if scope == "phone":
        return {"lines": [{"speaker": "测试角色", "content": "电话已接通。", "mood": "calm"}], "call_state": "ongoing"}
    if scope == "group_chat":
        return {"messages": [{"speaker": "测试角色", "type": "text", "content": compact_text(user_input, 80) or "收到测试消息。"}]}
    if scope in {"feed", "forum", "mail", "diary", "calendar", "live"}:
        return {
            "events": [
                {
                    "title": f"{scope} 测试内容",
                    "content": compact_text(user_input, 120) or "这是一条工作台测试内容。",
                    "author_name": "测试角色",
                    "event_type": {"forum": "thread", "mail": "mail", "diary": "diary", "calendar": "calendar", "live": "live"}.get(scope, "post"),
                    "tags": ["workbench", "test"],
                    "metadata": {"created_at": now, "replies": [] if scope == "forum" else None},
                }
            ]
        }
    return {"result": compact_text(user_input, 200)}


def workbench_channel_for_scope(scope: str, channel_id: str = "") -> dict[str, Any]:
    safe_channel_id = normalize_id(channel_id)
    if safe_channel_id:
        channel = get_channel_or_404(safe_channel_id)
        if channel["type"] != scope:
            raise HTTPException(status_code=400, detail="选择的频道类型与 scope 不一致。")
        return channel
    channel = next((item for item in get_channels(include_disabled=False) if item["type"] == scope), None)
    if not channel:
        raise HTTPException(status_code=404, detail="没有可用的频道用于该 scope。")
    return channel


async def run_workbench_generation(payload: WorkbenchGeneratePayload) -> dict[str, Any]:
    scope = normalize_id(payload.scope, "feed")
    mode = normalize_id(payload.mode, "mock")
    user_input = compact_text(payload.user_input, 1000)
    save_result = bool(payload.save)
    if scope not in CHANNEL_TYPES:
        raise HTTPException(status_code=400, detail="不支持的 scope。")
    if mode not in {"mock", "real"}:
        raise HTTPException(status_code=400, detail="不支持的生成模式。")

    channel_scopes = {"feed", "forum", "mail", "diary", "calendar", "live"}
    if mode == "mock":
        parsed = build_workbench_mock_payload(scope, user_input)
        saved = False
        channel = None
        if save_result and scope in channel_scopes:
            channel = workbench_channel_for_scope(scope, payload.channel_id or "")
            events = parsed.get("events", []) if isinstance(parsed, dict) else []
            stored = append_channel_events(channel["channel_id"], events)
            for event in stored:
                notification_from_event(event)
            parsed = {"events": stored}
            saved = bool(stored)
        return {"mode": "mock", "scope": scope, "channel": channel, "parsed": parsed, "saved": saved}

    job = begin_generation_job("workbench", scope)
    try:
        if scope in channel_scopes:
            channel = workbench_channel_for_scope(scope, payload.channel_id or "")
            raw_reply = await call_chat_model(
                build_channel_seed_messages(channel, 1),
                max_tokens=channel_seed_max_tokens(channel, 1),
                temperature=read_main_llm_config()["temperature"],
            )
            events = parse_channel_seed_events(raw_reply, channel, 1)
            if not events:
                raise HTTPException(status_code=502, detail="模型返回内容无法解析，请查看后台 diagnostics。")
            saved = False
            if save_result:
                stored = append_channel_events(channel["channel_id"], events)
                for event in stored:
                    notification_from_event(event)
                events = stored
                saved = bool(stored)
            finish_generation_job(job, "success")
            return {"mode": "real", "scope": scope, "channel": channel, "parsed": {"events": events}, "saved": saved}
        if scope == "phone":
            candidates = phone_role_candidates()
            role_id = payload.role_id or (candidates[0]["role_id"] if candidates else "")
            role = get_phone_role_or_404(role_id)
            session = {
                "session_id": make_id("calltest"),
                "role_id": role["role_id"],
                "role_name": role["display_name"],
                "status": "ongoing",
                "lines": [],
            }
            raw_reply = await call_chat_model(
                build_phone_call_messages(role, session, user_input or "你好，可以接通吗？"),
                max_tokens=min(get_settings()["max_tokens"], 600),
                temperature=read_main_llm_config()["temperature"],
            )
            lines, call_state = parse_phone_lines(raw_reply, role)
            finish_generation_job(job, "success")
            return {"mode": "real", "scope": scope, "parsed": {"lines": lines, "call_state": call_state}, "saved": False}
        raise HTTPException(status_code=400, detail="该 scope 暂不支持真实生成。")
    except HTTPException as exc:
        finish_generation_job(job, "error", compact_text(exc.detail, 240))
        raise






def channel_event_admin_rows(limit: int = 8) -> dict[str, Any]:
    channels = get_channels(include_disabled=True)
    rows: dict[str, Any] = {}
    for channel in channels:
        events = get_channel_events(channel["channel_id"])
        fallback = [item for item in events if "fallback" in item.get("tags", []) or item.get("source") == "fallback"]
        workbench = [item for item in events if "workbench" in item.get("tags", []) or item.get("source") == "workbench"]
        rows[channel["channel_id"]] = {
            "channel_id": channel["channel_id"],
            "label": channel["label"],
            "type": channel["type"],
            "count": len(events),
            "fallback_count": len(fallback),
            "workbench_count": len(workbench),
            "recent": [
                {
                    "event_id": item["event_id"],
                    "title": item["title"],
                    "author_name": item["author_name"],
                    "source": item.get("source", ""),
                    "tags": item.get("tags", []),
                    "created_at": item.get("created_at", ""),
                }
                for item in events[:limit]
            ],
        }
    return rows


def notification_invalid_source_ids() -> set[str]:
    valid_pairs = {
        (channel["channel_id"], event["event_id"])
        for channel in get_channels(include_disabled=True)
        for event in get_channel_events(channel["channel_id"])
    }
    invalid: set[str] = set()
    for item in get_notifications():
        channel_id = item.get("channel_id", "")
        event_id = item.get("event_id", "")
        if channel_id and event_id and (channel_id, event_id) not in valid_pairs:
            invalid.add(item["notification_id"])
    return invalid


def admin_data_overview() -> dict[str, Any]:
    notifications = get_notifications()
    sessions = get_phone_sessions()
    invalid_ids = notification_invalid_source_ids()
    empty_sessions = [item for item in sessions if not item.get("lines")]
    return {
        "channels": channel_event_admin_rows(),
        "notifications": {
            "count": len(notifications),
            "unread_count": len([item for item in notifications if not item.get("read")]),
            "invalid_source_count": len(invalid_ids),
            "recent": notifications[:10],
        },
        "phone": {
            "session_count": len(sessions),
            "empty_session_count": len(empty_sessions),
            "recent": [
                {
                    "session_id": item["session_id"],
                    "role_name": item["role_name"],
                    "status": item["status"],
                    "line_count": len(item.get("lines", [])),
                    "updated_at": item.get("updated_at", ""),
                }
                for item in sessions[:10]
            ],
        },
        "parser_diagnostics": get_parser_diagnostics()[:12],
        "generation_state": get_generation_state(),
    }


def clear_channel_test_events(channel_id: str, *, include_fallback: bool = True, include_workbench: bool = True) -> dict[str, Any]:
    channel = get_channel_or_404(channel_id)
    events = get_channel_events(channel["channel_id"])
    kept: list[dict[str, Any]] = []
    removed: list[dict[str, Any]] = []
    for event in events:
        tags = set(event.get("tags") or [])
        is_fallback = event.get("source") == "fallback" or "fallback" in tags
        is_workbench = event.get("source") == "workbench" or "workbench" in tags or "test" in tags
        if (include_fallback and is_fallback) or (include_workbench and is_workbench):
            removed.append(event)
        else:
            kept.append(event)
    save_channel_events(channel["channel_id"], kept)
    return {"channel": channel, "removed_count": len(removed), "remaining_count": len(kept)}


def clear_invalid_notifications() -> dict[str, Any]:
    invalid_ids = notification_invalid_source_ids()
    rows = get_notifications()
    kept = [item for item in rows if item["notification_id"] not in invalid_ids]
    save_notifications(kept)
    return {"removed_count": len(rows) - len(kept), "remaining_count": len(kept)}


def prune_empty_phone_sessions() -> dict[str, Any]:
    sessions = get_phone_sessions()
    kept = [item for item in sessions if item.get("lines")]
    save_phone_sessions(kept)
    return {"removed_count": len(sessions) - len(kept), "remaining_count": len(kept)}



@app.get("/api/admin/workbench")
async def api_admin_workbench() -> dict[str, Any]:
    return {"ok": True, "workbench": workbench_overview()}


@app.post("/api/admin/workbench/role-draft")
async def api_admin_workbench_role_draft(payload: WorkbenchRoleDraftPayload) -> dict[str, Any]:
    return {"ok": True, "draft": role_draft_from_source(payload)}


@app.post("/api/admin/workbench/generate", response_model=None)
async def api_admin_workbench_generate(payload: WorkbenchGeneratePayload) -> JSONResponse | dict[str, Any]:
    try:
        result = await run_workbench_generation(payload)
        return {"ok": True, **result}
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"ok": False, "error": compact_text(exc.detail, 240)})


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



@app.get("/api/admin/generation-control")
async def api_admin_generation_control() -> dict[str, Any]:
    return {"ok": True, "generation_control": generation_control_payload()}


@app.put("/api/admin/generation-control")
async def api_admin_save_generation_control(payload: dict[str, Any]) -> dict[str, Any]:
    current = get_settings()
    control = sanitize_generation_control(payload.get("generation_control", payload))
    merged = merge_settings_update(current, {"generation_control": control})
    write_json(SETTINGS_PATH, sanitize_settings(merged))
    return {"ok": True, "generation_control": generation_control_payload()}


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



@app.get("/api/admin/data-overview")
async def api_admin_data_overview() -> dict[str, Any]:
    return {"ok": True, "data": admin_data_overview()}


@app.post("/api/admin/data/channels/{channel_id}/clear-test-events")
async def api_admin_clear_channel_test_events(channel_id: str) -> dict[str, Any]:
    return {"ok": True, **clear_channel_test_events(channel_id)}


@app.post("/api/admin/data/notifications/read-all")
async def api_admin_notifications_read_all() -> dict[str, Any]:
    rows = get_notifications()
    for item in rows:
        item["read"] = True
    save_notifications(rows)
    return {"ok": True, "updated_count": len(rows), "data": admin_data_overview()}


@app.post("/api/admin/data/notifications/clear-invalid")
async def api_admin_clear_invalid_notifications() -> dict[str, Any]:
    return {"ok": True, **clear_invalid_notifications(), "data": admin_data_overview()}


@app.post("/api/admin/data/phone/prune-empty")
async def api_admin_prune_empty_phone_sessions() -> dict[str, Any]:
    return {"ok": True, **prune_empty_phone_sessions(), "data": admin_data_overview()}


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


@app.post("/api/channels/{channel_id}/interactions", response_model=None)
async def api_create_channel_interaction(channel_id: str, payload: ChannelInteractionPayload) -> JSONResponse | dict[str, Any]:
    channel = get_channel_or_404(channel_id)
    if channel["type"] not in {"feed", "forum"}:
        raise HTTPException(status_code=400, detail="This channel does not support user publishing.")
    content = compact_text(payload.content, 1200)
    if not content:
        raise HTTPException(status_code=400, detail="内容不能为空。")
    title = compact_text(payload.title, 120)
    event = {
        "title": title or ("新的帖子" if channel["type"] == "forum" else "新的动态"),
        "content": content,
        "event_type": "thread" if channel["type"] == "forum" else "post",
        "author_id": "user",
        "author_name": "你",
        "tags": ["user"],
        "metadata": {"replies": []},
        "source": "user",
    }
    stored = append_channel_events(channel["channel_id"], [event])
    if not stored:
        raise HTTPException(status_code=400, detail="Event content is empty.")
    try:
        event = await attach_generated_channel_replies(channel, stored[0], content, mode="post")
    except HTTPException as exc:
        event = update_channel_event(channel["channel_id"], stored[0])
        notification_from_event(event)
        return JSONResponse(
            status_code=exc.status_code,
            content={"ok": False, "event": event, "events": get_channel_events(channel["channel_id"]), "error": compact_text(exc.detail, 240)},
        )
    notification_from_event(event)
    return {"ok": True, "event": event, "events": get_channel_events(channel["channel_id"])}


@app.post("/api/channels/{channel_id}/events/{event_id}/replies", response_model=None)
async def api_reply_channel_event(channel_id: str, event_id: str, payload: ChannelReplyPayload) -> JSONResponse | dict[str, Any]:
    channel = get_channel_or_404(channel_id)
    if channel["type"] not in {"feed", "forum"}:
        raise HTTPException(status_code=400, detail="This channel does not support replies.")
    content = compact_text(payload.content, 800)
    if not content:
        raise HTTPException(status_code=400, detail="回复不能为空。")
    event = find_channel_event_or_404(channel["channel_id"], event_id)
    metadata = dict(event.get("metadata") or {})
    existing = sanitize_forum_replies(metadata.get("replies"))
    user_reply = sanitize_forum_replies([
        {
            "author_id": "user",
            "author_name": "你",
            "content": content,
            "mood": "user",
            "floor": len(existing) + 1,
            "created_at": now_iso(),
        }
    ])
    metadata["replies"] = sanitize_forum_replies([*existing, *user_reply])
    event["metadata"] = metadata
    event["updated_at"] = now_iso()
    event = update_channel_event(channel["channel_id"], event)
    try:
        event = await attach_generated_channel_replies(channel, event, content, mode="reply")
    except HTTPException as exc:
        notification_from_event(event)
        return JSONResponse(
            status_code=exc.status_code,
            content={"ok": False, "event": event, "events": get_channel_events(channel["channel_id"]), "error": compact_text(exc.detail, 240)},
        )
    notification_from_event(event)
    return {"ok": True, "event": event, "events": get_channel_events(channel["channel_id"])}


@app.post("/api/channels/{channel_id}/events/{event_id}/mail-replies", response_model=None)
async def api_reply_mail_event(channel_id: str, event_id: str, payload: MailReplyPayload) -> JSONResponse | dict[str, Any]:
    channel = get_channel_or_404(channel_id)
    if channel["type"] != "mail":
        raise HTTPException(status_code=400, detail="This channel does not support mail replies.")
    content = compact_text(payload.content, 1000)
    if not content:
        raise HTTPException(status_code=400, detail="回复不能为空。")
    event = find_channel_event_or_404(channel["channel_id"], event_id)
    metadata = dict(event.get("metadata") or {})
    existing = sanitize_mail_replies(metadata.get("replies"))
    user_reply = sanitize_mail_replies([
        {
            "author_id": "user",
            "author_name": "我",
            "direction": "sent",
            "content": content,
            "mood": "sent",
            "source": "user",
            "created_at": now_iso(),
        }
    ])
    metadata["replies"] = sanitize_mail_replies([*existing, *user_reply])
    event["metadata"] = metadata
    event["updated_at"] = now_iso()
    event = update_channel_event(channel["channel_id"], event)
    generated: list[dict[str, Any]] = []
    if payload.generate_reply is not False:
        try:
            generated = await generate_mail_reply(event, content)
        except HTTPException as exc:
            notification_from_event(event)
            return JSONResponse(
                status_code=exc.status_code,
                content={"ok": False, "event": event, "events": get_channel_events(channel["channel_id"]), "error": compact_text(exc.detail, 240)},
            )
        metadata = dict(event.get("metadata") or {})
        metadata["replies"] = sanitize_mail_replies([*sanitize_mail_replies(metadata.get("replies")), *generated])
        event["metadata"] = metadata
        event["updated_at"] = now_iso()
        event = update_channel_event(channel["channel_id"], event)
    notification_from_event(event)
    if generated:
        add_notification("Mail", f"{generated[-1]['author_name']}: {generated[-1]['content'][:160]}", source="mail", channel_id=channel["channel_id"], event_id=event["event_id"])
    return {"ok": True, "event": event, "events": get_channel_events(channel["channel_id"]), "replies": generated}


@app.post("/api/channels/{channel_id}/events/{event_id}/live-messages")
async def api_add_live_message(channel_id: str, event_id: str, payload: LiveMessagePayload) -> dict[str, Any]:
    channel = get_channel_or_404(channel_id)
    if channel["type"] != "live":
        raise HTTPException(status_code=400, detail="This channel does not support live messages.")
    content = compact_text(payload.content, 240)
    if not content:
        raise HTTPException(status_code=400, detail="弹幕不能为空。")
    event = find_channel_event_or_404(channel["channel_id"], event_id)
    metadata = dict(event.get("metadata") or {})
    existing = sanitize_live_messages(metadata.get("danmaku"), limit=80)
    user_message = sanitize_live_messages([
        {
            "author_name": "你",
            "author_type": "user",
            "content": content,
            "mood": "user",
            "created_at": now_iso(),
        }
    ], limit=1)
    metadata["danmaku"] = sanitize_live_messages([*existing, *user_message], limit=80)
    event["metadata"] = metadata
    event["updated_at"] = now_iso()
    event = update_channel_event(channel["channel_id"], event)
    return {"ok": True, "event": event, "events": get_channel_events(channel["channel_id"])}
async def run_channel_seed(channel: dict[str, Any], count: int) -> dict[str, Any]:
    job = begin_generation_job(f"channel_{channel['type']}", channel["channel_id"])
    try:
        raw_reply = await call_chat_model(
            build_channel_seed_messages(channel, count),
            max_tokens=channel_seed_max_tokens(channel, count),
            temperature=read_main_llm_config()["temperature"],
        )
    except HTTPException as exc:
        finish_generation_job(job, "error", compact_text(exc.detail, 240))
        raise
    events = parse_channel_seed_events(raw_reply, channel, count)
    if not events:
        finish_generation_job(job, "error", "parser_no_valid_events")
        raise HTTPException(status_code=502, detail="模型返回内容无法解析，请查看后台 diagnostics。")
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
    return {"ok": True, "sessions": get_phone_sessions(), "roles": phone_role_candidates()}


@app.post("/api/phone/sessions/{session_id}/hangup")
async def api_hangup_phone_session(session_id: str) -> dict[str, Any]:
    safe_session_id = normalize_id(session_id)
    sessions = get_phone_sessions()
    session = next((item for item in sessions if item["session_id"] == safe_session_id), None)
    if not session:
        raise HTTPException(status_code=404, detail="Phone session not found.")
    session["status"] = "ended"
    session["ended_by"] = "user"
    session["ended_at"] = now_iso()
    session["updated_at"] = now_iso()
    saved = save_phone_sessions([session, *[item for item in sessions if item["session_id"] != safe_session_id]])
    return {"ok": True, "session": saved[0], "sessions": get_phone_sessions()}


@app.post("/api/phone/call", response_model=None)
async def api_phone_call(payload: PhoneCallPayload) -> JSONResponse | dict[str, Any]:
    role = get_phone_role_or_404(payload.role_id)
    sessions = get_phone_sessions()
    session = next((item for item in sessions if item["session_id"] == normalize_id(payload.session_id or "")), None)
    if session and session.get("status") == "ended":
        session = None
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
    if not lines:
        finish_generation_job(job, "error", "parser_no_valid_lines")
        return JSONResponse(status_code=502, content={"ok": False, "error": "模型返回内容无法解析，请查看后台 diagnostics。", "session": session})
    session["lines"].extend(lines)
    session["status"] = call_state
    if call_state == "ended":
        session["ended_by"] = "role"
        session["ended_at"] = now_iso()
    elif call_state == "missed":
        session["ended_by"] = "role"
        session["ended_at"] = now_iso()
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
        "parser_diagnostics": PARSER_DIAGNOSTICS_PATH,
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
        "parser_diagnostics": get_parser_diagnostics()[:10],
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
