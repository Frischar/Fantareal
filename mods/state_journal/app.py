from __future__ import annotations

import hashlib
import json
import re
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


VERSION = "1.0.0-stable"


def get_resource_dir() -> Path:
    bundle_dir = getattr(sys, "_MEIPASS", "")
    if bundle_dir:
        return Path(bundle_dir)
    return Path(__file__).resolve().parent


APP_DIR = Path(__file__).resolve().parent
RESOURCE_DIR = get_resource_dir()
PROJECT_ROOT = APP_DIR.parent.parent if APP_DIR.parent.name.lower() == "mods" else APP_DIR.parent
DATA_DIR = PROJECT_ROOT / "data" / "mods" / "state_journal"
DB_PATH = DATA_DIR / "state_journal.db"
LEGACY_DATA_DIR = PROJECT_ROOT / "data" / "xinjian"
LEGACY_DB_PATH = LEGACY_DATA_DIR / "xinjian.db"
EXPORTS_DIR = DATA_DIR / "exports"
BACKUPS_DIR = DATA_DIR / "backups"
LOGS_DIR = DATA_DIR / "logs"
LATEST_LOG_PATH = LOGS_DIR / "latest_worker.json"
STATIC_DIR = RESOURCE_DIR / "static"
TEMPLATES_DIR = RESOURCE_DIR / "templates"
BUILTIN_TEMPLATES_DIR = RESOURCE_DIR / "templates_builtin"



DEFAULT_MUJIAN_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "standard_metrics",
        "name": "标准状态模板",
        "description": "推荐标准模板：完整角色状态字段 + 好感、信任、戒备、心绪四组通用数值；普通外观显示为 65/100（+2），状态面板 Pro 可渲染为进度条。",
        "note_style": "sensory",
        "fields": [
            {"key": "emotion", "label": "情绪", "instruction": "联系上下文，概括角色当下主要情绪，避免脱离正文凭空夸张。"},
            {"key": "clothing", "label": "衣着", "instruction": "根据场景、上下文、时间和人物性格描写衣着状态与外观变化。"},
            {"key": "posture", "label": "角色神态", "instruction": "角色当前姿势、表情、肢体位置、重心与动作趋势。"},
            {"key": "scene", "label": "场景", "instruction": "读取上下文，概括角色所在具体场景、距离关系与当前处境。"},
            {"key": "sensory_field", "label": "感官场域", "instruction": "当前环境光影、气味、声音、温度与角色存在感的共振。"},
            {"key": "body_temperature", "label": "驱体温差", "instruction": "当前体表触感、衣物质感、体温差异、湿冷或暖意；没有明确依据时保持含蓄。"},
            {"key": "body_motion", "label": "肢体动态", "instruction": "动作惯性、重心受力、手足位置、肩颈腰背等细微动态。"},
            {"key": "micro_reaction", "label": "微生理反应", "instruction": "呼吸节奏、眼睫、瞳孔、细微震颤、吞咽、喉音等微反应。"},
            {"key": "visual_focus", "label": "视线焦点", "instruction": "视线落点、注意力偏移、眼底映像与微表情。"},
            {"key": "interaction", "label": "角色互动", "instruction": "概括语气、潜台词、姿势博弈、亲近/信任/戒备等关系变化。"},
            {"key": "favor_level", "label": "好感", "instruction": "输出角色对用户或主要互动对象的好感当前值与本轮变化；格式必须为 65/100（+2）。当前值为0-100整数；本轮变化通常为-5到+5；无明显变化写 +0。不要写解释句。"},
            {"key": "trust_level", "label": "信任", "instruction": "输出信任当前值与本轮变化；格式必须为 72/100（+1）。当前值为0-100整数；本轮变化通常为-5到+5；无明显变化写 +0。不要写解释句。"},
            {"key": "guard_level", "label": "戒备", "instruction": "输出戒备/防备当前值与本轮变化，数值越高代表越戒备；格式必须为 18/100（-1）。当前值为0-100整数；本轮变化通常为-5到+5；无明显变化写 +0。不要写解释句。"},
            {"key": "pulse_level", "label": "心绪", "instruction": "输出心绪波动当前值与本轮变化，数值越高代表情绪起伏越明显；格式必须为 48/100（-3）。当前值为0-100整数；本轮变化通常为-10到+10；无明显变化写 +0。不要写解释句。"},
            {"key": "summary", "label": "摘要", "instruction": "一句话总结该角色本轮状态，兼顾情绪、身体状态与关系变化。"},
        ],
        "output_template": "<情绪({emotion})>\n<衣着({clothing})>\n<角色神态({posture})>\n<场景({scene})>\n<感官场域({sensory_field})>\n<驱体温差({body_temperature})>\n<肢体动态({body_motion})>\n<微生理反应({micro_reaction})>\n<视线焦点({visual_focus})>\n<角色互动({interaction})>\n<好感({favor_level})>\n<信任({trust_level})>\n<戒备({guard_level})>\n<心绪({pulse_level})>\n<摘要({summary})>",
    },
    {
        "id": "classic",
        "name": "简洁状态",
        "description": "清晰的角色状态卡，适合常规游玩。",
        "note_style": "classic",
        "fields": [
            {"key": "emotion", "label": "情绪", "instruction": "联系上下文，概括角色当下主要情绪。"},
            {"key": "clothing", "label": "衣着", "instruction": "根据正文和场景概括衣着与外观变化。"},
            {"key": "posture", "label": "角色神态", "instruction": "描写姿势、表情、肢体位置和重心。"},
            {"key": "scene", "label": "场景", "instruction": "概括角色当前所在场景与距离关系。"},
            {"key": "interaction", "label": "角色互动", "instruction": "概括语气、潜台词、信任或关系变化。"},
            {"key": "summary", "label": "摘要", "instruction": "一句话总结该角色本轮状态。"},
        ],
        "output_template": "【{name}】\n情绪：{emotion}\n衣着：{clothing}\n神态：{posture}\n互动：{interaction}\n摘要：{summary}",
    },
    {
        "id": "gufeng",
        "name": "古风状态",
        "description": "字段仍完整，但表达更像古风旁白，适合章节感叙事。",
        "note_style": "gufeng",
        "fields": [
            {"key": "emotion", "label": "情绪", "instruction": "以含蓄、克制的古风旁白描述角色心绪。"},
            {"key": "clothing", "label": "衣着", "instruction": "以古风语感描写衣着、袖口、发丝、衣料等细节。"},
            {"key": "posture", "label": "角色神态", "instruction": "描写身姿、眼神、手势和细微动作。"},
            {"key": "sensory_field", "label": "感官场域", "instruction": "描写光影、气息、声响与场景意象。"},
            {"key": "interaction", "label": "角色互动", "instruction": "写出语气、潜台词与未出口的关系张力。"},
            {"key": "summary", "label": "摘要", "instruction": "用一句带意象的短句收束角色状态。"},
        ],
        "output_template": "【{name}】\n情绪：{emotion}\n衣着：{clothing}\n神态：{posture}\n场域：{sensory_field}\n互动：{interaction}",
    },
    {
        "id": "sensory",
        "name": "感官标签",
        "description": "标签式状态描写，强调情绪、衣着、姿态、感官场域、互动潜台词。",
        "note_style": "sensory",
        "fields": [
            {"key": "emotion", "label": "情绪", "instruction": "联系上下文，要贴合角色现在情绪及角色特点。"},
            {"key": "clothing", "label": "衣着", "instruction": "根据场景、上下文、时间和人物性格描写衣着状态。"},
            {"key": "posture", "label": "角色神态", "instruction": "角色当前姿势、表情、肢体位置与重心。"},
            {"key": "scene", "label": "场景", "instruction": "读取上下文，概括角色所在具体场景与距离关系。"},
            {"key": "sensory_field", "label": "感官场域", "instruction": "当前环境光影、气味、声音、温度与角色存在感的共振。"},
            {"key": "body_temperature", "label": "躯体温差", "instruction": "当前体表触感、衣物质感、体温差异、湿冷或暖意。"},
            {"key": "body_motion", "label": "肢体动态", "instruction": "动作惯性、重心受力、压迫点、重量感。"},
            {"key": "micro_reaction", "label": "微生理反应", "instruction": "呼吸节奏、眼睫、瞳孔、细微震颤、喉音等。"},
            {"key": "visual_focus", "label": "视觉焦点", "instruction": "视线落点、眼底映像、微表情、注意力偏移。"},
            {"key": "interaction", "label": "角色互动", "instruction": "语气、潜台词、姿势博弈、亲近/信任变化。"},
        ],
        "output_template": "<情绪({emotion})>\n<衣着({clothing})>\n<角色神态({posture})>\n<场景({scene})>\n<感官场域({sensory_field})>\n<躯体温差({body_temperature})>\n<肢体动态({body_motion})>\n<微生理反应({micro_reaction})>\n<视觉焦点({visual_focus})>\n<角色互动({interaction})>",
    },
]



DEFAULT_MUJIAN_THEME_PACKS: list[dict[str, Any]] = [
    {
        "id": "standard",
        "name": "标准样式",
        "version": "1.0.0",
        "author": "Fantareal",
        "description": "心笺默认卡片样式：清晰、通用、适合大多数角色状态展示。",
        "style": {
            "class_name": "theme-standard",
            "accent": "#c98263",
            "layout": {
                "title_card": "standard",
                "scene_card": "chips",
                "character_card": "field_blocks",
                "relationship_card": "standard",
                "status_bar": "compact",
            },
            "title_card": {"background": "standard", "border": "soft", "radius": "large", "shadow": "soft"},
            "character_card": {"background": "standard", "field_style": "tag_block", "spacing": "standard"},
            "relationship_card": {"style": "standard"},
        },
    },
    {
        "id": "gufeng_paper",
        "name": "古风笺纸",
        "version": "1.1.0",
        "author": "Fantareal",
        "description": "宣纸底、淡墨边、朱砂点题，适合古风、武侠、仙侠和明末叙事。",
        "style": {
            "class_name": "theme-gufeng-paper",
            "accent": "#9f5f41",
            "layout": {
                "title_card": "gufeng_chapter",
                "scene_card": "paper_chips",
                "character_card": "paper_fields",
                "relationship_card": "side_note",
                "status_bar": "seal",
            },
            "tokens": {"emotion": "情", "clothing": "衣", "posture": "形", "scene": "景", "sensory_field": "境", "body_temperature": "温", "body_motion": "动", "micro_reaction": "息", "visual_focus": "眸", "interaction": "合", "summary": "记"},
            "title_card": {"background": "paper", "border": "ink", "radius": "soft", "shadow": "paper"},
            "character_card": {"background": "soft_paper", "field_style": "paper_tag", "spacing": "comfortable"},
            "relationship_card": {"style": "side_note"},
        },
    },
    {
        "id": "time_card",
        "name": "现代 Time Card",
        "version": "1.0.1",
        "author": "Fantareal",
        "description": "白卡、图标、时间场景信息块，适合现代信息卡式展示与高信息密度测试。",
        "style": {
            "class_name": "theme-time-card",
            "accent": "#1f6feb",
            "layout": {
                "layout_type": "time_card",
                "title_card": "time_card",
                "scene_card": "time_panel",
                "character_card": "info_rows",
                "relationship_card": "status_strip",
                "status_bar": "pill",
            },
            "tokens": {"time": "📅", "location": "🧭", "weather": "🌦️", "atmosphere": "📝", "characters": "👥", "emotion": "💗", "clothing": "👘", "posture": "🧍", "scene": "🌄", "sensory_field": "🌫️", "body_temperature": "🌡️", "body_motion": "〰️", "micro_reaction": "💫", "visual_focus": "👁️", "interaction": "🤝", "summary": "📌"},
            "title_card": {"background": "white", "border": "line", "radius": "large", "shadow": "paper"},
            "character_card": {"background": "white", "field_style": "icon_row", "spacing": "compact"},
            "relationship_card": {"style": "status_strip"},
        },
    },
    {"id": "moon_white_letter", "name": "月白冷笺", "version": "1.0.0", "author": "Fantareal", "description": "月白、冷灰、留白与细线，适合清冷女主、病弱感和含蓄情绪。", "style": {"class_name": "theme-moon-white", "accent": "#7e9bb8", "layout": {"title_card": "gufeng_chapter", "scene_card": "paper_chips", "character_card": "paper_fields", "relationship_card": "side_note", "status_bar": "seal"}, "tokens": {"emotion": "月", "clothing": "衣", "posture": "影", "scene": "境", "sensory_field": "息", "body_temperature": "温", "body_motion": "动", "micro_reaction": "微", "visual_focus": "眸", "interaction": "缘", "summary": "记"}, "title_card": {"background": "moon_paper", "border": "thin", "radius": "soft", "shadow": "mist"}, "character_card": {"background": "moon_paper", "field_style": "thin_note", "spacing": "comfortable"}, "relationship_card": {"style": "side_note"}}},
    {"id": "cinnabar_dossier", "name": "朱砂密卷", "version": "1.0.0", "author": "Fantareal", "description": "朱砂、黑墨、卷宗和批注感，适合权谋、杀伐、旧债和档案叙事。", "style": {"class_name": "theme-cinnabar-dossier", "accent": "#b8322a", "layout": {"title_card": "dossier", "scene_card": "paper_chips", "character_card": "field_blocks", "relationship_card": "side_note", "status_bar": "seal"}, "tokens": {"emotion": "情录", "clothing": "形录", "posture": "势录", "scene": "地录", "sensory_field": "境录", "body_temperature": "温录", "body_motion": "动录", "micro_reaction": "息录", "visual_focus": "目录", "interaction": "关系", "summary": "案结"}, "title_card": {"background": "dossier", "border": "ink", "radius": "small", "shadow": "paper"}, "character_card": {"background": "dossier", "field_style": "case_row", "spacing": "standard"}, "relationship_card": {"style": "case_note"}}},
    {"id": "jade_slip", "name": "玉简灵纹", "version": "1.0.0", "author": "Fantareal", "description": "玉色、灵纹、玄门与炁息光边，适合仙侠、修真、功法与世界观设定展示。", "style": {"class_name": "theme-jade-slip", "accent": "#47a985", "layout": {"title_card": "gufeng_chapter", "scene_card": "chips", "character_card": "field_blocks", "relationship_card": "side_note", "status_bar": "pill"}, "tokens": {"time": "时", "location": "界", "weather": "象", "atmosphere": "炁", "characters": "众", "emotion": "心息", "clothing": "形衣", "posture": "身法", "scene": "场域", "sensory_field": "灵场", "body_temperature": "温炁", "body_motion": "动势", "micro_reaction": "微息", "visual_focus": "灵眸", "interaction": "缘法", "summary": "简记"}, "title_card": {"background": "jade", "border": "glow", "radius": "large", "shadow": "glow"}, "character_card": {"background": "jade", "field_style": "glyph_block", "spacing": "comfortable"}, "relationship_card": {"style": "aura_note"}}},
    {"id": "midnight_archive", "name": "暗夜档案", "version": "1.0.0", "author": "Fantareal", "description": "暗色终端、档案编号、警告条与冷光边框，适合悬疑、末世、克系和暗色剧情。", "style": {"class_name": "theme-midnight-archive", "accent": "#62d6ff", "layout": {"title_card": "time_card", "scene_card": "time_panel", "character_card": "info_rows", "relationship_card": "status_strip", "status_bar": "pill"}, "tokens": {"time": "TIME", "location": "LOC", "weather": "ENV", "atmosphere": "MOOD", "characters": "SUBJ", "emotion": "PSY", "clothing": "GEAR", "posture": "POSE", "scene": "AREA", "sensory_field": "SENS", "body_temperature": "TEMP", "body_motion": "MOVE", "micro_reaction": "BIO", "visual_focus": "FOCUS", "interaction": "LINK", "summary": "NOTE"}, "title_card": {"background": "terminal", "border": "neon", "radius": "medium", "shadow": "neon"}, "character_card": {"background": "terminal", "field_style": "archive_row", "spacing": "compact"}, "relationship_card": {"style": "warning_strip"}}},
    {"id": "storyboard_frame", "name": "剧本分镜", "version": "1.0.1", "author": "Fantareal", "description": "镜头、场记、分镜格与动作记录，适合演出感、动画感和剧情截图式展示。", "style": {"class_name": "theme-storyboard", "accent": "#f59e0b", "layout": {"layout_type": "storyboard", "title_card": "storyboard", "scene_card": "storyboard", "character_card": "storyboard", "relationship_card": "status_strip", "status_bar": "compact"}, "tokens": {"time": "🎬", "location": "📍", "weather": "🌫", "atmosphere": "🎞", "characters": "👥", "emotion": "表情", "clothing": "服装", "posture": "动作", "scene": "镜头", "sensory_field": "音画", "body_temperature": "体感", "body_motion": "运动", "micro_reaction": "细节", "visual_focus": "焦点", "interaction": "调度", "summary": "镜头记"}, "title_card": {"background": "storyboard", "border": "frame", "radius": "small", "shadow": "soft"}, "character_card": {"background": "storyboard", "field_style": "shot_row", "spacing": "compact"}, "relationship_card": {"style": "cut_note"}}},
    {"id": "status_panel_pro", "name": "状态面板 Pro", "version": "1.0.1", "author": "Fantareal", "description": "深色半透明游戏 UI、状态条、字段编号和高亮标签，适合 RPG、战斗、属性与状态栏联动预备。", "style": {"class_name": "theme-status-pro", "accent": "#7c3aed", "layout": {"layout_type": "status_panel_pro", "title_card": "status_panel", "scene_card": "status_panel", "character_card": "status_panel_pro", "relationship_card": "status_strip", "status_bar": "pill"}, "tokens": {"time": "T", "location": "POS", "weather": "ENV", "atmosphere": "MODE", "characters": "UNIT", "emotion": "MIND", "clothing": "EQUIP", "posture": "POSE", "scene": "AREA", "sensory_field": "SENS", "body_temperature": "TEMP", "body_motion": "ACT", "micro_reaction": "BIO", "visual_focus": "LOCK", "interaction": "LINK", "summary": "SUM"}, "title_card": {"background": "hud", "border": "glow", "radius": "medium", "shadow": "hud"}, "character_card": {"background": "hud", "field_style": "stat_row", "spacing": "compact"}, "relationship_card": {"style": "status_strip"}}},
]

DEFAULT_CONFIG: dict[str, Any] = {
    "enabled": True,
    "auto_update": False,
    "notify_in_chat": True,
    "input_turn_count": 3,
    "api_type": "openai_compatible",
    "api_base_url": "",
    "api_key": "",
    "model": "",
    "temperature": 0,
    "request_timeout": 120,
    "strict_mode": True,
    "debug_enabled": True,
    "mujian_enabled": True,
    "mujian_title_card": True,
    "mujian_turn_note": True,
    "mujian_default_collapsed": True,
    "mujian_chat_display_mode": "collapsed",
    "mujian_style": "classic",
    "mujian_title_style": "classic",
    "mujian_note_style": "classic",
    "mujian_expand_level": "standard",
    "mujian_note_density": "standard",
    "mujian_character_filter": "turn",
    "mujian_character_names": "",
    "mujian_protagonist_card_enabled": False,
    "mujian_protagonist_card_mode": "when_relevant",
    "mujian_protagonist_name": "",
    "mujian_protagonist_aliases": "",
    "mujian_worker_custom_prompt_enabled": False,
    "mujian_worker_style_prompt": "",
    "mujian_worker_protagonist_prompt": "",
    "mujian_template_id": "standard_metrics",
    "mujian_templates": DEFAULT_MUJIAN_TEMPLATES,
    "mujian_theme_id": "standard",
    "mujian_theme_packs": DEFAULT_MUJIAN_THEME_PACKS,
}

FIELD_TYPES = {"text", "textarea", "number", "enum", "boolean"}
TEXT_TYPES = {"text", "textarea", "enum"}
OPERATION_ALIASES = {
    "upsert": "upsert",
    "insert": "upsert",
    "add": "upsert",
    "create": "upsert",
    "update": "update",
    "set": "update",
    "delete": "delete",
    "remove": "delete",
}

app = FastAPI(title="Fantareal State Journal Mod")

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def now_string() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def clone_json(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False))


def hash_text(value: Any) -> str:
    text = str(value or "")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def normalize_turn_id(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"[^a-zA-Z0-9_.:-]+", "_", text).strip("_")
    return text or datetime.now().isoformat(timespec="microseconds")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return clone_json(default)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return clone_json(default)
    return payload


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def safe_id(value: Any, fallback: str = "table") -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9_]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or fallback


def qident(identifier: str) -> str:
    safe = safe_id(identifier, "")
    if not safe:
        raise ValueError("空 SQL 标识符。")
    return '"' + safe.replace('"', '""') + '"'


def data_table_name(table_id: str) -> str:
    return f"xj_data_{safe_id(table_id)}"


def sqlite_type(field_type: str) -> str:
    if field_type == "number":
        return "REAL"
    if field_type == "boolean":
        return "INTEGER"
    return "TEXT"


def migrate_legacy_data_dir() -> None:
    """Copy pre-release data/xinjian runtime files to data/mods/state_journal once."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DB_PATH.exists() and LEGACY_DB_PATH.exists():
        shutil.copy2(LEGACY_DB_PATH, DB_PATH)
    for folder_name in ("exports", "backups", "logs"):
        legacy_folder = LEGACY_DATA_DIR / folder_name
        target_folder = DATA_DIR / folder_name
        if legacy_folder.exists() and not target_folder.exists():
            shutil.copytree(legacy_folder, target_folder)


def connect_db() -> sqlite3.Connection:
    migrate_legacy_data_dir()
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def normalize_field(field: Any) -> dict[str, Any] | None:
    if not isinstance(field, dict):
        return None
    key = safe_id(field.get("key"), "")
    if not key:
        return None
    field_type = str(field.get("type") or "text").strip().lower()
    if field_type not in FIELD_TYPES:
        field_type = "text"
    options = field.get("options", [])
    if isinstance(options, str):
        options = [item.strip() for item in re.split(r"[,，、\n]", options) if item.strip()]
    if not isinstance(options, list):
        options = []
    normalized = {
        "key": key,
        "label": str(field.get("label") or key).strip() or key,
        "type": field_type,
        "required": bool(field.get("required", False)),
        "options": [str(item).strip() for item in options if str(item).strip()],
        "note": str(field.get("note") or "").strip(),
    }
    if field.get("hidden") is True:
        normalized["hidden"] = True
    return normalized


def normalize_schema(schema: Any) -> dict[str, Any]:
    if not isinstance(schema, dict):
        schema = {}
    table_id = safe_id(schema.get("id") or schema.get("table_id"), "table")
    fields: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in schema.get("fields", []):
        normalized = normalize_field(item)
        if normalized and normalized["key"] not in seen:
            fields.append(normalized)
            seen.add(normalized["key"])
    primary_key = safe_id(schema.get("primary_key"), "")
    if not primary_key and fields:
        primary_key = fields[0]["key"]
    if primary_key and primary_key not in seen:
        fields.insert(0, {"key": primary_key, "label": primary_key, "type": "text", "required": True, "options": [], "note": "主键字段"})
        seen.add(primary_key)
    for field in fields:
        if field["key"] == primary_key:
            field["required"] = True
    rules = schema.get("rules") if isinstance(schema.get("rules"), dict) else {}
    normalized_rules = {
        "note": str(rules.get("note") or schema.get("description") or "").strip(),
        "init": str(rules.get("init") or "").strip(),
        "insert": str(rules.get("insert") or "").strip(),
        "update": str(rules.get("update") or "").strip(),
        "delete": str(rules.get("delete") or "").strip(),
        "ignore": str(rules.get("ignore") or "").strip(),
    }
    return {
        "id": table_id,
        "name": str(schema.get("name") or schema.get("table_name") or table_id).strip() or table_id,
        "description": str(schema.get("description") or normalized_rules["note"] or "").strip(),
        "primary_key": primary_key,
        "fields": fields,
        "rules": normalized_rules,
        "updated_at": str(schema.get("updated_at") or now_string()),
    }



def normalize_template_field(field: Any) -> dict[str, Any] | None:
    if not isinstance(field, dict):
        return None
    key = safe_id(field.get("key"), "")
    if not key or key == "name":
        return None
    label = str(field.get("label") or key).strip() or key
    instruction = str(field.get("instruction") or field.get("note") or "根据本轮上下文生成该字段。{}").strip()
    return {"key": key, "label": label[:40], "instruction": instruction[:360]}




def default_output_line_for_template_field(field: dict[str, Any]) -> str:
    key = safe_id(field.get("key"), "")
    label = str(field.get("label") or key).strip() or key
    return f"<{label}({{{key}}})>"


def ensure_template_output_fields(output_template: Any, fields: list[dict[str, Any]]) -> str:
    """Keep field definitions and output placeholders in sync.

    v0.5.2：模板字段不仅用于前端预览，也会进入实际 worker prompt。
    如果用户新增字段但输出格式里还没有对应 {field_key}，这里自动补一行，避免
    出现“字段已保存但 Chat 生成/渲染不生效”的断链。
    """
    text = str(output_template or "").strip()
    for field in fields:
        key = safe_id(field.get("key"), "")
        if not key or key == "name":
            continue
        token = "{" + key + "}"
        if token not in text:
            line = default_output_line_for_template_field(field)
            text = f"{text}\n{line}".strip() if text else line
    return text[:3000]


def build_template_character_schema(fields: list[dict[str, Any]]) -> dict[str, str]:
    schema: dict[str, str] = {"name": "角色名"}
    for field in fields:
        if not isinstance(field, dict):
            continue
        key = safe_id(field.get("key"), "")
        if not key or key == "name":
            continue
        label = str(field.get("label") or key).strip() or key
        instruction = str(field.get("instruction") or "根据本轮上下文生成该字段。").strip()
        schema[key] = f"{label}。{instruction}"
    if "summary" not in schema:
        schema["summary"] = "一句话角色状态摘要；如果模板没有摘要字段，可以简短生成。"
    return schema

def normalize_mujian_template(template: Any, fallback_id: str = "custom") -> dict[str, Any] | None:
    if not isinstance(template, dict):
        return None
    template_id = safe_id(template.get("id"), fallback_id)
    fields: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in template.get("fields") or []:
        normalized = normalize_template_field(item)
        if normalized and normalized["key"] not in seen:
            fields.append(normalized)
            seen.add(normalized["key"])
    if not fields:
        fields = clone_json(DEFAULT_MUJIAN_TEMPLATES[0]["fields"])
    note_style = str(template.get("note_style") or template.get("style") or "classic").strip()
    if note_style not in {"classic", "gufeng", "sensory"}:
        note_style = "classic"
    fields = fields[:16]
    output_template = ensure_template_output_fields(template.get("output_template") or "", fields)
    return {
        "id": template_id,
        "name": str(template.get("name") or template_id).strip()[:60] or template_id,
        "description": str(template.get("description") or "").strip()[:240],
        "note_style": note_style,
        "fields": fields,
        "output_template": output_template,
    }



def refresh_builtin_mujian_template(template: dict[str, Any]) -> dict[str, Any]:
    """让旧配置中的内置标准模板跟随新版说明更新，同时不影响用户自定义模板。"""
    if not isinstance(template, dict):
        return template
    template_id = str(template.get("id") or "")
    builtin = next((item for item in DEFAULT_MUJIAN_TEMPLATES if item.get("id") == template_id), None)
    if not builtin:
        return template
    refreshed = clone_json(template)
    if template_id == "standard_metrics":
        default_fields = {field.get("key"): field for field in builtin.get("fields") or [] if isinstance(field, dict)}
        new_fields = []
        for field in refreshed.get("fields") or []:
            key = field.get("key") if isinstance(field, dict) else ""
            if key in default_fields and key in {"favor_level", "trust_level", "guard_level", "pulse_level"}:
                merged = {**field, "label": default_fields[key].get("label", field.get("label")), "instruction": default_fields[key].get("instruction", field.get("instruction"))}
                new_fields.append(merged)
            else:
                new_fields.append(field)
        refreshed["fields"] = new_fields
        refreshed["description"] = builtin.get("description") or refreshed.get("description") or ""
        refreshed["output_template"] = ensure_template_output_fields(refreshed.get("output_template") or builtin.get("output_template") or "", refreshed.get("fields") or [])
    return refreshed


def refresh_builtin_mujian_theme_pack(pack: dict[str, Any]) -> dict[str, Any]:
    """刷新内置外观包定义，保留用户导入包与自定义包。"""
    if not isinstance(pack, dict):
        return pack
    theme_id = str(pack.get("id") or "")
    builtin = next((item for item in DEFAULT_MUJIAN_THEME_PACKS if item.get("id") == theme_id), None)
    if not builtin:
        return pack
    return normalize_mujian_theme_pack(builtin, theme_id) or clone_json(pack)


def refresh_builtin_assets(config: dict[str, Any]) -> dict[str, Any]:
    """正式版配置收口：刷新内置模板/美化包，不覆盖用户自定义项目。"""
    refreshed = clone_json(config)
    refreshed["mujian_templates"] = normalize_mujian_templates(refreshed.get("mujian_templates"))
    refreshed["mujian_theme_packs"] = normalize_mujian_theme_packs(refreshed.get("mujian_theme_packs"))
    return refreshed

def normalize_mujian_templates(value: Any) -> list[dict[str, Any]]:
    source = value if isinstance(value, list) else []
    templates_out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for idx, item in enumerate(source):
        normalized = normalize_mujian_template(item, f"template_{idx + 1}")
        normalized = refresh_builtin_mujian_template(normalized) if normalized else normalized
        if normalized and normalized["id"] not in seen:
            templates_out.append(normalized)
            seen.add(normalized["id"])
    for item in DEFAULT_MUJIAN_TEMPLATES:
        normalized = normalize_mujian_template(item, item["id"])
        if normalized and normalized["id"] not in seen:
            templates_out.append(normalized)
            seen.add(normalized["id"])
    return templates_out or clone_json(DEFAULT_MUJIAN_TEMPLATES)


def active_mujian_template(config: dict[str, Any]) -> dict[str, Any]:
    templates_list = normalize_mujian_templates(config.get("mujian_templates"))
    active_id = safe_id(config.get("mujian_template_id"), "")
    for template in templates_list:
        if template.get("id") == active_id:
            return template
    note_style = str(config.get("mujian_note_style") or config.get("mujian_style") or "").strip()
    for template in templates_list:
        if template.get("id") == note_style or template.get("note_style") == note_style:
            return template
    return templates_list[0]



def normalize_mujian_theme_pack(pack: Any, fallback_id: str = "theme") -> dict[str, Any] | None:
    if not isinstance(pack, dict):
        return None
    theme_id = safe_id(pack.get("id"), fallback_id)
    raw_style = pack.get("style") if isinstance(pack.get("style"), dict) else None
    if raw_style is None and isinstance(pack.get("theme"), dict):
        raw_style = pack.get("theme")
    style = raw_style if isinstance(raw_style, dict) else {}
    class_name = str(style.get("class_name") or style.get("class") or f"theme-{theme_id}").strip()
    class_name = re.sub(r"[^a-zA-Z0-9_-]+", "-", class_name).strip("-") or f"theme-{theme_id}"
    accent = str(style.get("accent") or style.get("primary") or "").strip()

    def json_dict(value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            return {}
        try:
            return clone_json(value)
        except (TypeError, ValueError):
            return {}

    def json_copy(value: Any) -> Any:
        if not isinstance(value, (dict, list)):
            return {} if not isinstance(value, list) else []
        try:
            return clone_json(value)
        except (TypeError, ValueError):
            return {} if isinstance(value, dict) else []

    safe_style = {
        "class_name": class_name,
        "accent": accent,
        "title_card": json_dict(style.get("title_card")),
        "character_card": json_dict(style.get("character_card")),
        "relationship_card": json_dict(style.get("relationship_card")),
        "status_bar": json_dict(style.get("status_bar")),
    }
    # Without this, embedded storyboard images and custom label text are stripped when config is saved.
    for extra_key in ("layout", "blocks", "tokens", "field_style", "media", "labels"):
        if isinstance(pack.get(extra_key), dict):
            safe_style[extra_key] = json_dict(pack.get(extra_key))
        elif isinstance(style.get(extra_key), dict):
            safe_style[extra_key] = json_dict(style.get(extra_key))
    # It defines how existing numeric fields are rendered, but does not create or delete content fields.
    for extra_key in ("progress_bars",):
        if isinstance(pack.get(extra_key), list):
            safe_style[extra_key] = json_copy(pack.get(extra_key))
        elif isinstance(style.get(extra_key), list):
            safe_style[extra_key] = json_copy(style.get(extra_key))

    normalized = {
        "id": theme_id,
        "name": str(pack.get("name") or theme_id).strip()[:60] or theme_id,
        "version": str(pack.get("version") or "1.0.0").strip()[:32] or "1.0.0",
        "author": str(pack.get("author") or "").strip()[:80],
        "description": str(pack.get("description") or "").strip()[:260],
        "style": safe_style,
    }
    # Keep top-level media/labels too for old front-end fallbacks and community pack compatibility.
    if isinstance(pack.get("media"), dict):
        normalized["media"] = json_dict(pack.get("media"))
    if isinstance(pack.get("labels"), dict):
        normalized["labels"] = json_dict(pack.get("labels"))
    return normalized


def normalize_mujian_theme_packs(value: Any) -> list[dict[str, Any]]:
    source = value if isinstance(value, list) else []
    packs_out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for idx, item in enumerate(source):
        normalized = normalize_mujian_theme_pack(item, f"theme_{idx + 1}")
        normalized = refresh_builtin_mujian_theme_pack(normalized) if normalized else normalized
        if normalized and normalized["id"] not in seen:
            packs_out.append(normalized)
            seen.add(normalized["id"])
    for item in DEFAULT_MUJIAN_THEME_PACKS:
        normalized = normalize_mujian_theme_pack(item, item["id"])
        if normalized and normalized["id"] not in seen:
            packs_out.append(normalized)
            seen.add(normalized["id"])
    return packs_out or clone_json(DEFAULT_MUJIAN_THEME_PACKS)


def active_mujian_theme_pack(config: dict[str, Any]) -> dict[str, Any]:
    packs = normalize_mujian_theme_packs(config.get("mujian_theme_packs"))
    active_id = safe_id(config.get("mujian_theme_id"), "")
    for pack in packs:
        if pack.get("id") == active_id:
            return pack
    return packs[0]

def normalize_config(config: Any) -> dict[str, Any]:
    source = config if isinstance(config, dict) else {}
    merged = {**DEFAULT_CONFIG, **source}
    try:
        merged["input_turn_count"] = max(1, min(10, int(merged.get("input_turn_count", 3) or 3)))
    except (TypeError, ValueError):
        merged["input_turn_count"] = 3
    try:
        merged["request_timeout"] = max(10, min(600, int(merged.get("request_timeout", 120) or 120)))
    except (TypeError, ValueError):
        merged["request_timeout"] = 120
    try:
        merged["temperature"] = max(0, min(2, float(merged.get("temperature", 0) or 0)))
    except (TypeError, ValueError):
        merged["temperature"] = 0
    for key in ["enabled", "auto_update", "notify_in_chat", "strict_mode", "debug_enabled", "mujian_enabled", "mujian_title_card", "mujian_turn_note", "mujian_default_collapsed", "mujian_protagonist_card_enabled", "mujian_worker_custom_prompt_enabled"]:
        merged[key] = bool(merged.get(key))
    for key in ["api_type", "api_base_url", "api_key", "model", "mujian_style", "mujian_title_style", "mujian_note_style", "mujian_expand_level", "mujian_note_density", "mujian_chat_display_mode", "mujian_character_filter", "mujian_character_names", "mujian_protagonist_card_mode", "mujian_protagonist_name", "mujian_protagonist_aliases", "mujian_worker_style_prompt", "mujian_worker_protagonist_prompt", "mujian_template_id", "mujian_theme_id"]:
        merged[key] = str(merged.get(key) or "").strip()
    legacy_style = merged.get("mujian_style") or "classic"
    if merged.get("mujian_title_style") not in {"classic", "gufeng", "chapter"}:
        merged["mujian_title_style"] = legacy_style if legacy_style in {"classic", "gufeng"} else "classic"
    if merged.get("mujian_note_style") not in {"classic", "gufeng", "sensory"}:
        merged["mujian_note_style"] = legacy_style if legacy_style in {"classic", "gufeng", "sensory"} else "classic"
    # 保留给旧前端读取。
    merged["mujian_style"] = merged.get("mujian_note_style") or legacy_style
    if merged.get("mujian_note_density") not in {"compact", "standard", "detailed"}:
        merged["mujian_note_density"] = "standard"
    if merged.get("mujian_chat_display_mode") not in {"collapsed", "expanded", "compact", "hidden"}:
        # 兼容 v0.3.x 的“附笺默认折叠”布尔配置。
        merged["mujian_chat_display_mode"] = "collapsed" if merged.get("mujian_default_collapsed", True) else "expanded"
    merged["mujian_default_collapsed"] = merged.get("mujian_chat_display_mode") == "collapsed"
    if merged.get("mujian_character_filter") not in {"turn", "heroine", "protagonist", "custom", "all"}:
        merged["mujian_character_filter"] = "turn"
    if merged.get("mujian_protagonist_card_mode") not in {"when_relevant", "always"}:
        merged["mujian_protagonist_card_mode"] = "when_relevant"
    merged["mujian_templates"] = normalize_mujian_templates(merged.get("mujian_templates"))
    merged["mujian_theme_packs"] = normalize_mujian_theme_packs(merged.get("mujian_theme_packs"))
    active_theme = active_mujian_theme_pack(merged)
    merged["mujian_theme_id"] = active_theme.get("id") or "standard"
    active_template = active_mujian_template(merged)
    merged["mujian_template_id"] = active_template.get("id") or "classic"
    merged["mujian_note_style"] = active_template.get("note_style") or merged.get("mujian_note_style") or "classic"
    merged["mujian_style"] = merged["mujian_note_style"]
    return merged


def init_meta_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS xj_config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS xj_tables (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            primary_key TEXT NOT NULL,
            rules_json TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS xj_columns (
            table_id TEXT NOT NULL,
            key TEXT NOT NULL,
            label TEXT NOT NULL,
            type TEXT NOT NULL,
            required INTEGER NOT NULL DEFAULT 0,
            options_json TEXT NOT NULL DEFAULT '[]',
            note TEXT NOT NULL DEFAULT '',
            position INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (table_id, key),
            FOREIGN KEY (table_id) REFERENCES xj_tables(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS xj_update_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS xj_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            table_id TEXT NOT NULL,
            rows_json TEXT NOT NULL,
            reason TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS xj_turn_displays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            turn_id TEXT NOT NULL,
            message_id TEXT NOT NULL DEFAULT '',
            content_hash TEXT NOT NULL DEFAULT '',
            turn_index INTEGER NOT NULL DEFAULT 0,
            trigger_source TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            subtitle TEXT NOT NULL DEFAULT '',
            scene_json TEXT NOT NULL DEFAULT '{}',
            characters_json TEXT NOT NULL DEFAULT '[]',
            relationships_json TEXT NOT NULL DEFAULT '[]',
            raw_json TEXT NOT NULL DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS xj_scene_state (
            id TEXT PRIMARY KEY,
            updated_at TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            subtitle TEXT NOT NULL DEFAULT '',
            scene_json TEXT NOT NULL DEFAULT '{}',
            raw_json TEXT NOT NULL DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS xj_turn_records (
            turn_id TEXT PRIMARY KEY,
            message_id TEXT NOT NULL DEFAULT '',
            turn_index INTEGER NOT NULL DEFAULT 0,
            trigger_source TEXT NOT NULL DEFAULT '',
            user_hash TEXT NOT NULL DEFAULT '',
            user_text TEXT NOT NULL DEFAULT '',
            assistant_hash TEXT NOT NULL DEFAULT '',
            assistant_text TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending_assistant',
            state_journal_status TEXT NOT NULL DEFAULT 'pending',
            stale_reason TEXT NOT NULL DEFAULT '',
            seq_no INTEGER NOT NULL DEFAULT 0,
            revision INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS xj_turn_effects (
            turn_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            effects_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY (turn_id) REFERENCES xj_turn_records(turn_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS xj_metric_states (
            character_name TEXT NOT NULL,
            metric_key TEXT NOT NULL,
            label TEXT NOT NULL DEFAULT '',
            current_value REAL NOT NULL DEFAULT 0,
            delta_value REAL NOT NULL DEFAULT 0,
            max_value REAL NOT NULL DEFAULT 100,
            raw_value TEXT NOT NULL DEFAULT '',
            source_turn_id TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,
            PRIMARY KEY (character_name, metric_key)
        );
        CREATE TABLE IF NOT EXISTS xj_metric_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            turn_id TEXT NOT NULL,
            character_name TEXT NOT NULL,
            metric_key TEXT NOT NULL,
            label TEXT NOT NULL DEFAULT '',
            old_value REAL,
            delta_value REAL NOT NULL DEFAULT 0,
            new_value REAL NOT NULL DEFAULT 0,
            max_value REAL NOT NULL DEFAULT 100,
            raw_value TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS xj_hook_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            event TEXT NOT NULL DEFAULT '',
            page TEXT NOT NULL DEFAULT '',
            turn_id TEXT NOT NULL DEFAULT '',
            payload_json TEXT NOT NULL DEFAULT '{}'
        );
        """
    )
    turn_cols = {row["name"] for row in conn.execute("PRAGMA table_info(xj_turn_records)").fetchall()}
    if "xinjian_status" in turn_cols and "state_journal_status" not in turn_cols:
        conn.execute("ALTER TABLE xj_turn_records RENAME COLUMN xinjian_status TO state_journal_status")
        turn_cols = {row["name"] for row in conn.execute("PRAGMA table_info(xj_turn_records)").fetchall()}
    if "state_journal_status" not in turn_cols:
        conn.execute("ALTER TABLE xj_turn_records ADD COLUMN state_journal_status TEXT NOT NULL DEFAULT 'pending'")
        turn_cols.add("state_journal_status")
    if "seq_no" not in turn_cols:
        conn.execute("ALTER TABLE xj_turn_records ADD COLUMN seq_no INTEGER NOT NULL DEFAULT 0")
    if "revision" not in turn_cols:
        conn.execute("ALTER TABLE xj_turn_records ADD COLUMN revision INTEGER NOT NULL DEFAULT 0")
        turn_cols.add("revision")
    if "message_id" not in turn_cols:
        conn.execute("ALTER TABLE xj_turn_records ADD COLUMN message_id TEXT NOT NULL DEFAULT ''")
        turn_cols.add("message_id")
    if "turn_index" not in turn_cols:
        conn.execute("ALTER TABLE xj_turn_records ADD COLUMN turn_index INTEGER NOT NULL DEFAULT 0")
        turn_cols.add("turn_index")
    if "trigger_source" not in turn_cols:
        conn.execute("ALTER TABLE xj_turn_records ADD COLUMN trigger_source TEXT NOT NULL DEFAULT ''")
        turn_cols.add("trigger_source")

    display_cols = {row["name"] for row in conn.execute("PRAGMA table_info(xj_turn_displays)").fetchall()}
    if "message_id" not in display_cols:
        conn.execute("ALTER TABLE xj_turn_displays ADD COLUMN message_id TEXT NOT NULL DEFAULT ''")
    if "content_hash" not in display_cols:
        conn.execute("ALTER TABLE xj_turn_displays ADD COLUMN content_hash TEXT NOT NULL DEFAULT ''")
    if "turn_index" not in display_cols:
        conn.execute("ALTER TABLE xj_turn_displays ADD COLUMN turn_index INTEGER NOT NULL DEFAULT 0")
        display_cols.add("turn_index")
    if "trigger_source" not in display_cols:
        conn.execute("ALTER TABLE xj_turn_displays ADD COLUMN trigger_source TEXT NOT NULL DEFAULT ''")
        display_cols.add("trigger_source")
    rows = conn.execute("SELECT turn_id FROM xj_turn_records WHERE seq_no IS NULL OR seq_no<=0 ORDER BY created_at, rowid").fetchall()
    if rows:
        max_row = conn.execute("SELECT COALESCE(MAX(seq_no), 0) AS max_seq FROM xj_turn_records").fetchone()
        next_seq = int(max_row["max_seq"] or 0) + 1
        for row in rows:
            conn.execute("UPDATE xj_turn_records SET seq_no=? WHERE turn_id=?", (next_seq, row["turn_id"]))
            next_seq += 1

    exists = conn.execute("SELECT value FROM xj_config WHERE key = 'runtime'").fetchone()
    if not exists:
        conn.execute("INSERT INTO xj_config(key, value) VALUES('runtime', ?)", (json.dumps(DEFAULT_CONFIG, ensure_ascii=False),))


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
    return bool(row)


def field_map(schema: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {field["key"]: field for field in schema.get("fields", []) if isinstance(field, dict) and field.get("key")}


def build_create_table_sql(schema: dict[str, Any], physical_name: str | None = None) -> str:
    fields = schema.get("fields", [])
    primary_key = schema.get("primary_key")
    parts: list[str] = []
    for field in fields:
        key = field["key"]
        col = f"{qident(key)} {sqlite_type(field.get('type') or 'text')}"
        if key == primary_key:
            col += " PRIMARY KEY"
        if field.get("required") and key != primary_key:
            # Keep user editing forgiving. Required is validated before save/AI update,
            # not as a hard NOT NULL that would make partial AI updates brittle.
            pass
        parts.append(col)
    if not parts:
        raise ValueError("至少需要一个字段。")
    table_name = physical_name or data_table_name(schema["id"])
    return f"CREATE TABLE {qident(table_name)} ({', '.join(parts)})"


def sync_physical_table(conn: sqlite3.Connection, schema: dict[str, Any]) -> None:
    table_name = data_table_name(schema["id"])
    fields = [field["key"] for field in schema.get("fields", [])]
    if not fields:
        raise HTTPException(status_code=400, detail="至少需要一个字段。")
    if not table_exists(conn, table_name):
        conn.execute(build_create_table_sql(schema))
        return

    existing_info = conn.execute(f"PRAGMA table_info({qident(table_name)})").fetchall()
    existing_cols = [str(row["name"]) for row in existing_info]
    old_pk = next((str(row["name"]) for row in existing_info if int(row["pk"] or 0) == 1), "")
    new_pk = str(schema.get("primary_key") or "")
    old_set = set(existing_cols)
    new_set = set(fields)
    need_rebuild = old_pk != new_pk or old_set != new_set

    if not need_rebuild:
        # SQLite type changes require rebuild too. Keep it simple and rebuild if any
        # known column type differs materially.
        existing_types = {str(row["name"]): str(row["type"] or "").upper() for row in existing_info}
        for field in schema.get("fields", []):
            if existing_types.get(field["key"], "") != sqlite_type(field.get("type") or "text"):
                need_rebuild = True
                break

    if not need_rebuild:
        return

    temp_name = f"{table_name}_new_{int(datetime.now().timestamp())}"
    conn.execute(build_create_table_sql(schema, temp_name))
    common = [col for col in fields if col in existing_cols]
    if common:
        cols = ", ".join(qident(col) for col in common)
        conn.execute(f"INSERT OR IGNORE INTO {qident(temp_name)} ({cols}) SELECT {cols} FROM {qident(table_name)}")
    conn.execute(f"DROP TABLE {qident(table_name)}")
    conn.execute(f"ALTER TABLE {qident(temp_name)} RENAME TO {qident(table_name)}")


def save_schema_to_db(conn: sqlite3.Connection, schema: dict[str, Any]) -> dict[str, Any]:
    payload = normalize_schema(schema)
    if not payload["fields"]:
        raise HTTPException(status_code=400, detail="至少需要一个字段。")
    if not payload["primary_key"]:
        raise HTTPException(status_code=400, detail="必须设置主键字段。")
    if payload["primary_key"] not in {field["key"] for field in payload["fields"]}:
        raise HTTPException(status_code=400, detail="主键字段必须存在于字段列表。")
    payload["updated_at"] = now_string()
    conn.execute(
        """
        INSERT INTO xj_tables(id, name, description, primary_key, rules_json, updated_at)
        VALUES(?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            description=excluded.description,
            primary_key=excluded.primary_key,
            rules_json=excluded.rules_json,
            updated_at=excluded.updated_at
        """,
        (payload["id"], payload["name"], payload["description"], payload["primary_key"], json.dumps(payload["rules"], ensure_ascii=False), payload["updated_at"]),
    )
    conn.execute("DELETE FROM xj_columns WHERE table_id=?", (payload["id"],))
    for index, field in enumerate(payload["fields"]):
        conn.execute(
            """
            INSERT INTO xj_columns(table_id, key, label, type, required, options_json, note, position)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["id"],
                field["key"],
                field["label"],
                field["type"],
                1 if field.get("required") else 0,
                json.dumps(field.get("options") or [], ensure_ascii=False),
                field.get("note") or "",
                index,
            ),
        )
    sync_physical_table(conn, payload)
    return payload


def load_schema_from_row(conn: sqlite3.Connection, table_row: sqlite3.Row) -> dict[str, Any]:
    table_id = str(table_row["id"])
    columns = conn.execute(
        "SELECT key, label, type, required, options_json, note FROM xj_columns WHERE table_id=? ORDER BY position ASC, key ASC",
        (table_id,),
    ).fetchall()
    fields: list[dict[str, Any]] = []
    for row in columns:
        try:
            options = json.loads(row["options_json"] or "[]")
        except ValueError:
            options = []
        fields.append(
            {
                "key": str(row["key"]),
                "label": str(row["label"]),
                "type": str(row["type"] or "text"),
                "required": bool(row["required"]),
                "options": options if isinstance(options, list) else [],
                "note": str(row["note"] or ""),
            }
        )
    try:
        rules = json.loads(table_row["rules_json"] or "{}")
    except ValueError:
        rules = {}
    return normalize_schema(
        {
            "id": table_id,
            "name": table_row["name"],
            "description": table_row["description"],
            "primary_key": table_row["primary_key"],
            "fields": fields,
            "rules": rules,
            "updated_at": table_row["updated_at"],
        }
    )


def list_schemas_from_db(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM xj_tables ORDER BY id ASC").fetchall()
    return [load_schema_from_row(conn, row) for row in rows]


def get_schema_from_db(conn: sqlite3.Connection, table_id: str) -> dict[str, Any]:
    safe_table_id = safe_id(table_id, "")
    if not safe_table_id:
        raise HTTPException(status_code=400, detail="表 ID 不能为空。")
    row = conn.execute("SELECT * FROM xj_tables WHERE id=?", (safe_table_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="找不到这张表的结构。")
    return load_schema_from_row(conn, row)


def serialize_db_value(value: Any, field: dict[str, Any]) -> Any:
    if value is None:
        if field.get("type") == "boolean":
            return False
        return ""
    if field.get("type") == "boolean":
        return bool(value)
    if field.get("type") == "number":
        if value == "":
            return ""
        try:
            number = float(value)
        except (TypeError, ValueError):
            return value
        return int(number) if number.is_integer() else number
    return str(value)


def get_table_rows_from_db(conn: sqlite3.Connection, schema: dict[str, Any]) -> list[dict[str, Any]]:
    table_name = data_table_name(schema["id"])
    if not table_exists(conn, table_name):
        sync_physical_table(conn, schema)
    fields = schema.get("fields", [])
    columns = ", ".join(qident(field["key"]) for field in fields)
    rows = conn.execute(f"SELECT {columns} FROM {qident(table_name)}").fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        item: dict[str, Any] = {}
        for field in fields:
            item[field["key"]] = serialize_db_value(row[field["key"]], field)
        result.append(item)
    return result


def coerce_value(value: Any, field: dict[str, Any]) -> Any:
    field_type = field.get("type") or "text"
    label = field.get("label") or field.get("key")
    if value is None:
        if field_type == "boolean":
            return 0
        if field_type == "number":
            return None
        return ""
    if field_type == "number":
        if value == "":
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"字段 {label} 必须是数字。")
        return int(number) if number.is_integer() else number
    if field_type == "boolean":
        if isinstance(value, bool):
            return 1 if value else 0
        text = str(value).strip().lower()
        if text in {"true", "1", "yes", "y", "是", "开", "启用"}:
            return 1
        if text in {"false", "0", "no", "n", "否", "关", "禁用", ""}:
            return 0
        return 1 if value else 0
    if field_type == "enum":
        text = str(value).strip()
        options = field.get("options") or []
        if text and options and text not in options:
            raise ValueError(f"字段 {label} 只能填写：{' / '.join(options)}。")
        return text
    return str(value).strip()


def clean_rows(schema: dict[str, Any], rows: Any) -> list[dict[str, Any]]:
    fmap = field_map(schema)
    primary_key = schema.get("primary_key")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    source_rows = rows if isinstance(rows, list) else []
    for row in source_rows:
        if not isinstance(row, dict):
            continue
        cleaned: dict[str, Any] = {}
        for key, field in fmap.items():
            try:
                cleaned[key] = coerce_value(row.get(key), field)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        pk_value = str(cleaned.get(primary_key, "") if primary_key else "").strip()
        if primary_key:
            if not pk_value:
                continue
            if pk_value in seen:
                raise HTTPException(status_code=400, detail=f"主键重复：{pk_value}")
            seen.add(pk_value)
        result.append(cleaned)
    return result


def replace_table_rows(conn: sqlite3.Connection, schema: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    table_name = data_table_name(schema["id"])
    sync_physical_table(conn, schema)
    conn.execute(f"DELETE FROM {qident(table_name)}")
    fields = schema.get("fields", [])
    if not fields:
        return
    column_list = ", ".join(qident(field["key"]) for field in fields)
    placeholders = ", ".join("?" for _ in fields)
    sql = f"INSERT INTO {qident(table_name)} ({column_list}) VALUES ({placeholders})"
    for row in rows:
        values = [row.get(field["key"]) for field in fields]
        conn.execute(sql, values)


def delete_table_from_db(conn: sqlite3.Connection, table_id: str) -> None:
    safe_table_id = safe_id(table_id, "")
    if not safe_table_id:
        raise HTTPException(status_code=400, detail="表 ID 不能为空。")
    conn.execute(f"DROP TABLE IF EXISTS {qident(data_table_name(safe_table_id))}")
    conn.execute("DELETE FROM xj_columns WHERE table_id=?", (safe_table_id,))
    conn.execute("DELETE FROM xj_tables WHERE id=?", (safe_table_id,))


def build_table_snapshot(conn: sqlite3.Connection, table_ids: list[str] | None = None) -> list[dict[str, Any]]:
    selected = {safe_id(item, "") for item in table_ids or [] if safe_id(item, "")}
    snapshots = []
    for schema in list_schemas_from_db(conn):
        if selected and schema["id"] not in selected:
            continue
        rows = get_table_rows_from_db(conn, schema)
        snapshots.append({"schema": schema, "rows": rows})
    return snapshots


def save_snapshot(conn: sqlite3.Connection, table_id: str, reason: str = "update") -> None:
    try:
        schema = get_schema_from_db(conn, table_id)
        rows = get_table_rows_from_db(conn, schema)
        conn.execute(
            "INSERT INTO xj_snapshots(created_at, table_id, rows_json, reason) VALUES(?, ?, ?, ?)",
            (now_string(), table_id, json.dumps(rows, ensure_ascii=False), reason),
        )
    except Exception:
        # Snapshot is defensive; never block the actual user action because of it.
        pass


def ensure_runtime_data() -> None:
    with connect_db() as conn:
        init_meta_tables(conn)
        count = conn.execute("SELECT COUNT(*) AS count FROM xj_tables").fetchone()["count"]
        if count == 0 and BUILTIN_TEMPLATES_DIR.exists():
            for template_path in sorted(BUILTIN_TEMPLATES_DIR.glob("*.json")):
                payload = read_json(template_path, {})
                schema_payload = payload.get("schema") if isinstance(payload, dict) and "schema" in payload else payload
                schema = save_schema_to_db(conn, schema_payload)
                rows = clean_rows(schema, payload.get("rows", []) if isinstance(payload, dict) else [])
                replace_table_rows(conn, schema, rows)
        sync_visible_metric_tables(conn)
        conn.commit()


def get_config() -> dict[str, Any]:
    ensure_runtime_data()
    with connect_db() as conn:
        row = conn.execute("SELECT value FROM xj_config WHERE key='runtime'").fetchone()
    if not row:
        return clone_json(DEFAULT_CONFIG)
    try:
        payload = json.loads(row["value"] or "{}")
    except ValueError:
        payload = {}
    return normalize_config(payload)


def save_config(config: dict[str, Any]) -> dict[str, Any]:
    payload = normalize_config(config)
    with connect_db() as conn:
        init_meta_tables(conn)
        conn.execute(
            "INSERT INTO xj_config(key, value) VALUES('runtime', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (json.dumps(payload, ensure_ascii=False),),
        )
        conn.commit()
    return payload


def get_config_value(key: str, default: Any = None) -> Any:
    ensure_runtime_data()
    with connect_db() as conn:
        init_meta_tables(conn)
        row = conn.execute("SELECT value FROM xj_config WHERE key=?", (key,)).fetchone()
    if not row:
        return clone_json(default)
    try:
        return json.loads(row["value"] or "null")
    except ValueError:
        return clone_json(default)


def set_config_value(key: str, value: Any) -> Any:
    with connect_db() as conn:
        init_meta_tables(conn)
        conn.execute(
            "INSERT INTO xj_config(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, json.dumps(value, ensure_ascii=False)),
        )
        conn.commit()
    return value


def build_openai_url(base_url: str, endpoint: str) -> str:
    base = str(base_url or "").strip().rstrip("/")
    if not base:
        return ""
    clean_endpoint = endpoint.strip("/")
    if base.endswith(f"/{clean_endpoint}"):
        return base
    return f"{base}/{clean_endpoint}"


def auth_headers(api_key: str = "") -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    token = str(api_key or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def read_main_llm_config() -> dict[str, Any]:
    """Best-effort read of Fantareal's main model config.

    心笺作为独立 mod，不能直接 import 主 app 的运行状态；这里读取项目 data/settings.json。
    当前源码中 settings_path() 实际也指向 data/settings.json。
    """
    candidates = [
        PROJECT_ROOT / "data" / "settings.json",
        DATA_DIR.parent / "settings.json",
    ]
    source = ""
    settings: dict[str, Any] = {}
    for path in candidates:
        if path.exists():
            payload = read_json(path, {})
            if isinstance(payload, dict):
                settings = payload
                source = str(path)
                break
    return {
        "api_base_url": str(settings.get("llm_base_url", "") or "").strip(),
        "api_key": str(settings.get("llm_api_key", "") or "").strip(),
        "model": str(settings.get("llm_model", "") or "").strip(),
        "request_timeout": int(settings.get("request_timeout", 120) or 120) if str(settings.get("request_timeout", "")).strip() else 120,
        "source": source,
    }


async def fetch_model_list(base_url: str, api_key: str = "", timeout: int | float = 30) -> list[str]:
    url = build_openai_url(base_url, "models")
    if not url:
        raise HTTPException(status_code=400, detail="Base URL 不能为空。")
    async with httpx.AsyncClient(timeout=float(timeout or 30)) as client:
        try:
            response = await client.get(url, headers=auth_headers(api_key))
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:600] if exc.response is not None else str(exc)
            raise HTTPException(status_code=502, detail=f"拉取模型列表失败：{detail}") from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"拉取模型列表失败：{exc}") from exc
    models: list[str] = []
    data = payload.get("data") if isinstance(payload, dict) else None
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and item.get("id"):
                models.append(str(item["id"]))
            elif isinstance(item, str):
                models.append(item)
    elif isinstance(payload, dict):
        for key in ("models", "model_list"):
            value = payload.get(key)
            if isinstance(value, list):
                models.extend(str(item.get("id") if isinstance(item, dict) else item) for item in value if item)
    return sorted({item for item in models if item})


async def test_chat_completion(base_url: str, api_key: str, model: str, timeout: int | float = 30) -> None:
    url = build_openai_url(base_url, "chat/completions")
    if not url or not model:
        raise HTTPException(status_code=400, detail="请填写 Base URL 和模型名。")
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "只回复 ok"}],
        "temperature": 0,
        "max_tokens": 8,
    }
    async with httpx.AsyncClient(timeout=float(timeout or 30)) as client:
        try:
            response = await client.post(url, headers=auth_headers(api_key), json=payload)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:600] if exc.response is not None else str(exc)
            raise HTTPException(status_code=502, detail=f"测试连接失败：{detail}") from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"测试连接失败：{exc}") from exc
    try:
        _ = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(status_code=502, detail="测试连接失败：返回不是 OpenAI Chat Completions 兼容格式。") from exc


def strip_json_fence(text: str) -> str:
    raw = str(text or "").strip()
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()
    return raw


def extract_json_candidates(text: str) -> list[str]:
    raw = strip_json_fence(text)
    candidates: list[str] = []
    if raw:
        candidates.append(raw)
    start_obj = raw.find("{")
    end_obj = raw.rfind("}")
    if start_obj >= 0 and end_obj > start_obj:
        obj = raw[start_obj : end_obj + 1].strip()
        if obj and obj not in candidates:
            candidates.append(obj)
    start_arr = raw.find("[")
    end_arr = raw.rfind("]")
    if start_arr >= 0 and end_arr > start_arr:
        arr = raw[start_arr : end_arr + 1].strip()
        if arr and arr not in candidates:
            candidates.append(arr)
    return candidates


def repair_common_json_issues(text: str) -> str:
    """Fix small model-formatting mistakes without changing semantics.

    This intentionally stays conservative: code fences, tail commas, control chars,
    and unescaped ASCII quotes inside simple string-value lines.
    """
    raw = strip_json_fence(text)
    raw = raw.replace("\ufeff", "")
    raw = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", raw)
    start_obj = raw.find("{")
    end_obj = raw.rfind("}")
    if start_obj >= 0 and end_obj > start_obj:
        raw = raw[start_obj : end_obj + 1]
    raw = re.sub(r",\s*([}\]])", r"\1", raw)
    fixed_lines: list[str] = []
    for line in raw.splitlines():
        # Handles common model bug:
        #   "interaction": "说"你该添一件"时透露关心",
        m = re.match(r'^(\s*"[^"\n]+"\s*:\s*")(.*)("\s*,?\s*)$', line)
        if m:
            prefix, body, suffix = m.groups()
            if '"' in body:
                body = body.replace('"', '”')
                line = prefix + body + suffix
        fixed_lines.append(line)
    return "\n".join(fixed_lines).strip()


def extract_json_from_text(text: str) -> Any:
    raw = str(text or "").strip()
    if not raw:
        raise ValueError("辅助模型没有返回内容。")
    errors: list[str] = []
    for candidate in extract_json_candidates(raw):
        try:
            return json.loads(candidate)
        except ValueError as exc:
            errors.append(str(exc))
    repaired = repair_common_json_issues(raw)
    for candidate in extract_json_candidates(repaired):
        try:
            return json.loads(candidate)
        except ValueError as exc:
            errors.append(str(exc))
    raise ValueError(errors[-1] if errors else "模型返回内容不是合法 JSON。")


def normalize_updates(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        candidates = payload
    elif isinstance(payload, dict):
        candidates = payload.get("updates", [])
    else:
        candidates = []
    return [item for item in candidates if isinstance(item, dict)]


def select_row_by_pk(conn: sqlite3.Connection, schema: dict[str, Any], pk_value: str) -> dict[str, Any] | None:
    primary_key = schema.get("primary_key")
    if not primary_key:
        return None
    table_name = data_table_name(schema["id"])
    fields = schema.get("fields", [])
    columns = ", ".join(qident(field["key"]) for field in fields)
    row = conn.execute(
        f"SELECT {columns} FROM {qident(table_name)} WHERE {qident(primary_key)}=?",
        (pk_value,),
    ).fetchone()
    if not row:
        return None
    return {field["key"]: serialize_db_value(row[field["key"]], field) for field in fields}


def reverse_pair_id(value: str) -> str:
    text = str(value or "").strip()
    if "-" not in text:
        return ""
    left, right = [part.strip() for part in text.split("-", 1)]
    if not left or not right:
        return ""
    return f"{right}-{left}"


def resolve_relationship_pk(conn: sqlite3.Connection, schema: dict[str, Any], pk_value: str) -> tuple[str, dict[str, Any] | None, str]:
    """relationship 表 A-B / B-A 自动反查，避免正反主键不同导致整轮失败。"""
    before = select_row_by_pk(conn, schema, pk_value)
    if before is not None:
        return pk_value, before, ""
    if schema.get("id") != "relationship" or schema.get("primary_key") != "pair_id":
        return pk_value, before, ""
    reversed_pk = reverse_pair_id(pk_value)
    if not reversed_pk:
        return pk_value, before, ""
    reversed_before = select_row_by_pk(conn, schema, reversed_pk)
    if reversed_before is not None:
        return reversed_pk, reversed_before, f"关系主键已按反向匹配：{pk_value} → {reversed_pk}"
    return pk_value, before, ""



def apply_updates(updates: list[dict[str, Any]], *, dry_run: bool = False) -> dict[str, Any]:
    applied: list[dict[str, Any]] = []
    errors: list[str] = []
    touched_tables: set[str] = set()
    with connect_db() as conn:
        init_meta_tables(conn)
        schemas = {schema["id"]: schema for schema in list_schemas_from_db(conn)}
        try:
            conn.execute("BEGIN")
            snapshot_done: set[str] = set()
            for index, update in enumerate(updates, start=1):
                table_id = safe_id(update.get("table") or update.get("table_id"), "")
                if not table_id or table_id not in schemas:
                    errors.append(f"第 {index} 条更新指向未知表：{table_id or '空'}")
                    continue
                schema = schemas[table_id]
                fmap = field_map(schema)
                primary_key = schema.get("primary_key")
                operation = OPERATION_ALIASES.get(str(update.get("operation") or "upsert").strip().lower(), "upsert")
                key_payload = update.get("key") if isinstance(update.get("key"), dict) else {}
                set_payload = update.get("set") if isinstance(update.get("set"), dict) else {}
                if not primary_key or primary_key not in fmap:
                    errors.append(f"表 {schema.get('name')} 没有有效主键。")
                    continue
                pk_value = str(key_payload.get(primary_key) or set_payload.get(primary_key) or update.get(primary_key) or "").strip()
                if not pk_value:
                    errors.append(f"第 {index} 条更新缺少主键 {primary_key}。")
                    continue

                table_name = data_table_name(table_id)
                sync_physical_table(conn, schema)
                before = select_row_by_pk(conn, schema, pk_value)
                if table_id == "relationship" and primary_key == "pair_id":
                    pk_value, before, _relation_note = resolve_relationship_pk(conn, schema, pk_value)
                if operation == "delete":
                    if before is not None:
                        if table_id not in snapshot_done:
                            save_snapshot(conn, table_id, "worker_update")
                            snapshot_done.add(table_id)
                        conn.execute(f"DELETE FROM {qident(table_name)} WHERE {qident(primary_key)}=?", (pk_value,))
                        applied.append({"table": table_id, "operation": "delete", "key": {primary_key: pk_value}, "old": before})
                        touched_tables.add(table_id)
                    continue

                cleaned_set: dict[str, Any] = {}
                for key, value in set_payload.items():
                    safe_key = safe_id(key, "")
                    if safe_key not in fmap:
                        errors.append(f"第 {index} 条更新包含未知字段：{key}")
                        continue
                    try:
                        cleaned_set[safe_key] = coerce_value(value, fmap[safe_key])
                    except ValueError as exc:
                        errors.append(f"第 {index} 条更新字段错误：{exc}")
                try:
                    cleaned_set[primary_key] = coerce_value(pk_value, fmap[primary_key])
                except ValueError as exc:
                    errors.append(f"第 {index} 条更新主键错误：{exc}")
                    continue
                if "updated_at" in fmap and "updated_at" not in cleaned_set:
                    cleaned_set["updated_at"] = now_string()

                if operation == "update" and before is None:
                    if table_id == "relationship":
                        # 关系表缺行时降级为 upsert：正反关系主键或新关系不应让整轮心笺失败。
                        operation = "upsert"
                    else:
                        errors.append(f"第 {index} 条更新找不到主键为 {pk_value} 的行，已跳过。")
                        continue
                if table_id not in snapshot_done:
                    save_snapshot(conn, table_id, "worker_update")
                    snapshot_done.add(table_id)
                if before is None:
                    fields = schema.get("fields", [])
                    insert_row = {field["key"]: None for field in fields}
                    insert_row.update(cleaned_set)
                    cols = list(insert_row.keys())
                    sql = f"INSERT INTO {qident(table_name)} ({', '.join(qident(col) for col in cols)}) VALUES ({', '.join('?' for _ in cols)})"
                    conn.execute(sql, [insert_row[col] for col in cols])
                    applied.append({"table": table_id, "operation": "insert", "key": {primary_key: pk_value}, "set": clone_json(cleaned_set)})
                else:
                    update_cols = [col for col in cleaned_set.keys() if col != primary_key]
                    if update_cols:
                        set_clause = ", ".join(f"{qident(col)}=?" for col in update_cols)
                        values = [cleaned_set[col] for col in update_cols] + [pk_value]
                        conn.execute(f"UPDATE {qident(table_name)} SET {set_clause} WHERE {qident(primary_key)}=?", values)
                    applied.append({"table": table_id, "operation": "update", "key": {primary_key: pk_value}, "set": clone_json(cleaned_set), "old": before})
                touched_tables.add(table_id)
            if dry_run:
                conn.rollback()
            else:
                conn.commit()
        except Exception:
            conn.rollback()
            raise
    return {"applied": applied, "errors": errors, "touched_tables": sorted(touched_tables)}



def upsert_full_row(conn: sqlite3.Connection, schema: dict[str, Any], row: dict[str, Any]) -> None:
    table_name = data_table_name(schema["id"])
    sync_physical_table(conn, schema)
    fields = schema.get("fields", [])
    if not fields:
        return
    values = []
    for field in fields:
        try:
            values.append(coerce_value(row.get(field["key"]), field))
        except ValueError:
            values.append(row.get(field["key"]))
    sql = f"INSERT OR REPLACE INTO {qident(table_name)} ({', '.join(qident(field['key']) for field in fields)}) VALUES ({', '.join('?' for _ in fields)})"
    conn.execute(sql, values)


def rollback_turn_effects(conn: sqlite3.Connection, turn_id: str, reason: str = "reroll") -> int:
    safe_turn = normalize_turn_id(turn_id)
    row = conn.execute("SELECT effects_json FROM xj_turn_effects WHERE turn_id=?", (safe_turn,)).fetchone()
    if not row:
        conn.execute("DELETE FROM xj_turn_displays WHERE turn_id=?", (safe_turn,))
        return 0
    try:
        payload = json.loads(row["effects_json"] or "{}")
    except ValueError:
        payload = {}
    applied = payload.get("applied") if isinstance(payload, dict) else []
    if not isinstance(applied, list):
        applied = []
    schemas = {schema["id"]: schema for schema in list_schemas_from_db(conn)}
    count = 0
    for item in reversed(applied):
        if not isinstance(item, dict):
            continue
        table_id = safe_id(item.get("table"), "")
        schema = schemas.get(table_id)
        if not schema:
            continue
        primary_key = schema.get("primary_key")
        if not primary_key:
            continue
        key_payload = item.get("key") if isinstance(item.get("key"), dict) else {}
        pk_value = str(key_payload.get(primary_key) or "").strip()
        if not pk_value:
            continue
        table_name = data_table_name(table_id)
        sync_physical_table(conn, schema)
        operation = str(item.get("operation") or "").lower()
        old_row = item.get("old") if isinstance(item.get("old"), dict) else None
        if operation == "insert":
            conn.execute(f"DELETE FROM {qident(table_name)} WHERE {qident(primary_key)}=?", (pk_value,))
            count += 1
        elif old_row:
            upsert_full_row(conn, schema, old_row)
            count += 1
    count += rollback_metric_effects(conn, safe_turn, payload.get("metrics") if isinstance(payload, dict) else [])
    conn.execute("DELETE FROM xj_turn_effects WHERE turn_id=?", (safe_turn,))
    conn.execute("DELETE FROM xj_turn_displays WHERE turn_id=?", (safe_turn,))
    conn.execute(
        "UPDATE xj_turn_records SET state_journal_status='rolled_back', stale_reason=?, updated_at=? WHERE turn_id=?",
        (reason, now_string(), safe_turn),
    )
    return count


def save_turn_record(conn: sqlite3.Connection, *, turn_id: str, user_text: str = "", assistant_text: str = "", status: str = "pending_assistant", state_journal_status: str = "pending", message_id: str = "", turn_index: int | None = None, trigger_source: str = "") -> dict[str, Any]:
    safe_turn = normalize_turn_id(turn_id)
    now = now_string()
    user_hash = hash_text(user_text) if user_text else ""
    assistant_hash = hash_text(assistant_text) if assistant_text else ""
    safe_message_id = normalize_turn_id(message_id) if message_id else ""
    safe_turn_index = int(turn_index or 0) if str(turn_index or "").strip() else 0
    safe_trigger_source = str(trigger_source or "").strip()[:80]
    existing = conn.execute("SELECT * FROM xj_turn_records WHERE turn_id=?", (safe_turn,)).fetchone()
    if existing:
        user_text = user_text or str(existing["user_text"] or "")
        assistant_text = assistant_text or str(existing["assistant_text"] or "")
        user_hash = hash_text(user_text) if user_text else str(existing["user_hash"] or "")
        assistant_hash = hash_text(assistant_text) if assistant_text else str(existing["assistant_hash"] or "")
        seq_no = int(existing["seq_no"] or 0) or allocate_turn_sequence(conn, safe_turn)
        old_assistant_hash = str(existing["assistant_hash"] or "")
        old_user_hash = str(existing["user_hash"] or "")
        revision = int(existing["revision"] or 0)
        if not safe_message_id:
            safe_message_id = str(existing["message_id"] or "") if "message_id" in existing.keys() else ""
        if not safe_turn_index:
            safe_turn_index = int(existing["turn_index"] or 0) if "turn_index" in existing.keys() else 0
        if status in {"assistant_ready", "completed"} and ((assistant_hash and assistant_hash != old_assistant_hash) or (user_hash and user_hash != old_user_hash)):
            revision += 1
        conn.execute(
            """
            UPDATE xj_turn_records
            SET user_text=?, user_hash=?, assistant_text=?, assistant_hash=?, status=?, state_journal_status=?, stale_reason='', seq_no=?, revision=?, message_id=?, turn_index=?, trigger_source=?, updated_at=?
            WHERE turn_id=?
            """,
            (user_text, user_hash, assistant_text, assistant_hash, status, state_journal_status, seq_no, revision, safe_message_id, safe_turn_index, safe_trigger_source, now, safe_turn),
        )
        created_at = str(existing["created_at"] or now)
    else:
        max_row = conn.execute("SELECT COALESCE(MAX(seq_no), 0) AS max_seq FROM xj_turn_records").fetchone()
        seq_no = int(max_row["max_seq"] or 0) + 1
        revision = 0
        conn.execute(
            """
            INSERT INTO xj_turn_records(turn_id, message_id, turn_index, user_hash, user_text, assistant_hash, assistant_text, status, state_journal_status, stale_reason, seq_no, revision, created_at, updated_at)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, '', ?, ?, ?, ?)
            """,
            (safe_turn, safe_message_id, safe_turn_index, user_hash, user_text, assistant_hash, assistant_text, status, state_journal_status, seq_no, revision, now, now),
        )
        created_at = now
    return {
        "turn_id": safe_turn,
        "message_id": safe_message_id,
        "turn_index": safe_turn_index,
        "user_hash": user_hash,
        "assistant_hash": assistant_hash,
        "status": status,
        "state_journal_status": state_journal_status,
        "seq_no": seq_no,
        "revision": revision,
        "created_at": created_at,
        "updated_at": now,
    }


def mark_turns_stale(conn: sqlite3.Connection, from_turn_id: str | None = None, reason: str = "history_changed") -> dict[str, Any]:
    init_meta_tables(conn)
    now = now_string()
    if from_turn_id:
        row = conn.execute("SELECT created_at FROM xj_turn_records WHERE turn_id=?", (normalize_turn_id(from_turn_id),)).fetchone()
        if row:
            created_at = row["created_at"]
            affected = conn.execute(
                "UPDATE xj_turn_records SET status='stale', state_journal_status='stale', stale_reason=?, updated_at=? WHERE created_at>=?",
                (reason, now, created_at),
            ).rowcount
            conn.execute("DELETE FROM xj_turn_displays WHERE turn_id IN (SELECT turn_id FROM xj_turn_records WHERE created_at>=?)", (created_at,))
            return {"affected": affected, "from_turn_id": normalize_turn_id(from_turn_id), "reason": reason}
    affected = conn.execute(
        "UPDATE xj_turn_records SET status='stale', state_journal_status='stale', stale_reason=?, updated_at=?",
        (reason, now),
    ).rowcount
    conn.execute("DELETE FROM xj_turn_displays")
    return {"affected": affected, "from_turn_id": from_turn_id or "", "reason": reason}


def save_turn_effects(conn: sqlite3.Connection, turn_id: str, result: dict[str, Any]) -> None:
    safe_turn = normalize_turn_id(turn_id)
    payload = {
        "applied": result.get("applied") or [],
        "errors": result.get("errors") or [],
        "touched_tables": result.get("touched_tables") or [],
        "metrics": result.get("metrics") or [],
    }
    conn.execute(
        "INSERT INTO xj_turn_effects(turn_id, created_at, effects_json) VALUES(?, ?, ?) ON CONFLICT(turn_id) DO UPDATE SET created_at=excluded.created_at, effects_json=excluded.effects_json",
        (safe_turn, now_string(), json.dumps(payload, ensure_ascii=False)),
    )


def record_hook_event(conn: sqlite3.Connection, *, event: str, page: str = "chat", turn_id: str = "", payload: dict[str, Any] | None = None) -> None:
    init_meta_tables(conn)
    safe_payload = payload if isinstance(payload, dict) else {}
    conn.execute(
        "INSERT INTO xj_hook_events(created_at, event, page, turn_id, payload_json) VALUES(?, ?, ?, ?, ?)",
        (now_string(), str(event or ""), str(page or ""), normalize_turn_id(turn_id) if turn_id else "", json.dumps(safe_payload, ensure_ascii=False)),
    )
    conn.execute("DELETE FROM xj_hook_events WHERE id NOT IN (SELECT id FROM xj_hook_events ORDER BY id DESC LIMIT 200)")


def strip_title_sequence(value: Any) -> str:
    text = clean_display_text(value, 80)
    # 幕笺序号由程序生成，模型只负责标题正文。
    return re.sub(r"^第[\d一二三四五六七八九十百千万零〇两]+[幕章回笺节篇]\s*[·：:、\-—]?\s*", "", text).strip() or text


def clean_display_text(value: Any, limit: int = 360) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    if limit and len(text) > limit:
        return text[:limit].rstrip() + "…"
    return text


METRIC_DEFINITIONS: list[dict[str, Any]] = [
    {"key": "favor_level", "label": "好感", "code": "FAVOR", "scope": "relationship", "max": 100, "aliases": ["favor", "好感", "好感值"]},
    {"key": "trust_level", "label": "信任", "code": "TRUST", "scope": "relationship", "max": 100, "aliases": ["trust", "信任", "信任值"]},
    {"key": "bond_level", "label": "牵系", "code": "BOND", "scope": "relationship", "max": 100, "aliases": ["bond", "牵系", "依赖", "羁绊"]},
    {"key": "guard_level", "label": "戒备", "code": "GUARD", "scope": "relationship", "max": 100, "aliases": ["guard", "戒备", "戒备值", "防备"]},
    {"key": "intimacy_level", "label": "亲密", "code": "INTIMACY", "scope": "relationship", "max": 100, "aliases": ["intimacy", "亲密", "亲密度"]},
    {"key": "tension_level", "label": "紧张", "code": "TENSION", "scope": "relationship", "max": 100, "aliases": ["tension", "紧张", "张力"]},
    {"key": "pulse_level", "label": "心绪", "code": "PULSE", "scope": "character", "max": 100, "aliases": ["pulse", "心绪", "心绪波动", "情绪波动"]},
    {"key": "fatigue_level", "label": "疲惫", "code": "FATIGUE", "scope": "character", "max": 100, "aliases": ["fatigue", "疲惫", "疲劳"]},
    {"key": "injury_level", "label": "伤势", "code": "INJURY", "scope": "character", "max": 100, "aliases": ["injury", "伤势", "受伤"]},
    {"key": "stress_level", "label": "压力", "code": "STRESS", "scope": "character", "max": 100, "aliases": ["stress", "压力", "压迫"]},
]

METRIC_DEFINITION_BY_KEY: dict[str, dict[str, Any]] = {str(item["key"]): item for item in METRIC_DEFINITIONS}


def clamp_number(value: Any, minimum: float = 0, maximum: float = 100) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = minimum
    return max(minimum, min(maximum, number))


def format_metric_number(value: Any) -> int | float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0
    return int(number) if number.is_integer() else round(number, 2)


def format_metric_delta(delta: Any) -> str:
    number = format_metric_number(delta)
    sign = "+" if isinstance(number, (int, float)) and float(number) >= 0 else ""
    return f"{sign}{number}"


def format_metric_value(value: Any, max_value: Any = 100, delta: Any = 0) -> str:
    return f"{format_metric_number(value)}/{format_metric_number(max_value)}（{format_metric_delta(delta)}）"


def metric_keys_by_scope(scope: str) -> set[str]:
    return {str(item.get("key")) for item in METRIC_DEFINITIONS if item.get("scope") == scope}


def parse_metric_value(raw_value: Any, default_max: float = 100) -> dict[str, Any] | None:
    raw = str(raw_value or "").strip()
    if not raw:
        return None
    normalized = raw.replace("＋", "+").replace("－", "-").replace("（", "(").replace("）", ")").replace("／", "/")
    value_match = re.search(r"(^|[^+\-\d])(\d{1,3}(?:\.\d+)?)\s*(?:/\s*(\d{1,3}(?:\.\d+)?)|分|$|\(|[^\d])", normalized)
    if value_match:
        value = float(value_match.group(2))
        max_value = float(value_match.group(3) or default_max)
    else:
        value_match = re.search(r"^(\d{1,3}(?:\.\d+)?)", normalized)
        if not value_match:
            return None
        value = float(value_match.group(1))
        max_value = default_max
    max_value = max(1, max_value)
    delta_match = re.search(r"([+\-]\s*\d{1,3}(?:\.\d+)?)", normalized)
    delta = float(delta_match.group(1).replace(" ", "")) if delta_match else 0.0
    return {"value": clamp_number(value, 0, max_value), "delta": delta, "max": max_value, "raw": raw}


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {key: row[key] for key in row.keys()}


def get_metric_snapshot(conn: sqlite3.Connection) -> dict[str, Any]:
    init_meta_tables(conn)
    rows = conn.execute(
        """
        SELECT character_name, metric_key, label, current_value, delta_value, max_value, raw_value, source_turn_id, updated_at
        FROM xj_metric_states
        ORDER BY character_name ASC, metric_key ASC
        """
    ).fetchall()
    by_character: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        name = str(row["character_name"] or "").strip()
        if not name:
            continue
        by_character.setdefault(name, []).append({
            "key": row["metric_key"],
            "label": row["label"],
            "value": format_metric_number(row["current_value"]),
            "delta": format_metric_number(row["delta_value"]),
            "max": format_metric_number(row["max_value"]),
            "raw": row["raw_value"],
            "source_turn_id": row["source_turn_id"],
            "updated_at": row["updated_at"],
        })
    return by_character


def normalize_metric_display_value(parsed: dict[str, Any]) -> str:
    return format_metric_value(parsed.get("value", 0), parsed.get("max", 100), parsed.get("delta", 0))


def apply_display_metrics(conn: sqlite3.Connection, turn_id: str, display_payload: dict[str, Any]) -> list[dict[str, Any]]:
    init_meta_tables(conn)
    safe_turn = normalize_turn_id(turn_id)
    characters = display_payload.get("characters") if isinstance(display_payload, dict) else []
    if not isinstance(characters, list):
        return []
    applied: list[dict[str, Any]] = []
    now = now_string()
    for character in characters:
        if not isinstance(character, dict):
            continue
        name = clean_display_text(character.get("name") or character.get("角色") or "", 80)
        if not name:
            continue
        for metric in METRIC_DEFINITIONS:
            key = str(metric.get("key") or "")
            raw_value = character.get(key)
            if raw_value is None:
                for alias in [metric.get("label"), *(metric.get("aliases") or [])]:
                    if alias and alias in character:
                        raw_value = character.get(alias)
                        break
            parsed = parse_metric_value(raw_value, float(metric.get("max") or 100))
            if not parsed:
                continue
            label = str(metric.get("label") or key)
            current_value = float(parsed["value"])
            delta_value = float(parsed.get("delta") or 0)
            max_value = float(parsed.get("max") or metric.get("max") or 100)
            normalized_raw = normalize_metric_display_value(parsed)
            old = row_to_dict(conn.execute(
                "SELECT * FROM xj_metric_states WHERE character_name=? AND metric_key=?",
                (name, key),
            ).fetchone())
            conn.execute(
                """
                INSERT INTO xj_metric_states(character_name, metric_key, label, current_value, delta_value, max_value, raw_value, source_turn_id, updated_at)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(character_name, metric_key) DO UPDATE SET
                    label=excluded.label,
                    current_value=excluded.current_value,
                    delta_value=excluded.delta_value,
                    max_value=excluded.max_value,
                    raw_value=excluded.raw_value,
                    source_turn_id=excluded.source_turn_id,
                    updated_at=excluded.updated_at
                """,
                (name, key, label, current_value, delta_value, max_value, normalized_raw, safe_turn, now),
            )
            conn.execute(
                """
                INSERT INTO xj_metric_history(turn_id, character_name, metric_key, label, old_value, delta_value, new_value, max_value, raw_value, created_at)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (safe_turn, name, key, label, old.get("current_value") if old else None, delta_value, current_value, max_value, normalized_raw, now),
            )
            character[key] = normalized_raw
            applied.append({
                "character_name": name,
                "metric_key": key,
                "label": label,
                "old_state": old,
                "new_state": {
                    "character_name": name,
                    "metric_key": key,
                    "label": label,
                    "current_value": current_value,
                    "delta_value": delta_value,
                    "max_value": max_value,
                    "raw_value": normalized_raw,
                    "source_turn_id": safe_turn,
                    "updated_at": now,
                },
                "old_value": old.get("current_value") if old else None,
                "delta_value": delta_value,
                "new_value": current_value,
                "max_value": max_value,
                "raw_value": normalized_raw,
            })
    if applied:
        sync_visible_metric_tables(conn)
    return applied


def rollback_metric_effects(conn: sqlite3.Connection, turn_id: str, metrics: list[dict[str, Any]]) -> int:
    safe_turn = normalize_turn_id(turn_id)
    count = 0
    for item in reversed(metrics if isinstance(metrics, list) else []):
        if not isinstance(item, dict):
            continue
        name = str(item.get("character_name") or "").strip()
        key = str(item.get("metric_key") or "").strip()
        if not name or not key:
            continue
        old_state = item.get("old_state") if isinstance(item.get("old_state"), dict) else None
        if old_state:
            conn.execute(
                """
                INSERT INTO xj_metric_states(character_name, metric_key, label, current_value, delta_value, max_value, raw_value, source_turn_id, updated_at)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(character_name, metric_key) DO UPDATE SET
                    label=excluded.label,
                    current_value=excluded.current_value,
                    delta_value=excluded.delta_value,
                    max_value=excluded.max_value,
                    raw_value=excluded.raw_value,
                    source_turn_id=excluded.source_turn_id,
                    updated_at=excluded.updated_at
                """,
                (
                    old_state.get("character_name") or name,
                    old_state.get("metric_key") or key,
                    old_state.get("label") or "",
                    float(old_state.get("current_value") or 0),
                    float(old_state.get("delta_value") or 0),
                    float(old_state.get("max_value") or 100),
                    old_state.get("raw_value") or "",
                    old_state.get("source_turn_id") or "",
                    old_state.get("updated_at") or now_string(),
                ),
            )
        else:
            conn.execute("DELETE FROM xj_metric_states WHERE character_name=? AND metric_key=?", (name, key))
        count += 1

    conn.execute("DELETE FROM xj_metric_history WHERE turn_id=?", (safe_turn,))
    sync_visible_metric_tables(conn)
    return count


def metric_state_display(row: sqlite3.Row | dict[str, Any]) -> str:
    value = row["current_value"] if isinstance(row, sqlite3.Row) else row.get("current_value", 0)
    max_value = row["max_value"] if isinstance(row, sqlite3.Row) else row.get("max_value", 100)
    delta = row["delta_value"] if isinstance(row, sqlite3.Row) else row.get("delta_value", 0)
    return format_metric_value(value, max_value, delta)


def ensure_schema_extra_field(conn: sqlite3.Connection, table_id: str, field_def: dict[str, Any]) -> None:
    table_id = safe_id(table_id, "")
    if not table_id:
        return
    row = conn.execute("SELECT * FROM xj_tables WHERE id=?", (table_id,)).fetchone()
    if not row:
        return
    schema = load_schema_from_row(conn, row)
    if any(str(field.get("key")) == str(field_def.get("key")) for field in schema.get("fields") or []):
        return
    schema.setdefault("fields", []).append(field_def)
    save_schema_to_db(conn, schema)


def ensure_metric_history_schema(conn: sqlite3.Connection) -> None:
    schema = {
        "id": "metric_history",
        "name": "数值变化记录",
        "description": "系统生成的每回合数值变化记录，用于查看好感、信任、戒备、心绪等数值 old → new → delta。",
        "primary_key": "record_id",
        "fields": [
            {"key": "record_id", "label": "记录ID", "type": "text", "required": True, "note": "系统生成。"},
            {"key": "turn_id", "label": "回合ID", "type": "text", "note": "来源回合。"},
            {"key": "character_name", "label": "角色", "type": "text", "note": "数值所属角色。"},
            {"key": "metric_label", "label": "数值项", "type": "text", "note": "好感、信任、戒备、心绪等。"},
            {"key": "old_value", "label": "旧值", "type": "number", "note": "本轮之前的值。"},
            {"key": "new_value", "label": "新值", "type": "number", "note": "本轮之后的值。"},
            {"key": "delta_display", "label": "本轮变化", "type": "text", "note": "统一显示 +0 / +1 / -1。"},
            {"key": "raw_value", "label": "显示值", "type": "text", "note": "例如 71/100（+1）。"},
            {"key": "created_at", "label": "记录时间", "type": "text", "note": "系统写入时间。"},
        ],
        "rules": {
            "note": "此表由心笺数值系统镜像生成，用于查看与导出，不建议手动改写。",
            "init": "每轮心笺生成数值后自动记录。",
            "insert": "系统自动写入。",
            "update": "重 roll 或编辑重算后由系统重建。",
            "delete": "不建议手动删除。",
            "ignore": "用户无需手动维护。",
        },
    }
    row = conn.execute("SELECT * FROM xj_tables WHERE id='metric_history'").fetchone()
    if not row:
        save_schema_to_db(conn, schema)
    else:
        current = load_schema_from_row(conn, row)
        changed = False
        existing = {field.get("key") for field in current.get("fields") or []}
        for field in schema["fields"]:
            if field["key"] not in existing:
                current.setdefault("fields", []).append(field)
                changed = True
        if changed:
            save_schema_to_db(conn, current)


def delta_display(delta: Any) -> str:
    return format_metric_delta(delta)


def sync_metric_history_table(conn: sqlite3.Connection) -> None:
    ensure_metric_history_schema(conn)
    schema = get_schema_from_db(conn, "metric_history")
    rows = []
    history_rows = conn.execute(
        """
        SELECT id, turn_id, character_name, metric_key, label, old_value, delta_value, new_value, max_value, raw_value, created_at
        FROM xj_metric_history
        ORDER BY id DESC
        LIMIT 300
        """
    ).fetchall()
    for row in reversed(history_rows):
        record_id = f"{row['turn_id']}:{row['character_name']}:{row['metric_key']}:{row['id']}"
        rows.append({
            "record_id": record_id,
            "turn_id": row["turn_id"],
            "character_name": row["character_name"],
            "metric_label": row["label"] or row["metric_key"],
            "old_value": "" if row["old_value"] is None else format_metric_number(row["old_value"]),
            "new_value": format_metric_number(row["new_value"]),
            "delta_display": delta_display(row["delta_value"]),
            "raw_value": row["raw_value"] or format_metric_value(row["new_value"], row["max_value"], row["delta_value"]),
            "created_at": row["created_at"],
        })
    replace_table_rows(conn, schema, rows)


def sync_metric_summary_tables(conn: sqlite3.Connection) -> None:
    """把真实数值表镜像到用户可见表册：角色状态表、关系表、数值变化记录。"""
    ensure_schema_extra_field(conn, "character_status", {"key": "metrics_summary", "label": "数值摘要", "type": "textarea", "note": "由心笺数值系统同步，角色自身状态数值，例如心绪 47/100（+0）。"})
    ensure_schema_extra_field(conn, "relationship", {"key": "metrics_summary", "label": "数值摘要", "type": "textarea", "note": "由心笺数值系统同步，关系数值，例如好感 71/100（+1）；信任 80/100（+2）。"})

    rows = conn.execute(
        """
        SELECT character_name, metric_key, label, current_value, delta_value, max_value, raw_value
        FROM xj_metric_states
        ORDER BY character_name ASC, metric_key ASC
        """
    ).fetchall()
    by_character: dict[str, list[sqlite3.Row]] = {}
    for row in rows:
        name = str(row["character_name"] or "").strip()
        if name:
            by_character.setdefault(name, []).append(row)

    character_metric_keys = metric_keys_by_scope("character")
    relationship_metric_keys = metric_keys_by_scope("relationship")

    def summary_for(items: list[sqlite3.Row], allowed: set[str]) -> str:
        parts = []
        for row in items:
            if row["metric_key"] not in allowed:
                continue
            parts.append(f"{row['label'] or row['metric_key']} {metric_state_display(row)}")
        return "；".join(parts)

    try:
        char_schema = get_schema_from_db(conn, "character_status")
        char_table = data_table_name("character_status")
        sync_physical_table(conn, char_schema)
        for name, items in by_character.items():
            summary = summary_for(items, character_metric_keys)
            if summary:
                conn.execute(f"UPDATE {qident(char_table)} SET metrics_summary=? WHERE name=?", (summary, name))
    except Exception:
        pass

    try:
        rel_schema = get_schema_from_db(conn, "relationship")
        rel_table = data_table_name("relationship")
        sync_physical_table(conn, rel_schema)
        for name, items in by_character.items():
            summary = summary_for(items, relationship_metric_keys)
            if not summary:
                continue
            conn.execute(
                f"UPDATE {qident(rel_table)} SET metrics_summary=? WHERE {qident('from')}=? OR pair_id LIKE ?",
                (summary, name, f"{name}-%"),
            )
    except Exception:
        pass

    sync_metric_history_table(conn)


def sync_visible_metric_tables(conn: sqlite3.Connection) -> None:
    ensure_metric_history_schema(conn)
    sync_metric_summary_tables(conn)


def normalize_display_payload(payload: Any, *, latest_turn: dict[str, Any] | None = None, tables: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Normalize the assistant-generated front-end display payload.

    幕笺是展示层，不等于事实表。这里做最小清洗，真正的 HTML 由前端渲染。
    """
    display: Any = None
    if isinstance(payload, dict):
        display = payload.get("display") or payload.get("mujian") or payload.get("turn_display")
    if not isinstance(display, dict):
        return build_fallback_display(latest_turn=latest_turn, tables=tables)

    scene = display.get("scene") or display.get("scene_card") or {}
    if not isinstance(scene, dict):
        scene = {}
    characters = display.get("characters") or display.get("character_cards") or []
    if not isinstance(characters, list):
        characters = []
    relationships = display.get("relationships") or display.get("relationship_cards") or []
    if not isinstance(relationships, list):
        relationships = []

    title = strip_title_sequence(display.get("title") or scene.get("title") or "本轮幕笺")
    subtitle = clean_display_text(display.get("subtitle") or scene.get("subtitle") or display.get("quote") or "", 160)
    normalized_scene = {
        "title": title,
        "subtitle": subtitle,
        "time": clean_display_text(scene.get("time") or scene.get("time_text") or "时间未明", 80),
        "location": clean_display_text(scene.get("location") or "", 100),
        "weather": clean_display_text(scene.get("weather") or "", 80),
        "atmosphere": clean_display_text(scene.get("atmosphere") or "", 160),
        "event_summary": clean_display_text(scene.get("event_summary") or scene.get("summary") or display.get("summary") or "", 320),
        "characters": clean_display_text(scene.get("characters") or "", 180),
    }

    try:
        template_config = get_config()
    except Exception:
        template_config = DEFAULT_CONFIG
    display_template = active_mujian_template(template_config)
    display_fields = display.get("template_fields") if isinstance(display.get("template_fields"), list) else display_template.get("fields", [])
    output_template = str(display.get("output_template") or display_template.get("output_template") or "")

    normalized_characters: list[dict[str, Any]] = []
    for item in characters[:8]:
        if not isinstance(item, dict):
            continue
        name = clean_display_text(item.get("name") or item.get("角色") or "", 40)
        if not name:
            continue
        normalized_item = {
            "name": name,
            "emotion": clean_display_text(item.get("emotion") or item.get("mood") or item.get("情绪") or "", 220),
            "clothing": clean_display_text(item.get("clothing") or item.get("衣着") or "", 260),
            "posture": clean_display_text(item.get("posture") or item.get("pose") or item.get("角色神态") or "", 260),
            "scene": clean_display_text(item.get("scene") or item.get("场景") or normalized_scene.get("location") or "", 180),
            "sensory_field": clean_display_text(item.get("sensory_field") or item.get("感官场域") or "", 280),
            "body_temperature": clean_display_text(item.get("body_temperature") or item.get("body_temp") or item.get("躯体温差") or "", 220),
            "body_motion": clean_display_text(item.get("body_motion") or item.get("肢体动态") or "", 260),
            "micro_reaction": clean_display_text(item.get("micro_reaction") or item.get("微生理反应") or "", 260),
            "visual_focus": clean_display_text(item.get("visual_focus") or item.get("视觉焦点") or "", 260),
            "interaction": clean_display_text(item.get("interaction") or item.get("角色互动") or "", 320),
            "summary": clean_display_text(item.get("summary") or item.get("状态摘要") or "", 320),
        }
        for field in display_fields:
            if not isinstance(field, dict):
                continue
            key = safe_id(field.get("key"), "")
            label = str(field.get("label") or "").strip()
            if not key or key == "name":
                continue
            value = item.get(key)
            if value is None and label:
                value = item.get(label)
            if value is not None:
                normalized_item[key] = clean_display_text(value, 360)
        normalized_characters.append(normalized_item)

    normalized_relationships: list[dict[str, Any]] = []
    for item in relationships[:8]:
        if not isinstance(item, dict):
            continue
        normalized_relationships.append({
            "pair": clean_display_text(item.get("pair") or item.get("pair_id") or item.get("name") or "", 80),
            "stage": clean_display_text(item.get("stage") or item.get("relation") or "", 80),
            "change": clean_display_text(item.get("change") or item.get("summary") or item.get("attitude") or "", 320),
        })

    try:
        template_config = get_config()
    except Exception:
        template_config = DEFAULT_CONFIG
    display_template = active_mujian_template(template_config)
    return {
        "title": title,
        "subtitle": subtitle,
        "scene": normalized_scene,
        "characters": normalized_characters,
        "relationships": normalized_relationships,
        "style": clean_display_text(display.get("style") or display.get("note_style") or "classic", 40),
        "title_style": clean_display_text(display.get("title_style") or display.get("title_generation_style") or "classic", 40),
        "note_style": clean_display_text(display.get("note_style") or display.get("note_generation_style") or display.get("style") or display_template.get("note_style") or "classic", 40),
        "template_id": clean_display_text(display.get("template_id") or display_template.get("id") or "classic", 80),
        "template_name": clean_display_text(display.get("template_name") or display_template.get("name") or "", 80),
        "template_fields": display_fields,
        "output_template": output_template,
        "raw": display,
    }


def build_fallback_display(*, latest_turn: dict[str, Any] | None = None, tables: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    latest_turn = latest_turn or {}
    assistant_text = clean_display_text(latest_turn.get("assistant") or latest_turn.get("assistantText") or "", 220)
    title = "本轮幕笺"
    subtitle = assistant_text[:90] if assistant_text else "心笺已整理本轮状态。"
    character_rows: list[dict[str, Any]] = []
    location = ""
    for table in tables or []:
        schema = table.get("schema") if isinstance(table, dict) else {}
        if not isinstance(schema, dict) or schema.get("id") != "character_status":
            continue
        for row in table.get("rows") or []:
            if not isinstance(row, dict):
                continue
            if not location and row.get("location"):
                location = str(row.get("location"))
            character_rows.append({
                "name": clean_display_text(row.get("name"), 40),
                "emotion": clean_display_text(row.get("mood"), 180),
                "clothing": clean_display_text(row.get("appearance"), 220),
                "posture": clean_display_text(row.get("appearance"), 220),
                "scene": clean_display_text(row.get("location"), 120),
                "sensory_field": "",
                "body_temperature": clean_display_text(row.get("condition"), 160),
                "body_motion": "",
                "micro_reaction": "",
                "visual_focus": "",
                "interaction": "",
                "summary": clean_display_text(row.get("summary"), 260),
            })
    try:
        template_config = get_config()
    except Exception:
        template_config = DEFAULT_CONFIG
    display_template = active_mujian_template(template_config)
    return {
        "title": title,
        "subtitle": subtitle,
        "scene": {"title": title, "subtitle": subtitle, "time": "时间未明", "location": location, "weather": "", "atmosphere": "", "event_summary": assistant_text, "characters": ""},
        "characters": [item for item in character_rows if item.get("name")][:6],
        "relationships": [],
        "style": "fallback",
        "title_style": "classic",
        "note_style": display_template.get("note_style") or "classic",
        "template_id": display_template.get("id") or "classic",
        "template_name": display_template.get("name") or "",
        "template_fields": display_template.get("fields") or [],
        "output_template": display_template.get("output_template") or "",
        "raw": {},
    }


def allocate_turn_sequence(conn: sqlite3.Connection, turn_id: str) -> int:
    safe_turn = normalize_turn_id(turn_id)
    row = conn.execute("SELECT seq_no FROM xj_turn_records WHERE turn_id=?", (safe_turn,)).fetchone()
    if row and int(row["seq_no"] or 0) > 0:
        return int(row["seq_no"] or 0)
    max_row = conn.execute("SELECT COALESCE(MAX(seq_no), 0) AS max_seq FROM xj_turn_records").fetchone()
    next_seq = int(max_row["max_seq"] or 0) + 1
    if row:
        conn.execute("UPDATE xj_turn_records SET seq_no=? WHERE turn_id=?", (next_seq, safe_turn))
    return max(1, next_seq)


def get_turn_sequence(conn: sqlite3.Connection, turn_id: str) -> int:
    return allocate_turn_sequence(conn, turn_id)


def save_turn_display(display: dict[str, Any], *, turn_id: str | None = None, message_id: str = "", content_hash: str = "", turn_index: int | None = None, trigger_source: str = "") -> dict[str, Any]:
    payload = normalize_display_payload({"display": display})
    safe_turn_id = normalize_turn_id(turn_id or datetime.now().isoformat(timespec="seconds"))
    safe_message_id = normalize_turn_id(message_id) if message_id else ""
    safe_content_hash = normalize_turn_id(content_hash) if content_hash else hash_text(payload.get("title") or json.dumps(payload, ensure_ascii=False))
    safe_turn_index = int(turn_index or 0) if str(turn_index or "").strip() else 0
    safe_trigger_source = str(trigger_source or "").strip()[:80]
    created_at = now_string()
    with connect_db() as conn:
        init_meta_tables(conn)
        db_sequence = get_turn_sequence(conn, safe_turn_id)
        if not safe_turn_index:
            row = conn.execute("SELECT turn_index FROM xj_turn_records WHERE turn_id=?", (safe_turn_id,)).fetchone()
            safe_turn_index = int(row["turn_index"] or 0) if row else 0
        sequence = safe_turn_index or db_sequence
        payload["sequence"] = sequence
        payload["sequence_label"] = f"第 {sequence} 笺"
        payload["message_id"] = safe_message_id
        payload["content_hash"] = safe_content_hash
        payload["turn_index"] = safe_turn_index
        payload["trigger_source"] = safe_trigger_source
        if safe_message_id:
            conn.execute("DELETE FROM xj_turn_displays WHERE message_id=? OR turn_id=?", (safe_message_id, safe_turn_id))
        else:
            conn.execute("DELETE FROM xj_turn_displays WHERE turn_id=?", (safe_turn_id,))
        conn.execute(
            """
            INSERT INTO xj_turn_displays(turn_id, message_id, content_hash, turn_index, trigger_source, created_at, title, subtitle, scene_json, characters_json, relationships_json, raw_json)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                safe_turn_id,
                safe_message_id,
                safe_content_hash,
                safe_turn_index,
                safe_trigger_source,
                created_at,
                payload.get("title", ""),
                payload.get("subtitle", ""),
                json.dumps(payload.get("scene") or {}, ensure_ascii=False),
                json.dumps(payload.get("characters") or [], ensure_ascii=False),
                json.dumps(payload.get("relationships") or [], ensure_ascii=False),
                json.dumps(payload, ensure_ascii=False),
            ),
        )
        conn.execute(
            """
            INSERT INTO xj_scene_state(id, updated_at, title, subtitle, scene_json, raw_json)
            VALUES('current', ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                updated_at=excluded.updated_at,
                title=excluded.title,
                subtitle=excluded.subtitle,
                scene_json=excluded.scene_json,
                raw_json=excluded.raw_json
            """,
            (
                created_at,
                payload.get("title", ""),
                payload.get("subtitle", ""),
                json.dumps(payload.get("scene") or {}, ensure_ascii=False),
                json.dumps(payload, ensure_ascii=False),
            ),
        )
        conn.commit()
    payload["turn_id"] = safe_turn_id
    payload["created_at"] = created_at
    return payload

def latest_turn_display() -> dict[str, Any]:
    ensure_runtime_data()
    with connect_db() as conn:
        init_meta_tables(conn)
        row = conn.execute("SELECT raw_json FROM xj_turn_displays ORDER BY id DESC LIMIT 1").fetchone()
    if not row:
        return {}
    try:
        payload = json.loads(row["raw_json"] or "{}")
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {}


def build_update_summary(result: dict[str, Any], tables: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    applied = result.get("applied") or []
    errors = result.get("errors") or []
    table_names = {}
    for item in tables or []:
        schema = item.get("schema") if isinstance(item, dict) else {}
        if isinstance(schema, dict) and schema.get("id"):
            table_names[str(schema.get("id"))] = str(schema.get("name") or schema.get("id"))
    by_table: dict[str, dict[str, Any]] = {}
    for item in applied:
        table_id = str(item.get("table") or "")
        if not table_id:
            continue
        bucket = by_table.setdefault(table_id, {"table": table_id, "name": table_names.get(table_id, table_id), "count": 0})
        bucket["count"] += 1
    parts = [f"{item['name']} +{item['count']}" for item in by_table.values()]
    if errors and applied:
        status = "partial"
        message = f"部分更新成功：{len(applied)} 条已应用，{len(errors)} 条跳过。"
    elif errors:
        status = "error"
        message = f"更新失败：{errors[0]}"
    elif applied:
        status = "updated"
        message = "已更新：" + "｜".join(parts)
    else:
        status = "empty"
        message = "本轮无状态变化。"
    return {
        "status": status,
        "message": message,
        "total": len(applied),
        "errors": len(errors),
        "by_table": list(by_table.values()),
    }

def format_history(history: Any, limit_turns: int) -> list[dict[str, str]]:
    source = history if isinstance(history, list) else []
    clean = []
    for item in source:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").strip()
        if role not in {"user", "assistant"}:
            continue
        content = str(item.get("content") or "").strip()
        if content:
            clean.append({"role": role, "content": content})
    max_messages = max(2, limit_turns * 2)
    return clean[-max_messages:]



TITLE_STYLE_RULES = {
    "classic": "标题卡用清晰的小说小标题：标题短，副标题说明本轮重点；不要过度修辞。",
    "gufeng": "标题卡偏古风章回：标题可含雨、灯、风、旧约、病骨等意象；副标题像一句含蓄引语。",
    "chapter": "标题卡偏章节结构：标题更像章节名，副标题概括冲突和转折；不要输出第几幕/第几章/第几笺，序号由心笺程序生成。",
}

NOTE_STYLE_RULES = {
    "classic": "角色附笺偏清晰状态卡：情绪、衣着、神态、场景、互动、摘要都用自然说明。",
    "gufeng": "角色附笺偏小说旁白：字段仍完整，但措辞更含蓄、古风、克制，避免直白标签堆砌。",
    "sensory": "角色附笺必须偏标签式细节：重点生成情绪、衣着、角色神态、感官场域、躯体温差、肢体动态、微生理反应、视觉焦点、角色互动。每个字段都要有可展示内容，尤其不要把感官场域、躯体温差、肢体动态、微生理反应、视觉焦点留空。",
}


def split_prompt_names(value: object) -> list[str]:
    return [item.strip() for item in re.split(r"[，,、;；\n]+", str(value or "")) if item.strip()]

def build_protagonist_prompt_rule(config: dict[str, Any]) -> str:
    if not config.get("mujian_protagonist_card_enabled"):
        return ""
    name = str(config.get("mujian_protagonist_name") or "").strip()
    aliases = split_prompt_names(config.get("mujian_protagonist_aliases"))
    mode = str(config.get("mujian_protagonist_card_mode") or "when_relevant")
    name_line = f"主角名称：{name}。" if name else "主角名称未填写；如果无法稳定识别主角，不要凭空猜测具体姓名。"
    alias_line = f"主角别名：{'、'.join(aliases)}。" if aliases else "主角别名：无。"
    if mode == "always":
        mode_line = "生成方式：每轮都生成。display.characters 必须包含主角状态卡；若本轮主角信息较少，也只能写可观察的低推断状态。"
    else:
        mode_line = "生成方式：明显涉及时生成。只有本轮正文、用户输入、最近上下文或旧状态明确涉及主角的身体状态、伤势、调息、位置、气息、被照料或与他人的互动时，才生成主角状态卡。"
    return "\n20. 当前设置启用主角状态卡。" + name_line + alias_line + mode_line + "主角状态卡只记录可观察状态、身体状态、衣着、姿态、位置、气息与互动关系；不得替用户决定未发生的行动、台词、心理活动和选择。"

def build_worker_custom_prompt_rule(config: dict[str, Any]) -> str:
    if not config.get("mujian_worker_custom_prompt_enabled"):
        return ""
    parts: list[str] = []
    style_prompt = str(config.get("mujian_worker_style_prompt") or "").strip()
    protagonist_prompt = str(config.get("mujian_worker_protagonist_prompt") or "").strip()
    if style_prompt:
        parts.append("用户自定义幕笺语言风格补充：" + style_prompt)
    if protagonist_prompt:
        parts.append("用户自定义主角状态卡规则：" + protagonist_prompt)
    if not parts:
        return ""
    return "\n21. 以下是用户提供的安全附加提示词，只影响幕笺表达和主角状态卡取舍，不得覆盖 JSON 输出协议、updates 协议、SQLite 写入规则、字段 key 或禁止替用户行动的硬性规则：" + "\n".join(parts)

def build_worker_prompt(*, tables: list[dict[str, Any]], latest_turn: dict[str, Any] | None, history: list[dict[str, str]], config: dict[str, Any], metric_states: dict[str, Any] | None = None) -> tuple[str, str]:
    mujian_enabled = bool(config.get("mujian_enabled", True))
    expand_level = str(config.get("mujian_expand_level") or "standard")
    title_style = str(config.get("mujian_title_style") or "classic")
    active_template = active_mujian_template(config)
    note_style = str(active_template.get("note_style") or config.get("mujian_note_style") or config.get("mujian_style") or "classic")
    title_style_rule = TITLE_STYLE_RULES.get(title_style, TITLE_STYLE_RULES["classic"])
    note_style_rule = NOTE_STYLE_RULES.get(note_style, NOTE_STYLE_RULES["classic"])
    template_fields = active_template.get("fields") or []
    template_lines = [f"- {item.get('label')} ({item.get('key')}): {item.get('instruction')}" for item in template_fields if item.get("key")]
    character_schema = build_template_character_schema(template_fields)
    metric_field_keys = {"favor_level", "trust_level", "bond_level", "guard_level", "pulse_level", "tension_level", "fatigue_level", "injury_level", "intimacy_level", "stress_level"}
    has_metric_fields = any(str(item.get("key") or "") in metric_field_keys for item in template_fields if isinstance(item, dict))
    system_prompt = """你是 Fantareal 的“心笺”结构化记录与幕笺展示助手。你的任务不是继续剧情，也不是扮演角色，而是根据聊天内容维护结构化表格，并生成正文之外给用户看的幕笺展示。\n\n硬性规则：\n1. 只输出一个合法 JSON 对象，不要输出 Markdown、解释、寒暄或代码块。\n2. JSON 根结构必须是 {\"updates\": [], \"display\": {}}。\n3. updates 用于写入事实表；没有明确事实变化时，updates 可以为空数组。\n4. display 是给用户看的幕笺展示，每轮都要生成，除非输入为空。\n5. 不要输出 SQL，心笺后端会把 JSON 更新安全写入 SQLite。\n6. 不要新增重大剧情事实，不要替用户行动，不要改变主模型正文已经确定的结果。\n7. 幕笺可以对情绪、衣着、姿态、感官、互动潜台词做合理扩写，但只能基于正文、上下文、角色状态与氛围自然延展。\n8. 事实表要保守，幕笺可以写意；不要把展示扩写当成长期事实强行写入 updates。\n9. updates 只能更新表结构中已经存在的字段，不得新增未知字段。\n10. operation 只能使用 upsert、update、delete。
11. JSON 字符串内容中不要使用英文双引号；如需引用台词，请使用中文引号“……”或单引号，避免破坏 JSON。"""
    if config.get("strict_mode"):
        system_prompt += "\n12. 严格模式：updates 的字段类型、枚举范围、主键必须完全符合表结构。"
    if not mujian_enabled:
        system_prompt += "\n13. 当前幕笺关闭：display 可返回空对象，但 updates 仍按事实变化处理。"
    else:
        system_prompt += f"\n13. 当前幕笺扩写强度：{expand_level}。保守=少量推断；standard=自然细化；rich=更丰富的氛围与感官，但仍不得新增重大事件。"
        system_prompt += f"\n14. 标题生成风格：{title_style_rule}"
        system_prompt += f"\n15. 附笺生成风格：{note_style_rule}"
        if note_style == "sensory":
            system_prompt += "\n16. 感官标签不是外观皮肤，而是角色附笺内容结构。必须优先填满当前模板字段列表中的每一个字段。"
        if template_lines:
            system_prompt += "\n17. 当前附笺模板字段如下，display.characters 中每个角色都要按这些字段 key 输出；新增字段也必须真实生成，不得只保留在前端预览：\n" + "\n".join(template_lines)
            system_prompt += "\n18. display.output_template 里的 {field_key} 占位符必须能从角色对象中取到对应 key 的内容。"
            if has_metric_fields:
                system_prompt += "\n19. 当前模板包含关系/状态数值字段：这类字段必须使用固定格式 `当前值/100（本轮变化）`，例如 `65/100（+2）`、`72/100（+0）`、`18/100（-1）`。当前值限制在 0-100；变化值只表示本轮变化，不要写成长句解释。"
                system_prompt += "\n20. 如果 current_metrics 提供了该角色上一轮数值，必须以上一轮数值为基准，根据本轮剧情判断 delta，再输出新当前值；不要每回合机械 +1 或凭空重置。"
        system_prompt += build_protagonist_prompt_rule(config)
        system_prompt += build_worker_custom_prompt_rule(config)


    display_schema = {
        "title_style": title_style,
        "note_style": note_style,
        "template_id": active_template.get("id"),
        "template_name": active_template.get("name"),
        "template_fields": template_fields,
        "output_template": active_template.get("output_template") or "",
        "theme_id": active_mujian_theme_pack(config).get("id"),
        "theme_name": active_mujian_theme_pack(config).get("name"),
        "title": "本轮小说式标题，短而有画面感；不要包含第几幕/第几章/第几笺等序号",
        "subtitle": "一句引语或副标题，用来给本轮定调",
        "scene": {
            "time": "当前剧情时间，没有就留空",
            "location": "当前地点",
            "weather": "天气或环境，没有就留空",
            "atmosphere": "氛围标签或短句",
            "event_summary": "本轮发生了什么，简洁概括",
            "characters": "在场人物，字符串即可"
        },
        "characters": [character_schema],
        "relationships": [
            {"pair": "角色A-角色B", "stage": "关系阶段", "change": "本轮关系变化，没有就少写或留空"}
        ]
    }

    user_payload = {
        "storage_engine": "sqlite",
        "tables": tables,
        "latest_turn": latest_turn or {},
        "recent_history": history,
        "mujian_display_required": mujian_enabled,
        "title_generation_style": title_style,
        "title_generation_rule": title_style_rule,
        "note_generation_style": note_style,
        "note_generation_rule": note_style_rule,
        "active_note_template": active_template,
        "current_metrics": metric_states or {},
        "protagonist_card": {
            "enabled": bool(config.get("mujian_protagonist_card_enabled")),
            "mode": config.get("mujian_protagonist_card_mode"),
            "name": config.get("mujian_protagonist_name"),
            "aliases": split_prompt_names(config.get("mujian_protagonist_aliases")),
            "custom_rule_enabled": bool(config.get("mujian_worker_custom_prompt_enabled")),
        },
        "metric_rules": {
            "range": "0-100",
            "delta": "本轮变化，通常 -5 到 +5；心绪类可 -10 到 +10",
            "format": "当前值/100（本轮变化），例如 65/100（+2）、72/100（+0）、18/100（-1）",
            "display_only": "v0.8 数值层会保存这些字段的当前值和 delta，但不替代正文。",
        },
        "display_schema": display_schema,
        "output_example": {
            "updates": [
                {
                    "table": "character_status",
                    "operation": "upsert",
                    "key": {"name": "角色名"},
                    "set": {"mood": "根据本轮剧情更新后的心绪", "summary": "一句话状态摘要"},
                }
            ],
            "display": display_schema,
        },
    }
    user_prompt = "请根据以下表结构、旧数据和聊天内容，完成事实更新与幕笺展示生成。\n" + json.dumps(user_payload, ensure_ascii=False, indent=2)
    return system_prompt, user_prompt

def normalize_chat_completion_url(base_url: str) -> str:
    url = str(base_url or "").strip().rstrip("/")
    if not url:
        return ""
    if url.endswith("/chat/completions"):
        return url
    return f"{url}/chat/completions"


class WorkerProviderError(Exception):
    def __init__(self, error_type: str, message: str, *, status_code: int = 502, detail: str = "") -> None:
        super().__init__(message)
        self.error_type = error_type
        self.message = message
        self.status_code = status_code
        self.detail = detail


def classify_provider_status(status_code: int) -> str:
    if status_code == 429:
        return "rate_limit"
    if status_code in {401, 403}:
        return "auth_error"
    if status_code in {408, 504}:
        return "timeout"
    if status_code >= 500:
        return "provider_error"
    return "provider_error"


def provider_error_message(error_type: str, detail: str = "", *, timeout: float | int | None = None) -> str:
    clean_detail = re.sub(r"\s+", " ", str(detail or "")).strip()[:360]
    suffix = f" 服务商返回：{clean_detail}" if clean_detail else ""
    if error_type == "timeout":
        seconds = int(float(timeout or 0)) if timeout else 0
        return f"心笺生成超时：服务商在 {seconds} 秒内未返回结果。本轮没有写入新数据，可以稍后重试。" if seconds else "心笺生成超时：服务商长时间未返回结果。本轮没有写入新数据，可以稍后重试。"
    if error_type == "empty_response":
        return "心笺生成失败：服务商返回了空内容。本轮没有写入新数据。"
    if error_type == "invalid_provider_response":
        return "心笺生成失败：服务商返回格式不是 OpenAI Chat Completions 兼容格式。本轮没有写入新数据。"
    if error_type == "rate_limit":
        return "心笺生成失败：服务商限流或拒绝请求。请稍后重试，或检查额度与并发限制。" + suffix
    if error_type == "auth_error":
        return "心笺生成失败：服务商鉴权失败。请检查 API Key、Base URL 与模型权限。" + suffix
    if error_type == "network_error":
        return "无法连接心笺模型服务。请检查 API 地址、网络状态或代理设置。" + suffix
    if error_type == "config_error":
        return "请先在心笺里配置辅助模型 Base URL 和模型名。"
    return "心笺生成失败：服务商请求异常。本轮没有写入新数据。" + suffix


async def call_worker_model(*, config: dict[str, Any], system_prompt: str, user_prompt: str, json_mode: bool = True) -> str:
    api_url = normalize_chat_completion_url(config.get("api_base_url", ""))
    model = str(config.get("model") or "").strip()
    if not api_url or not model:
        raise WorkerProviderError("config_error", provider_error_message("config_error"), status_code=400)
    headers = {"Content-Type": "application/json"}
    api_key = str(config.get("api_key") or "").strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": float(config.get("temperature", 0) or 0),
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    timeout = float(config.get("request_timeout", 120) or 120)

    async def _post(current_payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(api_url, headers=headers, json=current_payload)
            response.raise_for_status()
            return response.json()

    try:
        try:
            data = await _post(payload)
        except httpx.HTTPStatusError as exc:
            # Some OpenAI-compatible providers do not support response_format yet.
            # Fall back once to plain Chat Completions when JSON mode is rejected.
            status_code = exc.response.status_code if exc.response is not None else 502
            detail = exc.response.text[:600] if exc.response is not None else str(exc)
            if json_mode and status_code in {400, 422} and "response_format" in detail:
                payload.pop("response_format", None)
                data = await _post(payload)
            else:
                error_type = classify_provider_status(status_code)
                raise WorkerProviderError(error_type, provider_error_message(error_type, detail, timeout=timeout), status_code=502, detail=detail) from exc
    except WorkerProviderError:
        raise
    except httpx.TimeoutException as exc:
        raise WorkerProviderError("timeout", provider_error_message("timeout", timeout=timeout), detail=str(exc)) from exc
    except httpx.RequestError as exc:
        raise WorkerProviderError("network_error", provider_error_message("network_error", str(exc)), detail=str(exc)) from exc
    except ValueError as exc:
        raise WorkerProviderError("invalid_provider_response", provider_error_message("invalid_provider_response"), detail=str(exc)) from exc
    except Exception as exc:
        raise WorkerProviderError("provider_error", provider_error_message("provider_error", str(exc)), detail=str(exc)) from exc
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise WorkerProviderError("invalid_provider_response", provider_error_message("invalid_provider_response"), detail=str(exc)) from exc
    text = str(content or "").strip()
    if not text:
        raise WorkerProviderError("empty_response", provider_error_message("empty_response"))
    return text


async def repair_worker_json(*, config: dict[str, Any], raw_output: str, parse_error: str) -> str:
    system_prompt = (
        "你是严格的 JSON 修复器。只修复用户提供的非法 JSON 文本，"
        "不要新增、删减或改写剧情含义。必须只返回一个合法 JSON 对象，"
        "根结构必须是 {\"updates\": [], \"display\": {}}。"
    )
    user_prompt = (
        "下面是一段模型返回的非法 JSON，请修复为合法 JSON。\n"
        "要求：\n"
        "1. 只返回 JSON 对象，不要 Markdown、解释或代码块。\n"
        "2. 保留原字段和原内容含义。\n"
        "3. 字符串中的英文双引号请改为中文引号或正确转义。\n"
        "4. 不要新增重大剧情事实。\n\n"
        f"解析错误：{parse_error}\n\n"
        "非法 JSON 原文：\n"
        f"{raw_output}"
    )
    return await call_worker_model(config=config, system_prompt=system_prompt, user_prompt=user_prompt, json_mode=True)


def save_worker_log(payload: dict[str, Any]) -> None:
    if payload:
        try:
            write_json(LATEST_LOG_PATH, payload)
        except OSError:
            pass
    with connect_db() as conn:
        init_meta_tables(conn)
        conn.execute(
            "INSERT INTO xj_update_logs(created_at, payload_json) VALUES(?, ?)",
            (payload.get("created_at") or now_string(), json.dumps(payload, ensure_ascii=False)),
        )
        # Keep the SQLite log table bounded for long-running playthroughs.
        conn.execute(
            "DELETE FROM xj_update_logs WHERE id NOT IN (SELECT id FROM xj_update_logs ORDER BY id DESC LIMIT 50)"
        )
        conn.commit()


def latest_worker_log() -> dict[str, Any]:
    json_log = read_json(LATEST_LOG_PATH, {})
    if json_log:
        return json_log
    with connect_db() as conn:
        init_meta_tables(conn)
        row = conn.execute("SELECT payload_json FROM xj_update_logs ORDER BY id DESC LIMIT 1").fetchone()
    if not row:
        return {}
    try:
        payload = json.loads(row["payload_json"] or "{}")
    except ValueError:
        payload = {}
    return payload if isinstance(payload, dict) else {}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    ensure_runtime_data()
    return templates.TemplateResponse(request, "index.html", {"version": VERSION, "storage_engine": "SQLite"})


@app.get("/api/config")
async def api_get_config() -> dict[str, Any]:
    config = get_config()
    safe_config = {**config, "api_key": config.get("api_key", "")}
    return {"config": safe_config, "version": VERSION, "storage_engine": "sqlite"}


@app.post("/api/config")
async def api_save_config(request: Request) -> dict[str, Any]:
    payload = await request.json()
    config = save_config(payload.get("config", payload) if isinstance(payload, dict) else {})
    return {"ok": True, "config": config}


@app.get("/api/main-config")
async def api_main_config() -> dict[str, Any]:
    config = read_main_llm_config()
    return {
        "ok": True,
        "config": {
            "api_base_url": config.get("api_base_url", ""),
            "api_key": config.get("api_key", ""),
            "model": config.get("model", ""),
            "request_timeout": config.get("request_timeout", 120),
        },
        "source": config.get("source", ""),
        "message": "已读取 Fantareal 本体模型配置。" if config.get("source") else "未找到本体模型配置文件。",
    }


@app.post("/api/models")
async def api_models(request: Request) -> dict[str, Any]:
    payload = await request.json()
    if not isinstance(payload, dict):
        payload = {}
    config_payload = payload.get("config") if isinstance(payload.get("config"), dict) else payload
    base_url = str(config_payload.get("api_base_url") or config_payload.get("base_url") or "").strip()
    api_key = str(config_payload.get("api_key") or "").strip()
    timeout = int(config_payload.get("request_timeout") or 30)
    models = await fetch_model_list(base_url, api_key, timeout)
    return {"ok": True, "models": models, "count": len(models), "message": f"已拉取 {len(models)} 个模型。"}


@app.post("/api/test-connection")
async def api_test_connection(request: Request) -> dict[str, Any]:
    payload = await request.json()
    if not isinstance(payload, dict):
        payload = {}
    config_payload = payload.get("config") if isinstance(payload.get("config"), dict) else payload
    base_url = str(config_payload.get("api_base_url") or config_payload.get("base_url") or "").strip()
    api_key = str(config_payload.get("api_key") or "").strip()
    model = str(config_payload.get("model") or "").strip()
    timeout = int(config_payload.get("request_timeout") or 30)
    # Prefer a lightweight /models check. Some providers do not support it, so fall back
    # to a tiny chat completion if the user supplied a model name.
    try:
        models = await fetch_model_list(base_url, api_key, timeout)
        model_message = f"模型列表可用，共 {len(models)} 个模型。"
        if model and models and model not in models:
            model_message += f" 当前填写模型 `{model}` 不在列表中，请确认供应商是否隐藏该模型。"
        return {"ok": True, "mode": "models", "models": models[:50], "message": model_message}
    except HTTPException as model_exc:
        if not model:
            raise model_exc
        await test_chat_completion(base_url, api_key, model, timeout)
        return {"ok": True, "mode": "chat", "message": f"连接成功：{model} 可以完成 Chat Completions 请求。"}


@app.post("/api/hook/ping")
async def api_hook_ping(request: Request) -> dict[str, Any]:
    payload = await request.json()
    if not isinstance(payload, dict):
        payload = {}
    status = {
        "loaded": True,
        "updated_at": now_string(),
        "event": str(payload.get("event") or "ping"),
        "page": str(payload.get("page") or "chat"),
        "message": str(payload.get("message") or "聊天页心笺脚本已加载。"),
        "turn_id": str(payload.get("turn_id") or payload.get("turnId") or ""),
    }
    set_config_value("hook_status", status)
    try:
        with connect_db() as conn:
            init_meta_tables(conn)
            record_hook_event(conn, event=status["event"], page=status["page"], turn_id=status.get("turn_id") or "", payload={**payload, "status": status})
            conn.commit()
    except Exception:
        pass
    return {"ok": True, "hook": status}


@app.get("/api/hook/status")
async def api_hook_status() -> dict[str, Any]:
    status = get_config_value("hook_status", {})
    if not isinstance(status, dict):
        status = {}
    return {"ok": True, "hook": status}


@app.post("/api/turn/start")
async def api_turn_start(request: Request) -> dict[str, Any]:
    payload = await request.json()
    if not isinstance(payload, dict):
        payload = {}
    turn_id = normalize_turn_id(payload.get("turn_id") or payload.get("created_at") or datetime.now().isoformat(timespec="microseconds"))
    user_text = str(payload.get("user_text") or payload.get("userText") or "")
    message_id = str(payload.get("message_id") or payload.get("user_message_id") or "")
    turn_index = payload.get("turn_index") or payload.get("turnIndex")
    with connect_db() as conn:
        init_meta_tables(conn)
        record = save_turn_record(conn, turn_id=turn_id, user_text=user_text, status="pending_assistant", state_journal_status="pending", message_id=message_id, turn_index=turn_index, trigger_source=str(payload.get("trigger_source") or payload.get("triggerSource") or payload.get("source") or "turn_start"))
        conn.commit()
    return {"ok": True, "turn": record}


@app.post("/api/turn/complete")
async def api_turn_complete(request: Request) -> dict[str, Any]:
    payload = await request.json()
    if not isinstance(payload, dict):
        payload = {}
    turn_id = normalize_turn_id(payload.get("turn_id") or payload.get("created_at") or datetime.now().isoformat(timespec="microseconds"))
    user_text = str(payload.get("user_text") or payload.get("userText") or "")
    assistant_text = str(payload.get("assistant_text") or payload.get("assistantText") or "")
    message_id = str(payload.get("assistant_message_id") or payload.get("message_id") or "")
    turn_index = payload.get("turn_index") or payload.get("turnIndex")
    with connect_db() as conn:
        init_meta_tables(conn)
        record = save_turn_record(conn, turn_id=turn_id, user_text=user_text, assistant_text=assistant_text, status="assistant_ready", state_journal_status="pending", message_id=message_id, turn_index=turn_index, trigger_source=str(payload.get("trigger_source") or payload.get("triggerSource") or payload.get("source") or "turn_complete"))
        conn.commit()
    return {"ok": True, "turn": record}


@app.post("/api/turn/invalidate")
async def api_turn_invalidate(request: Request) -> dict[str, Any]:
    payload = await request.json()
    if not isinstance(payload, dict):
        payload = {}
    turn_id = str(payload.get("turn_id") or "").strip()
    reason = str(payload.get("reason") or "history_changed").strip() or "history_changed"
    with connect_db() as conn:
        init_meta_tables(conn)
        rollback_count = 0
        deleted_displays = 0
        if turn_id:
            rollback_count = rollback_turn_effects(conn, turn_id, reason=reason)
            try:
                deleted_displays = conn.execute("DELETE FROM xj_turn_displays WHERE turn_id=?", (turn_id,)).rowcount or 0
            except Exception:
                deleted_displays = 0
        stale = mark_turns_stale(conn, turn_id or None, reason=reason)
        conn.commit()
    return {"ok": True, "rollback_count": rollback_count, "deleted_displays": deleted_displays, "stale": stale, "message": "已标记心笺记录过期。"}


@app.get("/api/turns/recent")
async def api_recent_turns(limit: int = 30) -> dict[str, Any]:
    safe_limit = max(1, min(100, int(limit or 30)))
    ensure_runtime_data()
    with connect_db() as conn:
        init_meta_tables(conn)
        rows = conn.execute("SELECT * FROM xj_turn_records ORDER BY created_at DESC LIMIT ?", (safe_limit,)).fetchall()
    turns = []
    for row in rows:
        turns.append({key: row[key] for key in row.keys()})
    return {"ok": True, "turns": turns, "count": len(turns)}


@app.get("/api/state")
async def api_state() -> dict[str, Any]:
    ensure_runtime_data()
    with connect_db() as conn:
        init_meta_tables(conn)
        sync_visible_metric_tables(conn)
        tables = []
        for schema in list_schemas_from_db(conn):
            rows = get_table_rows_from_db(conn, schema)
            tables.append({"schema": schema, "rows": rows, "row_count": len(rows)})
        metrics = get_metric_snapshot(conn)
    return {"version": VERSION, "storage_engine": "sqlite", "config": get_config(), "tables": tables, "metrics": metrics}


@app.get("/api/metrics")
async def api_metrics() -> dict[str, Any]:
    with connect_db() as conn:
        init_meta_tables(conn)
        metrics = get_metric_snapshot(conn)
    return {"ok": True, "metrics": metrics}


@app.post("/api/table")
async def api_create_table(request: Request) -> dict[str, Any]:
    payload = await request.json()
    with connect_db() as conn:
        init_meta_tables(conn)
        schema = save_schema_to_db(conn, payload.get("schema", payload) if isinstance(payload, dict) else {})
        rows = clean_rows(schema, payload.get("rows", []) if isinstance(payload, dict) else [])
        replace_table_rows(conn, schema, rows)
        conn.commit()
    return {"ok": True, "schema": schema, "rows": rows}


@app.get("/api/table/{table_id}")
async def api_get_table(table_id: str) -> dict[str, Any]:
    ensure_runtime_data()
    with connect_db() as conn:
        init_meta_tables(conn)
        schema = get_schema_from_db(conn, table_id)
        rows = get_table_rows_from_db(conn, schema)
    return {"schema": schema, "rows": rows}


@app.post("/api/table/{table_id}")
async def api_save_table(table_id: str, request: Request) -> dict[str, Any]:
    payload = await request.json()
    schema_payload = payload.get("schema") if isinstance(payload, dict) else None
    rows_payload = payload.get("rows", []) if isinstance(payload, dict) else []
    with connect_db() as conn:
        init_meta_tables(conn)
        schema = save_schema_to_db(conn, schema_payload or get_schema_from_db(conn, table_id))
        rows = clean_rows(schema, rows_payload)
        save_snapshot(conn, schema["id"], "manual_save")
        replace_table_rows(conn, schema, rows)
        conn.commit()
    return {"ok": True, "schema": schema, "rows": get_table_rows_for_response(schema)}


def get_table_rows_for_response(schema: dict[str, Any]) -> list[dict[str, Any]]:
    with connect_db() as conn:
        init_meta_tables(conn)
        return get_table_rows_from_db(conn, schema)


@app.delete("/api/table/{table_id}")
async def api_delete_table(table_id: str) -> dict[str, Any]:
    with connect_db() as conn:
        init_meta_tables(conn)
        delete_table_from_db(conn, table_id)
        conn.commit()
    return {"ok": True}


@app.post("/api/import")
async def api_import(request: Request) -> dict[str, Any]:
    payload = await request.json()
    imported: list[str] = []
    if isinstance(payload, dict) and isinstance(payload.get("tables"), list):
        items = payload["tables"]
    else:
        items = [payload]
    with connect_db() as conn:
        init_meta_tables(conn)
        for item in items:
            if not isinstance(item, dict):
                continue
            schema = save_schema_to_db(conn, item.get("schema", item))
            rows = clean_rows(schema, item.get("rows", []))
            replace_table_rows(conn, schema, rows)
            imported.append(schema["id"])
        conn.commit()
    return {"ok": True, "imported": imported}


@app.get("/api/export")
async def api_export() -> JSONResponse:
    ensure_runtime_data()
    with connect_db() as conn:
        init_meta_tables(conn)
        tables = build_table_snapshot(conn)
    config = get_config()
    # 导出默认不携带真实 API Key，避免分享心笺表格时泄露密钥。
    safe_config = {**config, "api_key": ""}
    payload = {"version": VERSION, "storage_engine": "sqlite", "exported_at": now_string(), "tables": tables, "config": safe_config}
    return JSONResponse(payload)


def recent_turn_displays(limit: int = 20) -> list[dict[str, Any]]:
    ensure_runtime_data()
    safe_limit = max(1, min(100, int(limit or 20)))
    with connect_db() as conn:
        init_meta_tables(conn)
        rows = conn.execute(
            "SELECT turn_id, message_id, content_hash, turn_index, trigger_source, created_at, raw_json FROM xj_turn_displays ORDER BY id DESC LIMIT ?",
            (safe_limit,),
        ).fetchall()
    items: list[dict[str, Any]] = []
    for row in reversed(rows):
        try:
            payload = json.loads(row["raw_json"] or "{}")
        except ValueError:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        payload["turn_id"] = row["turn_id"]
        payload["message_id"] = row["message_id"]
        payload["content_hash"] = row["content_hash"]
        payload["turn_index"] = row["turn_index"]
        payload["trigger_source"] = row["trigger_source"]
        payload["created_at"] = row["created_at"]
        display_sequence = int(row["turn_index"] or 0) if str(row["turn_index"] or "").strip() else 0
        if display_sequence:
            payload["sequence"] = display_sequence
            payload["sequence_label"] = f"第 {display_sequence} 笺"
        else:
            if not payload.get("sequence"):
                payload["sequence"] = len(items) + 1
            if not payload.get("sequence_label"):
                payload["sequence_label"] = f"第 {payload.get('sequence')} 笺"
        items.append(payload)
    return items


@app.get("/api/display/latest")
async def api_latest_display() -> dict[str, Any]:
    return {"display": latest_turn_display()}


@app.get("/api/display/recent")
async def api_recent_display(limit: int = 20) -> dict[str, Any]:
    displays = recent_turn_displays(limit)
    scene = latest_turn_display().get("scene", {}) if latest_turn_display() else {}
    return {"ok": True, "scene": scene, "turns": displays, "count": len(displays)}


@app.get("/api/logs/latest")
async def api_latest_log() -> dict[str, Any]:
    return {"log": latest_worker_log()}


def redact_secret(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    if len(text) <= 8:
        return "********"
    return text[:4] + "…" + text[-4:]


def load_json_row(value: Any, fallback: Any) -> Any:
    try:
        return json.loads(str(value or ""))
    except ValueError:
        return clone_json(fallback)


@app.get("/api/logs/export")
async def api_export_debug_log(limit: int = 80) -> JSONResponse:
    ensure_runtime_data()
    safe_limit = max(10, min(300, int(limit or 80)))
    with connect_db() as conn:
        init_meta_tables(conn)
        config = get_config()
        safe_config = {**config, "api_key": redact_secret(config.get("api_key"))}
        turn_records = [{key: row[key] for key in row.keys()} for row in conn.execute("SELECT * FROM xj_turn_records ORDER BY created_at DESC LIMIT ?", (safe_limit,)).fetchall()]
        turn_effects = [
            {"turn_id": row["turn_id"], "created_at": row["created_at"], "effects": load_json_row(row["effects_json"], {})}
            for row in conn.execute("SELECT * FROM xj_turn_effects ORDER BY created_at DESC LIMIT ?", (safe_limit,)).fetchall()
        ]
        turn_displays = [
            {"turn_id": row["turn_id"], "message_id": row["message_id"], "content_hash": row["content_hash"], "turn_index": row["turn_index"], "trigger_source": row["trigger_source"], "created_at": row["created_at"], "display": load_json_row(row["raw_json"], {})}
            for row in conn.execute("SELECT turn_id, message_id, content_hash, turn_index, trigger_source, created_at, raw_json FROM xj_turn_displays ORDER BY id DESC LIMIT ?", (safe_limit,)).fetchall()
        ]
        hook_events = [
            {"id": row["id"], "created_at": row["created_at"], "event": row["event"], "page": row["page"], "turn_id": row["turn_id"], "payload": load_json_row(row["payload_json"], {})}
            for row in conn.execute("SELECT * FROM xj_hook_events ORDER BY id DESC LIMIT ?", (safe_limit,)).fetchall()
        ]
        update_logs = [
            {"id": row["id"], "created_at": row["created_at"], "payload": load_json_row(row["payload_json"], {})}
            for row in conn.execute("SELECT * FROM xj_update_logs ORDER BY id DESC LIMIT ?", (min(30, safe_limit),)).fetchall()
        ]
        metric_states = [
            {key: row[key] for key in row.keys()}
            for row in conn.execute("SELECT * FROM xj_metric_states ORDER BY character_name ASC, metric_key ASC").fetchall()
        ]
        metric_history = [
            {key: row[key] for key in row.keys()}
            for row in conn.execute("SELECT * FROM xj_metric_history ORDER BY id DESC LIMIT ?", (safe_limit,)).fetchall()
        ]
    payload = {
        "version": VERSION,
        "exported_at": now_string(),
        "storage_engine": "sqlite",
        "database": str(DB_PATH),
        "config": safe_config,
        "latest_worker_log": latest_worker_log(),
        "turn_records": turn_records,
        "turn_effects": turn_effects,
        "turn_displays": turn_displays,
        "hook_events": hook_events,
        "update_logs": update_logs,
        "metric_states": metric_states,
        "metric_history": metric_history,
    }
    # 二次脱敏，避免 latest_worker_log / update_logs 内部误带完整配置。
    text = json.dumps(payload, ensure_ascii=False)
    api_key = str(config.get("api_key") or "")
    if api_key:
        text = text.replace(api_key, redact_secret(api_key))
    return JSONResponse(json.loads(text))


@app.post("/api/worker/update")
async def api_worker_update(request: Request) -> dict[str, Any]:
    payload = await request.json()
    if not isinstance(payload, dict):
        payload = {}
    config = get_config()
    if payload.get("manual") is not True and not config.get("enabled", True):
        return {"ok": True, "skipped": True, "status": "skipped", "message": "心笺已关闭。", "reason": "心笺已关闭。"}
    with connect_db() as conn:
        init_meta_tables(conn)
        table_ids = payload.get("table_ids") if isinstance(payload.get("table_ids"), list) else None
        tables = build_table_snapshot(conn, table_ids)
        metric_states = get_metric_snapshot(conn)
    if not tables:
        return {"ok": True, "skipped": True, "status": "skipped", "message": "没有可更新的表。", "reason": "没有可更新的表。"}
    latest_turn = payload.get("latest_turn") if isinstance(payload.get("latest_turn"), dict) else None
    trigger_source = str(payload.get("trigger_source") or payload.get("triggerSource") or payload.get("source") or payload.get("event_type") or "manual_backend").strip() or "manual_backend"
    direct_user_text = str(payload.get("user_text") or payload.get("userText") or "")
    direct_assistant_text = str(
        payload.get("assistant_clean_text")
        or payload.get("assistantCleanText")
        or payload.get("assistant_text")
        or payload.get("assistantText")
        or ""
    )
    if latest_turn is None and (direct_user_text or direct_assistant_text):
        latest_turn = {"user": direct_user_text, "assistant": direct_assistant_text}
    elif isinstance(latest_turn, dict):
        latest_turn = {**latest_turn}
        if direct_user_text:
            latest_turn["user"] = direct_user_text
        if direct_assistant_text:
            latest_turn["assistant"] = direct_assistant_text
    history_source = payload.get("recent_history") if isinstance(payload.get("recent_history"), list) else payload.get("recentHistory")
    if history_source is None:
        history_source = payload.get("history")
    history = format_history(history_source, int(config.get("input_turn_count", 3) or 3))
    turn_id = normalize_turn_id(payload.get("turn_id") or payload.get("turnId") or payload.get("created_at") or payload.get("createdAt") or datetime.now().isoformat(timespec="seconds"))
    message_id = normalize_turn_id(payload.get("assistant_message_id") or payload.get("assistantMessageId") or payload.get("message_id") or payload.get("messageId") or "") if (payload.get("assistant_message_id") or payload.get("assistantMessageId") or payload.get("message_id") or payload.get("messageId")) else ""
    turn_index = payload.get("turn_index") or payload.get("turnIndex")
    safe_turn_index = int(turn_index or 0) if str(turn_index or "").strip() else 0
    user_text = str((latest_turn or {}).get("user") or (latest_turn or {}).get("userText") or "")
    assistant_text = str((latest_turn or {}).get("assistant") or (latest_turn or {}).get("assistantText") or "")
    if trigger_source in {"chat_hook", "dom_fallback"} and not assistant_text.strip():
        result = {"applied": [], "errors": ["心笺未检测到可绑定的 assistant 正文，本轮未生成幕笺。"], "touched_tables": []}
        log_payload = {
            "created_at": now_string(),
            "storage_engine": "sqlite",
            "database": str(DB_PATH),
            "request": {"turn_id": turn_id, "message_id": message_id, "turn_index": safe_turn_index, "trigger_source": trigger_source, "event_type": payload.get("event_type") or payload.get("source") or "auto_update", "latest_turn": latest_turn, "history": history, "table_ids": table_ids, "dry_run": bool(payload.get("dry_run", False)), "user_hash": payload.get("user_hash"), "assistant_hash": payload.get("assistant_hash")},
            "system_prompt": "",
            "user_prompt": "",
            "raw_output": "",
            "parsed": None,
            "updates": [],
            "display": {},
            "result": result,
            "error_type": "empty_context",
        }
        if config.get("debug_enabled", True):
            save_worker_log(log_payload)
        return {"ok": False, "status": "error", "error_type": "empty_context", "message": result["errors"][0], "summary": build_update_summary(result, tables), "updates": [], "turn_id": turn_id, "message_id": message_id, "turn_index": safe_turn_index, "trigger_source": trigger_source, "display": {}, "result": result, "raw_output": ""}
    system_prompt, user_prompt = build_worker_prompt(tables=tables, latest_turn=latest_turn, history=history, config=config, metric_states=metric_states)
    raw_output = ""
    try:
        raw_output = await call_worker_model(config=config, system_prompt=system_prompt, user_prompt=user_prompt)
    except WorkerProviderError as exc:
        result = {"applied": [], "errors": [exc.message], "touched_tables": []}
        log_payload = {
            "created_at": now_string(),
            "storage_engine": "sqlite",
            "database": str(DB_PATH),
            "request": {"turn_id": turn_id, "message_id": message_id, "turn_index": safe_turn_index, "trigger_source": trigger_source, "event_type": payload.get("event_type") or payload.get("source") or "auto_update", "latest_turn": latest_turn, "history": history, "table_ids": table_ids, "dry_run": bool(payload.get("dry_run", False)), "user_hash": payload.get("user_hash"), "assistant_hash": payload.get("assistant_hash")},
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "raw_output": raw_output,
            "parsed": None,
            "updates": [],
            "display": {},
            "result": result,
            "error_type": exc.error_type,
            "error_detail": exc.detail,
        }
        if config.get("debug_enabled", True):
            save_worker_log(log_payload)
        summary = build_update_summary(result, tables)
        return {
            "ok": False,
            "status": "error",
            "error_type": exc.error_type,
            "message": exc.message,
            "summary": summary,
            "updates": [],
            "turn_id": turn_id,
            "message_id": message_id,
            "turn_index": safe_turn_index,
            "trigger_source": trigger_source,
            "display": {},
            "result": result,
            "raw_output": "",
        }
    parse_error = ""
    repair_error = ""
    repair_used = False
    repair_output = ""
    parsed: Any = None
    updates: list[dict[str, Any]] = []
    display_payload: dict[str, Any] = {}
    try:
        parsed = extract_json_from_text(raw_output)
        updates = normalize_updates(parsed)
        if config.get("mujian_enabled", True):
            display_payload = normalize_display_payload(parsed, latest_turn=latest_turn, tables=tables)
    except Exception as exc:
        parse_error = str(exc)
        try:
            repair_output = await repair_worker_json(config=config, raw_output=raw_output, parse_error=parse_error)
            parsed = extract_json_from_text(repair_output)
            updates = normalize_updates(parsed)
            if config.get("mujian_enabled", True):
                display_payload = normalize_display_payload(parsed, latest_turn=latest_turn, tables=tables)
            repair_used = True
            parse_error = ""
        except Exception as repair_exc:
            repair_error = str(repair_exc)
    worker_error_type = ""
    if parse_error:
        worker_error_type = "invalid_json"
        detail = parse_error + (f"；JSON 修复失败：{repair_error}" if repair_error else "")
        result = {"applied": [], "errors": [f"心笺解析失败：模型返回内容不是合法 JSON。本轮没有写入新数据。详情：{detail}"], "touched_tables": []}
    else:
        if not payload.get("dry_run", False):
            with connect_db() as conn:
                init_meta_tables(conn)
                rollback_turn_effects(conn, turn_id, reason="regenerate_before_update")
                save_turn_record(conn, turn_id=turn_id, user_text=user_text, assistant_text=assistant_text, status="assistant_ready", state_journal_status="running", message_id=message_id, turn_index=safe_turn_index, trigger_source=trigger_source)
                conn.commit()
        result = apply_updates(updates, dry_run=bool(payload.get("dry_run", False)))
        if config.get("mujian_enabled", True) and not payload.get("dry_run", False):
            with connect_db() as conn:
                init_meta_tables(conn)
                metric_applied = apply_display_metrics(conn, turn_id, display_payload)
                if metric_applied:
                    result["metrics"] = metric_applied
                    result["metric_count"] = len(metric_applied)
                save_turn_effects(conn, turn_id, result)
                save_turn_record(conn, turn_id=turn_id, user_text=user_text, assistant_text=assistant_text, status="completed", state_journal_status="done" if not result.get("errors") else "error", message_id=message_id, turn_index=safe_turn_index, trigger_source=trigger_source)
                conn.commit()
        elif not payload.get("dry_run", False):
            with connect_db() as conn:
                init_meta_tables(conn)
                save_turn_effects(conn, turn_id, result)
                save_turn_record(conn, turn_id=turn_id, user_text=user_text, assistant_text=assistant_text, status="completed", state_journal_status="done" if not result.get("errors") else "error", message_id=message_id, turn_index=safe_turn_index, trigger_source=trigger_source)
                conn.commit()
        if config.get("mujian_enabled", True) and not payload.get("dry_run", False):
            try:
                # Refresh snapshots after fact updates so fallback display can read fresh state.
                with connect_db() as conn:
                    init_meta_tables(conn)
                    refreshed_tables = build_table_snapshot(conn, table_ids)
                if not display_payload:
                    display_payload = build_fallback_display(latest_turn=latest_turn, tables=refreshed_tables)
                display_payload = save_turn_display(display_payload, turn_id=turn_id, message_id=message_id, content_hash=payload.get("assistant_hash") or payload.get("content_hash") or payload.get("contentHash") or hash_text(assistant_text), turn_index=safe_turn_index, trigger_source=trigger_source)
            except Exception as exc:
                result.setdefault("errors", []).append(f"幕笺保存失败：{exc}")
    log_payload = {
        "created_at": now_string(),
        "storage_engine": "sqlite",
        "database": str(DB_PATH),
        "request": {"turn_id": turn_id, "message_id": message_id, "turn_index": safe_turn_index, "trigger_source": trigger_source, "event_type": payload.get("event_type") or payload.get("source") or "auto_update", "latest_turn": latest_turn, "history": history, "table_ids": table_ids, "dry_run": bool(payload.get("dry_run", False)), "user_hash": payload.get("user_hash"), "assistant_hash": payload.get("assistant_hash")},
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "raw_output": raw_output,
        "repair_output": repair_output if repair_used or repair_error else "",
        "repair_used": repair_used,
        "repair_error": repair_error,
        "parse_error": parse_error,
        "parsed": parsed,
        "updates": updates,
        "display": display_payload,
        "result": result,
        "error_type": worker_error_type,
    }
    if config.get("debug_enabled", True):
        save_worker_log(log_payload)
    summary = build_update_summary(result, tables)
    has_errors = bool(result.get("errors"))
    ok = not has_errors or bool(result.get("applied"))
    return {
        "ok": ok,
        "status": "error" if has_errors and not result.get("applied") else summary.get("status"),
        "error_type": worker_error_type,
        "message": (result.get("errors") or [summary.get("message")])[0] if has_errors and not result.get("applied") else summary.get("message"),
        "summary": summary,
        "updates": updates,
        "turn_id": turn_id,
        "message_id": message_id,
        "turn_index": safe_turn_index,
        "trigger_source": trigger_source,
        "repair_used": repair_used,
        "display": display_payload if config.get("mujian_enabled", True) and ok else {},
        "result": result,
        "raw_output": raw_output if config.get("debug_enabled") else "",
    }
