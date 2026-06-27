# memory_merge_logic.py

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from fastapi import HTTPException


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _build_api_url(base_url: str, endpoint: str) -> str:
    base = str(base_url or "").rstrip("/")
    suffix = str(endpoint or "").lstrip("/")
    if not base:
        return suffix
    if base.endswith("/v1"):
        return f"{base}/{suffix}"
    return f"{base}/v1/{suffix}"


def _compact_text(value: Any, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[: max(limit - 3, 0)].rstrip() + "..."


def _sanitize_tags(value: Any) -> list[str]:
    if isinstance(value, str):
        raw = value.replace("，", ",").replace("、", ",").split(",")
    elif isinstance(value, list):
        raw = value
    else:
        raw = []

    tags: list[str] = []
    for item in raw:
        text = str(item or "").strip()
        if text and text not in tags:
            tags.append(text)
    return tags[:8]


RP_IMPORTANT_ITEM_KEYWORDS = (
    "钥匙",
    "玉牌",
    "令牌",
    "信物",
    "戒指",
    "项链",
    "吊坠",
    "账本",
    "契约",
    "契书",
    "文书",
    "密信",
    "信件",
    "药",
    "药剂",
    "毒",
    "配方",
    "地图",
    "卷轴",
    "碎片",
    "印记",
    "刻印",
    "徽记",
    "债",
    "债务",
    "欠款",
    "银两",
    "金",
    "证据",
    "线索",
    "暗号",
    "密码",
    "门",
    "密室",
    "机关",
)

RP_UNRESOLVED_HINTS = (
    "未",
    "尚未",
    "仍需",
    "需要",
    "待",
    "等待",
    "继续",
    "后续",
    "之后",
    "尚待",
    "未解",
    "未定",
    "未完成",
    "未处理",
    "仍",
    "还需",
    "不得",
    "风险",
)

RP_FORESHADOWING_HINTS = (
    "伏笔",
    "暗示",
    "预兆",
    "隐患",
    "谜",
    "秘密",
    "真相",
    "揭示",
    "线索",
    "暗号",
    "密信",
    "尚未揭",
    "日后",
    "埋下",
    "疑点",
)


def _split_rp_candidate_sentences(*values: Any) -> list[str]:
    seen: set[str] = set()
    rows: list[str] = []
    for value in values:
        if isinstance(value, list):
            raw_parts = [str(item or "") for item in value]
        else:
            raw_parts = re.split(r"[\n。；;!?！？]+", str(value or ""))
        for part in raw_parts:
            text = re.sub(r"\s+", " ", str(part or "")).strip(" ，,、：:")
            if len(text) < 3:
                continue
            if text in seen:
                continue
            seen.add(text)
            rows.append(text)
    return rows


def _pick_rp_sentences(candidates: list[str], keywords: tuple[str, ...], *, limit: int = 4, char_limit: int = 180) -> str:
    picked: list[str] = []
    for text in candidates:
        if any(keyword and keyword in text for keyword in keywords):
            picked.append(_compact_text(text, 70))
        if len(picked) >= limit:
            break
    return "；".join(picked)[:char_limit]


def _extract_rp_location(candidates: list[str]) -> str:
    patterns = (
        r"(?:在|于|至|到|前往|抵达|进入|回到)([^，。；;、]{2,18}(?:宫|阁|院|府|城|镇|村|山|谷|湖|河|海|岛|寺|庙|塔|楼|馆|室|厅|门|桥|街|巷|店|营|宅|庄|殿|祠|苑|园|司|署|牢|狱|关|口|境|地))",
        r"([^，。；;、]{2,18}(?:宫|阁|院|府|城|镇|村|山|谷|湖|河|海|岛|寺|庙|塔|楼|馆|室|厅|门|桥|街|巷|店|营|宅|庄|殿|祠|苑|园|司|署|牢|狱|关|口|境|地))(?:中|内|外|前|后|里)",
    )
    for text in candidates:
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return _compact_text(match.group(1).strip(" ，,、：:"), 40)
    return ""


def _extract_rp_story_time(candidates: list[str]) -> str:
    patterns = (
        r"(第[一二三四五六七八九十百千万0-9]+[日天夜年月回幕章场段][^，。；;]{0,8})",
        r"([今昨明前后]夜|[今昨明前后]日|清晨|拂晓|黎明|上午|正午|午后|黄昏|傍晚|深夜|子时|丑时|寅时|卯时|辰时|巳时|午时|未时|申时|酉时|戌时|亥时)",
        r"([春夏秋冬][日夜]|冬至|除夕|元宵|中秋|雨夜|雪夜)",
    )
    for text in candidates:
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return _compact_text(match.group(1).strip(), 40)
    return ""


def _augment_outline_item_fields(outline_item: dict[str, Any], selected_memories: list[dict[str, Any]]) -> dict[str, Any]:
    memory_text_parts: list[Any] = []
    for item in selected_memories:
        memory_text_parts.extend([item.get("title", ""), item.get("content", ""), item.get("notes", ""), item.get("tags", [])])

    key_events = outline_item.get("key_events", []) if isinstance(outline_item.get("key_events"), list) else []
    candidates = _split_rp_candidate_sentences(
        outline_item.get("title", ""),
        outline_item.get("summary", ""),
        outline_item.get("relationship_progress", ""),
        outline_item.get("conflicts", ""),
        outline_item.get("next_hooks", ""),
        outline_item.get("notes", ""),
        key_events,
        *memory_text_parts,
    )

    if not str(outline_item.get("location", "")).strip():
        outline_item["location"] = _extract_rp_location(candidates)
    if not str(outline_item.get("story_time", "")).strip():
        story_time_candidates = _split_rp_candidate_sentences(
            outline_item.get("title", ""),
            outline_item.get("summary", ""),
            key_events,
            *memory_text_parts,
        )
        outline_item["story_time"] = _extract_rp_story_time(story_time_candidates)
    if not str(outline_item.get("important_items", "")).strip():
        outline_item["important_items"] = _pick_rp_sentences(candidates, RP_IMPORTANT_ITEM_KEYWORDS, limit=4, char_limit=220)
    if not str(outline_item.get("unresolved_items", "")).strip():
        outline_item["unresolved_items"] = _pick_rp_sentences(candidates, RP_UNRESOLVED_HINTS, limit=3, char_limit=200)
    if not str(outline_item.get("foreshadowing", "")).strip():
        outline_item["foreshadowing"] = _pick_rp_sentences(candidates, RP_FORESHADOWING_HINTS, limit=3, char_limit=200)
    if not str(outline_item.get("emotion_shift", "")).strip():
        outline_item["emotion_shift"] = _pick_rp_sentences(
            candidates,
            ("情绪", "愧", "怒", "恨", "怕", "恐", "惧", "信任", "依赖", "心软", "动摇", "释然", "悲", "喜", "羞", "怜", "怨"),
            limit=2,
            char_limit=160,
        )
    return outline_item


def _sanitize_memory_item(item: Any, *, fallback_id: str) -> dict[str, Any]:
    if not isinstance(item, dict):
        item = {}
    memory_status = str(item.get("memory_status", item.get("status", "active")) or "active").strip().lower()
    if memory_status not in {"active", "archived"}:
        memory_status = "active"

    return {
        "id": str(item.get("id", "")).strip() or fallback_id,
        "title": str(item.get("title", "")).strip(),
        "content": str(item.get("content", "")).strip(),
        "tags": _sanitize_tags(item.get("tags", [])),
        "notes": str(item.get("notes", "")).strip(),
        "memory_status": memory_status,
        "archived_at": str(item.get("archived_at", "")).strip() if memory_status == "archived" else "",
    }


def _parse_bool(value: Any, default: bool = True) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"1", "true", "yes", "on"}:
            return True
        if text in {"0", "false", "no", "off"}:
            return False
    if value is None:
        return default
    return bool(value)


def _sanitize_memory_list(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []

    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        normalized.append(_sanitize_memory_item(item, fallback_id=f"memory-{index}"))
    return normalized


def _sanitize_string_list(value: Any, *, limit: int = 12) -> list[str]:
    if isinstance(value, str):
        raw = [part.strip() for part in re.split(r"[,\n，、]+", value) if part.strip()]
    elif isinstance(value, list):
        raw = [str(part or "").strip() for part in value if str(part or "").strip()]
    else:
        raw = []

    result: list[str] = []
    for item in raw:
        if item and item not in result:
            result.append(item)
    return result[:limit]


def _sanitize_merged_memory_item(item: Any, *, fallback_index: int) -> dict[str, Any]:
    if not isinstance(item, dict):
        item = {}

    source_ids = _sanitize_string_list(item.get("source_memory_ids", []), limit=128)
    tags = _sanitize_tags(item.get("tags", []))

    return {
        "id": str(item.get("id", "")).strip() or f"merged-memory-{fallback_index}",
        "title": str(item.get("title", "")).strip(),
        "content": str(item.get("content", "")).strip(),
        "tags": tags,
        "notes": str(item.get("notes", "")).strip(),
        "source_memory_ids": source_ids,
        "created_at": str(item.get("created_at", "")).strip() or _now_text(),
    }


def _sanitize_merged_memory_list(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []

    return [
        _sanitize_merged_memory_item(item, fallback_index=index)
        for index, item in enumerate(items, start=1)
    ]


def _sanitize_outline_item(item: Any, *, fallback_index: int) -> dict[str, Any]:
    if not isinstance(item, dict):
        item = {}

    return {
        "id": str(item.get("id", "")).strip() or f"memory-outline-{fallback_index}",
        "title": str(item.get("title", "")).strip(),
        "summary": str(item.get("summary", "")).strip(),
        "story_time": str(item.get("story_time", "")).strip(),
        "chapter": str(item.get("chapter", "")).strip(),
        "location": str(item.get("location", "")).strip(),
        "characters": str(item.get("characters", "")).strip(),
        "relationship_progress": str(item.get("relationship_progress", "")).strip(),
        "emotion_shift": str(item.get("emotion_shift", "")).strip(),
        "key_events": _sanitize_string_list(item.get("key_events", []), limit=16),
        "conflicts": str(item.get("conflicts", "")).strip(),
        "foreshadowing": str(item.get("foreshadowing", "")).strip(),
        "unresolved_items": str(item.get("unresolved_items", "")).strip(),
        "important_items": str(item.get("important_items", "")).strip(),
        "next_hooks": str(item.get("next_hooks", "")).strip(),
        "notes": str(item.get("notes", "")).strip(),
        "participate_recall": _parse_bool(item.get("participate_recall"), True),
        "project_to_worldbook": _parse_bool(item.get("project_to_worldbook"), True),
        "source_memory_ids": _sanitize_string_list(item.get("source_memory_ids", []), limit=128),
        "merged_memory_id": str(item.get("merged_memory_id", "")).strip(),
        "updated_at": str(item.get("updated_at", "")).strip() or _now_text(),
    }


def _sanitize_outline_list(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []

    return [
        _sanitize_outline_item(item, fallback_index=index)
        for index, item in enumerate(items, start=1)
    ]


def _base_data_dir(ctx: Any, slot_id: str | None = None) -> Path:
    return Path(ctx.memories_path(slot_id)).resolve().parent


def merged_memories_path(ctx: Any, slot_id: str | None = None) -> Path:
    return _base_data_dir(ctx, slot_id) / "merged_memories.json"


def memory_outline_path(ctx: Any, slot_id: str | None = None) -> Path:
    return _base_data_dir(ctx, slot_id) / "memory_outline.json"


def get_merged_memories(ctx: Any, slot_id: str | None = None) -> list[dict[str, Any]]:
    raw = ctx.read_json(merged_memories_path(ctx, slot_id), [])
    return _sanitize_merged_memory_list(raw)


def save_merged_memories(ctx: Any, items: list[dict[str, Any]], slot_id: str | None = None) -> list[dict[str, Any]]:
    sanitized = _sanitize_merged_memory_list(items)
    ctx.persist_json(
        merged_memories_path(ctx, slot_id),
        sanitized,
        detail="Merged memories save failed. Please check disk space or file permissions.",
    )
    return sanitized


def get_memory_outline(ctx: Any, slot_id: str | None = None) -> list[dict[str, Any]]:
    raw = ctx.read_json(memory_outline_path(ctx, slot_id), [])
    return _sanitize_outline_list(raw)


def save_memory_outline(ctx: Any, items: list[dict[str, Any]], slot_id: str | None = None) -> list[dict[str, Any]]:
    sanitized = _sanitize_outline_list(items)
    ctx.persist_json(
        memory_outline_path(ctx, slot_id),
        sanitized,
        detail="Memory outline save failed. Please check disk space or file permissions.",
    )
    return sanitized


def build_memory_merge_prompt(
    selected_memories: list[dict[str, Any]],
    *,
    merged_title: str = "",
    outline_title: str = "",
) -> str:
    lines: list[str] = []
    for index, item in enumerate(selected_memories, start=1):
        lines.append(
            "\n".join(
                [
                    f"[Memory {index}]",
                    f"id: {item.get('id', '')}",
                    f"title: {item.get('title', '')}",
                    f"tags: {', '.join(item.get('tags', []))}",
                    f"content: {item.get('content', '')}",
                    f"notes: {item.get('notes', '')}",
                ]
            )
        )

    title_hint = merged_title.strip() or "请根据内容自动拟定合并标题"
    outline_hint = outline_title.strip() or "请根据内容自动拟定大纲标题"

    schema_hint = (
        '{\n'
        '  "merged_memory": {\n'
        '    "title": "合并后的记忆标题",\n'
        '    "content": "合并后的详细总结正文",\n'
        '    "tags": ["tag1", "tag2"],\n'
        '    "notes": "补充说明，可为空"\n'
        '  },\n'
        '  "outline_item": {\n'
        '    "title": "大纲标题",\n'
        '    "summary": "这一批记忆的大纲总结",\n'
        '    "story_time": "剧情时间或章节内时间，可为空",\n'
        '    "chapter": "章节、幕次或剧情段落，可为空",\n'
        '    "location": "主要地点，可为空",\n'
        '    "characters": "涉及角色，可为空",\n'
        '    "relationship_progress": "关系推进，可为空",\n'
        '    "emotion_shift": "情绪变化，可为空",\n'
        '    "key_events": ["事件1", "事件2"],\n'
        '    "conflicts": "矛盾点或问题，可为空",\n'
        '    "foreshadowing": "伏笔，可为空",\n'
        '    "unresolved_items": "未解决事项，可为空",\n'
        '    "important_items": "重要物品或线索，可为空",\n'
        '    "next_hooks": "后续可延展钩子，可为空",\n'
        '    "notes": "额外补充，可为空"\n'
        '  }\n'
        '}'
    )

    return (
        "请把下面多条长期记忆合并成一条新的“合并记忆”，并同时生成一条“大纲表项”。\n"
        "要求：\n"
        "1. 输出必须是一个严格 JSON 对象，不要输出 markdown，不要解释。\n"
        "2. merged_memory.content 要尽量保留事实，不要空泛。\n"
        "3. outline_item.summary 要偏大纲摘要；key_events 要列关键事件。\n"
        "4. outline_item 要主动填写 RP 剧情档案字段，宁可给用户一个可编辑草稿，也不要把明显信息留空。\n"
        "5. 分类规则：\n"
        "   - story_time：第几日、夜晚、雨夜、某章节内时间等。\n"
        "   - chapter：篇章、幕次、阶段名、事件线名称。\n"
        "   - location：明确发生地点、去向、门厅、宫室、城镇等。\n"
        "   - emotion_shift：角色态度、信任、愧疚、恐惧、依赖、敌意、心软等变化。\n"
        "   - foreshadowing：未来可能揭示的秘密、疑点、暗示、隐患、未明真相。\n"
        "   - unresolved_items：仍需处理、尚未完成、后续必须解决的事。\n"
        "   - important_items：钥匙、玉牌、信物、账本、契约、密信、药、债务、欠款、证据、暗号、机关等物品或线索。\n"
        "6. 如果原文出现“玉牌、信物、契约、债务、密信、账本、钥匙、药、地图、证据、暗号、机关”，通常应写入 important_items。\n"
        "7. 如果原文出现“后续、仍需、尚未、待、未解、不得、风险”，通常应写入 unresolved_items 或 next_hooks。\n"
        "8. 只能从原记忆中提取和压缩，不要虚构原记忆中没有的信息；确实没有依据才保持空字符串。\n"
        "9. 如果原记忆中有重复内容，请自动去重合并。\n"
        f"10. 合并记忆标题优先参考：{title_hint}\n"
        f"11. 大纲标题优先参考：{outline_hint}\n\n"
        f"格式示例：\n{schema_hint}\n\n"
        f"待合并记忆：\n\n{chr(10).join(lines)}"
    )


def _fallback_merge_result(
    selected_memories: list[dict[str, Any]],
    *,
    merged_title: str = "",
    outline_title: str = "",
) -> dict[str, Any]:
    titles = [str(item.get("title", "")).strip() for item in selected_memories if str(item.get("title", "")).strip()]
    tags: list[str] = []
    for item in selected_memories:
        for tag in item.get("tags", []):
            if tag not in tags:
                tags.append(tag)

    merged_content_parts: list[str] = []
    notes_parts: list[str] = []
    event_titles: list[str] = []

    for item in selected_memories:
        title = str(item.get("title", "")).strip()
        content = _compact_text(item.get("content", ""), 220)
        notes = _compact_text(item.get("notes", ""), 160)
        if title:
            event_titles.append(title)
        if title or content:
            merged_content_parts.append(
                f"{title or '未命名记忆'}：{content}" if content else (title or "未命名记忆")
            )
        if notes:
            notes_parts.append(f"{title or '未命名记忆'}备注：{notes}")

    auto_merged_title = merged_title.strip() or (titles[0] if titles else f"合并记忆 {_now_text()}")
    auto_outline_title = outline_title.strip() or auto_merged_title

    merged_content = "；".join(part for part in merged_content_parts if part).strip() or "这是一条由多条原记忆合并生成的新记忆。"
    outline_summary = (
        "本批记忆主要围绕以下内容展开："
        + "；".join(_compact_text(item.get("content", ""), 90) for item in selected_memories if str(item.get("content", "")).strip())
    ).strip("：")

    return {
        "merged_memory": {
            "title": auto_merged_title[:60],
            "content": merged_content[:1200],
            "tags": (tags or ["merged-memory", "summary"])[:8],
            "notes": "\n".join(notes_parts)[:1200],
        },
        "outline_item": {
            "title": auto_outline_title[:80],
            "summary": outline_summary[:900] or merged_content[:300],
            "story_time": "",
            "chapter": "",
            "location": "",
            "characters": "",
            "relationship_progress": "",
            "emotion_shift": "",
            "key_events": event_titles[:10],
            "conflicts": "",
            "foreshadowing": "",
            "unresolved_items": "",
            "important_items": "",
            "next_hooks": "",
            "notes": "该大纲项由本地回退逻辑生成，未使用模型结构化总结。",
            "participate_recall": True,
            "project_to_worldbook": True,
        },
    }


def _parse_merge_response_json(text: str) -> dict[str, Any]:
    cleaned = str(text or "").strip()
    if not cleaned:
        raise ValueError("empty merge response")

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        parsed = json.loads(cleaned)
    except ValueError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        parsed = json.loads(cleaned[start : end + 1])

    if not isinstance(parsed, dict):
        raise ValueError("merge response is not a json object")

    if "merged_memory" not in parsed or "outline_item" not in parsed:
        raise ValueError("merge response missing required keys")

    if not isinstance(parsed["merged_memory"], dict) or not isinstance(parsed["outline_item"], dict):
        raise ValueError("merge response inner payload invalid")

    return parsed


async def request_memory_merge_with_model(
    ctx: Any,
    selected_memories: list[dict[str, Any]],
    *,
    merged_title: str = "",
    outline_title: str = "",
    runtime_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    llm_config = ctx.get_runtime_chat_config(runtime_overrides)
    if not (llm_config.get("base_url") and llm_config.get("model")):
        raise ValueError("chat model is not configured")

    url = _build_api_url(llm_config["base_url"], "chat/completions")
    prompt = build_memory_merge_prompt(
        selected_memories,
        merged_title=merged_title,
        outline_title=outline_title,
    )

    payload = {
        "model": llm_config["model"],
        "temperature": 0.2,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a long-term memory merger and outline formatter. "
                    "Return one strict JSON object only. "
                    "Do not output markdown, explanation, XML, or any extra text. "
                    "The JSON object must contain exactly two top-level keys: merged_memory and outline_item."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    }

    headers = {"Content-Type": "application/json"}
    api_key = str(llm_config.get("api_key", "")).strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    async with httpx.AsyncClient(timeout=float(llm_config.get("request_timeout", 120))) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    try:
        text = str(data["choices"][0]["message"]["content"]).strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("invalid merge summary payload") from exc

    try:
        return _parse_merge_response_json(text)
    except Exception:
        repair_payload = {
            "model": llm_config["model"],
            "temperature": 0.0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Convert the provided content into one strict JSON object only. "
                        "Do not output markdown or explanation. "
                        "The object must contain exactly two top-level keys: merged_memory and outline_item."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Repair the following content into strict JSON.\n"
                        f"Original content:\n{text}"
                    ),
                },
            ],
        }

        async with httpx.AsyncClient(timeout=float(llm_config.get("request_timeout", 120))) as client:
            repair_response = await client.post(url, headers=headers, json=repair_payload)
            repair_response.raise_for_status()
            repair_data = repair_response.json()

        repaired_text = str(repair_data["choices"][0]["message"]["content"]).strip()
        return _parse_merge_response_json(repaired_text)


def _build_final_merged_memory(
    payload: dict[str, Any],
    *,
    selected_memories: list[dict[str, Any]],
    merged_title: str = "",
) -> dict[str, Any]:
    data = payload.get("merged_memory", {}) if isinstance(payload, dict) else {}
    source_ids = [str(item.get("id", "")).strip() for item in selected_memories if str(item.get("id", "")).strip()]
    auto_title = merged_title.strip() or str(data.get("title", "")).strip() or "合并记忆"
    auto_notes = str(data.get("notes", "")).strip()
    if source_ids:
        source_note = f"由 {len(source_ids)} 条原记忆合并生成"
        auto_notes = f"{source_note}\n{auto_notes}".strip()

    merged_item = {
        "id": f"merged-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        "title": auto_title[:60],
        "content": str(data.get("content", "")).strip()[:1200],
        "tags": (_sanitize_tags(data.get("tags", [])) or ["merged-memory", "summary"])[:8],
        "notes": auto_notes[:1200],
        "source_memory_ids": source_ids,
        "created_at": _now_text(),
    }
    return _sanitize_merged_memory_item(merged_item, fallback_index=1)


def _build_final_outline_item(
    payload: dict[str, Any],
    *,
    selected_memories: list[dict[str, Any]],
    merged_memory_id: str,
    outline_title: str = "",
) -> dict[str, Any]:
    data = payload.get("outline_item", {}) if isinstance(payload, dict) else {}
    source_ids = [str(item.get("id", "")).strip() for item in selected_memories if str(item.get("id", "")).strip()]

    outline_item = {
        "id": f"outline-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        "title": outline_title.strip() or str(data.get("title", "")).strip() or "记忆大纲",
        "summary": str(data.get("summary", "")).strip(),
        "story_time": str(data.get("story_time", "")).strip(),
        "chapter": str(data.get("chapter", "")).strip(),
        "location": str(data.get("location", "")).strip(),
        "characters": str(data.get("characters", "")).strip(),
        "relationship_progress": str(data.get("relationship_progress", "")).strip(),
        "emotion_shift": str(data.get("emotion_shift", "")).strip(),
        "key_events": _sanitize_string_list(data.get("key_events", []), limit=16),
        "conflicts": str(data.get("conflicts", "")).strip(),
        "foreshadowing": str(data.get("foreshadowing", "")).strip(),
        "unresolved_items": str(data.get("unresolved_items", "")).strip(),
        "important_items": str(data.get("important_items", "")).strip(),
        "next_hooks": str(data.get("next_hooks", "")).strip(),
        "notes": str(data.get("notes", "")).strip(),
        "participate_recall": True,
        "project_to_worldbook": True,
        "source_memory_ids": source_ids,
        "merged_memory_id": merged_memory_id,
        "updated_at": _now_text(),
    }
    outline_item = _augment_outline_item_fields(outline_item, selected_memories)
    return _sanitize_outline_item(outline_item, fallback_index=1)


async def merge_memories_to_outline(
    ctx: Any,
    memory_ids: list[str],
    *,
    merged_title: str = "",
    outline_title: str = "",
    delete_sources: bool = True,
    source_action: str = "",
    slot_id: str | None = None,
    runtime_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    active_slot = slot_id or ctx.get_active_slot_id()
    normalized_ids = [str(item or "").strip() for item in memory_ids if str(item or "").strip()]
    dedup_ids: list[str] = []
    for item in normalized_ids:
        if item not in dedup_ids:
            dedup_ids.append(item)

    if len(dedup_ids) < 2:
        raise HTTPException(status_code=400, detail="请至少选择两条原记忆再执行合并。")

    current_memories = _sanitize_memory_list(ctx.get_memories(active_slot))
    selected_memories = [item for item in current_memories if item["id"] in dedup_ids]
    selected_id_set = {item["id"] for item in selected_memories}
    missing_ids = [item for item in dedup_ids if item not in selected_id_set]

    if missing_ids:
        raise HTTPException(
            status_code=404,
            detail=f"以下记忆不存在或已失效：{', '.join(missing_ids)}",
        )

    try:
        merge_payload = await request_memory_merge_with_model(
            ctx,
            selected_memories,
            merged_title=merged_title,
            outline_title=outline_title,
            runtime_overrides=runtime_overrides,
        )
        merge_mode = "model"
    except Exception as exc:  # noqa: BLE001
        if hasattr(ctx, "logger"):
            ctx.logger.warning("记忆合并模型调用失败，改用本地合并：%s", exc)
        merge_payload = _fallback_merge_result(
            selected_memories,
            merged_title=merged_title,
            outline_title=outline_title,
        )
        merge_mode = "fallback"

    merged_memory = _build_final_merged_memory(
        merge_payload,
        selected_memories=selected_memories,
        merged_title=merged_title,
    )
    outline_item = _build_final_outline_item(
        merge_payload,
        selected_memories=selected_memories,
        merged_memory_id=merged_memory["id"],
        outline_title=outline_title,
    )

    merged_memories = get_merged_memories(ctx, active_slot)
    merged_memories.append(merged_memory)
    merged_memories = save_merged_memories(ctx, merged_memories, active_slot)

    outline_items = get_memory_outline(ctx, active_slot)
    outline_items.append(outline_item)
    outline_items = save_memory_outline(ctx, outline_items, active_slot)

    normalized_source_action = str(source_action or "").strip().lower()
    if normalized_source_action not in {"delete", "archive", "keep"}:
        normalized_source_action = "delete" if delete_sources else "keep"

    remaining_memories = current_memories
    removed_memory_ids: list[str] = []
    archived_memory_ids: list[str] = []
    if normalized_source_action == "delete":
        remaining_memories = [item for item in current_memories if item["id"] not in selected_id_set]
        removed_memory_ids = [item["id"] for item in current_memories if item["id"] in selected_id_set]
        remaining_memories = ctx.save_memories(remaining_memories, active_slot)
    elif normalized_source_action == "archive":
        archived_at = _now_text()
        remaining_memories = []
        for item in current_memories:
            if item["id"] in selected_id_set:
                archived_item = {
                    **item,
                    "memory_status": "archived",
                    "archived_at": archived_at,
                }
                remaining_memories.append(archived_item)
                archived_memory_ids.append(item["id"])
            else:
                remaining_memories.append(item)
        remaining_memories = ctx.save_memories(remaining_memories, active_slot)

    return {
        "ok": True,
        "mode": merge_mode,
        "source_action": normalized_source_action,
        "active_slot": active_slot,
        "selected_count": len(selected_memories),
        "removed_memory_ids": removed_memory_ids,
        "archived_memory_ids": archived_memory_ids,
        "remaining_items": remaining_memories,
        "merged_memory": merged_memory,
        "outline_item": outline_item,
        "merged_items": merged_memories,
        "outline_items": outline_items,
    }
