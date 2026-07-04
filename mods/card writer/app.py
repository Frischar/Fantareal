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

import colorama
import hashlib
import httpx
import logging
import time
import unicodedata

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
FA_DATA_DIR = PROJECT_ROOT / "data"
FA_CURRENT_CARD_PATH = FA_DATA_DIR / "current_role_card.json"
FA_PERSONA_PATH = FA_DATA_DIR / "persona.json"
FA_WORLDBOOK_PATH = FA_DATA_DIR / "worldbook.json"
FA_PRESET_PATH = FA_DATA_DIR / "preset.json"
FA_LEGACY_MEMORIES_PATH = FA_DATA_DIR / "memories.json"
FA_CARD_RUNTIME_CARDS_DIR = FA_DATA_DIR / "card_runtime" / "cards"
FA_BACKUPS_DIR = DATA_DIR / "fa_backups"

STATIC_DIR = RESOURCE_DIR / "static"
TEMPLATES_DIR = RESOURCE_DIR / "templates"
PROMPTS_DIR = RESOURCE_DIR / "prompts"
HUMAN_CHARACTER_PROMPT_DIR = PROMPTS_DIR / "human_character_system"
HUMAN_CHARACTER_PROMPT_FILES = [
    "wheelchair_core.md",
    "runtime_package.md",
    "container_router.md",
    "candidate_rules.md",
    "humanizer_guard.md",
    "database_designer.md",
    "worldbook_preset_memory.md",
]
HUMAN_CHARACTER_DEEP_PROMPT_FILES = [
    "orchestration_planner.md",
    "deep_reference.md",
    "question_bank_reference.md",
    "case_reference.md",
    "fa_container_deep_router.md",
]

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

DATABASE_VARIABLE_DEFAULT = {
    "id": "",
    "key": "",
    "label": "",
    "value_type": "number",
    "initial_value": "",
    "scope": "role",
    "description": "",
    "write_policy": "",
    "notes": "",
}

DATABASE_STAGE_DEFAULT = {
    "id": "",
    "role_id": "",
    "stage_key": "",
    "title": "",
    "condition": "",
    "active_tag": "",
    "emits_tags": [],
    "description": "",
    "notes": "",
}

DATABASE_TAG_DEFAULT = {
    "id": "",
    "tag": "",
    "title": "",
    "trigger": "",
    "target": "worldbook",
    "description": "",
    "notes": "",
}

DATABASE_DEFAULT = {
    "enabled": True,
    "notes": "",
    "variables": [],
    "stages": [],
    "tags": [],
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
    "database": copy.deepcopy(DATABASE_DEFAULT),
    "updated_at": "",
}

DEFAULT_PERSONA_PROMPT = """
你要为 Fa Card Writer 生成人设卡候选，输出内容必须可直接写入编辑器表单。
重点要求：
1. description 写身份、处境、关系起点和稳定事实，不要堆抽象形容词。
2. personality 写可执行反应：欲望、边界、防御、亲近方式、退缩方式、语言纹理。
3. scenario 写默认局势和关系张力，不要把完整世界观塞进来。
4. first_mes 必须是角色真实会说/会做的开场，不写作者说明。
5. mes_example 只写示例对话和动作节奏，不要代替 {{user}} 做过多决定。
6. creator_notes 写隐藏纪律：不跳关系阶段、不突然坦白、亲密和身体反应必须符合角色边界。
7. 如果是分身 persona，只生成当前分身所需字段，不扩写整张主卡。
""".strip()

DEFAULT_WORLDBOOK_PROMPT = """
你要为 Fa Card Writer 生成世界书候选，输出必须适合直接落入当前 entry。
重点要求：
1. 一个 entry 只承载一个事实、阶段、地点、组织、秘密或状态表现。
2. trigger 要便于触发；阶段表现可在 title/comment 中标明未来可由 tag 触发。
3. content 写成可注入上下文的正文，不写闲聊口吻和作者解释。
4. 阶段表现应约束“当前会怎样表现”，不要重复整张角色卡。
5. 优先使用 Fa runtime 可识别的语义：keyword/constant/external_tag、any/all、stable/current_state/dynamic/output_guard。
6. comment 只写维护备注，不重复正文。
""".strip()

DEFAULT_PRESET_PROMPT = """
你要为 Fa Card Writer 生成轻量预设适配候选，不要尝试从零创作高阶预设或大型叙事引擎。
重点要求：
1. preset 只做基础适配纪律：不替用户行动、不跳阶段、不突然亲密、不突然完全信任。
2. base_system_prompt 只写模型如何读取角色卡、世界书、记忆和状态，不写具体世界观百科。
3. modules 只开启真正需要的开关，避免互相冲突。
4. extra_prompts 可补充防总结腔、防替用户、防阶段跳跃等短规则。
5. prompt_groups 默认保持精简；不要生成复杂风格库或大型高阶预设结构。
6. 更重要的内容优先落到 persona、worldbook、memory、database。
""".strip()

DEFAULT_MEMORY_PROMPT = """
你要为 Fa Card Writer 生成记忆候选，输出必须适合直接写入 memory item。
重点要求：
1. content 聚焦单个已发生事实、事件、关系变化或长期偏好，不写散乱总结。
2. 不要把未发生的剧情冒充记忆；未发生内容应写到 scenario、worldbook 或 preset。
3. title 要短而明确，能快速说明这条记忆的主题。
4. tags 保持精简，便于检索，不要堆很多同义词。
5. notes 写维护信息、时间线提醒或补充说明，可标明这条记忆会影响哪些关系变量。
6. 每条记忆应当独立成立，便于后续单独删改。
""".strip()

DEFAULT_DATABASE_PROMPT = """
你要为 Fa Card Writer 生成数据库草稿候选，输出必须只写当前工程里的 database 草稿 JSON，不要尝试写运行时 SQLite 或真实状态库。
重点要求：
1. 数据库的意义是记录变量、判断阶段、发出 tag，用来触发世界书或演出工坊。
2. variables 写可被追踪的状态，例如 trust、guard、intimacy、desire、fatigue、jealousy；必须说明变量含义和写入纪律。
3. stages 写阶段判断规则和会发出的 tag，例如 state_journal.stage.<role_id>.<stage_key>。
4. tags 写 tag 与世界书/演出工坊的连接意图，不要写大段剧情正文。
5. 这是 P1 写卡草稿，只服务于设计和导出；不要伪装成已接入运行时。
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
    "database_prompt": DEFAULT_DATABASE_PROMPT,
}


class CardWriterProject(BaseModel):
    version: int = 3
    type: str = PROJECT_TYPE
    title: str = ""
    persona_card: dict[str, Any] = Field(default_factory=dict)
    worldbook: dict[str, Any] = Field(default_factory=dict)
    memory: dict[str, Any] = Field(default_factory=dict)
    preset: dict[str, Any] = Field(default_factory=dict)
    database: dict[str, Any] = Field(default_factory=dict)
    updated_at: str = ""


class ExportPayload(BaseModel):
    project: CardWriterProject = Field(default_factory=CardWriterProject)
    filename: str = ""
    target: str = "persona"


class FaApplyPreviewPayload(BaseModel):
    project: CardWriterProject = Field(default_factory=CardWriterProject)
    modules: list[str] = Field(default_factory=list)


class FaApplyPayload(FaApplyPreviewPayload):
    selected_group_ids: list[str] = Field(default_factory=list)


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
    database_prompt: str = ""


class CopilotGeneratePayload(BaseModel):
    project: CardWriterProject = Field(default_factory=CardWriterProject)
    module: str = "persona"
    prompt: str = ""
    follow_up: str = ""
    current_view: str = "persona"
    focus_hint: dict[str, Any] = Field(default_factory=dict)
    project_revision: str = ""
    thinking_mode: str = "fast"


class CopilotGenerateResponse(BaseModel):
    ok: bool = True
    review_id: str = ""
    summary: str = ""
    prompt_used: str = ""
    current_view: str = "persona"
    base_revision: str = ""
    focus_hint: dict[str, Any] = Field(default_factory=dict)
    plan: dict[str, Any] = Field(default_factory=dict)
    candidate_groups: list[dict[str, Any]] = Field(default_factory=list)
    package_audit: dict[str, Any] = Field(default_factory=dict)
    candidates: list[dict[str, Any]] = Field(default_factory=list)


CardWriterProject.model_rebuild()
ExportPayload.model_rebuild()
FaApplyPreviewPayload.model_rebuild()
FaApplyPayload.model_rebuild()
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
        thinking_mode = normalize_copilot_thinking_mode(payload.thinking_mode)
        review = request_copilot_review(
            prompt_text=prompt_text,
            current_view=current_view,
            focus_hint=focus_hint,
            project=project,
            project_revision=base_revision,
            thinking_mode=thinking_mode,
        )
        candidates = normalize_copilot_candidates(review.get("candidates"), project)
        explicit_name, corrected_names = enforce_explicit_persona_name(prompt_text, candidates)
        if explicit_name and corrected_names:
            for wrong_name in corrected_names:
                review["summary"] = replace_text_value(review.get("summary"), wrong_name, explicit_name)
                review["plan"] = replace_text_value(review.get("plan"), wrong_name, explicit_name)
                review["candidate_groups"] = replace_text_value(review.get("candidate_groups"), wrong_name, explicit_name)
        plan = normalize_copilot_plan(review.get("plan"), candidates)
        candidate_groups = normalize_copilot_candidate_groups(review.get("candidate_groups"), candidates)
        package_audit = build_copilot_package_audit(candidates, plan)
        summary = normalize_text(review.get("summary")) or build_copilot_review_summary(candidates, current_view)
        return CopilotGenerateResponse(
            ok=True,
            review_id=make_id("review"),
            summary=summary,
            prompt_used=prompt_text,
            current_view=current_view,
            base_revision=base_revision,
            focus_hint=focus_hint,
            plan=plan,
            candidate_groups=candidate_groups,
            package_audit=package_audit,
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
        if export_target == "database":
            return copy.deepcopy(normalized["database"])
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
        runtime_audit = build_project_runtime_package_audit(project)
        for tag in runtime_audit.get("missing_tag_consumers", []):
            warnings.append({
                "level": "warning",
                "field": "database.tags",
                "message": f"数据库 tag 尚未被世界书 external_tag 消费：{tag}",
            })
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
    data["database_prompt"] = normalize_text(raw.get("database_prompt")) or DEFAULT_COPILOT_SETTINGS["database_prompt"]
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
    data["personas"] = normalize_personas_map(raw.get("personas"))
    return data


def normalize_copilot_view(value: Any) -> str:
    view_name = str(value or "persona").strip().lower()
    if view_name not in {"persona", "worldbook", "preset", "memory", "database", "preview"}:
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
        "module": current_view if current_view in {"persona", "worldbook", "preset", "memory", "database"} else "persona",
        "persona_key": "",
        "worldbook_id": "",
        "preset_id": "",
        "memory_id": "",
        "database_kind": "",
        "database_id": "",
    }
    for key in ["title", "subtitle", "module", "persona_key", "worldbook_id", "preset_id", "memory_id", "database_kind", "database_id"]:
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
    elif current_view == "database":
        database_kind = normalized["database_kind"]
        database_id = normalized["database_id"]
        items = (project.get("database") or {}).get(database_kind, []) if database_kind in {"variables", "stages", "tags"} else []
        current = next((item for item in items if normalize_text(item.get("id")) == database_id), None)
        current_label = normalize_text((current or {}).get("label") or (current or {}).get("title") or (current or {}).get("key") or (current or {}).get("tag"))
        normalized["title"] = normalized["title"] or f"当前浏览：数据库 · {current_label or '草稿'}"
        normalized["subtitle"] = normalized["subtitle"] or "数据库这里只写变量、阶段和 tag 设计草稿，不写运行时状态库。"
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
    thinking_mode: str,
) -> dict[str, Any]:
    config = get_runtime_llm_config()
    if config["base_url"] and config["model"]:
        return call_copilot_llm(
            prompt_text=prompt_text,
            current_view=current_view,
            focus_hint=focus_hint,
            project=project,
            project_revision=project_revision,
            thinking_mode=thinking_mode,
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
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_before = copy.deepcopy(before)
    normalized_after = copy.deepcopy(after)
    fingerprint = build_copilot_fingerprint(module, action, target, normalized_before)
    candidate = {
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
    candidate.update(normalize_copilot_candidate_metadata(metadata))
    return candidate


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
    for key in ["path", "persona_key", "id", "field", "operation", "kind"]:
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


def find_database_item(project: dict[str, Any], kind: str, item_id: str) -> tuple[int, dict[str, Any] | None]:
    if kind not in {"variables", "stages", "tags"}:
        return -1, None
    items = (project.get("database") or {}).get(kind, [])
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
    if module_name == "database":
        kind = normalize_database_kind(focus_hint.get("database_kind")) or "variables"
        database_id = normalize_text(focus_hint.get("database_id"))
        if database_id:
            return {"kind": kind, "id": database_id}
        items = (project.get("database") or {}).get(kind, [])
        return {"kind": kind, "id": normalize_text(items[0].get("id"))} if items else {"kind": kind, "id": ""}
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
        "database": {"update_array_item", "append_array_item", "json_patch"},
    }
    if action_name in allowed.get(module_name, set()):
        return action_name
    return "replace_field" if module_name == "persona" else "update_array_item"


def slugify_copilot_group_id(value: Any, fallback: str = "default") -> str:
    text = normalize_text(value).lower()
    if not text:
        text = fallback
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^a-z0-9_.:-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text[:80] or fallback


def normalize_copilot_depends_on(value: Any) -> list[str]:
    raw_items = value if isinstance(value, list) else [value] if value else []
    result: list[str] = []
    for item in raw_items:
        item_text = slugify_copilot_group_id(item, "")
        if item_text and item_text not in result:
            result.append(item_text)
    return result[:12]


def normalize_copilot_candidate_metadata(raw: Any) -> dict[str, Any]:
    data = raw if isinstance(raw, dict) else {}
    group_id = slugify_copilot_group_id(data.get("group_id"), "")
    group_title = normalize_text(data.get("group_title"))
    container_role = normalize_text(data.get("container_role"))
    result: dict[str, Any] = {}
    if group_id:
        result["group_id"] = group_id
    if group_title:
        result["group_title"] = group_title[:120]
    if container_role:
        result["container_role"] = container_role[:240]
    depends_on = normalize_copilot_depends_on(data.get("depends_on"))
    if depends_on:
        result["depends_on"] = depends_on
    if "draft_only" in data:
        result["draft_only"] = as_bool(data.get("draft_only"), False)
    return result


def infer_candidate_group_id(candidate: dict[str, Any]) -> str:
    explicit = slugify_copilot_group_id(candidate.get("group_id"), "")
    if explicit:
        return explicit
    path = normalize_text((candidate.get("target") or {}).get("path"))
    if path.startswith("database."):
        return "database_mechanism"
    if path.startswith("worldbook."):
        return "worldbook_context"
    if path.startswith("preset."):
        return "preset_discipline"
    if path.startswith("memory."):
        return "memory_continuity"
    if path.startswith("persona_card."):
        return "persona_foundation"
    return slugify_copilot_group_id(candidate.get("module"), "ungrouped")


def infer_candidate_group_title(group_id: str, candidates: list[dict[str, Any]]) -> str:
    for candidate in candidates:
        if infer_candidate_group_id(candidate) == group_id:
            title = normalize_text(candidate.get("group_title"))
            if title:
                return title
    defaults = {
        "persona_foundation": "角色底座",
        "worldbook_context": "世界书承接",
        "preset_discipline": "预设纪律",
        "memory_continuity": "记忆连续性",
        "database_mechanism": "数据库机制",
        "tag_consumer_link": "tag 消费闭环",
        "ungrouped": "候选修改",
    }
    return defaults.get(group_id, group_id.replace("_", " ").strip().title() or "候选修改")


def collect_group_candidate_ids(group_id: str, candidates: list[dict[str, Any]]) -> list[str]:
    ids: list[str] = []
    for candidate in candidates:
        if infer_candidate_group_id(candidate) == group_id:
            candidate_id = normalize_text(candidate.get("id"))
            if candidate_id:
                ids.append(candidate_id)
    return ids


def build_default_candidate_groups(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    group_ids: list[str] = []
    for candidate in candidates:
        group_id = infer_candidate_group_id(candidate)
        if group_id not in group_ids:
            group_ids.append(group_id)
    groups: list[dict[str, Any]] = []
    for group_id in group_ids:
        candidate_ids = collect_group_candidate_ids(group_id, candidates)
        if not candidate_ids:
            continue
        groups.append({
            "group_id": group_id,
            "group_title": infer_candidate_group_title(group_id, candidates),
            "reason": "",
            "candidate_ids": candidate_ids,
        })
    return groups


def normalize_copilot_plan(raw: Any, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raw = {}
    allowed_modules = {"persona", "worldbook", "preset", "memory", "database"}
    plan: dict[str, Any] = {}
    for key in ["intent_type", "quality_goal", "summary", "package_mode"]:
        value = normalize_text(raw.get(key))
        if value:
            plan[key] = value[:500]
    required = raw.get("required_containers")
    if isinstance(required, list):
        containers = []
        for item in required:
            container = normalize_text(item).lower()
            if container in allowed_modules and container not in containers:
                containers.append(container)
        if containers:
            plan["required_containers"] = containers
    container_plan = []
    raw_container_plan = raw.get("container_plan") if isinstance(raw.get("container_plan"), list) else []
    for item in raw_container_plan[:12]:
        if not isinstance(item, dict):
            continue
        module = normalize_text(item.get("module")).lower()
        role = normalize_text(item.get("role"))
        if module in allowed_modules and role:
            container_plan.append({"module": module, "role": role[:300]})
    if container_plan:
        plan["container_plan"] = container_plan
    risks = []
    raw_risks = raw.get("risks") if isinstance(raw.get("risks"), list) else []
    for item in raw_risks[:8]:
        risk = normalize_text(item)
        if risk:
            risks.append(risk[:240])
    if risks:
        plan["risks"] = risks
    coverage = raw.get("coverage") if isinstance(raw.get("coverage"), dict) else {}
    if coverage:
        normalized_coverage: dict[str, str] = {}
        for key in ["persona", "worldbook", "memory", "database", "preset"]:
            value = normalize_text(coverage.get(key))
            if value:
                normalized_coverage[key] = value[:240]
        if normalized_coverage:
            plan["coverage"] = normalized_coverage
    touched_modules = []
    for candidate in candidates:
        module = normalize_text(candidate.get("module")).lower()
        if module in allowed_modules and module not in touched_modules:
            touched_modules.append(module)
    if touched_modules:
        current_required = plan.get("required_containers") if isinstance(plan.get("required_containers"), list) else []
        merged_required = [item for item in current_required if item in allowed_modules]
        for module in touched_modules:
            if module not in merged_required:
                merged_required.append(module)
        plan["required_containers"] = merged_required
        if not normalize_text(plan.get("package_mode")):
            plan["package_mode"] = "runtime_package" if len(merged_required) > 1 or "database" in merged_required else "single_edit"
        coverage_map = plan.get("coverage") if isinstance(plan.get("coverage"), dict) else {}
        default_coverage = {
            "persona": "承载角色身份、欲望、边界、语言纹理和可执行反应。",
            "worldbook": "承载稳定事实、阶段表现和 external_tag 消费者。",
            "memory": "承载已发生事实，或明确标注未来记忆模板。",
            "database": "承载变量、阶段判断和发出的 tag。",
            "preset": "只承载轻量适配纪律，不生成高阶预设工程。",
        }
        for module in merged_required:
            coverage_map.setdefault(module, default_coverage[module])
        if coverage_map:
            plan["coverage"] = coverage_map
    if not plan and candidates:
        modules = []
        for candidate in candidates:
            module = normalize_text(candidate.get("module"))
            if module and module not in modules:
                modules.append(module)
        if modules:
            plan["summary"] = f"本轮候选涉及 {', '.join(modules)}。"
            plan["required_containers"] = modules
    return plan


def normalize_copilot_candidate_groups(raw: Any, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    raw_groups = raw if isinstance(raw, list) else []
    groups_by_id: dict[str, dict[str, Any]] = {}
    ordered_ids: list[str] = []
    for item in raw_groups:
        if not isinstance(item, dict):
            continue
        group_id = slugify_copilot_group_id(item.get("group_id") or item.get("id"), "")
        if not group_id:
            continue
        candidate_ids = collect_group_candidate_ids(group_id, candidates)
        if not candidate_ids:
            continue
        group = {
            "group_id": group_id,
            "group_title": normalize_text(item.get("group_title") or item.get("title"))[:120] or infer_candidate_group_title(group_id, candidates),
            "reason": normalize_text(item.get("reason"))[:400],
            "candidate_ids": candidate_ids,
        }
        depends_on = normalize_copilot_depends_on(item.get("depends_on"))
        if depends_on:
            group["depends_on"] = depends_on
        draft_only = item.get("draft_only")
        if draft_only is not None:
            group["draft_only"] = as_bool(draft_only, False)
        groups_by_id[group_id] = group
        ordered_ids.append(group_id)

    for fallback_group in build_default_candidate_groups(candidates):
        group_id = fallback_group["group_id"]
        if group_id not in groups_by_id:
            groups_by_id[group_id] = fallback_group
            ordered_ids.append(group_id)

    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for group_id in ordered_ids:
        if group_id in seen or group_id not in groups_by_id:
            continue
        seen.add(group_id)
        result.append(groups_by_id[group_id])
    return result


def extract_candidate_emitted_tags(candidate: dict[str, Any]) -> list[str]:
    if candidate.get("module") != "database":
        return []
    after = candidate.get("after") if isinstance(candidate.get("after"), dict) else {}
    target = candidate.get("target") if isinstance(candidate.get("target"), dict) else {}
    path = normalize_text(target.get("path"))
    tags: list[str] = []
    for key in ["active_tag", "tag"]:
        value = normalize_text(after.get(key))
        if value and value not in tags:
            tags.append(value)
    if not tags and path.startswith("database.stages"):
        role_id = normalize_text(after.get("role_id"))
        stage_key = normalize_text(after.get("stage_key"))
        if role_id and stage_key:
            tags.append(f"state_journal.stage.{role_id}.{stage_key}")
    # database.tags[].trigger is a condition/description in this editor, not the
    # external tag consumed by worldbook. Only database.tags[].tag should emit.
    for value in split_tags(after.get("emits_tags", [])):
        if value and value not in tags:
            tags.append(value)
    return tags


def extract_candidate_consumed_tags(candidate: dict[str, Any]) -> list[str]:
    if candidate.get("module") != "worldbook":
        return []
    after = candidate.get("after") if isinstance(candidate.get("after"), dict) else {}
    entry_type = normalize_text(after.get("entry_type")).lower()
    if entry_type != "external_tag":
        return []
    tags = []
    for key in ["trigger", "secondary_trigger"]:
        for value in split_tags(after.get(key, "")):
            if value and value not in tags:
                tags.append(value)
    return tags


def sanitize_tag_slug(value: str) -> str:
    text = normalize_text(value)
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^0-9A-Za-z_.:-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "stage_tag"


def build_worldbook_consumer_candidate_for_tag(tag: str, source_candidate: dict[str, Any], project: dict[str, Any]) -> dict[str, Any] | None:
    normalized_tag = normalize_text(tag)
    if not normalized_tag:
        return None
    slug = sanitize_tag_slug(normalized_tag)
    source_after = source_candidate.get("after") if isinstance(source_candidate.get("after"), dict) else {}
    title = normalize_text(source_after.get("title") or source_after.get("label")) or "阶段状态"
    description = normalize_text(source_after.get("description") or source_after.get("notes"))
    content_parts = [
        f"当外部 tag `{normalized_tag}` 命中时，说明当前进入“{title}”状态。",
        "角色表现必须服从当前阶段：先体现可观察的情绪、距离、措辞和身体反应，不要跳到更高亲密或完全信任。",
    ]
    if description:
        content_parts.append(description)
    content_parts.append("如果后续记忆或互动没有支撑升级，保持本阶段边界。")
    entry = normalize_worldbook_entry({
        "id": f"wb_tag_{slug[:40]}",
        "title": f"{title} · tag 消费",
        "trigger": normalized_tag,
        "entry_type": "external_tag",
        "match_mode": "includes",
        "secondary_mode": "includes",
        "content": "\n".join(content_parts),
        "group": "状态联动",
        "order": len((project.get("worldbook") or {}).get("entries", [])),
        "priority": 20,
        "insertion_position": "after_char_defs",
        "prompt_layer": "current_state",
        "comment": f"自动补齐的世界书消费者，对应 database tag: {normalized_tag}",
    }, len((project.get("worldbook") or {}).get("entries", [])))
    return build_json_patch_candidate(
        "worldbook",
        "worldbook.entries",
        "append",
        None,
        entry,
        f"补齐 tag 消费者 · {title}",
        "数据库 tag 需要世界书 external_tag 或演出工坊消费；这里先补一个可审核的世界书消费者，保证运行包联动不断链。",
        {
            "group_id": "tag_consumer_link",
            "group_title": "tag 消费闭环",
            "container_role": "消费数据库阶段 tag，让状态能实际影响角色表现",
            "depends_on": [normalize_text(source_candidate.get("group_id")) or "database_mechanism"],
            "draft_only": True,
        },
    )


def ensure_copilot_tag_consumers(candidates: list[dict[str, Any]], project: dict[str, Any]) -> None:
    consumed_tags: set[str] = set()
    existing_entries = (project.get("worldbook") or {}).get("entries", [])
    for entry in existing_entries if isinstance(existing_entries, list) else []:
        if not isinstance(entry, dict):
            continue
        if normalize_text(entry.get("entry_type")).lower() != "external_tag":
            continue
        for key in ["trigger", "secondary_trigger"]:
            for value in split_tags(entry.get(key, "")):
                if value:
                    consumed_tags.add(value)
    for candidate in candidates:
        for tag in extract_candidate_consumed_tags(candidate):
            consumed_tags.add(tag)

    additions: list[dict[str, Any]] = []
    for candidate in list(candidates):
        for tag in extract_candidate_emitted_tags(candidate):
            if tag in consumed_tags:
                continue
            consumer = build_worldbook_consumer_candidate_for_tag(tag, candidate, project)
            if not consumer:
                continue
            additions.append(consumer)
            consumed_tags.add(tag)
    candidates.extend(additions)


def annotate_copilot_tag_consumers(candidates: list[dict[str, Any]]) -> None:
    consumed_tags: set[str] = set()
    for candidate in candidates:
        tags = extract_candidate_consumed_tags(candidate)
        if tags:
            candidate["consumes_tags"] = tags
            consumed_tags.update(tags)
    for candidate in candidates:
        emitted_tags = extract_candidate_emitted_tags(candidate)
        if not emitted_tags:
            continue
        missing = [tag for tag in emitted_tags if tag not in consumed_tags]
        if emitted_tags:
            candidate["emits_tags"] = emitted_tags
        if missing:
            candidate["tag_warnings"] = [
                f"{tag} 当前只是设计草稿，后续需要世界书 external_tag 或演出工坊消费。"
                for tag in missing
            ]


def build_copilot_package_audit(candidates: list[dict[str, Any]], plan: dict[str, Any] | None = None) -> dict[str, Any]:
    plan_data = plan if isinstance(plan, dict) else {}
    modules: list[str] = []
    for candidate in candidates:
        module = normalize_text(candidate.get("module"))
        if module and module not in modules:
            modules.append(module)

    emitted_tags: list[str] = []
    consumed_tags: list[str] = []
    for candidate in candidates:
        for tag in extract_candidate_emitted_tags(candidate):
            if tag not in emitted_tags:
                emitted_tags.append(tag)
        for tag in extract_candidate_consumed_tags(candidate):
            if tag not in consumed_tags:
                consumed_tags.append(tag)

    plan_required_raw = plan_data.get("required_containers")
    required = []
    if isinstance(plan_required_raw, list):
        for item in plan_required_raw:
            module = normalize_text(item)
            if module in {"persona", "worldbook", "memory", "database", "preset"} and module not in required:
                required.append(module)
    if not required and normalize_text(plan_data.get("package_mode")) == "runtime_package":
        required = ["persona", "worldbook", "memory", "database"]
    missing_containers = [module for module in required if module not in modules]
    missing_tag_consumers = [tag for tag in emitted_tags if tag not in consumed_tags]
    has_light_preset = "preset" in modules
    warnings: list[str] = []
    if missing_containers:
        warnings.append(f"运行包候选缺少容器：{', '.join(missing_containers)}。")
    if missing_tag_consumers:
        warnings.append(f"有数据库 tag 暂未被世界书 external_tag 消费：{', '.join(missing_tag_consumers)}。")
    if not has_light_preset:
        warnings.append("没有轻量预设适配候选；若已有外部预设可忽略。")

    return {
        "package_mode": normalize_text(plan_data.get("package_mode")) or ("runtime_package" if len(modules) > 1 else "single_edit"),
        "modules": modules,
        "required_containers": required,
        "missing_containers": missing_containers,
        "emitted_tags": emitted_tags,
        "consumed_tags": consumed_tags,
        "missing_tag_consumers": missing_tag_consumers,
        "has_light_preset": has_light_preset,
        "ready": not missing_tag_consumers and not missing_containers,
        "warnings": warnings,
    }


def build_project_runtime_package_audit(project: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_project(project)
    modules: list[str] = []
    persona = normalized.get("persona_card") or {}
    if any(normalize_text(persona.get(key)) for key in PERSONA_FIELDS) or persona.get("tags"):
        modules.append("persona")
    worldbook_entries = (normalized.get("worldbook") or {}).get("entries", [])
    if worldbook_entries:
        modules.append("worldbook")
    memory_items = (normalized.get("memory") or {}).get("items", [])
    if memory_items:
        modules.append("memory")
    preset_items = (normalized.get("preset") or {}).get("presets", [])
    if preset_items:
        modules.append("preset")
    database = normalized.get("database") or {}
    if database.get("variables") or database.get("stages") or database.get("tags"):
        modules.append("database")

    emitted_tags: list[str] = []
    for stage in database.get("stages", []):
        for tag in split_tags(stage.get("emits_tags") or stage.get("active_tag") or []):
            if tag not in emitted_tags:
                emitted_tags.append(tag)
    for tag_item in database.get("tags", []):
        tag = normalize_text(tag_item.get("tag"))
        if tag and tag not in emitted_tags:
            emitted_tags.append(tag)

    consumed_tags: list[str] = []
    for entry in worldbook_entries:
        if not isinstance(entry, dict) or normalize_text(entry.get("entry_type")).lower() != "external_tag":
            continue
        for tag in split_tags(entry.get("trigger", "")):
            if tag not in consumed_tags:
                consumed_tags.append(tag)
        for tag in split_tags(entry.get("secondary_trigger", "")):
            if tag not in consumed_tags:
                consumed_tags.append(tag)

    missing_tag_consumers = [tag for tag in emitted_tags if tag not in consumed_tags]
    return {
        "modules": modules,
        "emitted_tags": emitted_tags,
        "consumed_tags": consumed_tags,
        "missing_tag_consumers": missing_tag_consumers,
        "ready": not missing_tag_consumers and all(module in modules for module in ["persona", "worldbook", "memory", "database"]),
    }


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
    ensure_copilot_tag_consumers(result, project)
    annotate_copilot_tag_consumers(result)
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
    if not parts or not all(parts) or parts[0] not in {"persona_card", "worldbook", "preset", "memory", "database"}:
        return False
    blocked = {"version", "type", "updated_at", "__proto__", "prototype", "constructor"}
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


def build_json_patch_candidate(module_name: str, path: str, operation: str, before: Any, after: Any, label: str, reason: str, metadata: dict[str, Any] | None = None) -> dict[str, Any] | None:
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
        metadata=metadata,
    )


def build_copilot_candidate_from_raw(
    raw: dict[str, Any],
    *,
    module: str,
    action: str,
    label: str,
    reason: str,
    target: dict[str, Any],
    before: Any,
    after: Any,
) -> dict[str, Any]:
    return build_copilot_candidate(
        module=module,
        action=action,
        label=label,
        reason=reason,
        target=target,
        before=before,
        after=after,
        metadata=raw,
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
            raw,
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
        raw,
    )


def normalize_single_copilot_candidate(raw: Any, project: dict[str, Any]) -> dict[str, Any] | list[dict[str, Any]] | None:
    if not isinstance(raw, dict):
        return None
    module_name = str(raw.get("module") or "").strip().lower()
    if module_name not in {"persona", "worldbook", "preset", "memory", "database"}:
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
            return build_copilot_candidate_from_raw(
                raw,
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
        return build_copilot_candidate_from_raw(
            raw,
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
            return build_copilot_candidate_from_raw(
                raw,
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
        return build_copilot_candidate_from_raw(
            raw,
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
            return build_copilot_candidate_from_raw(
                raw,
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
        return build_copilot_candidate_from_raw(
            raw,
            module="preset",
            action="update_array_item",
            label=label or f"更新预设 · {after_value.get('name') or item_id}",
            reason=reason or "根据你的要求改写预设。",
            target={"id": item_id, "index": index},
            before=before_value,
            after=after_value,
        )

    if module_name == "database":
        kind = normalize_database_kind(target.get("kind") or raw.get("kind")) or "variables"
        if action == "append_array_item":
            index = len((project.get("database") or {}).get(kind, []))
            after_value = normalize_database_item(kind, raw.get("after"), index)
            label_value = after_value.get("label") or after_value.get("title") or after_value.get("key") or after_value.get("tag") or "新草稿"
            return build_copilot_candidate_from_raw(
                raw,
                module="database",
                action=action,
                label=label or f"新增数据库草稿 · {label_value}",
                reason=reason or "根据你的要求补充变量、阶段或 tag 草稿。",
                target={"kind": kind, "id": normalize_text(after_value.get("id")), "index": index},
                before=None,
                after=after_value,
            )
        item_id = normalize_text(target.get("id"))
        index, current_item = find_database_item(project, kind, item_id)
        if not current_item:
            return None
        after_value = normalize_database_item(kind, {**copy.deepcopy(current_item), **(raw.get("after") if isinstance(raw.get("after"), dict) else {})}, index)
        before_value = normalize_database_item(kind, raw.get("before") or current_item, index)
        label_value = after_value.get("label") or after_value.get("title") or after_value.get("key") or after_value.get("tag") or item_id
        return build_copilot_candidate_from_raw(
            raw,
            module="database",
            action="update_array_item",
            label=label or f"更新数据库草稿 · {label_value}",
            reason=reason or "根据你的要求改写数据库设计草稿。",
            target={"kind": kind, "id": item_id, "index": index},
            before=before_value,
            after=after_value,
        )

    if action == "append_array_item":
        index = len((project.get("memory") or {}).get("items", []))
        after_value = normalize_memory_item(raw.get("after"), index)
        return build_copilot_candidate_from_raw(
            raw,
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
    return build_copilot_candidate_from_raw(
        raw,
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
    module_labels = {"persona": "人设", "worldbook": "世界书", "preset": "预设", "memory": "记忆", "database": "数据库"}
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
        "plan": {
            "intent_type": "string",
            "package_mode": "runtime_package|single_edit|repair",
            "quality_goal": "string",
            "required_containers": ["persona|worldbook|preset|memory|database"],
            "container_plan": [
                {"module": "persona|worldbook|preset|memory|database", "role": "string"}
            ],
            "coverage": {
                "persona": "what persona covers",
                "worldbook": "what worldbook covers",
                "memory": "what memory covers",
                "database": "what database covers",
                "preset": "light adapter only"
            },
            "risks": ["string"]
        },
        "candidate_groups": [
            {
                "group_id": "stable_group_id",
                "group_title": "string",
                "reason": "string",
                "candidate_ids": ["optional; backend will rebuild this from candidates"],
                "depends_on": ["optional_group_id"],
                "draft_only": False
            }
        ],
        "candidates": [
            {
                "module": "persona|worldbook|preset|memory|database",
                "action": "json_patch",
                "label": "string",
                "reason": "string",
                "target": {
                    "path": "persona_card.name|worldbook.entries.0.content|preset.presets.0.base_system_prompt|memory.items.0.content|database.variables.0.description",
                    "operation": "set|delete|append"
                },
                "before": "current JSON value or null",
                "after": "final JSON value to set or append",
                "group_id": "stable_group_id",
                "group_title": "string",
                "container_role": "why this candidate belongs in this container",
                "depends_on": ["optional_group_id"],
                "draft_only": False
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
            "personas": {"1": PERSONA_SINGLE_DEFAULT},
        },
        "worldbook": {"settings": WORLDBOOK_SETTINGS_DEFAULTS, "entries": [WORLDBOOK_ENTRY_DEFAULT]},
        "preset": {"active_preset_id": "string", "presets": [PRESET_ITEM_DEFAULT]},
        "memory": {"items": [MEMORY_ITEM_DEFAULT]},
        "database": {
            "enabled": True,
            "notes": "string",
            "variables": [DATABASE_VARIABLE_DEFAULT],
            "stages": [DATABASE_STAGE_DEFAULT],
            "tags": [DATABASE_TAG_DEFAULT],
        },
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


def infer_explicit_persona_name(prompt_text: str) -> str:
    text = normalize_text(prompt_text)
    patterns = [
        r"(?:名叫|名字叫|名字是|叫做|叫)\s*[「“\"]?([^，。,.、；;\s「」“”\"']{1,32})[」”\"]?",
        r"([^，。,.、；;\s「」“”\"']{1,32})\s*(?:这个|这名|这位)?角色",
    ]
    blocked = {"一个", "一位", "一名", "当前", "原创", "现代幻想", "角色", "人设", "用户", "她", "他", "它"}
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        name = normalize_text(match.group(1))
        name = re.sub(r"^(一个|一位|一名|个|位|名)", "", name)
        name = re.split(r"(?:的|这个|这名|这位)?(?:现代|古代|原创|幻想|科幻|校园|都市|角色|人设|人物|女主|男主)", name, maxsplit=1)[0]
        name = name.strip("：:，。,.、；;「」“”\"'")
        if name and name not in blocked:
            return name[:32]
    return ""


def replace_text_value(value: Any, old: str, new: str) -> Any:
    if not old or old == new:
        return value
    if isinstance(value, str):
        return value.replace(old, new)
    if isinstance(value, list):
        return [replace_text_value(item, old, new) for item in value]
    if isinstance(value, dict):
        return {key: replace_text_value(item, old, new) for key, item in value.items()}
    return value


def enforce_explicit_persona_name(prompt_text: str, candidates: list[dict[str, Any]]) -> tuple[str, list[str]]:
    explicit_name = infer_explicit_persona_name(prompt_text)
    if not explicit_name:
        return "", []
    wrong_names: list[str] = []
    for candidate in candidates:
        target = candidate.get("target") if isinstance(candidate.get("target"), dict) else {}
        path = normalize_text(target.get("path"))
        if path == "persona_card.name":
            current_name = normalize_text(candidate.get("after"))
            if current_name and current_name != explicit_name and current_name not in wrong_names:
                wrong_names.append(current_name)
            candidate["after"] = explicit_name
            candidate["label"] = "填充 persona_card.name"
            reason = normalize_text(candidate.get("reason"))
            note = f"已按用户显式指定的角色名“{explicit_name}”纠正。"
            candidate["reason"] = f"{reason} {note}".strip() if reason else note
        elif path == "persona_card" and isinstance(candidate.get("after"), dict):
            after_card = copy.deepcopy(candidate.get("after"))
            current_name = normalize_text(after_card.get("name"))
            if current_name and current_name != explicit_name and current_name not in wrong_names:
                wrong_names.append(current_name)
            after_card["name"] = explicit_name
            candidate["after"] = after_card
            reason = normalize_text(candidate.get("reason"))
            note = f"已按用户显式指定的角色名“{explicit_name}”纠正。"
            if note not in reason:
                candidate["reason"] = f"{reason} {note}".strip() if reason else note
    if not wrong_names:
        return explicit_name, []
    for candidate in candidates:
        after_value = candidate.get("after")
        for wrong_name in wrong_names:
            after_value = replace_text_value(after_value, wrong_name, explicit_name)
        candidate["after"] = after_value
    return explicit_name, wrong_names


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
    reason = build_default_candidate_reason(current_view if current_view in {"persona", "worldbook", "preset", "memory", "database"} else "persona", current_view)
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
            "group_id": "persona_foundation",
            "group_title": "角色底座",
            "container_role": "补齐主卡底座字段",
        })

    if "世界" in prompt_line or "设定" in prompt_line or current_view == "worldbook":
        candidates.append({
            "module": "worldbook",
            "action": "json_patch",
            "label": "填充 worldbook.entries.0",
            "reason": "你的要求里提到了可补充的设定信息。",
            "target": {"path": "worldbook.entries.0", "operation": "append"},
            "before": None,
            "group_id": "worldbook_context",
            "group_title": "世界书承接",
            "container_role": "补充可被上下文检索的承接信息",
            "depends_on": ["persona_foundation"],
            "after": {
                "id": make_id("wb"),
                "title": f"{persona_after.get('name') or '角色'}相关设定",
                "trigger": ",".join([item for item in [persona_after.get("name"), *persona_after.get("tags", [])] if item]) or "关键词",
                "content": f"围绕“{prompt_line}”补充上下文设定，保证角色身份、关系张力和场景规则在后续对话中稳定出现。",
                "comment": "AI 候选修改，可再人工润色。",
            },
        })

    if "数据库" in prompt_line or "变量" in prompt_line or "tag" in prompt_line.lower() or current_view == "database":
        stage_tag = "state_journal.stage.main.trust_observe"
        candidates.append({
            "module": "database",
            "action": "json_patch",
            "label": "新增 database.variables 草稿",
            "reason": "你的要求里提到了变量、阶段或 tag，可先落为写卡器数据库设计草稿。",
            "target": {"path": "database.variables", "operation": "append"},
            "before": None,
            "group_id": "database_mechanism",
            "group_title": "数据库机制",
            "container_role": "设计可被后续规则读取的变量",
            "depends_on": ["persona_foundation"],
            "draft_only": True,
            "after": {
                "id": "db_var_001",
                "key": "trust",
                "label": "信任",
                "value_type": "number",
                "initial_value": "0",
                "scope": "role",
                "description": f"围绕“{prompt_line}”追踪角色对 {{user}} 的信任变化。",
                "write_policy": "只根据明确互动和已发生记忆变化；不要单轮大幅跳变。",
                "notes": "AI fallback 草稿，可在数据库视图继续拆成阶段和 tag。",
            },
        })

        candidates.append({
            "module": "database",
            "action": "json_patch",
            "label": "新增 database.stages 草稿",
            "reason": "数据库联动需要阶段判断和可发出的 tag，先落为可审核的阶段草稿。",
            "target": {"path": "database.stages", "operation": "append"},
            "before": None,
            "group_id": "database_mechanism",
            "group_title": "数据库机制",
            "container_role": "把变量变化转换成阶段 tag",
            "depends_on": ["persona_foundation"],
            "draft_only": True,
            "after": {
                "id": "db_stage_trust_observe",
                "role_id": "main",
                "stage_key": "trust_observe",
                "title": "信任观察",
                "condition": "trust 处于低到中间区间，角色开始观察 {{user}} 是否稳定、尊重边界。",
                "active_tag": stage_tag,
                "emits_tags": [stage_tag],
                "description": "该阶段用于让角色保持试探和迟疑，不直接跳到完全信任。",
                "notes": "AI fallback 阶段草稿；应用时会补齐世界书 external_tag 消费者。",
            },
        })

        if "tag" in prompt_line.lower() or current_view == "database":
            candidates.append({
                "module": "database",
                "action": "json_patch",
                "label": "新增 database.tags 草稿",
                "reason": "用户要求包含 tag；先生成可审核的数据库 tag 草稿，后续需要世界书或演出工坊消费。",
                "target": {"path": "database.tags", "operation": "append"},
                "before": None,
                "group_id": "database_mechanism",
                "group_title": "数据库机制",
                "container_role": "发出阶段 tag，等待世界书或演出工坊消费",
                "depends_on": ["persona_foundation"],
                "draft_only": True,
                "after": {
                    "id": "db_tag_trust_observe",
                    "tag": stage_tag,
                    "title": "信任观察",
                    "trigger": stage_tag,
                    "target": "worldbook",
                    "description": f"围绕“{prompt_line}”预留的阶段 tag；若要生效，需要世界书 external_tag 或演出工坊消费。",
                    "notes": "AI fallback tag 草稿。",
                },
            })

    fallback_groups = build_default_candidate_groups(candidates)
    fallback_plan = normalize_copilot_plan({
        "intent_type": "fallback_review",
        "quality_goal": "根据当前请求生成可安全应用的候选修改。",
        "required_containers": [candidate.get("module") for candidate in candidates],
        "container_plan": [
            {"module": candidate.get("module"), "role": candidate.get("reason") or candidate.get("label")}
            for candidate in candidates
        ],
    }, candidates)
    return {
        "summary": f"已根据整张卡整理出 {len(candidates)} 条候选修改，请选择 YES 填充或 NO 取消。",
        "plan": fallback_plan,
        "candidate_groups": fallback_groups,
        "candidates": candidates,
    }


def build_copilot_module_prompt(module_name: str, settings: dict[str, Any]) -> str:
    prompt_map = {
        "persona": normalize_text(settings.get("persona_prompt")),
        "worldbook": normalize_text(settings.get("worldbook_prompt")),
        "preset": normalize_text(settings.get("preset_prompt")),
        "memory": normalize_text(settings.get("memory_prompt")),
        "database": normalize_text(settings.get("database_prompt")),
    }
    return prompt_map.get(module_name, "")


def normalize_copilot_thinking_mode(value: Any) -> str:
    mode = normalize_text(value).lower()
    return "deep" if mode in {"deep", "depth", "think", "slow", "full"} else "fast"


def load_human_character_prompt_pack(thinking_mode: str = "fast") -> list[str]:
    prompts: list[str] = []
    filenames = list(HUMAN_CHARACTER_PROMPT_FILES)
    is_deep = normalize_copilot_thinking_mode(thinking_mode) == "deep"
    if is_deep:
        filenames.extend(HUMAN_CHARACTER_DEEP_PROMPT_FILES)
    for filename in filenames:
        path = HUMAN_CHARACTER_PROMPT_DIR / filename
        try:
            text = path.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if text:
            prompts.append(text)
    return prompts


def build_copilot_system_prompt(current_view: str, focus_hint: dict[str, Any], settings: dict[str, Any], thinking_mode: str = "fast") -> str:
    schema = build_copilot_candidate_schema()
    thinking_mode = normalize_copilot_thinking_mode(thinking_mode)
    shared_prompt = normalize_text(settings.get("base_system_prompt")) or DEFAULT_COPILOT_SETTINGS["base_system_prompt"]
    human_prompts = load_human_character_prompt_pack(thinking_mode)
    module_prompts = [
        build_copilot_module_prompt("persona", settings),
        build_copilot_module_prompt("worldbook", settings),
        build_copilot_module_prompt("preset", settings),
        build_copilot_module_prompt("memory", settings),
        build_copilot_module_prompt("database", settings),
    ]
    focus_title = normalize_text(focus_hint.get("title")) or "当前卡"
    focus_subtitle = normalize_text(focus_hint.get("subtitle"))
    return "\n\n".join([
        shared_prompt,
        *human_prompts,
        "你现在负责分析整张 Card Writer 工程，而不是只重写当前条目。",
        f"当前轮椅思考模式是：{'深度思考' if thinking_mode == 'deep' else '快速模式'}。",
        f"当前视图是 {current_view}，当前焦点提示是：{focus_title}。",
        focus_subtitle or "焦点提示仅用于帮助你理解用户此刻在看哪里，不限制修改范围。",
        "必须读取 user payload 里的 json_schema 和 project：json_schema 是当前写卡器允许填充的容器键结构，project 是当前实际内容。",
        "优先输出 action=json_patch：target.path 必须精确匹配 json_schema/project 中的点路径，例如 persona_card.name、persona_card.tags、worldbook.entries.0.content、memory.items.0.tags。",
        "json_patch 的 target.operation 只允许 set、delete、append；after 必须是该路径要写入或追加的 JSON 值，不要包一层无关对象。",
        "除非是在数组上追加整条 entry/item，否则不要输出整块对象；普通填卡必须一键一候选，例如 persona_card.name 一条、persona_card.description 一条。",
        "禁止输出空字符串、空数组、空对象作为 after；不确定就不要生成该候选。",
        "输出必须是候选修改列表，让用户自己选择 YES/NO 后再应用。不要直接返回整张卡，不要输出解释性文字。",
        "如果用户要求生成人设卡、角色卡或自动填充，请分别给出 persona_card.name、description、personality、scenario、first_mes、mes_example、creator_notes、tags 等键的 json_patch 候选。",
        "如果用户给出角色名、世界名、地点名或关系名，必须原样沿用；不要从案例、示例或参考材料中借用名字。",
        "禁止把用户要求原样塞进 description，也禁止输出“应填写/需要生成/建议补充某字段”这类元说明；after 必须是最终要填入表单的内容。",
        "只返回与用户要求直接相关的修改，避免无关大改。候选 action 优先使用 json_patch；兼容动作只允许 replace_field、update_array_item、append_array_item。",
        "当前阶段允许 module 为 persona、worldbook、preset、memory、database；database 只代表写卡器工程里的数据库设计草稿，不代表运行时 SQLite 或真实 state_journal 写入。",
        "当前目标是角色运行包：让 persona、worldbook、memory、database 形成可运行闭环；preset 只做轻量适配纪律，不生成高阶预设、复杂风格库或大型叙事引擎。",
        "生成 database tag 或 stage 时，必须优先同时生成 worldbook external_tag 消费者；如果你漏掉，后端会补齐一个草稿消费者供用户审核。",
        "database.tags[].trigger 是触发条件或说明，不是世界书 external_tag 的 trigger；世界书 external_tag.trigger 必须等于 database.tags[].tag 或 database.stages[].active_tag。",
        "深度思考模式必须先完成意图识别、人化诊断、运行包容器规划和 tag 消费者检查；可以把结果压缩到 plan 与 candidate_groups 字段，但不要输出长篇推理过程。",
        "深度思考模式的 summary 要简短说明本轮候选涉及哪些容器以及各自承担的作用，不要写内部推理过程。",
        "P2.5 允许输出 plan.package_mode、plan.coverage、candidate_groups，以及候选上的 group_id、group_title、container_role、depends_on、draft_only；这些都是 review UI 元信息，真正写入仍只依赖 candidates 的 module/action/target/before/after。",
        "不要输出 analysis、markdown、代码块或额外解释；必须只返回符合 schema 的 JSON 对象。",
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
    thinking_mode: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    url = build_copilot_api_url(config["base_url"], "chat/completions")
    settings = get_copilot_settings()
    payload = {
        "model": config["model"],
        "messages": [
            {"role": "system", "content": build_copilot_system_prompt(current_view, focus_hint, settings, thinking_mode)},
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


def normalize_database_kind(value: Any) -> str:
    kind = normalize_text(value).lower()
    aliases = {
        "variable": "variables",
        "variables": "variables",
        "var": "variables",
        "stage": "stages",
        "stages": "stages",
        "tag": "tags",
        "tags": "tags",
    }
    return aliases.get(kind, "")


def normalize_database_variable(value: Any, index: int) -> dict[str, Any]:
    raw = value if isinstance(value, dict) else {}
    data = copy.deepcopy(DATABASE_VARIABLE_DEFAULT)
    data["id"] = normalize_text(raw.get("id")) or f"db_var_{index + 1:03d}"
    for key in ["key", "label", "value_type", "initial_value", "scope", "description", "write_policy", "notes"]:
        data[key] = normalize_text(raw.get(key, data[key])) or data[key]
    return data


def normalize_database_stage(value: Any, index: int) -> dict[str, Any]:
    raw = value if isinstance(value, dict) else {}
    data = copy.deepcopy(DATABASE_STAGE_DEFAULT)
    data["id"] = normalize_text(raw.get("id")) or f"db_stage_{index + 1:03d}"
    for key in ["role_id", "stage_key", "title", "condition", "active_tag", "description", "notes"]:
        data[key] = normalize_text(raw.get(key, data[key])) or data[key]
    data["emits_tags"] = split_tags(raw.get("emits_tags", []))
    if not data["active_tag"] and data["role_id"] and data["stage_key"]:
        data["active_tag"] = f"state_journal.stage.{data['role_id']}.{data['stage_key']}"
    if not data["emits_tags"] and data["active_tag"]:
        data["emits_tags"] = [data["active_tag"]]
    return data


def normalize_database_tag(value: Any, index: int) -> dict[str, Any]:
    raw = value if isinstance(value, dict) else {}
    data = copy.deepcopy(DATABASE_TAG_DEFAULT)
    data["id"] = normalize_text(raw.get("id")) or f"db_tag_{index + 1:03d}"
    for key in ["tag", "title", "trigger", "target", "description", "notes"]:
        data[key] = normalize_text(raw.get(key, data[key])) or data[key]
    return data


def normalize_database_item(kind: str, value: Any, index: int) -> dict[str, Any]:
    normalized_kind = normalize_database_kind(kind) or "variables"
    if normalized_kind == "stages":
        return normalize_database_stage(value, index)
    if normalized_kind == "tags":
        return normalize_database_tag(value, index)
    return normalize_database_variable(value, index)


def normalize_database(value: Any) -> dict[str, Any]:
    raw = value if isinstance(value, dict) else {}
    variables_raw = raw.get("variables") if isinstance(raw.get("variables"), list) else []
    stages_raw = raw.get("stages") if isinstance(raw.get("stages"), list) else []
    tags_raw = raw.get("tags") if isinstance(raw.get("tags"), list) else []
    return {
        "enabled": as_bool(raw.get("enabled"), True),
        "notes": normalize_text(raw.get("notes")),
        "variables": [normalize_database_variable(item, index) for index, item in enumerate(variables_raw)],
        "stages": [normalize_database_stage(item, index) for index, item in enumerate(stages_raw)],
        "tags": [normalize_database_tag(item, index) for index, item in enumerate(tags_raw)],
    }


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

    if payload.get("type") == PROJECT_TYPE and any(key in payload for key in ["persona_card", "worldbook", "memory", "preset", "database"]):
        project = create_empty_project()
        project["version"] = as_int(payload.get("version"), 3)
        project["type"] = PROJECT_TYPE
        project["title"] = normalize_text(payload.get("title"))
        project["updated_at"] = normalize_text(payload.get("updated_at"))
        project["persona_card"] = normalize_persona_card(payload.get("persona_card"))
        project["worldbook"] = normalize_worldbook(payload.get("worldbook"))
        project["memory"] = normalize_memory(payload.get("memory"))
        project["preset"] = normalize_preset(payload.get("preset"))
        project["database"] = normalize_database(payload.get("database"))
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

    if looks_like_database(payload):
        project = create_empty_project()
        project["database"] = normalize_database(payload)
        project["title"] = "导入的数据库草稿"
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
    worldbooks_raw = payload.get("worldbooks") if isinstance(payload.get("worldbooks"), list) else []
    memories_raw = payload.get("memories") if isinstance(payload.get("memories"), list) else []
    presets_raw = payload.get("presets") if isinstance(payload.get("presets"), list) else []

    persona_map = normalize_personas_map(personas_raw)
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
        "personas": persona_map,
    }
    project["version"] = as_int(payload.get("version"), 2)
    project["title"] = normalize_text(payload.get("title")) or persona_card["name"]
    project["updated_at"] = normalize_text(payload.get("updated_at"))
    project["persona_card"] = normalize_persona_card(persona_card)
    project["worldbook"] = normalize_worldbook({"settings": copy.deepcopy(WORLDBOOK_SETTINGS_DEFAULTS), "entries": [legacy_worldbook_to_entry(item, index) for index, item in enumerate(worldbooks_raw)]})
    project["memory"] = normalize_memory({"items": [legacy_memory_to_item(item, index) for index, item in enumerate(memories_raw)]})
    project["preset"] = normalize_preset({"active_preset_id": "", "presets": [legacy_preset_to_item(item, index) for index, item in enumerate(presets_raw)]})
    project["database"] = normalize_database(payload.get("database"))
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


def looks_like_database(payload: dict[str, Any]) -> bool:
    database_keys = {"enabled", "notes", "variables", "stages", "tags"}
    if any(key not in database_keys for key in payload):
        return False
    if "variables" in payload or "stages" in payload:
        return True
    tags = payload.get("tags")
    return isinstance(tags, list) and any(isinstance(item, dict) and any(key in item for key in ["tag", "target", "trigger"]) for item in tags)


def looks_like_memory(payload: dict[str, Any]) -> bool:
    return list(payload.keys()) == ["items"] or "items" in payload


def looks_like_preset(payload: dict[str, Any]) -> bool:
    return "active_preset_id" in payload or "presets" in payload


def detect_import_target(payload: Any) -> str:
    if not isinstance(payload, dict):
        return "preview"
    if payload.get("type") == PROJECT_TYPE:
        return "preview"
    if payload.get("card") is None and payload.get("nodes"):
        return "persona"
    if looks_like_persona_card(payload):
        return "persona"
    if looks_like_worldbook(payload):
        return "worldbook"
    if looks_like_database(payload):
        return "database"
    if looks_like_memory(payload):
        return "memory"
    if looks_like_preset(payload):
        return "preset"
    return "preview"


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
    database = normalized.get("database") or {}
    if database.get("variables") or database.get("stages") or database.get("tags") or normalize_text(database.get("notes")):
        return True
    return False


FA_APPLY_MODULES = {"persona", "database", "worldbook", "preset", "memory"}
FA_PERSONA_APPLY_FIELDS = ["name", "description", "personality", "first_mes", "mes_example", "scenario", "creator_notes"]


def json_clone(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False))


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def normalize_fa_lookup(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "").strip().lower())


def normalize_fa_key(value: Any, fallback: str = "global") -> str:
    text = str(value or "").strip().lower() or fallback
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^a-z0-9_\-]+", "", text)
    text = re.sub(r"[_\-]{2,}", "_", text).strip("_-")
    return text or fallback


def preview_value(value: Any, limit: int = 180) -> str:
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False)
    else:
        text = str(value or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else f"{text[:limit]}..."


def make_fa_change(path: str, action: str, label: str, before: Any = "", after: Any = "") -> dict[str, Any]:
    return {
        "path": path,
        "action": action,
        "label": label,
        "before_preview": preview_value(before),
        "after_preview": preview_value(after),
    }


def make_fa_group(
    group_id: str,
    module: str,
    title: str,
    description: str,
    changes: list[dict[str, Any]],
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": group_id,
        "module": module,
        "title": title,
        "description": description,
        "enabled": bool(changes),
        "item_count": len(changes),
        "changes": changes,
        "warnings": warnings or [],
    }


def normalize_fa_modules(modules: list[str] | None = None) -> set[str]:
    selected = {str(item or "").strip().lower() for item in (modules or []) if str(item or "").strip()}
    selected = {item for item in selected if item in FA_APPLY_MODULES}
    return selected or set(FA_APPLY_MODULES)


def extract_fa_card_uid(card_payload: Any) -> str:
    payload = card_payload if isinstance(card_payload, dict) else {}
    raw = payload.get("raw") if isinstance(payload.get("raw"), dict) else payload
    state_journal = raw.get("stateJournal") if isinstance(raw.get("stateJournal"), dict) else {}
    for value in (
        payload.get("card_uid"),
        state_journal.get("card_uid"),
        raw.get("card_uid"),
        raw.get("uid"),
        raw.get("id"),
    ):
        text = normalize_fa_key(value, "")
        if text:
            return text
    return "global"


def fa_memories_path_for_card_uid(card_uid: str) -> Path:
    return FA_CARD_RUNTIME_CARDS_DIR / normalize_fa_key(card_uid, "global") / "memories.json"


def read_fa_current_card() -> dict[str, Any]:
    payload = read_json(FA_CURRENT_CARD_PATH, {})
    if not isinstance(payload, dict):
        payload = {}
    raw = payload.get("raw") if isinstance(payload.get("raw"), dict) else {}
    if not raw and any(key in payload for key in PERSONA_FIELDS):
        raw = {key: payload.get(key) for key in payload}
    card_uid = extract_fa_card_uid({"card_uid": payload.get("card_uid", ""), "raw": raw})
    return {
        "source_name": normalize_text(payload.get("source_name")),
        "card_uid": card_uid,
        "raw": raw if isinstance(raw, dict) else {},
    }


def read_fa_memories(card_uid: str) -> tuple[list[dict[str, Any]], Path]:
    primary_path = fa_memories_path_for_card_uid(card_uid)
    if primary_path.exists() or not FA_LEGACY_MEMORIES_PATH.exists():
        raw = read_json(primary_path, [])
        return raw if isinstance(raw, list) else [], primary_path
    raw = read_json(FA_LEGACY_MEMORIES_PATH, [])
    return raw if isinstance(raw, list) else [], FA_LEGACY_MEMORIES_PATH


def get_fa_state_journal_roles(raw_card: dict[str, Any]) -> list[dict[str, Any]]:
    state_journal = raw_card.get("stateJournal") if isinstance(raw_card.get("stateJournal"), dict) else {}
    roles = state_journal.get("roles") if isinstance(state_journal.get("roles"), list) else []
    if roles:
        return [role for role in roles if isinstance(role, dict)]

    fallback_roles: list[dict[str, Any]] = []
    main_name = normalize_text(raw_card.get("name")) or "main_card"
    fallback_roles.append({
        "role_id": "main_card",
        "role_name": main_name,
        "aliases": ["main_card", main_name],
        "enabled": True,
        "mode": "default",
        "stateJournalMode": "default",
        "variables": [],
        "stages": [],
        "snapshotFields": [],
        "initial_stage": "stage_a",
        "source": "main_card",
        "display_policy": "show",
    })
    personas = raw_card.get("personas") if isinstance(raw_card.get("personas"), dict) else {}
    for index, (key, persona) in enumerate(personas.items(), start=1):
        if not isinstance(persona, dict):
            continue
        role_id = f"current_card_{index}"
        role_name = normalize_text(persona.get("name")) or str(key)
        fallback_roles.append({
            "role_id": role_id,
            "role_name": role_name,
            "aliases": [str(key), role_id, role_name],
            "enabled": True,
            "mode": "default",
            "stateJournalMode": "default",
            "variables": [],
            "stages": [],
            "snapshotFields": [],
            "initial_stage": "stage_a",
            "source": "persona",
            "display_policy": "show",
        })
    return fallback_roles


def ensure_fa_state_journal(raw_card: dict[str, Any]) -> dict[str, Any]:
    state_journal = raw_card.get("stateJournal") if isinstance(raw_card.get("stateJournal"), dict) else {}
    state_journal = json_clone(state_journal)
    state_journal.setdefault("version", 1)
    state_journal["enabled"] = state_journal.get("enabled") is not False
    state_journal.setdefault("role_source_mode", "auto")
    roles = state_journal.get("roles") if isinstance(state_journal.get("roles"), list) else []
    if not roles:
        roles = get_fa_state_journal_roles(raw_card)
    state_journal["roles"] = [role for role in roles if isinstance(role, dict)]
    raw_card["stateJournal"] = state_journal
    return state_journal


def fa_role_lookup(roles: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for role in roles:
        keys = [
            role.get("role_id"),
            role.get("id"),
            role.get("role_name"),
            role.get("name"),
        ]
        aliases = role.get("aliases") if isinstance(role.get("aliases"), list) else []
        keys.extend(aliases)
        for key in keys:
            normalized = normalize_fa_lookup(key)
            if normalized:
                lookup[normalized] = role
    return lookup


def resolve_fa_role(role_hint: Any, roles: list[dict[str, Any]]) -> dict[str, Any] | None:
    hint = normalize_text(role_hint)
    if not hint or hint.lower() in {"role", "default", "auto", "global"}:
        return roles[0] if len(roles) == 1 else None
    return fa_role_lookup(roles).get(normalize_fa_lookup(hint))


def fa_number(value: Any, default: float = 0) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def state_journal_to_database(state_journal: Any) -> dict[str, Any]:
    journal = state_journal if isinstance(state_journal, dict) else {}
    database = copy.deepcopy(DATABASE_DEFAULT)
    variables: list[dict[str, Any]] = []
    stages: list[dict[str, Any]] = []
    tags: list[dict[str, Any]] = []
    seen_tags: set[str] = set()
    roles = journal.get("roles") if isinstance(journal.get("roles"), list) else []
    for role in roles:
        if not isinstance(role, dict):
            continue
        role_id = normalize_text(role.get("role_id") or role.get("id"))
        role_name = normalize_text(role.get("role_name") or role.get("name")) or role_id
        for index, variable in enumerate(role.get("variables") if isinstance(role.get("variables"), list) else [], start=1):
            if not isinstance(variable, dict):
                continue
            var_key = normalize_text(variable.get("var_key") or variable.get("key"))
            if not var_key:
                continue
            variables.append({
                "id": f"db_var_{role_id}_{var_key}" if role_id else f"db_var_{index}",
                "key": var_key,
                "label": normalize_text(variable.get("var_name") or variable.get("label")) or var_key,
                "value_type": "number",
                "initial_value": str(variable.get("default_value", "")),
                "scope": role_id or role_name or "role",
                "description": normalize_text(variable.get("instruction")),
                "write_policy": "",
                "notes": f"来自 Fa 角色：{role_name}",
            })
        for index, stage in enumerate(role.get("stages") if isinstance(role.get("stages"), list) else [], start=1):
            if not isinstance(stage, dict):
                continue
            stage_key = normalize_text(stage.get("stage_key") or stage.get("key"))
            if not stage_key:
                continue
            active_tag = normalize_text(stage.get("activation_tag")) or (f"state_journal.stage.{role_id}.{stage_key}" if role_id else "")
            stages.append({
                "id": f"db_stage_{role_id}_{stage_key}" if role_id else f"db_stage_{index}",
                "role_id": role_id,
                "stage_key": stage_key,
                "title": normalize_text(stage.get("stage_name") or stage.get("name")) or stage_key,
                "condition": summarize_fa_stage_conditions(stage.get("conditions")),
                "active_tag": active_tag,
                "emits_tags": [active_tag] if active_tag else [],
                "description": "",
                "notes": f"来自 Fa 角色：{role_name}",
            })
            if active_tag and active_tag not in seen_tags:
                seen_tags.add(active_tag)
                tags.append({
                    "id": f"db_tag_{role_id}_{stage_key}" if role_id else f"db_tag_{index}",
                    "tag": active_tag,
                    "title": normalize_text(stage.get("stage_name") or stage.get("name")) or stage_key,
                    "trigger": "由 stateJournal 阶段命中发出。",
                    "target": "worldbook",
                    "description": "",
                    "notes": f"来自 Fa 阶段：{role_name} / {stage_key}",
                })
    database["variables"] = variables
    database["stages"] = stages
    database["tags"] = tags
    return normalize_database(database)


def summarize_fa_stage_conditions(conditions: Any) -> str:
    if not isinstance(conditions, list):
        return ""
    parts: list[str] = []
    for condition in conditions:
        if not isinstance(condition, dict):
            continue
        var_key = normalize_text(condition.get("var") or condition.get("field"))
        op = normalize_text(condition.get("op")) or ">="
        value = condition.get("value", 0)
        if var_key:
            parts.append(f"{var_key} {op} {value}")
    return "；".join(parts)


def load_fa_context() -> dict[str, Any]:
    card_payload = read_fa_current_card()
    raw_card = card_payload.get("raw") if isinstance(card_payload.get("raw"), dict) else {}
    card_uid = extract_fa_card_uid(card_payload)
    memories, memories_path = read_fa_memories(card_uid)
    worldbook_store = read_json(FA_WORLDBOOK_PATH, {"settings": copy.deepcopy(WORLDBOOK_SETTINGS_DEFAULTS), "entries": []})
    if not isinstance(worldbook_store, dict):
        worldbook_store = {"settings": copy.deepcopy(WORLDBOOK_SETTINGS_DEFAULTS), "entries": []}
    preset_store = read_json(FA_PRESET_PATH, {"active_preset_id": "", "presets": []})
    if not isinstance(preset_store, dict):
        preset_store = {"active_preset_id": "", "presets": []}
    roles = get_fa_state_journal_roles(raw_card)
    active_preset_id = normalize_text(preset_store.get("active_preset_id"))
    presets = preset_store.get("presets") if isinstance(preset_store.get("presets"), list) else []
    active_preset = next((item for item in presets if isinstance(item, dict) and normalize_text(item.get("id")) == active_preset_id), None)
    entries = worldbook_store.get("entries") if isinstance(worldbook_store.get("entries"), list) else []
    return {
        "card": card_payload,
        "worldbook": worldbook_store,
        "preset": preset_store,
        "memories": memories,
        "memories_path": memories_path,
        "binding": {
            "loaded_at": now_text(),
            "card": {
                "source_name": card_payload.get("source_name", ""),
                "card_uid": card_uid,
                "name": normalize_text(raw_card.get("name")),
                "role_count": len(roles),
                "roles": [
                    {
                        "role_id": normalize_text(role.get("role_id") or role.get("id")),
                        "role_name": normalize_text(role.get("role_name") or role.get("name")),
                        "variables": len(role.get("variables") if isinstance(role.get("variables"), list) else []),
                        "stages": len(role.get("stages") if isinstance(role.get("stages"), list) else []),
                        "snapshotFields": len(role.get("snapshotFields") if isinstance(role.get("snapshotFields"), list) else []),
                    }
                    for role in roles
                ],
            },
            "worldbook": {
                "path": str(FA_WORLDBOOK_PATH),
                "entry_count": len(entries),
                "external_tag_count": sum(1 for item in entries if isinstance(item, dict) and normalize_text(item.get("entry_type")) == "external_tag"),
            },
            "preset": {
                "path": str(FA_PRESET_PATH),
                "active_preset_id": active_preset_id,
                "active_preset_name": normalize_text((active_preset or {}).get("name")) if isinstance(active_preset, dict) else "",
                "preset_count": len(presets),
            },
            "memory": {
                "path": str(memories_path),
                "item_count": len(memories),
            },
        },
    }


def build_project_from_fa_context(context: dict[str, Any]) -> dict[str, Any]:
    card_payload = context.get("card") if isinstance(context.get("card"), dict) else {}
    raw_card = card_payload.get("raw") if isinstance(card_payload.get("raw"), dict) else {}
    project = create_empty_project()
    project["title"] = normalize_text(raw_card.get("name")) or "当前 Fa 内容"
    project["persona_card"] = normalize_persona_card(raw_card)
    project["worldbook"] = normalize_worldbook(context.get("worldbook"))
    project["memory"] = normalize_memory({"items": context.get("memories") if isinstance(context.get("memories"), list) else []})
    project["preset"] = normalize_preset(context.get("preset"))
    project["database"] = state_journal_to_database(raw_card.get("stateJournal"))
    project["updated_at"] = now_text()
    return project


def merge_project_persona_into_card(card_payload: dict[str, Any], project: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    updated = json_clone(card_payload)
    raw = updated.get("raw") if isinstance(updated.get("raw"), dict) else {}
    raw = json_clone(raw)
    persona = project.get("persona_card") if isinstance(project.get("persona_card"), dict) else {}
    changes: list[dict[str, Any]] = []
    warnings: list[str] = []
    for key in FA_PERSONA_APPLY_FIELDS:
        after = normalize_text(persona.get(key))
        before = normalize_text(raw.get(key))
        if after == before:
            continue
        if not after and before:
            warnings.append(f"跳过清空字段 persona_card.{key}，避免误删当前角色卡内容。")
            continue
        raw[key] = after
        changes.append(make_fa_change(f"raw.{key}", "update", f"更新 {key}", before, after))

    after_tags = split_tags(persona.get("tags", []))
    before_tags = split_tags(raw.get("tags", []))
    if after_tags and after_tags != before_tags:
        raw["tags"] = after_tags
        changes.append(make_fa_change("raw.tags", "update", "更新 tags", before_tags, after_tags))

    project_personas = persona.get("personas") if isinstance(persona.get("personas"), dict) else {}
    raw_personas = raw.get("personas") if isinstance(raw.get("personas"), dict) else {}
    raw_personas = json_clone(raw_personas)
    for persona_key, next_persona in project_personas.items():
        if not isinstance(next_persona, dict):
            continue
        current_persona = raw_personas.get(persona_key) if isinstance(raw_personas.get(persona_key), dict) else {}
        merged_persona = json_clone(current_persona)
        persona_changed = False
        for key in ["name", "description", "personality", "scenario", "creator_notes"]:
            after = normalize_text(next_persona.get(key))
            before = normalize_text(current_persona.get(key))
            if after == before:
                continue
            if not after and before:
                warnings.append(f"跳过清空分身 {persona_key}.{key}。")
                continue
            merged_persona[key] = after
            persona_changed = True
            changes.append(make_fa_change(f"raw.personas.{persona_key}.{key}", "update", f"更新分身 {persona_key}.{key}", before, after))
        if persona_changed or persona_key not in raw_personas:
            raw_personas[persona_key] = merged_persona
    if raw_personas:
        raw["personas"] = raw_personas

    updated["raw"] = raw
    updated["card_uid"] = updated.get("card_uid") or extract_fa_card_uid(updated)
    return updated, changes, warnings


def build_fa_persona_from_role_card(card: dict[str, Any]) -> dict[str, str]:
    sections: list[str] = []
    for label, key in [
        ("Character Description", "description"),
        ("Personality", "personality"),
        ("Scenario", "scenario"),
        ("Creator Notes", "creator_notes"),
        ("Dialogue Example", "mes_example"),
    ]:
        value = normalize_text(card.get(key))
        if value:
            sections.append(f"{label}: {value}")

    personas = card.get("personas") if isinstance(card.get("personas"), dict) else {}
    persona_lines: list[str] = []
    persona_names: list[str] = []
    for key, value in personas.items():
        if not isinstance(value, dict):
            continue
        name = normalize_text(value.get("name")) or f"Persona {key}"
        persona_names.append(name)
        details = [
            normalize_text(value.get("description")),
            normalize_text(value.get("personality")),
            normalize_text(value.get("scenario")),
        ]
        detail_text = "; ".join(item for item in details if item)
        if detail_text:
            persona_lines.append(f"{name}: {detail_text}")
    if persona_lines:
        sections.append(
            "Multi-Character Cast Rules:\n"
            "This role card contains multiple active characters. Keep each character's name, voice, motive, and boundary separate. "
            "Do not merge different characters into one voice, and do not force every character to speak when the scene does not need it."
        )
        sections.append("Character Cast:\n" + "\n".join(persona_lines))

    return {
        "name": normalize_text(card.get("name")) or "Unnamed Character",
        "greeting": normalize_text(card.get("first_mes")) or "Hello, let's start chatting.",
        "system_prompt": "\n\n".join(section for section in sections if section).strip(),
    }


def database_variable_to_state(variable: dict[str, Any], index: int) -> dict[str, Any]:
    key = normalize_fa_key(variable.get("key") or variable.get("id"), f"var_{index}")
    default_value = fa_number(variable.get("initial_value"), 0)
    instruction_parts = [
        normalize_text(variable.get("description")),
        normalize_text(variable.get("write_policy")),
        normalize_text(variable.get("notes")),
    ]
    return {
        "var_key": key,
        "var_name": normalize_text(variable.get("label")) or key,
        "enabled": True,
        "default_value": default_value,
        "min_value": 0,
        "max_value": 100,
        "delta_min": -5,
        "delta_max": 5,
        "display": True,
        "stage_relevant": True,
        "instruction": "\n".join(part for part in instruction_parts if part),
    }


def parse_database_stage_conditions(condition_text: str, variable_keys: set[str]) -> tuple[list[dict[str, Any]], bool]:
    conditions: list[dict[str, Any]] = []
    text = normalize_text(condition_text)
    if not text:
        return conditions, True
    parts = re.split(r"(?:\n|；|;|，|,|、|\band\b|&&)+", text, flags=re.IGNORECASE)
    parsed_any = False
    for part in parts:
        match = re.search(r"([A-Za-z_][A-Za-z0-9_\-]*)\s*(>=|<=|==|!=|=|>|<)\s*(-?\d+(?:\.\d+)?)", part)
        if not match:
            continue
        var_key = normalize_fa_key(match.group(1), "")
        if variable_keys and var_key not in variable_keys:
            continue
        op = match.group(2)
        if op == "==":
            op = "="
        conditions.append({"var": var_key, "op": op, "value": fa_number(match.group(3), 0)})
        parsed_any = True
    return conditions, parsed_any


def database_stage_to_state(stage: dict[str, Any], index: int, variable_keys: set[str]) -> tuple[dict[str, Any], bool]:
    role_id = normalize_fa_key(stage.get("role_id"), "")
    stage_key = normalize_fa_key(stage.get("stage_key") or stage.get("id"), f"stage_{index}")
    active_tag = normalize_text(stage.get("active_tag")) or (f"state_journal.stage.{role_id}.{stage_key}" if role_id else "")
    conditions, parsed = parse_database_stage_conditions(normalize_text(stage.get("condition")), variable_keys)
    return {
        "stage_key": stage_key,
        "stage_name": normalize_text(stage.get("title")) or stage_key,
        "enabled": True,
        "priority": index * 10,
        "condition_mode": "all",
        "conditions": conditions,
        "allow_regression": False,
        "confirm_turns": 1,
        "cooldown_turns": 0,
        "activation_tag": active_tag,
    }, parsed


def update_role_state_mode(role: dict[str, Any]) -> None:
    has_vars = bool(role.get("variables"))
    has_stages = bool(role.get("stages"))
    has_snapshot = bool(role.get("snapshotFields"))
    if has_vars and has_stages:
        mode = "full"
    elif has_vars:
        mode = "variables"
    elif has_stages:
        mode = "stages"
    elif has_snapshot:
        mode = "snapshot_only"
    else:
        mode = role.get("mode") or role.get("stateJournalMode") or "default"
    role["mode"] = mode
    role["stateJournalMode"] = mode
    if mode != "default":
        role["has_state_journal_config"] = True
        role["display_policy"] = role.get("display_policy") or "show"


def merge_project_database_into_card(card_payload: dict[str, Any], project: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    updated = json_clone(card_payload)
    raw = updated.get("raw") if isinstance(updated.get("raw"), dict) else {}
    raw = json_clone(raw)
    state_journal = ensure_fa_state_journal(raw)
    roles = state_journal.get("roles") if isinstance(state_journal.get("roles"), list) else []
    lookup = fa_role_lookup(roles)
    database = normalize_database(project.get("database"))
    changes: list[dict[str, Any]] = []
    warnings: list[str] = []

    for index, variable in enumerate(database.get("variables") or [], start=1):
        role = resolve_fa_role(variable.get("scope"), roles)
        if role is None:
            warnings.append(f"变量 {variable.get('key') or variable.get('label') or index} 没有明确角色目标，请把 scope 改成 role_id 或角色名。")
            continue
        role.setdefault("variables", [])
        state_variable = database_variable_to_state(variable, index)
        existing = next((item for item in role["variables"] if isinstance(item, dict) and item.get("var_key") == state_variable["var_key"]), None)
        if existing and stable_json(existing) == stable_json(state_variable):
            continue
        if existing:
            existing.update(state_variable)
            action = "update"
        else:
            role["variables"].append(state_variable)
            action = "append"
        changes.append(make_fa_change(
            f"raw.stateJournal.roles.{role.get('role_id')}.variables.{state_variable['var_key']}",
            action,
            f"{role.get('role_name') or role.get('role_id')} / 变量 {state_variable['var_name']}",
            "",
            state_variable,
        ))

    for index, stage in enumerate(database.get("stages") or [], start=1):
        role_id = normalize_text(stage.get("role_id"))
        role = lookup.get(normalize_fa_lookup(role_id)) if role_id else None
        if role is None:
            warnings.append(f"阶段 {stage.get('stage_key') or stage.get('title') or index} 没有明确 role_id，无法写入角色卡 stateJournal。")
            continue
        role.setdefault("stages", [])
        variable_keys = {item.get("var_key") for item in role.get("variables") or [] if isinstance(item, dict) and item.get("var_key")}
        state_stage, parsed = database_stage_to_state(stage, index, variable_keys)
        if not parsed:
            warnings.append(f"阶段 {stage.get('stage_key') or index} 的 condition 未解析成结构化条件，已保留阶段但条件为空。")
        existing = next((item for item in role["stages"] if isinstance(item, dict) and item.get("stage_key") == state_stage["stage_key"]), None)
        if existing and stable_json(existing) == stable_json(state_stage):
            continue
        if existing:
            existing.update(state_stage)
            action = "update"
        else:
            role["stages"].append(state_stage)
            action = "append"
        if not normalize_text(role.get("initial_stage")) or role.get("initial_stage") == "stage_a":
            role["initial_stage"] = state_stage["stage_key"]
        changes.append(make_fa_change(
            f"raw.stateJournal.roles.{role.get('role_id')}.stages.{state_stage['stage_key']}",
            action,
            f"{role.get('role_name') or role.get('role_id')} / 阶段 {state_stage['stage_name']}",
            "",
            state_stage,
        ))

    for role in roles:
        if isinstance(role, dict):
            role.setdefault("snapshotFields", role.get("snapshotFields") if isinstance(role.get("snapshotFields"), list) else [])
            update_role_state_mode(role)
    raw["stateJournal"] = state_journal
    updated["raw"] = raw
    updated["card_uid"] = updated.get("card_uid") or extract_fa_card_uid(updated)
    return updated, changes, warnings


def worldbook_entry_signature(item: Any) -> str:
    raw = item if isinstance(item, dict) else {}
    fields = [
        normalize_text(raw.get("id")),
        normalize_text(raw.get("entry_type")),
        normalize_text(raw.get("title")),
        normalize_text(raw.get("trigger")),
        normalize_text(raw.get("content")),
    ]
    return stable_json(fields)


def is_worldbook_external_consumer(item: Any, tag: str) -> bool:
    raw = item if isinstance(item, dict) else {}
    wanted = normalize_text(tag)
    if not wanted:
        return False
    if normalize_text(raw.get("entry_type")) == "external_tag" and normalize_text(raw.get("trigger")) == wanted:
        return True
    activation_tags = raw.get("activation_tags") if isinstance(raw.get("activation_tags"), list) else []
    return wanted in [normalize_text(item) for item in activation_tags]


def collect_database_tags_for_worldbook(project: dict[str, Any]) -> list[dict[str, str]]:
    database = normalize_database(project.get("database"))
    tags: list[dict[str, str]] = []
    seen: set[str] = set()
    for stage in database.get("stages") or []:
        for tag in split_tags(stage.get("emits_tags") or ([stage.get("active_tag")] if stage.get("active_tag") else [])):
            if tag and tag not in seen:
                seen.add(tag)
                tags.append({
                    "tag": tag,
                    "title": normalize_text(stage.get("title")) or tag,
                    "content": normalize_text(stage.get("description") or stage.get("notes")) or f"当状态 tag「{tag}」激活时，按对应阶段表现约束角色反应。",
                })
    for item in database.get("tags") or []:
        tag = normalize_text(item.get("tag"))
        if tag and tag not in seen:
            seen.add(tag)
            tags.append({
                "tag": tag,
                "title": normalize_text(item.get("title")) or tag,
                "content": normalize_text(item.get("description") or item.get("notes") or item.get("trigger")) or f"当 tag「{tag}」激活时，注入对应表现约束。",
            })
    return tags


def build_worldbook_external_tag_entry(tag_item: dict[str, str], order: int) -> dict[str, Any]:
    tag = normalize_text(tag_item.get("tag"))
    return {
        "id": make_id("wbtag"),
        "title": normalize_text(tag_item.get("title")) or tag,
        "trigger": tag,
        "secondary_trigger": "",
        "entry_type": "external_tag",
        "group_operator": "and",
        "match_mode": "includes",
        "secondary_mode": "includes",
        "content": normalize_text(tag_item.get("content")),
        "group": "state_journal",
        "chance": 100,
        "sticky_turns": 0,
        "cooldown_turns": 0,
        "order": order,
        "priority": order,
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
        "activation_tags": [tag],
        "external_source": "card_writer",
        "external_ref": {"source": "card_writer_p3", "tag": tag},
        "comment": "Card Writer P3 自动补齐的 stateJournal tag 消费者。",
    }


def merge_project_worldbook(worldbook_store: dict[str, Any], project: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    updated = json_clone(worldbook_store if isinstance(worldbook_store, dict) else {})
    updated.setdefault("settings", copy.deepcopy(WORLDBOOK_SETTINGS_DEFAULTS))
    current_entries = updated.get("entries") if isinstance(updated.get("entries"), list) else []
    current_entries = [item for item in current_entries if isinstance(item, dict)]
    signatures = {worldbook_entry_signature(item) for item in current_entries}
    existing_ids = {normalize_text(item.get("id")) for item in current_entries if isinstance(item, dict) and normalize_text(item.get("id"))}
    changes: list[dict[str, Any]] = []
    warnings: list[str] = []
    appended: list[dict[str, Any]] = []
    project_entries = (project.get("worldbook") or {}).get("entries", [])

    for item in project_entries if isinstance(project_entries, list) else []:
        if not isinstance(item, dict):
            continue
        normalized = normalize_worldbook_entry(item, len(current_entries) + len(appended))
        entry_id = normalize_text(normalized.get("id"))
        signature = worldbook_entry_signature(normalized)
        if (entry_id and entry_id in existing_ids) or signature in signatures:
            continue
        entry_type = normalize_text(normalized.get("entry_type")) or "keyword"
        content = normalize_text(normalized.get("content"))
        trigger = normalize_text(normalized.get("trigger"))
        if not content:
            warnings.append(f"跳过世界书「{normalized.get('title') or entry_id}」：正文为空。")
            continue
        if entry_type not in {"constant", "external_tag"} and not trigger:
            warnings.append(f"跳过世界书「{normalized.get('title') or entry_id}」：非 constant/external_tag 条目需要 trigger。")
            continue
        if entry_type == "external_tag":
            normalized["activation_tags"] = [trigger] if trigger else []
            normalized["external_source"] = normalized.get("external_source") or "card_writer"
            normalized["external_ref"] = normalized.get("external_ref") or {"source": "card_writer_p3", "tag": trigger}
        appended.append(normalized)
        signatures.add(signature)
        if entry_id:
            existing_ids.add(entry_id)
        changes.append(make_fa_change(
            f"worldbook.entries.{len(current_entries) + len(appended) - 1}",
            "append",
            f"追加世界书：{normalized.get('title') or trigger or entry_id}",
            "",
            normalized,
        ))

    all_entries_for_tag_check = current_entries + appended
    for tag_item in collect_database_tags_for_worldbook(project):
        tag = normalize_text(tag_item.get("tag"))
        if not tag or any(is_worldbook_external_consumer(item, tag) for item in all_entries_for_tag_check):
            continue
        generated = build_worldbook_external_tag_entry(tag_item, len(current_entries) + len(appended))
        appended.append(generated)
        all_entries_for_tag_check.append(generated)
        changes.append(make_fa_change(
            f"worldbook.entries.{len(current_entries) + len(appended) - 1}",
            "append",
            f"补齐 tag 消费者：{tag}",
            "",
            generated,
        ))

    updated["entries"] = current_entries + appended
    return updated, changes, warnings


def active_preset_from_store(store: dict[str, Any]) -> dict[str, Any] | None:
    presets = store.get("presets") if isinstance(store.get("presets"), list) else []
    active_id = normalize_text(store.get("active_preset_id"))
    if active_id:
        found = next((item for item in presets if isinstance(item, dict) and normalize_text(item.get("id")) == active_id), None)
        if found:
            return found
    return next((item for item in presets if isinstance(item, dict)), None)


def merge_project_preset(preset_store: dict[str, Any], project: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    updated = json_clone(preset_store if isinstance(preset_store, dict) else {})
    updated.setdefault("active_preset_id", "")
    updated.setdefault("presets", [])
    current_active = active_preset_from_store(updated)
    project_preset = normalize_preset(project.get("preset"))
    project_active = active_preset_from_store(project_preset)
    changes: list[dict[str, Any]] = []
    warnings: list[str] = []
    if not current_active or not project_active:
        warnings.append("没有找到当前 active preset，跳过预设应用。")
        return updated, changes, warnings

    current_modules = current_active.get("modules") if isinstance(current_active.get("modules"), dict) else {}
    project_modules = project_active.get("modules") if isinstance(project_active.get("modules"), dict) else {}
    merged_modules = {**current_modules, **project_modules}
    if stable_json(merged_modules) != stable_json(current_modules):
        current_active["modules"] = merged_modules
        changes.append(make_fa_change("preset.active.modules", "update", "合并 active preset modules", current_modules, merged_modules))

    current_extra = current_active.get("extra_prompts") if isinstance(current_active.get("extra_prompts"), list) else []
    current_ids = {normalize_text(item.get("id")) for item in current_extra if isinstance(item, dict) and normalize_text(item.get("id"))}
    current_sigs = {stable_json([normalize_text(item.get("name")), normalize_text(item.get("content"))]) for item in current_extra if isinstance(item, dict)}
    project_extra = project_active.get("extra_prompts") if isinstance(project_active.get("extra_prompts"), list) else []
    for index, item in enumerate(project_extra):
        if not isinstance(item, dict):
            continue
        normalized = normalize_extra_prompt(item, len(current_extra) + index)
        if not normalize_text(normalized.get("content")):
            continue
        item_id = normalize_text(normalized.get("id"))
        sig = stable_json([normalize_text(normalized.get("name")), normalize_text(normalized.get("content"))])
        if (item_id and item_id in current_ids) or sig in current_sigs:
            continue
        current_extra.append(normalized)
        if item_id:
            current_ids.add(item_id)
        current_sigs.add(sig)
        changes.append(make_fa_change("preset.active.extra_prompts", "append", f"追加子提示：{normalized.get('name') or item_id}", "", normalized))
    current_active["extra_prompts"] = current_extra

    if normalize_text(project_active.get("base_system_prompt")) != normalize_text(current_active.get("base_system_prompt")):
        warnings.append("检测到 base_system_prompt 差异；P3 MVP 不自动覆盖高阶预设正文，请在预设页手动确认或导出处理。")
    if stable_json(project_active.get("prompt_groups") or []) != stable_json(current_active.get("prompt_groups") or []):
        warnings.append("检测到 prompt_groups 差异；P3 MVP 不自动覆盖高阶 prompt_groups。")
    return updated, changes, warnings


def merge_project_memories(memories: list[dict[str, Any]], project: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    current = json_clone(memories if isinstance(memories, list) else [])
    existing_ids = {normalize_text(item.get("id")) for item in current if isinstance(item, dict) and normalize_text(item.get("id"))}
    existing_sigs = {stable_json([normalize_text(item.get("title")), normalize_text(item.get("content"))]) for item in current if isinstance(item, dict)}
    changes: list[dict[str, Any]] = []
    warnings: list[str] = []
    project_items = ((project.get("memory") or {}).get("items") if isinstance(project.get("memory"), dict) else [])
    for index, item in enumerate(project_items if isinstance(project_items, list) else [], start=1):
        if not isinstance(item, dict):
            continue
        normalized = normalize_memory_item(item, len(current) + index)
        if not normalize_text(normalized.get("content")):
            continue
        item_id = normalize_text(normalized.get("id"))
        sig = stable_json([normalize_text(normalized.get("title")), normalize_text(normalized.get("content"))])
        if (item_id and item_id in existing_ids) or sig in existing_sigs:
            continue
        normalized["memory_status"] = normalize_text(item.get("memory_status")) or "active"
        normalized["archived_at"] = normalize_text(item.get("archived_at")) if normalized["memory_status"] == "archived" else ""
        current.append(normalized)
        if item_id:
            existing_ids.add(item_id)
        existing_sigs.add(sig)
        changes.append(make_fa_change(f"memories.{len(current) - 1}", "append", f"追加记忆：{normalized.get('title') or item_id}", "", normalized))
    return current, changes, warnings


def build_fa_apply_plan(project: dict[str, Any], modules: list[str] | None = None) -> dict[str, Any]:
    normalized_project = normalize_project(project)
    selected_modules = normalize_fa_modules(modules)
    context = load_fa_context()
    groups: list[dict[str, Any]] = []
    warnings: list[str] = []

    if "persona" in selected_modules:
        _next_card, changes, group_warnings = merge_project_persona_into_card(context["card"], normalized_project)
        groups.append(make_fa_group("persona", "persona", "角色卡主字段", "把写卡器里的人设主字段与分身字段增量写回当前角色卡。", changes, group_warnings))
        warnings.extend(group_warnings)
    if "database" in selected_modules:
        _next_card, changes, group_warnings = merge_project_database_into_card(context["card"], normalized_project)
        groups.append(make_fa_group("database", "database", "角色卡 stateJournal", "把数据库草稿里的变量与阶段写入角色卡 stateJournal；不写运行时 SQLite。", changes, group_warnings))
        warnings.extend(group_warnings)
    if "worldbook" in selected_modules:
        _next_worldbook, changes, group_warnings = merge_project_worldbook(context["worldbook"], normalized_project)
        groups.append(make_fa_group("worldbook", "worldbook", "世界书增量条目", "只追加新世界书条目，并补齐缺失的 external_tag 消费者。", changes, group_warnings))
        warnings.extend(group_warnings)
    if "preset" in selected_modules:
        _next_preset, changes, group_warnings = merge_project_preset(context["preset"], normalized_project)
        groups.append(make_fa_group("preset", "preset", "Active preset 轻量增强", "只合并 modules 与追加 extra_prompts，不覆盖高阶预设正文和 prompt_groups。", changes, group_warnings))
        warnings.extend(group_warnings)
    if "memory" in selected_modules:
        _next_memories, changes, group_warnings = merge_project_memories(context["memories"], normalized_project)
        groups.append(make_fa_group("memory", "memory", "标准记忆增量", "只向当前角色的标准 memories.json 追加新记忆，不触碰合并记忆和大纲表。", changes, group_warnings))
        warnings.extend(group_warnings)

    return {
        "ok": True,
        "binding": context["binding"],
        "groups": groups,
        "warnings": warnings,
        "summary": {
            "group_count": len(groups),
            "change_count": sum(group.get("item_count", 0) for group in groups),
            "warning_count": len(warnings),
        },
    }


def backup_fa_paths(paths: list[Path]) -> list[str]:
    existing: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        if not path.exists():
            continue
        key = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        existing.append(path)
    if not existing:
        return []
    backup_dir = FA_BACKUPS_DIR / datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir.mkdir(parents=True, exist_ok=True)
    backups: list[str] = []
    for path in existing:
        try:
            rel = path.relative_to(PROJECT_ROOT)
        except ValueError:
            rel = Path(path.name)
        safe_name = sanitize_filename(str(rel).replace("\\", "__").replace("/", "__")) or path.name
        target = backup_dir / safe_name
        target.write_bytes(path.read_bytes())
        backups.append(str(target))
    return backups


def apply_fa_plan(project: dict[str, Any], selected_group_ids: list[str]) -> dict[str, Any]:
    selected = {str(item or "").strip() for item in selected_group_ids if str(item or "").strip()}
    modules = list(selected) if selected else list(FA_APPLY_MODULES)
    plan = build_fa_apply_plan(project, modules)
    groups = [group for group in plan["groups"] if (not selected or group["id"] in selected) and group.get("item_count", 0) > 0]
    group_ids = {group["id"] for group in groups}
    if not group_ids:
        return {"ok": True, "applied": [], "backups": [], "preview": plan}

    context = load_fa_context()
    normalized_project = normalize_project(project)
    target_paths: list[Path] = []
    if {"persona", "database"} & group_ids:
        target_paths.append(FA_CURRENT_CARD_PATH)
        if "persona" in group_ids:
            target_paths.append(FA_PERSONA_PATH)
    if "worldbook" in group_ids:
        target_paths.append(FA_WORLDBOOK_PATH)
    if "preset" in group_ids:
        target_paths.append(FA_PRESET_PATH)
    if "memory" in group_ids:
        target_paths.append(context["memories_path"])
    backups = backup_fa_paths(target_paths)

    applied: list[str] = []
    card_payload = context["card"]
    card_dirty = False
    persona_dirty = False
    if "persona" in group_ids:
        card_payload, changes, _warnings = merge_project_persona_into_card(card_payload, normalized_project)
        card_dirty = card_dirty or bool(changes)
        persona_dirty = persona_dirty or bool(changes)
        if changes:
            applied.append("persona")
    if "database" in group_ids:
        card_payload, changes, _warnings = merge_project_database_into_card(card_payload, normalized_project)
        card_dirty = card_dirty or bool(changes)
        if changes:
            applied.append("database")
    if card_dirty:
        write_json(FA_CURRENT_CARD_PATH, card_payload)
    if persona_dirty:
        raw = card_payload.get("raw") if isinstance(card_payload.get("raw"), dict) else {}
        write_json(FA_PERSONA_PATH, build_fa_persona_from_role_card(raw))

    if "worldbook" in group_ids:
        next_worldbook, changes, _warnings = merge_project_worldbook(context["worldbook"], normalized_project)
        if changes:
            write_json(FA_WORLDBOOK_PATH, next_worldbook)
            applied.append("worldbook")
    if "preset" in group_ids:
        next_preset, changes, _warnings = merge_project_preset(context["preset"], normalized_project)
        if changes:
            write_json(FA_PRESET_PATH, next_preset)
            applied.append("preset")
    if "memory" in group_ids:
        next_memories, changes, _warnings = merge_project_memories(context["memories"], normalized_project)
        if changes:
            write_json(context["memories_path"], next_memories)
            applied.append("memory")

    return {
        "ok": True,
        "applied": applied,
        "backups": backups,
        "preview": build_fa_apply_plan(normalized_project, list(group_ids)),
    }


colorama.just_fix_windows_console()

LOG_COLORS = {
    "reset": colorama.Style.RESET_ALL,
    "muted": colorama.Fore.LIGHTBLACK_EX,
    "view": colorama.Fore.CYAN,
    "data": colorama.Fore.YELLOW,
    "success": colorama.Fore.GREEN,
    "error": colorama.Fore.RED,
}

def make_access_style(label: str, method: str, status_code: int) -> str:
    if status_code >= 400:
        return LOG_COLORS["error"]
    if method in {"POST", "PUT", "PATCH", "DELETE"}:
        return LOG_COLORS["data"]
    if label.startswith("打开"):
        return LOG_COLORS["view"]
    return LOG_COLORS["muted"]


def format_access_log(label: str, method: str, status_code: int, mood: str) -> str:
    base_color = make_access_style(label, method, status_code)
    status_color = LOG_COLORS["success"] if status_code < 400 else LOG_COLORS["error"]
    timestamp = datetime.now().strftime("%H:%M:%S")
    return f"{LOG_COLORS['muted']}[{timestamp}]{base_color}[日志]{label} {status_color}{status_code}{base_color} {mood}{LOG_COLORS['reset']}"


logger = logging.getLogger("card_writer_mod")
logger.setLevel(logging.INFO)
logger.handlers.clear()
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(_handler)
logger.propagate = False
logging.getLogger("uvicorn.access").disabled = True


def resolve_access_label(method: str, path: str) -> str:
    label_map = {
        "/": "打开缃笺首页",
        "/api/projects": "项目列表",
        "/api/settings": "AI 设置",
        "/api/workspace": "工作区",
        "/api/autosave": "自动保存",
    }
    direct_label = label_map.get(path)
    if direct_label:
        return direct_label
    if path.startswith("/api/"):
        return "访问接口"
    return {"GET": "访问页面", "POST": "提交请求", "PUT": "更新数据", "PATCH": "更新数据", "DELETE": "删除数据"}.get(method, "请求接口")


app = FastAPI(title="Card Writer")

@app.middleware("http")
async def chinese_access_log(request: Request, call_next):
    started_at = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = int((time.perf_counter() - started_at) * 1000)
    method = request.method.upper()
    path = request.url.path
    label = resolve_access_label(method, path)
    mood = "成功了喵~" if response.status_code < 400 else "出错了喵呜..."
    logger.info(format_access_log(label, method, response.status_code, mood))
    logger.debug("请求耗时%dms", elapsed_ms)
    return response

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

    def static_asset_url(filename: str) -> str:
        base = f"{root_path}/static/{filename}" if root_path else f"/static/{filename}"
        try:
            version = int((STATIC_DIR / filename).stat().st_mtime)
        except OSError:
            return base
        return f"{base}?v={version}"

    stylesheet_url = static_asset_url("card-writer.css")
    script_url = static_asset_url("card-writer.js")
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
    return {"ok": True, "project": compiler.import_payload(payload), "import_target": detect_import_target(payload)}


@app.get("/api/fa/context")
async def api_fa_context() -> dict[str, Any]:
    context = load_fa_context()
    return {"ok": True, "project": build_project_from_fa_context(context), "binding": context["binding"]}


@app.post("/api/fa/apply-preview")
async def api_fa_apply_preview(payload: FaApplyPreviewPayload) -> dict[str, Any]:
    return build_fa_apply_plan(payload.project.model_dump(), payload.modules)


@app.post("/api/fa/apply")
async def api_fa_apply(payload: FaApplyPayload) -> dict[str, Any]:
    return apply_fa_plan(payload.project.model_dump(), payload.selected_group_ids)
