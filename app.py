import asyncio
import json
import logging
import os
import re
import shutil
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from chat_api_routes import register_chat_api_routes
from config_api_routes import register_config_api_routes
from page_routes import register_page_routes
from preset_rules import (
    PRESET_MODULE_RULES,
    activate_preset_in_store,
    build_preset_prompt_from_preset,
    create_preset_in_store,
    default_preset_store as default_preset_store_data,
    delete_preset_from_store,
    duplicate_preset_in_store,
    get_active_preset_from_store,
    sanitize_preset_store as sanitize_preset_store_data,
)
from slot_runtime import SlotRuntimeService
from workshop_logic import (
    build_workshop_trigger_token,
    default_workshop_state,
    get_workshop_stage,
    get_workshop_stage_label,
    get_workshop_trigger_label,
    normalize_workshop_action_type,
    normalize_workshop_stage,
    normalize_workshop_trigger_mode,
    sanitize_creative_workshop,
    sanitize_workshop_state,
    select_workshop_match,
    workshop_effective_fields,
    workshop_rule_matches_trigger,
)
from worldbook_logic import (
    DEFAULT_WORLDBOOK_SETTINGS,
    default_worldbook_store,
    keyword_matches_query,
    normalize_match_text,
    sanitize_worldbook,
    sanitize_worldbook_entry,
    sanitize_worldbook_settings,
    sanitize_worldbook_store,
    split_trigger_aliases,
)


def get_runtime_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        try:
            exe_dir.mkdir(parents=True, exist_ok=True)
            probe_path = exe_dir / ".xuqi_write_test"
            probe_path.write_text("ok", encoding="utf-8")
            probe_path.unlink(missing_ok=True)
            return exe_dir
        except OSError:
            local_app_data = os.environ.get("LOCALAPPDATA")
            if local_app_data:
                return Path(local_app_data) / "XuqiLLMChat"
            return Path.home() / "AppData" / "Local" / "XuqiLLMChat"
    return Path(__file__).resolve().parent


def get_resource_dir() -> Path:
    if getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


BASE_DIR = get_runtime_base_dir()
RESOURCE_DIR = get_resource_dir()
DATA_DIR = BASE_DIR / "data"
SLOTS_DIR = DATA_DIR / "slots"
STATIC_DIR = BASE_DIR / "static"
RESOURCE_STATIC_DIR = RESOURCE_DIR / "static"
TEMPLATES_DIR = RESOURCE_DIR / "templates"
UPLOAD_DIR = STATIC_DIR / "uploads"
SPRITES_DIR = STATIC_DIR / "sprites"
CARDS_DIR = BASE_DIR / "cards"
RESOURCE_CARDS_DIR = RESOURCE_DIR / "cards"
ROLE_CARD_EXTENSIONS = {".json", ".txt"}
SLOT_META_PATH = DATA_DIR / "save_slots.json"
EXPORT_DIR = BASE_DIR / "exports"
LEGACY_PERSONA_PATH = DATA_DIR / "persona.json"
LEGACY_CONVERSATION_PATH = DATA_DIR / "conversations.json"
LEGACY_SETTINGS_PATH = DATA_DIR / "settings.json"
LEGACY_MEMORIES_PATH = DATA_DIR / "memories.json"
LEGACY_WORLDBOOK_PATH = DATA_DIR / "worldbook.json"
LEGACY_CURRENT_CARD_PATH = DATA_DIR / "current_role_card.json"
GLOBAL_PRESET_PATH = DATA_DIR / "preset.json"
GLOBAL_WORKSHOP_STATE_PATH = DATA_DIR / "creative_workshop_state.json"
GLOBAL_USER_PROFILE_PATH = DATA_DIR / "user_profile.json"
SLOT_MIGRATION_MARKER_PATH = DATA_DIR / ".slot_migration_done"
GLOBAL_RUNTIME_MIGRATION_MARKER_PATH = DATA_DIR / ".global_runtime_migration_done"
PRESET_FILENAME = "preset.json"

ALLOWED_EMBEDDING_FIELDS = ("title", "content", "tags", "notes")
ALLOWED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
ALLOWED_AUDIO_SUFFIXES = {".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac", ".webm"}
ALLOWED_BACKGROUND_SCHEMES = {"http", "https"}
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024
MAX_BACKGROUND_UPLOAD_SIZE_BYTES = 30 * 1024 * 1024
MAX_WORKSHOP_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024
REQUEST_RETRY_ATTEMPTS = 5
REQUEST_RETRY_BASE_DELAY_SECONDS = 1.0
DEFAULT_SPRITE_BASE_PATH = "/static/sprites"
GLOBAL_RUNTIME_ID = "global_workspace"
GLOBAL_RUNTIME_NAME = "当前记忆"
LEGACY_SLOT_IDS = ("slot_1", "slot_2", "slot_3")
DEFAULT_SLOT_IDS = (GLOBAL_RUNTIME_ID,)
WORKSHOP_STAGE_LIMITS = {"aMax": 2, "bMax": 5}

logger = logging.getLogger("xuqi_llm_chat")
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO)


def bootstrap_runtime_layout() -> None:
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    if RESOURCE_STATIC_DIR.exists() and not (STATIC_DIR / "styles.css").exists():
        shutil.copytree(RESOURCE_STATIC_DIR, STATIC_DIR, dirs_exist_ok=True)

    if RESOURCE_CARDS_DIR.exists() and not CARDS_DIR.exists():
        shutil.copytree(RESOURCE_CARDS_DIR, CARDS_DIR, dirs_exist_ok=True)

    if (RESOURCE_DIR / "data").exists() and not DATA_DIR.exists():
        shutil.copytree(RESOURCE_DIR / "data", DATA_DIR, dirs_exist_ok=True)

DEFAULT_PERSONA = {
    "name": "Xuxu",
    "system_prompt": (
        "You are a gentle, patient, and attentive AI companion. "
        "Respond naturally, show care, and avoid overly templated phrasing."
    ),
    "greeting": "What would you like to talk about today? I am here with you.",
}

DEFAULT_SETTINGS = {
    "llm_base_url": "",
    "llm_api_key": "",
    "llm_model": "",
    "theme": "light",
    "temperature": 0.85,
    "history_limit": 20,
    "request_timeout": 120,
    "demo_mode": False,
    "ui_opacity": 0.84,
    "background_image_url": "",
    "background_overlay": 0.42,
    "embedding_base_url": "",
    "embedding_api_key": "",
    "embedding_model": "",
    "embedding_fields": ["title", "content", "tags"],
    "retrieval_top_k": 4,
    "rerank_enabled": False,
    "rerank_base_url": "",
    "rerank_api_key": "",
    "rerank_model": "",
    "rerank_top_n": 3,
    "sprite_enabled": True,
    "sprite_base_path": DEFAULT_SPRITE_BASE_PATH,
}


def default_slot_registry() -> dict[str, Any]:
    return {
        "active_slot": GLOBAL_RUNTIME_ID,
        "slots": [{"id": GLOBAL_RUNTIME_ID, "name": GLOBAL_RUNTIME_NAME}],
    }


def default_sprite_base_path_for_slot(slot_id: str | None = None) -> str:
    return DEFAULT_SPRITE_BASE_PATH


def sprite_dir_path(slot_id: str | None = None) -> Path:
    return SPRITES_DIR


def sanitize_sprite_filename_tag(value: str) -> str:
    text = str(value or "").strip()
    text = re.sub(r'[\\/:*?"<>|]+', "_", text)
    return text[:64].strip(" ._")


def list_sprite_assets(slot_id: str | None = None) -> list[dict[str, Any]]:
    directory = sprite_dir_path(slot_id)
    if not directory.exists():
        return []

    items: list[dict[str, Any]] = []
    for path in sorted(directory.iterdir(), key=lambda item: item.name.lower()):
        if not path.is_file() or path.suffix.lower() not in ALLOWED_IMAGE_SUFFIXES:
            continue
        items.append(
            {
                "filename": path.name,
                "tag": path.stem,
                "url": f"{default_sprite_base_path_for_slot(slot_id)}/{path.name}",
                "size": path.stat().st_size,
                "updated_at": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
    return items


def default_role_card() -> dict[str, Any]:
    return {
        "name": "",
        "description": "",
        "personality": "",
        "first_mes": "",
        "mes_example": "",
        "scenario": "",
        "creator_notes": "",
        "tags": [],
        "creativeWorkshop": {
            "enabled": True,
            "items": [
                {
                    "id": "workshop_stage_a",
                    "name": "A阶段规则",
                    "enabled": True,
                    "triggerMode": "stage",
                    "triggerStage": "A",
                    "triggerTempMin": 0,
                    "triggerTempMax": 0,
                    "actionType": "music",
                    "popupTitle": "",
                    "musicPreset": "off",
                    "musicUrl": "",
                    "autoplay": True,
                    "loop": True,
                    "volume": 0.85,
                    "imageUrl": "",
                    "imageAlt": "",
                    "note": "",
                }
            ],
        },
        "plotStages": {
            "A": {"description": "", "rules": ""},
            "B": {"description": "", "rules": ""},
            "C": {"description": "", "rules": ""},
        },
        "personas": {
            "1": {
                "name": "",
                "description": "",
                "personality": "",
                "scenario": "",
                "creator_notes": "",
            },
            "2": {
                "name": "",
                "description": "",
                "personality": "",
                "scenario": "",
                "creator_notes": "",
            },
            "3": {
                "name": "",
                "description": "",
                "personality": "",
                "scenario": "",
                "creator_notes": "",
            },
        },
    }



def default_user_profile() -> dict[str, Any]:
    return {
        "display_name": "",
        "nickname": "",
        "profile_text": "",
        "notes": "",
        "avatar_url": "",
    }


def default_creative_workshop() -> dict[str, Any]:
    return json.loads(json.dumps(default_role_card()["creativeWorkshop"], ensure_ascii=False))


def get_workshop_state(slot_id: str | None = None) -> dict[str, Any]:
    return sanitize_workshop_state(read_json(workshop_state_path(slot_id), default_workshop_state()))


def save_workshop_state(payload: dict[str, Any], slot_id: str | None = None) -> dict[str, Any]:
    sanitized = sanitize_workshop_state(payload)
    persist_json(
        workshop_state_path(slot_id),
        sanitized,
        detail="Creative workshop state save failed. Please check disk space or file permissions.",
    )
    return sanitized


def reset_workshop_state(slot_id: str | None = None) -> dict[str, Any]:
    return save_workshop_state(default_workshop_state(), slot_id)


def workshop_signature(slot: dict[str, Any] | None, workshop: dict[str, Any], stage: str) -> str:
    payload = {
        "slot": str((slot or {}).get("source_name", "")),
        "enabled": bool(workshop.get("enabled", False)),
        "stage": stage,
        "items": [
            {
                **workshop_effective_fields(item),
            }
            for item in workshop.get("items", [])
            if isinstance(item, dict)
        ],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def resolve_workshop_music_url(item: dict[str, Any]) -> str:
    return str(item.get("musicUrl", "")).strip()


def resolve_workshop_image_url(item: dict[str, Any]) -> str:
    return str(item.get("imageUrl", "")).strip()


def evaluate_creative_workshop(*, slot_id: str | None = None, reason: str = "sync") -> dict[str, Any]:
    target_slot = sanitize_slot_id(slot_id, get_active_slot_id())
    current_card = get_current_card(target_slot)
    workshop = sanitize_creative_workshop(current_card.get("raw", {}).get("creativeWorkshop", {}))
    state = get_workshop_state(target_slot)
    current_temp = int(state.get("temp", 0) or 0)
    stage = get_workshop_stage(current_temp)

    result: dict[str, Any] = {
        "stage": stage,
        "stage_label": get_workshop_stage_label(stage),
        "temp": current_temp,
        "reason": reason,
        "triggered": False,
        "action": None,
        "workshop": workshop,
        "current_card_name": str(current_card.get("source_name", "")).strip(),
    }

    if reason != "chat_round_start":
        return result

    pending_temp = clamp_int(state.get("pending_temp"), -1, 9999, -1)
    if pending_temp != current_temp:
        return result

    match = select_workshop_match(workshop, temp=current_temp, stage=stage)
    signature = build_workshop_trigger_token(match, temp=current_temp, stage=stage) if match else ""
    previous = str(state.get("last_signature", "")).strip()
    state["pending_temp"] = -1
    state["last_signature"] = signature
    save_workshop_state(state, target_slot)

    if not workshop.get("enabled", False) or not match:
        return result

    trigger_history = state.get("trigger_history", []) if isinstance(state.get("trigger_history"), list) else []
    if signature and (signature == previous or signature in trigger_history):
        return result

    if signature:
        updated_state = get_workshop_state(target_slot)
        updated_history = updated_state.get("trigger_history", []) if isinstance(updated_state.get("trigger_history"), list) else []
        updated_history = [token for token in updated_history if token != signature]
        updated_state["trigger_history"] = (updated_history + [signature])[-128:]
        updated_state["last_signature"] = signature
        save_workshop_state(updated_state, target_slot)

    action_type = normalize_workshop_action_type(match.get("actionType"))
    action = {
        "id": match.get("id", ""),
        "name": match.get("name", ""),
        "stage": stage,
        "stage_label": result["stage_label"],
        "trigger_mode": normalize_workshop_trigger_mode(match.get("triggerMode")),
        "trigger_label": get_workshop_trigger_label(match, temp=current_temp, stage=stage),
        "reason": reason,
        "action_type": action_type,
        "note": str(match.get("note", "")).strip(),
    }

    if action_type == "image":
        action.update(
            {
                "popup_title": str(match.get("popupTitle", "")).strip() or str(match.get("name", "")).strip() or "鍒涙剰宸ュ潑寮圭獥",
                "image_url": resolve_workshop_image_url(match),
                "image_alt": str(match.get("imageAlt", "")).strip() or str(match.get("name", "")).strip() or "鍒涙剰宸ュ潑鍥剧墖",
            }
        )
    else:
        action.update(
            {
                "music_preset": str(match.get("musicPreset", "off")).strip() or "off",
                "music_url": resolve_workshop_music_url(match),
                "autoplay": bool(match.get("autoplay", True)),
                "loop": bool(match.get("loop", True)),
                "volume": clamp_float(match.get("volume"), 0.0, 1.0, 0.85),
            }
        )

    if action_type == "image" and not action["image_url"]:
        return result
    if action_type == "music" and not action["music_url"] and action["music_preset"] == "off":
        return result

    result["triggered"] = True
    result["action"] = action
    return result


def default_preset_store() -> dict[str, Any]:
    return default_preset_store_data()


def sanitize_preset_store(raw: Any) -> dict[str, Any]:
    return sanitize_preset_store_data(raw)


def preset_path(slot_id: str | None = None) -> Path:
    return GLOBAL_PRESET_PATH


def get_preset_store(slot_id: str | None = None) -> dict[str, Any]:
    return sanitize_preset_store(read_json(preset_path(slot_id), default_preset_store()))


def save_preset_store(payload: dict[str, Any], slot_id: str | None = None) -> dict[str, Any]:
    sanitized = sanitize_preset_store(payload)
    persist_json(
        preset_path(slot_id),
        sanitized,
        detail="Preset save failed. Please check disk space or file permissions.",
    )
    return sanitized


def get_active_preset(slot_id: str | None = None) -> dict[str, Any]:
    return get_active_preset_from_store(get_preset_store(slot_id))


def build_preset_prompt(slot_id: str | None = None) -> str:
    return build_preset_prompt_from_preset(get_active_preset(slot_id))


def get_active_preset_module_labels(slot_id: str | None = None) -> list[str]:
    preset = get_active_preset(slot_id)
    modules = preset.get("modules", {}) if isinstance(preset, dict) else {}
    labels: list[str] = []
    for key, meta in PRESET_MODULE_RULES.items():
        if modules.get(key):
            labels.append(str(meta.get("label", key)))
    return labels


def build_preset_debug_payload(slot_id: str | None = None) -> dict[str, Any]:
    store = get_preset_store(slot_id)
    preset = get_active_preset_from_store(store)
    prompt = build_preset_prompt_from_preset(preset)
    return {
        "active_preset_id": str(store.get("active_preset_id", "")).strip(),
        "active_preset_name": str(preset.get("name", "Unnamed preset")).strip() or "Unnamed preset",
        "enabled": bool(preset.get("enabled", True)),
        "active_modules": get_active_preset_module_labels(slot_id),
        "prompt": prompt,
    }

def load_env_file() -> None:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.warning("璇诲彇 JSON 澶辫触锛屼娇鐢ㄩ粯璁ゅ€? %s (%s)", path, exc)
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def persist_json(path: Path, payload: Any, *, detail: str, status_code: int = 500) -> None:
    try:
        write_json(path, payload)
    except OSError as exc:
        logger.exception("鍐欏叆 JSON 澶辫触: %s", path)
        raise HTTPException(status_code=status_code, detail=detail) from exc


def parse_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if value is None:
        return default
    return bool(value)


def clamp_int(value: Any, minimum: int, maximum: int, default: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return min(max(number, minimum), maximum)


def clamp_float(value: Any, minimum: float, maximum: float, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return min(max(number, minimum), maximum)


def sanitize_background_image_url(value: Any, *, strict: bool = False) -> str:
    text = str(value or "").strip()
    if not text:
        return ""

    if text.startswith("/static/uploads/"):
        return text

    parsed = urlparse(text)
    if parsed.scheme in ALLOWED_BACKGROUND_SCHEMES and parsed.netloc:
        return text

    if strict:
        raise HTTPException(
            status_code=400,
            detail="Background image URLs must be http/https or a /static/uploads/ local path.",
        )
    return ""


def sanitize_embedding_fields(value: Any) -> list[str]:
    raw_fields = value if isinstance(value, list) else DEFAULT_SETTINGS["embedding_fields"]
    normalized_fields: list[str] = []
    for field_name in raw_fields:
        field_value = str(field_name).strip()
        if field_value in ALLOWED_EMBEDDING_FIELDS and field_value not in normalized_fields:
            normalized_fields.append(field_value)
    return normalized_fields or list(DEFAULT_SETTINGS["embedding_fields"])


def sanitize_settings(raw: dict[str, Any] | None, *, strict: bool = False, slot_id: str | None = None) -> dict[str, Any]:
    settings = DEFAULT_SETTINGS.copy()
    if raw:
        settings.update(raw)

    default_sprite_path = default_sprite_base_path_for_slot(slot_id)
    sprite_base_path = str(settings.get("sprite_base_path", default_sprite_path)).strip() or default_sprite_path
    if sprite_base_path == DEFAULT_SPRITE_BASE_PATH or sprite_base_path.startswith(f"{DEFAULT_SPRITE_BASE_PATH}/"):
        sprite_base_path = default_sprite_path

    return {
        "llm_base_url": str(settings.get("llm_base_url", "")).strip(),
        "llm_api_key": str(settings.get("llm_api_key", "")).strip(),
        "llm_model": str(settings.get("llm_model", "")).strip(),
        "theme": "dark" if str(settings.get("theme", "light")).strip() == "dark" else "light",
        "temperature": clamp_float(settings.get("temperature"), 0.0, 2.0, 0.85),
        "history_limit": clamp_int(settings.get("history_limit"), 1, 100, 20),
        "request_timeout": clamp_int(settings.get("request_timeout"), 10, 600, 120),
        "demo_mode": parse_bool(settings.get("demo_mode"), False),
        "ui_opacity": clamp_float(settings.get("ui_opacity"), 0.2, 1.0, 0.84),
        "background_image_url": sanitize_background_image_url(
            settings.get("background_image_url", ""),
            strict=strict,
        ),
        "background_overlay": clamp_float(settings.get("background_overlay"), 0.0, 0.85, 0.42),
        "sprite_enabled": parse_bool(settings.get("sprite_enabled"), True),
        "sprite_base_path": sprite_base_path,
        "embedding_base_url": str(settings.get("embedding_base_url", "")).strip(),
        "embedding_api_key": str(settings.get("embedding_api_key", "")).strip(),
        "embedding_model": str(settings.get("embedding_model", "")).strip(),
        "embedding_fields": sanitize_embedding_fields(settings.get("embedding_fields")),
        "retrieval_top_k": clamp_int(settings.get("retrieval_top_k"), 1, 12, 4),
        "rerank_enabled": parse_bool(settings.get("rerank_enabled"), False),
        "rerank_base_url": str(settings.get("rerank_base_url", "")).strip(),
        "rerank_api_key": str(settings.get("rerank_api_key", "")).strip(),
        "rerank_model": str(settings.get("rerank_model", "")).strip(),
        "rerank_top_n": clamp_int(settings.get("rerank_top_n"), 1, 12, 3),
    }


def sanitize_tags(value: Any) -> list[str]:
    if isinstance(value, str):
        raw_tags = value.replace("?", ",").split(",")
    elif isinstance(value, list):
        raw_tags = value
    else:
        raw_tags = []

    tags: list[str] = []
    for item in raw_tags:
        text = str(item).strip()
        if text and text not in tags:
            tags.append(text)
    return tags


def sanitize_memories(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []

    items: list[dict[str, Any]] = []
    for index, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            continue
        memory_id = str(item.get("id", "")).strip() or f"memory-{index}"
        items.append(
            {
                "id": memory_id,
                "title": str(item.get("title", "")).strip(),
                "content": str(item.get("content", "")).strip(),
                "tags": sanitize_tags(item.get("tags", [])),
                "notes": str(item.get("notes", "")).strip(),
            }
        )
    return items


def sanitize_slot_id(value: Any, default: str | None = None) -> str:
    return GLOBAL_RUNTIME_ID


def sanitize_legacy_slot_id(value: Any, default: str | None = None) -> str:
    slot_id = str(value or "").strip()
    if slot_id in LEGACY_SLOT_IDS:
        return slot_id
    return default or LEGACY_SLOT_IDS[0]


def sanitize_slot_registry(raw: Any) -> dict[str, Any]:
    return default_slot_registry()
    default = default_slot_registry()
    if not isinstance(raw, dict):
        return default

    raw_slots = raw.get("slots", [])
    seen: set[str] = set()
    slots: list[dict[str, str]] = []
    if isinstance(raw_slots, list):
        for index, item in enumerate(raw_slots, start=1):
            if not isinstance(item, dict):
                continue
            slot_id = sanitize_slot_id(item.get("id"), "")
            if not slot_id or slot_id in seen:
                continue
            seen.add(slot_id)
            name = str(item.get("name", "")).strip() or f"瀛樻。 {index}"
            slots.append({"id": slot_id, "name": name[:32]})

    for index, slot_id in enumerate(DEFAULT_SLOT_IDS, start=1):
        if slot_id not in seen:
            slots.append({"id": slot_id, "name": f"瀛樻。 {index}"})

    active_slot = sanitize_slot_id(raw.get("active_slot"), DEFAULT_SLOT_IDS[0])
    return {"active_slot": active_slot, "slots": slots}


def get_slot_registry() -> dict[str, Any]:
    return sanitize_slot_registry(read_json(SLOT_META_PATH, default_slot_registry()))


def save_slot_registry(registry: dict[str, Any]) -> dict[str, Any]:
    return sanitize_slot_registry(registry)
    sanitized = sanitize_slot_registry(registry)
    persist_json(
        SLOT_META_PATH,
        sanitized,
        detail="Slot registry save failed. Please check disk space or file permissions.",
    )
    return sanitized


def get_active_slot_id() -> str:
    return GLOBAL_RUNTIME_ID
    return get_slot_registry()["active_slot"]


def get_slot_name(slot_id: str | None = None) -> str:
    return GLOBAL_RUNTIME_NAME
    target = sanitize_slot_id(slot_id, get_active_slot_id())
    for item in get_slot_registry()["slots"]:
        if item["id"] == target:
            return item["name"]
    return target


def slot_summary(slot_id: str | None = None) -> dict[str, Any]:
    current_card = get_current_card()
    workshop_state = get_workshop_state()
    return {
        "id": GLOBAL_RUNTIME_ID,
        "name": GLOBAL_RUNTIME_NAME,
        "persona_name": get_persona().get("name", ""),
        "memory_count": len(get_memories()),
        "worldbook_count": len(get_worldbook()),
        "conversation_count": len(get_conversation()),
        "current_card_name": current_card.get("source_name", ""),
        "workshop_temp": workshop_state.get("temp", 0),
        "workshop_stage": get_workshop_stage(workshop_state.get("temp", 0)),
    }
    target = sanitize_slot_id(slot_id, get_active_slot_id())
    current_card = get_current_card(target)
    workshop_state = get_workshop_state(target)
    return {
        "id": target,
        "name": get_slot_name(target),
        "persona_name": get_persona(target).get("name", ""),
        "memory_count": len(get_memories(target)),
        "worldbook_count": len(get_worldbook(target)),
        "conversation_count": len(get_conversation(target)),
        "current_card_name": current_card.get("source_name", ""),
        "workshop_temp": workshop_state.get("temp", 0),
        "workshop_stage": get_workshop_stage(workshop_state.get("temp", 0)),
    }


def get_slot_dir(slot_id: str | None = None) -> Path:
    return DATA_DIR
    return SLOTS_DIR / sanitize_slot_id(slot_id, get_active_slot_id())


def persona_path(slot_id: str | None = None) -> Path:
    return global_persona_path()
    return get_slot_dir(slot_id) / "persona.json"


def legacy_slot_dir(slot_id: str | None = None) -> Path:
    return SLOTS_DIR / sanitize_legacy_slot_id(slot_id, LEGACY_SLOT_IDS[0])


def legacy_persona_path(slot_id: str | None = None) -> Path:
    return legacy_slot_dir(slot_id) / "persona.json"


def global_persona_path() -> Path:
    return LEGACY_PERSONA_PATH


def conversation_path(slot_id: str | None = None) -> Path:
    return LEGACY_CONVERSATION_PATH
    return get_slot_dir(slot_id) / "conversations.json"


def settings_path(slot_id: str | None = None) -> Path:
    return LEGACY_SETTINGS_PATH
    return get_slot_dir(slot_id) / "settings.json"


def memories_path(slot_id: str | None = None) -> Path:
    return LEGACY_MEMORIES_PATH
    return get_slot_dir(slot_id) / "memories.json"


def worldbook_path(slot_id: str | None = None) -> Path:
    return LEGACY_WORLDBOOK_PATH
    return get_slot_dir(slot_id) / "worldbook.json"


def current_card_path(slot_id: str | None = None) -> Path:
    return global_current_card_path()
    return get_slot_dir(slot_id) / "current_role_card.json"


def legacy_current_card_path(slot_id: str | None = None) -> Path:
    return legacy_slot_dir(slot_id) / "current_role_card.json"


def global_current_card_path() -> Path:
    return LEGACY_CURRENT_CARD_PATH


def workshop_state_path(slot_id: str | None = None) -> Path:
    return GLOBAL_WORKSHOP_STATE_PATH
    return get_slot_dir(slot_id) / "creative_workshop_state.json"


def user_profile_path(slot_id: str | None = None) -> Path:
    return GLOBAL_USER_PROFILE_PATH
    return get_slot_dir(slot_id) / "user_profile.json"


def avatar_upload_url(filename: str) -> str:
    safe_name = Path(str(filename or "")).name
    return f"/static/uploads/{safe_name}" if safe_name else ""


def remove_upload_variants(prefix: str) -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    for path in UPLOAD_DIR.glob(f"{prefix}.*"):
        if path.is_file():
            path.unlink(missing_ok=True)


def save_image_upload_for_slot(
    *,
    file: UploadFile,
    prefix: str,
    empty_detail: str,
    too_large_detail: str,
    invalid_type_detail: str,
    save_failed_detail: str,
) -> str:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_IMAGE_SUFFIXES:
        raise HTTPException(status_code=400, detail=invalid_type_detail)
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail=invalid_type_detail)
    content = file.file.read(MAX_UPLOAD_SIZE_BYTES + 1)
    if not content:
        raise HTTPException(status_code=400, detail=empty_detail)
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=413, detail=too_large_detail)

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    remove_upload_variants(prefix)
    target = UPLOAD_DIR / f"{prefix}{suffix}"
    try:
        target.write_bytes(content)
    except OSError as exc:
        logger.exception("Avatar write failed: %s", target)
        raise HTTPException(status_code=500, detail=save_failed_detail) from exc
    return avatar_upload_url(target.name)


def workshop_asset_dir(kind: str) -> Path:
    normalized = "image" if str(kind or "").strip().lower() == "image" else "music"
    return UPLOAD_DIR / "workshop" / normalized


def workshop_asset_url(kind: str, filename: str) -> str:
    normalized = "image" if str(kind or "").strip().lower() == "image" else "music"
    safe_name = Path(str(filename or "")).name
    return f"/static/uploads/workshop/{normalized}/{safe_name}" if safe_name else ""


async def save_workshop_asset_upload(*, kind: str, file: UploadFile) -> dict[str, Any]:
    normalized_kind = "image" if str(kind or "").strip().lower() == "image" else "music"
    suffix = Path(file.filename or "").suffix.lower()
    allowed_suffixes = ALLOWED_IMAGE_SUFFIXES if normalized_kind == "image" else ALLOWED_AUDIO_SUFFIXES
    if suffix not in allowed_suffixes:
        if normalized_kind == "image":
            raise HTTPException(status_code=400, detail="Creative workshop images only support png / jpg / jpeg / webp / gif.")
        raise HTTPException(status_code=400, detail="Creative workshop audio only supports mp3 / wav / ogg / m4a / aac / flac / webm.")

    content_type = str(file.content_type or "").strip().lower()
    if normalized_kind == "image":
        if content_type and content_type != "application/octet-stream" and not content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="The selected file is not an image.")
    else:
        if content_type and content_type != "application/octet-stream" and not (
            content_type.startswith("audio/") or content_type.startswith("video/")
        ):
            raise HTTPException(status_code=400, detail="The selected file is not audio.")

    content = await file.read(MAX_WORKSHOP_UPLOAD_SIZE_BYTES + 1)
    if not content:
        raise HTTPException(status_code=400, detail="Upload file cannot be empty.")
    if len(content) > MAX_WORKSHOP_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Workshop assets cannot be larger than 25 MB.")

    normalized_stem = sanitize_sprite_filename_tag(Path(file.filename or "").stem) or f"workshop_{normalized_kind}"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    directory = workshop_asset_dir(normalized_kind)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{timestamp}_{normalized_stem}{suffix}"
    try:
        target.write_bytes(content)
    except OSError as exc:
        logger.exception("Workshop asset write failed: %s", target)
        raise HTTPException(status_code=500, detail="Workshop asset save failed. Please check disk space or file permissions.") from exc

    return {
        "ok": True,
        "kind": normalized_kind,
        "filename": target.name,
        "url": workshop_asset_url(normalized_kind, target.name),
    }


def reset_slot_data(slot_id: str) -> dict[str, Any]:
    persist_json(conversation_path(), [], detail="Workspace reset failed: could not clear chat history.")
    persist_json(settings_path(), sanitize_settings(DEFAULT_SETTINGS), detail="Workspace reset failed: could not reset settings.")
    persist_json(memories_path(), [], detail="Workspace reset failed: could not clear memories.")
    persist_json(worldbook_path(), {}, detail="Workspace reset failed: could not clear worldbook.")
    reset_workshop_state()
    persist_json(user_profile_path(), default_user_profile(), detail="Workspace reset failed: could not reset user profile.")
    persist_json(preset_path(), default_preset_store(), detail="Workspace reset failed: could not reset presets.")
    remove_upload_variants("user_avatar")
    remove_upload_variants("role_avatar")
    return slot_summary()


def normalize_role_card(raw: Any) -> dict[str, Any]:
    card = default_role_card()
    if not isinstance(raw, dict):
        return card

    for key in [
        "name",
        "description",
        "personality",
        "first_mes",
        "mes_example",
        "scenario",
        "creator_notes",
    ]:
        card[key] = str(raw.get(key, "")).strip()

    card["tags"] = sanitize_tags(raw.get("tags", []))

    card["creativeWorkshop"] = sanitize_creative_workshop(raw.get("creativeWorkshop", {}))

    plot_stages = raw.get("plotStages", {})
    if isinstance(plot_stages, dict):
        for key in card["plotStages"]:
            value = plot_stages.get(key, {})
            if isinstance(value, dict):
                card["plotStages"][key]["description"] = str(value.get("description", "")).strip()
                card["plotStages"][key]["rules"] = str(value.get("rules", "")).strip()

    personas = raw.get("personas", {})
    if isinstance(personas, dict):
        persona_items: list[tuple[str, Any]]
        if any(str(key) in card["personas"] for key in personas):
            persona_items = [(key, personas.get(key, {})) for key in card["personas"]]
        else:
            persona_items = list(personas.items())[: len(card["personas"])]

        for slot, item in zip(card["personas"], persona_items):
            source_key, value = item
            if isinstance(value, dict):
                source_name = str(source_key).strip()
                raw_name = str(value.get("name", "")).strip()
                display_name = raw_name or source_name
                if not display_name or re.fullmatch(r"[A-Z]", display_name):
                    extracted_name = extract_persona_name_from_fields(
                        str(value.get("description", "")).strip(),
                        str(value.get("scenario", "")).strip(),
                        str(value.get("personality", "")).strip(),
                    )
                    if extracted_name:
                        display_name = extracted_name
                    elif source_name and source_name not in {"1", "2", "3"}:
                        display_name = source_name
                card["personas"][slot]["name"] = display_name
                card["personas"][slot]["description"] = str(value.get("description", "")).strip()
                card["personas"][slot]["personality"] = str(value.get("personality", "")).strip()
                card["personas"][slot]["scenario"] = str(value.get("scenario", "")).strip()
                card["personas"][slot]["creator_notes"] = str(value.get("creator_notes", "")).strip()

    return card


def extract_persona_name_from_fields(*texts: str) -> str:
    patterns = [
        r"姓名[:：]\s*([^\n,，。；;]{1,16})",
        r"名为([^\n,，。；;]{1,16})",
        r"^([^\n,，。；;]{1,16})[:：]",
        r"^([^\n,，。；;]{1,16})[：:]",
    ]
    for text in texts:
        content = str(text or "").strip()
        if not content:
            continue
        for pattern in patterns:
            match = re.search(pattern, content, re.MULTILINE)
            if match:
                return match.group(1).strip()
    return ""

def is_legacy_demo_reply(content: str) -> bool:
    text = str(content or "").strip()
    if not text:
        return False

    markers = [
        "收到啦：",
        "我现在处于本地演示模式",
        "Config 椤甸潰濉啓鑱婂ぉ妯″瀷",
        "请先去配置页面",
        "本地演示模式",
        "Config 页面",
    ]
    return any(marker in text for marker in markers)


def is_garbled_placeholder_message(content: str) -> bool:
    text = str(content or "").strip()
    if len(text) < 3:
        return False
    return set(text) <= {"?"}


def normalize_legacy_message_content(role: str, content: str) -> str:
    text = str(content or "")
    if role != "assistant":
        return text

    stripped = text.lstrip()
    if stripped.startswith("??????"):
        remainder = stripped.lstrip("?").lstrip(":").lstrip()
        return f"Error: {remainder}" if remainder else "Error."
    return text


def sanitize_conversation(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []

    cleaned: list[dict[str, Any]] = []
    changed = False

    for item in raw:
        if not isinstance(item, dict):
            changed = True
            continue

        role = str(item.get("role", "")).strip()
        content = normalize_legacy_message_content(role, str(item.get("content", "")))
        created_at = str(item.get("created_at", "")).strip()

        if role not in {"user", "assistant", "system"}:
            changed = True
            continue

        if role == "assistant" and is_legacy_demo_reply(content):
            changed = True
            continue

        cleaned.append(
            {
                "role": role,
                "content": content,
                "created_at": created_at,
            }
        )

    if changed:
        logger.info("Detected legacy demo messages and filtered them from chat history.")
    return cleaned


def legacy_active_slot_id() -> str:
    raw = read_json(SLOT_META_PATH, {})
    if isinstance(raw, dict):
        slot_id = str(raw.get("active_slot", "")).strip()
        if slot_id in LEGACY_SLOT_IDS:
            return slot_id
    return ""


def legacy_slot_last_updated(slot_id: str) -> float:
    source_dir = legacy_slot_dir(slot_id)
    timestamps: list[float] = []
    for path in source_dir.glob("*.json"):
        try:
            timestamps.append(path.stat().st_mtime)
        except OSError:
            continue
    return max(timestamps) if timestamps else 0.0


def legacy_slot_seed_order() -> list[str]:
    preferred = legacy_active_slot_id()
    ordered = ([preferred] if preferred else []) + sorted(LEGACY_SLOT_IDS, key=legacy_slot_last_updated, reverse=True)
    seen: set[str] = set()
    result: list[str] = []
    for slot_id in ordered:
        target = sanitize_legacy_slot_id(slot_id, LEGACY_SLOT_IDS[0])
        if target in seen:
            continue
        seen.add(target)
        result.append(target)
    return result


def legacy_slot_has_runtime_data(slot_id: str) -> bool:
    target = sanitize_legacy_slot_id(slot_id, LEGACY_SLOT_IDS[0])
    slot_dir = legacy_slot_dir(target)
    if not slot_dir.exists():
        return False

    conversation_file = slot_dir / "conversations.json"
    settings_file = slot_dir / "settings.json"
    memories_file = slot_dir / "memories.json"
    worldbook_file = slot_dir / "worldbook.json"
    workshop_file = slot_dir / "creative_workshop_state.json"
    user_profile_file = slot_dir / "user_profile.json"
    preset_file = slot_dir / PRESET_FILENAME

    return any(
        (
            sanitize_conversation(read_json(conversation_file, [])),
            sanitize_settings(read_json(settings_file, {}), slot_id=GLOBAL_RUNTIME_ID) != sanitize_settings(DEFAULT_SETTINGS),
            sanitize_memories(read_json(memories_file, [])),
            sanitize_worldbook_store(read_json(worldbook_file, {}))["entries"],
            sanitize_workshop_state(read_json(workshop_file, default_workshop_state())) != default_workshop_state(),
            sanitize_user_profile(read_json(user_profile_file, {})) != default_user_profile(),
            sanitize_preset_store(read_json(preset_file, {})) != default_preset_store(),
        )
    )


def migrate_legacy_avatar_upload(prefix: str, legacy_slot_id: str) -> None:
    existing = [
        path
        for path in UPLOAD_DIR.glob(f"{prefix}.*")
        if path.is_file() and path.suffix.lower() in ALLOWED_IMAGE_SUFFIXES
    ]
    if existing:
        return
    for path in sorted(UPLOAD_DIR.glob(f"{prefix}_{legacy_slot_id}.*")):
        if not path.is_file() or path.suffix.lower() not in ALLOWED_IMAGE_SUFFIXES:
            continue
        shutil.copy2(path, UPLOAD_DIR / f"{prefix}{path.suffix.lower()}")
        return


def migrate_legacy_sprite_assets(legacy_slot_id: str) -> None:
    existing = [
        path
        for path in SPRITES_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in ALLOWED_IMAGE_SUFFIXES
    ] if SPRITES_DIR.exists() else []
    if existing:
        return

    source_dir = SPRITES_DIR / legacy_slot_id
    if not source_dir.exists():
        return

    for path in source_dir.iterdir():
        if not path.is_file() or path.suffix.lower() not in ALLOWED_IMAGE_SUFFIXES:
            continue
        shutil.copy2(path, SPRITES_DIR / path.name)


def migrate_slot_runtime_to_global_files() -> None:
    if GLOBAL_RUNTIME_MIGRATION_MARKER_PATH.exists():
        return

    source_slot = next((slot_id for slot_id in legacy_slot_seed_order() if legacy_slot_has_runtime_data(slot_id)), "")
    if not source_slot:
        GLOBAL_RUNTIME_MIGRATION_MARKER_PATH.write_text("no-legacy-slot-data", encoding="utf-8")
        return

    source_dir = legacy_slot_dir(source_slot)
    persist_json(
        conversation_path(),
        sanitize_conversation(read_json(source_dir / "conversations.json", [])),
        detail="Workspace migration failed while importing chat history.",
    )
    persist_json(
        settings_path(),
        sanitize_settings(read_json(source_dir / "settings.json", {}), slot_id=GLOBAL_RUNTIME_ID),
        detail="Workspace migration failed while importing settings.",
    )
    persist_json(
        memories_path(),
        sanitize_memories(read_json(source_dir / "memories.json", [])),
        detail="Workspace migration failed while importing memories.",
    )
    persist_json(
        worldbook_path(),
        sanitize_worldbook_store(read_json(source_dir / "worldbook.json", {})),
        detail="Workspace migration failed while importing worldbook.",
    )
    persist_json(
        workshop_state_path(),
        sanitize_workshop_state(read_json(source_dir / "creative_workshop_state.json", default_workshop_state())),
        detail="Workspace migration failed while importing workshop state.",
    )
    persist_json(
        user_profile_path(),
        sanitize_user_profile(read_json(source_dir / "user_profile.json", {})),
        detail="Workspace migration failed while importing user profile.",
    )
    persist_json(
        preset_path(),
        sanitize_preset_store(read_json(source_dir / PRESET_FILENAME, {})),
        detail="Workspace migration failed while importing presets.",
    )
    migrate_legacy_avatar_upload("user_avatar", source_slot)
    migrate_legacy_avatar_upload("role_avatar", source_slot)
    migrate_legacy_sprite_assets(source_slot)
    GLOBAL_RUNTIME_MIGRATION_MARKER_PATH.write_text(source_slot, encoding="utf-8")
    logger.info("Migrated legacy slot runtime data from %s to the global workspace.", source_slot)


def slot_looks_uninitialized(slot_id: str) -> bool:
    return (
        get_conversation(slot_id) == []
        and get_settings(slot_id) == sanitize_settings(DEFAULT_SETTINGS, slot_id=slot_id)
        and get_memories(slot_id) == []
        and get_worldbook(slot_id) == {}
    )


def has_legacy_root_data() -> bool:
    return any(
        path.exists()
        for path in (
            LEGACY_CONVERSATION_PATH,
            LEGACY_SETTINGS_PATH,
            LEGACY_MEMORIES_PATH,
            LEGACY_WORLDBOOK_PATH,
        )
    )


def migrate_legacy_root_to_primary_slot() -> None:
    migrate_slot_runtime_to_global_files()
    return
    if SLOT_MIGRATION_MARKER_PATH.exists():
        return
    if not has_legacy_root_data():
        SLOT_MIGRATION_MARKER_PATH.write_text("no-legacy-data", encoding="utf-8")
        return
    if not slot_looks_uninitialized(DEFAULT_SLOT_IDS[0]):
        SLOT_MIGRATION_MARKER_PATH.write_text("slot-1-already-in-use", encoding="utf-8")
        return

    persist_json(
        conversation_path(DEFAULT_SLOT_IDS[0]),
        sanitize_conversation(read_json(LEGACY_CONVERSATION_PATH, [])),
        detail="Legacy conversation migration failed. Please check disk space or file permissions.",
    )
    persist_json(
        settings_path(DEFAULT_SLOT_IDS[0]),
        sanitize_settings(read_json(LEGACY_SETTINGS_PATH, {}), slot_id=DEFAULT_SLOT_IDS[0]),
        detail="Legacy settings migration failed. Please check disk space or file permissions.",
    )
    persist_json(
        memories_path(DEFAULT_SLOT_IDS[0]),
        sanitize_memories(read_json(LEGACY_MEMORIES_PATH, [])),
        detail="Legacy memories migration failed. Please check disk space or file permissions.",
    )
    persist_json(
        worldbook_path(DEFAULT_SLOT_IDS[0]),
        sanitize_worldbook(read_json(LEGACY_WORLDBOOK_PATH, {})),
        detail="Legacy worldbook migration failed. Please check disk space or file permissions.",
    )
    SLOT_MIGRATION_MARKER_PATH.write_text("migrated-slot-1", encoding="utf-8")
    logger.info("Migrated legacy data root contents to slot_1.")


def slot_role_state_seed_order() -> list[str]:
    return legacy_slot_seed_order()
    active_slot = get_active_slot_id()
    ordered = [active_slot, *DEFAULT_SLOT_IDS]
    seen: set[str] = set()
    result: list[str] = []
    for slot_id in ordered:
        target = sanitize_slot_id(slot_id, DEFAULT_SLOT_IDS[0])
        if target in seen:
            continue
        seen.add(target)
        result.append(target)
    return result


def seed_global_role_state() -> None:
    seeded_persona: dict[str, Any] | None = None
    for slot_id in slot_role_state_seed_order():
        raw_persona = read_json(legacy_persona_path(slot_id), {})
        if not isinstance(raw_persona, dict):
            continue
        candidate = {
            "name": str(raw_persona.get("name", "")).strip(),
            "system_prompt": str(raw_persona.get("system_prompt", "")).strip(),
            "greeting": str(raw_persona.get("greeting", "")).strip(),
        }
        if any(candidate.values()):
            seeded_persona = candidate
            break

    persona_target = global_persona_path()
    if not persona_target.exists():
        write_json(persona_target, seeded_persona or DEFAULT_PERSONA)
    else:
        normalized_persona = get_persona()
        if seeded_persona and normalized_persona == DEFAULT_PERSONA:
            write_json(persona_target, seeded_persona)
        elif normalized_persona != read_json(persona_target, {}):
            write_json(persona_target, normalized_persona)

    seeded_card: dict[str, Any] | None = None
    for slot_id in slot_role_state_seed_order():
        raw_card = read_json(legacy_current_card_path(slot_id), {})
        if not isinstance(raw_card, dict):
            continue
        source_name = str(raw_card.get("source_name", "")).strip()
        raw_payload = raw_card.get("raw", {})
        normalized_payload = normalize_role_card(raw_payload) if isinstance(raw_payload, dict) else default_role_card()
        if source_name or normalized_payload != default_role_card():
            seeded_card = {
                "source_name": source_name,
                "raw": normalized_payload,
            }
            break

    card_target = global_current_card_path()
    if not card_target.exists():
        write_json(card_target, seeded_card or {})
    else:
        normalized_card = get_current_card()
        is_blank_card = (
            not str(normalized_card.get("source_name", "")).strip()
            and normalize_role_card(normalized_card.get("raw", {})) == default_role_card()
        )
        if seeded_card and is_blank_card:
            write_json(card_target, seeded_card)
        elif normalized_card != read_json(card_target, {}):
            write_json(card_target, normalized_card)


def ensure_data_files() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SLOTS_DIR.mkdir(parents=True, exist_ok=True)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    SPRITES_DIR.mkdir(parents=True, exist_ok=True)
    CARDS_DIR.mkdir(parents=True, exist_ok=True)
    if not conversation_path().exists():
        write_json(conversation_path(), [])
    if not settings_path().exists():
        write_json(settings_path(), sanitize_settings(DEFAULT_SETTINGS))
    else:
        normalized_settings = sanitize_settings(read_json(settings_path(), {}))
        if normalized_settings != read_json(settings_path(), {}):
            write_json(settings_path(), normalized_settings)
    if not memories_path().exists():
        write_json(memories_path(), [])
    if not worldbook_path().exists():
        write_json(worldbook_path(), sanitize_worldbook_store({}))
    if not workshop_state_path().exists():
        write_json(workshop_state_path(), default_workshop_state())
    if not user_profile_path().exists():
        write_json(user_profile_path(), default_user_profile())
    if not preset_path().exists():
        write_json(preset_path(), default_preset_store())
    migrate_slot_runtime_to_global_files()
    seed_global_role_state()
    return
    if not SLOT_META_PATH.exists():
        write_json(SLOT_META_PATH, default_slot_registry())

    registry = get_slot_registry()
    if registry != read_json(SLOT_META_PATH, {}):
        write_json(SLOT_META_PATH, registry)

    for slot_id in DEFAULT_SLOT_IDS:
        slot_dir = get_slot_dir(slot_id)
        slot_dir.mkdir(parents=True, exist_ok=True)
        sprite_dir_path(slot_id).mkdir(parents=True, exist_ok=True)
        if not conversation_path(slot_id).exists():
            write_json(conversation_path(slot_id), [])
        if not settings_path(slot_id).exists():
            write_json(settings_path(slot_id), sanitize_settings(DEFAULT_SETTINGS, slot_id=slot_id))
        else:
            normalized_settings = sanitize_settings(read_json(settings_path(slot_id), {}), slot_id=slot_id)
            if normalized_settings != read_json(settings_path(slot_id), {}):
                write_json(settings_path(slot_id), normalized_settings)
        if not memories_path(slot_id).exists():
            write_json(memories_path(slot_id), [])
        if not worldbook_path(slot_id).exists():
            write_json(worldbook_path(slot_id), {})
        if not workshop_state_path(slot_id).exists():
            write_json(workshop_state_path(slot_id), default_workshop_state())
        if not user_profile_path(slot_id).exists():
            write_json(user_profile_path(slot_id), default_user_profile())
        if not preset_path(slot_id).exists():
            write_json(preset_path(slot_id), default_preset_store())
    migrate_legacy_root_to_primary_slot()
    seed_global_role_state()


def get_persona(slot_id: str | None = None) -> dict[str, Any]:
    persona = DEFAULT_PERSONA.copy()
    persona.update(read_json(global_persona_path(), {}))
    return persona


def get_conversation(slot_id: str | None = None) -> list[dict[str, Any]]:
    path = conversation_path(slot_id)
    history = sanitize_conversation(read_json(path, []))
    stored = read_json(path, [])
    if history != stored:
        persist_json(
            path,
            history,
            detail="Chat history cleanup failed. Please check disk space or file permissions.",
        )
    return history


def get_settings(slot_id: str | None = None) -> dict[str, Any]:
    target = sanitize_slot_id(slot_id, get_active_slot_id())
    return sanitize_settings(read_json(settings_path(target), {}), slot_id=target)


def sanitize_user_profile(payload: Any, *, slot_id: str | None = None) -> dict[str, Any]:
    base = default_user_profile()
    if isinstance(payload, dict):
        base["display_name"] = str(payload.get("display_name", base["display_name"])).strip()[:24] or "User"
        base["nickname"] = str(payload.get("nickname", "")).strip()[:40]
        base["profile_text"] = str(payload.get("profile_text", "")).strip()[:4000]
        base["notes"] = str(payload.get("notes", "")).strip()[:1000]
        avatar_url = str(payload.get("avatar_url", "")).strip()
        if avatar_url.startswith("/static/uploads/"):
            base["avatar_url"] = avatar_url
    avatar_prefix = "user_avatar"
    role_prefix = "role_avatar"
    for path in sorted(UPLOAD_DIR.glob(f"{avatar_prefix}.*")):
        if path.is_file() and path.suffix.lower() in ALLOWED_IMAGE_SUFFIXES:
            base["avatar_url"] = avatar_upload_url(path.name)
            break
    base["role_avatar_url"] = ""
    for path in sorted(UPLOAD_DIR.glob(f"{role_prefix}.*")):
        if path.is_file() and path.suffix.lower() in ALLOWED_IMAGE_SUFFIXES:
            base["role_avatar_url"] = avatar_upload_url(path.name)
            break
    return base


def get_user_profile(slot_id: str | None = None) -> dict[str, Any]:
    return sanitize_user_profile(read_json(user_profile_path(), {}))


def save_user_profile(payload: dict[str, Any], slot_id: str | None = None) -> dict[str, Any]:
    existing = get_user_profile()
    merged = {**existing, **payload}
    sanitized = sanitize_user_profile(merged)
    persist_json(user_profile_path(), sanitized, detail="User profile save failed. Please check disk space or file permissions.")
    return sanitized


def get_role_avatar_url(slot_id: str | None = None) -> str:
    return str(get_user_profile(slot_id).get("role_avatar_url", "")).strip()


def get_memories(slot_id: str | None = None) -> list[dict[str, Any]]:
    return sanitize_memories(read_json(memories_path(slot_id), []))


def get_worldbook(slot_id: str | None = None) -> dict[str, str]:
    return sanitize_worldbook(get_worldbook_store(slot_id))


def get_worldbook_store(slot_id: str | None = None) -> dict[str, Any]:
    return sanitize_worldbook_store(read_json(worldbook_path(slot_id), {}))


def get_worldbook_entries(slot_id: str | None = None) -> list[dict[str, Any]]:
    return get_worldbook_store(slot_id)["entries"]


def get_worldbook_settings(slot_id: str | None = None) -> dict[str, Any]:
    return get_worldbook_store(slot_id)["settings"]


def save_memories(items: list[dict[str, Any]], slot_id: str | None = None) -> list[dict[str, Any]]:
    sanitized = sanitize_memories(items)
    persist_json(
        memories_path(slot_id),
        sanitized,
        detail="Memory save failed. Please check disk space or file permissions.",
    )
    return sanitized


def save_worldbook(entries: dict[str, str], slot_id: str | None = None) -> dict[str, str]:
    sanitized = sanitize_worldbook(entries)
    persist_json(
        worldbook_path(slot_id),
        {"settings": get_worldbook_settings(slot_id), "entries": [{"trigger": key, "content": value} for key, value in sanitized.items()]},
        detail="Worldbook save failed. Please check disk space or file permissions.",
    )
    return sanitized


def save_worldbook_store(store: dict[str, Any], slot_id: str | None = None) -> dict[str, Any]:
    sanitized = sanitize_worldbook_store(store)
    persist_json(
        worldbook_path(slot_id),
        sanitized,
        detail="Worldbook save failed. Please check disk space or file permissions.",
    )
    return sanitized


def save_worldbook_entries(entries: list[dict[str, Any]], slot_id: str | None = None) -> list[dict[str, Any]]:
    store = get_worldbook_store(slot_id)
    store["entries"] = entries
    return save_worldbook_store(store, slot_id)["entries"]


def save_worldbook_settings(settings: dict[str, Any], slot_id: str | None = None) -> dict[str, Any]:
    store = get_worldbook_store(slot_id)
    store["settings"] = settings
    return save_worldbook_store(store, slot_id)["settings"]


def get_current_card(slot_id: str | None = None) -> dict[str, Any]:
    data = read_json(global_current_card_path(), {})
    if not isinstance(data, dict):
        return {"source_name": "", "raw": default_role_card()}
    return {
        "source_name": str(data.get("source_name", "")).strip(),
        "raw": normalize_role_card(data.get("raw", {})),
    }

def list_role_card_files() -> list[dict[str, str]]:
    cards: list[dict[str, str]] = []
    for path in sorted(CARDS_DIR.iterdir(), key=lambda item: item.name.lower()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in ROLE_CARD_EXTENSIONS:
            continue
        cards.append({"filename": path.name, "path": str(path)})
    return cards


def read_role_card_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "utf-16"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
        except OSError as exc:
            raise HTTPException(status_code=500, detail="Role card file read failed.") from exc
    raise HTTPException(status_code=400, detail="Role card file encoding could not be detected. Please convert it to UTF-8 or UTF-8 with BOM.")


def repair_deepseek_card_json(text: str) -> str:
    repaired = text.strip()
    if not repaired:
        return repaired

    if not repaired.startswith("{"):
        repaired = "{\n" + repaired

    if not repaired.endswith("}"):
        repaired = repaired.rstrip(", \r\n\t") + "\n}"

    repaired = re.sub(r",\s*([}\]])", r"\1", repaired)

    marker = '"plotStages"'
    if marker in repaired:
        marker_index = repaired.find(marker)
        close_index = repaired.rfind("}", 0, marker_index)
        open_index = repaired.rfind("{", 0, marker_index)
        if close_index != -1 and open_index != -1 and close_index > open_index:
            repaired = repaired[:close_index] + repaired[close_index + 1 :]
            repaired = re.sub(r",\s*([}\]])", r"\1", repaired)

    return repaired


def extract_role_card_payload(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {}

    candidate = data
    if isinstance(data.get("data"), dict):
        candidate = data["data"]
    else:
        for value in data.values():
            if isinstance(value, dict) and isinstance(value.get("data"), dict):
                candidate = value["data"]
                break

    if not isinstance(candidate, dict):
        return {}

    merged = dict(candidate)
    for key in ["name", "description", "personality", "first_mes", "mes_example", "scenario", "creator_notes", "tags", "creativeWorkshop", "plotStages", "personas"]:
        if not merged.get(key) and data.get(key):
            merged[key] = data.get(key)

    return merged


def parse_role_card_json(text: str) -> dict[str, Any]:
    raw = text.strip()
    if not raw:
        raise HTTPException(status_code=400, detail="Role card JSON cannot be empty.")

    try:
        data = json.loads(raw)
    except ValueError:
        repaired = repair_deepseek_card_json(raw)
        try:
            data = json.loads(repaired)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Role card JSON parse failed: {exc}") from exc

    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="Role card JSON root must be an object.")
    return normalize_role_card(extract_role_card_payload(data))

def build_persona_from_role_card(card: dict[str, Any]) -> dict[str, str]:
    sections: list[str] = []

    description = str(card.get("description", "")).strip()
    personality = str(card.get("personality", "")).strip()
    scenario = str(card.get("scenario", "")).strip()
    creator_notes = str(card.get("creator_notes", "")).strip()
    mes_example = str(card.get("mes_example", "")).strip()

    if description:
        sections.append(f"Character Description: {description}")
    if personality:
        sections.append(f"Personality: {personality}")
    if scenario:
        sections.append(f"Scenario: {scenario}")
    if creator_notes:
        sections.append(f"Creator Notes: {creator_notes}")
    if mes_example:
        sections.append(f"Dialogue Example: {mes_example}")

    plot_stages = card.get("plotStages", {})
    if isinstance(plot_stages, dict):
        stage_lines = []
        for key, value in plot_stages.items():
            if not isinstance(value, dict):
                continue
            desc = str(value.get("description", "")).strip()
            rules = str(value.get("rules", "")).strip()
            if desc or rules:
                line = f"Stage {key}"
                if desc:
                    line += f": {desc}"
                if rules:
                    line += f"; Rules: {rules}"
                stage_lines.append(line)
        if stage_lines:
            sections.append("Plot Stages:\n" + "\n".join(stage_lines))

    personas = card.get("personas", {})
    if isinstance(personas, dict):
        persona_lines = []
        persona_names = []
        for key, value in personas.items():
            if not isinstance(value, dict):
                continue
            name = str(value.get("name", "")).strip() or f"Persona {key}"
            persona_names.append(name)
            desc = str(value.get("description", "")).strip()
            personality_text = str(value.get("personality", "")).strip()
            scenario_text = str(value.get("scenario", "")).strip()
            details = [item for item in [desc, personality_text, scenario_text] if item]
            if details:
                persona_lines.append(f"{name}: {'; '.join(details)}")
        if persona_lines:
            if len(persona_names) >= 3:
                ordered_names = ", ".join(persona_names)
                sections.append(
                    "Multi-Character Cast Rules:\n"
                    "This role card contains multiple active characters.\n"
                    f"Every assistant turn must include all of these characters speaking: {ordered_names}.\n"
                    "Do not omit any of them.\n"
                    "Do not merge different characters into one voice.\n"
                    "Write each speaker in a separate paragraph.\n"
                    "Use the exact format `Name: dialogue` for every paragraph.\n"
                    "Keep the speaking order stable across turns unless the user clearly asks for a different order.\n"
                    "Do not say that only one or two characters are present unless the user explicitly removes the others from the scene."
                )
            else:
                sections.append(
                    "Multi-Character Cast Rules:\n"
                    "This role card contains multiple active characters.\n"
                    "When the scene fits, any of them may appear and speak in the same conversation.\n"
                    "Keep each character's name exactly as listed.\n"
                    "Do not merge different characters into one voice.\n"
                    "Write each speaker in separate paragraphs."
                )
            sections.append("Character Cast:\n" + "\n".join(persona_lines))

    return {
        "name": str(card.get("name", "")).strip() or "Unnamed Character",
        "greeting": str(card.get("first_mes", "")).strip() or "Hello, let's start chatting.",
        "system_prompt": "\n\n".join(section for section in sections if section).strip(),
    }

def build_memories_from_role_card(card: dict[str, Any]) -> list[dict[str, Any]]:
    memories: list[dict[str, Any]] = []

    tags = sanitize_tags(card.get("tags", []))
    base_content = "\n".join(
        part
        for part in [
            str(card.get("description", "")).strip(),
            str(card.get("personality", "")).strip(),
            str(card.get("scenario", "")).strip(),
        ]
        if part
    ).strip()
    if base_content:
        memories.append(
            {
                "id": "card-base",
                "title": str(card.get("name", "")).strip() or "瑙掕壊鍩虹璁惧畾",
                "content": base_content,
                "tags": tags,
                "notes": str(card.get("creator_notes", "")).strip(),
            }
        )

    plot_stages = card.get("plotStages", {})
    if isinstance(plot_stages, dict):
        for key, value in plot_stages.items():
            if not isinstance(value, dict):
                continue
            content = "\n".join(
                part
                for part in [
                    str(value.get("description", "")).strip(),
                    str(value.get("rules", "")).strip(),
                ]
                if part
            ).strip()
            if content:
                memories.append(
                    {
                        "id": f"plot-stage-{key}",
                        "title": f"鍓ф儏闃舵 {key}",
                        "content": content,
                        "tags": ["plotStage", key],
                        "notes": "",
                    }
                )

    personas = card.get("personas", {})
    if isinstance(personas, dict):
        for key, value in personas.items():
            if not isinstance(value, dict):
                continue
            content = "\n".join(
                part
                for part in [
                    str(value.get("description", "")).strip(),
                    str(value.get("personality", "")).strip(),
                    str(value.get("scenario", "")).strip(),
                ]
                if part
            ).strip()
            if content:
                memories.append(
                    {
                        "id": f"persona-{key}",
                        "title": str(value.get("name", "")).strip() or f"瑙掕壊 {key}",
                        "content": content,
                        "tags": ["persona", key],
                        "notes": str(value.get("creator_notes", "")).strip(),
                    }
                )

    return sanitize_memories(memories)


def apply_role_card(card: dict[str, Any], *, source_name: str = "", slot_id: str | None = None) -> dict[str, Any]:
    normalized_card = normalize_role_card(card)
    target_slot = sanitize_slot_id(slot_id, get_active_slot_id())
    next_source_name = Path(str(source_name or "").strip()).name
    persona = build_persona_from_role_card(normalized_card)
    current_settings = get_settings(target_slot)
    current_memories = get_memories(target_slot)
    current_worldbook_store = get_worldbook_store(target_slot)

    persist_json(
        global_persona_path(),
        persona,
        detail="Failed to write role settings. Please check persona.json permissions.",
    )
    current_card = {
        "source_name": next_source_name,
        "raw": normalized_card,
    }
    persist_json(
        global_current_card_path(),
        current_card,
        detail="Failed to save current card data. Please check file permissions.",
    )

    return {
        "persona": persona,
        "card": current_card,
        "current_memory_count": len(current_memories),
        "current_worldbook_count": len(current_worldbook_store["entries"]),
        "current_background_image_url": str(current_settings.get("background_image_url", "")).strip(),
        "current_background_overlay": clamp_float(
            current_settings.get("background_overlay"),
            0.0,
            0.85,
            DEFAULT_SETTINGS["background_overlay"],
        ),
    }


def save_workshop_card(workshop: dict[str, Any], *, slot_id: str | None = None) -> dict[str, Any]:
    target_slot = sanitize_slot_id(slot_id, get_active_slot_id())
    current_card = get_current_card(target_slot)
    current_raw = current_card.get("raw", {})
    if not isinstance(current_raw, dict):
        current_raw = {}

    updated_raw = json.loads(json.dumps(current_raw, ensure_ascii=False))
    updated_raw["creativeWorkshop"] = sanitize_creative_workshop(workshop)
    normalized_card = normalize_role_card(updated_raw)
    source_name = str(current_card.get("source_name", "")).strip()
    if not source_name:
        source_name = "role_card.json"
    source_path = CARDS_DIR / Path(source_name).name

    persist_json(
        source_path,
        normalized_card,
        detail="Creative workshop config save failed. Could not write the role card file.",
    )
    current_card_payload = {
        "source_name": source_path.name,
        "raw": normalized_card,
    }
    persist_json(
        global_current_card_path(),
        current_card_payload,
        detail="Creative workshop config save failed. Could not update the current card record.",
    )
    return {
        "current_card": current_card_payload,
        "card": normalized_card,
        "workshop": sanitize_creative_workshop(updated_raw["creativeWorkshop"]),
        "workshop_state": get_workshop_state(target_slot),
    }


def sanitize_runtime_overrides(raw: dict[str, Any] | None) -> dict[str, Any]:
    source = raw if isinstance(raw, dict) else {}
    default_sprite_path = default_sprite_base_path_for_slot()
    sprite_base_path = str(source.get("sprite_base_path", default_sprite_path)).strip() or default_sprite_path
    if sprite_base_path == DEFAULT_SPRITE_BASE_PATH or sprite_base_path.startswith(f"{DEFAULT_SPRITE_BASE_PATH}/"):
        sprite_base_path = default_sprite_path
    return {
        "llm_base_url": str(source.get("llm_base_url", "")).strip(),
        "llm_api_key": str(source.get("llm_api_key", "")).strip(),
        "llm_model": str(source.get("llm_model", "")).strip(),
        "temperature": clamp_float(source.get("temperature"), 0.0, 2.0, 0.85),
        "history_limit": clamp_int(source.get("history_limit"), 1, 100, 20),
        "request_timeout": clamp_int(source.get("request_timeout"), 10, 600, 120),
        "demo_mode": parse_bool(source.get("demo_mode"), False),
        "embedding_base_url": str(source.get("embedding_base_url", "")).strip(),
        "embedding_api_key": str(source.get("embedding_api_key", "")).strip(),
        "embedding_model": str(source.get("embedding_model", "")).strip(),
        "embedding_fields": sanitize_embedding_fields(source.get("embedding_fields")),
        "retrieval_top_k": clamp_int(source.get("retrieval_top_k"), 1, 12, 4),
        "rerank_enabled": parse_bool(source.get("rerank_enabled"), False),
        "rerank_base_url": str(source.get("rerank_base_url", "")).strip(),
        "rerank_api_key": str(source.get("rerank_api_key", "")).strip(),
        "rerank_model": str(source.get("rerank_model", "")).strip(),
        "rerank_top_n": clamp_int(source.get("rerank_top_n"), 1, 12, 3),
        "sprite_enabled": parse_bool(source.get("sprite_enabled"), True),
        "sprite_base_path": sprite_base_path,
    }


def resolve_runtime_value(override_value: Any, stored_value: Any, env_key: str | None = None) -> Any:
    if isinstance(override_value, str):
        if override_value.strip():
            return override_value.strip()
    elif override_value is not None:
        return override_value

    if isinstance(stored_value, str):
        if stored_value.strip():
            return stored_value.strip()
    elif stored_value is not None:
        return stored_value

    if env_key:
        return os.getenv(env_key, "").strip()
    return stored_value


def get_runtime_chat_config(runtime_overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    settings = get_settings()
    overrides = sanitize_runtime_overrides(runtime_overrides)
    return {
        "base_url": resolve_runtime_value(overrides.get("llm_base_url"), settings.get("llm_base_url", ""), "LLM_BASE_URL"),
        "api_key": resolve_runtime_value(overrides.get("llm_api_key"), settings.get("llm_api_key", ""), "LLM_API_KEY"),
        "model": resolve_runtime_value(overrides.get("llm_model"), settings.get("llm_model", ""), "LLM_MODEL"),
        "temperature": overrides.get("temperature") if runtime_overrides else settings.get("temperature", 0.85),
        "history_limit": overrides.get("history_limit") if runtime_overrides else settings.get("history_limit", 20),
        "request_timeout": overrides.get("request_timeout") if runtime_overrides else settings.get("request_timeout", 120),
        "demo_mode": overrides.get("demo_mode") if runtime_overrides else settings.get("demo_mode", False),
        "sprite_enabled": overrides.get("sprite_enabled") if runtime_overrides else settings.get("sprite_enabled", True),
        "sprite_base_path": overrides.get("sprite_base_path") if runtime_overrides else settings.get("sprite_base_path", DEFAULT_SPRITE_BASE_PATH),
    }


def get_runtime_embedding_config(runtime_overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    settings = get_settings()
    overrides = sanitize_runtime_overrides(runtime_overrides)
    return {
        "base_url": resolve_runtime_value(overrides.get("embedding_base_url"), settings.get("embedding_base_url", ""), "EMBEDDING_BASE_URL"),
        "api_key": resolve_runtime_value(overrides.get("embedding_api_key"), settings.get("embedding_api_key", ""), "EMBEDDING_API_KEY"),
        "model": resolve_runtime_value(overrides.get("embedding_model"), settings.get("embedding_model", ""), "EMBEDDING_MODEL"),
        "request_timeout": overrides.get("request_timeout") if runtime_overrides else settings.get("request_timeout", 120),
        "fields": overrides.get("embedding_fields") if runtime_overrides else settings.get("embedding_fields", DEFAULT_SETTINGS["embedding_fields"]),
        "top_k": overrides.get("retrieval_top_k") if runtime_overrides else settings.get("retrieval_top_k", 4),
    }


def get_runtime_rerank_config(runtime_overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    settings = get_settings()
    overrides = sanitize_runtime_overrides(runtime_overrides)
    return {
        "enabled": overrides.get("rerank_enabled") if runtime_overrides else settings.get("rerank_enabled", False),
        "base_url": resolve_runtime_value(overrides.get("rerank_base_url"), settings.get("rerank_base_url", ""), "RERANK_BASE_URL"),
        "api_key": resolve_runtime_value(overrides.get("rerank_api_key"), settings.get("rerank_api_key", ""), "RERANK_API_KEY"),
        "model": resolve_runtime_value(overrides.get("rerank_model"), settings.get("rerank_model", ""), "RERANK_MODEL"),
        "request_timeout": overrides.get("request_timeout") if runtime_overrides else settings.get("request_timeout", 120),
        "top_n": overrides.get("rerank_top_n") if runtime_overrides else settings.get("rerank_top_n", 3),
    }


def append_messages(entries: list[tuple[str, str]]) -> None:
    history = get_conversation()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for role, content in entries:
        history.append(
            {
                "role": role,
                "content": content,
                "created_at": timestamp,
            }
        )

    persist_json(
        conversation_path(),
        history,
        detail="Chat history save failed. Please check disk space or file permissions.",
    )


def build_memory_text(memory: dict[str, Any], fields: list[str]) -> str:
    parts: list[str] = []
    if "title" in fields and memory.get("title"):
        parts.append(f"Title: {memory['title']}")
    if "content" in fields and memory.get("content"):
        parts.append(f"Content: {memory['content']}")
    if "tags" in fields and memory.get("tags"):
        parts.append(f"Tags: {'、'.join(memory['tags'])}")
    if "notes" in fields and memory.get("notes"):
        parts.append(f"Notes: {memory['notes']}")
    return "\n".join(parts).strip()


def normalize_base_url(base_url: str) -> str:
    return base_url.strip().rstrip("/")


def build_api_url(base_url: str, endpoint: str) -> str:
    clean_base = normalize_base_url(base_url)
    clean_endpoint = endpoint.strip("/")
    if not clean_base:
        return ""
    if clean_base.endswith("/" + clean_endpoint) or clean_base.endswith(clean_endpoint):
        return clean_base
    return f"{clean_base}/{clean_endpoint}"


def build_headers(api_key: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_key.strip():
        headers["Authorization"] = f"Bearer {api_key.strip()}"
    return headers


def should_retry_status_code(status_code: int) -> bool:
    if status_code in {408, 409, 425, 429}:
        return True
    return status_code >= 500


async def request_json(
    *,
    url: str,
    api_key: str,
    payload: dict[str, Any],
    request_timeout: int,
) -> dict[str, Any]:
    last_error: Exception | None = None
    last_error_detail = ""

    for attempt in range(1, REQUEST_RETRY_ATTEMPTS + 1):
        try:
            async with httpx.AsyncClient(timeout=float(request_timeout)) as client:
                response = await client.post(url, headers=build_headers(api_key), json=payload)
                response.raise_for_status()

            try:
                return response.json()
            except ValueError as exc:
                last_error = exc
                logger.warning(
                    "Upstream JSON parse failed on attempt %s/%s for %s",
                    attempt,
                    REQUEST_RETRY_ATTEMPTS,
                    url,
                )
        except httpx.HTTPStatusError as exc:
            last_error = exc
            response_text = exc.response.text.strip() if exc.response is not None else ""
            last_error_detail = response_text[:500]
            logger.warning(
                "Upstream request failed on attempt %s/%s for %s: %s | body=%s",
                attempt,
                REQUEST_RETRY_ATTEMPTS,
                url,
                exc,
                last_error_detail or "<empty>",
            )
            status_code = exc.response.status_code if exc.response is not None else 0
            if 400 <= status_code < 500 and not should_retry_status_code(status_code):
                break
        except httpx.HTTPError as exc:
            last_error = exc
            last_error_detail = ""
            logger.warning(
                "Upstream request failed on attempt %s/%s for %s: %s",
                attempt,
                REQUEST_RETRY_ATTEMPTS,
                url,
                exc,
            )

        if attempt < REQUEST_RETRY_ATTEMPTS:
            await asyncio.sleep(REQUEST_RETRY_BASE_DELAY_SECONDS * attempt)

    if isinstance(last_error, ValueError):
        raise HTTPException(status_code=502, detail="妯″瀷杩斿洖鐨勪笉鏄悎娉?JSON") from last_error

    detail = f"妯″瀷璇锋眰澶辫触: {last_error}"
    if last_error_detail:
        detail = f"{detail} | upstream={last_error_detail}"
    raise HTTPException(status_code=502, detail=detail) from last_error


async def fetch_available_models(
    *,
    base_url: str,
    api_key: str,
    request_timeout: int,
) -> list[str]:
    url = build_api_url(base_url, "models")
    if not url:
        raise HTTPException(status_code=400, detail="Please enter a chat model API URL first.")

    try:
        async with httpx.AsyncClient(timeout=float(request_timeout)) as client:
            response = await client.get(url, headers=build_headers(api_key))
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        response_text = exc.response.text.strip() if exc.response is not None else ""
        detail = response_text[:500] if response_text else str(exc)
        raise HTTPException(status_code=502, detail=f"Failed to fetch model list: {detail}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch model list: {exc}") from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Model list endpoint did not return valid JSON.") from exc

    rows = data.get("data", [])
    if not isinstance(rows, list):
        raise HTTPException(status_code=502, detail="Model list endpoint returned an invalid format.")

    models: list[str] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        model_id = str(item.get("id", "")).strip()
        if model_id and model_id not in models:
            models.append(model_id)

    return models


async def request_minimal_model_reply() -> dict[str, Any]:
    llm_config = get_runtime_chat_config()
    url = build_api_url(llm_config["base_url"], "chat/completions")
    payload = {
        "model": llm_config["model"],
        "messages": [
            {
                "role": "user",
                "content": "Please reply with one short sentence: connection test successful.",
            }
        ],
    }
    data = await request_json(
        url=url,
        api_key=llm_config["api_key"],
        payload=payload,
        request_timeout=int(llm_config["request_timeout"]),
    )

    try:
        raw_reply = str(data["choices"][0]["message"]["content"]).strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(status_code=502, detail="Model response format is invalid.") from exc

    sprite_tag, cleaned_reply = extract_sprite_tag(raw_reply)
    return {
        "reply": cleaned_reply or raw_reply,
        "sprite_tag": sprite_tag,
        "worldbook_enforced": False,
    }


async def fetch_embeddings(texts: list[str], runtime_overrides: dict[str, Any] | None = None) -> list[list[float]]:
    embedding = get_runtime_embedding_config(runtime_overrides)
    if not (embedding["base_url"] and embedding["model"]):
        return []

    url = build_api_url(embedding["base_url"], "embeddings")
    payload = {"model": embedding["model"], "input": texts}
    data = await request_json(
        url=url,
        api_key=embedding["api_key"],
        payload=payload,
        request_timeout=int(embedding["request_timeout"]),
    )

    rows = data.get("data", [])
    if not isinstance(rows, list):
        raise HTTPException(status_code=502, detail="Embedding model response format is invalid.")

    vectors: list[list[float]] = []
    for row in rows:
        vector = row.get("embedding", []) if isinstance(row, dict) else []
        if not isinstance(vector, list):
            raise HTTPException(status_code=502, detail="Embedding model response format is invalid.")
        vectors.append([float(value) for value in vector])
    return vectors


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0

    dot = sum(l * r for l, r in zip(left, right))
    left_norm = sum(value * value for value in left) ** 0.5
    right_norm = sum(value * value for value in right) ** 0.5
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


async def rerank_documents(
    query: str,
    documents: list[dict[str, Any]],
    runtime_overrides: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    rerank = get_runtime_rerank_config(runtime_overrides)
    if not rerank["enabled"] or not documents:
        return documents
    if not (rerank["base_url"] and rerank["model"]):
        return documents

    url = build_api_url(rerank["base_url"], "rerank")
    payload = {
        "model": rerank["model"],
        "query": query,
        "documents": [item["text"] for item in documents],
        "top_n": min(int(rerank["top_n"]), len(documents)),
    }
    data = await request_json(
        url=url,
        api_key=rerank["api_key"],
        payload=payload,
        request_timeout=int(rerank["request_timeout"]),
    )

    results = data.get("results") or data.get("data") or []
    if not isinstance(results, list):
        logger.warning("Rerank model returned a non-list result; falling back to original documents.")
        return documents

    reranked: list[dict[str, Any]] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        index = item.get("index")
        if not isinstance(index, int) or not (0 <= index < len(documents)):
            continue
        updated = documents[index].copy()
        updated["score"] = round(float(item.get("relevance_score", item.get("score", 0.0))), 4)
        reranked.append(updated)

    return reranked or documents


def match_worldbook_entries(query: str) -> list[dict[str, Any]]:
    text = str(query or "").strip()
    if not text:
        return []

    settings = get_worldbook_settings()
    if not settings.get("enabled", True):
        return []

    hits: list[dict[str, Any]] = []
    for item in get_worldbook_entries():
        if not item.get("enabled", True):
            continue

        primary_aliases = split_trigger_aliases(item.get("trigger", ""))
        if not primary_aliases:
            continue

        case_sensitive = bool(item.get("case_sensitive", settings["default_case_sensitive"]))
        whole_word = bool(item.get("whole_word", settings["default_whole_word"]))
        primary_matches = [
            alias for alias in primary_aliases if keyword_matches_query(text, alias, case_sensitive=case_sensitive, whole_word=whole_word)
        ]

        primary_mode = str(item.get("match_mode", settings["default_match_mode"])).strip().lower()
        primary_ok = bool(primary_matches) if primary_mode != "all" else len(primary_matches) == len(primary_aliases)
        if not primary_ok:
            continue

        secondary_aliases = split_trigger_aliases(item.get("secondary_trigger", ""))
        secondary_matches: list[str] = []
        if secondary_aliases:
            secondary_matches = [
                alias for alias in secondary_aliases if keyword_matches_query(text, alias, case_sensitive=case_sensitive, whole_word=whole_word)
            ]
            secondary_mode = str(item.get("secondary_mode", settings["default_secondary_mode"])).strip().lower()
            secondary_ok = bool(secondary_matches) if secondary_mode != "all" else len(secondary_matches) == len(secondary_aliases)
            if not secondary_ok:
                continue

        hits.append(
            {
                "id": str(item.get("id", "")).strip(),
                "title": str(item.get("title", "")).strip(),
                "trigger": str(item.get("trigger", "")).strip(),
                "secondary_trigger": str(item.get("secondary_trigger", "")).strip(),
                "content": str(item.get("content", "")).strip(),
                "matched": " / ".join(primary_matches + secondary_matches),
                "comment": str(item.get("comment", "")).strip(),
                "priority": int(item.get("priority", 100) or 100),
            }
        )

    hits.sort(key=lambda item: (-int(item.get("priority", 100) or 100), item.get("title", "")))
    max_hits = max(1, int(settings.get("max_hits", DEFAULT_WORLDBOOK_SETTINGS["max_hits"])))
    hits = hits[:max_hits]

    if hits:
        logger.info("涓栫晫涔﹀懡涓細%s", ", ".join(item["matched"] for item in hits))
    return hits


def build_worldbook_prompt(matches: list[dict[str, Any]]) -> str:
    if not matches:
        return ""

    blocks = [
        "The following are the worldbook notes matched in this turn.",
        "These are high-priority factual backdrops for the current conversation.",
        "If the user is asking about any of these items directly, answer from these notes first.",
        "Do not mention that you saw the worldbook notes in your answer.",
    ]
    for index, item in enumerate(matches, start=1):
        matched = item.get("matched", "")
        title = str(item.get("title", "")).strip()
        lines = [f"{index}. Title: {title or item['trigger']}"]
        lines.append(f"Trigger: {item['trigger']}")
        if matched:
            lines.append(f"Matched: {matched}")
        if item.get("secondary_trigger"):
            lines.append(f"Secondary trigger: {item['secondary_trigger']}")
        lines.append(f"Content: {item['content']}")
        if item.get("comment"):
            lines.append(f"Comment: {item['comment']}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def build_worldbook_answer_guard(user_message: str, matches: list[dict[str, str]]) -> str:
    if not matches:
        return ""

    text = str(user_message or "").strip()
    if not text:
        return ""

    direct_question_markers = ("what", "who", "why", "how", "tell me", "explain", "?")
    if not any(marker in text for marker in direct_question_markers):
        return ""

    primary_match = matches[0]
    subject = primary_match.get("matched") or primary_match.get("trigger") or "this item"
    fact = primary_match.get("content", "").strip()
    if not fact:
        return ""

    return (
        f"The user is directly asking about \"{subject}\".\n"
        f"Your first sentence must state the core fact directly, for example: {fact}\n"
        "Answer directly first, then continue in character without dodging or pretending not to know."
    )


def enforce_worldbook_fact_in_reply(
    user_message: str,
    reply_text: str,
    matches: list[dict[str, str]],
) -> str:
    if not matches:
        return reply_text

    text = str(reply_text or "").strip()
    if not text:
        return text

    direct_question_markers = ("what", "who", "why", "how", "tell me", "explain", "?")
    if not any(marker in str(user_message or "") for marker in direct_question_markers):
        return text

    primary_match = matches[0]
    subject = str(primary_match.get("matched") or primary_match.get("trigger") or "").strip()
    fact = str(primary_match.get("content") or "").strip()
    if not subject or not fact:
        return text

    normalized_reply = normalize_match_text(text)
    normalized_subject = normalize_match_text(subject)
    normalized_fact = normalize_match_text(fact[:48])
    if (normalized_subject and normalized_subject in normalized_reply) or (
        normalized_fact and normalized_fact in normalized_reply
    ):
        return text

    logger.info("Worldbook direct-answer guard applied before reply.")
    return f"{fact}\n\n{text}"


def build_sprite_prompt(llm_config: dict[str, Any]) -> str:
    if not llm_config.get("sprite_enabled", True):
        return ""

    return (
        "Always start every reply with a single sprite tag on the first line in the format [expression:tag].\n"
        "Do not omit the tag. Do not place anything before it.\n"
        "Keep the tag short and simple, such as happy, calm, angry, sad, or surprised.\n"
        "After the tag, write the normal reply. Do not explain the rule.\n"
    )


def normalize_sprite_tag(tag: str) -> str:
    text = str(tag or "").strip().lower()
    if not text:
        return ""

    replacements = {
        "neutral": "calm",
        "quiet": "calm",
        "relaxed": "calm",
        "angry": "angry",
        "mad": "angry",
        "happy": "happy",
        "sad": "sad",
        "surprised": "surprised",
    }
    return replacements.get(text, text)


def extract_sprite_tag(reply_text: str) -> tuple[str, str]:
    text = str(reply_text or "").strip()
    if not text:
        return "", ""

    match = re.match(r"^\s*\[(?:琛ㄦ儏|emotion)\s*:\s*([^\]\n]{1,32})\]\s*", text, flags=re.IGNORECASE)
    if not match:
        return "", text

    tag = normalize_sprite_tag(match.group(1).strip())
    cleaned = text[match.end() :].lstrip()
    return tag, cleaned


def extract_reply_parts(raw_text: str) -> dict[str, Any]:
    text = str(raw_text or "")
    if not text:
        return {"sprite_tag": "", "visible": "", "think": "", "thinking": False}

    stripped = text.lstrip()
    if stripped.startswith("[") and "]" not in stripped[:48]:
        return {"sprite_tag": "", "visible": "", "think": "", "thinking": False}

    sprite_tag, cleaned = extract_sprite_tag(text)
    source = cleaned or text

    think_parts: list[str] = []
    visible_parts: list[str] = []
    cursor = 0
    thinking = False
    open_tag_pattern = re.compile(r"<think\b[^>]*>", flags=re.IGNORECASE)

    while True:
        match = open_tag_pattern.search(source, cursor)
        if not match:
            if cursor < len(source):
                visible_parts.append(source[cursor:])
            break

        start = match.start()
        open_end = match.end()
        if start > cursor:
            visible_parts.append(source[cursor:start])

        close_match = re.search(r"</think>", source[open_end:], flags=re.IGNORECASE)
        if not close_match:
            trailing = source[open_end:].strip()
            if trailing:
                think_parts.append(trailing)
            thinking = True
            cursor = len(source)
            break

        close_index = open_end + close_match.start()
        inner = source[open_end:close_index].strip()
        if inner:
            think_parts.append(inner)
        cursor = close_index + len(close_match.group(0))

    visible = "".join(visible_parts)
    visible = re.sub(r"\n{3,}", "\n\n", visible).strip()
    think = "\n\n".join(part for part in think_parts if part).strip()
    return {
        "sprite_tag": sprite_tag,
        "visible": visible,
        "think": think,
        "thinking": thinking,
    }


def compose_full_reply(think_text: str, visible_text: str) -> str:
    think = str(think_text or "").strip()
    visible = str(visible_text or "").strip()
    if think and visible:
        return f"<think>\n{think}\n</think>\n\n{visible}"
    if think:
        return f"<think>\n{think}\n</think>"
    return visible


def extract_stream_visible_reply(raw_text: str) -> tuple[str, str]:
    reply_parts = extract_reply_parts(raw_text)
    return str(reply_parts["sprite_tag"]), str(reply_parts["visible"])


async def retrieve_memories(query: str, runtime_overrides: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    embedding = get_runtime_embedding_config(runtime_overrides)
    memories = get_memories()
    if not memories:
        return []
    if not (embedding["base_url"] and embedding["model"]):
        return []

    documents: list[dict[str, Any]] = []
    for item in memories:
        text = build_memory_text(item, list(embedding["fields"]))
        if text:
            documents.append({**item, "text": text})

    if not documents:
        return []

    vectors = await fetch_embeddings([query] + [item["text"] for item in documents], runtime_overrides)
    expected_count = len(documents) + 1
    if len(vectors) != expected_count:
        logger.warning(
            "Embedding model returned an unexpected number of vectors: expected %s, got %s; skipping memory recall for this turn.",
            expected_count,
            len(vectors),
        )
        return []

    query_vector = vectors[0]
    scored: list[dict[str, Any]] = []
    for doc, doc_vector in zip(documents, vectors[1:]):
        scored.append({**doc, "score": round(cosine_similarity(query_vector, doc_vector), 4)})

    scored.sort(key=lambda item: item["score"], reverse=True)
    top_k = min(int(embedding["top_k"]), len(scored))
    selected = scored[:top_k]
    reranked = await rerank_documents(query, selected, runtime_overrides)

    return [
        {
            "id": item["id"],
            "title": item["title"],
            "content": item["content"],
            "tags": item["tags"],
            "notes": item["notes"],
            "text": item["text"],
            "score": item["score"],
        }
        for item in reranked
    ]


def build_retrieval_prompt(retrieved_items: list[dict[str, Any]]) -> str:
    if not retrieved_items:
        return ""

    blocks = [
        "The following are the most relevant long-term memories for the current message.",
        "Use them as supporting context, but do not hallucinate details that are not present.",
    ]
    for index, item in enumerate(retrieved_items, start=1):
        title = str(item.get("title", "")).strip() or f"Memory {index}"
        blocks.append(f"{index}. {title}\n{item.get('text', '')}")
    return "\n\n".join(blocks)


def build_memory_recap_prompt(memories: list[dict[str, Any]]) -> str:
    if not memories:
        return ""

    blocks = [
        "The following are long-term memories that should stay consistent over time.",
        "Treat them as durable background facts unless the user explicitly asks to revise them.",
    ]
    for index, item in enumerate(memories, start=1):
        title = str(item.get("title", "")).strip() or f"Memory {index}"
        content = str(item.get("content", "")).strip()
        tags = ", ".join(sanitize_tags(item.get("tags", [])))
        notes = str(item.get("notes", "")).strip()
        lines = [f"{index}. {title}"]
        if content:
            lines.append(f"Content: {content}")
        if tags:
            lines.append(f"Tags: {tags}")
        if notes:
            lines.append(f"Notes: {notes}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def build_user_profile_prompt(user_profile: dict[str, Any]) -> str:
    if not isinstance(user_profile, dict):
        return ""

    display_name = str(user_profile.get("display_name", "")).strip()
    nickname = str(user_profile.get("nickname", "")).strip()
    profile_text = str(user_profile.get("profile_text", "")).strip()
    notes = str(user_profile.get("notes", "")).strip()

    if display_name == "" and not any([nickname, profile_text, notes]):
        return ""

    blocks = [
        "The following are the user profile details bound to the current slot.",
        "Treat them as stable background information for addressing and understanding the user.",
        "Do not rewrite these details as if they were your own persona settings.",
    ]
    if display_name:
        blocks.append(f"Display name: {display_name}")
    if nickname:
        blocks.append(f"Nickname: {nickname}")
    if profile_text:
        blocks.append(f"Profile text: {profile_text}")
    if notes:
        blocks.append(f"Notes: {notes}")
    return "\n".join(blocks)


def build_prompt_package(
    user_message: str,
    retrieved_items: list[dict[str, Any]] | None = None,
    *,
    runtime_overrides: dict[str, Any] | None = None,
    worldbook_matches: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    persona = get_persona()
    history = get_conversation()
    memories = get_memories()
    user_profile = get_user_profile()
    llm_config = get_runtime_chat_config(runtime_overrides)

    matched_worldbook_entries = worldbook_matches or []
    recalled_memories = retrieved_items or []

    preset_prompt = build_preset_prompt()
    system_prompt = str(persona.get("system_prompt", "")).strip()
    memory_recap_prompt = build_memory_recap_prompt(memories)
    user_profile_prompt = build_user_profile_prompt(user_profile)
    worldbook_prompt = build_worldbook_prompt(matched_worldbook_entries)
    worldbook_answer_guard = build_worldbook_answer_guard(user_message, matched_worldbook_entries)
    retrieval_prompt = build_retrieval_prompt(recalled_memories)
    sprite_prompt = build_sprite_prompt(llm_config)

    history_limit = max(1, int(llm_config["history_limit"]))
    recent_history = history[-history_limit:]
    recent_history_text = build_conversation_transcript(recent_history)

    actual_system_sections = [
        prompt
        for prompt in [
            preset_prompt,
            system_prompt,
            memory_recap_prompt,
            user_profile_prompt,
            worldbook_prompt,
            worldbook_answer_guard,
            retrieval_prompt,
            sprite_prompt,
        ]
        if str(prompt or "").strip()
    ]

    messages: list[dict[str, str]] = []
    if actual_system_sections:
        messages.append({"role": "system", "content": "\n\n".join(actual_system_sections)})

    for item in recent_history:
        role = str(item.get("role", "assistant")).strip() or "assistant"
        content = str(item.get("content", "")).strip()
        if content:
            messages.append({"role": role, "content": content})

    clean_user_message = str(user_message or "").strip()
    messages.append({"role": "user", "content": clean_user_message})

    layers: list[dict[str, Any]] = []

    def append_layer(layer_id: str, title: str, sections: list[str], **meta: Any) -> None:
        content = "\n\n".join(part for part in sections if str(part or "").strip()).strip()
        if not content:
            return
        layer: dict[str, Any] = {
            "id": layer_id,
            "title": title,
            "content": content,
        }
        if meta:
            layer["meta"] = meta
        layers.append(layer)

    append_layer(
        "system_main",
        "系统提示词 / 主提示",
        [preset_prompt],
        section_count=1 if preset_prompt else 0,
    )
    append_layer(
        "role_card",
        "角色卡固定设定",
        [system_prompt],
        character_name=str(persona.get("name", "")).strip(),
    )
    append_layer(
        "memory_context",
        "记忆 / 摘要 / 长期信息",
        [memory_recap_prompt, retrieval_prompt, user_profile_prompt],
        stored_memory_count=len(memories),
        recalled_memory_count=len(recalled_memories),
    )
    append_layer(
        "worldbook_context",
        "世界书（按需触发）",
        [worldbook_prompt, worldbook_answer_guard],
        hit_count=len(matched_worldbook_entries),
    )
    append_layer(
        "output_rules",
        "输出格式约束",
        [sprite_prompt],
        sprite_enabled=bool(llm_config.get("sprite_enabled", True)),
    )
    append_layer(
        "recent_history",
        "最近聊天记录",
        [recent_history_text],
        turn_count=len(recent_history),
    )
    append_layer(
        "user_input",
        "本轮新输入",
        [clean_user_message],
        char_count=len(clean_user_message),
    )

    preview_blocks: list[str] = []
    for index, layer in enumerate(layers, start=1):
        preview_blocks.append(f"[{index}. {layer['title']}]\n{layer['content']}")

    return {
        "layers": layers,
        "messages": messages,
        "preview_text": "\n\n".join(preview_blocks).strip(),
        "message_count": len(messages),
        "system_section_count": len(actual_system_sections),
        "recent_history_turns": len(recent_history),
    }


def build_messages(
    user_message: str,
    retrieved_items: list[dict[str, Any]] | None = None,
    *,
    runtime_overrides: dict[str, Any] | None = None,
    worldbook_matches: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    return build_prompt_package(
        user_message,
        retrieved_items,
        runtime_overrides=runtime_overrides,
        worldbook_matches=worldbook_matches,
    )["messages"]


async def request_model_reply(
    user_message: str,
    retrieved_items: list[dict[str, Any]],
    *,
    runtime_overrides: dict[str, Any] | None = None,
    worldbook_matches: list[dict[str, str]] | None = None,
    prompt_package: dict[str, Any] | None = None,
) -> dict[str, Any]:
    llm_config = get_runtime_chat_config(runtime_overrides)
    package = prompt_package or build_prompt_package(
        user_message,
        retrieved_items,
        runtime_overrides=runtime_overrides,
        worldbook_matches=worldbook_matches,
    )
    url = build_api_url(llm_config["base_url"], "chat/completions")
    payload = {
        "model": llm_config["model"],
        "messages": package["messages"],
        "temperature": llm_config["temperature"],
    }
    data = await request_json(
        url=url,
        api_key=llm_config["api_key"],
        payload=payload,
        request_timeout=int(llm_config["request_timeout"]),
    )

    try:
        raw_reply = str(data["choices"][0]["message"]["content"]).strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(status_code=502, detail="Model response format is invalid.") from exc

    reply_parts = extract_reply_parts(raw_reply)
    sprite_tag = str(reply_parts["sprite_tag"])
    reply_source = str(reply_parts["visible"] or raw_reply)
    final_reply = enforce_worldbook_fact_in_reply(
        user_message,
        reply_source,
        worldbook_matches or [],
    )
    worldbook_enforced = final_reply != reply_source
    if not sprite_tag and llm_config.get("sprite_enabled", True):
        sprite_tag = "calm"
    return {
        "reply": final_reply,
        "full_reply": compose_full_reply(str(reply_parts["think"]), final_reply),
        "think": str(reply_parts["think"]),
        "sprite_tag": sprite_tag,
        "worldbook_enforced": worldbook_enforced,
    }


def build_worldbook_debug_payload(
    user_message: str,
    worldbook_matches: list[dict[str, str]],
    *,
    reply_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not get_worldbook_settings().get("debug_enabled", False):
        return {}
    return {
        "hit_count": len(worldbook_matches),
        "prompt": build_worldbook_prompt(worldbook_matches),
        "guard": build_worldbook_answer_guard(user_message, worldbook_matches),
        "enforced": bool((reply_result or {}).get("worldbook_enforced")),
        "matched": worldbook_matches,
    }


async def stream_model_reply(
    user_message: str,
    retrieved_items: list[dict[str, Any]],
    *,
    runtime_overrides: dict[str, Any] | None = None,
    worldbook_matches: list[dict[str, str]] | None = None,
    prompt_package: dict[str, Any] | None = None,
):
    llm_config = get_runtime_chat_config(runtime_overrides)
    package = prompt_package or build_prompt_package(
        user_message,
        retrieved_items,
        runtime_overrides=runtime_overrides,
        worldbook_matches=worldbook_matches,
    )
    url = build_api_url(llm_config["base_url"], "chat/completions")
    payload = {
        "model": llm_config["model"],
        "messages": package["messages"],
        "temperature": llm_config["temperature"],
        "stream": True,
    }

    accumulated_raw = ""
    accumulated_visible = ""
    accumulated_think = ""
    sprite_tag = ""
    was_thinking = False
    stream_started = False
    last_error: Exception | None = None
    last_error_detail = ""

    for attempt in range(1, REQUEST_RETRY_ATTEMPTS + 1):
        try:
            async with httpx.AsyncClient(timeout=float(llm_config["request_timeout"])) as client:
                async with client.stream(
                    "POST",
                    url,
                    headers=build_headers(llm_config["api_key"]),
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        if not line.startswith("data:"):
                            continue
                        data_line = line[5:].strip()
                        if not data_line or data_line == "[DONE]":
                            break
                        try:
                            data = json.loads(data_line)
                        except ValueError:
                            continue

                        choices = data.get("choices") or []
                        if not isinstance(choices, list) or not choices:
                            continue
                        delta = choices[0].get("delta") or {}
                        chunk = delta.get("content")
                        if not isinstance(chunk, str) or not chunk:
                            continue

                        stream_started = True
                        accumulated_raw += chunk
                        reply_parts = extract_reply_parts(accumulated_raw)
                        parsed_tag = str(reply_parts["sprite_tag"])
                        visible_text = str(reply_parts["visible"])
                        think_text = str(reply_parts["think"])
                        is_thinking = bool(reply_parts["thinking"])
                        if parsed_tag and not sprite_tag:
                            sprite_tag = parsed_tag
                        if is_thinking and not was_thinking:
                            yield {"type": "think_start"}
                        if len(think_text) > len(accumulated_think):
                            think_delta = think_text[len(accumulated_think) :]
                            accumulated_think = think_text
                            if think_delta:
                                yield {"type": "think_chunk", "delta": think_delta}
                        if was_thinking and not is_thinking:
                            yield {"type": "think_end"}
                        was_thinking = is_thinking
                        if len(visible_text) > len(accumulated_visible):
                            delta_text = visible_text[len(accumulated_visible) :]
                            accumulated_visible = visible_text
                            if delta_text:
                                yield {"type": "chunk", "delta": delta_text}
            break
        except httpx.HTTPStatusError as exc:
            last_error = exc
            response_text = exc.response.text.strip() if exc.response is not None else ""
            last_error_detail = response_text[:500]
            status_code = exc.response.status_code if exc.response is not None else 0
            logger.warning(
                "Upstream stream request failed on attempt %s/%s for %s: %s | body=%s",
                attempt,
                REQUEST_RETRY_ATTEMPTS,
                url,
                exc,
                last_error_detail or "<empty>",
            )
            if stream_started or (400 <= status_code < 500 and not should_retry_status_code(status_code)):
                break
        except httpx.HTTPError as exc:
            last_error = exc
            last_error_detail = ""
            logger.warning(
                "Upstream stream request failed on attempt %s/%s for %s: %s",
                attempt,
                REQUEST_RETRY_ATTEMPTS,
                url,
                exc,
            )
            if stream_started:
                break

        if attempt < REQUEST_RETRY_ATTEMPTS and not stream_started:
            await asyncio.sleep(REQUEST_RETRY_BASE_DELAY_SECONDS * attempt)

    if last_error and not accumulated_raw and not accumulated_visible and not accumulated_think:
        detail = f"妯″瀷娴佸紡璇锋眰澶辫触: {last_error}"
        if last_error_detail:
            detail = f"{detail} | upstream={last_error_detail}"
        raise HTTPException(status_code=502, detail=detail) from last_error

    reply_result: dict[str, Any] = {
        "reply": enforce_worldbook_fact_in_reply(
            user_message,
            accumulated_visible or accumulated_raw,
            worldbook_matches or [],
        ),
        "sprite_tag": sprite_tag or ("骞抽潤" if llm_config.get("sprite_enabled", True) else ""),
    }
    reply_result["full_reply"] = compose_full_reply(accumulated_think, str(reply_result["reply"]))
    reply_result["think"] = accumulated_think
    reply_result["worldbook_enforced"] = reply_result["reply"] != (accumulated_visible or accumulated_raw)
    yield {"type": "done", **reply_result}


async def generate_reply(
    user_message: str,
    runtime_overrides: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, str]], dict[str, Any]]:
    llm_config = get_runtime_chat_config(runtime_overrides)
    retrieved = await retrieve_memories(user_message, runtime_overrides)
    worldbook_matches = match_worldbook_entries(user_message)
    prompt_package = build_prompt_package(
        user_message,
        retrieved,
        runtime_overrides=runtime_overrides,
        worldbook_matches=worldbook_matches,
    )

    if not (llm_config["base_url"] and llm_config["model"]):
        if not llm_config["demo_mode"]:
            raise HTTPException(
                status_code=400,
                detail="Please configure the chat model API URL and model name first, or enable demo mode.",
            )
        return {"reply": "", "sprite_tag": ""}, retrieved, worldbook_matches, prompt_package

    reply = await request_model_reply(
        user_message,
        retrieved,
        runtime_overrides=runtime_overrides,
        worldbook_matches=worldbook_matches,
        prompt_package=prompt_package,
    )
    return reply, retrieved, worldbook_matches, prompt_package


def build_conversation_transcript(history: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for item in history:
        role = item.get("role", "")
        content = str(item.get("content", "")).strip()
        if role not in {"user", "assistant"} or not content:
            continue
        speaker = "User" if role == "user" else "AI"
        lines.append(f"{speaker}: {content}")
    return "\n".join(lines)


def fallback_memory_from_conversation(history: list[dict[str, Any]]) -> dict[str, Any]:
    def compact_text(value: Any, limit: int) -> str:
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        if len(text) <= limit:
            return text
        return text[: max(limit - 3, 0)].rstrip() + "..."

    transcript = build_conversation_transcript(history)
    last_user = next(
        (str(item.get("content", "")).strip() for item in reversed(history) if item.get("role") == "user"),
        "",
    )
    title_source = last_user or transcript or "Conversation Memory"
    title = compact_text(title_source, 32) or "Conversation Memory"

    highlighted_turns: list[str] = []
    for item in history[-8:]:
        role = str(item.get("role", "")).strip()
        content = compact_text(item.get("content", ""), 110)
        if role not in {"user", "assistant"} or not content:
            continue
        speaker = "User" if role == "user" else "AI"
        highlighted_turns.append(f"{speaker}: {content}")

    recent_exchange = " | ".join(highlighted_turns)
    compact = recent_exchange or compact_text(transcript, 420)
    notes_parts = []
    if last_user:
        notes_parts.append(f"Latest user request: {compact_text(last_user, 140)}")
    if highlighted_turns:
        notes_parts.append(f"Recent key turns: {recent_exchange}")
    return {
        "title": title,
        "content": compact or "A detailed long-term memory summary was created for this conversation.",
        "tags": ["auto-memory", "summary"],
        "notes": "\n".join(notes_parts).strip(),
    }


async def request_conversation_summary_with_model(history: list[dict[str, Any]]) -> dict[str, Any]:
    llm_config = get_runtime_chat_config()
    if not (llm_config["base_url"] and llm_config["model"]):
        raise ValueError("chat model is not configured")

    url = build_api_url(llm_config["base_url"], "chat/completions")
    transcript = build_conversation_transcript(history)
    schema_hint = (
        '{\n'
        '  "title": "short topic title",\n'
        '  "content": "a detailed long-term memory summary that covers the important events, decisions, outcomes, and unresolved threads",\n'
        '  "tags": ["tag1", "tag2", "tag3"],\n'
        '  "notes": "optional extra specifics such as names, promises, locations, numbers, and unresolved items"\n'
        '}'
    )
    payload = {
        "model": llm_config["model"],
        "temperature": 0.2,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a dialogue memory formatter for long-term chat memory. "
                    "Return one strict JSON object only. "
                    "Do not output markdown fences, explanation, roleplay, XML, or any extra text. "
                    "The JSON object must contain exactly these keys: title, content, tags, notes. "
                    "Capture concrete events instead of vague themes. "
                    "If multiple important events happened, include all of them. "
                    "Prefer specifics: requests, decisions, promises, outcomes, emotional turning points, changes of state, and unresolved follow-ups. "
                    "title must be a short topic title within 32 Chinese characters or 64 ASCII chars. "
                    "content must be a detailed but compact memory summary, usually 2 to 5 sentences. "
                    "content should normally be at least 120 Chinese characters or 220 ASCII chars when enough detail exists. "
                    "tags must be an array of 2 to 6 short strings. "
                    "notes may be empty, but should include extra specifics when useful. "
                    "Output must start with { and end with }."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Summarize the full conversation below into one long-term memory entry.\n"
                    "Do not omit important incidents just to keep it short.\n"
                    "Focus on what actually happened, what changed, what was decided, what was promised, and what still matters later.\n"
                    "Return JSON only.\n"
                    f"Format example:\n{schema_hint}\n\n"
                    f"Conversation:\n{transcript}"
                ),
            },
        ],
    }
    data = await request_json(
        url=url,
        api_key=llm_config["api_key"],
        payload=payload,
        request_timeout=int(llm_config["request_timeout"]),
    )

    try:
        text = str(data["choices"][0]["message"]["content"]).strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("invalid summary payload") from exc

    def parse_summary_json(candidate: str) -> dict[str, Any]:
        cleaned = str(candidate or "").strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            parsed = json.loads(cleaned)
        except ValueError:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start == -1 or end == -1 or end <= start:
                raise ValueError("summary is not json") from None
            parsed = json.loads(cleaned[start : end + 1])

        if not isinstance(parsed, dict):
            raise ValueError("summary json must be an object")

        required_keys = {"title", "content", "tags", "notes"}
        if not required_keys.issubset(parsed.keys()):
            raise ValueError("summary json missing required keys")
        return parsed

    try:
        summary = parse_summary_json(text)
        logger.info("Automatic memory summary parsed as strict JSON on first pass.")
        return summary
    except ValueError:
        logger.warning("Automatic memory summary was not strict JSON, trying one repair pass.")
        repair_payload = {
            "model": llm_config["model"],
            "temperature": 0.0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Convert the provided text into one strict JSON object only. "
                        "Do not output markdown, explanation, or extra text. "
                        "The object must contain exactly these keys: title, content, tags, notes."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Repair the following content into strict JSON.\n"
                        f"Format example:\n{schema_hint}\n\n"
                        f"Original content:\n{text}"
                    ),
                },
            ],
        }
        repair_data = await request_json(
            url=url,
            api_key=llm_config["api_key"],
            payload=repair_payload,
            request_timeout=int(llm_config["request_timeout"]),
        )
        try:
            repaired_text = str(repair_data["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("invalid summary repair payload") from exc
        summary = parse_summary_json(repaired_text)
        logger.info("Automatic memory summary repaired into strict JSON successfully.")
        return summary


def sanitize_memory_summary(payload: dict[str, Any], *, fallback: dict[str, Any]) -> dict[str, Any]:
    title = str(payload.get("title", "")).strip() or fallback["title"]
    content = str(payload.get("content", "")).strip() or fallback["content"]
    tags = sanitize_tags(payload.get("tags", fallback["tags"])) or ["auto-memory", "summary"]
    notes = str(payload.get("notes", "")).strip() or str(fallback.get("notes", "")).strip()

    normalized_content = re.sub(r"\s+", " ", content).strip()
    fallback_content = str(fallback.get("content", "")).strip()
    if len(normalized_content) < 80 and len(fallback_content) > len(normalized_content):
        content = fallback_content

    return {
        "id": f"memory-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        "title": title[:60],
        "content": content[:520],
        "tags": tags[:8],
        "notes": notes[:800],
    }


async def summarize_conversation_to_memory(history: list[dict[str, Any]]) -> dict[str, Any]:
    fallback = fallback_memory_from_conversation(history)
    try:
        summary_payload = await request_conversation_summary_with_model(history)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Automatic memory summary failed, falling back to local summary: %s", exc)
        summary_payload = fallback

    return sanitize_memory_summary(summary_payload, fallback=fallback)


async def archive_current_conversation() -> dict[str, Any]:
    history = [item for item in get_conversation() if item.get("role") in {"user", "assistant"}]
    if not history:
        raise HTTPException(status_code=400, detail="There is no conversation to archive yet.")

    memory = await summarize_conversation_to_memory(history)
    memories = get_memories()
    if memories:
        last = memories[-1]
        if last.get("title") == memory["title"] and last.get("content") == memory["content"]:
            persist_json(
                conversation_path(),
                [],
                detail="Conversation archive failed: could not clear the current chat history.",
            )
            return last

    memories.append(memory)
    save_memories(memories)
    persist_json(
        conversation_path(),
        [],
        detail="Conversation archive failed: could not clear the current chat history.",
    )
    return memory

load_env_file()
ensure_data_files()

bootstrap_runtime_layout()

app = FastAPI(title="Xuqi LLM Chat")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))



route_ctx = SimpleNamespace(
    ALLOWED_IMAGE_SUFFIXES=ALLOWED_IMAGE_SUFFIXES,
    CARDS_DIR=CARDS_DIR,
    EXPORT_DIR=EXPORT_DIR,
    MAX_BACKGROUND_UPLOAD_SIZE_BYTES=MAX_BACKGROUND_UPLOAD_SIZE_BYTES,
    ROLE_CARD_EXTENSIONS=ROLE_CARD_EXTENSIONS,
    UPLOAD_DIR=UPLOAD_DIR,
    activate_preset_in_store=activate_preset_in_store,
    append_messages=append_messages,
    apply_role_card=apply_role_card,
    archive_current_conversation=archive_current_conversation,
    build_prompt_package=build_prompt_package,
    build_preset_debug_payload=build_preset_debug_payload,
    build_worldbook_debug_payload=build_worldbook_debug_payload,
    conversation_path=conversation_path,
    create_preset_in_store=create_preset_in_store,
    default_sprite_base_path_for_slot=default_sprite_base_path_for_slot,
    delete_preset_from_store=delete_preset_from_store,
    duplicate_preset_in_store=duplicate_preset_in_store,
    evaluate_creative_workshop=evaluate_creative_workshop,
    fetch_available_models=fetch_available_models,
    fetch_embeddings=fetch_embeddings,
    generate_reply=generate_reply,
    get_active_preset=get_active_preset,
    get_active_preset_from_store=get_active_preset_from_store,
    get_active_slot_id=get_active_slot_id,
    get_conversation=get_conversation,
    get_current_card=get_current_card,
    get_memories=get_memories,
    get_persona=get_persona,
    get_preset_store=get_preset_store,
    get_role_avatar_url=get_role_avatar_url,
    get_runtime_chat_config=get_runtime_chat_config,
    get_runtime_embedding_config=get_runtime_embedding_config,
    get_settings=get_settings,
    get_slot_dir=get_slot_dir,
    get_slot_name=get_slot_name,
    get_slot_registry=get_slot_registry,
    get_user_profile=get_user_profile,
    global_persona_path=global_persona_path,
    get_workshop_stage=get_workshop_stage,
    get_workshop_stage_label=get_workshop_stage_label,
    get_workshop_state=get_workshop_state,
    get_worldbook_entries=get_worldbook_entries,
    get_worldbook_settings=get_worldbook_settings,
    get_worldbook_store=get_worldbook_store,
    list_role_card_files=list_role_card_files,
    list_sprite_assets=list_sprite_assets,
    logger=logger,
    match_worldbook_entries=match_worldbook_entries,
    normalize_role_card=normalize_role_card,
    parse_role_card_json=parse_role_card_json,
    persona_path=persona_path,
    persist_json=persist_json,
    preset_path=preset_path,
    preset_module_rules=PRESET_MODULE_RULES,
    read_json=read_json,
    read_role_card_text=read_role_card_text,
    request_minimal_model_reply=request_minimal_model_reply,
    reset_slot_data=reset_slot_data,
    reset_workshop_state=reset_workshop_state,
    retrieve_memories=retrieve_memories,
    memories_path=memories_path,
    sanitize_creative_workshop=sanitize_creative_workshop,
    sanitize_preset_store=sanitize_preset_store,
    sanitize_settings=sanitize_settings,
    sanitize_slot_id=sanitize_slot_id,
    sanitize_sprite_filename_tag=sanitize_sprite_filename_tag,
    save_image_upload_for_slot=save_image_upload_for_slot,
    save_memories=save_memories,
    save_preset_store=save_preset_store,
    save_slot_registry=save_slot_registry,
    save_user_profile=save_user_profile,
    save_workshop_asset_upload=save_workshop_asset_upload,
    save_workshop_card=save_workshop_card,
    save_workshop_state=save_workshop_state,
    save_worldbook_entries=save_worldbook_entries,
    save_worldbook_settings=save_worldbook_settings,
    save_worldbook_store=save_worldbook_store,
    settings_path=settings_path,
    slot_summary=slot_summary,
    sprite_dir_path=sprite_dir_path,
    stream_model_reply=stream_model_reply,
    user_profile_path=user_profile_path,
    workshop_state_path=workshop_state_path,
    worldbook_path=worldbook_path,
    workshop_signature=workshop_signature,
)
route_ctx.slot_runtime_service = SlotRuntimeService(route_ctx)

register_page_routes(app, templates=templates, ctx=route_ctx)
register_config_api_routes(app, ctx=route_ctx)
register_chat_api_routes(app, ctx=route_ctx)
