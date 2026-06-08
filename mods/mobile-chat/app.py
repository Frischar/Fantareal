from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
from datetime import date, datetime, timedelta, timezone
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

try:
    from fantareal.route_forwarding import _hook_depth as ROUTE_FORWARDING_HOOK_DEPTH
except Exception:
    ROUTE_FORWARDING_HOOK_DEPTH = None


APP_DIR = Path(__file__).resolve().parent
RESOURCE_DIR = APP_DIR
PROJECT_ROOT = APP_DIR.parent.parent if APP_DIR.parent.name.lower() == "mods" else APP_DIR.parent
DATA_DIR = PROJECT_ROOT / "data" / "mobile_chat"
CARDS_DIR = DATA_DIR / "cards"
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
MAIN_CONVERSATIONS_PATH = PROJECT_ROOT / "data" / "conversations.json"
STATIC_DIR = RESOURCE_DIR / "static"
TEMPLATES_DIR = RESOURCE_DIR / "templates"
PROMPT_PATH = RESOURCE_DIR / "prompts" / "mobile_chat_prompt.txt"

DEFAULT_STICKER_IDS = ("happy", "sweat", "stare", "shy", "heart", "cry")
STICKER_IDS = set(DEFAULT_STICKER_IDS)
STICKER_PACK_ROOT = STATIC_DIR / "stickers"
RESERVED_STICKER_PACK_IDS = {"default"}
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
    "ui_theme": "modern",
}
WORLD_THEME_IDS = {"modern", "xianxia", "apocalypse"}
DEFAULT_WORLD_THEME = "modern"
WORLD_THEME_PROMPTS = {
    "modern": "",
    "xianxia": (
        "World style layer: keep the phone UI and JSON schema modern internally, but let wording and character behavior fit a xianxia or classical fantasy setting. "
        "Use display concepts such as transmission, letter, voice transmission and sightings when natural. Keep replies light, fragmented and conversational; do not force archaic prose."
    ),
    "apocalypse": (
        "World style layer: keep the phone UI and JSON schema modern internally, but let wording and character behavior fit an apocalypse or survival network. "
        "Characters may care about risk, supplies, routes and signal status. Use channel, message, call and broadcast concepts when natural, without retelling long main-chat plot."
    ),
}
DEFAULT_GENERATION_SETTINGS = {
    "model_source": "main",
    "api_config": {
        "base_url": "",
        "api_key": "",
        "model": "",
        "temperature": 0.85,
        "request_timeout": 120,
    },
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
PROMPT_SCOPE_LABELS = {
    "group_chat": "群聊",
    "feed": "动态",
    "forum": "论坛",
    "live": "直播",
    "mail": "邮箱",
    "diary": "日记",
    "calendar": "日程",
    "phone": "电话",
    "notification": "通知",
}
PROMPT_SCOPE_ORDER = tuple(PROMPT_SCOPE_LABELS.keys())
DEFAULT_PROMPT_SETTINGS = {
    "preset": "default",
    "editable_blocks": True,
    "use_block_prompt": False,
    "use_custom_prompt": False,
    "prompt_mode": "default",
    "append_json_contract": True,
    "custom_prompts": {scope: "" for scope in PROMPT_SCOPE_ORDER},
    "last_preview_channel": "group_chat",
}
DEFAULT_CHANNEL_TOKEN_SETTINGS = {
    "default": {"initial": 4500, "retry": 6000},
    "feed": {"initial": 4500, "retry": 6000},
    "forum": {"initial": 8000, "retry": 10000},
    "live": {"initial": 4500, "retry": 6000},
    "mail": {"initial": 4500, "retry": 6000},
    "diary": {"initial": 4500, "retry": 6000},
    "calendar": {"initial": 4500, "retry": 6000},
}
DEFAULT_GENERATION_CONTROL_SETTINGS = {
    "paused": False,
    "hourly_limit": 200,
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
    "ui_theme": DEFAULT_UI_SETTINGS["ui_theme"],
    "world_theme": DEFAULT_WORLD_THEME,
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
    "channel_token_settings": DEFAULT_CHANNEL_TOKEN_SETTINGS,
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
        {"channel_id": "forum_main", "type": "forum", "label": "论坛", "description": "角色和世界内路人讨论事件的帖子。", "seed_count": 3, "enabled": True},
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
    "recent_live_ticks": [],
}
GENERATION_ACTIVE_JOB_TTL_SECONDS = 15 * 60
CHANNEL_TYPES = set(PROMPT_SCOPE_ORDER)
CHANNEL_EVENT_TYPES = {"post", "thread", "reply", "notice", "mail", "diary", "calendar", "call_line", "live", "system"}


class SettingsPayload(BaseModel):
    schema_version: int | None = None
    enabled: bool | None = None
    show_floating_button: bool | None = None
    remember_position: bool | None = None
    floating_position: dict[str, Any] | None = None
    panel_position: dict[str, Any] | None = None
    ui_theme: str | None = None
    world_theme: str | None = None
    model_source: str | None = None
    api_config: dict[str, Any] | None = None
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    temperature: float | None = None
    request_timeout: int | None = None
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
    channel_token_settings: dict[str, Any] | None = None
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
    app_roles: dict[str, Any] | None = None
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
    app_roles: dict[str, Any] | None = None
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
    app_roles: dict[str, Any] | None = None
    count: int | None = None
    source: str | None = Field(default="role_generator", max_length=40)


class RoleGeneratorSavePayload(BaseModel):
    role: dict[str, Any] | None = None
    roles: list[Any] | None = None


class RoleEventExtractPayload(BaseModel):
    channel_ids: list[Any] | None = None
    limit: int | None = None


class RoleChatExtractPayload(BaseModel):
    limit: int | None = None
    recent_messages: int | None = None


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


class ChannelEventPatchPayload(BaseModel):
    read: bool | None = None

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


class MailOutgoingPayload(BaseModel):
    recipient_id: str = Field(default="", max_length=120)
    title: str | None = Field(default=None, max_length=120)
    content: str = Field(default="", max_length=1200)
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


class PromptTestPayload(BaseModel):
    scope: str = Field(default="feed", max_length=40)
    mode: str = Field(default="dry-run", max_length=20)
    channel_id: str | None = Field(default=None, max_length=120)
    role_id: str | None = Field(default=None, max_length=120)
    user_input: str | None = Field(default="", max_length=1200)


class NotificationPatchPayload(BaseModel):
    read: bool | None = None


class PhoneCallPayload(BaseModel):
    role_id: str
    user_line: str | None = Field(default="", max_length=500)
    session_id: str | None = Field(default=None, max_length=120)


class PhoneHangupPayload(BaseModel):
    session_id: str = Field(default="", max_length=120)


class ModelListPayload(BaseModel):
    base_url: str | None = Field(default="", max_length=500)
    api_key: str | None = Field(default="", max_length=500)
    request_timeout: int | None = None


app = FastAPI(title="Fantareal Mobile Chat Mod")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def clone_default(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False))


def compact_text(value: Any, limit: int = 500) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def safe_url_host(value: Any) -> str:
    text = compact_text(value, 500)
    if not text:
        return ""
    try:
        from urllib.parse import urlparse

        parsed = urlparse(text)
        return compact_text(parsed.netloc or parsed.path.split("/")[0], 200)
    except Exception:
        return ""


def classify_mobile_error(message: str, status_code: int = 0) -> str:
    text = compact_text(message, 1000).lower()
    if "http 422" in text or "http 400" in text or "upstream=" in text or "\u4e0a\u6e38" in text:
        return "upstream_rejected"
    if "\u8d85\u65f6" in text or "timeout" in text:
        return "timeout"
    if "\u65e0\u6cd5\u8fde\u63a5" in text or "network" in text or "connect" in text:
        return "network"
    if "\u65e0\u6cd5\u89e3\u6790" in text or "\u4e0d\u662f\u5408\u6cd5 json" in text or "\u683c\u5f0f\u4e0d\u517c\u5bb9" in text or "parser" in text:
        return "parse_error"
    if status_code in {400, 422}:
        return "bad_request"
    return "request_failed"


def mobile_error_suggestions(error_type: str) -> list[str]:
    if error_type == "upstream_rejected":
        return [
            "\u68c0\u67e5 API Key\u3001Base URL \u548c\u6a21\u578b\u540d\u662f\u5426\u5339\u914d\u5f53\u524d\u4f9b\u5e94\u5546\u3002",
            "\u5c1d\u8bd5\u62c9\u53d6\u6a21\u578b\u5217\u8868\u6216\u5207\u6362\u5230\u5df2\u786e\u8ba4\u53ef\u7528\u7684\u6a21\u578b\u3002",
            "\u5982\u679c\u662f 422/400\uff0c\u5c1d\u8bd5\u964d\u4f4e max_tokens\u3001temperature\uff0c\u6216\u5173\u95ed\u4e0d\u517c\u5bb9\u53c2\u6570\u3002",
        ]
    if error_type == "timeout":
        return ["\u8c03\u5927 Timeout \u6216\u7a0d\u540e\u91cd\u8bd5\u3002", "\u964d\u4f4e\u8f93\u51fa token\uff0c\u51cf\u5c11\u672c\u6b21\u751f\u6210\u5185\u5bb9\u3002"]
    if error_type == "network":
        return ["\u68c0\u67e5 Base URL\u3001\u7f51\u7edc\u3001\u4ee3\u7406\u548c\u4f9b\u5e94\u5546\u670d\u52a1\u72b6\u6001\u3002", "\u786e\u8ba4\u5c0f\u624b\u673a\u72ec\u7acb API \u662f\u5426\u5df2\u542f\u7528\u6216\u662f\u5426\u5e94\u8ddf\u968f\u4e3b\u7a0b\u5e8f\u3002"]
    if error_type == "parse_error":
        return ["\u67e5\u770b\u540e\u53f0 diagnostics \u4e2d\u7684\u89e3\u6790\u8bb0\u5f55\u3002", "\u4fdd\u7559 Prompt JSON contract\uff0c\u6216\u964d\u4f4e temperature \u540e\u91cd\u8bd5\u3002"]
    return ["\u67e5\u770b\u540e\u53f0 diagnostics\u3002", "\u68c0\u67e5\u5f53\u524d\u6a21\u578b\u914d\u7f6e\u540e\u91cd\u8bd5\u3002"]


def mobile_error_payload(exc: HTTPException, *, include_model_context: bool = True, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    message = compact_text(exc.detail, 500)
    error_type = classify_mobile_error(message, exc.status_code)
    payload: dict[str, Any] = {
        "ok": False,
        "error": message,
        "error_type": error_type,
        "suggestions": mobile_error_suggestions(error_type),
    }
    if include_model_context:
        try:
            config = read_mobile_llm_config()
        except Exception:
            config = {}
        payload["model_context"] = {
            "model_source": compact_text(config.get("model_source"), 80),
            "provider": compact_text(config.get("provider"), 80),
            "model": compact_text(config.get("model"), 160),
            "base_url_host": safe_url_host(config.get("base_url")),
            "request_timeout": config.get("request_timeout"),
        }
    if extra:
        payload.update(extra)
    return payload


def clean_multiline_text(value: Any, limit: int = 12000) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(line.rstrip() for line in text.split("\n")).strip()
    return text[:limit]


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


def is_safe_sticker_pack_id(pack_id: Any) -> bool:
    value = compact_text(pack_id, 80)
    if not value or value in RESERVED_STICKER_PACK_IDS:
        return False
    return bool(re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,79}", value))


def custom_sticker_packs() -> dict[str, dict[str, Any]]:
    if not STICKER_PACK_ROOT.is_dir():
        return {}
    packs: dict[str, dict[str, Any]] = {}
    for directory in sorted(STICKER_PACK_ROOT.iterdir(), key=lambda path: path.name.casefold()):
        if not directory.is_dir() or not is_safe_sticker_pack_id(directory.name):
            continue
        pack_id = directory.name
        label = pack_id.replace("_", " ").replace("-", " ").title()
        manifest = read_json(directory / "manifest.json", {})
        if isinstance(manifest, dict):
            label = compact_text(manifest.get("label"), 80) or label
        packs[pack_id] = {
            "label": label,
            "directory": directory,
        }
    return packs


def custom_sticker_pack(pack_id: Any) -> dict[str, Any] | None:
    value = compact_text(pack_id, 80)
    if not is_safe_sticker_pack_id(value):
        return None
    return custom_sticker_packs().get(value)


def default_sticker_directory() -> Path:
    return STICKER_PACK_ROOT / "default"


def default_sticker_files() -> list[Path]:
    directory = default_sticker_directory()
    if not directory.is_dir():
        return []
    files = [
        path
        for path in directory.iterdir()
        if path.is_file() and is_safe_png_filename(path.name)
    ]
    return sorted(files, key=custom_sticker_sort_key)[:MAX_CUSTOM_STICKERS_PER_PACK]


def custom_sticker_path(pack_id: str, filename: str, require_exists: bool = True) -> Path | None:
    safe_pack_id = compact_text(pack_id, 80)
    pack = custom_sticker_pack(safe_pack_id)
    if safe_pack_id == "default":
        pack = {"label": "默认", "directory": default_sticker_directory()}
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
    if compact_text(pack_id, 80) == "default":
        return default_sticker_files()
    pack = custom_sticker_pack(pack_id)
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
    if compact_text(pack_id, 80) == "default":
        return {}
    pack = custom_sticker_pack(pack_id)
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
    for path in default_sticker_files():
        stickers.append(
            {
                "id": f"default:{path.name}",
                "type": "image",
                "pack_id": "default",
                "pack_label": "默认",
                "label": path.stem,
                "tags": [path.stem],
                "description": "",
                "filename": path.name,
                "url_path": f"/stickers/default/{quote(path.name)}",
            }
        )
    for pack_id, pack in custom_sticker_packs().items():
        manifest = custom_sticker_manifest(pack_id)
        for path in custom_sticker_files(pack_id):
            meta = manifest.get(path.name, {})
            stickers.append(
                {
                    "id": f"{safe_pack_id}:{path.name}",
                    "type": "image",
                    "pack_id": pack_id,
                    "pack_label": pack["label"],
                    "label": compact_text(meta.get("label"), 80) or path.stem,
                    "tags": meta.get("tags", []),
                    "description": compact_text(meta.get("description"), 120),
                    "filename": path.name,
                    "url_path": f"/stickers/{safe_pack_id}/{quote(path.name)}",
                }
            )
    return stickers


def sticker_pack_summaries() -> list[dict[str, Any]]:
    packs = [
        {
            "pack_id": "default",
            "label": "默认",
            "type": "builtin",
            "count": len(DEFAULT_STICKER_IDS) + len(default_sticker_files()),
            "manifest_editable": False,
            "directory": "",
        }
    ]
    for pack_id, pack in custom_sticker_packs().items():
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
    safe_pack_id = compact_text(pack_id, 80)
    if safe_pack_id != "default" and not custom_sticker_pack(safe_pack_id):
        raise HTTPException(status_code=404, detail="表情包不存在。")
    manifest = custom_sticker_manifest(safe_pack_id)
    rows: list[dict[str, Any]] = []
    for path in custom_sticker_files(safe_pack_id):
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
    pack = custom_sticker_pack(pack_id)
    if not pack:
        raise HTTPException(status_code=404, detail="表情包不存在。")
    existing_files = {path.name for path in custom_sticker_files(pack_id)}
    sanitized = [row for row in sanitize_manifest_rows(rows) if row["file"] in existing_files]
    existing_manifest = read_json(pack["directory"] / "manifest.json", {})
    payload = {
        "schema_version": 1,
        "updated_at": now_iso(),
        "stickers": sanitized,
    }
    if isinstance(existing_manifest, dict) and compact_text(existing_manifest.get("label"), 80):
        payload["label"] = compact_text(existing_manifest.get("label"), 80)
    write_json(pack["directory"] / "manifest.json", payload)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def local_today() -> date:
    return datetime.now(timezone.utc).astimezone().date()


def local_today_iso() -> str:
    return local_today().isoformat()


def normalize_id(value: Any, fallback: str = "") -> str:
    raw = compact_text(value, 120).lower().replace(" ", "_")
    normalized = SAFE_ID_RE.sub("_", raw).strip("_")
    return normalized[:80] or fallback


def make_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def current_role_card_payload() -> dict[str, Any]:
    payload = read_json(CURRENT_ROLE_CARD_PATH, {})
    if not isinstance(payload, dict):
        return {}
    raw = payload.get("raw") if isinstance(payload.get("raw"), dict) else {}
    return raw if isinstance(raw, dict) else {}


def current_mobile_card_uid() -> str:
    raw = current_role_card_payload()
    if not raw:
        return "global"
    for value in (raw.get("card_uid"), raw.get("uid"), raw.get("id")):
        safe_uid = normalize_id(value, "")
        if safe_uid:
            return safe_uid
    personas = raw.get("personas") if isinstance(raw.get("personas"), (dict, list)) else {}
    fingerprint_payload = {
        "name": raw.get("name") or raw.get("role_name") or "",
        "personas": personas,
    }
    digest = hashlib.sha1(json.dumps(fingerprint_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    return f"card_{digest}"


def current_mobile_card_dir() -> Path:
    safe_uid = normalize_id(current_mobile_card_uid(), "global")
    return CARDS_DIR / safe_uid


def card_groups_path() -> Path:
    return current_mobile_card_dir() / "groups.json"


def card_role_profiles_path() -> Path:
    return current_mobile_card_dir() / "role_profiles.json"


def card_messages_dir() -> Path:
    return current_mobile_card_dir() / "messages"


def card_events_dir() -> Path:
    return current_mobile_card_dir() / "events"


def card_notifications_path() -> Path:
    return current_mobile_card_dir() / "notifications.json"


def card_phone_calls_path() -> Path:
    return current_mobile_card_dir() / "phone_calls.json"


def card_generation_state_path() -> Path:
    return current_mobile_card_dir() / "generation_state.json"


def card_parser_diagnostics_path() -> Path:
    return current_mobile_card_dir() / "parser_diagnostics.json"


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
        card_messages_dir().mkdir(parents=True, exist_ok=True)
        card_events_dir().mkdir(parents=True, exist_ok=True)
        if not SETTINGS_PATH.exists():
            _write_json_unlocked(SETTINGS_PATH, DEFAULT_SETTINGS)
        if not card_groups_path().exists():
            _write_json_unlocked(card_groups_path(), [])
        if not card_role_profiles_path().exists():
            _write_json_unlocked(card_role_profiles_path(), DEFAULT_ROLE_PROFILES)
        if not AUTOMATION_STATE_PATH.exists():
            _write_json_unlocked(AUTOMATION_STATE_PATH, DEFAULT_AUTOMATION_STATE)
        if not PROMPT_BLOCKS_PATH.exists():
            _write_json_unlocked(PROMPT_BLOCKS_PATH, DEFAULT_PROMPT_BLOCKS)
        if not APP_REGISTRY_PATH.exists():
            _write_json_unlocked(APP_REGISTRY_PATH, DEFAULT_APP_REGISTRY)
        if not CHANNELS_PATH.exists():
            _write_json_unlocked(CHANNELS_PATH, DEFAULT_CHANNELS)
        if not card_notifications_path().exists():
            _write_json_unlocked(card_notifications_path(), DEFAULT_NOTIFICATIONS)
        if not card_phone_calls_path().exists():
            _write_json_unlocked(card_phone_calls_path(), DEFAULT_PHONE_CALLS)
        if not card_generation_state_path().exists():
            _write_json_unlocked(card_generation_state_path(), DEFAULT_GENERATION_STATE)
        if not card_parser_diagnostics_path().exists():
            _write_json_unlocked(card_parser_diagnostics_path(), {"schema_version": 1, "items": []})


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
        "hourly_limit": clamp_int(source.get("hourly_limit"), 1, 500, defaults["hourly_limit"]),
        "retry_limit": clamp_int(source.get("retry_limit"), 0, 5, defaults["retry_limit"]),
        "cost_notice": bool(source.get("cost_notice", defaults["cost_notice"])),
        "app_enabled": app_enabled,
    }


def generation_kind_scope(kind: str) -> str:
    safe = compact_text(kind, 80)
    if safe.startswith("channel_"):
        return safe.replace("channel_", "", 1).replace("_interaction", "").replace("_tick", "")
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
        raise HTTPException(status_code=423, detail="\u751f\u6210\u5df2\u5728\u540e\u53f0\u5168\u5c40\u6682\u505c\uff0c\u8bf7\u5728\u540e\u53f0\u6062\u590d\u540e\u91cd\u8bd5\u3002")
    if control.get("app_enabled", {}).get(scope, True) is False:
        label = PROMPT_SCOPE_LABELS.get(scope, scope)
        raise HTTPException(status_code=423, detail=f"{label} \u751f\u6210\u5f00\u5173\u5df2\u5173\u95ed\uff0c\u8bf7\u5728\u540e\u53f0\u5f00\u542f\u540e\u91cd\u8bd5\u3002")
    hourly_limit = clamp_int(control.get("hourly_limit"), 1, 500, DEFAULT_GENERATION_CONTROL_SETTINGS["hourly_limit"])
    recent = [item for item in get_generation_state().get("last_jobs", []) if compact_text(item.get("finished_at"), 13) == compact_text(now_iso(), 13)]
    if len(recent) >= hourly_limit:
        raise HTTPException(status_code=429, detail="\u672c\u5c0f\u65f6\u751f\u6210\u9884\u7b97\u5df2\u7528\u5c3d\uff0c\u8bf7\u7a0d\u540e\u518d\u8bd5\u6216\u5728\u540e\u53f0\u8c03\u9ad8\u9884\u7b97\u3002")


def generation_control_payload() -> dict[str, Any]:
    return {
        "settings": get_settings().get("generation_control", DEFAULT_GENERATION_CONTROL_SETTINGS),
        "state": get_generation_state(),
    }



def sanitize_channel_token_settings(raw: Any) -> dict[str, dict[str, int]]:
    source = raw if isinstance(raw, dict) else {}
    settings = clone_default(DEFAULT_CHANNEL_TOKEN_SETTINGS)
    for key, defaults in DEFAULT_CHANNEL_TOKEN_SETTINGS.items():
        row = source.get(key) if isinstance(source.get(key), dict) else {}
        initial = clamp_int(row.get("initial"), 64, 32000, defaults["initial"])
        retry = clamp_int(row.get("retry"), 64, 32000, defaults["retry"])
        settings[key] = {"initial": initial, "retry": max(initial, retry)}
    return settings


def sanitize_model_source(value: Any) -> str:
    return "custom" if compact_text(value, 20).lower() == "custom" else "main"


def sanitize_api_config(raw: Any) -> dict[str, Any]:
    source = raw if isinstance(raw, dict) else {}
    defaults = DEFAULT_GENERATION_SETTINGS["api_config"]
    return {
        "base_url": compact_text(source.get("base_url") or source.get("llm_base_url"), 500),
        "api_key": compact_text(source.get("api_key") or source.get("llm_api_key"), 500),
        "model": compact_text(source.get("model") or source.get("llm_model"), 160),
        "temperature": clamp_float(source.get("temperature"), 0.0, 2.0, defaults["temperature"]),
        "request_timeout": clamp_int(source.get("request_timeout"), 10, 600, defaults["request_timeout"]),
    }


def redact_api_config(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "base_url": config.get("base_url", ""),
        "api_key": "",
        "api_key_configured": bool(config.get("api_key")),
        "model": config.get("model", ""),
        "temperature": config.get("temperature", DEFAULT_GENERATION_SETTINGS["api_config"]["temperature"]),
        "request_timeout": config.get("request_timeout", DEFAULT_GENERATION_SETTINGS["api_config"]["request_timeout"]),
    }


def settings_public_payload(settings: dict[str, Any]) -> dict[str, Any]:
    payload = clone_default(settings)
    api_config = sanitize_api_config(payload.get("api_config"))
    payload["api_config"] = redact_api_config(api_config)
    generation = payload.get("generation") if isinstance(payload.get("generation"), dict) else {}
    generation["api_config"] = redact_api_config(api_config)
    payload["generation"] = generation
    payload["llm_api_key"] = ""
    payload["api_key_configured"] = bool(api_config.get("api_key"))
    return payload


def sanitize_custom_prompts(raw: Any) -> dict[str, str]:
    source = raw if isinstance(raw, dict) else {}
    return {scope: clean_multiline_text(source.get(scope), 12000) for scope in PROMPT_SCOPE_ORDER}


def normalize_prompt_scope(value: Any) -> str:
    scope = compact_text(value, 40) or DEFAULT_PROMPT_SETTINGS["last_preview_channel"]
    return scope if scope in CHANNEL_TYPES else DEFAULT_PROMPT_SETTINGS["last_preview_channel"]


def normalize_prompt_mode(value: Any, *, use_custom_prompt: bool = False) -> str:
    mode = normalize_id(value, "")
    if mode in {"additive", "override"}:
        return mode
    if use_custom_prompt:
        return "override"
    return "default"


def sanitize_world_theme(value: Any) -> str:
    theme = normalize_id(value, DEFAULT_WORLD_THEME)
    return theme if theme in WORLD_THEME_IDS else DEFAULT_WORLD_THEME


def sanitize_prompt_settings(raw: Any) -> dict[str, Any]:
    source = raw if isinstance(raw, dict) else {}
    last_preview = normalize_prompt_scope(source.get("last_preview_channel", DEFAULT_PROMPT_SETTINGS["last_preview_channel"]))
    use_custom = bool(source.get("use_custom_prompt", DEFAULT_PROMPT_SETTINGS["use_custom_prompt"]))
    prompt_mode = normalize_prompt_mode(source.get("prompt_mode"), use_custom_prompt=use_custom)
    return {
        "preset": compact_text(source.get("preset"), 40) or DEFAULT_PROMPT_SETTINGS["preset"],
        "editable_blocks": bool(source.get("editable_blocks", DEFAULT_PROMPT_SETTINGS["editable_blocks"])),
        "use_block_prompt": bool(source.get("use_block_prompt", DEFAULT_PROMPT_SETTINGS["use_block_prompt"])),
        "use_custom_prompt": prompt_mode != "default",
        "prompt_mode": prompt_mode,
        "append_json_contract": bool(source.get("append_json_contract", DEFAULT_PROMPT_SETTINGS["append_json_contract"])),
        "custom_prompts": sanitize_custom_prompts(source.get("custom_prompts")),
        "last_preview_channel": last_preview,
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
    channel_token_source = section_source(source, "channel_token_settings")

    settings["schema_version"] = 2
    settings["enabled"] = bool(source.get("enabled", DEFAULT_SETTINGS["enabled"]))
    settings["show_floating_button"] = bool(pick_section_value(source, ui_source, "show_floating_button", DEFAULT_UI_SETTINGS["show_floating_button"]))
    settings["remember_position"] = bool(pick_section_value(source, ui_source, "remember_position", DEFAULT_UI_SETTINGS["remember_position"]))
    settings["ui_theme"] = sanitize_world_theme(pick_section_value(source, ui_source, "ui_theme", source.get("world_theme", DEFAULT_WORLD_THEME)))
    settings["world_theme"] = settings["ui_theme"]
    settings["floating_position"] = sanitize_position(
        pick_section_value(source, ui_source, "floating_position", DEFAULT_UI_SETTINGS["floating_position"]),
        DEFAULT_UI_SETTINGS["floating_position"],
    )
    settings["panel_position"] = sanitize_position(
        pick_section_value(source, ui_source, "panel_position", DEFAULT_UI_SETTINGS["panel_position"]),
        DEFAULT_UI_SETTINGS["panel_position"],
    )
    settings["model_source"] = sanitize_model_source(pick_section_value(source, generation_source, "model_source", DEFAULT_GENERATION_SETTINGS["model_source"]))
    nested_api_source = generation_source.get("api_config") if isinstance(generation_source.get("api_config"), dict) else {}
    raw_api_config = {
        **(nested_api_source if isinstance(nested_api_source, dict) else {}),
        **(source.get("api_config") if isinstance(source.get("api_config"), dict) else {}),
    }
    for target_key, source_key in (
        ("base_url", "llm_base_url"),
        ("api_key", "llm_api_key"),
        ("model", "llm_model"),
        ("temperature", "temperature"),
        ("request_timeout", "request_timeout"),
    ):
        if source_key in source:
            raw_api_config[target_key] = source.get(source_key)
        if source_key in generation_source:
            raw_api_config[target_key] = generation_source.get(source_key)
    api_config = sanitize_api_config(raw_api_config)
    settings["api_config"] = api_config
    settings["llm_base_url"] = api_config["base_url"]
    settings["llm_api_key"] = api_config["api_key"]
    settings["llm_model"] = api_config["model"]
    settings["temperature"] = api_config["temperature"]
    settings["request_timeout"] = api_config["request_timeout"]
    raw_reply_count = pick_section_value(source, generation_source, "reply_count", DEFAULT_GENERATION_SETTINGS["reply_count"])
    settings["reply_count"] = "1-2" if str(raw_reply_count).strip() != "1" else "1"
    settings["max_tokens"] = clamp_int(
        pick_section_value(source, generation_source, "max_tokens", DEFAULT_GENERATION_SETTINGS["max_tokens"]),
        64,
        32000,
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
        "ui_theme": settings["ui_theme"],
    }
    settings["generation"] = {
        "model_source": settings["model_source"],
        "api_config": settings["api_config"],
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
    settings["prompt"] = sanitize_prompt_settings(prompt_source)
    settings["channel_token_settings"] = sanitize_channel_token_settings(channel_token_source)
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
    content = clean_multiline_text(raw.get("content"), 4000)
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


def prompt_scope_catalog() -> list[dict[str, str]]:
    return [{"scope": scope, "label": PROMPT_SCOPE_LABELS.get(scope, scope)} for scope in PROMPT_SCOPE_ORDER]


def prompt_blocks_for_scope(scope: str, *, locked_only: bool = False) -> list[dict[str, Any]]:
    target = normalize_prompt_scope(scope)
    rows = []
    for item in get_prompt_blocks()["blocks"]:
        if not item.get("enabled") or (target not in item.get("scope", []) and "*" not in item.get("scope", [])):
            continue
        if locked_only and not item.get("locked"):
            continue
        rows.append(item)
    return rows


def prompt_mode_for_settings(settings: dict[str, Any] | None = None) -> str:
    prompt_settings = (settings or get_settings()).get("prompt", {})
    return normalize_prompt_mode(prompt_settings.get("prompt_mode"), use_custom_prompt=bool(prompt_settings.get("use_custom_prompt")))


def custom_prompt_for_scope(scope: str, settings: dict[str, Any] | None = None) -> str:
    prompt_settings = (settings or get_settings()).get("prompt", {})
    if prompt_mode_for_settings(settings) == "default":
        return ""
    prompts = prompt_settings.get("custom_prompts") if isinstance(prompt_settings.get("custom_prompts"), dict) else {}
    return clean_multiline_text(prompts.get(normalize_prompt_scope(scope)), 12000)


def default_prompt_text(scope: str) -> str:
    target = normalize_prompt_scope(scope)
    blocks = prompt_blocks_for_scope(target)
    return "\n\n".join(item["content"] for item in blocks).strip()


def locked_prompt_contract_text(scope: str) -> str:
    target = normalize_prompt_scope(scope)
    return "\n\n".join(item["content"] for item in prompt_blocks_for_scope(target, locked_only=True)).strip()


def strip_locked_prompt_contract(text: str, scope: str) -> str:
    body = clean_multiline_text(text, 12000)
    contract = locked_prompt_contract_text(scope)
    if body and contract and body.endswith(contract):
        body = body[: -len(contract)].strip()
    return body


def editable_default_prompt_text(scope: str) -> str:
    target = normalize_prompt_scope(scope)
    return "\n\n".join(item["content"] for item in prompt_blocks_for_scope(target) if not item.get("locked")).strip()


def prompt_body_preview_text(scope: str, settings: dict[str, Any] | None = None) -> str:
    target = normalize_prompt_scope(scope)
    active_settings = settings or get_settings()
    custom_prompt = custom_prompt_for_scope(target, active_settings)
    if prompt_mode_for_settings(active_settings) == "override" and custom_prompt:
        return strip_locked_prompt_contract(custom_prompt, target)
    return editable_default_prompt_text(target)


def world_theme_prompt_section(settings: dict[str, Any] | None = None) -> str:
    theme = sanitize_world_theme((settings or get_settings()).get("world_theme"))
    return WORLD_THEME_PROMPTS.get(theme, "")


def custom_prompt_user_section(scope: str, settings: dict[str, Any] | None = None) -> str:
    if prompt_mode_for_settings(settings) != "additive":
        return ""
    target = normalize_prompt_scope(scope)
    custom_prompt = custom_prompt_for_scope(target, settings)
    if not custom_prompt:
        return ""
    label = PROMPT_SCOPE_LABELS.get(target, target)
    return (
        f"Admin extra instructions for {label} ({target}). Follow them as high-priority task instructions. "
        "Do not mention this section in the output.\n"
        f"{custom_prompt}"
    )


def apply_custom_prompt_to_user_text(scope: str, user_text: str, settings: dict[str, Any] | None = None) -> str:
    section = custom_prompt_user_section(scope, settings)
    if not section:
        return user_text
    return f"{section}\n\nGeneration task:\n{user_text}"


def assembled_prompt_text(scope: str) -> str:
    target = normalize_prompt_scope(scope)
    settings = get_settings()
    custom_prompt = custom_prompt_for_scope(target, settings)
    theme_section = world_theme_prompt_section(settings)
    if prompt_mode_for_settings(settings) == "override" and custom_prompt:
        parts = [strip_locked_prompt_contract(custom_prompt, target)]
        if theme_section:
            parts.append(theme_section)
        if settings.get("prompt", {}).get("append_json_contract", True):
            contract = locked_prompt_contract_text(target)
            if contract:
                parts.append(contract)
        return "\n\n".join(parts).strip()
    parts = [default_prompt_text(target)]
    if theme_section:
        parts.append(theme_section)
    return "\n\n".join(part for part in parts if part).strip()


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
    target_scope = normalize_prompt_scope(scope)
    settings = get_settings()
    prompt_settings = settings.get("prompt", {})
    group: dict[str, Any] | None = None
    if group_id:
        try:
            group = get_group_or_404(group_id)
        except HTTPException:
            group = None
    blocks = prompt_blocks_for_scope(target_scope)
    contract_blocks = prompt_blocks_for_scope(target_scope, locked_only=True)
    prompts = prompt_settings.get("custom_prompts") if isinstance(prompt_settings.get("custom_prompts"), dict) else {}
    custom_prompt = clean_multiline_text(prompts.get(target_scope), 12000)
    context: dict[str, Any] = {
        "scope": target_scope,
        "settings": prompt_settings,
        "block_count": len(blocks),
        "contract_block_count": len(contract_blocks),
        "use_custom_prompt": bool(prompt_settings.get("use_custom_prompt")),
        "custom_prompt_configured": bool(custom_prompt),
        "prompt_mode": prompt_mode_for_settings(settings),
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
        "scope_label": PROMPT_SCOPE_LABELS.get(target_scope, target_scope),
        "scopes": prompt_scope_catalog(),
        "settings": prompt_settings,
        "blocks": blocks,
        "contract_blocks": contract_blocks,
        "custom_prompt": custom_prompt,
        "default_prompt": default_prompt_text(target_scope),
        "editable_default_prompt": editable_default_prompt_text(target_scope),
        "prompt_body": prompt_body_preview_text(target_scope, settings),
        "locked_contract_text": locked_prompt_contract_text(target_scope),
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
    recent_live_source = source.get("recent_live_ticks") if isinstance(source.get("recent_live_ticks"), list) else []
    recent_live_ticks: list[dict[str, Any]] = []
    for item in recent_live_source[:20]:
        if not isinstance(item, dict):
            continue
        recent_live_ticks.append(
            {
                "recorded_at": compact_text(item.get("recorded_at"), 80),
                "status": compact_text(item.get("status"), 40),
                "channel_id": normalize_id(item.get("channel_id")),
                "event_id": normalize_id(item.get("event_id")),
                "live_tick": compact_text(item.get("live_tick"), 40),
                "title": compact_text(item.get("title"), 120),
                "content_preview": compact_text(item.get("content_preview"), 180),
                "danmaku_count": live_metric_int(item.get("danmaku_count"), 0),
                "highlight_count": live_metric_int(item.get("highlight_count"), 0),
                "contributor_count": live_metric_int(item.get("contributor_count"), 0),
                "viewers": compact_text(item.get("viewers"), 40),
                "likes": compact_text(item.get("likes"), 40),
                "error": compact_text(item.get("error"), 240),
            }
        )
    return {"schema_version": 1, "active_jobs": sanitized_active, "last_jobs": sanitized_last, "recent_live_ticks": recent_live_ticks}


def get_generation_state() -> dict[str, Any]:
    ensure_runtime_data()
    payload = sanitize_generation_state(read_json(card_generation_state_path(), DEFAULT_GENERATION_STATE))
    if payload != read_json(card_generation_state_path(), DEFAULT_GENERATION_STATE):
        write_json(card_generation_state_path(), payload)
    return payload


def save_generation_state(state: dict[str, Any]) -> dict[str, Any]:
    payload = sanitize_generation_state(state)
    write_json(card_generation_state_path(), payload)
    return payload


def active_job_age_seconds(job: dict[str, Any]) -> float:
    started_at = compact_text(job.get("started_at"), 80)
    if not started_at:
        return 0
    try:
        started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    except ValueError:
        return 0
    if started.tzinfo is None:
        started = started.replace(tzinfo=datetime.now(timezone.utc).astimezone().tzinfo)
    return max(0.0, (datetime.now(timezone.utc).astimezone() - started).total_seconds())


def prune_stale_generation_jobs(state: dict[str, Any]) -> dict[str, Any]:
    active = state.get("active_jobs") if isinstance(state.get("active_jobs"), dict) else {}
    stale: list[dict[str, Any]] = []
    for key, job in list(active.items()):
        if isinstance(job, dict) and active_job_age_seconds(job) > GENERATION_ACTIVE_JOB_TTL_SECONDS:
            stale.append(job)
            active.pop(key, None)
    if stale:
        state["active_jobs"] = active
        state["last_jobs"] = [
            {
                **job,
                "finished_at": now_iso(),
                "status": "error",
                "error": "stale_active_job_pruned",
            }
            for job in stale
        ] + state.get("last_jobs", [])
        state["last_jobs"] = state["last_jobs"][:30]
        save_generation_state(state)
    return state


def interrupted_generation_error(exc: BaseException | None = None) -> str:
    if exc is None:
        return "generation_interrupted"
    return compact_text(f"generation_interrupted:{exc.__class__.__name__}:{exc}", 240) or "generation_interrupted"


def begin_generation_job(kind: str, target_id: str) -> dict[str, str]:
    safe_kind = compact_text(kind, 80) or "unknown"
    safe_target = compact_text(target_id, 120) or "default"
    key = f"{safe_kind}:{safe_target}"
    assert_generation_allowed(safe_kind)
    state = prune_stale_generation_jobs(get_generation_state())
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


def record_live_tick_diagnostic(channel: dict[str, Any], event: dict[str, Any], *, status: str, error: str = "") -> None:
    metadata = dict(event.get("metadata") or {})
    row = {
        "recorded_at": now_iso(),
        "status": compact_text(status, 40) or "unknown",
        "channel_id": normalize_id(channel.get("channel_id")),
        "event_id": normalize_id(event.get("event_id")),
        "live_tick": compact_text(metadata.get("live_tick"), 40),
        "title": compact_text(event.get("title"), 120),
        "content_preview": compact_text(event.get("content"), 180),
        "danmaku_count": len(sanitize_live_messages(metadata.get("danmaku"), limit=80)),
        "highlight_count": len(sanitize_live_messages(metadata.get("highlights"), limit=12)),
        "contributor_count": len(sanitize_live_contributors(metadata.get("contributors"))),
        "viewers": compact_text(metadata.get("viewers"), 40),
        "likes": compact_text(metadata.get("likes"), 40),
        "error": compact_text(error, 240),
    }
    state = get_generation_state()
    state["recent_live_ticks"] = [row, *state.get("recent_live_ticks", [])][:20]
    save_generation_state(state)


def merge_settings_update(current: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    merged = {**current, **updates}
    for key in ("ui", "generation", "api_config", "auto_behavior", "stickers", "roles", "groups", "prompt", "generation_control", "channel_token_settings"):
        if isinstance(current.get(key), dict) and isinstance(updates.get(key), dict):
            merged[key] = {**current[key], **updates[key]}
    if isinstance(current.get("generation"), dict) and isinstance(updates.get("generation"), dict):
        current_api = current["generation"].get("api_config") if isinstance(current["generation"].get("api_config"), dict) else {}
        update_api = updates["generation"].get("api_config") if isinstance(updates["generation"].get("api_config"), dict) else {}
        if current_api or update_api:
            merged["generation"]["api_config"] = {**current_api, **update_api}
    if isinstance(current.get("prompt"), dict) and isinstance(updates.get("prompt"), dict):
        current_prompts = current["prompt"].get("custom_prompts") if isinstance(current["prompt"].get("custom_prompts"), dict) else {}
        update_prompts = updates["prompt"].get("custom_prompts") if isinstance(updates["prompt"].get("custom_prompts"), dict) else {}
        if current_prompts or update_prompts:
            merged["prompt"]["custom_prompts"] = {**current_prompts, **update_prompts}
    current_api_key = compact_text((current.get("api_config") or {}).get("api_key") if isinstance(current.get("api_config"), dict) else current.get("llm_api_key"), 500)
    for container in (merged, merged.get("generation") if isinstance(merged.get("generation"), dict) else {}):
        api_config = container.get("api_config") if isinstance(container.get("api_config"), dict) else None
        if api_config is not None and not compact_text(api_config.get("api_key"), 500) and current_api_key:
            api_config["api_key"] = current_api_key
    if "llm_api_key" in updates and not compact_text(updates.get("llm_api_key"), 500) and current_api_key:
        merged["llm_api_key"] = current_api_key
    ui = updates.get("ui") if isinstance(updates.get("ui"), dict) else {}
    generation = updates.get("generation") if isinstance(updates.get("generation"), dict) else {}
    auto_behavior = updates.get("auto_behavior") if isinstance(updates.get("auto_behavior"), dict) else {}
    if ui:
        for key in ("show_floating_button", "remember_position", "floating_position", "panel_position", "ui_theme"):
            if key in ui and key not in updates:
                merged[key] = ui[key]
    if "ui_theme" in updates and isinstance(merged.get("ui"), dict):
        merged["ui"] = {**merged["ui"], "ui_theme": updates["ui_theme"]}
    if "world_theme" in updates and "ui_theme" not in updates and isinstance(merged.get("ui"), dict):
        merged["ui"] = {**merged["ui"], "ui_theme": updates["world_theme"]}
    if generation:
        for key in ("model_source", "api_config", "reply_count", "max_tokens", "recent_message_limit", "allow_role_to_role_reply"):
            if key in generation and key not in updates:
                if key == "api_config" and isinstance(merged.get("generation"), dict):
                    merged[key] = merged["generation"].get("api_config", generation[key])
                else:
                    merged[key] = generation[key]
    if "enabled" in auto_behavior and "allow_auto_interject" not in updates:
        merged["allow_auto_interject"] = auto_behavior["enabled"]
    if "allow_auto_interject" in updates and not auto_behavior and isinstance(merged.get("auto_behavior"), dict):
        merged["auto_behavior"] = {**merged["auto_behavior"], "enabled": updates["allow_auto_interject"]}
    if isinstance(merged.get("api_config"), dict):
        api_config = merged["api_config"]
        legacy_keys = {
            "base_url": "llm_base_url",
            "api_key": "llm_api_key",
            "model": "llm_model",
            "temperature": "temperature",
            "request_timeout": "request_timeout",
        }
        for api_key, legacy_key in legacy_keys.items():
            if api_key in api_config:
                merged[legacy_key] = api_config[api_key]
    return merged


def safe_avatar(value: Any) -> str:
    text = compact_text(value, 500)
    return text if text.startswith("/") else ""


def role_name_key(value: Any) -> str:
    cleaned = clean_extracted_role_name(value, limit=120)
    return (cleaned or compact_text(value, 120)).casefold()


def placeholder_role_name(value: Any) -> bool:
    text = role_name_key(value)
    compact = re.sub(r"[\s_-]+", "", text)
    return bool(compact and (compact.isdecimal() or re.fullmatch(r"(?:role|角色|persona|personas|char|character)\d+", compact)))


def sanitize_member(raw: Any, index: int = 0) -> dict[str, str] | None:
    if not isinstance(raw, dict):
        return None
    member_type = "user" if str(raw.get("type", "")).strip().lower() == "user" else "character"
    name = compact_text(raw.get("name"), 80)
    if not name or (member_type == "character" and placeholder_role_name(name)):
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


def normalize_app_alias(value: Any) -> str:
    text = compact_text(value, 40).strip().casefold()
    if not text:
        return ""
    normalized = normalize_id(text, "")
    aliases = {
        "\u7fa4\u804a": "group_chat", "group": "group_chat", "chat": "group_chat",
        "\u52a8\u6001": "feed", "\u670b\u53cb\u5708": "feed", "feed": "feed",
        "\u8bba\u575b": "forum", "\u5e16\u5b50": "forum", "forum": "forum",
        "\u76f4\u64ad": "live", "live": "live",
        "\u7535\u8bdd": "phone", "phone": "phone",
        "\u90ae\u7bb1": "mail", "\u90ae\u4ef6": "mail", "mail": "mail",
        "\u65e5\u8bb0": "diary", "diary": "diary",
        "\u65e5\u7a0b": "calendar", "\u65e5\u5386": "calendar", "calendar": "calendar",
        "\u901a\u77e5": "notifications", "notification": "notifications", "notifications": "notifications",
    }
    return aliases.get(text) or aliases.get(normalized) or normalized


def sanitize_role_app_scope(value: Any) -> list[str]:
    allowed = {app.get("app_id") for app in sanitize_app_registry(read_json(APP_REGISTRY_PATH, DEFAULT_APP_REGISTRY)).get("apps", []) if isinstance(app, dict)}
    allowed.update(CHANNEL_TYPES)
    allowed.discard("assist")
    rows = split_compact_values(value, limit=12, item_limit=40)
    result: list[str] = []
    seen: set[str] = set()
    for item in rows:
        app_id = normalize_app_alias(item)
        if app_id and app_id not in seen and (not allowed or app_id in allowed):
            seen.add(app_id)
            result.append(app_id)
    return result

def sanitize_role_app_roles(value: Any) -> dict[str, list[str]]:
    source = value if isinstance(value, dict) else {}
    allowed_apps = {app.get("app_id") for app in sanitize_app_registry(read_json(APP_REGISTRY_PATH, DEFAULT_APP_REGISTRY)).get("apps", []) if isinstance(app, dict)}
    allowed_apps.update(CHANNEL_TYPES)
    allowed_apps.discard("assist")
    result: dict[str, list[str]] = {}
    for app_id, roles in source.items():
        safe_app = normalize_app_alias(app_id)
        if not safe_app or (allowed_apps and safe_app not in allowed_apps):
            continue
        values = split_compact_values(roles, limit=8, item_limit=40)
        values = [normalize_id(item, "") for item in values if normalize_id(item, "")]
        if values:
            result[safe_app] = values
    return result


def role_app_allowed(profile: dict[str, Any], app_id: str, *, strict_suitable: bool = False) -> bool:
    target = normalize_id(app_id, "")
    if not target:
        return True
    blocked = set(sanitize_role_app_scope(profile.get("blocked_apps")))
    if target in blocked or "*" in blocked:
        return False
    suitable = set(sanitize_role_app_scope(profile.get("suitable_apps")))
    if strict_suitable and suitable and target not in suitable and "*" not in suitable:
        return False
    return True


def role_app_usage(profile: dict[str, Any], app_id: str) -> list[str]:
    roles = sanitize_role_app_roles(profile.get("app_roles"))
    return roles.get(normalize_id(app_id, ""), [])


def role_profiles_for_app(app_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
    target = normalize_id(app_id, "")
    profiles = [profile for profile in get_role_profiles(include_disabled=False) if role_app_allowed(profile, target)]
    preferred = [profile for profile in profiles if target and target in set(profile.get("suitable_apps") or [])]
    neutral = [profile for profile in profiles if profile not in preferred]
    return [*preferred, *neutral][:limit]


def role_app_generation_policy(app_id: str) -> dict[str, Any]:
    target = normalize_app_alias(app_id)
    labels = {
        "group_chat": ["active_chat_member", "friend", "topic_starter"],
        "feed": ["poster", "commenter", "friend", "bystander"],
        "forum": ["thread_author", "floor_reply", "moderator", "bystander"],
        "live": ["streamer", "viewer", "highlight_sender", "contributor"],
        "mail": ["sender", "recipient", "contact", "organization", "system_notice"],
        "diary": ["writer", "related_person", "memory_subject"],
        "calendar": ["participant", "organizer", "location_contact", "organization"],
        "phone": ["caller", "callee", "phone_contact"],
        "notifications": ["source", "system_notice", "related_person"],
    }
    return {
        "target_app": target,
        "preferred_usages": labels.get(target, ["related_person"]),
        "selection_rules": [
            "Exclude roles whose blocked_apps contains target_app.",
            "Prefer roles whose suitable_apps contains target_app.",
            "Use usage_in_target_app/app_roles to decide whether a role should be author, participant, viewer, sender, or bystander.",
            "If no suitable saved role exists, keep generated bystanders as event metadata only; do not invent saved role IDs.",
        ],
    }


def sanitize_sticker_preferences(value: Any) -> dict[str, Any]:
    source = value if isinstance(value, dict) else {}
    default_pack = compact_text(source.get("default_pack"), 80) or DEFAULT_STICKERS_SETTINGS["default_pack"]
    if default_pack != "default" and not custom_sticker_pack(default_pack):
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
    if source not in {"manual", "current_card", "group_import", "role_generator", "admin_role_generator", "event_extract", "admin_event_extract", "chat_extract", "admin_chat_extract", "admin_workbench"}:
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
        "app_roles": sanitize_role_app_roles(raw.get("app_roles")),
        "generator_notes": compact_text(raw.get("generator_notes"), 500),
        "sticker_preferences": sanitize_sticker_preferences(raw.get("sticker_preferences")),
        "auto_speak_weight": auto_weight,
        "enabled": raw.get("enabled") is not False,
        "created_at": compact_text(raw.get("created_at"), 80) or now_iso(),
        "updated_at": compact_text(raw.get("updated_at"), 80) or now_iso(),
    }


def get_role_profiles(*, include_disabled: bool = True) -> list[dict[str, Any]]:
    ensure_runtime_data()
    stored = read_json(card_role_profiles_path(), DEFAULT_ROLE_PROFILES)
    rows = stored.get("roles", []) if isinstance(stored, dict) else stored
    if not isinstance(rows, list):
        rows = []
    profiles = [profile for index, item in enumerate(rows) if (profile := sanitize_role_profile(item, index)) is not None]
    if not include_disabled:
        profiles = [profile for profile in profiles if profile["enabled"]]
    return sorted(profiles, key=lambda item: (not item["enabled"], item["display_name"].casefold(), item["role_id"]))


def save_role_profiles(profiles: list[dict[str, Any]]) -> None:
    sanitized = [profile for index, item in enumerate(profiles) if (profile := sanitize_role_profile(item, index)) is not None]
    write_json(card_role_profiles_path(), {"schema_version": 1, "roles": sanitized})


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


def default_app_roles_for_profile(apps: list[str], raw: dict[str, Any] | None = None) -> dict[str, list[str]]:
    source = raw or {}
    hint = " ".join(
        compact_text(source.get(key), 300)
        for key in ("identity", "impression", "known_info", "overall_request", "speech_style", "nickname", "real_name")
    ).lower()
    result: dict[str, list[str]] = {}
    for app_id in apps:
        safe_app = normalize_id(app_id, "")
        if safe_app == "feed":
            result[safe_app] = ["poster"]
        elif safe_app == "forum":
            result[safe_app] = ["thread_author", "reply_user"]
        elif safe_app == "live":
            roles = ["viewer"]
            if any(word in hint for word in ("??", "??", "anchor", "streamer", "??", "??", "??")):
                roles.insert(0, "anchor")
            else:
                roles.append("donor")
            result[safe_app] = roles
        elif safe_app == "mail":
            result[safe_app] = ["sender", "reply_contact"]
        elif safe_app == "phone":
            result[safe_app] = ["caller"]
        elif safe_app == "diary":
            result[safe_app] = ["related_person"]
        elif safe_app == "calendar":
            result[safe_app] = ["participant"]
        elif safe_app in {"notification", "notifications"}:
            result[safe_app] = ["source"]
    return result


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
    app_roles = sanitize_role_app_roles(raw.get("app_roles")) or default_app_roles_for_profile(suitable_apps, raw)
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
            "app_roles": app_roles,
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



def clean_extracted_role_name(value: Any, *, limit: int = 80) -> str:
    """Normalize role names extracted from loose JSON/list-looking text."""
    if isinstance(value, (list, tuple, set)):
        rows = list(value)
        if len(rows) == 1:
            value = rows[0]
        else:
            value = " ".join(compact_text(item, limit) for item in rows)
    text = compact_text(value, limit)
    if not text:
        return ""
    text = text.replace("\u200b", "").replace("\ufeff", "")
    text = re.sub(r"^[\\/]+|[\\/]+$", "", text)
    wrapper_chars = " \t\r\n,\uFF0C\u3001;\uFF1B\u3002.!\uFF01?\uFF1F:\uFF1A|[](){}<>\u300A\u300B\u3010\u3011\uFF08\uFF09'\"`\u201C\u201D\u2018\u2019\u300C\u300D\u300E\u300F"
    for _ in range(4):
        trimmed = text.strip(wrapper_chars)
        if trimmed == text:
            break
        text = trimmed
    text = re.sub(r"^\s*(?:name|\u89d2\u8272|\u4eba\u7269|\u6635\u79f0)\s*[:\uFF1A]\s*", "", text, flags=re.IGNORECASE)
    text = text.strip(wrapper_chars)
    if re.search(r"[\[\]{}]", text):
        text = text.replace("[", "").replace("]", "").replace("{", "").replace("}", "").strip(wrapper_chars)
    return compact_text(text, limit)

def event_role_name_allowed(name: str) -> bool:
    text = clean_extracted_role_name(name, limit=80)
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
        "主角",
        "先生",
        "姑娘",
        "小姐",
        "夫人",
        "公子",
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
        raw_rows = re.split(r"[,\uFF0C\u3001;\uFF1B\n]+", compact_text(value, 500))
    names: list[str] = []
    seen: set[str] = set()
    for item in raw_rows:
        name = clean_extracted_role_name(item, limit=80)
        key = role_name_key(name)
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
    name = clean_extracted_role_name(candidate.get("name"), limit=80)
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
        display_name = clean_extracted_role_name(name, limit=80)
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


CHAT_SPEAKER_LABEL_RE = re.compile(r"(?:^|\n)\s*([A-Za-z\u4e00-\u9fff][A-Za-z0-9\u4e00-\u9fff·._ -]{1,23})\s*[：:]\s*(?=\S)")
CHAT_TTS_LABEL_RE = re.compile(r"\[TTSVoice:([^:\]\n]{2,40})")
CHAT_MENTION_RE = re.compile(r"(?:看着|望向|想起|提到|遇见|听见|联系|拨给|写给|收到|名叫|叫做)([A-Za-z\u4e00-\u9fff·]{2,12})")


def main_chat_existing_name_keys() -> set[str]:
    keys = {role_name_key(item.get("display_name")) for item in get_role_profiles(include_disabled=True)}
    current = extract_current_card_roles()
    for role in current.get("roles", []):
        keys.add(role_name_key(role.get("name")))
    keys.add(role_name_key(current.get("user", {}).get("name") or current_user_member().get("name")))
    return {key for key in keys if key}


def iter_main_chat_messages(payload: Any) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []

    def visit(value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                visit(item)
            return
        if not isinstance(value, dict):
            return
        nested = value.get("messages") or value.get("conversation") or value.get("items")
        if isinstance(nested, list):
            visit(nested)
        if any(key in value for key in ("content", "raw_content", "assistant_clean_text")):
            messages.append(value)

    visit(payload)
    return messages


def read_main_chat_conversation_payload() -> Any:
    try:
        from fantareal.app import conversation_path as main_conversation_path
        from fantareal.app import get_active_slot_id as main_get_active_slot_id

        path = main_conversation_path(main_get_active_slot_id())
        return read_json(path, [])
    except Exception:
        return read_json(MAIN_CONVERSATIONS_PATH, [])


def main_chat_message_text(message: dict[str, Any]) -> str:
    parts = [
        compact_text(message.get("raw_content"), 4000),
        compact_text(message.get("assistant_clean_text"), 4000),
        compact_text(message.get("content"), 4000),
    ]
    seen: set[str] = set()
    rows: list[str] = []
    for part in parts:
        if part and part not in seen:
            rows.append(part)
            seen.add(part)
    return "\n".join(rows)


def main_chat_candidate_names(text: str) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    seen: set[str] = set()

    def add(name: Any, kind: str) -> None:
        cleaned = clean_extracted_role_name(name, limit=80)
        cleaned = re.sub(r"(?:\u7684|\u5411|\u7ed9|\u53eb|\u5462)$", "", cleaned)
        key = role_name_key(cleaned)
        if event_role_name_allowed(cleaned) and key not in seen:
            seen.add(key)
            candidates.append((cleaned, kind))

    for match in CHAT_TTS_LABEL_RE.finditer(text):
        add(match.group(1), "tts")
    for match in CHAT_SPEAKER_LABEL_RE.finditer(text):
        add(match.group(1), "speaker")
    for match in CHAT_MENTION_RE.finditer(text):
        add(match.group(1), "mention")
    return candidates


def clean_main_story_text(value: Any, limit: int = 360) -> str:
    text = re.sub(r"<think>[\s\S]*?</think>", "", str(value or ""), flags=re.IGNORECASE)
    text = re.sub(r"\[TTSVoice:[^\]]+\]", "", text)
    return compact_text(text, limit)


def summarize_main_story_messages(messages: list[dict[str, Any]], limit: int = 620) -> str:
    rows: list[str] = []
    for item in messages:
        if not isinstance(item, dict):
            continue
        role = compact_text(item.get("role"), 24) or compact_text(item.get("source"), 24) or "story"
        content = clean_main_story_text(item.get("assistant_clean_text") or item.get("raw_content") or item.get("content"), 180)
        if content:
            rows.append(f"{role}: {content}")
    if not rows:
        return ""
    return compact_text(" | ".join(rows), limit)


def current_card_memory_items(limit: int = 6) -> list[dict[str, str]]:
    try:
        from fantareal.app import get_memories as main_get_memories
    except Exception:
        main_get_memories = None
    if main_get_memories is not None:
        try:
            raw_items = main_get_memories()
        except Exception:
            raw_items = []
    else:
        raw_items = []
    rows: list[dict[str, str]] = []
    for item in raw_items[-limit:] if isinstance(raw_items, list) else []:
        if not isinstance(item, dict):
            continue
        title = compact_text(item.get("title"), 80)
        content = compact_text(item.get("content") or item.get("notes"), 260)
        if not title and not content:
            continue
        rows.append(
            {
                "title": title,
                "content": content,
                "tags": ", ".join(compact_text(tag, 24) for tag in item.get("tags", [])[:6]) if isinstance(item.get("tags"), list) else "",
            }
        )
    return rows


def main_story_context_payload(recent_limit: int = 8, memory_limit: int = 6) -> dict[str, Any]:
    conversations = read_main_chat_conversation_payload()
    messages = iter_main_chat_messages(conversations)[-recent_limit:]
    main_chat_summary = summarize_main_story_messages(messages)
    recent_messages: list[dict[str, str]] = []
    for item in messages[-2:]:
        if not isinstance(item, dict):
            continue
        content = clean_main_story_text(item.get("assistant_clean_text") or item.get("raw_content") or item.get("content"), 180)
        if not content:
            continue
        recent_messages.append(
            {
                "role": compact_text(item.get("role"), 40) or compact_text(item.get("source"), 40),
                "content": content,
                "turn_id": compact_text(item.get("turn_id") or item.get("message_id"), 80),
            }
        )
    return {
        "enabled": True,
        "source": "summarized_main_chat_and_current_card_memories",
        "instruction": "Use main_chat_summary and current_card_memories as latest canon for relationship stage, plot phase, location, promises, injuries, secrets and emotional continuity. recent_main_chat only gives a tiny tail excerpt for tone. Do not roll back events already established here.",
        "main_chat_summary": main_chat_summary,
        "recent_main_chat": recent_messages,
        "current_card_memories": current_card_memory_items(memory_limit),
    }

def extract_main_chat_role_profiles(payload: RoleChatExtractPayload | None = None, *, source: str = "chat_extract") -> list[dict[str, Any]]:
    payload = payload or RoleChatExtractPayload()
    limit = clamp_int(payload.limit, 1, 30, 12)
    recent_messages = clamp_int(payload.recent_messages, 20, 300, 120)
    conversations = read_main_chat_conversation_payload()
    messages = iter_main_chat_messages(conversations)[-recent_messages:]
    existing_names = main_chat_existing_name_keys()
    candidates: dict[str, dict[str, Any]] = {}

    def add_candidate(message: dict[str, Any], name: str, kind: str, snippet_source: str) -> None:
        key = role_name_key(name)
        if not key or key in existing_names:
            return
        row = candidates.setdefault(
            key,
            {
                "name": name,
                "count": 0,
                "apps": {"group_chat"},
                "refs": [],
                "snippets": [],
                "appearances": [],
                "identity": "从主 Chat 正文只读提取的边缘角色候选",
            },
        )
        row["count"] += 1
        ref = compact_text(f"main_chat:{message.get('turn_id') or message.get('message_id') or 'message'}:{kind}", 180)
        if ref and ref not in row["refs"]:
            row["refs"].append(ref)
        snippet = compact_text(snippet_source, 180)
        if snippet and snippet not in row["snippets"]:
            row["snippets"].append(snippet)

    for message in messages:
        text = main_chat_message_text(message)
        if not text:
            continue
        snippet = compact_text(re.sub(r"\[TTSVoice:[^\]]+\]", "", text), 180)
        for name, kind in main_chat_candidate_names(text):
            add_candidate(message, name, kind, snippet)

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
            "app_roles",
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
    members = [role_profile_to_member(profile) for profile in profiles if not placeholder_role_name(profile.get("display_name"))]
    seen = {item["role_id"] for item in members}
    current = extract_current_card_roles()
    for role in current.get("roles", []):
        if role.get("role_id") in seen or placeholder_role_name(role.get("name")):
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
        row["app_roles"] = profile.get("app_roles", {})
        row["usage_in_group_chat"] = role_app_usage(profile, "group_chat")
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


def declared_persona_name(raw: dict[str, Any], fallback: Any = "") -> str:
    explicit = compact_text(raw.get("name"), 80)
    fallback_text = compact_text(fallback, 80)
    if explicit and not placeholder_role_name(explicit):
        return explicit
    for key in ("description", "personality", "scenario", "creator_notes"):
        text = compact_text(raw.get(key), 1000)
        if not text:
            continue
        match = re.search(r"(?:\[|【)?姓名\s*[:：]\s*([^\]\[】；;，,\n\r]+)", text)
        if match:
            name = compact_text(match.group(1), 80).strip("。.!！?？")
            if name and not placeholder_role_name(name):
                return name
    return "" if placeholder_role_name(fallback_text) else fallback_text


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

    main_name = declared_persona_name(raw, raw.get("name"))
    if main_name:
        upsert(
            {
                "role_id": raw.get("role_id") or raw.get("id") or normalize_id(main_name, "main_role"),
                "name": main_name,
                "summary": summarize_persona(raw),
                "avatar": raw.get("avatar") or raw.get("avatar_url") or "",
                "type": "character",
            },
            0,
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
        persona_summary = summarize_persona(persona)
        name = declared_persona_name(persona, persona_key)
        if not name:
            continue
        upsert(
            {
                "role_id": persona.get("role_id") or persona.get("id") or normalize_id(f"current_card_{persona_key}_{name}", f"current_card_role_{index + 1}"),
                "name": name,
                "summary": persona_summary,
                "avatar": persona.get("avatar") or persona.get("avatar_url") or "",
                "type": "character",
            },
            index,
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
    messages_dir = card_messages_dir()
    target = (messages_dir / f"{safe_group_id}.json").resolve()
    if target.parent != messages_dir.resolve():
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
        "members": sanitize_members(raw.get("members"), ensure_user=False),
        "allow_role_to_role_reply": bool(raw.get("allow_role_to_role_reply", settings["allow_role_to_role_reply"])),
        "allow_auto_interject": bool(raw.get("allow_auto_interject", settings["allow_auto_interject"])),
        "reply_count": "1" if str(raw.get("reply_count", settings["reply_count"])).strip() == "1" else "1-2",
        "sticker_pack": "default",
        "created_at": compact_text(raw.get("created_at"), 80) or now_iso(),
        "updated_at": compact_text(raw.get("updated_at"), 80) or now_iso(),
    }


def default_group() -> dict[str, Any]:
    user = current_user_member()
    roles = available_role_members().get("roles", [])
    members = [user]
    if roles:
        members.append(roles[0])
    else:
        members.append(
            {
                "role_id": "review_character",
                "name": "Review Character",
                "type": "character",
                "summary": "Temporary character for prompt tests.",
                "avatar": "",
            }
        )
    return sanitize_group(
        {
            "group_id": "group_prompt_test",
            "name": "Prompt Test Group",
            "description": "Temporary group for prompt tests only.",
            "members": members,
            "allow_role_to_role_reply": True,
            "allow_auto_interject": False,
            "reply_count": "1",
            "sticker_pack": "default",
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
    ) or {
        "group_id": "group_prompt_test",
        "name": "Prompt Test Group",
        "description": "Temporary group for prompt tests only.",
        "members": members,
        "allow_role_to_role_reply": True,
        "allow_auto_interject": False,
        "reply_count": "1",
        "sticker_pack": "default",
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }


def get_groups() -> list[dict[str, Any]]:
    ensure_runtime_data()
    stored = read_json(card_groups_path(), [])
    rows = stored.get("groups", []) if isinstance(stored, dict) else stored
    if not isinstance(rows, list):
        rows = []
    groups = [group for item in rows if (group := sanitize_group(item)) is not None]
    return sorted(groups, key=lambda item: item["updated_at"], reverse=True)


def save_groups(groups: list[dict[str, Any]]) -> None:
    write_json(card_groups_path(), groups)


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
    seed_count = clamp_int(raw.get("seed_count"), 1, 20, 5)
    if channel_type == "forum":
        seed_count = min(seed_count, 3)
    return {
        "channel_id": channel_id,
        "type": channel_type,
        "label": label,
        "description": compact_text(raw.get("description"), 500),
        "seed_count": seed_count,
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
    return card_events_dir() / f"{safe_channel_id}.json"


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
        if isinstance(raw_value, bool):
            metadata[safe_key] = raw_value
        elif isinstance(raw_value, (int, float)):
            metadata[safe_key] = raw_value
        elif isinstance(raw_value, (dict, list)):
            metadata[safe_key] = raw_value
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


def calendar_date_only(value: Any, index: int = 0) -> str:
    today = local_today()
    offset = max(0, min(index, 30))
    fallback = (today + timedelta(days=offset)).isoformat()
    text = date_only(value, fallback=fallback)
    try:
        parsed = date.fromisoformat(text)
    except ValueError:
        return fallback
    return parsed.isoformat() if parsed >= today else fallback


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


def live_contributor_key(value: Any) -> str:
    return compact_text(value, 80).casefold().strip()


def merge_live_contributors(existing: Any, incoming: Any, *, limit: int = 12) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    order = 0
    for source, is_new in ((existing, False), (incoming, True)):
        for item in sanitize_live_contributors(source):
            key = live_contributor_key(item.get("name"))
            if not key:
                continue
            amount = live_metric_int(item.get("amount"), 0)
            if key not in merged:
                merged[key] = {
                    "name": item["name"],
                    "amount_value": 0,
                    "note": "",
                    "order": order,
                }
                order += 1
            merged[key]["amount_value"] = live_metric_int(merged[key].get("amount_value"), 0) + max(0, amount)
            if is_new and item.get("note"):
                merged[key]["note"] = item["note"]
            elif not merged[key].get("note") and item.get("note"):
                merged[key]["note"] = item["note"]
    rows = sorted(merged.values(), key=lambda item: (-live_metric_int(item.get("amount_value"), 0), item.get("order", 0)))
    return [
        {
            "name": compact_text(item.get("name"), 80),
            "amount": live_metric_text(item.get("amount_value"), 0),
            "note": compact_text(item.get("note"), 120),
        }
        for item in rows[:limit]
        if compact_text(item.get("name"), 80)
    ]


def live_metric_int(value: Any, fallback: int = 0) -> int:
    if isinstance(value, (int, float)):
        return max(0, int(value))
    text = compact_text(value, 40).casefold().replace(",", "").strip()
    if not text:
        return max(0, int(fallback))
    multiplier = 1
    if text.endswith("k"):
        multiplier = 1000
        text = text[:-1]
    elif text.endswith("w"):
        multiplier = 10000
        text = text[:-1]
    elif text.endswith("\u4e07"):
        multiplier = 10000
        text = text[:-1]
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return max(0, int(fallback))
    return max(0, int(float(match.group(0)) * multiplier))


def live_metric_text(value: Any, fallback: int = 0) -> str:
    number = live_metric_int(value, fallback)
    if number >= 10000:
        label = f"{number / 10000:.1f}".rstrip("0").rstrip(".")
        return f"{label}\u4e07"
    return str(number)


def next_live_metric(value: Any, fallback: int, step: int) -> str:
    current = live_metric_int(value, fallback)
    return live_metric_text(current + max(1, step), fallback)


def sanitize_channel_event(raw: Any, channel: dict[str, Any], index: int = 0) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    content = compact_text(raw.get("content") or raw.get("body"), 2000)
    if not content:
        return None
    event_type = normalize_id(raw.get("event_type") or raw.get("type"), channel["type"])
    if event_type not in CHANNEL_EVENT_TYPES:
        event_type = {"feed": "post", "forum": "thread", "mail": "mail", "diary": "diary", "calendar": "calendar", "live": "live"}.get(channel["type"], "post")
    if channel["type"] == "forum":
        event_type = "thread"
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
        metadata["date"] = calendar_date_only(metadata_source.get("date") or metadata_source.get("time") or raw.get("created_at"), index)
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
        metadata["likes"] = compact_text(metadata_source.get("likes") or raw.get("likes"), 40) or str(120 + index * 23)
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


def summarize_mobile_context(app_id: str = "") -> dict[str, Any]:
    target_app = normalize_id(app_id, "")
    roles = (role_profiles_for_app(target_app, limit=20) if target_app else get_role_profiles(include_disabled=False)[:20])
    groups = get_groups()[:20]
    return {
        "target_app": target_app,
        "role_app_policy": role_app_generation_policy(target_app),
        "roles": [
            {
                "role_id": item["role_id"],
                "display_name": item["display_name"],
                "summary": item.get("summary", ""),
                "status": item.get("status", ""),
                "chat_style": item.get("chat_style", ""),
                "suitable_apps": item.get("suitable_apps", []),
                "blocked_apps": item.get("blocked_apps", []),
                "app_roles": item.get("app_roles", {}),
                "usage_in_target_app": role_app_usage(item, target_app) if target_app else [],
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
        "main_story_context": main_story_context_payload(),
    }


def summarize_mobile_seed_context(channel: dict[str, Any]) -> dict[str, Any]:
    target_app = normalize_id(channel.get("type") or channel.get("app_id"), "")
    roles = role_profiles_for_app(target_app, limit=12)
    groups = get_groups()[:8]
    return {
        "target_app": target_app,
        "role_app_policy": role_app_generation_policy(target_app),
        "role_filter": {"blocked_apps_excluded": True, "preferred_apps_first": True},
        "roles": [
            {
                "role_id": item["role_id"],
                "display_name": item["display_name"],
                "summary": compact_text(item.get("summary"), 160),
                "status": compact_text(item.get("status"), 80),
                "chat_style": compact_text(item.get("chat_style"), 120),
                "suitable_apps": item.get("suitable_apps", []),
                "blocked_apps": item.get("blocked_apps", []),
                "app_roles": item.get("app_roles", {}),
                "usage_in_target_app": role_app_usage(item, target_app),
            }
            for item in roles
        ],
        "groups": [
            {
                "name": item["name"],
                "members": [member["name"] for member in item.get("members", []) if member.get("type") == "character"][:8],
            }
            for item in groups
        ],
        "recent_channel_events": [
            {"title": event["title"], "author_name": event["author_name"], "content": event["content"][:120]}
            for event in get_channel_events(channel["channel_id"])[:3]
        ],
        "main_story_context": main_story_context_payload(recent_limit=6, memory_limit=5),
    }


def effective_channel_seed_count(channel: dict[str, Any], count: Any = None) -> int:
    safe_count = clamp_int(count, 1, 20, channel.get("seed_count", 5))
    if channel.get("type") == "forum":
        return 1
    return safe_count


def build_channel_seed_messages(channel: dict[str, Any], count: int) -> list[dict[str, str]]:
    schema = next((item for item in channel_schema_catalog() if item["type"] == channel["type"]), {})
    current_datetime = now_iso()
    context = {
        "channel": channel,
        "count": count,
        "schema": schema,
        "current_date": current_datetime[:10],
        "current_datetime": current_datetime,
        "mobile_context": summarize_mobile_seed_context(channel),
    }
    system_text = assembled_prompt_text(channel["type"]) or system_prompt_text()
    content_limit = 520 if channel["type"] == "forum" else 280 if channel["type"] in {"diary", "live"} else 180 if channel["type"] in {"mail", "calendar"} else 140
    output_rules = [
        f"Generate exactly {count} event(s) for this mobile app channel.",
        "Return compact valid JSON only, with no markdown, no explanation, and no surrounding text.",
        "The root shape must be {\"events\":[...]} and each event must include title, content, author_name, event_type, tags and metadata.",
        f"Use 1-3 short text tags. Keep each title <= 24 Chinese characters and each content <= {content_limit} Chinese characters.",
        "Keep metadata small and JSON-serializable.",
        "Use Context JSON current_date/current_datetime as the present time unless the provided world context explicitly sets a different in-world date.",
        "Honor mobile_context.main_story_context as latest canon from the main story and current-card memories; do not roll back established plot or relationship stages.",
        "Follow Context JSON mobile_context.role_app_policy: exclude blocked roles, prefer suitable roles, and use usage_in_target_app/app_roles for authors, participants, viewers, senders and bystanders.",
    ]
    if channel["type"] == "forum":
        output_rules.append(
            "Generate one substantial forum thread, not a short social feed post. "
            "The thread content should read like a complete forum post with concrete details, context, and a clear question or point of discussion. "
            "For each forum thread, put exactly 2 compact floor replies in metadata.replies; "
            "each reply must include author_name, author_type, source, content, mood and floor. "
            "Mix at least one bystander/random passerby reply with role/moderator replies; each reply content <= 120 Chinese characters."
        )
    if channel["type"] == "calendar":
        output_rules.append(
            "For every calendar event, metadata.date is required in YYYY-MM-DD format; "
            "metadata.date must be current_date or a future date when no explicit in-world date is provided; "
            "spread events across current_date and the next few days instead of inventing unrelated past months or years. "
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
    user_text = apply_custom_prompt_to_user_text(channel["type"], user_text)
    return [{"role": "system", "content": system_text}, {"role": "user", "content": user_text}]


def build_channel_seed_retry_messages(channel: dict[str, Any], count: int) -> list[dict[str, str]]:
    current_datetime = now_iso()
    context = {
        "channel": {
            "channel_id": channel["channel_id"],
            "type": channel["type"],
            "label": channel["label"],
            "description": channel.get("description", ""),
        },
        "count": count,
        "current_date": current_datetime[:10],
        "current_datetime": current_datetime,
        "mobile_context": summarize_mobile_seed_context(channel),
    }
    system_text = (
        "Return compact valid JSON only. Do not include markdown, prose, analysis, hidden reasoning, or explanations. "
        "The response must start with { and end with }."
    )
    reply_rule = ""
    if channel["type"] == "forum":
        reply_rule = (
            "Generate one substantial forum thread with concrete details, context, and a clear question or point of discussion. "
            "Each event must be event_type thread and include metadata.replies with exactly 2 replies. "
            "Each reply must include author_name, author_type, source, content, mood and floor, and each reply content <= 120 Chinese characters."
        )
    user_text = (
        f"Generate exactly {count} {channel['type']} event(s). "
        "Root shape: {\"events\":[...]}. "
        "Each event requires title, content, author_name, event_type, tags and metadata. "
        "Keep titles <= 24 Chinese characters, content <= 520 Chinese characters, tags <= 3. "
        "Honor mobile_context.main_story_context as latest canon from the main story and current-card memories. "
        "Follow mobile_context.role_app_policy when choosing authors and metadata participants. "
        f"{reply_rule}\nContext JSON:\n"
        + json.dumps(context, ensure_ascii=False, separators=(",", ":"))
    )
    user_text = apply_custom_prompt_to_user_text(channel["type"], user_text)
    return [{"role": "system", "content": system_text}, {"role": "user", "content": user_text}]


def channel_seed_max_tokens(channel: dict[str, Any], count: int, *, retry: bool = False) -> int:
    settings = get_settings()
    configured = settings["max_tokens"]
    safe_count = clamp_int(count, 1, 20, 1)
    baseline = 1100 if channel["type"] == "forum" else 1000
    per_event = 380 if channel["type"] == "forum" else 340
    recommended = baseline + safe_count * per_event
    token_settings = settings.get("channel_token_settings", {})
    channel_floor = token_settings.get(channel["type"], token_settings.get("default", {}))
    floor_key = "retry" if retry else "initial"
    configured_floor = clamp_int(channel_floor.get(floor_key), 64, 32000, 0) if isinstance(channel_floor, dict) else 0
    recommended = max(recommended, configured_floor)
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
        "mobile_context": summarize_mobile_context(channel["type"]),
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
        "Honor mobile_context.main_story_context as latest canon from the main story and current-card memories. "
        "Follow mobile_context.role_app_policy when choosing role/moderator replies; bystanders must stay metadata-only. "
        "Each reply must include author_name, author_type, source, content, mood and floor. "
        "Keep each content <= 70 Chinese characters, in-character, varied, and directly responsive to the user's content. "
        "Valid author_type values: role, bystander, moderator, system. Bystanders must not be treated as saved character profiles. "
        "Do not mention system prompts or plugin internals.\n"
        "Context JSON:\n"
        + json.dumps(context, ensure_ascii=False, separators=(",", ":"))
    )
    user_text = apply_custom_prompt_to_user_text(channel["type"], user_text)
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
            temperature=read_mobile_llm_config()["temperature"],
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


def build_live_tick_messages(channel: dict[str, Any], event: dict[str, Any]) -> list[dict[str, str]]:
    metadata = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
    context = {
        "channel": channel,
        "event": {
            "title": event.get("title", ""),
            "content": event.get("content", ""),
            "author_name": event.get("author_name", ""),
            "tags": event.get("tags", []),
            "metadata": {
                "live_status": metadata.get("live_status", "直播中"),
                "viewers": metadata.get("viewers", ""),
                "likes": metadata.get("likes", ""),
                "fans": metadata.get("fans", ""),
                "inner_thought": metadata.get("inner_thought", ""),
                "recent_danmaku": sanitize_live_messages(metadata.get("danmaku"), limit=80)[-12:],
                "recent_highlights": sanitize_live_messages(metadata.get("highlights"), limit=12)[:6],
                "contributors": sanitize_live_contributors(metadata.get("contributors"))[:8],
                "live_tick": metadata.get("live_tick", "0"),
            },
        },
        "current_datetime": now_iso(),
        "mobile_context": summarize_mobile_context("live"),
        "output_schema": {
            "tick": {
                "title": "optional updated live segment title",
                "content": "next streamer segment, <= 120 Chinese characters",
                "live_status": "直播中",
                "viewers": "viewer count text",
                "likes": "like count text",
                "fans": "fan count text",
                "inner_thought": "optional inner thought, <= 80 Chinese characters",
                "danmaku": [{"author_name": "观众名", "author_type": "bystander", "content": "弹幕", "mood": "excited"}],
                "highlights": [{"author_name": "用户", "author_type": "bystander", "content": "醒目留言", "mood": "supportive", "amount": "6"}],
                "contributors": [{"name": "用户", "amount": "6", "note": "optional"}],
                "notification": "optional short notification text",
            }
        },
    }
    system_text = assembled_prompt_text("live") or system_prompt_text()
    user_text = (
        "Continue the current live room with one new live segment. "
        "Do not create a new live room. Update the existing stream only. "
        "Return valid JSON only, root shape {\"tick\":{...}}. "
        "The tick must include content, danmaku, highlights, contributors, viewers, likes and live_status. "
        "Keep output short: content <=120 Chinese characters, inner_thought <=80, notification <=40. "
        "Generate exactly 2 compact danmaku messages, 0-1 highlight message, and 0-2 contributor updates. "
        "Honor mobile_context.main_story_context as latest canon from the main story and current-card memories. "
        "Follow mobile_context.role_app_policy: streamer should match the current author if possible; viewers/highlight senders/contributors can be saved roles suitable for live or metadata-only bystanders. "
        "Keep the next segment concrete, in-world, and responsive to the previous content. "
        "Do not mention plugins, APIs, prompts, or JSON.\n"
        "Context JSON:\n"
        + json.dumps(context, ensure_ascii=False, separators=(",", ":"))
    )
    user_text = apply_custom_prompt_to_user_text("live", user_text)
    return [{"role": "system", "content": system_text}, {"role": "user", "content": user_text}]


def parse_live_tick(raw: str, event: dict[str, Any]) -> dict[str, Any]:
    tick, parse_error = parse_model_json_output(
        raw,
        scope="channel_live_tick",
        schema="tick",
        root_key="tick",
        target_id=event["event_id"],
    )
    if parse_error:
        return {}
    if isinstance(tick, dict) and isinstance(tick.get("tick"), dict):
        tick = tick["tick"]
    if not isinstance(tick, dict):
        record_parser_diagnostic("channel_live_tick", "tick", event["event_id"], "tick_not_object", raw)
        return {}
    content = compact_text(tick.get("content") or tick.get("body") or tick.get("text"), 1000)
    if not content:
        record_parser_diagnostic("channel_live_tick", "tick", event["event_id"], "tick_missing_content", raw)
        return {}
    return tick


def apply_live_tick(event: dict[str, Any], tick: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(event.get("metadata") or {})
    existing_danmaku = sanitize_live_messages(metadata.get("danmaku"), limit=80)
    new_danmaku = sanitize_live_messages(tick.get("danmaku") or tick.get("messages"), limit=12)
    existing_highlights = sanitize_live_messages(metadata.get("highlights"), limit=12)
    new_highlights = sanitize_live_messages(tick.get("highlights") or tick.get("highlight_messages"), limit=4)
    existing_contributors = sanitize_live_contributors(metadata.get("contributors"))
    new_contributors = sanitize_live_contributors(tick.get("contributors"))
    metadata["danmaku"] = sanitize_live_messages([*existing_danmaku, *new_danmaku], limit=80)
    metadata["highlights"] = sanitize_live_messages([*new_highlights, *existing_highlights], limit=12)
    metadata["contributors"] = merge_live_contributors(existing_contributors, new_contributors)
    metadata["viewers"] = compact_text(tick.get("viewers"), 40) or next_live_metric(metadata.get("viewers"), 900, 37 + len(new_danmaku) * 5)
    metadata["likes"] = compact_text(tick.get("likes"), 40) or next_live_metric(metadata.get("likes"), 120, 8 + len(new_danmaku))
    metadata["fans"] = compact_text(tick.get("fans"), 40) or metadata.get("fans") or next_live_metric(metadata.get("viewers"), 900, 12)
    metadata["live_status"] = compact_text(tick.get("live_status"), 40) or metadata.get("live_status") or "直播中"
    metadata["inner_thought"] = compact_text(tick.get("inner_thought"), 500) or metadata.get("inner_thought", "")
    metadata["live_tick"] = str(live_metric_int(metadata.get("live_tick"), 0) + 1)
    metadata["refreshed_at"] = now_iso()
    event["metadata"] = metadata
    event["title"] = compact_text(tick.get("title"), 120) or event.get("title") or "直播"
    event["content"] = compact_text(tick.get("content") or tick.get("body") or tick.get("text"), 2000) or event.get("content", "")
    if tick.get("tags"):
        event["tags"] = sanitize_tags(tick.get("tags"))
    event["updated_at"] = now_iso()
    return event


async def advance_live_event(channel: dict[str, Any], event: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    job = begin_generation_job("channel_live_tick", event["event_id"])
    try:
        raw_reply = await call_chat_model(
            build_live_tick_messages(channel, event),
            max_tokens=min(2200, max(get_settings()["max_tokens"], 1200)),
            temperature=read_mobile_llm_config()["temperature"],
        )
    except HTTPException as exc:
        finish_generation_job(job, "error", compact_text(exc.detail, 240))
        raise
    tick = parse_live_tick(raw_reply, event)
    if not tick:
        finish_generation_job(job, "error", "parser_no_valid_live_tick")
        raise HTTPException(status_code=502, detail="模型返回的直播续写无法解析，请查看后台 diagnostics。")
    updated = update_channel_event(channel["channel_id"], apply_live_tick({**event}, tick))
    notification_text = compact_text(tick.get("notification"), 160) or f"{updated['author_name']} 的直播有新内容：{updated['content'][:80]}"
    notification = add_notification("直播更新", notification_text, source="live", channel_id=channel["channel_id"], event_id=updated["event_id"])
    record_live_tick_diagnostic(channel, updated, status="success")
    finish_generation_job(job, "success")
    return updated, notification


def build_mail_reply_messages(event: dict[str, Any], user_content: str) -> list[dict[str, str]]:
    context = {
        "mail": {
            "title": event.get("title", ""),
            "content": event.get("content", ""),
            "author_name": event.get("author_name", ""),
            "metadata": event.get("metadata", {}),
        },
        "user_reply": user_content,
        "mobile_context": summarize_mobile_context("mail"),
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
        "Honor mobile_context.main_story_context as latest canon from the main story and current-card memories. "
        "Follow mobile_context.role_app_policy when choosing relevant mail contacts; prefer saved roles suitable for mail and never use roles blocked from mail. "
        "Each reply must include author_name, direction, content and mood. Keep content <= 220 Chinese characters. "
        "Do not mention plugins, APIs, prompts, or JSON.\n"
        "Context JSON:\n"
        + json.dumps(context, ensure_ascii=False, separators=(",", ":"))
    )
    user_text = apply_custom_prompt_to_user_text("mail", user_text)
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
            temperature=read_mobile_llm_config()["temperature"],
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


def is_reasoning_only_error(exc: HTTPException) -> bool:
    detail = compact_text(exc.detail, 240).lower()
    return "只返回了推理内容" in detail or "reasoning" in detail


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
    payload = read_json(card_notifications_path(), DEFAULT_NOTIFICATIONS)
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
    write_json(card_notifications_path(), {"schema_version": 1, "items": sanitized[:300]})
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
    payload = read_json(card_phone_calls_path(), DEFAULT_PHONE_CALLS)
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
    write_json(card_phone_calls_path(), {"schema_version": 1, "sessions": sanitized[:80]})
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
        if not role_app_allowed(profile, "phone"):
            continue
        add_role(profile["role_id"], profile["display_name"], profile.get("summary"), profile.get("avatar"), profile.get("chat_style"), profile.get("status"))
    profiles_by_id = profile_lookup()
    for member in available_role_members().get("roles", []):
        profile = profiles_by_id.get(normalize_id(member.get("role_id"), ""))
        if profile and not role_app_allowed(profile, "phone"):
            continue
        add_role(member.get("role_id"), member.get("name"), member.get("summary"), member.get("avatar"))
    for group in get_groups():
        for member in group.get("members", []):
            if member.get("type") == "character":
                profile = profiles_by_id.get(normalize_id(member.get("role_id"), ""))
                if profile and not role_app_allowed(profile, "phone"):
                    continue
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
            "usage_in_phone": role_app_usage(role, "phone"),
        },
        "mobile_context": summarize_mobile_context("phone"),
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
        "The target role is already filtered for the phone app; keep the conversation consistent with role.usage_in_phone and mobile_context.role_app_policy. "
        "Honor mobile_context.main_story_context as latest canon from the main story and current-card memories. "
        "If the role naturally ends the call, set call_state to ended and make the final line sound like a real phone goodbye.\n"
        + json.dumps(context, ensure_ascii=False, indent=2)
    )
    user_text = apply_custom_prompt_to_user_text("phone", user_text)
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


def read_mobile_llm_config() -> dict[str, Any]:
    settings = get_settings()
    if settings.get("model_source") == "custom":
        config = sanitize_api_config(settings.get("api_config"))
        config["provider"] = "mobile_custom"
        config["model_source"] = "custom"
        return config

    config = read_main_llm_config()
    route = read_route_forwarding_fallback()
    config["provider"] = "route_forwarding" if route.get("base_url") and route.get("base_url") == config.get("base_url") else "main_settings"
    config["model_source"] = "main"
    return config


def build_api_url(base_url: str, endpoint: str) -> str:
    clean_base = compact_text(base_url, 500).rstrip("/")
    clean_endpoint = endpoint.strip("/")
    if not clean_base:
        return ""
    if clean_base.endswith(f"/{clean_endpoint}") or clean_base.endswith(clean_endpoint):
        return clean_base
    return f"{clean_base}/{clean_endpoint}"


def provider_strategy_for_config(config: dict[str, Any] | None = None) -> dict[str, Any]:
    source = config or read_mobile_llm_config()
    base_url = compact_text(source.get("base_url"), 500).lower()
    model = compact_text(source.get("model"), 160).lower()
    provider = compact_text(source.get("provider"), 80)

    strategy = {
        "provider": provider or "openai_compatible",
        "profile": "openai_compatible",
        "label": "OpenAI-compatible",
        "supports_stream": True,
        "supports_model_list": True,
        "model_list_endpoint": "models",
        "chat_endpoint": "chat/completions",
        "error_detail_paths": ["error.message", "message", "detail"],
        "prompt_injection_strategy": "system_and_user_when_custom",
        "parser_profile": "json_lenient",
        "send_reasoning_effort": should_request_low_reasoning(source.get("model", "")),
        "notes": "Default OpenAI-compatible strategy.",
    }

    hints = [base_url, model, provider.lower()]
    joined = " ".join(hints)
    if "minimax" in joined or "abab" in joined:
        strategy.update({
            "profile": "minimax",
            "label": "MiniMax",
            "supports_stream": False,
            "error_detail_paths": ["base_resp.status_msg", "error.message", "message"],
            "prompt_injection_strategy": "system_and_user_when_custom",
            "parser_profile": "json_lenient_think_fence",
            "notes": "MiniMax-M3 has been verified with custom prompt mirrored into the final user message.",
        })
    elif "bigmodel" in joined or "glm" in joined:
        strategy.update({
            "profile": "glm",
            "label": "GLM / BigModel",
            "error_detail_paths": ["error.message", "msg", "message"],
            "parser_profile": "json_lenient_think_fence",
            "notes": "GLM-compatible endpoint; keep model-list and error shape visible in diagnostics.",
        })
    elif "generativelanguage" in joined or "gemini" in joined:
        strategy.update({
            "profile": "gemini",
            "label": "Gemini compatible",
            "supports_stream": False,
            "error_detail_paths": ["error.message", "message", "detail"],
            "parser_profile": "json_lenient_think_fence",
            "notes": "Gemini OpenAI-compatible paths can vary by gateway; verify with Prompt test before release.",
        })
    elif "anthropic" in joined or "claude" in joined:
        strategy.update({
            "profile": "claude",
            "label": "Claude compatible",
            "error_detail_paths": ["error.message", "message", "detail"],
            "parser_profile": "json_lenient_think_fence",
            "notes": "Claude-compatible gateway strategy; direct Anthropic Messages API is not used here.",
        })
    elif "deepseek" in joined:
        strategy.update({
            "profile": "deepseek",
            "label": "DeepSeek compatible",
            "error_detail_paths": ["error.message", "message", "detail"],
            "parser_profile": "json_lenient_think_fence",
            "notes": "DeepSeek OpenAI-compatible strategy.",
        })
    return strategy


def should_request_low_reasoning(model: str) -> bool:
    normalized = compact_text(model, 160).lower()
    return any(hint in normalized for hint in REASONING_MODEL_HINTS)


def chat_model_extra_payload(config: dict[str, Any]) -> dict[str, Any]:
    strategy = provider_strategy_for_config(config)
    if strategy.get("send_reasoning_effort"):
        return {"reasoning_effort": "low"}
    return {}


def should_bypass_route_forwarding(config: dict[str, Any]) -> bool:
    return bool(config.get("model_source") == "custom" and ROUTE_FORWARDING_HOOK_DEPTH is not None)


def extract_model_ids(payload: Any) -> list[str]:
    rows: list[Any] = []
    if isinstance(payload, dict):
        if isinstance(payload.get("data"), list):
            rows = payload["data"]
        elif isinstance(payload.get("models"), list):
            rows = payload["models"]
        elif isinstance(payload.get("model_list"), list):
            rows = payload["model_list"]
    elif isinstance(payload, list):
        rows = payload

    models: list[str] = []
    seen: set[str] = set()
    for item in rows:
        model_id = ""
        if isinstance(item, dict):
            model_id = compact_text(item.get("id") or item.get("name") or item.get("model"), 200)
        else:
            model_id = compact_text(item, 200)
        if model_id and model_id not in seen:
            seen.add(model_id)
            models.append(model_id)
    return models


async def fetch_mobile_models(base_url: str, api_key: str, request_timeout: int) -> list[str]:
    url = build_api_url(base_url, "models")
    if not url:
        raise HTTPException(status_code=400, detail="请先填写 Base URL。")
    headers = {"Content-Type": "application/json"}
    if compact_text(api_key, 500):
        headers["Authorization"] = f"Bearer {compact_text(api_key, 500)}"

    try:
        async with httpx.AsyncClient(timeout=float(request_timeout)) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code if exc.response is not None else 502
        detail = ""
        if exc.response is not None:
            try:
                detail = exc.response.text.strip()[:500]
            except Exception:
                detail = ""
        message = f"拉取模型列表失败：HTTP {status_code}。"
        if detail:
            message = f"{message} upstream={detail}"
        raise HTTPException(status_code=502, detail=message) from exc
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="拉取模型列表超时，请稍后重试。") from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="无法连接模型列表接口，请检查 Base URL 和网络。") from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="模型列表接口返回的不是合法 JSON。") from exc

    return extract_model_ids(payload)


async def call_chat_model(messages: list[dict[str, str]], *, max_tokens: int, temperature: float) -> str:
    config = read_mobile_llm_config()
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
    route_bypass_token = None
    try:
        if should_bypass_route_forwarding(config):
            route_bypass_token = ROUTE_FORWARDING_HOOK_DEPTH.set(ROUTE_FORWARDING_HOOK_DEPTH.get() + 1)
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
        response_text = ""
        if exc.response is not None:
            try:
                response_text = exc.response.text.strip()[:500]
            except Exception:
                response_text = ""
        detail = f"模型服务返回 HTTP {status_code}。"
        if response_text:
            detail = f"{detail} upstream={response_text}"
        raise HTTPException(status_code=502, detail=detail) from exc
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="模型服务响应超时，请稍后重试。") from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="无法连接聊天模型服务，请检查网络与 API 地址。") from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="模型服务返回的不是合法 JSON。") from exc
    finally:
        if route_bypass_token is not None and ROUTE_FORWARDING_HOOK_DEPTH is not None:
            ROUTE_FORWARDING_HOOK_DEPTH.reset(route_bypass_token)
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
        if custom_prompt_for_scope("group_chat", settings):
            return assembled_prompt_text("group_chat")
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
        "role_app_policy": role_app_generation_policy("group_chat"),
        "available_stickers": sticker_prompt_catalog(),
        "main_story_context": main_story_context_payload(),
    }
    user_text = (
        "请根据以下群聊上下文生成本轮回复，只返回 JSON：\n"
        "Follow role_app_policy and each member usage_in_group_chat/app_roles; avoid choosing members explicitly blocked from group_chat.\n"
        "Honor main_story_context as latest canon from the main story and current-card memories; do not roll back relationship or plot stages already established there.\n"
        + json.dumps(context, ensure_ascii=False, indent=2)
    )
    user_text = apply_custom_prompt_to_user_text("group_chat", user_text)
    return [
        {"role": "system", "content": system_prompt_text()},
        {
            "role": "user",
            "content": user_text,
        },
    ]


def strip_thinking_sections(text: str) -> str:
    raw = str(text or "")
    previous = None
    while previous != raw:
        previous = raw
        raw = re.sub(r"<think>[\s\S]*?</think>", "", raw, flags=re.IGNORECASE).strip()
    return raw


def strip_json_fence(text: str) -> str:
    raw = strip_thinking_sections(text).strip()
    fenced = re.search(r"```(?:json|JSON)?\s*([\s\S]*?)```", raw, re.IGNORECASE)
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


def loads_json_lenient_with_reason(text: str) -> tuple[Any, str]:
    original = str(text or "")
    cleaned = strip_json_fence(original)
    think_stripped = strip_thinking_sections(original) != original
    for candidate_index, candidate in enumerate(json_text_candidates(original)):
        variants = [
            (candidate, "direct"),
            (escape_json_string_newlines(candidate), "escaped_newlines"),
            (re.sub(r",\s*([}\]])", r"\1", candidate), "trimmed_trailing_commas"),
            (re.sub(r",\s*([}\]])", r"\1", escape_json_string_newlines(candidate)), "escaped_newlines_trimmed_trailing_commas"),
        ]
        for variant, reason in variants:
            try:
                payload = json.loads(variant)
                notes: list[str] = []
                if think_stripped:
                    notes.append("think_stripped")
                if strip_json_fence(original) != original.strip():
                    notes.append("fence_or_wrapper_stripped")
                if candidate_index > 0 or candidate.strip() != cleaned.strip():
                    notes.append("json_substring_extracted")
                if reason != "direct":
                    notes.append(reason)
                return payload, "+".join(notes) if notes else "direct"
            except ValueError:
                continue
    return None, "json_parse_failed"


def loads_json_lenient(text: str) -> Any:
    payload, _reason = loads_json_lenient_with_reason(text)
    return payload


def recover_json_array_items(text: str, root_key: str, *, limit: int = 20) -> list[dict[str, Any]]:
    cleaned = strip_json_fence(text)
    match = re.search(rf'"{re.escape(root_key)}"\s*:\s*\[', cleaned)
    if not match:
        return []
    rows: list[dict[str, Any]] = []
    depth = 0
    item_start: int | None = None
    in_string = False
    escaped = False
    for index in range(match.end(), len(cleaned)):
        char = cleaned[index]
        if escaped:
            escaped = False
            continue
        if char == "\\" and in_string:
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            if depth == 0:
                item_start = index
            depth += 1
            continue
        if char == "}":
            if depth <= 0:
                continue
            depth -= 1
            if depth == 0 and item_start is not None:
                item = loads_json_lenient(cleaned[item_start : index + 1])
                if isinstance(item, dict):
                    rows.append(item)
                item_start = None
                if len(rows) >= limit:
                    break
            continue
        if char == "]" and depth == 0:
            break
    return rows



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
    payload = read_json(card_parser_diagnostics_path(), {"schema_version": 1, "items": []})
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
    write_json(card_parser_diagnostics_path(), {"schema_version": 1, "items": rows[:80]})


def parse_model_json_output(raw: str, *, scope: str, schema: str, root_key: str, target_id: str = "") -> tuple[Any, str]:
    cleaned = strip_json_fence(raw)
    payload, recovery_reason = loads_json_lenient_with_reason(raw)
    if payload is None:
        recovered = recover_json_array_items(cleaned, root_key)
        if recovered:
            record_parser_diagnostic(scope, schema, target_id, "json_partial_recovered", raw)
            return recovered, ""
        record_parser_diagnostic(scope, schema, target_id, "json_parse_failed", raw)
        return None, "json_parse_failed"
    if recovery_reason and recovery_reason != "direct":
        record_parser_diagnostic(scope, schema, target_id, f"json_recovered:{recovery_reason}", raw)
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
        speaker_value = compact_text(
            item.get("speaker")
            or item.get("speaker_name")
            or item.get("speaker_id")
            or item.get("role_id")
            or item.get("name")
            or item.get("author")
            or item.get("author_name")
            or item.get("author_id"),
            80,
        )
        member = by_name.get(role_name_key(speaker_value)) or by_id.get(normalize_id(speaker_value))
        message_type = compact_text(item.get("type"), 20).lower()
        if not message_type and any(item.get(key) for key in ("content", "text", "body")):
            message_type = "text"
        if message_type in {"message", "reply"}:
            message_type = "text"
        content = compact_text(item.get("sticker") if message_type == "sticker" else item.get("content") or item.get("text") or item.get("body"), 280)
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
    return parsed


def group_async_lock(group_id: str) -> asyncio.Lock:
    safe_group_id = validate_group_id(group_id)
    with STORAGE_LOCK:
        return GROUP_ASYNC_LOCKS.setdefault(safe_group_id, asyncio.Lock())


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    ensure_runtime_data()
    return templates.TemplateResponse(request, "index.html", {"settings": settings_public_payload(get_settings())})


@app.get("/chat", response_class=HTMLResponse)
async def chat_index(request: Request) -> HTMLResponse:
    ensure_runtime_data()
    return templates.TemplateResponse(request, "chat.html", {"settings": settings_public_payload(get_settings())})


@app.get("/api/settings")
async def api_get_settings() -> dict[str, Any]:
    settings = settings_public_payload(get_settings())
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
    return {"ok": True, "settings": settings_public_payload(settings)}


@app.post("/api/admin/models")
async def api_admin_models(payload: ModelListPayload | None = None) -> dict[str, Any]:
    settings = get_settings()
    saved_api = sanitize_api_config(settings.get("api_config"))
    incoming = payload.model_dump(exclude_none=True) if payload else {}
    base_url = compact_text(incoming.get("base_url") or saved_api.get("base_url") or read_mobile_llm_config().get("base_url"), 500)
    request_api_key = compact_text(incoming.get("api_key"), 500)
    api_key = request_api_key or saved_api.get("api_key") or read_mobile_llm_config().get("api_key", "")
    request_timeout = clamp_int(incoming.get("request_timeout") or saved_api.get("request_timeout"), 10, 600, read_mobile_llm_config().get("request_timeout", 120))
    models = await fetch_mobile_models(base_url, api_key, request_timeout)
    current_model = compact_text(saved_api.get("model") or read_mobile_llm_config().get("model"), 160)
    preferred = current_model if current_model in models else (models[0] if models else "")
    return {"ok": True, "items": models, "current_model": current_model, "preferred_model": preferred}


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


@app.get("/api/roles/disabled")
async def api_get_disabled_roles() -> dict[str, Any]:
    roles = [role for role in get_role_profiles(include_disabled=True) if not role.get("enabled")]
    return {"ok": True, "roles": roles}


@app.post("/api/roles/{role_id}/restore")
async def api_restore_mobile_role(role_id: str) -> dict[str, Any]:
    safe_role_id = normalize_id(role_id)
    profiles = get_role_profiles(include_disabled=True)
    index = next((idx for idx, item in enumerate(profiles) if item["role_id"] == safe_role_id), None)
    if index is None:
        raise HTTPException(status_code=404, detail="\u89d2\u8272\u4e0d\u5b58\u5728\u3002")
    profiles[index] = {**profiles[index], "enabled": True, "updated_at": now_iso()}
    save_role_profiles(profiles)
    return {"ok": True, "role": profiles[index], "roles": [role for role in get_role_profiles(include_disabled=True) if not role.get("enabled")], "available": available_role_members()["roles"]}


@app.get("/api/admin/roles")
async def api_admin_roles() -> dict[str, Any]:
    return {"ok": True, "roles": get_role_profiles(include_disabled=True), "available": available_role_members()["roles"], "user": current_user_member()}


@app.get("/api/admin/role-app-pools")
async def api_admin_role_app_pools() -> dict[str, Any]:
    content_app_ids = set(CHANNEL_TYPES) | {"notifications"}
    apps = [
        app
        for app in sanitize_app_registry(read_json(APP_REGISTRY_PATH, DEFAULT_APP_REGISTRY)).get("apps", [])
        if normalize_id(app.get("app_id"), "") in content_app_ids and app.get("app_id") != "assist"
    ]
    pools: dict[str, Any] = {}
    all_roles = get_role_profiles(include_disabled=False)
    for app in apps:
        app_id = normalize_id(app.get("app_id"), "")
        if not app_id:
            continue
        roles = role_profiles_for_app(app_id, limit=80)
        suitable_count = sum(1 for role in roles if app_id in set(role.get("suitable_apps") or []))
        blocked_count = sum(1 for role in all_roles if not role_app_allowed(role, app_id))
        pools[app_id] = {
            "app_id": app_id,
            "label": compact_text(app.get("label"), 80) or app_id,
            "count": len(roles),
            "suitable_count": suitable_count,
            "neutral_count": max(0, len(roles) - suitable_count),
            "blocked_count": blocked_count,
            "policy": role_app_generation_policy(app_id),
            "roles": [
                {
                    "role_id": role["role_id"],
                    "display_name": role["display_name"],
                    "suitable_apps": role.get("suitable_apps", []),
                    "blocked_apps": role.get("blocked_apps", []),
                    "usage": role_app_usage(role, app_id),
                }
                for role in roles
            ],
        }
    return {"ok": True, "pools": pools}


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


@app.post("/api/admin/roles/{role_id}/restore")
async def api_restore_role(role_id: str) -> dict[str, Any]:
    safe_role_id = normalize_id(role_id)
    profiles = get_role_profiles(include_disabled=True)
    index = next((idx for idx, item in enumerate(profiles) if item["role_id"] == safe_role_id), None)
    if index is None:
        raise HTTPException(status_code=404, detail="角色不存在。")
    profiles[index] = {**profiles[index], "enabled": True, "updated_at": now_iso()}
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


@app.post("/api/role-generator/extract-chat")
async def api_role_generator_extract_chat(payload: RoleChatExtractPayload | None = None) -> dict[str, Any]:
    drafts = extract_main_chat_role_profiles(payload, source="chat_extract")
    return {"ok": True, "draft": drafts[0] if drafts else None, "drafts": drafts}


@app.post("/api/admin/role-generator/extract-chat")
async def api_admin_role_generator_extract_chat(payload: RoleChatExtractPayload | None = None) -> dict[str, Any]:
    drafts = extract_main_chat_role_profiles(payload, source="admin_chat_extract")
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
    members = sanitize_members(payload.members, ensure_user=False)
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
            merged["members"] = sanitize_members(updates["members"], ensure_user=False)
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
    job_finished = False
    async with group_async_lock(safe_group_id):
        try:
            group = get_group_or_404(safe_group_id)
            recent = get_messages(safe_group_id)
            user_message = append_group_messages(safe_group_id, [user_message_for(group, user_text)])[0]
            model_messages = build_mobile_model_messages(group, recent, user_text)
            settings = get_settings()
            try:
                raw_reply = await call_chat_model(
                    model_messages,
                    max_tokens=settings["max_tokens"],
                    temperature=read_mobile_llm_config()["temperature"],
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
                job_finished = True
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
                job_finished = True
                return JSONResponse(status_code=502, content={"ok": False, "user_message": user_message, "messages": stored_error, "error": error_message["content"]})
            stored_messages = append_group_messages(safe_group_id, ai_messages)
            finish_generation_job(job, "success")
            job_finished = True
            return {"ok": True, "user_message": user_message, "messages": stored_messages}
        except BaseException as exc:
            if not job_finished:
                finish_generation_job(job, "error", interrupted_generation_error(exc))
                job_finished = True
            raise
        finally:
            if not job_finished:
                finish_generation_job(job, "error", interrupted_generation_error())


@app.post("/api/continue", response_model=None)
async def api_continue(payload: ContinuePayload) -> JSONResponse | dict[str, Any]:
    safe_group_id = validate_group_id(payload.group_id)
    job = begin_generation_job("group_chat", safe_group_id)
    job_finished = False
    async with group_async_lock(safe_group_id):
        try:
            group = get_group_or_404(safe_group_id)
            recent = get_messages(safe_group_id)
            model_messages = build_mobile_model_messages(group, recent, "", generation_mode="role_continue")
            settings = get_settings()
            try:
                raw_reply = await call_chat_model(
                    model_messages,
                    max_tokens=settings["max_tokens"],
                    temperature=read_mobile_llm_config()["temperature"],
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
                job_finished = True
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
                job_finished = True
                return JSONResponse(status_code=502, content={"ok": False, "messages": stored_error, "error": error_message["content"]})
            stored_messages = append_group_messages(safe_group_id, ai_messages)
            finish_generation_job(job, "success")
            job_finished = True
            return {"ok": True, "messages": stored_messages}
        except BaseException as exc:
            if not job_finished:
                finish_generation_job(job, "error", interrupted_generation_error(exc))
                job_finished = True
            raise
        finally:
            if not job_finished:
                finish_generation_job(job, "error", interrupted_generation_error())


def model_status_deep() -> dict[str, Any]:
    config = read_mobile_llm_config()
    route = read_route_forwarding_fallback()
    return {
        "provider": config.get("provider", "main_settings"),
        "model_source": config.get("model_source", "main"),
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
        "settings_generation": settings_public_payload(get_settings()).get("generation", {}),
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


def prompt_test_root_key(scope: str) -> str:
    schema = next((item for item in channel_schema_catalog() if item["type"] == scope), None)
    return compact_text(schema.get("root") if schema else "", 40) or {
        "group_chat": "messages",
        "phone": "lines",
        "notification": "notifications",
    }.get(scope, "events")


def prompt_test_mock_raw(scope: str, user_input: str) -> str:
    payload = build_workbench_mock_payload(scope, user_input)
    # Intentionally wrap the JSON to exercise lenient parser paths used by real models.
    return "<think>mock reasoning should be stripped</think>\n```json\n" + json.dumps(payload, ensure_ascii=False) + "\n```"


def prompt_test_messages(scope: str, user_input: str, channel_id: str = "", role_id: str = "") -> tuple[list[dict[str, str]], dict[str, Any]]:
    target = normalize_prompt_scope(scope)
    context: dict[str, Any] = {"scope": target}
    if target == "group_chat":
        groups = get_groups()
        group = groups[0] if groups else default_group()
        recent_messages = get_messages(group["group_id"])[-8:] if groups else []
        text = compact_text(user_input, 1200) or "\u8bf7\u751f\u6210\u4e00\u8f6e\u5c0f\u624b\u673a\u7fa4\u804a\u6d4b\u8bd5\u56de\u590d\u3002"
        context["group_id"] = group.get("group_id")
        return build_mobile_model_messages(group, recent_messages, text), context
    if target == "phone":
        candidates = phone_role_candidates()
        selected_role_id = normalize_id(role_id or (candidates[0]["role_id"] if candidates else ""))
        role = get_phone_role_or_404(selected_role_id)
        session = {
            "session_id": make_id("prompttest"),
            "role_id": role["role_id"],
            "role_name": role["display_name"],
            "status": "ongoing",
            "lines": [],
        }
        text = compact_text(user_input, 1200) or "\u4f60\u597d\uff0c\u8bf7\u7528\u7535\u8bdd\u53e3\u543b\u56de\u590d\u4e00\u53e5\u3002"
        context["role_id"] = role["role_id"]
        return build_phone_call_messages(role, session, text), context
    channel_scopes = {"feed", "forum", "mail", "diary", "calendar", "live"}
    if target in channel_scopes:
        channel = workbench_channel_for_scope(target, channel_id)
        messages = build_channel_seed_messages(channel, 1)
        custom_text = compact_text(user_input, 1200)
        if custom_text:
            messages = [*messages, {"role": "user", "content": apply_custom_prompt_to_user_text(target, f"Prompt test extra context: {custom_text}")}]
        context["channel_id"] = channel["channel_id"]
        return messages, context
    preview = prompt_preview_payload(target)
    text = compact_text(user_input, 1200) or f"Generate a {target} JSON payload for prompt testing."
    return [
        {"role": "system", "content": preview["assembled_prompt"] or system_prompt_text()},
        {"role": "user", "content": apply_custom_prompt_to_user_text(target, text)},
    ], context


def redact_prompt_test_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {"role": compact_text(item.get("role"), 40), "content": compact_text(item.get("content"), 12000)}
        for item in messages
        if isinstance(item, dict)
    ]


async def run_prompt_test(payload: PromptTestPayload) -> dict[str, Any]:
    scope = normalize_prompt_scope(payload.scope)
    mode = normalize_id(payload.mode, "dry-run")
    if mode not in {"dry-run", "mock", "real"}:
        raise HTTPException(status_code=400, detail="\u4e0d\u652f\u6301\u7684 Prompt \u6d4b\u8bd5\u6a21\u5f0f\u3002")

    user_input = compact_text(payload.user_input, 1200)
    preview = prompt_preview_payload(scope)
    config = read_mobile_llm_config()
    strategy = provider_strategy_for_config(config)
    messages, context = prompt_test_messages(scope, user_input, payload.channel_id or "", payload.role_id or "")
    root_key = prompt_test_root_key(scope)
    result: dict[str, Any] = {
        "mode": mode,
        "scope": scope,
        "scope_label": PROMPT_SCOPE_LABELS.get(scope, scope),
        "assembled_prompt": preview.get("assembled_prompt", ""),
        "messages": redact_prompt_test_messages(messages),
        "root_key": root_key,
        "provider_strategy": strategy,
        "model_context": {
            "model_source": config.get("model_source", ""),
            "provider": config.get("provider", ""),
            "model": config.get("model", ""),
            "base_url_host": safe_url_host(config.get("base_url", "")),
            "request_timeout": config.get("request_timeout"),
        },
        "save": False,
        "context": context,
    }
    if mode == "dry-run":
        return result

    raw_reply = prompt_test_mock_raw(scope, user_input) if mode == "mock" else await call_chat_model(
        messages,
        max_tokens=min(get_settings()["max_tokens"], 1200),
        temperature=read_mobile_llm_config()["temperature"],
    )
    parsed, parse_error = parse_model_json_output(
        raw_reply,
        scope=f"prompt_test_{scope}",
        schema=root_key,
        root_key=root_key,
        target_id=compact_text(context.get("channel_id") or context.get("role_id") or context.get("group_id"), 120),
    )
    parsed_output = {root_key: parsed} if isinstance(parsed, list) else parsed
    result.update({
        "raw_reply": compact_text(raw_reply, 12000),
        "parsed": parsed_output,
        "parse_error": parse_error,
        "diagnostics": get_parser_diagnostics()[:5],
    })
    return result


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
                temperature=read_mobile_llm_config()["temperature"],
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
                temperature=read_mobile_llm_config()["temperature"],
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



def prune_ended_phone_sessions() -> dict[str, Any]:
    sessions = get_phone_sessions()
    kept = [item for item in sessions if item.get("status") != "ended"]
    save_phone_sessions(kept)
    return {"removed_count": len(sessions) - len(kept), "remaining_count": len(kept)}


def delete_phone_session(session_id: str) -> dict[str, Any]:
    safe_session_id = normalize_id(session_id, "")
    if not safe_session_id:
        raise HTTPException(status_code=400, detail="Phone session id is required.")
    sessions = get_phone_sessions()
    kept = [item for item in sessions if item.get("session_id") != safe_session_id]
    if len(kept) == len(sessions):
        raise HTTPException(status_code=404, detail="Phone session not found.")
    save_phone_sessions(kept)
    return {"deleted_session_id": safe_session_id, "remaining_count": len(kept)}


def delete_channel_event(channel_id: str, event_id: str) -> dict[str, Any]:
    channel = get_channel_or_404(channel_id)
    safe_event_id = normalize_id(event_id, "")
    if not safe_event_id:
        raise HTTPException(status_code=400, detail="Event id is required.")
    events = get_channel_events(channel["channel_id"])
    kept = [item for item in events if item.get("event_id") != safe_event_id]
    if len(kept) == len(events):
        raise HTTPException(status_code=404, detail="Event not found.")
    save_channel_events(channel["channel_id"], kept)
    return {"channel": channel, "deleted_event_id": safe_event_id, "remaining_count": len(kept)}


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
        return JSONResponse(status_code=exc.status_code, content=mobile_error_payload(exc))


@app.post("/api/admin/prompt-test", response_model=None)
async def api_admin_prompt_test(payload: PromptTestPayload) -> JSONResponse | dict[str, Any]:
    try:
        result = await run_prompt_test(payload)
        return {"ok": True, **result}
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content=mobile_error_payload(exc))


@app.get("/api/admin/provider-strategy")
async def api_admin_provider_strategy() -> dict[str, Any]:
    config = read_mobile_llm_config()
    return {"ok": True, "strategy": provider_strategy_for_config(config), "model_context": mobile_error_payload(HTTPException(status_code=200, detail="ok")).get("model_context", {})}


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
    write_json(card_generation_state_path(), DEFAULT_GENERATION_STATE)
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



@app.post("/api/admin/data/channels/clear-test-events")
async def api_admin_clear_all_channel_test_events() -> dict[str, Any]:
    results = [clear_channel_test_events(channel["channel_id"]) for channel in get_channels(include_disabled=True)]
    return {"ok": True, "results": results, "removed_count": sum(item.get("removed_count", 0) for item in results), "data": admin_data_overview()}


@app.delete("/api/admin/data/channels/{channel_id}/events/{event_id}")
async def api_admin_delete_channel_event(channel_id: str, event_id: str) -> dict[str, Any]:
    return {"ok": True, **delete_channel_event(channel_id, event_id), "data": admin_data_overview()}


@app.post("/api/admin/data/phone/prune-ended")
async def api_admin_prune_ended_phone_sessions() -> dict[str, Any]:
    return {"ok": True, **prune_ended_phone_sessions(), "data": admin_data_overview()}


@app.delete("/api/admin/data/phone/sessions/{session_id}")
async def api_admin_delete_phone_session(session_id: str) -> dict[str, Any]:
    return {"ok": True, **delete_phone_session(session_id), "data": admin_data_overview()}

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


@app.patch("/api/channels/{channel_id}/events/{event_id}")
async def api_patch_channel_event(channel_id: str, event_id: str, payload: ChannelEventPatchPayload) -> dict[str, Any]:
    channel = get_channel_or_404(channel_id)
    if channel["type"] != "mail":
        raise HTTPException(status_code=400, detail="Only mail events support read-state updates.")
    event = find_channel_event_or_404(channel["channel_id"], event_id)
    if payload.read is not None:
        metadata = dict(event.get("metadata") or {})
        read_state = bool(payload.read)
        event["read"] = read_state
        metadata["read"] = read_state
        metadata["unread"] = not read_state
        metadata["status"] = "已读" if read_state else "未读"
        if read_state:
            metadata["read_at"] = now_iso()
        event["metadata"] = metadata
        event["updated_at"] = now_iso()
        event = update_channel_event(channel["channel_id"], event)
    return {"ok": True, "event": event, "events": get_channel_events(channel["channel_id"])}

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
            content=mobile_error_payload(exc, extra={"event": event, "events": get_channel_events(channel["channel_id"])}),
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
            content=mobile_error_payload(exc, extra={"event": event, "events": get_channel_events(channel["channel_id"])}),
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
                content=mobile_error_payload(exc, extra={"event": event, "events": get_channel_events(channel["channel_id"])}),
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


@app.post("/api/channels/{channel_id}/outgoing-mails", response_model=None)
async def api_create_outgoing_mail(channel_id: str, payload: MailOutgoingPayload) -> JSONResponse | dict[str, Any]:
    channel = get_channel_or_404(channel_id)
    if channel["type"] != "mail":
        raise HTTPException(status_code=400, detail="This channel does not support outgoing mail.")
    content = compact_text(payload.content, 1200)
    if not content:
        raise HTTPException(status_code=400, detail="邮件正文不能为空。")
    recipient_id = normalize_id(payload.recipient_id, "")
    recipient = next((role for role in available_role_members().get("roles", []) if normalize_id(role.get("role_id"), "") == recipient_id), None)
    if not recipient:
        raise HTTPException(status_code=400, detail="请选择当前角色卡里的收件人。")
    recipient_name = compact_text(recipient.get("name") or recipient.get("display_name"), 80) or "对方"
    title = compact_text(payload.title, 120) or f"写给{recipient_name}的邮件"
    event = {
        "title": title,
        "content": content,
        "event_type": "mail",
        "author_id": "user",
        "author_name": "我",
        "tags": ["sent"],
        "metadata": {
            "direction": "sent",
            "folder": "sent",
            "recipient_id": recipient_id,
            "recipient_name": recipient_name,
            "read": True,
            "unread": False,
            "status": "已发送",
            "replies": [],
        },
        "source": "user",
    }
    stored = append_channel_events(channel["channel_id"], [event])
    if not stored:
        raise HTTPException(status_code=400, detail="Event content is empty.")
    event = stored[0]
    generated: list[dict[str, Any]] = []
    if payload.generate_reply is not False:
        reply_seed = {
            **event,
            "author_id": recipient_id,
            "author_name": recipient_name,
            "content": f"我发给{recipient_name}的邮件：{content}",
        }
        try:
            generated = await generate_mail_reply(reply_seed, content)
        except HTTPException as exc:
            notification_from_event(event)
            return JSONResponse(
                status_code=exc.status_code,
                content=mobile_error_payload(exc, extra={"event": event, "events": get_channel_events(channel["channel_id"])}),
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


@app.post("/api/channels/{channel_id}/events/{event_id}/live-tick", response_model=None)
async def api_advance_live_event(channel_id: str, event_id: str) -> JSONResponse | dict[str, Any]:
    channel = get_channel_or_404(channel_id)
    if channel["type"] != "live":
        raise HTTPException(status_code=400, detail="This channel does not support live tick generation.")
    event = find_channel_event_or_404(channel["channel_id"], event_id)
    try:
        updated, notification = await advance_live_event(channel, event)
    except HTTPException as exc:
        record_live_tick_diagnostic(channel, event, status="error", error=compact_text(exc.detail, 240))
        return JSONResponse(status_code=exc.status_code, content=mobile_error_payload(exc, extra={"event": event, "events": get_channel_events(channel["channel_id"])}))
    return {"ok": True, "event": updated, "events": get_channel_events(channel["channel_id"]), "notification": notification}


async def run_channel_seed(channel: dict[str, Any], count: int) -> dict[str, Any]:
    count = effective_channel_seed_count(channel, count)
    job = begin_generation_job(f"channel_{channel['type']}", channel["channel_id"])
    try:
        raw_reply = await call_chat_model(
            build_channel_seed_messages(channel, count),
            max_tokens=channel_seed_max_tokens(channel, count),
            temperature=read_mobile_llm_config()["temperature"],
        )
    except HTTPException as exc:
        if not is_reasoning_only_error(exc):
            finish_generation_job(job, "error", compact_text(exc.detail, 240))
            raise
        try:
            raw_reply = await call_chat_model(
                build_channel_seed_retry_messages(channel, count),
                max_tokens=channel_seed_max_tokens(channel, count, retry=True),
                temperature=read_mobile_llm_config()["temperature"],
            )
        except HTTPException as retry_exc:
            finish_generation_job(job, "error", compact_text(retry_exc.detail, 240))
            raise retry_exc
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
    count = effective_channel_seed_count(channel, payload.count if payload else None)
    try:
        return await run_channel_seed(channel, count)
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content=mobile_error_payload(exc))


@app.post("/api/admin/seed-channel", response_model=None)
async def api_admin_seed_channel(payload: ChannelSeedPayload) -> JSONResponse | dict[str, Any]:
    channel = get_channel_or_404(payload.channel_id)
    existing = get_channel_events(channel["channel_id"])
    if existing and not payload.force:
        return {"ok": True, "channel": channel, "events": existing[: effective_channel_seed_count(channel)], "skipped": True}
    count = effective_channel_seed_count(channel, payload.count)
    try:
        return await run_channel_seed(channel, count)
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content=mobile_error_payload(exc))


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
            temperature=read_mobile_llm_config()["temperature"],
        )
    except HTTPException as exc:
        finish_generation_job(job, "error", compact_text(exc.detail, 240))
        return JSONResponse(status_code=exc.status_code, content=mobile_error_payload(exc, extra={"session": session}))
    lines, call_state = parse_phone_lines(raw_reply, role)
    if not lines:
        finish_generation_job(job, "error", "parser_no_valid_lines")
        parse_exc = HTTPException(status_code=502, detail="\u6a21\u578b\u8fd4\u56de\u5185\u5bb9\u65e0\u6cd5\u89e3\u6790\uff0c\u8bf7\u67e5\u770b\u540e\u53f0 diagnostics\u3002")
        return JSONResponse(status_code=502, content=mobile_error_payload(parse_exc, extra={"session": session}))
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
        "settings": settings_public_payload(get_settings()),
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
    config = read_mobile_llm_config()
    api_url = build_api_url(config["base_url"], "chat/completions")
    return {
        "configured": bool(api_url and config["model"]),
        "provider": config.get("provider", "main_settings"),
        "model_source": config.get("model_source", "main"),
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
        "groups": card_groups_path(),
        "roles": card_role_profiles_path(),
        "automation": AUTOMATION_STATE_PATH,
        "prompt_blocks": PROMPT_BLOCKS_PATH,
        "app_registry": APP_REGISTRY_PATH,
        "channels": CHANNELS_PATH,
        "notifications": card_notifications_path(),
        "phone_calls": card_phone_calls_path(),
        "generation_state": card_generation_state_path(),
        "parser_diagnostics": card_parser_diagnostics_path(),
    }
    try:
        data_dir_label = str(DATA_DIR.relative_to(PROJECT_ROOT))
    except ValueError:
        data_dir_label = str(DATA_DIR)
    return {
        "data_dir": data_dir_label,
        "files": {key: path.exists() for key, path in expected_files.items()},
        "card_uid": current_mobile_card_uid(),
        "card_data_dir": str(current_mobile_card_dir()),
        "events_dir_exists": card_events_dir().exists(),
        "channel_event_counts": {channel["channel_id"]: len(get_channel_events(channel["channel_id"])) for channel in channels},
        "notification_count": len(notifications),
        "unread_notification_count": len([item for item in notifications if not item["read"]]),
        "phone_session_count": len(phone_sessions),
        "active_generation_jobs": len(generation_state["active_jobs"]),
        "last_generation_jobs": generation_state["last_jobs"][:5],
        "recent_live_ticks": generation_state.get("recent_live_ticks", [])[:10],
        "parser_diagnostics": get_parser_diagnostics()[:10],
        "isolation": {
            "writes_main_chat": False,
            "writes_role_card": False,
            "writes_worldbook": False,
            "plugin_data_root": "data/mobile_chat",
            "card_data_root": "data/mobile_chat/cards/{card_uid}",
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
        "settings": settings_public_payload(get_settings()),
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
