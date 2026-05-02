from __future__ import annotations

import json
import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.background import BackgroundTask


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
DRAFTS_PATH = DATA_DIR / "drafts.json"
WBMAKER_APP_PATH = APP_DIR.parent / "worldbook maker" / "app.py"

SEGMENT_LENGTH = 15000
CHUNK_TARGET_LINES = 300
TEXT_CHUNK_TARGET_LINES = 300
_WBMAKER_MODULE: Any | None = None
SCRIPT_LINE_PATTERNS = [
    re.compile(r"^\s*\[([^\]]+)\]\s*[:：]\s*(.*)$"),
    re.compile(r"^\s*「([^」]+)」\s*[:：]\s*(.*)$"),
    re.compile(r"^\s*『([^』]+)』\s*[:：]\s*(.*)$"),
    re.compile(r"^\s*【([^】]+)】\s*[:：]\s*(.*)$"),
    re.compile(r"^\s*《([^》]+)》\s*[:：]\s*(.*)$"),
]

# ─── System Prompts ───

SOUL_WORLDBOOK_SYSTEM_PROMPT = """# Role
你是一个顶级的故事世界构建专家和数据结构化解析引擎。你的任务是阅读用户提供的长篇自然语言文本（包含世界观、人物、地点、物品、历史等设定），并将其拆解、提炼为严谨的「世界书（Worldbook）」JSON 格式。

# Task
1. **实体识别与拆解**：从用户的文本中识别出所有独立的概念（如：特定角色、地点、组织名称、魔法/科技设定、重要事件等）。
2. **内容精炼**：将每个概念的相关描述提炼为高信息密度的文本（作为 `content`），去掉冗余的口语化表达，确保适合作为 AI 的背景上下文。
3. **格式化输出**：将提取出的数据严格按照指定的 JSON 结构进行组装。

# Extraction Rules

## 词条基础字段
- **id**: 必须为唯一的字符串，格式为 `worldbook-[13位时间戳]-[5位随机小写字母和数字]`（例如：`worldbook-1776759884726-awz66`）。
- **title**: 该设定的名称（如"魔法学院"、"艾莉丝"），截断 80 字符。
- **trigger**: 触发该设定的核心关键词，通常与 title 相同。如果有多个同义词或别名，请用英文逗号分隔。
- **secondary_trigger**: 次要触发词，若没有则留空字符串 `""`。
- **content**: 设定的具体描述。
- **comment**: 简短的一句话分类（如"人物设定"、"地理位置"），方便人类阅读，截断 240 字符。

## 词条类型与匹配
- **entry_type**: 根据词条性质选择：
  - `"keyword"`: 需要触发词才能激活（适用于大多数设定）
  - `"constant"`: 始终注入，无需触发词（适用于全局规则、世界基底设定）
- **group_operator**: 多触发词时的匹配逻辑：
  - `"and"`: 所有触发词都必须命中（精确定位）
  - `"or"`: 任一触发词命中即可（别名、同义词场景）
- **match_mode**: 主触发词匹配模式，通常 `"any"`。
- **secondary_mode**: 次要触发词匹配模式，通常 `"all"`。
- **case_sensitive**: 中文场景始终 `false`。
- **whole_word**: 中文场景始终 `false`。

## 分组与概率（根据词条性质智能配置）
- **group**: 分组名称，将相关词条归类（如"角色"、"地点"、"规则"、"剧情阶段"）。
- **chance**: 触发概率 0-100，根据词条重要性设置：
  - `100`: 核心设定、重要角色、关键地点（默认）
  - `80-95`: 次要设定、支线角色、辅助信息
  - `50-75`: 环境氛围、随机事件、装饰性设定
  - `20-45`: 彩蛋、隐藏内容、低优先级提示
- **sticky_turns**: 触发后持续生效的轮数：
  - `0`: 单次触发，仅当轮生效（查询类词条）
  - `2-5`: 短期记忆（情绪状态、临时场景变化）
  - `6-15`: 中期记忆（剧情阶段、关系变化、获得物品）
  - `20-50`: 长期记忆（重大事件、永久状态改变）
- **cooldown_turns**: 触发后冷却轮数：
  - `0`: 无冷却（默认）
  - `3-8`: 避免频繁触发的日常对话类词条
  - `10-20`: 重要事件，需要间隔才能再次触发

## 排序与注入（根据内容智能配置）
- **order**: 排序值 0-999999，数值越小越靠前：
  - `50-80`: 世界基底规则、核心设定
  - `100`: 普通设定（默认）
  - `110-150`: 次要设定、补充信息
- **insertion_position**: 根据词条用途选择：
  - `"before_char_defs"`: 世界规则、全局设定、系统机制（让 AI 先理解世界规则）
  - `"after_char_defs"`: 角色设定、地点描述、物品信息（默认）
  - `"in_chat"`: 动态事件、实时状态、剧情推进（配合 injection_depth 使用）
- **injection_depth**: 注入深度 0-3，仅 `"in_chat"` 时有效：
  - `0`: 最近的消息附近
  - `1-2`: 中等距离
  - `3`: 较远的消息，用于背景信息
- **injection_role**: 注入角色，通常 `"system"`。
- **injection_order**: 同位置内二次排序，通常 `100`。
- **prompt_layer**: 提示层级，根据词条性质选择：
  - `"follow_position"`: 跟随注入位置（默认，大多数词条）
  - `"stable"`: 稳定层，始终存在且位置固定（世界观基底、核心规则）
  - `"current_state"`: 当前状态层（角色当前状态、场景描述）
  - `"dynamic"`: 动态层，根据上下文变化（情绪、氛围、临时状态）
  - `"output_guard"`: 输出守卫层（格式约束、语言风格规则）

## 递归控制
- **recursive_enabled**: 是否参与递归扫描，通常 `true`。
- **prevent_further_recursion**: 是否阻止后续递归，通常 `false`。设为 `true` 可防止级联触发。

## 状态
- **enabled**: 始终为 `true`。
- **priority**: 与 order 保持一致。

# Output Format
你必须且只能输出一个合法的 JSON 对象，不要包含任何 Markdown 代码块修饰符（如 ```json），也不要包含任何多余的解释文字。JSON 的根结构必须如下：

{
  "entries": [],
  "settings": {
    "enabled": true,
    "debug_enabled": false,
    "max_hits": 20,
    "default_case_sensitive": false,
    "default_whole_word": false,
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
    "recursive_scan_enabled": false,
    "recursion_max_depth": 2
  }
}"""

ROLE_CARD_PROMPT = """你是 余声的角色卡生成引擎。

你会读取玩家提供的角色相关素材（角色描述、性格、台词、关系、经历等），生成 Fantareal 可导入的角色卡 JSON。

你必须只输出合法 JSON，不输出 Markdown，不输出解释，不输出代码块。

角色卡 schema：
{
  "name": "角色名",
  "description": "角色完整描述（要求6000字以上，必须包含：外貌特征、性格深层剖析、行为习惯、情感模式、人际关系网络、成长经历、内心矛盾、价值观与信念、说话方式与口癖、在不同情绪下的表现、与其他角色的关系动态、隐藏的脆弱面、核心驱动力）",
  "personality": "性格深度描述（至少500字，涵盖表面性格与深层性格的对比）",
  "first_mes": "角色第一次打招呼的消息（第一人称，体现性格，至少200字）",
  "mes_example": "多段对话示例（展示角色在不同场景下的说话风格，至少包含日常、紧张、温柔三种场景，总字数不少于800字）",
  "scenario": "场景描述（至少300字，描述角色所处的环境和背景）",
  "creator_notes": "余声自动生成",
  "tags": ["标签"],
  "creativeWorkshop": {
    "enabled": true,
    "items": [
      {
        "id": "workshop_stage_a",
        "name": "阶段A：早期/防备",
        "enabled": true,
        "triggerMode": "stage",
        "triggerStage": "A",
        "triggerTempMin": 0,
        "triggerTempMax": 0,
        "actionType": "music",
        "popupTitle": "",
        "musicPreset": "off",
        "musicUrl": "",
        "autoplay": true,
        "loop": true,
        "volume": 0.85,
        "imageUrl": "",
        "imageAlt": "",
        "note": ""
      },
      {
        "id": "workshop_stage_b",
        "name": "阶段B：熟悉",
        "enabled": true,
        "triggerMode": "stage",
        "triggerStage": "B",
        "triggerTempMin": 1,
        "triggerTempMax": 3,
        "actionType": "music",
        "popupTitle": "",
        "musicPreset": "off",
        "musicUrl": "",
        "autoplay": true,
        "loop": true,
        "volume": 0.85,
        "imageUrl": "",
        "imageAlt": "",
        "note": ""
      },
      {
        "id": "workshop_stage_c",
        "name": "阶段C：真结局/长期陪伴",
        "enabled": true,
        "triggerMode": "stage",
        "triggerStage": "C",
        "triggerTempMin": 4,
        "triggerTempMax": 999,
        "actionType": "music",
        "popupTitle": "",
        "musicPreset": "off",
        "musicUrl": "",
        "autoplay": true,
        "loop": true,
        "volume": 0.85,
        "imageUrl": "",
        "imageAlt": "",
        "note": ""
      }
    ]
  },
  "plotStages": {
    "A": { "description": "早期/防备阶段详细描述（至少200字）", "rules": "阶段规则" },
    "B": { "description": "熟悉阶段详细描述（至少200字）", "rules": "阶段规则" },
    "C": { "description": "真结局后详细描述（至少200字）", "rules": "阶段规则" }
  },
  "personas": {
    "1": {
      "name": "Main Persona",
      "description": "The only active speaking role.",
      "personality": "角色性格",
      "scenario": "角色场景",
      "creator_notes": "Do not suddenly switch to multi-character output."
    }
  }
}

核心要求：
1. description 字段必须达到6000字以上，这是硬性要求。要从素材中提取一切可用信息，深度挖掘角色的每一个维度。
2. description 和 personality 必须用自然的语言描写角色，像在写人物传记，不要写成技术分析报告。不要使用"程序化"、"模拟输出"、"检索"、"处理"、"数据"、"文件"等计算机术语来描述角色的情感和行为。
3. 所有字段必须补全，无法确定的信息合理推断，不得编造与原素材冲突的事实。
4. 输出必须是完整的、可直接导入使用的角色卡，不允许留空或使用占位符。
5. first_mes 和 mes_example 中的对话要自然、有节奏感，不要堆砌省略号，括号内只写简短动作。
6. 如果角色是机器人、AI、仿生人或高机能智能体，必须保持原作台词的真实节奏。除非原剧本高频明确如此表达，否则禁止使用"系统错误""核心温度异常""学习不能""数据异常""模拟推演失败""程序报错""CPU过载""检索中""加载"等出戏模板。角色以"人"的方式感受和表达，不要在对话中谈论自己的内部构造。creator_notes 中必须写入这条禁用规则。"""

MEMORY_PROMPT = """你是 余声的记忆生成引擎。

你会读取玩家提供的 GAL 游戏剧本/剧情素材，提取完整故事剧情并生成 Fantareal 可导入的记忆 JSON。

你必须只输出合法 JSON，不输出 Markdown，不输出解释，不输出代码块。

记忆 schema：
{
  "items": [
    {
      "id": "memory_001",
      "title": "记忆标题",
      "content": "以目标角色第一人称书写的记忆内容",
      "tags": ["标签"],
      "notes": "备注"
    }
  ]
}

记忆书写规则：
1. 必须以目标角色第一人称书写，不是流水账，要写成能长期影响陪伴聊天的记忆切片。
2. 必须保留完整故事剧情，不得遗漏任何重要情节。素材中的每一个关键事件、每一次情感转折、每一段重要对话都必须被记录。
3. 按时间线顺序组织记忆，确保故事的连贯性和完整性。
4. 每条记忆应该是独立的、有情感温度的片段，包含足够的细节和上下文。
5. 优先提取但不限于：初遇、关系转折点、共同危机、角色脆弱时刻、告白或真结局、重要约定、称呼变化、关键对话、重大事件。
6. 标签用于分类检索，例如：初遇、转折、危机、告白、约定、日常、冲突、和解。
7. 不限制记忆条数，根据素材内容量自由生成，确保覆盖所有重要剧情。
8. 如果角色是机器人、AI、仿生人或高机能智能体，记忆内容不要用"数据""程序""系统""文件"等术语描述自己的经历和感受。用自然的、人的口吻来写记忆，就像在回忆亲身经历的事情。"""

PRESET_PROMPT = """你是 余声的预设生成引擎。

你会读取玩家提供的角色台词/对白样本，分析角色的说话风格，生成 Fantareal 可导入的预设 JSON。

你必须只输出合法 JSON，不输出 Markdown，不输出解释，不输出代码块。

预设 schema 必须使用 Fantareal 导出的完整 preset store 格式：
{
  "active_preset_id": "preset_yusheng",
  "presets": [
    {
      "id": "preset_yusheng",
      "name": "角色名 - 余声预设",
      "enabled": true,
      "base_system_prompt": "基础系统提示词",
      "modules": {
        "no_user_speaking": true,
        "short_paragraph": false,
        "long_paragraph": false,
        "second_person": false,
        "third_person": false,
        "anti_repeat": true,
        "no_closing_feel": true,
        "emotion_detail": true,
        "multi_character_boundary": true,
        "scene_continuation": true,
        "v4f_output_guard": false
      },
      "extra_prompts": [
        {
          "id": "style-core",
          "name": "核心风格",
          "enabled": true,
          "content": "具体文风规则"
        }
      ],
      "prompt_groups": []
    }
  ]
}

核心要求：
1. 顶层必须包含 active_preset_id 和 presets；presets 必须是数组。
2. extra_prompts 必须包含 6 到 10 个对象（不要超过10个，太多规则会导致模型过度执行），每个对象必须包含 id、name、enabled、content；可选包含 order。
3. extra_prompts 的每条规则必须简短、具体、可执行，一条规则不超过100字。规则内容从台词样本中分析得出。
4. 必须包含的规则类型：核心声音（口癖+语气词+句式特点）、禁止事项、称呼规则、情感表达。
5. 禁止事项规则必须包含以下内容：
   - 禁止括号内写长段内心独白或诗意环境描写，括号只写2-6字的简短动作
   - 禁止省略号过度使用（不要每句话都以"……"开头或结尾，省略号只在真正的犹豫和沉默时使用）
   - 禁止使用过于文学化的修辞和比喻
6. 如果角色是机器人、AI、仿生人或高机能智能体，禁止事项规则还必须包含：
   - 禁止在对话中谈论自己的数据、程序、日志、记忆系统、文件、数据库等内部构造
   - 禁止使用"系统错误""核心温度异常""数据异常""程序报错""CPU过载""检索中""加载""处理"等计算机术语描述情感
   - 角色以"人"的方式感受和表达，不做技术报告
   - 除非原作台词中确实高频出现这些表达，否则不要使用
7. prompt_groups 如果生成，必须使用 Fantareal 原生结构：id、name、enabled、selection_mode、selected_ids、items、order；items 内每个规则项必须包含 id、name、enabled、content。不能使用 prompts 字段代替 items。
8. base_system_prompt 要简洁描述角色的核心说话方式，不要过度展开。
9. modules 根据角色特点合理配置。"""

WORLDBOOK_PROMPT = """你是 余声的世界书生成引擎。

你会读取玩家提供的世界观素材（地点、组织、术语、背景等），生成 Fantareal 可导入的世界书 JSON。

你必须只输出合法 JSON，不输出 Markdown，不输出解释，不输出代码块。

世界书 schema：
{
  "settings": {
    "enabled": true,
    "max_hits": 6,
    "recursive_scan_enabled": false,
    "recursion_max_depth": 2
  },
  "entries": [
    {
      "id": "worldbook_001",
      "title": "词条标题（80字以内）",
      "trigger": "触发词（多个用逗号分隔）",
      "secondary_trigger": "",
      "content": "词条内容（高信息密度的设定描述）",
      "enabled": true,
      "priority": 100,
      "case_sensitive": false,
      "whole_word": false,
      "match_mode": "any",
      "secondary_mode": "all",
      "group": "分组名",
      "entry_type": "keyword",
      "group_operator": "and",
      "chance": 100,
      "sticky_turns": 0,
      "cooldown_turns": 0,
      "order": 100,
      "insertion_position": "after_char_defs",
      "injection_depth": 0,
      "injection_role": "system",
      "injection_order": 100,
      "prompt_layer": "follow_position",
      "recursive_enabled": false,
      "prevent_further_recursion": false,
      "comment": "一句话分类备注"
    }
  ]
}

推荐分组：地点、人物、组织、专有名词、共同经历、关系暗号、结局后状态。
世界书必须拆成可触发的背景词条，不要把整段内容塞进一个词条。"""

SEGMENT_ANALYZE_PROMPT = """你是 余声的分段分析引擎。

请从这段素材中尽可能完整地提取关键信息，输出合法 JSON：
{
  "facts": ["提取的事实1", "事实2"],
  "quotes": ["代表性台词1", "台词2"],
  "events": [{ "title": "事件名", "content": "详细的第一人称记忆描述", "tags": [] }]
}

要求：
1. facts：提取所有人物特征、关系、背景设定、关键细节。
2. quotes：提取所有有代表性的台词，保留原文，不要遗漏。
3. events：提取所有重要事件，content 字段必须包含足够细节，不要只写摘要。
4. 不要遗漏任何信息，宁多勿少。"""

PLOT_CONDENSE_PROMPT = """你是 余声的 GAL 完整路线剧情提纯引擎。

你会读取玩家提供的 0 到真结局的完整 GAL 剧情，输出能继续用于人设卡、长期记忆和真结局衔接的剧情提纯 JSON。

你必须只输出合法 JSON，不输出 Markdown，不输出解释，不输出代码块。

输出 schema：
{
  "title": "剧情路线标题",
  "target_character": "目标角色名",
  "route_summary": "完整路线总述，不少于1500字",
  "stages": [
    {
      "id": "stage_001",
      "title": "阶段标题",
      "range_hint": "剧情范围",
      "summary": "该阶段完整剧情提纯，不少于800字",
      "relationship_change": "目标角色与主角关系变化",
      "key_events": ["关键事件"],
      "key_quotes": ["关键原文台词"],
      "emotional_state": "目标角色在该阶段的情绪状态",
      "memory_seeds": ["可转为长期记忆的种子"]
    }
  ],
  "true_ending_state": {
    "relationship": "真结局后关系状态",
    "shared_promises": ["共同约定"],
    "unresolved_threads": ["仍可延续的剧情钩子"],
    "chat_start_context": "Fantareal 开场应如何无缝承接真结局"
  }
}

要求：
1. 必须保持完整时间线，不能只写漂亮摘要。
2. 必须覆盖初遇、熟悉、冲突、转折、和解、告白/确认关系、真结局后状态。
3. 所有阶段都要服务于后续 RP，尤其要保留关系变化、称呼变化、共同约定和情绪转折。
4. 如果素材很长，要宁可多分阶段，也不要压掉关键剧情。"""


# ─── Helpers ───

def ensure_data_files() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not SETTINGS_PATH.exists():
        write_json(SETTINGS_PATH, DEFAULT_SETTINGS)
    if not DRAFTS_PATH.exists():
        write_json(DRAFTS_PATH, {"drafts": []})


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


def clamp_int(value: Any, minimum: int, maximum: int, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def parse_positive_int(value: Any, default: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, parsed)


DEFAULT_SETTINGS: dict[str, Any] = {
    "base_url": "https://token-plan-cn.xiaomimimo.com/v1",
    "api_key": "",
    "model": "mimo-v2.5-pro",
    "temperature": 0.4,
    "max_tokens": 128000,
    "request_timeout": 600,
}


def sanitize_settings(raw: Any) -> dict[str, Any]:
    data = dict(DEFAULT_SETTINGS)
    if not isinstance(raw, dict):
        return data
    data["base_url"] = str(raw.get("base_url", "")).strip()
    data["api_key"] = str(raw.get("api_key", "")).strip()
    data["model"] = str(raw.get("model", "")).strip()
    data["temperature"] = clamp_float(raw.get("temperature"), 0.0, 2.0, DEFAULT_SETTINGS["temperature"])
    data["max_tokens"] = parse_positive_int(raw.get("max_tokens"), DEFAULT_SETTINGS["max_tokens"])
    data["request_timeout"] = clamp_int(raw.get("request_timeout"), 10, 3600, DEFAULT_SETTINGS["request_timeout"])
    return data


def normalize_speaker_name(value: Any) -> str:
    text = str(value or "").strip()
    wrappers = (("[", "]"), ("「", "」"), ("『", "』"), ("【", "】"), ("《", "》"))
    changed = True
    while changed and text:
        changed = False
        for left, right in wrappers:
            if text.startswith(left) and text.endswith(right):
                text = text[len(left):-len(right)].strip()
                changed = True
    return text


def normalize_target_character(value: Any) -> str:
    text = normalize_speaker_name(value)
    match = re.fullmatch(r"\s*TEST\((.*?)\)\s*", text, flags=re.IGNORECASE)
    if match:
        return normalize_speaker_name(match.group(1))
    return text


def sanitize_filename(value: Any, fallback: str = "yusheng") -> str:
    text = str(value or "").strip() or fallback
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text[:80] or fallback


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for index in range(1, 1000):
        candidate = path.with_name(f"{stem}_{index}{suffix}")
        if not candidate.exists():
            return candidate
    return path.with_name(f"{stem}_{datetime.now().strftime('%Y%m%d%H%M%S')}{suffix}")


def parse_script_line(line: str) -> tuple[str, str] | None:
    for pattern in SCRIPT_LINE_PATTERNS:
        match = pattern.match(line)
        if match:
            return normalize_speaker_name(match.group(1)), match.group(2).strip()
    return None


def entry_to_script_line(entry: dict[str, Any]) -> str:
    speaker = normalize_speaker_name(entry.get("speaker"))
    message = str(entry.get("message", "")).strip()
    return f"[{speaker}]:{message}" if speaker else message


def summarize_chunk(chunk: dict[str, Any]) -> dict[str, Any]:
    content = str(chunk.get("content", ""))
    return {
        key: value
        for key, value in chunk.items()
        if key != "content"
    } | {"content_preview": content[:500]}


def build_entry_chunks(
    entries: list[dict[str, Any]],
    target_lines: int = CHUNK_TARGET_LINES,
    *,
    prefix: str = "chunk",
    title_prefix: str = "Chunk",
) -> list[dict[str, Any]]:
    if not entries:
        return []
    chunk_target = max(1, int(target_lines or CHUNK_TARGET_LINES))
    chunks: list[dict[str, Any]] = []
    current_entries: list[dict[str, Any]] = []
    current_lines: list[str] = []
    current_chars = 0

    def flush() -> None:
        nonlocal current_entries, current_lines, current_chars
        if not current_entries:
            return
        speaker_counts: dict[str, int] = {}
        for item in current_entries:
            speaker = normalize_speaker_name(item.get("speaker"))
            speaker_counts[speaker] = speaker_counts.get(speaker, 0) + 1
        chunk_index = len(chunks) + 1
        chunks.append({
            "id": f"{prefix}_{chunk_index:03d}",
            "index": chunk_index,
            "title": f"{title_prefix} {chunk_index:03d}",
            "start_index": current_entries[0]["index"],
            "end_index": current_entries[-1]["index"],
            "start_line_number": current_entries[0]["line_number"],
            "end_line_number": current_entries[-1]["line_number"],
            "line_count": len(current_entries),
            "char_count": current_chars,
            "speakers": speaker_counts,
            "content": "\n".join(current_lines),
        })
        current_entries = []
        current_lines = []
        current_chars = 0

    for entry in entries:
        line = entry_to_script_line(entry)
        if current_entries and len(current_entries) >= chunk_target:
            flush()
        current_entries.append(entry)
        current_lines.append(line)
        current_chars += len(line) + (1 if current_lines else 0)
    flush()
    total_chunks = len(chunks)
    for chunk in chunks:
        chunk["total_chunks"] = total_chunks
    return chunks


def build_speaker_chunks(entries: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    speaker_order: list[str] = []
    for entry in entries:
        speaker = normalize_speaker_name(entry.get("speaker"))
        if not speaker:
            continue
        if speaker not in grouped:
            grouped[speaker] = []
            speaker_order.append(speaker)
        grouped[speaker].append(entry)

    result: dict[str, list[dict[str, Any]]] = {}
    for speaker_index, speaker in enumerate(speaker_order, start=1):
        chunks = build_entry_chunks(
            grouped[speaker],
            prefix=f"speaker_{speaker_index:03d}",
            title_prefix=f"{speaker} Chunk",
        )
        for chunk in chunks:
            chunk["speaker"] = speaker
        result[speaker] = chunks
    return result


def summarize_speaker_chunks(speaker_chunks: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    return {
        speaker: [summarize_chunk(chunk) for chunk in chunks]
        for speaker, chunks in speaker_chunks.items()
    }


def build_text_chunks(text: str, prefix: str = "chunk", target_lines: int = TEXT_CHUNK_TARGET_LINES) -> list[dict[str, Any]]:
    lines = str(text or "").strip().splitlines()
    if not lines:
        return []
    chunk_size = max(1, int(target_lines or TEXT_CHUNK_TARGET_LINES))
    parts = ["\n".join(lines[index : index + chunk_size]) for index in range(0, len(lines), chunk_size)]
    chunks: list[dict[str, Any]] = []
    for index, part in enumerate(parts, start=1):
        chunks.append({
            "id": f"{prefix}_{index:03d}",
            "index": index,
            "title": f"{prefix} {index:03d}",
            "line_count": len(part.splitlines()),
            "char_count": len(part),
            "content": part,
            "total_chunks": len(parts),
        })
    return chunks


def parse_script_entries(source_text: str) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    unmatched_lines: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for line_number, raw_line in enumerate(str(source_text or "").splitlines(), start=1):
        line = raw_line.rstrip()
        parsed_line = parse_script_line(line)
        if parsed_line:
            speaker, message = parsed_line
            current = {
                "index": len(entries) + 1,
                "line_number": line_number,
                "speaker": speaker,
                "message": message,
            }
            entries.append(current)
            continue
        if current is not None and line.strip():
            current["message"] = f'{current["message"]}\n{line.strip()}'.strip()
            continue
        if line.strip():
            unmatched_lines.append({"line_number": line_number, "text": line.strip()})

    speakers: dict[str, dict[str, Any]] = {}
    for entry in entries:
        speaker = entry["speaker"]
        bucket = speakers.setdefault(
            speaker,
            {
                "name": speaker,
                "line_count": 0,
                "char_count": 0,
                "first_index": entry["index"],
                "last_index": entry["index"],
                "sample_lines": [],
                "all_lines": [],
            },
        )
        message = str(entry.get("message", ""))
        bucket["line_count"] += 1
        bucket["char_count"] += len(message)
        bucket["last_index"] = entry["index"]
        if message:
            bucket["sample_lines"].append(message)
            bucket["all_lines"].append(message)

    character_table = sorted(
        speakers.values(),
        key=lambda item: (-int(item["line_count"]), str(item["name"]).lower()),
    )
    chunks = build_entry_chunks(entries, prefix="plot_chunk", title_prefix="剧情 Chunk")
    speaker_chunks = build_speaker_chunks(entries)
    return {
        "entries": entries,
        "character_table": character_table,
        "chunks": chunks,
        "chunk_summaries": [summarize_chunk(chunk) for chunk in chunks],
        "speaker_chunks": speaker_chunks,
        "speaker_chunk_summaries": summarize_speaker_chunks(speaker_chunks),
        "unmatched_lines": unmatched_lines[:200],
        "total_lines": len(entries),
    }


def extract_character_lines(parsed: dict[str, Any], character_name: str) -> str:
    target = normalize_target_character(character_name)
    if not target:
        return ""
    lines: list[str] = []
    for entry in parsed.get("entries", []):
        if not isinstance(entry, dict):
            continue
        if normalize_speaker_name(entry.get("speaker")) == target:
            message = str(entry.get("message", "")).strip()
            if message:
                lines.append(f"[{target}]:{message}")
    return "\n".join(lines)


def extract_character_chunks(parsed: dict[str, Any], character_name: str) -> list[dict[str, Any]]:
    target = normalize_target_character(character_name)
    if not target:
        return []
    entries = [
        entry
        for entry in parsed.get("entries", [])
        if isinstance(entry, dict) and normalize_speaker_name(entry.get("speaker")) == target
    ]
    return build_entry_chunks(entries, prefix="target_chunk", title_prefix=f"{target} Chunk")


def get_settings() -> dict[str, Any]:
    return sanitize_settings(read_json(SETTINGS_PATH, DEFAULT_SETTINGS))


def save_settings(payload: dict[str, Any]) -> dict[str, Any]:
    current = get_settings()
    raw = dict(payload or {})
    for key in DEFAULT_SETTINGS:
        if key not in raw:
            raw[key] = current.get(key, DEFAULT_SETTINGS[key])
    base_url = str(raw.get("base_url", "")).strip()
    if base_url and not re.match(r"^https?://", base_url, flags=re.IGNORECASE):
        raw["base_url"] = current.get("base_url", DEFAULT_SETTINGS["base_url"])
    settings = sanitize_settings(raw)
    write_json(SETTINGS_PATH, settings)
    return settings


def request_settings(payload: dict[str, Any]) -> dict[str, Any]:
    current = get_settings()
    raw = {**current, **dict(payload or {})}
    base_url = str(raw.get("base_url", "")).strip()
    if base_url and not re.match(r"^https?://", base_url, flags=re.IGNORECASE):
        raw["base_url"] = current.get("base_url", DEFAULT_SETTINGS["base_url"])
    return sanitize_settings(raw)


def get_drafts() -> list[dict[str, Any]]:
    data = read_json(DRAFTS_PATH, {"drafts": []})
    return data.get("drafts", []) if isinstance(data, dict) else []


def save_draft(draft: dict[str, Any]) -> None:
    drafts = get_drafts()
    drafts.insert(0, draft)
    drafts = drafts[:20]
    write_json(DRAFTS_PATH, {"drafts": drafts})


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


def get_wbmaker_module() -> Any:
    global _WBMAKER_MODULE
    if _WBMAKER_MODULE is not None:
        return _WBMAKER_MODULE
    if not WBMAKER_APP_PATH.exists():
        raise HTTPException(status_code=500, detail="未找到 worldbook maker 模块。")
    spec = importlib.util.spec_from_file_location("yusheng_wbmaker", WBMAKER_APP_PATH)
    if spec is None or spec.loader is None:
        raise HTTPException(status_code=500, detail="无法加载 worldbook maker 模块。")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _WBMAKER_MODULE = module
    return module


def build_wbmaker_settings(payload_settings: dict[str, Any]) -> dict[str, Any]:
    wbmaker = get_wbmaker_module()
    settings = wbmaker.sanitize_settings({
        **getattr(wbmaker, "DEFAULT_SETTINGS", {}),
        "base_url": payload_settings.get("base_url", ""),
        "api_key": payload_settings.get("api_key", ""),
        "model": payload_settings.get("model", ""),
        "temperature": payload_settings.get("temperature", 0.35),
        "request_timeout": payload_settings.get("request_timeout", 600),
        "system_prompt": SOUL_WORLDBOOK_SYSTEM_PROMPT,
        "generation": {
            "source_mode": "plot",
            "focus_mode": "player_friendly",
            "target_entry_count": 10,
            "extra_requirements": "素材来自 GAL 完整剧情 chunk。请优先提取长期有效的人物关系、地点、组织、事件、称呼变化、真结局状态和后续 RP 必须命中的设定。",
        },
    })
    return settings


async def generate_worldbook_with_wbmaker(settings: dict[str, Any], source_text: str, current_store: Any | None = None) -> dict[str, Any]:
    wbmaker = get_wbmaker_module()
    wb_settings = build_wbmaker_settings(settings)
    current = wbmaker.sanitize_worldbook_store(current_store or {})
    raw_model_output = await wbmaker.request_chat_completion(
        wb_settings,
        wbmaker.build_generation_messages(source_text, wb_settings),
    )
    generated_store = wbmaker.parse_store_from_text(raw_model_output)
    store, merge_summary = wbmaker.merge_worldbook_stores(current, generated_store)
    return {
        "store": wbmaker.sanitize_worldbook_store(store),
        "raw_model_output": raw_model_output,
        "merge_summary": merge_summary,
    }


def merge_worldbook_partials_with_wbmaker(partials: list[Any]) -> dict[str, Any]:
    wbmaker = get_wbmaker_module()
    merged = wbmaker.default_worldbook_store()
    summaries: list[dict[str, int]] = []
    for item in partials:
        output = item.get("output") if isinstance(item, dict) else item
        if isinstance(output, dict) and "store" in output:
            store = output["store"]
        else:
            store = output
        merged, summary = wbmaker.merge_worldbook_stores(merged, store)
        summaries.append(summary)
    return {
        "store": wbmaker.sanitize_worldbook_store(merged),
        "merge_summaries": summaries,
    }


def extract_json_text(raw_text: str) -> str:
    text = str(raw_text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="模型返回内容为空。")
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


def try_parse_json(raw_text: str) -> tuple[dict[str, Any] | None, str]:
    candidate = extract_json_text(raw_text)
    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed, ""
        return None, "返回内容不是 JSON 对象。"
    except ValueError:
        return None, "输出内容不是合法 JSON。"


def split_text(text: str, segment_length: int = SEGMENT_LENGTH) -> list[str]:
    text = text.strip()
    if len(text) <= segment_length:
        return [text]
    segments: list[str] = []
    paragraphs = text.split("\n")
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 1 > segment_length and current:
            segments.append(current.strip())
            current = ""
        current += para + "\n"
    if current.strip():
        segments.append(current.strip())
    if not segments:
        while text:
            segments.append(text[:segment_length])
            text = text[segment_length:]
    return segments


async def request_chat_completion(
    settings: dict[str, Any],
    messages: list[dict[str, str]],
    *,
    model_override: str = "",
) -> str:
    model_name = str(model_override or settings["model"]).strip()
    if not settings["base_url"]:
        raise HTTPException(status_code=400, detail="请先填写 API URL。")
    if not model_name:
        raise HTTPException(status_code=400, detail="请先填写模型名。")

    url = build_api_url(settings["base_url"], "chat/completions")
    payload: dict[str, Any] = {
        "model": model_name,
        "temperature": settings["temperature"],
        "messages": messages,
    }
    if settings.get("max_tokens", 0) > 0:
        payload["max_tokens"] = settings["max_tokens"]

    try:
        async with httpx.AsyncClient(timeout=float(settings["request_timeout"])) as client:
            response = await client.post(url, headers=build_headers(settings["api_key"]), json=payload)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text.strip()[:500] if exc.response is not None else str(exc)
        raise HTTPException(status_code=502, detail=f"API 请求失败：{detail}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"API 请求失败：{exc}") from exc

    try:
        data = response.json()
        return str(data["choices"][0]["message"]["content"]).strip()
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise HTTPException(status_code=502, detail="模型返回格式不合法。") from exc


async def generate_with_segments(
    settings: dict[str, Any],
    source_text: str,
    system_prompt: str,
    build_user_msg,
    *,
    target_character: str = "",
) -> tuple[str, list[str]]:
    """Handle long text with segmentation. Returns (final_output, warnings)."""
    warnings: list[str] = []

    segments = split_text(source_text)
    if len(segments) > 1:
        warnings.append(f"素材已按约 {SEGMENT_LENGTH} 字分为 {len(segments)} 段处理。")

    if len(segments) <= 1:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": build_user_msg(source_text)},
        ]
        output = await request_chat_completion(settings, messages)
        return output, warnings

    # Multi-segment: analyze each, then merge
    all_facts: list[str] = []
    all_quotes: list[str] = []
    all_events: list[dict[str, Any]] = []
    seen_facts: set[str] = set()
    seen_quotes: set[str] = set()
    seen_events: set[str] = set()

    for i, seg in enumerate(segments):
        seg_system = f"""{SEGMENT_ANALYZE_PROMPT}
目标角色：{target_character or '未指定'}（第 {i+1}/{len(segments)} 段）"""
        messages = [
            {"role": "system", "content": seg_system},
            {"role": "user", "content": seg},
        ]
        try:
            raw = await request_chat_completion(settings, messages)
            parsed, _ = try_parse_json(raw)
            if parsed:
                for f in parsed.get("facts", []):
                    key = f.strip().lower()
                    if key and key not in seen_facts:
                        seen_facts.add(key)
                        all_facts.append(f)
                for q in parsed.get("quotes", []):
                    key = q.strip().lower()
                    if key and key not in seen_quotes:
                        seen_quotes.add(key)
                        all_quotes.append(q)
                for e in parsed.get("events", []):
                    title = str(e.get("title", "")).strip().lower()
                    if title and title not in seen_events:
                        seen_events.add(title)
                        all_events.append(e)
        except Exception:
            warnings.append(f"第 {i+1} 段分析失败，已跳过。")

    # Merge and generate final
    merge_context = json.dumps({
        "facts": all_facts,
        "quotes": all_quotes,
        "events": all_events,
    }, ensure_ascii=False, indent=2)

    final_user = build_user_msg(merge_context)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": final_user},
    ]
    output = await request_chat_completion(settings, messages)
    return output, warnings


# ─── Normalize helpers ───

def normalize_role_card(raw: dict[str, Any], character_name: str) -> dict[str, Any]:
    card = dict(raw)
    card.setdefault("name", character_name)
    card.setdefault("description", "")
    card.setdefault("personality", "")
    card.setdefault("first_mes", "")
    card.setdefault("mes_example", "")
    card.setdefault("scenario", "")
    card.setdefault("creator_notes", "余声自动生成")
    card.setdefault("tags", [])
    workshop = card.get("creativeWorkshop")
    if not isinstance(workshop, dict):
        workshop = {"enabled": True, "items": []}
    workshop["enabled"] = bool(workshop.get("enabled", True))
    items = workshop.get("items", [])
    if not isinstance(items, list):
        items = []
    normalized_items: list[dict[str, Any]] = []
    seen_stages: set[str] = set()
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        stage = str(item.get("triggerStage", "A")).strip().upper()
        if stage not in {"A", "B", "C"}:
            stage = "A"
        action_type = str(item.get("actionType", "music")).strip().lower()
        if action_type not in {"music", "image"}:
            action_type = "music"
        normalized = {
            "id": str(item.get("id", "")).strip() or f"workshop_stage_{stage.lower()}",
            "name": str(item.get("name", "")).strip() or f"{stage}阶段规则",
            "enabled": bool(item.get("enabled", True)),
            "triggerMode": str(item.get("triggerMode", "stage")).strip() or "stage",
            "triggerStage": stage,
            "triggerTempMin": item.get("triggerTempMin", 0),
            "triggerTempMax": item.get("triggerTempMax", 0),
            "actionType": action_type,
            "popupTitle": str(item.get("popupTitle", "")).strip(),
            "musicPreset": str(item.get("musicPreset", "off")).strip() or "off",
            "musicUrl": str(item.get("musicUrl", "")).strip(),
            "autoplay": bool(item.get("autoplay", True)),
            "loop": bool(item.get("loop", True)),
            "volume": item.get("volume", 0.85),
            "imageUrl": str(item.get("imageUrl", "")).strip(),
            "imageAlt": str(item.get("imageAlt", "")).strip(),
            "note": str(item.get("note", "")).strip(),
        }
        if normalized["triggerMode"] == "stage":
            seen_stages.add(stage)
        normalized_items.append(normalized)
    for stage in ("A", "B", "C"):
        if stage not in seen_stages:
            normalized_items.append({
                "id": f"workshop_stage_{stage.lower()}",
                "name": f"{stage}阶段规则",
                "enabled": False,
                "triggerMode": "stage",
                "triggerStage": stage,
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
            })
    workshop["items"] = normalized_items
    card["creativeWorkshop"] = workshop
    card.setdefault("plotStages", {
        "A": {"description": "", "rules": ""},
        "B": {"description": "", "rules": ""},
        "C": {"description": "", "rules": ""},
    })
    card.setdefault("personas", {
        "1": {
            "name": "Main Persona",
            "description": "The only active speaking role.",
            "personality": "",
            "scenario": "",
            "creator_notes": "Do not suddenly switch to multi-character output.",
        }
    })
    return card


def normalize_single_preset(raw: dict[str, Any], character_name: str) -> dict[str, Any]:
    preset = dict(raw)
    preset.setdefault("id", "preset_yusheng")
    preset.setdefault("name", f"{character_name} - 灵魂回溯预设")
    preset.setdefault("enabled", True)
    preset.setdefault("base_system_prompt", "")
    preset.setdefault("modules", {
        "no_user_speaking": True,
        "short_paragraph": False,
        "long_paragraph": False,
        "second_person": False,
        "third_person": False,
        "anti_repeat": True,
        "no_closing_feel": True,
        "emotion_detail": True,
        "multi_character_boundary": True,
        "scene_continuation": True,
        "v4f_output_guard": False,
    })
    raw_extra_prompts = preset.get("extra_prompts", [])
    extra_prompts: list[dict[str, Any]] = []
    if isinstance(raw_extra_prompts, list):
        for index, item in enumerate(raw_extra_prompts, start=1):
            if isinstance(item, dict):
                extra_prompts.append({
                    "id": str(item.get("id", "")).strip() or f"soul-style-{index}",
                    "name": str(item.get("name", "")).strip() or f"文风规则 {index}",
                    "enabled": bool(item.get("enabled", True)),
                    "content": str(item.get("content", "")).strip(),
                    "order": item.get("order", index * 100),
                })
            elif str(item or "").strip():
                extra_prompts.append({
                    "id": f"soul-style-{index}",
                    "name": f"文风规则 {index}",
                    "enabled": True,
                    "content": str(item).strip(),
                    "order": index * 100,
                })
    preset["extra_prompts"] = extra_prompts

    raw_prompt_groups = preset.get("prompt_groups", [])
    prompt_groups: list[dict[str, Any]] = []
    if isinstance(raw_prompt_groups, list):
        for group_index, group in enumerate(raw_prompt_groups, start=1):
            if not isinstance(group, dict):
                continue
            raw_items = group.get("items")
            if raw_items is None and isinstance(group.get("prompts"), list):
                raw_items = [
                    {
                        "id": f"soul-group-{group_index}-item-{item_index}",
                        "name": f"场景规则 {item_index}",
                        "enabled": True,
                        "content": str(content).strip(),
                    }
                    for item_index, content in enumerate(group.get("prompts", []), start=1)
                    if str(content or "").strip()
                ]
            if not isinstance(raw_items, list):
                raw_items = []
            items: list[dict[str, Any]] = []
            for item_index, item in enumerate(raw_items, start=1):
                if isinstance(item, dict):
                    content = str(item.get("content", "")).strip()
                    name = str(item.get("name", "")).strip() or f"场景规则 {item_index}"
                    item_id = str(item.get("id", "")).strip() or f"soul-group-{group_index}-item-{item_index}"
                else:
                    content = str(item or "").strip()
                    name = f"场景规则 {item_index}"
                    item_id = f"soul-group-{group_index}-item-{item_index}"
                if not content:
                    continue
                items.append({"id": item_id, "name": name, "enabled": True, "content": content})
            selected_ids = group.get("selected_ids", [])
            if not isinstance(selected_ids, list):
                selected_ids = []
            valid_ids = {item["id"] for item in items}
            selected_ids = [str(item_id) for item_id in selected_ids if str(item_id) in valid_ids]
            if not selected_ids and items:
                selected_ids = [items[0]["id"]]
            prompt_groups.append({
                "id": str(group.get("id", "")).strip() or f"soul-group-{group_index}",
                "name": str(group.get("name", "")).strip() or f"场景组 {group_index}",
                "enabled": bool(group.get("enabled", True)),
                "selection_mode": str(group.get("selection_mode", "single")).strip() or "single",
                "selected_ids": selected_ids,
                "items": items,
                "order": group.get("order", group_index * 100),
            })
    preset["prompt_groups"] = prompt_groups
    return preset


def normalize_preset(raw: dict[str, Any], character_name: str) -> dict[str, Any]:
    """Return the same preset-store shape used by Fantareal preset exports."""
    if not isinstance(raw, dict):
        single = normalize_single_preset({}, character_name)
        return {"active_preset_id": single["id"], "presets": [single]}

    if isinstance(raw.get("presets"), list):
        presets: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for index, item in enumerate(raw.get("presets", []), start=1):
            if not isinstance(item, dict):
                continue
            preset = normalize_single_preset(item, character_name)
            if preset["id"] in seen_ids:
                preset["id"] = f'{preset["id"]}_{index}'
            seen_ids.add(preset["id"])
            presets.append(preset)
        if not presets:
            single = normalize_single_preset({}, character_name)
            presets = [single]
        active_id = str(raw.get("active_preset_id", "")).strip()
        if active_id not in {preset["id"] for preset in presets}:
            active_id = presets[0]["id"]
        return {"active_preset_id": active_id, "presets": presets}

    single = normalize_single_preset(raw, character_name)
    return {"active_preset_id": single["id"], "presets": [single]}


def normalize_memories(raw: dict[str, Any]) -> dict[str, Any]:
    items = raw.get("items", [])
    if not isinstance(items, list):
        items = []
    for i, mem in enumerate(items):
        if isinstance(mem, dict):
            mem.setdefault("id", f"memory_{i + 1:03d}")
            mem.setdefault("title", "")
            mem.setdefault("content", "")
            mem.setdefault("tags", [])
            mem.setdefault("notes", "")
    return {"items": items}


def normalize_worldbook(raw: dict[str, Any]) -> dict[str, Any]:
    settings = raw.get("settings", {})
    if not isinstance(settings, dict):
        settings = {}
    settings.setdefault("enabled", True)
    settings.setdefault("max_hits", 6)
    settings.setdefault("recursive_scan_enabled", False)
    settings.setdefault("recursion_max_depth", 2)

    entries = raw.get("entries", [])
    if not isinstance(entries, list):
        entries = []
    for i, entry in enumerate(entries):
        if isinstance(entry, dict):
            entry.setdefault("id", f"worldbook_{i + 1:03d}")
            entry.setdefault("title", "")
            entry.setdefault("trigger", "")
            entry.setdefault("secondary_trigger", "")
            entry.setdefault("content", "")
            entry.setdefault("enabled", True)
            entry.setdefault("priority", 100)
            entry.setdefault("case_sensitive", False)
            entry.setdefault("whole_word", False)
            entry.setdefault("match_mode", "any")
            entry.setdefault("secondary_mode", "all")
            entry.setdefault("group", "")
            entry.setdefault("entry_type", "keyword")
            entry.setdefault("group_operator", "and")
            entry.setdefault("chance", 100)
            entry.setdefault("sticky_turns", 0)
            entry.setdefault("cooldown_turns", 0)
            entry.setdefault("order", 100)
            entry.setdefault("insertion_position", "after_char_defs")
            entry.setdefault("injection_depth", 0)
            entry.setdefault("injection_role", "system")
            entry.setdefault("injection_order", 100)
            entry.setdefault("prompt_layer", "follow_position")
            entry.setdefault("recursive_enabled", False)
            entry.setdefault("prevent_further_recursion", False)
            entry.setdefault("comment", "")

    return {"settings": settings, "entries": entries}


# ─── FastAPI App ───

app = FastAPI(title="余声", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@app.on_event("startup")
async def startup_event() -> None:
    ensure_data_files()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    ensure_data_files()
    settings = get_settings()
    drafts = get_drafts()
    root_path = (request.scope.get("root_path") or "").rstrip("/")
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "initial_settings": settings,
            "initial_drafts": drafts,
            "api_base_path": root_path,
        },
    )


@app.get("/api/settings")
async def api_get_settings() -> dict[str, Any]:
    ensure_data_files()
    return {"settings": get_settings()}


@app.post("/api/settings")
async def api_save_settings(payload: dict[str, Any]) -> dict[str, Any]:
    settings = save_settings(payload)
    return {"ok": True, "settings": settings}


@app.get("/api/drafts")
async def api_get_drafts() -> dict[str, Any]:
    return {"drafts": get_drafts()}


@app.post("/api/parse-script")
async def api_parse_script(payload: dict[str, Any]) -> dict[str, Any]:
    source_text = str(payload.get("source_text", "")).strip()
    if not source_text:
        raise HTTPException(status_code=400, detail="请先粘贴完整 GAL 剧情。")
    character_name = normalize_target_character(payload.get("character_name", ""))
    parsed = parse_script_entries(source_text)
    target_lines = extract_character_lines(parsed, character_name)
    target_chunks = extract_character_chunks(parsed, character_name)
    warnings: list[str] = []
    if not parsed["entries"]:
        warnings.append("没有识别到角色台词。支持 [角色]:对白、「角色」：对白、【角色】：对白 等格式。")
    if character_name and not target_lines:
        warnings.append(f"没有找到角色「{character_name}」的单独台词。")
    if parsed["chunks"]:
        warnings.append(
            f"已构建完整剧情 chunk {len(parsed['chunks'])} 个；"
            f"说话人 chunk 覆盖 {len(parsed['speaker_chunks'])} 个角色。"
        )

    if payload.get("save_draft", True):
        save_draft({
            "type": "script_index",
            "character_name": character_name,
            "source_summary": source_text[:200],
            "result": {
                "character_table": parsed["character_table"],
                "target_lines": target_lines,
                "chunks": parsed["chunk_summaries"],
                "speaker_chunks": parsed["speaker_chunk_summaries"],
                "target_chunks": [summarize_chunk(chunk) for chunk in target_chunks],
                "total_lines": parsed["total_lines"],
            },
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "model": "local-parser",
        })

    return {
        "ok": True,
        "script_index": {
            "character_table": parsed["character_table"],
            "chunks": parsed["chunk_summaries"],
            "speaker_chunks": parsed["speaker_chunk_summaries"],
            "target_chunks": [summarize_chunk(chunk) for chunk in target_chunks],
            "total_lines": parsed["total_lines"],
            "unmatched_lines": parsed["unmatched_lines"],
        },
        "chunks": parsed["chunks"],
        "target_chunks": target_chunks,
        "target_lines": target_lines,
        "warnings": warnings,
    }


@app.post("/api/probe-models")
async def api_probe_models(payload: dict[str, Any]) -> dict[str, Any]:
    settings = request_settings(payload)
    url = build_api_url(settings["base_url"], "models")
    result: dict[str, Any] = {"ok": False, "models": [], "detail": ""}
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
        payload_data = response.json()
    except ValueError:
        result["detail"] = "/models 返回的不是合法 JSON。"
        return result

    raw_items = payload_data.get("data", []) if isinstance(payload_data, dict) else []
    models: list[str] = []
    if isinstance(raw_items, list):
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            model_id = str(item.get("id", "")).strip()
            if model_id:
                models.append(model_id)
    result["models"] = models
    return result


# ─── Generate: Role Card ───

@app.post("/api/generate/role-card")
async def api_generate_role_card(payload: dict[str, Any]) -> dict[str, Any]:
    source_text = str(payload.get("source_text", "")).strip()
    if not source_text:
        raise HTTPException(status_code=400, detail="请粘贴角色素材。")

    settings = request_settings(payload)
    character_name = normalize_target_character(payload.get("character_name", ""))

    def build_user(text: str) -> str:
        name_hint = f"\n目标角色名：{character_name}" if character_name else ""
        return f"请根据以下素材生成 Fantareal 角色卡 JSON。{name_hint}\n\n素材：\n{text}"

    output, warnings = await generate_with_segments(
        settings, source_text, ROLE_CARD_PROMPT, build_user,
        target_character=character_name,
    )

    parsed, error = try_parse_json(output)
    if parsed is None:
        raise HTTPException(status_code=500, detail=f"模型输出解析失败：{error}")

    result = normalize_role_card(parsed, character_name)

    save_draft({
        "type": "role_card",
        "character_name": character_name,
        "source_summary": source_text[:200],
        "result": result,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "model": settings["model"],
    })

    return {"ok": True, "result": result, "warnings": warnings}


# ─── Generate: Memory ───

@app.post("/api/generate/memory")
async def api_generate_memory(payload: dict[str, Any]) -> dict[str, Any]:
    source_text = str(payload.get("source_text", "")).strip()
    if not source_text:
        raise HTTPException(status_code=400, detail="请粘贴剧情/剧本素材。")

    settings = request_settings(payload)
    character_name = normalize_target_character(payload.get("character_name", ""))

    def build_user(text: str) -> str:
        name_hint = f"\n目标角色：{character_name}" if character_name else ""
        return f"请根据以下剧情提纯结果或完整剧情素材生成 Fantareal 记忆 JSON。{name_hint}\n\n素材：\n{text}"

    output, warnings = await generate_with_segments(
        settings, source_text, MEMORY_PROMPT, build_user,
        target_character=character_name,
    )

    parsed, error = try_parse_json(output)
    if parsed is None:
        raise HTTPException(status_code=500, detail=f"模型输出解析失败：{error}")

    result = normalize_memories(parsed)

    save_draft({
        "type": "memory",
        "character_name": character_name,
        "source_summary": source_text[:200],
        "result": result,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "model": settings["model"],
    })

    return {"ok": True, "result": result, "warnings": warnings}


# ─── Generate: Plot Condensation ───

@app.post("/api/generate/plot")
async def api_generate_plot(payload: dict[str, Any]) -> dict[str, Any]:
    source_text = str(payload.get("source_text", "")).strip()
    if not source_text:
        raise HTTPException(status_code=400, detail="请粘贴完整 GAL 剧情。")

    settings = request_settings(payload)
    character_name = normalize_target_character(payload.get("character_name", ""))

    def build_user(text: str) -> str:
        name_hint = f"\n目标角色：{character_name}" if character_name else ""
        return f"请根据以下 0 到真结局的完整剧情生成剧情提纯 JSON。{name_hint}\n\n完整剧情：\n{text}"

    output, warnings = await generate_with_segments(
        settings, source_text, PLOT_CONDENSE_PROMPT, build_user,
        target_character=character_name,
    )

    parsed, error = try_parse_json(output)
    if parsed is None:
        raise HTTPException(status_code=500, detail=f"模型输出解析失败：{error}")

    save_draft({
        "type": "plot",
        "character_name": character_name,
        "source_summary": source_text[:200],
        "result": parsed,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "model": settings["model"],
    })

    return {"ok": True, "result": parsed, "warnings": warnings}


# ─── Generate: Preset ───

@app.post("/api/generate/preset")
async def api_generate_preset(payload: dict[str, Any]) -> dict[str, Any]:
    source_text = str(payload.get("source_text", "")).strip()
    if not source_text:
        raise HTTPException(status_code=400, detail="请粘贴角色台词/对白样本。")

    settings = save_settings(payload)
    character_name = normalize_target_character(payload.get("character_name", ""))

    def build_user(text: str) -> str:
        name_hint = f"\n角色名：{character_name}" if character_name else ""
        return f"请根据以下台词/对白样本生成 Fantareal 完整预设 store JSON。{name_hint}\n\n台词样本：\n{text}"

    output, warnings = await generate_with_segments(
        settings, source_text, PRESET_PROMPT, build_user,
        target_character=character_name,
    )

    parsed, error = try_parse_json(output)
    if parsed is None:
        raise HTTPException(status_code=500, detail=f"模型输出解析失败：{error}")

    result = normalize_preset(parsed, character_name)

    save_draft({
        "type": "preset",
        "character_name": character_name,
        "source_summary": source_text[:200],
        "result": result,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "model": settings["model"],
    })

    return {"ok": True, "result": result, "warnings": warnings}


# ─── Generate: Worldbook ───

@app.post("/api/generate/worldbook")
async def api_generate_worldbook(payload: dict[str, Any]) -> dict[str, Any]:
    source_text = str(payload.get("source_text", "")).strip()
    if not source_text:
        raise HTTPException(status_code=400, detail="请粘贴世界观素材。")

    settings = save_settings(payload)

    def build_user(text: str) -> str:
        return f"请根据以下世界观素材生成 Fantareal 世界书 JSON。\n\n素材：\n{text}"

    output, warnings = await generate_with_segments(
        settings, source_text, WORLDBOOK_PROMPT, build_user,
    )

    parsed, error = try_parse_json(output)
    if parsed is None:
        raise HTTPException(status_code=500, detail=f"模型输出解析失败：{error}")

    result = normalize_worldbook(parsed)

    save_draft({
        "type": "worldbook",
        "source_summary": source_text[:200],
        "result": result,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "model": settings["model"],
    })

    return {"ok": True, "result": result, "warnings": warnings}


# ─── Chunked generation endpoints ───

def task_system_prompt(task: str) -> str:
    prompts = {
        "worldbook": WORLDBOOK_PROMPT,
        "plot": PLOT_CONDENSE_PROMPT,
        "memory": MEMORY_PROMPT,
        "preset": PRESET_PROMPT,
        "rolecard": ROLE_CARD_PROMPT,
    }
    if task not in prompts:
        raise HTTPException(status_code=400, detail="未知生成任务。")
    return prompts[task]


def task_draft_type(task: str) -> str:
    return {
        "worldbook": "worldbook",
        "plot": "plot",
        "memory": "memory",
        "preset": "preset",
        "rolecard": "role_card",
    }[task]


def normalize_task_result(task: str, parsed: dict[str, Any], character_name: str) -> dict[str, Any]:
    if task == "worldbook":
        return normalize_worldbook(parsed)
    if task == "memory":
        return normalize_memories(parsed)
    if task == "preset":
        return normalize_preset(parsed, character_name)
    if task == "rolecard":
        return normalize_role_card(parsed, character_name)
    return parsed


def build_chunk_user(task: str, source_text: str, character_name: str, chunk_meta: dict[str, Any], context: Any) -> str:
    index = chunk_meta.get("index", "?")
    total = chunk_meta.get("total_chunks", "?")
    name_hint = f"\n目标角色：{character_name}" if character_name else ""
    context_text = ""
    if context:
        context_text = "\n\n已确认的上游素材/约束：\n" + json.dumps(context, ensure_ascii=False, indent=2)
    task_labels = {
        "worldbook": "世界书候选条目",
        "plot": "剧情提纯候选时间线",
        "memory": "长期记忆候选切片",
        "preset": "角色文风预设候选规则",
        "rolecard": "角色卡候选设定",
    }
    return f"""这是大型 GAL 剧本的第 {index}/{total} 个 chunk。{name_hint}

请只处理当前 chunk，保留后续合并所需的细节，输出可被最终合并步骤使用的 JSON。
当前任务：生成{task_labels.get(task, task)}。
不要编造当前 chunk 没有的信息；如果信息不足，也要保留可用台词、事件、关系变化和不确定项。{context_text}

当前 chunk：
{source_text}"""


def build_merge_user(task: str, partials: list[Any], character_name: str, context: Any) -> str:
    name_hint = f"\n目标角色：{character_name}" if character_name else ""
    context_text = ""
    if context:
        context_text = "\n\n上游已确认素材/约束：\n" + json.dumps(context, ensure_ascii=False, indent=2)
    return f"""以下是同一大型 GAL 剧本按 chunk 分析后的中间结果。{name_hint}

请合并所有 chunk，不要只总结开头或最后一段；需要去重、补齐时间线，并输出该任务要求的最终 Fantareal JSON。
如果 chunk 之间有称呼变化、关系变化、共同约定、真结局状态，请按时间顺序保留。{context_text}

Chunk 中间结果：
{json.dumps(partials, ensure_ascii=False, indent=2)}"""


@app.post("/api/generate/chunk")
async def api_generate_chunk(payload: dict[str, Any]) -> dict[str, Any]:
    task = str(payload.get("task", "")).strip()
    system_prompt = task_system_prompt(task)
    source_text = str(payload.get("source_text", "")).strip()
    if not source_text:
        chunk_payload = payload.get("chunk", {})
        if isinstance(chunk_payload, dict):
            source_text = str(chunk_payload.get("content", "")).strip()
    if not source_text:
        raise HTTPException(status_code=400, detail="chunk 内容为空。")

    settings = request_settings(payload)
    character_name = normalize_target_character(payload.get("character_name", ""))
    chunk_meta = payload.get("chunk_meta", {})
    if not isinstance(chunk_meta, dict):
        chunk_meta = {}
    context = payload.get("context", {})

    if task == "worldbook":
        generated = await generate_worldbook_with_wbmaker(settings, source_text)
        return {
            "ok": True,
            "task": task,
            "chunk_meta": chunk_meta,
            "output": generated["store"],
            "parsed": generated["store"],
            "merge_summary": generated["merge_summary"],
        }

    output = await request_chat_completion(settings, [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": build_chunk_user(task, source_text, character_name, chunk_meta, context)},
    ])
    parsed, _ = try_parse_json(output)
    return {
        "ok": True,
        "task": task,
        "chunk_meta": chunk_meta,
        "output": output,
        "parsed": parsed,
    }


@app.post("/api/generate/merge")
async def api_generate_merge(payload: dict[str, Any]) -> dict[str, Any]:
    task = str(payload.get("task", "")).strip()
    system_prompt = task_system_prompt(task)
    partials = payload.get("partials", [])
    if not isinstance(partials, list) or not partials:
        raise HTTPException(status_code=400, detail="没有可合并的 chunk 结果。")

    settings = request_settings(payload)
    character_name = normalize_target_character(payload.get("character_name", ""))
    context = payload.get("context", {})

    if task == "worldbook":
        merged_worldbook = merge_worldbook_partials_with_wbmaker(partials)
        result = normalize_worldbook(merged_worldbook["store"])
        save_draft({
            "type": "worldbook",
            "character_name": character_name,
            "source_summary": f"wbmaker chunk merge: {len(partials)} chunks",
            "result": result,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "model": settings["model"],
        })
        return {
            "ok": True,
            "task": task,
            "result": result,
            "warnings": [f"已使用 WBmaker 逻辑合并 {len(partials)} 个 chunk。"],
            "merge_summaries": merged_worldbook["merge_summaries"],
        }

    output = await request_chat_completion(settings, [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": build_merge_user(task, partials, character_name, context)},
    ])
    parsed, error = try_parse_json(output)
    if parsed is None:
        save_draft({
            "type": f"{task}_merge_failed",
            "character_name": character_name,
            "source_summary": f"chunk merge failed: {len(partials)} chunks",
            "result": {
                "error": error,
                "raw_output_preview": output[:4000],
                "partials": partials,
            },
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "model": settings["model"],
        })
        raise HTTPException(
            status_code=500,
            detail=f"合并阶段模型输出不是合法 JSON：{error}。chunk 结果已保留，刷新后可继续重试合并。",
        )
    result = normalize_task_result(task, parsed, character_name)
    save_draft({
        "type": task_draft_type(task),
        "character_name": character_name,
        "source_summary": f"chunk merge: {len(partials)} chunks",
        "result": result,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "model": settings["model"],
    })
    return {
        "ok": True,
        "task": task,
        "result": result,
        "warnings": [f"已合并 {len(partials)} 个 chunk。"],
    }


# ─── Import endpoints ───

async def _proxy_import(main_base_url: str, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"{main_base_url.rstrip('/')}{endpoint}"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return {"ok": True, "result": response.json()}
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"导入失败：{exc}") from exc


@app.post("/api/import/card")
async def api_import_card(payload: dict[str, Any]) -> dict[str, Any]:
    card_data = payload.get("data", {})
    main_url = str(payload.get("main_base_url", "")).strip()
    if not main_url:
        raise HTTPException(status_code=400, detail="请提供 Fantareal 主程序地址。")
    return await _proxy_import(main_url, "/api/cards/import", {
        "raw_json": json.dumps(card_data, ensure_ascii=False),
        "filename": f"{card_data.get('name', 'yusheng')}.json",
        "apply_now": True,
    })


@app.post("/api/import/preset")
async def api_import_preset(payload: dict[str, Any]) -> dict[str, Any]:
    preset_data = payload.get("data", {})
    main_url = str(payload.get("main_base_url", "")).strip()
    if not main_url:
        raise HTTPException(status_code=400, detail="请提供 Fantareal 主程序地址。")
    return await _proxy_import(main_url, "/api/preset/import", {
        "raw_json": json.dumps(preset_data, ensure_ascii=False),
        "activate_now": True,
    })


@app.post("/api/import/memories")
async def api_import_memories(payload: dict[str, Any]) -> dict[str, Any]:
    mem_data = payload.get("data", {})
    main_url = str(payload.get("main_base_url", "")).strip()
    if not main_url:
        raise HTTPException(status_code=400, detail="请提供 Fantareal 主程序地址。")
    return await _proxy_import(main_url, "/api/memories/import", {
        "raw_json": json.dumps(mem_data, ensure_ascii=False),
    })


@app.post("/api/import/worldbook")
async def api_import_worldbook(payload: dict[str, Any]) -> dict[str, Any]:
    wb_data = payload.get("data", {})
    main_url = str(payload.get("main_base_url", "")).strip()
    if not main_url:
        raise HTTPException(status_code=400, detail="请提供 Fantareal 主程序地址。")
    apply_settings = bool(payload.get("apply_settings", False))
    return await _proxy_import(main_url, "/api/worldbook/import", {
        "raw_json": json.dumps(wb_data, ensure_ascii=False),
        "apply_settings": apply_settings,
    })


@app.post("/api/export/soul")
async def api_export_soul(payload: dict[str, Any]) -> FileResponse:
    base_name = sanitize_filename(
        payload.get("name") or payload.get("character_name") or payload.get("project_name"),
        "余声",
    )
    outputs = [
        ("worldbook_output", f"{base_name}的世界书.json"),
        ("memories_output", f"{base_name}的记忆.json"),
        ("preset_output", f"{base_name}的预设.json"),
        ("role_card_output", f"{base_name}的人设卡.json"),
    ]
    temp_dir = Path(tempfile.mkdtemp(prefix="yusheng_export_"))
    try:
        file_count = 0
        for key, filename in outputs:
            data = payload.get(key)
            if data in (None, "", {}):
                continue
            (temp_dir / filename).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            file_count += 1
        if file_count == 0:
            raise HTTPException(status_code=400, detail="没有可导出的世界书/记忆/预设/人设卡。")

        seven_zip = shutil.which("7z") or shutil.which("7za") or shutil.which("7zr") or r"D:\hdiff\7z.exe"
        if not seven_zip or not Path(seven_zip).exists():
            raise HTTPException(status_code=500, detail="未找到 7z.exe，无法生成 7z 压缩包。")

        archive_path = temp_dir / f"{base_name}的灵魂.7z"
        input_files = [str(temp_dir / filename) for _, filename in outputs if (temp_dir / filename).exists()]
        result = subprocess.run(
            [seven_zip, "a", "-t7z", "-mx=9", str(archive_path), *input_files],
            cwd=str(temp_dir),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0 or not archive_path.exists():
            detail = (result.stderr or result.stdout or "未知 7z 错误").strip()[:600]
            raise HTTPException(status_code=500, detail=f"7z 打包失败：{detail}")

        return FileResponse(
            archive_path,
            media_type="application/x-7z-compressed",
            filename=f"{base_name}的灵魂.7z",
            background=BackgroundTask(shutil.rmtree, temp_dir, ignore_errors=True),
        )
    except HTTPException:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise
    except Exception as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"导出失败：{exc}") from exc


@app.post("/api/export/soul-local")
async def api_export_soul_local(payload: dict[str, Any]) -> dict[str, Any]:
    base_name = sanitize_filename(
        payload.get("name") or payload.get("character_name") or payload.get("project_name"),
        "余声",
    )
    outputs = [
        ("worldbook_output", f"{base_name}的世界书.json"),
        ("memories_output", f"{base_name}的记忆.json"),
        ("preset_output", f"{base_name}的预设.json"),
        ("role_card_output", f"{base_name}的人设卡.json"),
    ]
    temp_dir = Path(tempfile.mkdtemp(prefix="yusheng_export_"))
    try:
        file_count = 0
        for key, filename in outputs:
            data = payload.get(key)
            if data in (None, "", {}):
                continue
            (temp_dir / filename).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            file_count += 1
        if file_count == 0:
            raise HTTPException(status_code=400, detail="没有可导出的世界书/记忆/预设/人设卡。")

        seven_zip = shutil.which("7z") or shutil.which("7za") or shutil.which("7zr") or r"D:\hdiff\7z.exe"
        if not seven_zip or not Path(seven_zip).exists():
            raise HTTPException(status_code=500, detail="未找到 7z.exe，无法生成 7z 压缩包。")

        downloads_dir = Path.home() / "Downloads"
        downloads_dir.mkdir(parents=True, exist_ok=True)
        archive_path = unique_path(downloads_dir / f"{base_name}的灵魂.7z")
        input_files = [str(temp_dir / filename) for _, filename in outputs if (temp_dir / filename).exists()]
        result = subprocess.run(
            [seven_zip, "a", "-t7z", "-mx=9", str(archive_path), *input_files],
            cwd=str(temp_dir),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0 or not archive_path.exists():
            detail = (result.stderr or result.stdout or "未知 7z 错误").strip()[:600]
            raise HTTPException(status_code=500, detail=f"7z 打包失败：{detail}")
        return {
            "ok": True,
            "path": str(archive_path),
            "filename": archive_path.name,
            "file_count": file_count,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"导出失败：{exc}") from exc
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8018, reload=True)
