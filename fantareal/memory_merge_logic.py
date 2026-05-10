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


def _sanitize_memory_item(item: Any, *, fallback_id: str) -> dict[str, Any]:
    if not isinstance(item, dict):
        item = {}

    return {
        "id": str(item.get("id", "")).strip() or fallback_id,
        "title": str(item.get("title", "")).strip(),
        "content": str(item.get("content", "")).strip(),
        "tags": _sanitize_tags(item.get("tags", [])),
        "notes": str(item.get("notes", "")).strip(),
    }


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
        "characters": str(item.get("characters", "")).strip(),
        "relationship_progress": str(item.get("relationship_progress", "")).strip(),
        "key_events": _sanitize_string_list(item.get("key_events", []), limit=16),
        "conflicts": str(item.get("conflicts", "")).strip(),
        "next_hooks": str(item.get("next_hooks", "")).strip(),
        "notes": str(item.get("notes", "")).strip(),
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
        '    "characters": "涉及角色，可为空",\n'
        '    "relationship_progress": "关系推进，可为空",\n'
        '    "key_events": ["事件1", "事件2"],\n'
        '    "conflicts": "矛盾点或问题，可为空",\n'
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
        "4. 如果原记忆中有重复内容，请自动去重合并。\n"
        "5. 不要虚构原记忆中没有的信息。\n"
        f"6. 合并记忆标题优先参考：{title_hint}\n"
        f"7. 大纲标题优先参考：{outline_hint}\n\n"
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
            "characters": "",
            "relationship_progress": "",
            "key_events": event_titles[:10],
            "conflicts": "",
            "next_hooks": "",
            "notes": "该大纲项由本地回退逻辑生成，未使用模型结构化总结。",
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
        "characters": str(data.get("characters", "")).strip(),
        "relationship_progress": str(data.get("relationship_progress", "")).strip(),
        "key_events": _sanitize_string_list(data.get("key_events", []), limit=16),
        "conflicts": str(data.get("conflicts", "")).strip(),
        "next_hooks": str(data.get("next_hooks", "")).strip(),
        "notes": str(data.get("notes", "")).strip(),
        "source_memory_ids": source_ids,
        "merged_memory_id": merged_memory_id,
        "updated_at": _now_text(),
    }
    return _sanitize_outline_item(outline_item, fallback_index=1)


async def merge_memories_to_outline(
    ctx: Any,
    memory_ids: list[str],
    *,
    merged_title: str = "",
    outline_title: str = "",
    delete_sources: bool = True,
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

    remaining_memories = current_memories
    removed_memory_ids: list[str] = []
    if delete_sources:
        remaining_memories = [item for item in current_memories if item["id"] not in selected_id_set]
        removed_memory_ids = [item["id"] for item in current_memories if item["id"] in selected_id_set]
        remaining_memories = ctx.save_memories(remaining_memories, active_slot)

    return {
        "ok": True,
        "mode": merge_mode,
        "active_slot": active_slot,
        "selected_count": len(selected_memories),
        "removed_memory_ids": removed_memory_ids,
        "remaining_items": remaining_memories,
        "merged_memory": merged_memory,
        "outline_item": outline_item,
        "merged_items": merged_memories,
        "outline_items": outline_items,
    }
