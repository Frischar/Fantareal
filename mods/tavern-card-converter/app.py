import base64
import io
import json
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from PIL import Image

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


def extract_tavern_card(file_bytes: bytes) -> tuple[dict, dict]:
    """Extract V2-spec JSON from a tavern PNG via the iTXt 'chara' chunk.

    Returns (tavern_data, png_meta) where png_meta includes all PNG metadata keys
    and the raw image bytes for preservation.
    """
    png_meta: dict = {"format": "", "size": (0, 0), "info_keys": [], "file_bytes": file_bytes}

    try:
        img = Image.open(io.BytesIO(file_bytes))
    except Exception as exc:
        raise ValueError(f"无法识别为有效的图片文件，请确认上传的是 PNG 格式: {exc}")

    try:
        with img:
            png_meta["format"] = img.format or "unknown"
            png_meta["size"] = (img.width, img.height)
            png_meta["info_keys"] = list(img.info.keys())

            if img.format and img.format.upper() != "PNG":
                raise ValueError(
                    f"文件格式为 {img.format}，而非 PNG。酒馆角色卡的 JSON 数据存储在 PNG 的元数据块中，"
                    "请上传 PNG 格式的角色卡"
                )

            if "chara" not in img.info:
                available = ", ".join(str(k) for k in img.info) if img.info else "（无）"
                raise ValueError(
                    f"PNG 元数据中未找到 'chara' 键。"
                    f"当前 PNG 包含的元数据键: {available}。"
                    "请确认这是一张酒馆（SillyTavern）导出的 PNG 角色卡，而非普通图片"
                )

            encoded = img.info["chara"]
            try:
                decoded = base64.b64decode(encoded)
            except Exception as exc:
                raise ValueError(
                    f"'chara' 数据的 Base64 解码失败。卡片可能使用了非标准编码或已损坏: {exc}"
                ) from exc

            json_str = decoded.decode("utf-8", errors="ignore")
            try:
                tavern_data = json.loads(json_str)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"解码后的数据不是有效的 JSON。卡片可能已损坏，或使用了加密/二次编码: {exc}"
                ) from exc

            if not isinstance(tavern_data, dict):
                raise ValueError(f"卡片 JSON 结构异常（类型为 {type(tavern_data).__name__}），应为对象")

            png_meta["other_info"] = {
                k: v for k, v in img.info.items() if k != "chara"
            }
            return tavern_data, png_meta
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"解析 PNG 时发生未知错误: {exc}") from exc


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
        "plotStages": {},
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
            depth = int(depth)
        except (TypeError, ValueError):
            depth = ENTRY_DEFAULTS["injection_depth"]

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
        position = str(entry.get("position") or "").strip()
        if not position:
            position = WORLDBOOK_SETTINGS["default_insertion_position"]
        position_map = {
            "0": "before_char_defs",
            "1": "after_char_defs",
            "2": "in_chat",
        }
        position = position_map.get(position, position)
        if position not in {"before_char_defs", "after_char_defs", "in_chat"}:
            position = "after_char_defs"

        xuqi_entry: dict = {
            **ENTRY_DEFAULTS,
            "trigger": trigger,
            "secondary_trigger": secondary_trigger,
            "content": str(entry.get("content") or "").strip(),
            "entry_type": "constant" if constant else "keyword",
            "order": order,
            "insertion_position": position,
            "injection_depth": depth,
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
            "depth→injection_depth", "probability→chance",
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
        raw = await file.read()
    except Exception:
        raise HTTPException(400, "读取上传文件失败")

    try:
        tavern_data, png_meta = extract_tavern_card(raw)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    xuqi_card, preserved = convert_card_to_xuqi(tavern_data)
    xuqi_json = json.dumps(xuqi_card, ensure_ascii=False, indent=2)

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
        "tavern_spec": tavern_data.get("spec", "unknown"),
        "tavern_spec_version": tavern_data.get("spec_version", "unknown"),
    })


@app.post("/api/convert/worldbook")
async def convert_worldbook(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(400, "未提供文件名")
    try:
        raw = await file.read()
    except Exception:
        raise HTTPException(400, "读取上传文件失败")

    try:
        tavern_wb = json.loads(raw.decode("utf-8", errors="ignore"))
    except json.JSONDecodeError as exc:
        raise HTTPException(400, f"JSON 解析失败: {exc}")

    xuqi_wb, conversion_info = convert_worldbook_to_xuqi(tavern_wb)
    xuqi_json = json.dumps(xuqi_wb, ensure_ascii=False, indent=2)

    wb_name = str(tavern_wb.get("name") or "未命名世界书").strip()
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


# ── Static files ──
_static_dir = MOD_DIR / "static"
if _static_dir.is_dir():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="tavern_converter_static")
