import base64
import io
import json
import struct
from pathlib import Path

import re

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from PIL import Image
from PIL.PngImagePlugin import PngInfo

MOD_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MOD_DIR.parent.parent

TEMPLATES = Jinja2Templates(directory=str(MOD_DIR / "templates"))

# ── Xuqi worldbook default settings (from fantareal/worldbook_logic.py) ──
WORLDBOOK_SETTINGS: dict = {
    "enabled": True,
    "debug_enabled": False,
    "max_hits": 20,
    "default_case_sensitive": False,
    "default_whole_word": False,
    "default_match_mode": "any",
    "default_secondary_mode": "all",
    "default_entry_type": "keyword",
    "default_group_operator": "and",
    "default_chance": 100,
    "default_sticky_turns": 0,
    "default_cooldown_turns": 0,
    "default_insertion_position": "after_char_defs",
    "default_injection_depth": 0,
    "default_injection_role": "system",
    "default_injection_order": 100,
    "default_prompt_layer": "follow_position",
    "recursive_scan_enabled": False,
    "recursion_max_depth": 2,
}

# ── Xuqi entry field defaults ──
ENTRY_DEFAULTS: dict = {
    "entry_type": "keyword",
    "case_sensitive": False,
    "whole_word": False,
    "match_mode": "any",
    "secondary_mode": "all",
    "group_operator": "and",
    "chance": 100,
    "sticky_turns": 0,
    "cooldown_turns": 0,
    "order": 100,
    "injection_depth": 0,
    "injection_role": "system",
    "prompt_layer": "follow_position",
    "enabled": True,
    "note": "",
}

app = FastAPI()

MAX_CARD_UPLOAD_SIZE_BYTES = 20 * 1024 * 1024
MAX_WORLDBOOK_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024
MAX_PORTRAIT_UPLOAD_SIZE_BYTES = 20 * 1024 * 1024


async def read_upload_bytes(file: UploadFile, *, max_bytes: int, label: str) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(413, f"{label}文件不能大于 {max_bytes // (1024 * 1024)} MB")
        chunks.append(chunk)
    data = b"".join(chunks)
    if not data:
        raise HTTPException(400, f"{label}不能为空")
    return data

# ── Pydantic models for save endpoints ──
class SaveCardPayload(BaseModel):
    card_json: str
    filename: str

class SaveWorldbookPayload(BaseModel):
    worldbook_json: str
    filename: str


# ═══════════════════════════════════════════════════
#  Card conversion
# ═══════════════════════════════════════════════════

def strip_chara_metadata(file_bytes: bytes) -> bytes:
    """Remove 'chara' iTXt chunk from PNG, returning clean image bytes."""
    try:
        with Image.open(io.BytesIO(file_bytes)) as img:
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
    except Exception:
        # If stripping fails, return original bytes as fallback
        return file_bytes


def _extract_chara_raw(file_bytes: bytes) -> str | None:
    """Parse PNG chunks directly to find chara data (handles both tEXt and iTXt)."""
    i = 8  # skip 8-byte PNG signature
    while i + 8 <= len(file_bytes):
        length = struct.unpack('>I', file_bytes[i:i + 4])[0]
        chunk_type = file_bytes[i + 4:i + 8].decode('latin-1', errors='replace')
        chunk_data = file_bytes[i + 8:i + 8 + length]
        i += 12 + length
        if chunk_type in ('tEXt', 'iTXt'):
            parts = chunk_data.split(b'\x00')
            if parts[0] == b'chara':
                # Last non-empty segment is the text value
                text = parts[-1]
                return base64.b64decode(text).decode('utf-8', errors='ignore')
    return None


def extract_tavern_card(file_bytes: bytes) -> tuple[dict, dict]:
    """Extract V2-spec JSON from a tavern PNG via iTXt/tEXt 'chara' chunk.

    Returns (tavern_data, png_meta) where png_meta includes PNG metadata
    and the raw image bytes.
    """
    png_meta: dict = {"format": "", "size": (0, 0), "info_keys": [], "file_bytes": file_bytes, "chunk_type": ""}

    # Validate as an image first
    try:
        img = Image.open(io.BytesIO(file_bytes))
    except Exception as exc:
        raise ValueError(f"这个文件不是有效的图片格式喵，请上传 PNG 格式的酒馆卡~")

    try:
        with img:
            png_meta["format"] = img.format or "unknown"
            png_meta["size"] = (img.width, img.height)
            png_meta["info_keys"] = list(img.info.keys()) if img.info else []

            if img.format and img.format.upper() != "PNG":
                raise ValueError(
                    f"这个文件是 {img.format} 格式而不是 PNG 喵，请上传 PNG 格式的酒馆卡~"
                )

            json_str: str | None = None

            # 1. Try Pillow (handles iTXt well)
            if "chara" in img.info:
                png_meta["chunk_type"] = "iTXt"
                try:
                    encoded = img.info["chara"]
                    decoded = base64.b64decode(encoded)
                    json_str = decoded.decode("utf-8", errors="ignore")
                except Exception:
                    pass  # Fall through to raw parsing

            # 2. Fallback: raw chunk parsing (handles tEXt and edge cases)
            if json_str is None:
                raw_json = _extract_chara_raw(file_bytes)
                if raw_json:
                    json_str = raw_json
                    png_meta["chunk_type"] = "tEXt"
                else:
                    available = ", ".join(str(k) for k in img.info) if img.info else "（无）"
                    raise ValueError(
                        f"这不是一张酒馆卡喵~ PNG 元数据中没有找到角色信息。"
                        f"当前元数据键: {available}。"
                        "请确认这是从 SillyTavern / 酒馆 导出的 PNG 角色卡，而不是普通图片~"
                    )

            try:
                tavern_data = json.loads(json_str)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    "这张卡的数据无法解析喵，可能文件已损坏或使用了加密~"
                ) from exc

            if not isinstance(tavern_data, dict):
                raise ValueError("卡片数据结构异常喵，可能不是标准的酒馆卡格式~")

            png_meta["other_info"] = {
                k: v for k, v in img.info.items() if k != "chara"
            }
            return tavern_data, png_meta
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"解析 PNG 时发生未知错误喵~ 请检查文件是否完整: {exc}") from exc


def convert_card_to_xuqi(tavern_data: dict) -> tuple[dict, list[str]]:
    """Map a V2-spec tavern card dict to Xuqi_LLM role card format.

    Returns (xuqi_card, preserved_fields) where preserved_fields lists all
    non-Xuqi fields that were merged into creator_notes for preservation.
    """
    if "data" in tavern_data and isinstance(tavern_data["data"], dict):
        src = tavern_data["data"]
    else:
        src = tavern_data

    name = str(src.get("name") or "").strip()
    description = str(src.get("description") or "").strip()
    personality = str(src.get("personality") or "").strip()
    scenario = str(src.get("scenario") or "").strip()
    creator_notes = str(src.get("creator_notes") or "").strip()

    tags = src.get("tags")
    if not isinstance(tags, list):
        tags = []

    # ── Preserve unmapped tavern fields by merging into creator_notes ──
    preserved: list[str] = []
    extra_blocks: list[str] = []

    sp = str(src.get("system_prompt") or "").strip()
    if sp:
        extra_blocks.append(f"【系统提示（来自酒馆 system_prompt）】\n{sp}")
        preserved.append("system_prompt")

    phi = str(src.get("post_history_instructions") or "").strip()
    if phi:
        extra_blocks.append(f"【对话后指令（来自酒馆 post_history_instructions）】\n{phi}")
        preserved.append("post_history_instructions")

    alt_greetings = src.get("alternate_greetings")
    if isinstance(alt_greetings, list) and alt_greetings:
        lines = ["【备选开场白（来自酒馆 alternate_greetings）】"]
        for i, g in enumerate(alt_greetings, 1):
            lines.append(f"{i}. {str(g).strip()}")
        extra_blocks.append("\n".join(lines))
        preserved.append(f"alternate_greetings ({len(alt_greetings)}条)")

    creator = str(src.get("creator") or "").strip()
    if creator:
        extra_blocks.append(f"【原作者】{creator}")
        preserved.append("creator")

    char_ver = str(src.get("character_version") or "").strip()
    if char_ver:
        extra_blocks.append(f"【版本】{char_ver}")
        preserved.append("character_version")

    avatar = str(src.get("avatar") or "").strip()
    if avatar and avatar.lower() != "none":
        extra_blocks.append(f"【原头像 URL】{avatar}")
        preserved.append("avatar")

    extensions = src.get("extensions")
    if isinstance(extensions, dict) and extensions:
        try:
            ext_json = json.dumps(extensions, ensure_ascii=False, indent=2)
            extra_blocks.append(f"【扩展数据（来自酒馆 extensions）】\n{ext_json}")
            preserved.append(f"extensions ({', '.join(extensions.keys())})")
        except (TypeError, ValueError):
            extra_blocks.append(f"【扩展数据（来自酒馆 extensions）】\n{str(extensions)}")
            preserved.append("extensions")

    if extra_blocks:
        separator = "\n\n" + "─" * 40 + "\n\n"
        merged_notes = creator_notes + separator + separator.join(extra_blocks) if creator_notes else "\n\n".join(extra_blocks)
    else:
        merged_notes = creator_notes

    xuqi_card: dict = {
        "name": name,
        "description": description,
        "personality": personality,
        "first_mes": str(src.get("first_mes") or "").strip(),
        "mes_example": str(src.get("mes_example") or "").strip(),
        "scenario": scenario,
        "creator_notes": merged_notes,
        "tags": tags,
        "personas": {
            "1": {
                "name": name,
                "description": description,
                "personality": personality,
                "scenario": scenario,
                "creator_notes": merged_notes,
            }
        },
    }
    return xuqi_card, preserved


# ═══════════════════════════════════════════════════
#  General card conversion (character_book aware)
# ═══════════════════════════════════════════════════

def _has_meaningful_card(src: dict) -> bool:
    """Check if the card has enough character content to be worth converting."""
    name = str(src.get("name") or "").strip()
    if not name:
        return False
    for field in ("description", "personality", "first_mes", "mes_example", "scenario", "creator_notes"):
        if len(str(src.get(field) or "").strip()) > 50:
            return True
    return False


def _is_non_empty_tavern_value(value) -> bool:
    """Return True when a SillyTavern extension/top-level value actually carries content."""
    if value is None:
        return False
    if value in ("", [], {}):
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True


def detect_non_character_content(src: dict) -> list[dict]:
    """Detect content that pure character conversion will not split out.

    The pure role-card endpoint intentionally returns only the Fantareal role card.
    When a PNG also contains an embedded worldbook or SillyTavern extensions,
    the frontend should suggest trying the general converter instead.
    """
    found: list[dict] = []

    character_book = src.get("character_book")
    if isinstance(character_book, dict):
        entries = character_book.get("entries")
        entry_count = len(entries) if isinstance(entries, list) else 0
        if entry_count > 0:
            found.append({
                "type": "worldbook",
                "label": "内嵌世界书",
                "detail": f"{entry_count} 条",
                "count": entry_count,
            })

    exts = src.get("extensions")
    if isinstance(exts, dict):
        ext_labels = {
            "depth_prompt": "深度提示",
            "regex_scripts": "正则脚本",
            "tavern_helper": "酒馆辅助配置",
            "xiaobaix-tasks": "小白任务配置",
            "world": "世界设定",
            "talkativeness": "话量设定",
            "fav": "收藏标记",
        }
        for key, label in ext_labels.items():
            if _is_non_empty_tavern_value(exts.get(key)):
                found.append({
                    "type": key,
                    "label": label,
                    "detail": "已检测",
                })

        # Unknown extension keys can also contain useful non-character content.
        known = set(ext_labels)
        unknown_keys = [str(k) for k, v in exts.items() if k not in known and _is_non_empty_tavern_value(v)]
        if unknown_keys:
            preview = "、".join(unknown_keys[:5])
            suffix = "等" if len(unknown_keys) > 5 else ""
            found.append({
                "type": "extensions",
                "label": "其他扩展字段",
                "detail": f"{preview}{suffix}",
            })

    return found


def convert_card_general(tavern_data: dict) -> dict:
    """General converter: auto-detects content types and returns named sections.

    Each section has: type, title, has_content, and type-specific fields
    (json, filename, entry_count, reason, content, etc.)
    """
    if "data" in tavern_data and isinstance(tavern_data["data"], dict):
        src = tavern_data["data"]
    else:
        src = tavern_data

    safe_name = str(src.get("name") or "").strip() or "未命名角色"
    sections: list[dict] = []

    # ── Section 1: Worldbook ──
    character_book = src.get("character_book")
    if isinstance(character_book, dict):
        cb_entries = character_book.get("entries")
        if isinstance(cb_entries, list) and cb_entries:
            cb_name = str(character_book.get("name") or f"{safe_name}的世界书").strip()
            cb_data = {"entries": cb_entries}
            xuqi_wb, wb_info = convert_worldbook_to_xuqi(cb_data)
            sections.append({
                "type": "worldbook",
                "title": "世界书",
                "has_content": True,
                "json": json.dumps(xuqi_wb, ensure_ascii=False, indent=2),
                "filename": f"{cb_name}的世界书.json",
                "entry_count": len(xuqi_wb["entries"]),
                "conversion_info": wb_info,
            })
    if not any(s["type"] == "worldbook" for s in sections):
        sections.append({"type": "worldbook", "title": "世界书", "has_content": False,
                         "reason": "未检测到嵌入的世界书内容"})

    # ── Section 2: Role Card ──
    if _has_meaningful_card(src):
        xuqi_card, preserved = convert_card_to_xuqi(tavern_data)
        sections.append({
            "type": "card",
            "title": "角色卡",
            "has_content": True,
            "json": json.dumps(xuqi_card, ensure_ascii=False, indent=2),
            "filename": f"{safe_name}的人设卡.json",
            "preserved_fields": preserved,
        })
    else:
        sections.append({"type": "card", "title": "角色卡", "has_content": False,
                         "reason": "未检测到角色卡信息，该卡可能仅含世界书等附加内容，建议到「纯角色卡转换」使用纯角色卡"})

    # ── Section 3+: Auto-detect extensions ──
    exts = src.get("extensions")
    if isinstance(exts, dict):
        ext_map = {
            "depth_prompt": "深度提示",
            "regex_scripts": "正则脚本",
            "tavern_helper": "酒馆辅助配置",
            "xiaobaix-tasks": "小白任务配置",
            "world": "世界设定",
            "talkativeness": "话量设定",
            "fav": "收藏标记",
        }
        for key, title in ext_map.items():
            val = exts.get(key)
            if val is not None and val != "" and val != [] and val != {}:
                if isinstance(val, (dict, list)):
                    sections.append({
                        "type": key,
                        "title": title,
                        "has_content": True,
                        "json": json.dumps(val, ensure_ascii=False, indent=2),
                    })
                elif isinstance(val, (str, int, float, bool)):
                    sections.append({
                        "type": key,
                        "title": title,
                        "has_content": True,
                        "content": str(val),
                    })

    all_empty = not any(s["has_content"] for s in sections)
    return {
        "success": True,
        "sections": sections,
        "is_pure_character": not any(s["type"] == "worldbook" and s["has_content"] for s in sections),
        "warning": "empty_card" if all_empty else None,
        "message": "这个PNG文件没有包含任何可识别的内容喵，可能不是一张酒馆卡~" if all_empty else None,
        "tavern_spec": tavern_data.get("spec", "unknown"),
        "tavern_spec_version": tavern_data.get("spec_version", "unknown"),
    }


# ═══════════════════════════════════════════════════
#  Worldbook conversion
# ═══════════════════════════════════════════════════

# Fields dropped because Xuqi has no equivalent concept
DROPPED_ENTRY_FIELDS = [
    "uid", "id", "selective", "selectiveLogic", "addMemo",
    "excludeRecursion", "displayIndex", "characterFilter",
    "extensions", "insertion_order", "secondary_keys", "useProbability",
]

DROPPED_TOP_FIELDS = [
    "description", "is_creation", "extensions",
]


def convert_worldbook_to_xuqi(tavern_wb: dict) -> tuple[dict, dict]:
    """Convert a SillyTavern worldbook dict to Xuqi_LLM worldbook format.

    Returns (xuqi_worldbook, conversion_info) with statistics about the conversion.
    """
    raw_entries = tavern_wb.get("entries")
    if isinstance(raw_entries, dict):
        entry_list = list(raw_entries.values())
    elif isinstance(raw_entries, list):
        entry_list = raw_entries
    else:
        entry_list = []

    # ── Build settings, pulling relevant top-level fields ──
    settings = dict(WORLDBOOK_SETTINGS)
    if tavern_wb.get("recursive_scanning"):
        settings["recursive_scan_enabled"] = True
    scan_depth = tavern_wb.get("scan_depth")
    if isinstance(scan_depth, (int, float)) and int(scan_depth) > 0:
        settings["recursion_max_depth"] = int(scan_depth)
    if tavern_wb.get("token_budget"):
        settings["max_hits"] = max(settings["max_hits"], int(tavern_wb["token_budget"]))

    converted: list[dict] = []
    for entry in entry_list:
        keys = entry.get("key") or entry.get("keys") or []
        if not isinstance(keys, list):
            keys = []

        trigger = str(keys[0]).strip() if keys else ""
        secondary_trigger = ", ".join(str(k).strip() for k in keys[1:]) if len(keys) > 1 else ""

        # ── Field mapping with tavern-sourced values ──
        constant = bool(entry.get("constant", False))

        # priority > insertion_order > order (short-circuit)
        if "priority" in entry:
            order = entry["priority"]
        elif "insertion_order" in entry:
            order = entry["insertion_order"]
        elif "order" in entry:
            order = entry["order"]
        else:
            order = ENTRY_DEFAULTS["order"]
        try:
            order = int(order)
        except (TypeError, ValueError):
            order = ENTRY_DEFAULTS["order"]

        # depth → injection_depth
        depth = entry.get("depth", ENTRY_DEFAULTS["injection_depth"])
        try:
            depth = max(0, min(int(depth), 999))
        except (TypeError, ValueError):
            depth = ENTRY_DEFAULTS["injection_depth"]

        raw_role = entry.get("role", ENTRY_DEFAULTS["injection_role"])
        role_key = str(raw_role).strip().lower()
        role_map = {
            "0": "system",
            "1": "user",
            "2": "assistant",
            "ai": "assistant",
            "model": "assistant",
        }
        injection_role = role_map.get(role_key, role_key)
        if injection_role not in {"system", "user", "assistant"}:
            injection_role = ENTRY_DEFAULTS["injection_role"]

        # probability → chance
        probability = entry.get("probability", ENTRY_DEFAULTS["chance"])
        try:
            probability = int(probability)
        except (TypeError, ValueError):
            probability = ENTRY_DEFAULTS["chance"]

        # disable → enabled (inverse)
        disabled = bool(entry.get("disable", False))
        enabled = not disabled

        # Build note from comment + name
        note_parts: list[str] = []
        name_val = str(entry.get("name") or "").strip()
        comment_val = str(entry.get("comment") or "").strip()
        if name_val and name_val != comment_val:
            note_parts.append(f"name: {name_val}")
        if comment_val:
            note_parts.append(comment_val)
        note = "\n".join(note_parts)

        # Map position
        position = str(entry.get("position") if "position" in entry else "").strip().lower()
        if not position:
            position = WORLDBOOK_SETTINGS["default_insertion_position"]
        position_map = {
            "0": "before_char_defs",
            "1": "after_char_defs",
            "4": "in_chat",
            "before_character": "before_char_defs",
            "before_char": "before_char_defs",
            "after_character": "after_char_defs",
            "after_char": "after_char_defs",
            "depth": "in_chat",
            "at_depth": "in_chat",
            "in-chat": "in_chat",
            "inchat": "in_chat",
            "d_system": "at_depth_system",
            "depth_system": "at_depth_system",
            "at_depth_sys": "at_depth_system",
            "d_user": "at_depth_user",
            "depth_user": "at_depth_user",
            "d_ai": "at_depth_assistant",
            "d_assistant": "at_depth_assistant",
            "depth_ai": "at_depth_assistant",
            "depth_assistant": "at_depth_assistant",
            "assistant": "at_depth_assistant",
            "ai": "at_depth_assistant",
        }
        position = position_map.get(position, position)
        if position not in {
            "before_char_defs",
            "after_char_defs",
            "in_chat",
            "at_depth_system",
            "at_depth_user",
            "at_depth_assistant",
        }:
            position = "after_char_defs"
        if position == "at_depth_system":
            injection_role = "system"
        elif position == "at_depth_user":
            injection_role = "user"
        elif position == "at_depth_assistant":
            injection_role = "assistant"

        xuqi_entry: dict = {
            **ENTRY_DEFAULTS,
            "trigger": trigger,
            "secondary_trigger": secondary_trigger,
            "content": str(entry.get("content") or "").strip(),
            "entry_type": "constant" if constant else "keyword",
            "order": order,
            "insertion_position": position,
            "injection_depth": depth,
            "injection_role": injection_role,
            "chance": probability,
            "enabled": enabled,
            "note": note,
        }
        converted.append(xuqi_entry)

    xuqi_wb: dict = {
        "settings": settings,
        "entries": converted,
    }

    # Report what was done and what was dropped
    conversion_info = {
        "input_entries": len(entry_list),
        "output_entries": len(converted),
        "fields_mapped_from_tavern": [
            "key[0]→trigger", "key[1:]→secondary_trigger", "content→content",
            "constant→entry_type", "priority/insertion_order/order→order",
            "depth→injection_depth", "role→injection_role", "probability→chance",
            "disable→enabled", "comment+name→note",
            "position→insertion_position",
        ],
        "top_fields_merged_to_settings": [
            "recursive_scanning→recursive_scan_enabled",
            "scan_depth→recursion_max_depth",
            "token_budget→max_hits",
        ],
        "fields_not_preserved_per_entry": DROPPED_ENTRY_FIELDS,
        "fields_not_preserved_top_level": DROPPED_TOP_FIELDS,
    }

    return xuqi_wb, conversion_info


# ═══════════════════════════════════════════════════
#  Reverse conversion (Fantareal → Tavern PNG)
# ═══════════════════════════════════════════════════

def normalize_fantareal_card(raw: dict) -> dict:
    """Normalize various Fantareal card shapes into a flat card dict."""
    if not isinstance(raw, dict):
        return {}

    # Unwrap known wrappers
    if "persona_card" in raw and isinstance(raw["persona_card"], dict):
        raw = raw["persona_card"]
    elif "card" in raw and isinstance(raw["card"], dict):
        raw = raw["card"]

    card = {k: v for k, v in raw.items()}

    # Normalize tags: string → list
    tags = card.get("tags")
    if isinstance(tags, str):
        card["tags"] = [t.strip() for t in re.split(r'[,，]', tags) if t.strip()]
    elif not isinstance(tags, list):
        card["tags"] = []

    # Ensure key fields are strings
    for field in ("name", "description", "personality", "scenario",
                  "first_mes", "mes_example", "creator_notes",
                  "system_prompt", "post_history_instructions",
                  "creator", "character_version"):
        card.setdefault(field, "")

    return card


def validate_tavern_generation(card: dict, has_image: bool) -> tuple[list[dict], list[dict]]:
    """Validate inputs for tavern PNG generation. Returns (errors, warnings)."""
    errors: list[dict] = []
    warnings: list[dict] = []

    if not has_image:
        errors.append({"field": "image", "message": "请上传角色立绘图片"})

    name = str(card.get("name") or "").strip()
    if not name:
        errors.append({"field": "name", "message": "请填写角色名"})

    first_mes = str(card.get("first_mes") or "").strip()
    if not first_mes:
        errors.append({"field": "first_mes", "message": "请填写开场白"})

    # Suggested but non-blocking
    if not str(card.get("description") or "").strip():
        warnings.append({"field": "description", "message": "建议填写角色描述"})
    if not str(card.get("personality") or "").strip():
        warnings.append({"field": "personality", "message": "建议填写性格/口吻"})
    if not str(card.get("scenario") or "").strip():
        warnings.append({"field": "scenario", "message": "建议填写场景"})
    if not str(card.get("mes_example") or "").strip():
        warnings.append({"field": "mes_example", "message": "缺少示例对话，不影响生成"})
    if not str(card.get("creator_notes") or "").strip():
        warnings.append({"field": "creator_notes", "message": "缺少作者备注，不影响生成"})
    tags = card.get("tags")
    if not tags or (isinstance(tags, list) and not any(tags)):
        warnings.append({"field": "tags", "message": "缺少标签，不影响生成"})

    return errors, warnings


def build_tavern_v2_card(card: dict) -> dict:
    """Build a chara_card_v2 spec dict from a normalized Fantareal card."""
    data: dict = {
        "name": str(card.get("name") or "").strip(),
        "description": str(card.get("description") or "").strip(),
        "personality": str(card.get("personality") or "").strip(),
        "scenario": str(card.get("scenario") or "").strip(),
        "first_mes": str(card.get("first_mes") or "").strip(),
        "mes_example": str(card.get("mes_example") or "").strip(),
        "creator_notes": str(card.get("creator_notes") or "").strip(),
        "tags": card.get("tags") if isinstance(card.get("tags"), list) else [],
    }

    # Optional fields
    for opt_field in ("alternate_greetings", "creator", "character_version",
                      "system_prompt", "post_history_instructions"):
        val = card.get(opt_field)
        if val is not None and val != "" and val != []:
            data[opt_field] = val

    # Preserve Fantareal-specific info in extensions
    extensions: dict = {}
    personas = card.get("personas")
    if personas and isinstance(personas, dict):
        extensions["fantareal"] = {"personas": personas}
    workshop = card.get("creativeWorkshop")
    if workshop and isinstance(workshop, dict):
        extensions.setdefault("fantareal", {})["creativeWorkshop"] = workshop
    if extensions:
        data["extensions"] = extensions

    return {
        "spec": "chara_card_v2",
        "spec_version": "2.0",
        "data": data,
    }


def render_tavern_png(image_bytes: bytes, tavern_payload: dict) -> bytes:
    """Embed tavern V2 JSON as 'chara' tEXt metadata into an image, output PNG."""
    img = Image.open(io.BytesIO(image_bytes))
    json_str = json.dumps(tavern_payload, ensure_ascii=False)
    chara_b64 = base64.b64encode(json_str.encode("utf-8")).decode("ascii")

    pnginfo = PngInfo()
    pnginfo.add_text("chara", chara_b64)

    buf = io.BytesIO()
    img.save(buf, format="PNG", pnginfo=pnginfo)
    img.close()
    return buf.getvalue()


def safe_card_filename(name: str) -> str:
    """Clean a character name into a safe PNG filename."""
    safe = re.sub(r'[\\/:*?"<>|]', "", str(name or "未命名角色").strip())
    safe = safe.strip() or "未命名角色"
    return f"{safe}_tavern.png"


def convert_xuqi_wb_to_tavern(xuqi_wb: dict) -> tuple[dict, dict]:
    """Convert a Fantareal worldbook dict to SillyTavern worldbook format.

    Returns (tavern_wb, conversion_info).
    """
    raw_entries = xuqi_wb.get("entries", [])
    if isinstance(raw_entries, dict):
        entry_list = list(raw_entries.values())
    elif isinstance(raw_entries, list):
        entry_list = raw_entries
    else:
        entry_list = []

    settings = xuqi_wb.get("settings", {})

    position_map = {
        "before_char_defs": "0",
        "after_char_defs": "1",
        "in_chat": "2",
    }

    converted: list[dict] = []
    for idx, entry in enumerate(entry_list):
        if not isinstance(entry, dict):
            continue

        # keys array from trigger + secondary_trigger
        keys: list[str] = []
        trigger = str(entry.get("trigger") or "").strip()
        if trigger:
            keys.append(trigger)
        secondary = str(entry.get("secondary_trigger") or "").strip()
        if secondary:
            keys.extend([k.strip() for k in secondary.split(",") if k.strip()])

        entry_type = str(entry.get("entry_type") or "").strip()
        constant = entry_type == "constant"

        order = entry.get("order")
        try:
            priority = int(order) if order is not None else 100
        except (TypeError, ValueError):
            priority = 100

        depth = entry.get("injection_depth")
        try:
            depth = int(depth) if depth is not None else 0
        except (TypeError, ValueError):
            depth = 0

        chance = entry.get("chance")
        try:
            probability = int(chance) if chance is not None else 100
        except (TypeError, ValueError):
            probability = 100

        enabled = entry.get("enabled")
        disable = False if enabled is None else not bool(enabled)

        position = position_map.get(
            str(entry.get("insertion_position") or "").strip(), "1"
        )

        name_val = str(entry.get("title") or "").strip()
        comment_val = str(entry.get("comment") or entry.get("note") or "").strip()

        tavern_entry: dict = {
            "uid": idx,
            "key": keys,
            "keysecondary": [],
            "comment": comment_val,
            "content": str(entry.get("content") or "").strip(),
            "constant": constant,
            "selective": False,
            "selectiveLogic": 0,
            "addMemo": True,
            "order": priority,
            "position": position,
            "disable": disable,
            "excludeRecursion": False,
            "preventRecursion": False,
            "delayUntilRecursion": False,
            "probability": probability,
            "useProbability": probability < 100,
            "depth": depth,
            "group": "",
            "groupOverride": False,
            "groupWeight": 100,
            "scanDepth": None,
            "caseSensitive": None,
            "matchWholeWords": None,
            "useGroupScoring": None,
            "automationId": "",
            "role": None,
            "sticky": None,
            "cooldown": None,
            "delayUntil": None,
            "displayIndex": idx,
            "name": name_val,
            "extensions": {},
        }
        converted.append(tavern_entry)

    tavern_wb: dict = {"entries": converted}
    if settings.get("recursive_scan_enabled"):
        tavern_wb["recursive_scanning"] = True
    recursion_max = settings.get("recursion_max_depth")
    if isinstance(recursion_max, (int, float)) and int(recursion_max) > 0:
        tavern_wb["scan_depth"] = int(recursion_max)

    conversion_info = {
        "input_entries": len(entry_list),
        "output_entries": len(converted),
        "fields_mapped": [
            "trigger→keys[0]", "secondary_trigger→keys[1:]",
            "entry_type→constant", "enabled→disable(反转)",
            "order→priority", "injection_depth→depth",
            "chance→probability", "insertion_position→position",
            "comment/note→comment", "title→name",
        ],
        "tavern_defaults_added": [
            "uid", "selective", "selectiveLogic", "addMemo",
            "displayIndex", "useProbability", "extensions",
        ],
        "fields_not_preserved": [
            "match_mode", "secondary_mode", "group_operator",
            "sticky_turns", "cooldown_turns", "injection_order",
            "injection_role", "prompt_layer", "recursive_enabled",
        ],
    }

    return tavern_wb, conversion_info


# ═══════════════════════════════════════════════════
#  Routes
# ═══════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def page(request: Request):
    return TEMPLATES.TemplateResponse("index.html", {"request": request})


@app.post("/api/convert/card")
async def convert_card(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(400, "未提供文件名")
    try:
        raw = await read_upload_bytes(file, max_bytes=MAX_CARD_UPLOAD_SIZE_BYTES, label="角色卡")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "读取上传文件失败")

    try:
        tavern_data, png_meta = extract_tavern_card(raw)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    # Check if card has meaningful character content
    src = tavern_data.get("data", tavern_data)
    if not _has_meaningful_card(src):
        has_wb = bool(src.get("character_book", {}).get("entries"))
        if has_wb:
            mixed_content = detect_non_character_content(src)
            return JSONResponse({
                "success": True,
                "warning": "worldbook_only",
                "message": "没找到角色信息喵，但是检测到世界书信息，推荐去「角色卡通用转换」使用这个文件喵~",
                "has_non_character_content": True,
                "non_character_content": mixed_content,
                "recommend_general_conversion": True,
            })
        else:
            raise HTTPException(400,
                "这不是一个包含信息的有效PNG文件喵，可能是没有原图保存或者只是一张单纯的PNG图片喵~")

    xuqi_card, preserved = convert_card_to_xuqi(tavern_data)
    xuqi_json = json.dumps(xuqi_card, ensure_ascii=False, indent=2)
    mixed_content = detect_non_character_content(src)

    # Preview
    png_b64 = base64.b64encode(raw).decode("ascii")

    # Clean PNG (stripped of chara metadata)
    clean_png = strip_chara_metadata(raw)
    clean_png_b64 = base64.b64encode(clean_png).decode("ascii")

    safe_name = xuqi_card["name"] or "未命名角色"

    return JSONResponse({
        "success": True,
        "card": xuqi_card,
        "card_json": xuqi_json,
        "filename": f"{safe_name}的人设卡.json",
        "preview_png": f"data:image/png;base64,{png_b64}",
        "clean_png_base64": clean_png_b64,
        "clean_png_filename": f"{safe_name}（纯图片）.png",
        "png_info": {
            "format": png_meta["format"],
            "width": png_meta["size"][0],
            "height": png_meta["size"][1],
            "meta_keys": png_meta["info_keys"],
        },
        "preserved_fields": preserved,
        "has_non_character_content": bool(mixed_content),
        "non_character_content": mixed_content,
        "recommend_general_conversion": bool(mixed_content),
        "tavern_spec": tavern_data.get("spec", "unknown"),
        "tavern_spec_version": tavern_data.get("spec_version", "unknown"),
    })


@app.post("/api/convert/card/general")
async def convert_card_general_endpoint(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(400, "未提供文件名")
    try:
        raw = await read_upload_bytes(file, max_bytes=MAX_CARD_UPLOAD_SIZE_BYTES, label="角色卡")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "读取上传文件失败")

    try:
        tavern_data, png_meta = extract_tavern_card(raw)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    result = convert_card_general(tavern_data)

    png_b64 = base64.b64encode(raw).decode("ascii")
    clean_png = strip_chara_metadata(raw)
    clean_png_b64 = base64.b64encode(clean_png).decode("ascii")

    # Find card section name for image filename
    safe_name = "未命名角色"
    for s in result["sections"]:
        if s["type"] == "card" and s["has_content"]:
            card_data = json.loads(s["json"])
            safe_name = card_data.get("name", "") or safe_name
            break

    result["preview_png"] = f"data:image/png;base64,{png_b64}"
    result["clean_png_base64"] = clean_png_b64
    result["clean_png_filename"] = f"{safe_name}（纯图片）.png"
    result["png_info"] = {
        "format": png_meta["format"],
        "width": png_meta["size"][0],
        "height": png_meta["size"][1],
        "meta_keys": png_meta["info_keys"],
        "chunk_type": png_meta.get("chunk_type", ""),
    }

    return JSONResponse(result)


@app.post("/api/convert/worldbook")
async def convert_worldbook(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(400, "未提供文件名")
    try:
        raw = await read_upload_bytes(file, max_bytes=MAX_WORLDBOOK_UPLOAD_SIZE_BYTES, label="世界书")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "读取上传文件失败")

    try:
        tavern_wb = json.loads(raw.decode("utf-8", errors="ignore"))
    except json.JSONDecodeError as exc:
        raise HTTPException(400, f"JSON 解析失败: {exc}")

    xuqi_wb, conversion_info = convert_worldbook_to_xuqi(tavern_wb)
    xuqi_json = json.dumps(xuqi_wb, ensure_ascii=False, indent=2)

    wb_name = str(tavern_wb.get("name") or "未命名世界书").strip()
    if len(xuqi_wb["entries"]) == 0:
        return JSONResponse({
            "success": True,
            "warning": "empty_worldbook",
            "message": "这个世界书JSON没有任何条目喵，建议检查文件来源~",
            "worldbook": xuqi_wb,
            "worldbook_json": xuqi_json,
            "entry_count": 0,
            "filename": f"{wb_name}的世界书.json",
            "conversion_info": conversion_info,
        })

    return JSONResponse({
        "success": True,
        "worldbook": xuqi_wb,
        "worldbook_json": xuqi_json,
        "entry_count": len(xuqi_wb["entries"]),
        "filename": f"{wb_name}的世界书.json",
        "conversion_info": conversion_info,
    })


# ── Save endpoints ──

@app.post("/api/save/card")
async def save_card(payload: SaveCardPayload):
    target_dir = PROJECT_ROOT / "assets" / "人设卡"
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise HTTPException(500, f"无法创建目录 {target_dir}: {exc}")

    safe_filename = Path(payload.filename).name  # strip any path components
    target_path = target_dir / safe_filename
    try:
        # Validate JSON is parseable before saving
        json.loads(payload.card_json)
        target_path.write_text(payload.card_json, encoding="utf-8")
        return JSONResponse({
            "success": True,
            "saved_path": str(target_path),
            "filename": safe_filename,
        })
    except json.JSONDecodeError as exc:
        raise HTTPException(400, f"JSON 格式无效: {exc}")
    except OSError as exc:
        raise HTTPException(500, f"写入文件失败: {exc}")


@app.post("/api/save/worldbook")
async def save_worldbook(payload: SaveWorldbookPayload):
    target_dir = PROJECT_ROOT / "assets" / "世界书"
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise HTTPException(500, f"无法创建目录 {target_dir}: {exc}")

    safe_filename = Path(payload.filename).name
    target_path = target_dir / safe_filename
    try:
        json.loads(payload.worldbook_json)
        target_path.write_text(payload.worldbook_json, encoding="utf-8")
        return JSONResponse({
            "success": True,
            "saved_path": str(target_path),
            "filename": safe_filename,
        })
    except json.JSONDecodeError as exc:
        raise HTTPException(400, f"JSON 格式无效: {exc}")
    except OSError as exc:
        raise HTTPException(500, f"写入文件失败: {exc}")


# ── Reverse conversion: Fantareal → Tavern PNG ──

@app.post("/api/convert/fantareal-to-tavern")
async def fantareal_to_tavern(
    image: UploadFile = File(...),
    card_json: str = Form(""),
    manual_fields: str = Form(""),
):
    if not image.filename:
        raise HTTPException(400, "未提供立绘文件")

    try:
        image_bytes = await read_upload_bytes(image, max_bytes=MAX_PORTRAIT_UPLOAD_SIZE_BYTES, label="立绘图片")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "读取立绘文件失败")

    # Validate image
    try:
        test_img = Image.open(io.BytesIO(image_bytes))
        test_img.verify()
        test_img.close()
    except Exception:
        raise HTTPException(400, "立绘文件不是有效的图片，请上传 PNG/JPEG/WebP 格式")

    # Build card from inputs
    card: dict = {}

    # Parse card_json if provided
    if card_json and card_json.strip():
        parsed = None
        try:
            parsed = json.loads(card_json)
        except json.JSONDecodeError:
            raise HTTPException(400, "card_json 不是有效的 JSON")
        if isinstance(parsed, dict):
            card = normalize_fantareal_card(parsed)

    # Parse manual_fields if provided, merge (manual overrides json)
    if manual_fields and manual_fields.strip():
        manual = None
        try:
            manual = json.loads(manual_fields)
        except json.JSONDecodeError:
            raise HTTPException(400, "manual_fields 不是有效的 JSON")
        if isinstance(manual, dict):
            for k, v in manual.items():
                if v is not None and str(v).strip():
                    card[k] = v

    # Validate
    errors, warnings = validate_tavern_generation(card, has_image=True)
    if errors:
        return JSONResponse(
            status_code=422,
            content={"success": False, "errors": errors, "warnings": warnings},
        )

    # Build and render
    tavern_card = build_tavern_v2_card(card)
    png_bytes = render_tavern_png(image_bytes, tavern_card)
    filename = safe_card_filename(card.get("name", ""))
    png_b64 = base64.b64encode(png_bytes).decode("ascii")

    return JSONResponse({
        "success": True,
        "filename": filename,
        "png_base64": png_b64,
        "tavern_json": json.dumps(tavern_card, ensure_ascii=False, indent=2),
        "card": tavern_card,
        "warnings": warnings,
    })


# ── Reverse worldbook conversion: Fantareal → Tavern worldbook ──

@app.post("/api/convert/worldbook-to-tavern")
async def worldbook_to_tavern(file: UploadFile = File(default=None)):
    # Accept either multipart file upload or JSON body
    raw_json = ""
    if file and file.filename:
        try:
            data = await read_upload_bytes(file, max_bytes=MAX_WORLDBOOK_UPLOAD_SIZE_BYTES, label="世界书")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(400, "读取上传文件失败")
        raw_json = data.decode("utf-8", errors="ignore")
    else:
        raise HTTPException(400, "请上传 Fantareal 世界书 JSON 文件")

    try:
        xuqi_wb = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(400, f"JSON 解析失败: {exc}")

    tavern_wb, conversion_info = convert_xuqi_wb_to_tavern(xuqi_wb)
    tavern_json = json.dumps(tavern_wb, ensure_ascii=False, indent=2)

    entry_count = len(tavern_wb.get("entries", []))
    wb_name = str(xuqi_wb.get("name") or "未命名世界书").strip()

    return JSONResponse({
        "success": True,
        "tavern_wb": tavern_wb,
        "tavern_json": tavern_json,
        "entry_count": entry_count,
        "filename": f"{wb_name}_tavern_worldbook.json",
        "conversion_info": conversion_info,
    })


# ── Card Writer import endpoints ──

_CARD_WRITER_DATA_DIR = PROJECT_ROOT / "data" / "card_writer"
_CARD_WRITER_PROJECTS_DIR = _CARD_WRITER_DATA_DIR / "projects"
_CARD_WRITER_WORKSPACE = _CARD_WRITER_DATA_DIR / "workspace.cardwork.json"


def _read_cardwork_file(path: Path) -> dict | None:
    """Read a .cardwork.json file, returning the parsed dict or None."""
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


@app.get("/api/card-writer/imports")
async def list_card_writer_imports():
    sources: list[dict] = []

    # Workspace
    ws = _read_cardwork_file(_CARD_WRITER_WORKSPACE)
    if ws and isinstance(ws, dict):
        pc = ws.get("persona_card", {})
        sources.append({
            "id": "workspace",
            "type": "workspace",
            "filename": "workspace.cardwork.json",
            "title": ws.get("title") or "当前工作区",
            "character_name": pc.get("name", "") if isinstance(pc, dict) else "",
            "updated_at": ws.get("updated_at", ""),
        })

    # Projects
    if _CARD_WRITER_PROJECTS_DIR.is_dir():
        for f in sorted(_CARD_WRITER_PROJECTS_DIR.glob("*.cardwork.json")):
            proj = _read_cardwork_file(f)
            if not proj or not isinstance(proj, dict):
                continue
            pc = proj.get("persona_card", {})
            sources.append({
                "id": f.stem,
                "type": "project",
                "filename": f.name,
                "title": proj.get("title") or f.stem,
                "character_name": pc.get("name", "") if isinstance(pc, dict) else "",
                "updated_at": proj.get("updated_at", ""),
            })

    return JSONResponse({"success": True, "sources": sources})


@app.get("/api/card-writer/imports/{source_id}")
async def get_card_writer_import(source_id: str):
    if source_id == "workspace":
        path = _CARD_WRITER_WORKSPACE
    else:
        path = _CARD_WRITER_PROJECTS_DIR / f"{source_id}.cardwork.json"

    proj = _read_cardwork_file(path)
    if not proj:
        raise HTTPException(404, f"未找到缃笺项目: {source_id}")

    pc = proj.get("persona_card")
    if not isinstance(pc, dict):
        raise HTTPException(400, "该项目没有 persona_card 数据")

    card = normalize_fantareal_card(pc)
    # Also attach personas and creativeWorkshop if present
    if "personas" in proj.get("persona_card", {}):
        card["personas"] = proj["persona_card"]["personas"]
    cw = proj.get("persona_card", {}).get("creativeWorkshop")
    if cw:
        card["creativeWorkshop"] = cw

    return JSONResponse({
        "success": True,
        "card": card,
        "title": proj.get("title", ""),
    })


# ── Static files ──
_static_dir = MOD_DIR / "static"
if _static_dir.is_dir():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="tavern_converter_static")
