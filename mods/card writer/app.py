from __future__ import annotations

import copy
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote
from uuid import uuid4

import hashlib
import httpx

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
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

DATA_DIR = PROJECT_ROOT / "data" / "card_writer"
PROJECTS_DIR = DATA_DIR / "projects"
EXPORTS_DIR = DATA_DIR / "exports"
AUTOSAVES_DIR = DATA_DIR / "autosaves"
SETTINGS_PATH = DATA_DIR / "settings.json"
WORKSPACE_PATH = DATA_DIR / "workspace.cardwork.json"

STATIC_DIR = RESOURCE_DIR / "static"
TEMPLATES_DIR = RESOURCE_DIR / "templates"

FILENAME_RE = re.compile(r'[\\/:*?"<>|]')
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
AUTOSAVE_FILENAME = "autosave.cardwork.json"
PROJECT_TYPE = "fantareal_card_writer_project"
AUTHOR_PATTERNS = ["这是一个角色卡", "角色介绍", "设定如下", "以下是角色"]
LLM_BASE_URL_ENV = "LLM_BASE_URL"
LLM_API_KEY_ENV = "LLM_API_KEY"
LLM_MODEL_ENV = "LLM_MODEL"
LLM_TIMEOUT_ENV = "LLM_REQUEST_TIMEOUT"
DEFAULT_LLM_TIMEOUT = 120
DEFAULT_LLM_TEMPERATURE = 0.8

PERSONA_FIELDS = [
    "name",
    "description",
    "personality",
    "first_mes",
    "mes_example",
    "scenario",
    "creator_notes",
]

PLOT_STAGE_DEFAULT = {
    "description": "",
    "rules": "",
}

PERSONA_SINGLE_DEFAULT = {
    "name": "",
    "description": "",
    "personality": "",
    "scenario": "",
    "creator_notes": "",
}

WORKSHOP_ITEM_DEFAULT = {
    "id": "",
    "name": "",
    "enabled": True,
    "triggerMode": "manual",
    "triggerStage": "",
    "triggerTempMin": 0,
    "triggerTempMax": 1,
    "actionType": "note",
    "popupTitle": "",
    "musicPreset": "",
    "musicUrl": "",
    "autoplay": False,
    "loop": False,
    "volume": 0.7,
    "imageUrl": "",
    "imageAlt": "",
    "note": "",
}

PERSONA_CARD_DEFAULTS = {
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
        "items": [],
    },
    "plotStages": {},
    "personas": {"1": copy.deepcopy(PERSONA_SINGLE_DEFAULT)},
}

WORLDBOOK_SETTINGS_DEFAULTS = {
    "enabled": True,
    "debug_enabled": False,
    "max_hits": 10,
    "default_case_sensitive": False,
    "default_whole_word": False,
    "default_match_mode": "includes",
    "default_secondary_mode": "includes",
    "default_entry_type": "lore",
    "default_group_operator": "and",
    "default_chance": 100,
    "default_sticky_turns": 0,
    "default_cooldown_turns": 0,
    "default_insertion_position": "after_system",
    "default_injection_depth": 0,
    "default_injection_role": "system",
    "default_injection_order": 100,
    "default_prompt_layer": "default",
    "recursive_scan_enabled": False,
    "recursion_max_depth": 3,
}

WORLDBOOK_ENTRY_DEFAULT = {
    "id": "",
    "title": "",
    "trigger": "",
    "secondary_trigger": "",
    "entry_type": "lore",
    "group_operator": "and",
    "match_mode": "includes",
    "secondary_mode": "includes",
    "content": "",
    "group": "",
    "chance": 100,
    "sticky_turns": 0,
    "cooldown_turns": 0,
    "order": 0,
    "priority": 0,
    "insertion_position": "after_system",
    "injection_depth": 0,
    "injection_order": 100,
    "injection_role": "system",
    "prompt_layer": "default",
    "recursive_enabled": False,
    "prevent_further_recursion": False,
    "enabled": True,
    "case_sensitive": False,
    "whole_word": False,
    "comment": "",
}

MEMORY_ITEM_DEFAULT = {
    "id": "",
    "title": "",
    "content": "",
    "tags": [],
    "notes": "",
}

PRESET_MODULE_DEFAULTS = {
    "no_user_speaking": False,
    "short_paragraph": False,
    "long_paragraph": False,
    "second_person": False,
    "third_person": False,
    "anti_repeat": False,
    "no_closing_feel": False,
    "emotion_detail": False,
    "multi_character_boundary": False,
    "scene_continuation": False,
    "v4f_output_guard": False,
}

EXTRA_PROMPT_DEFAULT = {
    "id": "",
    "name": "",
    "enabled": True,
    "content": "",
    "order": 0,
}

PRESET_ITEM_DEFAULT = {
    "id": "",
    "name": "",
    "enabled": True,
    "base_system_prompt": "",
    "modules": copy.deepcopy(PRESET_MODULE_DEFAULTS),
    "extra_prompts": [],
    "prompt_groups": [],
}

NEW_PROJECT_DEFAULTS = {
    "version": 3,
    "type": PROJECT_TYPE,
    "title": "",
    "persona_card": copy.deepcopy(PERSONA_CARD_DEFAULTS),
    "worldbook": {
        "settings": copy.deepcopy(WORLDBOOK_SETTINGS_DEFAULTS),
        "entries": [],
    },
    "memory": {
        "items": [],
    },
    "preset": {
        "active_preset_id": "",
        "presets": [],
    },
    "updated_at": "",
}

DEFAULT_PERSONA_PROMPT = """
你要为 Card Writer 生成人设卡草稿，输出内容必须可直接写入编辑器表单。
重点要求：
1. 角色身份、关系、行为习惯要清楚，避免空泛形容词堆砌。
2. personality 要稳定可执行，能直接指导后续对话语气与反应方式。
3. first_mes 必须像真实开场白，能直接发给用户，不要写说明文字。
4. mes_example 只写示例对话，不要代替 {{user}} 做过多决定。
5. creator_notes 只写隐藏约束、禁忌和稳定角色表现的规则，不写解释。
6. 如果是分身 persona，只生成当前分身所需字段，不扩写整张主卡。
""".strip()

DEFAULT_WORLDBOOK_PROMPT = """
你要为 Card Writer 生成单条世界书词条，输出必须适合直接落入当前 entry。
重点要求：
1. 一次只写一个词条，不要把多个设定混成一个 entry。
2. trigger 要便于触发，尽量是角色、地点、组织、事件等关键词。
3. content 要写成可注入上下文的设定正文，避免闲聊口吻。
4. 注入位置、提示层、触发方式要和词条用途一致。
5. comment 只写维护备注，不重复正文。
""".strip()

DEFAULT_PRESET_PROMPT = """
你要为 Card Writer 生成单个聊天预设，输出必须能直接成为可用 preset。
重点要求：
1. base_system_prompt 要具体、可执行，能直接约束模型说话方式。
2. modules 只开启真正需要的开关，避免互相冲突。
3. extra_prompts 要补充 base_system_prompt，而不是重复口号。
4. prompt_groups 若无明确需求可保持精简，不要虚构复杂结构。
5. 整体目标是让语气、边界、叙事方式稳定一致。
""".strip()

DEFAULT_MEMORY_PROMPT = """
你要为 Card Writer 生成单条记忆，输出必须适合直接写入 memory item。
重点要求：
1. content 聚焦单个事实、事件、关系或长期偏好，不写散乱总结。
2. title 要短而明确，能快速说明这条记忆的主题。
3. tags 保持精简，便于检索，不要堆很多同义词。
4. notes 只写维护信息、时间线提醒或补充说明，不重复正文。
5. 每条记忆应当独立成立，便于后续单独删改。
""".strip()

DEFAULT_COPILOT_SETTINGS = {
    "base_url": "",
    "api_key": "",
    "model": "",
    "request_timeout": DEFAULT_LLM_TIMEOUT,
    "temperature": DEFAULT_LLM_TEMPERATURE,
    "base_system_prompt": "你是缃笺 Card Writer 的结构化写作助手。",
    "persona_prompt": DEFAULT_PERSONA_PROMPT,
    "worldbook_prompt": DEFAULT_WORLDBOOK_PROMPT,
    "preset_prompt": DEFAULT_PRESET_PROMPT,
    "memory_prompt": DEFAULT_MEMORY_PROMPT,
}


class CardWriterProject(BaseModel):
    version: int = 3
    type: str = PROJECT_TYPE
    title: str = ""
    persona_card: dict[str, Any] = Field(default_factory=dict)
    worldbook: dict[str, Any] = Field(default_factory=dict)
    memory: dict[str, Any] = Field(default_factory=dict)
    preset: dict[str, Any] = Field(default_factory=dict)
    updated_at: str = ""


class ExportPayload(BaseModel):
    project: CardWriterProject = Field(default_factory=CardWriterProject)
    filename: str = ""
    target: str = "persona"


class CopilotSettingsPayload(BaseModel):
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    request_timeout: int = Field(default=DEFAULT_LLM_TIMEOUT)
    temperature: float = Field(default=DEFAULT_LLM_TEMPERATURE)
    base_system_prompt: str = ""
    persona_prompt: str = ""
    worldbook_prompt: str = ""
    preset_prompt: str = ""
    memory_prompt: str = ""


class CopilotGeneratePayload(BaseModel):
    project: CardWriterProject = Field(default_factory=CardWriterProject)
    module: str = "persona"
    prompt: str = ""
    follow_up: str = ""
    current_view: str = "persona"
    focus_hint: dict[str, Any] = Field(default_factory=dict)
    project_revision: str = ""


class CopilotGenerateResponse(BaseModel):
    ok: bool = True
    review_id: str = ""
    summary: str = ""
    prompt_used: str = ""
    current_view: str = "persona"
    base_revision: str = ""
    focus_hint: dict[str, Any] = Field(default_factory=dict)
    candidates: list[dict[str, Any]] = Field(default_factory=list)


CardWriterProject.model_rebuild()
ExportPayload.model_rebuild()
CopilotSettingsPayload.model_rebuild()
CopilotGeneratePayload.model_rebuild()
CopilotGenerateResponse.model_rebuild()


class ProjectStore:
    def __init__(self, projects_dir: Path, autosaves_dir: Path, exports_dir: Path, workspace_path: Path) -> None:
        self.projects_dir = projects_dir
        self.autosaves_dir = autosaves_dir
        self.exports_dir = exports_dir
        self.workspace_path = workspace_path

    def ensure_dirs(self) -> None:
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.autosaves_dir.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.workspace_path.parent.mkdir(parents=True, exist_ok=True)

    def list_projects(self) -> list[dict[str, Any]]:
        projects: list[dict[str, Any]] = []
        if not self.projects_dir.exists():
            return projects
        for path in sorted(self.projects_dir.glob("*.cardwork.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            data = read_json(path, {})
            normalized = normalize_project(data)
            projects.append({
                "filename": path.name,
                "title": normalized.get("title") or path.stem.replace(".cardwork", ""),
                "updated_at": normalized.get("updated_at", ""),
            })
        return projects

    def load_project(self, filename: str) -> dict[str, Any]:
        path = self.projects_dir / sanitize_filename(filename)
        if not path.exists():
            raise HTTPException(status_code=404, detail="工程文件不存在。")
        data = read_json(path, None)
        if data is None:
            raise HTTPException(status_code=400, detail="无法解析工程文件。")
        return normalize_project(data)

    def save_project(self, filename: str, project: dict[str, Any]) -> dict[str, Any]:
        safe = ensure_project_filename(filename)
        normalized = normalize_project(project)
        normalized["updated_at"] = now_text()
        write_json(self.projects_dir / safe, normalized)
        return {"ok": True, "filename": safe, "updated_at": normalized["updated_at"]}

    def delete_project(self, filename: str) -> None:
        path = self.projects_dir / sanitize_filename(filename)
        if path.exists():
            path.unlink()

    def load_autosave(self) -> dict[str, Any]:
        if self.workspace_path.exists():
            data = read_json(self.workspace_path, None)
            if data is not None:
                return normalize_project(data)
        path = self.autosaves_dir / AUTOSAVE_FILENAME
        if not path.exists():
            raise HTTPException(status_code=404, detail="没有自动保存。")
        data = read_json(path, None)
        if data is None:
            raise HTTPException(status_code=400, detail="无法解析自动保存。")
        return normalize_project(data)

    def save_autosave(self, project: dict[str, Any]) -> dict[str, Any]:
        normalized = normalize_project(project)
        normalized["updated_at"] = now_text()
        write_json(self.autosaves_dir / AUTOSAVE_FILENAME, normalized)
        write_json(self.workspace_path, normalized)
        return {"ok": True, "updated_at": normalized["updated_at"]}

    def load_workspace(self) -> dict[str, Any]:
        data = read_json(self.workspace_path, None)
        if data is None:
            return create_empty_project()
        return normalize_project(data)

    def save_workspace(self, project: dict[str, Any]) -> dict[str, Any]:
        normalized = normalize_project(project)
        normalized["updated_at"] = now_text()
        write_json(self.workspace_path, normalized)
        return {"ok": True, "updated_at": normalized["updated_at"]}

    def clear_workspace(self) -> dict[str, Any]:
        empty = create_empty_project()
        write_json(self.workspace_path, empty)
        return {"ok": True}

    def export_json(self, filename: str, payload: dict[str, Any]) -> dict[str, Any]:
        raw_name = filename.strip() or "untitled"
        safe = ensure_export_filename(raw_name)
        write_json(self.exports_dir / safe, payload)
        return {"ok": True, "filename": safe, "payload": payload}


class CardCompiler:
    def compile(self, project: dict[str, Any]) -> dict[str, Any]:
        normalized = normalize_project(project)
        card = copy.deepcopy(normalized["persona_card"])
        card["tags"] = split_tags(card.get("tags", []))
        card["creativeWorkshop"] = normalize_creative_workshop(card.get("creativeWorkshop"))
        card["plotStages"] = normalize_plot_stage_map(card.get("plotStages"))
        card["personas"] = normalize_personas_map(card.get("personas"))
        return card

    def generate_copilot_draft(self, payload: CopilotGeneratePayload) -> CopilotGenerateResponse:
        prompt_text = build_copilot_prompt_text(payload.prompt, payload.follow_up)
        if not prompt_text:
            raise HTTPException(status_code=400, detail="请输入想让 AI 处理的内容。")
        project = normalize_project(payload.project.model_dump())
        current_view = normalize_copilot_view(payload.current_view)
        focus_hint = normalize_copilot_focus_hint(payload.focus_hint, project, current_view)
        base_revision = build_project_revision(project)
        review = request_copilot_review(
            prompt_text=prompt_text,
            current_view=current_view,
            focus_hint=focus_hint,
            project=project,
            project_revision=base_revision,
        )
        candidates = normalize_copilot_candidates(review.get("candidates"), project)
        summary = normalize_text(review.get("summary")) or build_copilot_review_summary(candidates, current_view)
        return CopilotGenerateResponse(
            ok=True,
            review_id=make_id("review"),
            summary=summary,
            prompt_used=prompt_text,
            current_view=current_view,
            base_revision=base_revision,
            focus_hint=focus_hint,
            candidates=candidates,
        )

    def export_payload(self, project: dict[str, Any], target: str) -> dict[str, Any]:
        normalized = normalize_project(project)
        export_target = str(target or "persona").strip().lower()
        if export_target == "persona":
            return self.compile(normalized)
        if export_target == "worldbook":
            return copy.deepcopy(normalized["worldbook"])
        if export_target == "preset":
            return copy.deepcopy(normalized["preset"])
        if export_target == "memory":
            return copy.deepcopy(normalized["memory"])
        raise HTTPException(status_code=400, detail="不支持的导出类型。")

    def validate(self, project: dict[str, Any], card: dict[str, Any]) -> list[dict[str, Any]]:
        warnings: list[dict[str, Any]] = []
        if not str(card.get("name", "")).strip():
            warnings.append({"level": "error", "field": "name", "message": "角色名不能为空。"})
        if not str(card.get("first_mes", "")).strip():
            warnings.append({"level": "error", "field": "first_mes", "message": "开场白不能为空。"})
        if not isinstance(card.get("tags"), list):
            warnings.append({"level": "error", "field": "tags", "message": "标签必须是数组。"})

        if len(str(card.get("personality", ""))) < 10:
            warnings.append({"level": "warning", "field": "personality", "message": "性格口吻较短，角色表现可能不稳定。"})
        if not str(card.get("mes_example", "")).strip():
            warnings.append({"level": "warning", "field": "mes_example", "message": "示例对话为空。"})
        if not str(card.get("creator_notes", "")).strip():
            warnings.append({"level": "warning", "field": "creator_notes", "message": "隐藏规则为空。"})

        first_mes = str(card.get("first_mes", ""))
        for pattern in AUTHOR_PATTERNS:
            if pattern in first_mes:
                warnings.append({"level": "warning", "field": "first_mes", "message": f"开场白可能像作者说明（检测到「{pattern}」）。"})
                break

        if not normalized_has_content(project):
            warnings.append({"level": "warning", "field": "project", "message": "当前工程内容几乎为空。"})
        return warnings

    def import_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return project_from_payload(payload)


def now_text() -> str:
    return datetime.now().strftime(TIMESTAMP_FORMAT)


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


def clamp_float(value: Any, minimum: float, maximum: float, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def sanitize_copilot_settings(raw: Any) -> dict[str, Any]:
    data = copy.deepcopy(DEFAULT_COPILOT_SETTINGS)
    if not isinstance(raw, dict):
        return data
    data["base_url"] = normalize_text(raw.get("base_url"))
    data["api_key"] = normalize_text(raw.get("api_key"))
    data["model"] = normalize_text(raw.get("model"))
    data["request_timeout"] = as_int(raw.get("request_timeout"), DEFAULT_LLM_TIMEOUT)
    data["request_timeout"] = max(10, min(3600, data["request_timeout"]))
    data["temperature"] = clamp_float(raw.get("temperature"), 0.0, 2.0, DEFAULT_LLM_TEMPERATURE)
    data["base_system_prompt"] = normalize_text(raw.get("base_system_prompt")) or DEFAULT_COPILOT_SETTINGS["base_system_prompt"]
    data["persona_prompt"] = normalize_text(raw.get("persona_prompt")) or DEFAULT_COPILOT_SETTINGS["persona_prompt"]
    data["worldbook_prompt"] = normalize_text(raw.get("worldbook_prompt")) or DEFAULT_COPILOT_SETTINGS["worldbook_prompt"]
    data["preset_prompt"] = normalize_text(raw.get("preset_prompt")) or DEFAULT_COPILOT_SETTINGS["preset_prompt"]
    data["memory_prompt"] = normalize_text(raw.get("memory_prompt")) or DEFAULT_COPILOT_SETTINGS["memory_prompt"]
    return data


def get_copilot_settings() -> dict[str, Any]:
    return sanitize_copilot_settings(read_json(SETTINGS_PATH, DEFAULT_COPILOT_SETTINGS))


def save_copilot_settings(payload: Any) -> dict[str, Any]:
    settings = sanitize_copilot_settings(payload)
    write_json(SETTINGS_PATH, settings)
    return settings


def sanitize_filename(name: str) -> str:
    return FILENAME_RE.sub("_", str(name or "")).strip()


def ensure_project_filename(name: str) -> str:
    safe = sanitize_filename(name) or "untitled"
    return safe if safe.endswith(".cardwork.json") else f"{safe}.cardwork.json"


def ensure_export_filename(name: str) -> str:
    safe = sanitize_filename(name) or "untitled"
    return safe if safe.endswith(".json") else f"{safe}.json"


def make_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:8]}"


def create_empty_project() -> dict[str, Any]:
    return copy.deepcopy(NEW_PROJECT_DEFAULTS)


def split_tags(value: str | list[Any]) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in re.split(r"[、，,]", str(value or "")) if item.strip()]


def as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off", ""}:
        return False
    return default


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_text(value: Any) -> str:
    return str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def normalize_stage_item(key: str, stage: Any) -> dict[str, Any]:
    raw = stage if isinstance(stage, dict) else {}
    label = normalize_text(raw.get("label", "")) or key
    return {
        "label": label,
        "description": normalize_text(raw.get("description", "")),
        "rules": normalize_text(raw.get("rules", "")),
    }


def normalize_plot_stage_map(value: Any) -> dict[str, dict[str, Any]]:
    if isinstance(value, dict):
        items = value.items()
    elif isinstance(value, list):
        items = ((str(item.get("id") or item.get("label") or chr(ord("A") + index)).strip().upper(), item) for index, item in enumerate(value) if isinstance(item, dict))
    else:
        items = []
    result: dict[str, dict[str, Any]] = {}
    for key, item in items:
        stage_key = str(key or "").strip().upper() or "A"
        result[stage_key] = normalize_stage_item(stage_key, item)
    return result


def normalize_persona_single(value: Any) -> dict[str, Any]:
    raw = value if isinstance(value, dict) else {}
    result = copy.deepcopy(PERSONA_SINGLE_DEFAULT)
    for key in result.keys():
        result[key] = normalize_text(raw.get(key, ""))
    return result


def normalize_personas_map(value: Any) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    if isinstance(value, dict):
        for key, item in value.items():
            result[str(key or "1").strip() or "1"] = normalize_persona_single(item)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            if not isinstance(item, dict):
                continue
            key = str(item.get("id") or index + 1).strip() or str(index + 1)
            result[key] = normalize_persona_single(item)
    if not result:
        result["1"] = copy.deepcopy(PERSONA_SINGLE_DEFAULT)
    return result


def normalize_workshop_item(item: Any, index: int) -> dict[str, Any]:
    raw = item if isinstance(item, dict) else {}
    data = copy.deepcopy(WORKSHOP_ITEM_DEFAULT)
    data["id"] = normalize_text(raw.get("id")) or make_id("workshop")
    data["name"] = normalize_text(raw.get("name"))
    data["enabled"] = as_bool(raw.get("enabled"), True)
    data["triggerMode"] = normalize_text(raw.get("triggerMode")) or WORKSHOP_ITEM_DEFAULT["triggerMode"]
    data["triggerStage"] = normalize_text(raw.get("triggerStage"))
    data["triggerTempMin"] = as_int(raw.get("triggerTempMin"), WORKSHOP_ITEM_DEFAULT["triggerTempMin"])
    data["triggerTempMax"] = as_int(raw.get("triggerTempMax"), WORKSHOP_ITEM_DEFAULT["triggerTempMax"])
    data["actionType"] = normalize_text(raw.get("actionType")) or WORKSHOP_ITEM_DEFAULT["actionType"]
    data["popupTitle"] = normalize_text(raw.get("popupTitle"))
    data["musicPreset"] = normalize_text(raw.get("musicPreset"))
    data["musicUrl"] = normalize_text(raw.get("musicUrl"))
    data["autoplay"] = as_bool(raw.get("autoplay"), False)
    data["loop"] = as_bool(raw.get("loop"), False)
    data["volume"] = as_float(raw.get("volume"), WORKSHOP_ITEM_DEFAULT["volume"])
    data["imageUrl"] = normalize_text(raw.get("imageUrl"))
    data["imageAlt"] = normalize_text(raw.get("imageAlt"))
    data["note"] = normalize_text(raw.get("note"))
    return data


def normalize_creative_workshop(value: Any) -> dict[str, Any]:
    raw = value if isinstance(value, dict) else {}
    items = raw.get("items") if isinstance(raw.get("items"), list) else []
    return {
        "enabled": as_bool(raw.get("enabled"), True),
        "items": [normalize_workshop_item(item, index) for index, item in enumerate(items)],
    }


def normalize_persona_card(value: Any) -> dict[str, Any]:
    raw = value if isinstance(value, dict) else {}
    data = copy.deepcopy(PERSONA_CARD_DEFAULTS)
    for key in PERSONA_FIELDS:
        data[key] = normalize_text(raw.get(key, data[key]))
    data["tags"] = split_tags(raw.get("tags", []))
    data["creativeWorkshop"] = normalize_creative_workshop(raw.get("creativeWorkshop"))
    data["plotStages"] = normalize_plot_stage_map(raw.get("plotStages"))
    data["personas"] = normalize_personas_map(raw.get("personas"))
    return data


def normalize_copilot_view(value: Any) -> str:
    view_name = str(value or "persona").strip().lower()
    if view_name not in {"persona", "worldbook", "preset", "memory", "preview"}:
        return "persona"
    return view_name


def build_project_revision(project: dict[str, Any]) -> str:
    serialized = json.dumps(normalize_project(project), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(serialized.encode("utf-8")).hexdigest()


def normalize_copilot_focus_hint(raw: Any, project: dict[str, Any], current_view: str) -> dict[str, Any]:
    hint = raw if isinstance(raw, dict) else {}
    normalized: dict[str, Any] = {
        "view": current_view,
        "title": "",
        "subtitle": "",
        "module": current_view if current_view in {"persona", "worldbook", "preset", "memory"} else "persona",
        "persona_key": "",
        "worldbook_id": "",
        "preset_id": "",
        "memory_id": "",
    }
    for key in ["title", "subtitle", "module", "persona_key", "worldbook_id", "preset_id", "memory_id"]:
        if key in hint:
            normalized[key] = normalize_text(hint.get(key))

    if current_view == "persona":
        persona_key = normalized["persona_key"]
        personas = (project.get("persona_card") or {}).get("personas", {})
        if persona_key and persona_key in personas:
            persona = personas[persona_key]
            normalized["title"] = normalized["title"] or f"当前浏览：分身 · {persona.get('name') or persona_key}"
            normalized["subtitle"] = normalized["subtitle"] or f"焦点提示：personas.{persona_key}"
        else:
            normalized["persona_key"] = ""
            normalized["title"] = normalized["title"] or "当前浏览：角色主体"
            normalized["subtitle"] = normalized["subtitle"] or "焦点提示：persona_card 主字段"
    elif current_view == "worldbook":
        worldbook_id = normalized["worldbook_id"]
        entries = (project.get("worldbook") or {}).get("entries", [])
        current = next((item for item in entries if normalize_text(item.get("id")) == worldbook_id), None)
        normalized["title"] = normalized["title"] or f"当前浏览：世界书 · {current.get('title') if current else '词条'}"
        normalized["subtitle"] = normalized["subtitle"] or "焦点提示仅用于帮助 AI 理解你此刻在看哪里，不限制修改范围。"
    elif current_view == "preset":
        preset_id = normalized["preset_id"]
        presets = (project.get("preset") or {}).get("presets", [])
        current = next((item for item in presets if normalize_text(item.get("id")) == preset_id), None)
        normalized["title"] = normalized["title"] or f"当前浏览：预设 · {current.get('name') if current else '预设'}"
        normalized["subtitle"] = normalized["subtitle"] or "焦点提示仅用于帮助 AI 理解你此刻在看哪里，不限制修改范围。"
    elif current_view == "memory":
        memory_id = normalized["memory_id"]
        items = (project.get("memory") or {}).get("items", [])
        current = next((item for item in items if normalize_text(item.get("id")) == memory_id), None)
        normalized["title"] = normalized["title"] or f"当前浏览：记忆 · {current.get('title') if current else '记忆'}"
        normalized["subtitle"] = normalized["subtitle"] or "焦点提示仅用于帮助 AI 理解你此刻在看哪里，不限制修改范围。"
    else:
        normalized["title"] = normalized["title"] or "当前浏览：预览"
        normalized["subtitle"] = normalized["subtitle"] or "AI 将分析整张卡内容并返回候选修改。"
    return normalized


def build_copilot_prompt_text(prompt: Any, follow_up: Any) -> str:
    base = normalize_text(prompt)
    extra = normalize_text(follow_up)
    if base and extra:
        return f"{base}\n\n补充要求：{extra}"
    return base or extra


def get_runtime_llm_config() -> dict[str, Any]:
    settings = get_copilot_settings()
    env_base_url = normalize_text(os.getenv(LLM_BASE_URL_ENV, ""))
    env_api_key = normalize_text(os.getenv(LLM_API_KEY_ENV, ""))
    env_model = normalize_text(os.getenv(LLM_MODEL_ENV, ""))
    timeout_raw = normalize_text(os.getenv(LLM_TIMEOUT_ENV, ""))
    try:
        env_timeout = int(timeout_raw) if timeout_raw else DEFAULT_LLM_TIMEOUT
    except ValueError:
        env_timeout = DEFAULT_LLM_TIMEOUT
    return {
        "base_url": normalize_text(settings.get("base_url")) or env_base_url.rstrip("/"),
        "api_key": normalize_text(settings.get("api_key")) or env_api_key,
        "model": normalize_text(settings.get("model")) or env_model,
        "request_timeout": max(as_int(settings.get("request_timeout"), env_timeout), 1),
        "temperature": clamp_float(settings.get("temperature"), 0.0, 2.0, DEFAULT_LLM_TEMPERATURE),
    }


def request_copilot_review(
    *,
    prompt_text: str,
    current_view: str,
    focus_hint: dict[str, Any],
    project: dict[str, Any],
    project_revision: str,
) -> dict[str, Any]:
    config = get_runtime_llm_config()
    if config["base_url"] and config["model"]:
        return call_copilot_llm(
            prompt_text=prompt_text,
            current_view=current_view,
            focus_hint=focus_hint,
            project=project,
            project_revision=project_revision,
            config=config,
        )
    return generate_copilot_fallback(prompt_text, current_view, focus_hint, project)


def build_copilot_candidate(
    *,
    module: str,
    action: str,
    label: str,
    reason: str,
    target: dict[str, Any],
    before: Any,
    after: Any,
) -> dict[str, Any]:
    normalized_before = copy.deepcopy(before)
    normalized_after = copy.deepcopy(after)
    fingerprint = build_copilot_fingerprint(module, action, target, normalized_before)
    return {
        "id": make_id("candidate"),
        "module": module,
        "action": action,
        "label": normalize_text(label) or "未命名修改",
        "reason": normalize_text(reason),
        "target": normalize_copilot_target_ref(module, action, target),
        "before": normalized_before,
        "after": normalized_after,
        "fingerprint": fingerprint,
    }


def build_copilot_fingerprint(module: str, action: str, target: dict[str, Any], before: Any) -> str:
    payload = {
        "module": module,
        "action": action,
        "target": normalize_copilot_target_ref(module, action, target),
        "before": before,
    }
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(serialized.encode("utf-8")).hexdigest()


def normalize_copilot_target_ref(module: str, action: str, raw: Any) -> dict[str, Any]:
    target = raw if isinstance(raw, dict) else {}
    normalized: dict[str, Any] = {"module": module, "action": action}
    for key in ["path", "persona_key", "id", "field", "operation"]:
        value = normalize_text(target.get(key))
        if value:
            normalized[key] = value
    if "index" in target:
        normalized["index"] = as_int(target.get("index"), 0)
    return normalized


def get_persona_main_snapshot(project: dict[str, Any]) -> dict[str, Any]:
    persona_card = project.get("persona_card") or {}
    return {key: copy.deepcopy(persona_card.get(key)) for key in PERSONA_FIELDS + ["tags"]}


def find_worldbook_entry(project: dict[str, Any], entry_id: str) -> tuple[int, dict[str, Any] | None]:
    entries = (project.get("worldbook") or {}).get("entries", [])
    for index, item in enumerate(entries):
        if normalize_text(item.get("id")) == entry_id:
            return index, item
    return -1, None


def find_memory_item(project: dict[str, Any], item_id: str) -> tuple[int, dict[str, Any] | None]:
    items = (project.get("memory") or {}).get("items", [])
    for index, item in enumerate(items):
        if normalize_text(item.get("id")) == item_id:
            return index, item
    return -1, None


def find_preset_item(project: dict[str, Any], item_id: str) -> tuple[int, dict[str, Any] | None]:
    items = (project.get("preset") or {}).get("presets", [])
    for index, item in enumerate(items):
        if normalize_text(item.get("id")) == item_id:
            return index, item
    return -1, None


def build_default_candidate_target(module_name: str, project: dict[str, Any], current_view: str, focus_hint: dict[str, Any]) -> dict[str, Any]:
    if module_name == "persona":
        persona_key = normalize_text(focus_hint.get("persona_key"))
        personas = (project.get("persona_card") or {}).get("personas", {})
        if persona_key and persona_key in personas:
            return {"persona_key": persona_key}
        return {"path": "persona_card"}
    if module_name == "worldbook":
        worldbook_id = normalize_text(focus_hint.get("worldbook_id"))
        if worldbook_id:
            return {"id": worldbook_id}
        entries = (project.get("worldbook") or {}).get("entries", [])
        return {"id": normalize_text(entries[0].get("id"))} if entries else {"id": ""}
    if module_name == "preset":
        preset_id = normalize_text(focus_hint.get("preset_id"))
        if preset_id:
            return {"id": preset_id}
        items = (project.get("preset") or {}).get("presets", [])
        return {"id": normalize_text(items[0].get("id"))} if items else {"id": ""}
    memory_id = normalize_text(focus_hint.get("memory_id"))
    if memory_id:
        return {"id": memory_id}
    items = (project.get("memory") or {}).get("items", [])
    return {"id": normalize_text(items[0].get("id"))} if items else {"id": ""}


def build_default_candidate_reason(module_name: str, current_view: str) -> str:
    if module_name == current_view:
        return "根据当前视图与你的要求整理出的优先修改。"
    return "这是为了满足你的整体要求而联动调整的相关模块。"


def normalize_candidate_action(module_name: str, action: Any) -> str:
    action_name = str(action or "").strip().lower()
    allowed = {
        "persona": {"replace_field", "update_array_item", "json_patch"},
        "worldbook": {"update_array_item", "append_array_item", "json_patch"},
        "preset": {"update_array_item", "append_array_item", "json_patch"},
        "memory": {"update_array_item", "append_array_item", "json_patch"},
    }
    if action_name in allowed.get(module_name, set()):
        return action_name
    return "replace_field" if module_name == "persona" else "update_array_item"


def normalize_copilot_candidates(raw_candidates: Any, project: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(raw_candidates, list):
        return []
    result: list[dict[str, Any]] = []
    for item in raw_candidates:
        normalized_items = normalize_single_copilot_candidate(item, project)
        if isinstance(normalized_items, list):
            result.extend([candidate for candidate in normalized_items if candidate])
        elif normalized_items:
            result.append(normalized_items)
    return result


def get_project_path_value(project: dict[str, Any], path: str) -> Any:
    if not path:
        return None
    ref: Any = project
    for part in path.split("."):
        if isinstance(ref, dict):
            if part not in ref:
                return None
            ref = ref.get(part)
        elif isinstance(ref, list) and part.isdigit():
            index = int(part)
            if index < 0 or index >= len(ref):
                return None
            ref = ref[index]
        else:
            return None
    return copy.deepcopy(ref)


def is_allowed_json_patch_path(path: str) -> bool:
    if not path or ".." in path:
        return False
    parts = path.split(".")
    if not parts or parts[0] not in {"persona_card", "worldbook", "preset", "memory"}:
        return False
    blocked = {"version", "type", "updated_at"}
    return not any(part in blocked for part in parts)


def should_keep_patch_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value)
    if isinstance(value, dict):
        return any(should_keep_patch_value(item) for item in value.values())
    return True


def build_json_patch_candidate(module_name: str, path: str, operation: str, before: Any, after: Any, label: str, reason: str) -> dict[str, Any] | None:
    if operation != "delete" and not should_keep_patch_value(after):
        return None
    return build_copilot_candidate(
        module=module_name,
        action="json_patch",
        label=label,
        reason=reason or "根据 JSON 路径精确修改对应键。",
        target={"path": path, "operation": operation},
        before=before,
        after=None if operation == "delete" else copy.deepcopy(after),
    )


def persona_replace_to_json_patch_candidates(raw: dict[str, Any], project: dict[str, Any], label: str, reason: str) -> list[dict[str, Any]]:
    after_raw = raw.get("after") if isinstance(raw.get("after"), dict) else {}
    before_raw = raw.get("before") if isinstance(raw.get("before"), dict) else {}
    normalized_after = normalize_persona_card({**copy.deepcopy(project.get("persona_card") or {}), **after_raw})
    result: list[dict[str, Any]] = []
    for key in PERSONA_FIELDS + ["tags"]:
        if key not in after_raw:
            continue
        after_value = copy.deepcopy(normalized_after.get(key))
        before_value = before_raw.get(key) if key in before_raw else get_project_path_value(project, f"persona_card.{key}")
        candidate = build_json_patch_candidate(
            "persona",
            f"persona_card.{key}",
            "set",
            before_value,
            after_value,
            label or f"填充 persona_card.{key}",
            reason or "按人设卡 JSON 键填充对应字段。",
        )
        if candidate:
            result.append(candidate)
    return result


def normalize_json_patch_candidate(raw: dict[str, Any], project: dict[str, Any], module_name: str, label: str, reason: str) -> dict[str, Any] | None:
    target = raw.get("target") if isinstance(raw.get("target"), dict) else {}
    path = normalize_text(target.get("path") or raw.get("path"))
    if not is_allowed_json_patch_path(path):
        return None
    operation = normalize_text(target.get("operation") or raw.get("operation") or "set").lower()
    if operation not in {"set", "delete", "append"}:
        operation = "set"
    before_value = get_project_path_value(project, path)
    after_value = copy.deepcopy(raw.get("after"))
    if operation == "delete":
        after_value = None
    return build_json_patch_candidate(
        module_name,
        path,
        operation,
        raw.get("before") if "before" in raw else before_value,
        after_value,
        label or f"{operation} · {path}",
        reason,
    )


def normalize_single_copilot_candidate(raw: Any, project: dict[str, Any]) -> dict[str, Any] | list[dict[str, Any]] | None:
    if not isinstance(raw, dict):
        return None
    module_name = str(raw.get("module") or "").strip().lower()
    if module_name not in {"persona", "worldbook", "preset", "memory"}:
        return None
    action = normalize_candidate_action(module_name, raw.get("action"))
    target = raw.get("target") if isinstance(raw.get("target"), dict) else {}
    label = normalize_text(raw.get("label"))
    reason = normalize_text(raw.get("reason"))
    if action == "json_patch":
        return normalize_json_patch_candidate(raw, project, module_name, label, reason)

    if module_name == "persona":
        if action != "replace_field":
            action = "replace_field"
        persona_key = normalize_text(target.get("persona_key"))
        if not persona_key:
            patch_candidates = persona_replace_to_json_patch_candidates(raw, project, label, reason)
            if patch_candidates:
                return patch_candidates
        if persona_key:
            personas = (project.get("persona_card") or {}).get("personas", {})
            current_item = personas.get(persona_key)
            if current_item is None:
                return None
            after_value = normalize_persona_single(raw.get("after"))
            before_value = normalize_persona_single(raw.get("before") or current_item)
            return build_copilot_candidate(
                module="persona",
                action=action,
                label=label or f"更新分身 · {after_value.get('name') or persona_key}",
                reason=reason or "根据你的要求调整分身设定。",
                target={"persona_key": persona_key},
                before=before_value,
                after=after_value,
            )
        after_value = normalize_persona_card({**copy.deepcopy(project.get("persona_card") or {}), **(raw.get("after") if isinstance(raw.get("after"), dict) else {})})
        before_value = get_persona_main_snapshot(project)
        after_main = {key: copy.deepcopy(after_value.get(key)) for key in PERSONA_FIELDS + ["tags"]}
        return build_copilot_candidate(
            module="persona",
            action=action,
            label=label or f"更新角色主体 · {after_main.get('name') or '主卡'}",
            reason=reason or "根据你的要求调整主卡字段。",
            target={"path": "persona_card"},
            before=raw.get("before") if isinstance(raw.get("before"), dict) else before_value,
            after=after_main,
        )

    if module_name == "worldbook":
        if action == "append_array_item":
            index = len((project.get("worldbook") or {}).get("entries", []))
            after_value = normalize_worldbook_entry(raw.get("after"), index)
            return build_copilot_candidate(
                module="worldbook",
                action=action,
                label=label or f"新增世界书 · {after_value.get('title') or '新词条'}",
                reason=reason or "根据你的要求补充新的世界书词条。",
                target={"id": normalize_text(after_value.get("id")), "index": index},
                before=None,
                after=after_value,
            )
        entry_id = normalize_text(target.get("id"))
        index, current_item = find_worldbook_entry(project, entry_id)
        if not current_item:
            return None
        after_value = normalize_worldbook_entry({**copy.deepcopy(current_item), **(raw.get("after") if isinstance(raw.get("after"), dict) else {})}, index)
        before_value = normalize_worldbook_entry(raw.get("before") or current_item, index)
        return build_copilot_candidate(
            module="worldbook",
            action="update_array_item",
            label=label or f"更新世界书 · {after_value.get('title') or entry_id}",
            reason=reason or "根据你的要求改写世界书词条。",
            target={"id": entry_id, "index": index},
            before=before_value,
            after=after_value,
        )

    if module_name == "preset":
        if action == "append_array_item":
            index = len((project.get("preset") or {}).get("presets", []))
            after_value = normalize_preset_item(raw.get("after"), index)
            return build_copilot_candidate(
                module="preset",
                action=action,
                label=label or f"新增预设 · {after_value.get('name') or '新预设'}",
                reason=reason or "根据你的要求补充新的预设。",
                target={"id": normalize_text(after_value.get("id")), "index": index},
                before=None,
                after=after_value,
            )
        item_id = normalize_text(target.get("id"))
        index, current_item = find_preset_item(project, item_id)
        if not current_item:
            return None
        after_value = normalize_preset_item({**copy.deepcopy(current_item), **(raw.get("after") if isinstance(raw.get("after"), dict) else {})}, index)
        before_value = normalize_preset_item(raw.get("before") or current_item, index)
        return build_copilot_candidate(
            module="preset",
            action="update_array_item",
            label=label or f"更新预设 · {after_value.get('name') or item_id}",
            reason=reason or "根据你的要求改写预设。",
            target={"id": item_id, "index": index},
            before=before_value,
            after=after_value,
        )

    if action == "append_array_item":
        index = len((project.get("memory") or {}).get("items", []))
        after_value = normalize_memory_item(raw.get("after"), index)
        return build_copilot_candidate(
            module="memory",
            action=action,
            label=label or f"新增记忆 · {after_value.get('title') or '新记忆'}",
            reason=reason or "根据你的要求补充新的记忆。",
            target={"id": normalize_text(after_value.get("id")), "index": index},
            before=None,
            after=after_value,
        )
    item_id = normalize_text(target.get("id"))
    index, current_item = find_memory_item(project, item_id)
    if not current_item:
        return None
    after_value = normalize_memory_item({**copy.deepcopy(current_item), **(raw.get("after") if isinstance(raw.get("after"), dict) else {})}, index)
    before_value = normalize_memory_item(raw.get("before") or current_item, index)
    return build_copilot_candidate(
        module="memory",
        action="update_array_item",
        label=label or f"更新记忆 · {after_value.get('title') or item_id}",
        reason=reason or "根据你的要求改写记忆。",
        target={"id": item_id, "index": index},
        before=before_value,
        after=after_value,
    )


def build_copilot_review_summary(candidates: list[dict[str, Any]], current_view: str) -> str:
    if not candidates:
        return "这次没有整理出可安全应用的候选修改。"
    module_labels = {"persona": "人设", "worldbook": "世界书", "preset": "预设", "memory": "记忆"}
    touched_modules = []
    for candidate in candidates:
        module_name = candidate.get("module")
        if module_name in module_labels and module_labels[module_name] not in touched_modules:
            touched_modules.append(module_labels[module_name])
    focus_label = module_labels.get(current_view, "当前卡")
    module_text = "、".join(touched_modules) if touched_modules else focus_label
    return f"已基于整张卡内容整理出 {len(candidates)} 条候选修改，涉及 {module_text}。"


def build_copilot_candidate_schema() -> dict[str, Any]:
    return {
        "summary": "string",
        "candidates": [
            {
                "module": "persona|worldbook|preset|memory",
                "action": "json_patch",
                "label": "string",
                "reason": "string",
                "target": {
                    "path": "persona_card.name|worldbook.entries.0.content|preset.presets.0.base_system_prompt|memory.items.0.content",
                    "operation": "set|delete|append"
                },
                "before": "current JSON value or null",
                "after": "final JSON value to set or append"
            }
        ]
    }


def build_card_writer_json_schema() -> dict[str, Any]:
    return {
        "persona_card": {
            "name": "string",
            "description": "string",
            "personality": "string",
            "scenario": "string",
            "first_mes": "string",
            "mes_example": "string",
            "creator_notes": "string",
            "tags": ["string"],
            "creativeWorkshop": {"enabled": True, "items": [WORKSHOP_ITEM_DEFAULT]},
            "plotStages": {"A": {"label": "string", "description": "string", "rules": "string"}},
            "personas": {"1": PERSONA_SINGLE_DEFAULT},
        },
        "worldbook": {"settings": WORLDBOOK_SETTINGS_DEFAULTS, "entries": [WORLDBOOK_ENTRY_DEFAULT]},
        "preset": {"active_preset_id": "string", "presets": [PRESET_ITEM_DEFAULT]},
        "memory": {"items": [MEMORY_ITEM_DEFAULT]},
    }


def truncate_preview_text(value: Any, limit: int) -> str:
    text = normalize_text(value)
    return text if len(text) <= limit else f"{text[:limit]}…"


def infer_persona_name(prompt_text: str) -> str:
    text = normalize_text(prompt_text)
    patterns = [
        r"生成\s*([^，。,.\s]+?)\s*的?人设卡",
        r"生成\s*([^，。,.\s]+?)\s*的?角色卡",
        r"生成\s*([^，。,.\s]+?)\s*的?人设",
        r"生成\s*([^，。,.\s]+?)\s*的?角色",
        r"(?:叫|名叫|名字叫)\s*([^，。,.\s]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            name = normalize_text(match.group(1))
            name = re.sub(r"^(一个|一位|一只|个|位|只)", "", name)
            name = re.sub(r"^(猫娘|病娇|女仆|妹妹|姐姐|吸血鬼|恶魔)+", "", name)
            if name:
                return name[:32]
    if "莉莉丝" in text:
        return "莉莉丝"
    return "新角色"


def infer_persona_tags(prompt_text: str, name: str) -> list[str]:
    text = normalize_text(prompt_text)
    tags: list[str] = []
    keyword_tags = [
        ("猫娘", "猫娘"),
        ("病娇", "病娇"),
        ("校园", "校园"),
        ("幻想", "幻想"),
        ("女仆", "女仆"),
        ("妹妹", "妹妹"),
        ("姐姐", "姐姐"),
        ("吸血鬼", "吸血鬼"),
        ("恶魔", "恶魔"),
    ]
    for keyword, tag in keyword_tags:
        if keyword in text and tag not in tags:
            tags.append(tag)
    if name and name != "新角色" and name not in tags:
        tags.insert(0, name)
    return tags[:6]


def build_fallback_persona_after(prompt_text: str, project: dict[str, Any]) -> dict[str, Any]:
    prompt_line = truncate_preview_text(prompt_text, 180)
    persona_before = get_persona_main_snapshot(project)
    name = infer_persona_name(prompt_line)
    tags = infer_persona_tags(prompt_line, name)
    identity_parts = []
    if "猫娘" in prompt_line:
        identity_parts.append("带有猫耳与猫尾特征的猫娘")
    if "病娇" in prompt_line:
        identity_parts.append("情感占有欲强、表面甜软但容易偏执的角色")
    if not identity_parts:
        identity_parts.append("围绕用户要求生成的原创角色")
    identity = "，".join(identity_parts)
    relationship = "她会把 {{user}} 视为最重要的互动对象，主动观察对方的反应并用贴近设定的方式推进对话。"

    return {
        "name": name,
        "description": f"{name}是{identity}。{relationship}",
        "personality": "语气鲜明、反应具体，保持角色身份稳定；表达时有自己的欲望、边界与小动作，不用空泛旁白代替角色行动。",
        "first_mes": f"{{{{user}}}}，你终于来了。{name}轻轻靠近，像是已经等了很久，眼神专注地落在你身上。",
        "mes_example": f"{{{{char}}}}: 我是{name}，会一直记得你的味道和声音。\n{{{{user}}}}: 你为什么这么在意我？\n{{{{char}}}}: 因为你是特别的呀，所以我想更了解你一点。",
        "scenario": f"{{{{user}}}}与{name}刚开始近距离相处，当前场景需要自然展示角色设定、关系张力和后续互动方向。",
        "creator_notes": "必须直接扮演角色，不输出字段说明；保持人设一致，避免替用户决定行动或情绪；所有补充都围绕用户要求展开。",
        "tags": tags or [name, "AI草稿"],
    }


def generate_copilot_fallback(prompt_text: str, current_view: str, focus_hint: dict[str, Any], project: dict[str, Any]) -> dict[str, Any]:
    prompt_line = truncate_preview_text(prompt_text, 180)
    reason = build_default_candidate_reason(current_view if current_view in {"persona", "worldbook", "preset", "memory"} else "persona", current_view)
    candidates: list[dict[str, Any]] = []

    persona_before = get_persona_main_snapshot(project)
    persona_after = build_fallback_persona_after(prompt_line, project)
    for key, value in persona_after.items():
        candidates.append({
            "module": "persona",
            "action": "json_patch",
            "label": f"填充 persona_card.{key}",
            "reason": reason,
            "target": {"path": f"persona_card.{key}", "operation": "set"},
            "before": persona_before.get(key),
            "after": value,
        })

    if "世界" in prompt_line or "设定" in prompt_line or current_view == "worldbook":
        candidates.append({
            "module": "worldbook",
            "action": "json_patch",
            "label": "填充 worldbook.entries.0",
            "reason": "你的要求里提到了可补充的设定信息。",
            "target": {"path": "worldbook.entries.0", "operation": "append"},
            "before": None,
            "after": {
                "id": make_id("wb"),
                "title": f"{persona_after.get('name') or '角色'}相关设定",
                "trigger": ",".join([item for item in [persona_after.get("name"), *persona_after.get("tags", [])] if item]) or "关键词",
                "content": f"围绕“{prompt_line}”补充上下文设定，保证角色身份、关系张力和场景规则在后续对话中稳定出现。",
                "comment": "AI 候选修改，可再人工润色。",
            },
        })

    return {
        "summary": f"已根据整张卡整理出 {len(candidates)} 条候选修改，请选择 YES 填充或 NO 取消。",
        "candidates": candidates,
    }


def build_copilot_module_prompt(module_name: str, settings: dict[str, Any]) -> str:
    prompt_map = {
        "persona": normalize_text(settings.get("persona_prompt")),
        "worldbook": normalize_text(settings.get("worldbook_prompt")),
        "preset": normalize_text(settings.get("preset_prompt")),
        "memory": normalize_text(settings.get("memory_prompt")),
    }
    return prompt_map.get(module_name, "")


def build_copilot_system_prompt(current_view: str, focus_hint: dict[str, Any], settings: dict[str, Any]) -> str:
    schema = build_copilot_candidate_schema()
    shared_prompt = normalize_text(settings.get("base_system_prompt")) or DEFAULT_COPILOT_SETTINGS["base_system_prompt"]
    module_prompts = [
        build_copilot_module_prompt("persona", settings),
        build_copilot_module_prompt("worldbook", settings),
        build_copilot_module_prompt("preset", settings),
        build_copilot_module_prompt("memory", settings),
    ]
    focus_title = normalize_text(focus_hint.get("title")) or "当前卡"
    focus_subtitle = normalize_text(focus_hint.get("subtitle"))
    return "\n\n".join([
        shared_prompt,
        "你现在负责分析整张 Card Writer 工程，而不是只重写当前条目。",
        f"当前视图是 {current_view}，当前焦点提示是：{focus_title}。",
        focus_subtitle or "焦点提示仅用于帮助你理解用户此刻在看哪里，不限制修改范围。",
        "必须读取 user payload 里的 json_schema 和 project：json_schema 是四个卡区允许填充的 JSON 键结构，project 是当前实际内容。",
        "优先输出 action=json_patch：target.path 必须精确匹配 json_schema/project 中的点路径，例如 persona_card.name、persona_card.tags、worldbook.entries.0.content、memory.items.0.tags。",
        "json_patch 的 target.operation 只允许 set、delete、append；after 必须是该路径要写入或追加的 JSON 值，不要包一层无关对象。",
        "除非是在数组上追加整条 entry/item，否则不要输出整块对象；普通填卡必须一键一候选，例如 persona_card.name 一条、persona_card.description 一条。",
        "禁止输出空字符串、空数组、空对象作为 after；不确定就不要生成该候选。",
        "输出必须是候选修改列表，让用户自己选择 YES/NO 后再应用。不要直接返回整张卡，不要输出解释性文字。",
        "如果用户要求生成人设卡、角色卡或自动填充，请分别给出 persona_card.name、description、personality、scenario、first_mes、mes_example、creator_notes、tags 等键的 json_patch 候选。",
        "禁止把用户要求原样塞进 description，也禁止输出“应填写/需要生成/建议补充某字段”这类元说明；after 必须是最终要填入表单的内容。",
        "只返回与用户要求直接相关的修改，避免无关大改。候选 action 只允许 replace_field、update_array_item、append_array_item。",
        *[item for item in module_prompts if item],
        "必须只返回一个 JSON 对象，不要输出 markdown、解释、代码块或额外文字。",
        f"输出结构必须符合这个 JSON 形状：{json.dumps(schema, ensure_ascii=False)}",
    ])


def build_copilot_user_payload(prompt_text: str, focus_hint: dict[str, Any], project: dict[str, Any], project_revision: str, current_view: str) -> str:
    context = {
        "prompt": prompt_text,
        "current_view": current_view,
        "focus_hint": focus_hint,
        "project_revision": project_revision,
        "project_title": project.get("title", ""),
        "json_schema": build_card_writer_json_schema(),
        "project": project,
    }
    return json.dumps(context, ensure_ascii=False)


def parse_llm_json_text(raw_text: str) -> dict[str, Any]:
    text = str(raw_text or "").strip()
    fenced_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fenced_match:
        text = fenced_match.group(1).strip()
    try:
        parsed = json.loads(text)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="AI 返回的不是合法 JSON。") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=502, detail="AI 返回的 JSON 根节点必须是对象。")
    return parsed


def call_copilot_llm(
    *,
    prompt_text: str,
    current_view: str,
    focus_hint: dict[str, Any],
    project: dict[str, Any],
    project_revision: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    url = build_copilot_api_url(config["base_url"], "chat/completions")
    settings = get_copilot_settings()
    payload = {
        "model": config["model"],
        "messages": [
            {"role": "system", "content": build_copilot_system_prompt(current_view, focus_hint, settings)},
            {"role": "user", "content": build_copilot_user_payload(prompt_text, focus_hint, project, project_revision, current_view)},
        ],
        "temperature": clamp_float(config.get("temperature"), 0.0, 2.0, DEFAULT_LLM_TEMPERATURE),
        "response_format": {"type": "json_object"},
    }

    data = request_json_sync(
        url=url,
        api_key=config["api_key"],
        payload=payload,
        request_timeout=int(config["request_timeout"]),
    )
    try:
        raw_reply = str(data["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(status_code=502, detail="AI 返回格式无效。") from exc
    return parse_llm_json_text(raw_reply)


def build_copilot_api_url(base_url: str, endpoint: str) -> str:
    clean_base = base_url.strip().rstrip("/")
    clean_endpoint = endpoint.strip("/")
    if not clean_base:
        raise HTTPException(status_code=400, detail="未配置 LLM_BASE_URL。")
    if clean_base.endswith(f"/{clean_endpoint}") or clean_base.endswith(clean_endpoint):
        return clean_base
    return f"{clean_base}/{clean_endpoint}"


def build_copilot_headers(api_key: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    key = api_key.strip()
    if key:
        try:
            key.encode("ascii")
        except UnicodeEncodeError as exc:
            raise HTTPException(status_code=400, detail="API Key 只能包含 ASCII 字符。") from exc
        headers["Authorization"] = f"Bearer {key}"
    return headers


def request_json_sync(
    *,
    url: str,
    api_key: str,
    payload: dict[str, Any],
    request_timeout: int,
) -> dict[str, Any]:
    try:
        with httpx.Client(timeout=float(request_timeout)) as client:
            response = client.post(url, headers=build_copilot_headers(api_key), json=payload)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        response_text = exc.response.text.strip() if exc.response is not None else ""
        detail = response_text[:500] if response_text else str(exc)
        raise HTTPException(status_code=502, detail=f"AI 请求失败：{detail}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"AI 请求失败：{exc}") from exc
    try:
        data = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="AI 返回的不是合法 JSON。") from exc
    if not isinstance(data, dict):
        raise HTTPException(status_code=502, detail="AI 返回的根结构无效。")
    return data


def normalize_worldbook_entry(value: Any, index: int) -> dict[str, Any]:
    raw = value if isinstance(value, dict) else {}
    data = copy.deepcopy(WORLDBOOK_ENTRY_DEFAULT)
    data["id"] = normalize_text(raw.get("id")) or make_id("wb")
    text_fields = [
        "title",
        "trigger",
        "secondary_trigger",
        "entry_type",
        "group_operator",
        "match_mode",
        "secondary_mode",
        "content",
        "group",
        "insertion_position",
        "injection_role",
        "prompt_layer",
        "comment",
    ]
    for key in text_fields:
        data[key] = normalize_text(raw.get(key, data[key])) or data[key]
    for key in ["chance", "sticky_turns", "cooldown_turns", "order", "priority", "injection_depth", "injection_order"]:
        data[key] = as_int(raw.get(key), data[key])
    for key in ["recursive_enabled", "prevent_further_recursion", "enabled", "case_sensitive", "whole_word"]:
        data[key] = as_bool(raw.get(key), data[key])
    if not normalize_text(raw.get("title")):
        data["title"] = data["title"] or f"词条 {index + 1}"
    if not normalize_text(raw.get("entry_type")):
        data["entry_type"] = WORLDBOOK_ENTRY_DEFAULT["entry_type"]
    if not normalize_text(raw.get("group_operator")):
        data["group_operator"] = WORLDBOOK_ENTRY_DEFAULT["group_operator"]
    if not normalize_text(raw.get("match_mode")):
        data["match_mode"] = WORLDBOOK_ENTRY_DEFAULT["match_mode"]
    if not normalize_text(raw.get("secondary_mode")):
        data["secondary_mode"] = WORLDBOOK_ENTRY_DEFAULT["secondary_mode"]
    if not normalize_text(raw.get("insertion_position")):
        data["insertion_position"] = WORLDBOOK_ENTRY_DEFAULT["insertion_position"]
    if not normalize_text(raw.get("injection_role")):
        data["injection_role"] = WORLDBOOK_ENTRY_DEFAULT["injection_role"]
    if not normalize_text(raw.get("prompt_layer")):
        data["prompt_layer"] = WORLDBOOK_ENTRY_DEFAULT["prompt_layer"]
    data["order"] = as_int(raw.get("order"), index)
    return data


def normalize_worldbook(value: Any) -> dict[str, Any]:
    raw = value if isinstance(value, dict) else {}
    settings_raw = raw.get("settings") if isinstance(raw.get("settings"), dict) else {}
    settings = copy.deepcopy(WORLDBOOK_SETTINGS_DEFAULTS)
    for key, default in WORLDBOOK_SETTINGS_DEFAULTS.items():
        if isinstance(default, bool):
            settings[key] = as_bool(settings_raw.get(key), default)
        elif isinstance(default, int):
            settings[key] = as_int(settings_raw.get(key), default)
        else:
            settings[key] = normalize_text(settings_raw.get(key, default)) or default
    entries_raw = raw.get("entries") if isinstance(raw.get("entries"), list) else []
    return {
        "settings": settings,
        "entries": [normalize_worldbook_entry(item, index) for index, item in enumerate(entries_raw)],
    }


def normalize_memory_item(value: Any, index: int) -> dict[str, Any]:
    raw = value if isinstance(value, dict) else {}
    return {
        "id": normalize_text(raw.get("id")) or f"memory_{index + 1:03d}",
        "title": normalize_text(raw.get("title")),
        "content": normalize_text(raw.get("content")),
        "tags": split_tags(raw.get("tags", [])),
        "notes": normalize_text(raw.get("notes")),
    }


def normalize_memory(value: Any) -> dict[str, Any]:
    raw = value if isinstance(value, dict) else {}
    items_raw = raw.get("items") if isinstance(raw.get("items"), list) else []
    return {"items": [normalize_memory_item(item, index) for index, item in enumerate(items_raw)]}


def normalize_extra_prompt(value: Any, index: int) -> dict[str, Any]:
    raw = value if isinstance(value, dict) else {}
    return {
        "id": normalize_text(raw.get("id")) or make_id("extra") ,
        "name": normalize_text(raw.get("name")),
        "enabled": as_bool(raw.get("enabled"), True),
        "content": normalize_text(raw.get("content")),
        "order": as_int(raw.get("order"), index),
    }


def normalize_modules(value: Any) -> dict[str, bool]:
    raw = value if isinstance(value, dict) else {}
    result = copy.deepcopy(PRESET_MODULE_DEFAULTS)
    for key in list(raw.keys()):
        result[str(key)] = as_bool(raw.get(key), False)
    for key in list(result.keys()):
        result[key] = as_bool(result.get(key), False)
    return result


def normalize_preset_item(value: Any, index: int) -> dict[str, Any]:
    raw = value if isinstance(value, dict) else {}
    extra_prompts = raw.get("extra_prompts") if isinstance(raw.get("extra_prompts"), list) else []
    prompt_groups = raw.get("prompt_groups") if isinstance(raw.get("prompt_groups"), list) else []
    return {
        "id": normalize_text(raw.get("id")) or make_id("preset"),
        "name": normalize_text(raw.get("name")),
        "enabled": as_bool(raw.get("enabled"), True),
        "base_system_prompt": normalize_text(raw.get("base_system_prompt")),
        "modules": normalize_modules(raw.get("modules")),
        "extra_prompts": [normalize_extra_prompt(item, extra_index) for extra_index, item in enumerate(extra_prompts)],
        "prompt_groups": copy.deepcopy(prompt_groups),
    }


def normalize_preset(value: Any) -> dict[str, Any]:
    raw = value if isinstance(value, dict) else {}
    presets_raw = raw.get("presets") if isinstance(raw.get("presets"), list) else []
    presets = [normalize_preset_item(item, index) for index, item in enumerate(presets_raw)]
    active_id = normalize_text(raw.get("active_preset_id"))
    if not active_id and presets:
        active_id = presets[0]["id"]
    return {
        "active_preset_id": active_id,
        "presets": presets,
    }


def normalize_project(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return create_empty_project()

    if payload.get("type") == PROJECT_TYPE and any(key in payload for key in ["persona_card", "worldbook", "memory", "preset"]):
        project = create_empty_project()
        project["version"] = as_int(payload.get("version"), 3)
        project["type"] = PROJECT_TYPE
        project["title"] = normalize_text(payload.get("title"))
        project["updated_at"] = normalize_text(payload.get("updated_at"))
        project["persona_card"] = normalize_persona_card(payload.get("persona_card"))
        project["worldbook"] = normalize_worldbook(payload.get("worldbook"))
        project["memory"] = normalize_memory(payload.get("memory"))
        project["preset"] = normalize_preset(payload.get("preset"))
        if not project["title"]:
            project["title"] = project["persona_card"].get("name", "")
        return project

    if payload.get("card") is None and payload.get("nodes"):
        return normalize_legacy_project(payload)

    if looks_like_persona_card(payload):
        project = create_empty_project()
        project["persona_card"] = normalize_persona_card(payload)
        project["title"] = project["persona_card"].get("name", "") or "导入的人设卡"
        return project

    if looks_like_worldbook(payload):
        project = create_empty_project()
        project["worldbook"] = normalize_worldbook(payload)
        project["title"] = "导入的世界书"
        return project

    if looks_like_memory(payload):
        project = create_empty_project()
        project["memory"] = normalize_memory(payload)
        project["title"] = "导入的记忆"
        return project

    if looks_like_preset(payload):
        project = create_empty_project()
        project["preset"] = normalize_preset(payload)
        project["title"] = "导入的预设"
        return project

    if any(key in payload for key in ["card", "plot_stages", "worldbooks", "memories", "presets"]):
        return normalize_old_project(payload)

    return create_empty_project()


def normalize_old_project(payload: dict[str, Any]) -> dict[str, Any]:
    project = create_empty_project()
    card_raw = payload.get("card") if isinstance(payload.get("card"), dict) else {}
    personas_raw = payload.get("personas") if isinstance(payload.get("personas"), list) else []
    plot_raw = payload.get("plot_stages") if isinstance(payload.get("plot_stages"), list) else []
    worldbooks_raw = payload.get("worldbooks") if isinstance(payload.get("worldbooks"), list) else []
    memories_raw = payload.get("memories") if isinstance(payload.get("memories"), list) else []
    presets_raw = payload.get("presets") if isinstance(payload.get("presets"), list) else []

    persona_map = normalize_personas_map(personas_raw)
    plot_map = normalize_plot_stage_map(plot_raw)
    persona_card = {
        "name": normalize_text(card_raw.get("name")),
        "description": normalize_text(card_raw.get("description")),
        "personality": normalize_text(card_raw.get("personality")),
        "first_mes": normalize_text(card_raw.get("first_mes")),
        "mes_example": normalize_text(card_raw.get("mes_example")),
        "scenario": normalize_text(card_raw.get("scenario")),
        "creator_notes": normalize_text(card_raw.get("creator_notes")),
        "tags": split_tags(card_raw.get("tags", [])),
        "creativeWorkshop": {"enabled": True, "items": []},
        "plotStages": plot_map,
        "personas": persona_map,
    }
    project["version"] = as_int(payload.get("version"), 2)
    project["title"] = normalize_text(payload.get("title")) or persona_card["name"]
    project["updated_at"] = normalize_text(payload.get("updated_at"))
    project["persona_card"] = normalize_persona_card(persona_card)
    project["worldbook"] = normalize_worldbook({"settings": copy.deepcopy(WORLDBOOK_SETTINGS_DEFAULTS), "entries": [legacy_worldbook_to_entry(item, index) for index, item in enumerate(worldbooks_raw)]})
    project["memory"] = normalize_memory({"items": [legacy_memory_to_item(item, index) for index, item in enumerate(memories_raw)]})
    project["preset"] = normalize_preset({"active_preset_id": "", "presets": [legacy_preset_to_item(item, index) for index, item in enumerate(presets_raw)]})
    return project


def legacy_worldbook_to_entry(item: Any, index: int) -> dict[str, Any]:
    raw = item if isinstance(item, dict) else {}
    return {
        "id": normalize_text(raw.get("id")) or make_id("wb"),
        "title": normalize_text(raw.get("title")),
        "trigger": normalize_text(raw.get("keywords")),
        "secondary_trigger": "",
        "entry_type": "lore",
        "group_operator": "and",
        "match_mode": "includes",
        "secondary_mode": "includes",
        "content": normalize_text(raw.get("content")),
        "group": "",
        "chance": 100,
        "sticky_turns": 0,
        "cooldown_turns": 0,
        "order": index,
        "priority": 0,
        "insertion_position": "after_system",
        "injection_depth": 0,
        "injection_order": 100,
        "injection_role": "system",
        "prompt_layer": "default",
        "recursive_enabled": False,
        "prevent_further_recursion": False,
        "enabled": True,
        "case_sensitive": False,
        "whole_word": False,
        "comment": normalize_text(raw.get("notes")),
    }


def legacy_memory_to_item(item: Any, index: int) -> dict[str, Any]:
    raw = item if isinstance(item, dict) else {}
    return {
        "id": normalize_text(raw.get("id")) or f"memory_{index + 1:03d}",
        "title": normalize_text(raw.get("title")),
        "content": normalize_text(raw.get("content")),
        "tags": [],
        "notes": normalize_text(raw.get("notes") or raw.get("summary")),
    }


def legacy_preset_to_item(item: Any, index: int) -> dict[str, Any]:
    raw = item if isinstance(item, dict) else {}
    return {
        "id": normalize_text(raw.get("id")) or make_id("preset"),
        "name": normalize_text(raw.get("title")) or f"预设 {index + 1}",
        "enabled": True,
        "base_system_prompt": normalize_text(raw.get("content")),
        "modules": copy.deepcopy(PRESET_MODULE_DEFAULTS),
        "extra_prompts": [],
        "prompt_groups": [],
    }


def normalize_legacy_project(payload: dict[str, Any]) -> dict[str, Any]:
    node_map: dict[str, str] = {}
    for node in payload.get("nodes", []):
        if isinstance(node, dict):
            node_map[str(node.get("type", ""))] = str(node.get("content", ""))

    basic = parse_basic(node_map.get("basic", ""))
    project = create_empty_project()
    persona_map = normalize_personas_map(parse_personas(node_map.get("personas", "")))
    stage_map = normalize_plot_stage_map(parse_plot_stages(node_map.get("plot_stages", "")))
    project["version"] = 3
    project["type"] = PROJECT_TYPE
    project["title"] = normalize_text(payload.get("title")) or basic["name"]
    project["updated_at"] = normalize_text(payload.get("updated_at"))
    project["persona_card"] = normalize_persona_card({
        "name": basic["name"],
        "tags": basic["tags"],
        "description": node_map.get("description", ""),
        "personality": node_map.get("personality", ""),
        "scenario": node_map.get("scenario", ""),
        "first_mes": node_map.get("first_mes", ""),
        "mes_example": node_map.get("mes_example", ""),
        "creator_notes": node_map.get("creator_notes", ""),
        "plotStages": stage_map,
        "personas": persona_map,
    })
    return project


def parse_basic(content: str) -> dict[str, Any]:
    result: dict[str, Any] = {"name": "", "tags": []}
    text = normalize_text(content)
    if not text:
        return result
    for line in text.split("\n"):
        current = line.strip()
        if not current:
            continue
        if match := re.match(r"角色名[：:]\s*(.*)", current):
            result["name"] = match.group(1).strip()
        elif match := re.match(r"标签[：:]\s*(.*)", current):
            result["tags"] = split_tags(match.group(1).strip())
    return result


def parse_plot_stages(content: str) -> list[dict[str, Any]]:
    stages: list[dict[str, Any]] = []
    text = normalize_text(content)
    if not text:
        return stages
    blocks = re.split(r"\n+(?=阶段\s*[A-Za-z0-9])", text)
    for block in blocks:
        current = block.strip()
        if not current:
            continue
        header = re.match(r"阶段\s*([A-Za-z0-9]+)[：:]\s*(.*)", current)
        if not header:
            continue
        key = header.group(1).upper()
        body = current[header.end():].strip()
        description = ""
        rules = ""
        if match := re.search(r"描述[：:]\s*([\s\S]*?)(?=\n规则[：:]|\Z)", body):
            description = match.group(1).strip()
        if match := re.search(r"规则[：:]\s*([\s\S]*)", body):
            rules = match.group(1).strip()
        stages.append({"id": key, "label": header.group(2).strip() or key, "description": description, "rules": rules})
    return stages


def parse_personas(content: str) -> list[dict[str, Any]]:
    personas: list[dict[str, Any]] = []
    text = normalize_text(content)
    if not text:
        return personas
    blocks = re.split(r"\n+(?=角色\s*\d)", text)
    for block in blocks:
        current = block.strip()
        if not current:
            continue
        header = re.match(r"角色\s*(\d+)[：:]\s*(.*)", current)
        if not header:
            continue
        key = header.group(1)
        body = current[header.end():].strip()
        personas.append({
            "id": key,
            "name": header.group(2).strip(),
            "description": extract_section(body, "描述", ["性格", "场景", "备注"]),
            "personality": extract_section(body, "性格", ["场景", "备注"]),
            "scenario": extract_section(body, "场景", ["备注"]),
            "creator_notes": extract_section(body, "备注", []),
        })
    return personas


def extract_section(body: str, label: str, next_labels: list[str]) -> str:
    if next_labels:
        lookahead = "|".join(fr"\n{next_label}[：:]" for next_label in next_labels)
        pattern = fr"{label}[：:]\s*([\s\S]*?)(?={lookahead}|\Z)"
    else:
        pattern = fr"{label}[：:]\s*([\s\S]*)"
    match = re.search(pattern, body)
    return match.group(1).strip() if match else ""


def looks_like_persona_card(payload: dict[str, Any]) -> bool:
    return "personas" in payload or "creativeWorkshop" in payload or all(key in payload for key in ["name", "description", "first_mes"])


def looks_like_worldbook(payload: dict[str, Any]) -> bool:
    return "settings" in payload and "entries" in payload


def looks_like_memory(payload: dict[str, Any]) -> bool:
    return list(payload.keys()) == ["items"] or "items" in payload


def looks_like_preset(payload: dict[str, Any]) -> bool:
    return "active_preset_id" in payload or "presets" in payload


def project_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="请提供合法的 JSON 对象。")
    return normalize_project(payload)


def normalized_has_content(project: dict[str, Any]) -> bool:
    normalized = normalize_project(project)
    persona = normalized["persona_card"]
    if any(str(persona.get(key, "")).strip() for key in PERSONA_FIELDS):
        return True
    if persona.get("tags"):
        return True
    if normalized["worldbook"].get("entries"):
        return True
    if normalized["memory"].get("items"):
        return True
    if normalized["preset"].get("presets"):
        return True
    return False


app = FastAPI(title="Fantareal Card Writer Mod")
store = ProjectStore(PROJECTS_DIR, AUTOSAVES_DIR, EXPORTS_DIR, WORKSPACE_PATH)
compiler = CardCompiler()

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.on_event("startup")
async def startup() -> None:
    store.ensure_dirs()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    root_path = (request.scope.get("root_path") or "").rstrip("/")
    stylesheet_url = f"{root_path}/static/card-writer.css" if root_path else "/static/card-writer.css"
    script_url = f"{root_path}/static/card-writer.js" if root_path else "/static/card-writer.js"
    context = {
        "project": store.load_workspace(),
        "api_base_path": root_path,
        "static_stylesheet_url": stylesheet_url,
        "static_script_url": script_url,
    }
    return templates.TemplateResponse(request, "index.html", context)


@app.get("/api/projects")
async def list_projects() -> dict[str, Any]:
    return {"projects": store.list_projects()}


@app.get("/api/projects/{filename}")
async def get_project(filename: str) -> dict[str, Any]:
    return {"project": store.load_project(filename)}


@app.post("/api/projects/{filename}")
async def save_project(filename: str, payload: CardWriterProject) -> dict[str, Any]:
    return store.save_project(filename, payload.model_dump())


@app.delete("/api/projects/{filename}")
async def delete_project(filename: str) -> dict[str, Any]:
    store.delete_project(filename)
    return {"ok": True}


@app.get("/api/autosave")
async def get_autosave() -> dict[str, Any]:
    return {"project": store.load_autosave()}


@app.post("/api/autosave")
async def save_autosave(payload: CardWriterProject) -> dict[str, Any]:
    return store.save_autosave(payload.model_dump())


@app.get("/api/workspace")
async def get_workspace() -> dict[str, Any]:
    return {"project": store.load_workspace()}


@app.post("/api/workspace")
async def save_workspace(payload: CardWriterProject) -> dict[str, Any]:
    return store.save_workspace(payload.model_dump())


@app.delete("/api/workspace")
async def clear_workspace() -> dict[str, Any]:
    return store.clear_workspace()


@app.post("/api/compile")
async def api_compile(payload: CardWriterProject) -> dict[str, Any]:
    return {"ok": True, "card": compiler.compile(payload.model_dump())}


@app.post("/api/validate")
async def api_validate(payload: CardWriterProject) -> dict[str, Any]:
    project = payload.model_dump()
    card = compiler.compile(project)
    warnings = compiler.validate(project, card)
    return {"ok": not any(item["level"] == "error" for item in warnings), "warnings": warnings}


@app.get("/api/settings")
async def api_get_settings() -> dict[str, Any]:
    return {"ok": True, "settings": get_copilot_settings()}


@app.post("/api/settings")
async def api_save_settings(payload: CopilotSettingsPayload) -> dict[str, Any]:
    return {"ok": True, "settings": save_copilot_settings(payload.model_dump())}


@app.post("/api/ai/generate")
async def api_ai_generate(payload: CopilotGeneratePayload) -> dict[str, Any]:
    return compiler.generate_copilot_draft(payload).model_dump()


@app.post("/api/export")
async def api_export(payload: ExportPayload) -> Response:
    export_target = str(payload.target or "persona").strip().lower()
    content_payload = compiler.export_payload(payload.project.model_dump(), export_target)
    export_result = store.export_json(payload.filename, content_payload)
    filename = export_result["filename"]
    content = json.dumps(content_payload, ensure_ascii=False, indent=2)
    encoded_filename = quote(filename)
    headers = {"Content-Disposition": f"attachment; filename=download.json; filename*=UTF-8''{encoded_filename}"}
    return Response(content=content, media_type="application/json; charset=utf-8", headers=headers)


@app.post("/api/import-card")
async def api_import_card(payload: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "project": compiler.import_payload(payload)}
