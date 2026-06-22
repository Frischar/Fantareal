from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any

from .memory_merge_logic import get_memory_outline, get_merged_memories


MANAGED_SOURCE = "fantareal_memory_sync"
MANAGED_GROUP = "managed_memory"
MANAGED_ID_PREFIX = "managed-memory-"


def _compact_text(value: Any, limit: int = 240) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[: max(limit - 3, 0)].rstrip() + "..."


def _clean_id(value: Any, fallback: str) -> str:
    text = str(value or "").strip() or fallback
    text = re.sub(r"\s+", "-", text.lower())
    text = re.sub(r"[^a-z0-9_\-]+", "", text)
    text = re.sub(r"[_\-]{2,}", "-", text).strip("-_")
    return text or fallback


def _stable_hash(value: Any, length: int = 12) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:length]


def _clamp_int(value: Any, minimum: int, maximum: int, default: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(maximum, number))


def sanitize_sync_options(raw: dict[str, Any] | None = None) -> dict[str, Any]:
    source = raw if isinstance(raw, dict) else {}
    return {
        "include_core": bool(source.get("include_core", True)),
        "include_index": bool(source.get("include_index", True)),
        "include_details": bool(source.get("include_details", True)),
        "recent_constant_count": _clamp_int(source.get("recent_constant_count"), 0, 12, 3),
        "detail_entry_limit": _clamp_int(source.get("detail_entry_limit"), 1, 200, 80),
        "index_entry_limit": _clamp_int(source.get("index_entry_limit"), 1, 200, 80),
        "replace_existing": bool(source.get("replace_existing", True)),
        "confirm_replace_existing": bool(source.get("confirm_replace_existing", False)),
    }


def is_managed_memory_worldbook_entry(entry: dict[str, Any]) -> bool:
    if not isinstance(entry, dict):
        return False
    if str(entry.get("external_source", "")).strip() == MANAGED_SOURCE:
        return True
    metadata = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {}
    if str(metadata.get("managed_by", "")).strip() == MANAGED_SOURCE:
        return True
    entry_id = str(entry.get("id", "")).strip()
    group = str(entry.get("group", "")).strip()
    return entry_id.startswith(MANAGED_ID_PREFIX) and group == MANAGED_GROUP


def _outline_rows(outline_items: list[dict[str, Any]], merged_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged_by_id = {
        str(item.get("id", "")).strip(): item
        for item in merged_items
        if isinstance(item, dict) and str(item.get("id", "")).strip()
    }
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(outline_items, start=1):
        if not isinstance(item, dict):
            continue
        merged_id = str(item.get("merged_memory_id", "")).strip()
        merged = merged_by_id.get(merged_id, {})
        source_ids = item.get("source_memory_ids") if isinstance(item.get("source_memory_ids"), list) else []
        rows.append(
            {
                "source": "outline",
                "source_index": index,
                "outline_id": str(item.get("id", "")).strip() or f"outline-{index}",
                "merged_memory_id": merged_id,
                "source_memory_ids": [str(value).strip() for value in source_ids if str(value).strip()],
                "title": str(item.get("title", "")).strip() or str(merged.get("title", "")).strip() or f"记忆大纲 {index}",
                "summary": str(item.get("summary", "")).strip() or str(merged.get("content", "")).strip(),
                "characters": str(item.get("characters", "")).strip(),
                "relationship_progress": str(item.get("relationship_progress", "")).strip(),
                "key_events": item.get("key_events") if isinstance(item.get("key_events"), list) else [],
                "conflicts": str(item.get("conflicts", "")).strip(),
                "next_hooks": str(item.get("next_hooks", "")).strip(),
                "notes": str(item.get("notes", "")).strip(),
                "updated_at": str(item.get("updated_at", "")).strip(),
            }
        )
    if rows:
        return rows

    for index, item in enumerate(merged_items, start=1):
        if not isinstance(item, dict):
            continue
        source_ids = item.get("source_memory_ids") if isinstance(item.get("source_memory_ids"), list) else []
        rows.append(
            {
                "source": "merged",
                "source_index": index,
                "outline_id": "",
                "merged_memory_id": str(item.get("id", "")).strip() or f"merged-{index}",
                "source_memory_ids": [str(value).strip() for value in source_ids if str(value).strip()],
                "title": str(item.get("title", "")).strip() or f"合并记忆 {index}",
                "summary": str(item.get("content", "")).strip(),
                "characters": "",
                "relationship_progress": "",
                "key_events": [],
                "conflicts": "",
                "next_hooks": "",
                "notes": str(item.get("notes", "")).strip(),
                "updated_at": str(item.get("created_at", "")).strip(),
            }
        )
    return rows


def _row_code(index: int) -> str:
    return f"FM{index:04d}"


def _metadata(row: dict[str, Any], code: str, sync_hash: str, entry_kind: str) -> dict[str, Any]:
    return {
        "managed_by": MANAGED_SOURCE,
        "entry_kind": entry_kind,
        "code": code,
        "outline_id": row.get("outline_id", ""),
        "merged_memory_id": row.get("merged_memory_id", ""),
        "source_memory_ids": row.get("source_memory_ids", []),
        "sync_hash": sync_hash,
    }


def _base_entry(
    *,
    entry_id: str,
    title: str,
    content: str,
    entry_type: str,
    prompt_layer: str,
    order: int,
    trigger: str = "",
    comment: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": entry_id,
        "title": title,
        "trigger": trigger,
        "secondary_trigger": "",
        "content": content,
        "enabled": True,
        "priority": order,
        "order": order,
        "group": MANAGED_GROUP,
        "entry_type": entry_type,
        "group_operator": "and",
        "chance": 100,
        "sticky_turns": 0,
        "cooldown_turns": 0,
        "insertion_position": "after_char_defs",
        "injection_depth": 0,
        "injection_role": "system",
        "injection_order": order,
        "prompt_layer": prompt_layer,
        "recursive_enabled": True,
        "prevent_further_recursion": True,
        "external_source": MANAGED_SOURCE,
        "external_ref": {"type": "memory_sync"},
        "activation_tags": [],
        "case_sensitive": False,
        "whole_word": False,
        "match_mode": "any",
        "secondary_mode": "all",
        "comment": comment,
        "metadata": metadata or {},
    }


def _trigger_terms(row: dict[str, Any], code: str) -> str:
    raw_parts: list[str] = [code, row.get("title", ""), row.get("characters", "")]
    raw_parts.extend(str(item) for item in row.get("key_events", []) if str(item).strip())
    raw_parts.append(row.get("relationship_progress", ""))
    raw_parts.append(row.get("next_hooks", ""))

    terms: list[str] = []
    stop_words = {"记忆", "总结", "大纲", "阶段", "事件", "关系", "当前", "无", "暂无"}
    for part in raw_parts:
        for token in re.split(r"[,，、/|｜;；\s\n]+", str(part or "")):
            text = token.strip("：:。.，,；;（）()[]【】<>《》\"'`")
            if not text or text in stop_words:
                continue
            if len(text) < 2 or len(text) > 32:
                continue
            if text not in terms:
                terms.append(text)
            if len(terms) >= 12:
                return ", ".join(terms)
    return ", ".join(terms) if terms else code


def _detail_content(row: dict[str, Any], code: str) -> str:
    lines = [
        f"【过往记忆 {code}】",
        "这是已经发生过的 RP 事实，只作为连续性参考。不要主动向用户复述本条总结；当前剧情相关时，应该自然体现在态度、称呼、行动、回忆反应和剧情承接中。",
        f"标题：{row.get('title', '')}",
    ]
    if row.get("updated_at"):
        lines.append(f"记录时间：{row['updated_at']}")
    if row.get("characters"):
        lines.append(f"涉及角色：{row['characters']}")
    if row.get("summary"):
        lines.append(f"摘要：{row['summary']}")
    if row.get("relationship_progress"):
        lines.append(f"关系进展：{row['relationship_progress']}")
    events = [str(item).strip() for item in row.get("key_events", []) if str(item).strip()]
    if events:
        lines.append("关键事件：")
        lines.extend(f"- {item}" for item in events[:8])
    if row.get("conflicts"):
        lines.append(f"冲突/风险：{row['conflicts']}")
    if row.get("next_hooks"):
        lines.append(f"后续钩子：{row['next_hooks']}")
    if row.get("notes"):
        lines.append(f"备注：{row['notes']}")
    lines.append("注入策略：默认常驻；如需精确召回，可在世界书词条管理中手动改为关键词触发。")
    return "\n".join(line for line in lines if str(line).strip())


def _build_detail_entries(rows: list[dict[str, Any]], options: dict[str, Any]) -> list[dict[str, Any]]:
    if not options["include_details"]:
        return []
    limit = options["detail_entry_limit"]
    selected_rows = rows[-limit:] if len(rows) > limit else rows

    entries: list[dict[str, Any]] = []
    for local_index, row in enumerate(selected_rows, start=1):
        source_index = int(row.get("source_index") or local_index)
        code = _row_code(source_index)
        sync_hash = _stable_hash(row)
        source_key = row.get("outline_id") or row.get("merged_memory_id") or code
        entry_id = f"{MANAGED_ID_PREFIX}{_clean_id(source_key, code.lower())}"
        entries.append(
            _base_entry(
                entry_id=entry_id,
                title=f"记忆投影 {code}：{_compact_text(row.get('title', ''), 36)}",
                trigger="",
                content=_detail_content(row, code),
                entry_type="constant",
                prompt_layer="stable",
                order=9050 + (len(selected_rows) - local_index),
                comment=f"Fantareal 记忆投影 detail {code}",
                metadata=_metadata(row, code, sync_hash, "detail"),
            )
        )
    return entries


def _build_core_entry(rows: list[dict[str, Any]], options: dict[str, Any]) -> list[dict[str, Any]]:
    if not options["include_core"] or not rows:
        return []
    recent_count = min(max(options["recent_constant_count"], 1), len(rows))
    recent_rows = rows[-recent_count:]
    lines = [
        "【长期记忆核心状态】",
        "以下内容是已经发生过的 RP 事实和当前连续性状态。请隐性使用，不要主动向用户复述为总结。",
        f"同步时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"来源摘要数量：{len(rows)} 条；最近常驻摘要：{recent_count} 条。",
        "",
        "最近关键摘要：",
    ]
    for index, row in enumerate(recent_rows, start=1):
        code = _row_code(int(row.get("source_index") or index))
        summary = _compact_text(row.get("summary", ""), 180)
        hook = _compact_text(row.get("next_hooks", ""), 120)
        line = f"- {code} {row.get('title', '')}：{summary}"
        if hook:
            line += f" 后续：{hook}"
        lines.append(line)
    return [
        _base_entry(
            entry_id=f"{MANAGED_ID_PREFIX}core-state",
            title="记忆投影：长期记忆核心状态",
            content="\n".join(lines).strip(),
            entry_type="constant",
            prompt_layer="current_state",
            order=9000,
            comment="Fantareal 记忆投影 core",
            metadata={
                "managed_by": MANAGED_SOURCE,
                "entry_kind": "core",
                "source_count": len(rows),
                "recent_constant_count": recent_count,
                "sync_hash": _stable_hash(rows),
            },
        )
    ]


def _build_index_entry(rows: list[dict[str, Any]], options: dict[str, Any]) -> list[dict[str, Any]]:
    if not options["include_index"] or not rows:
        return []
    limit = options["index_entry_limit"]
    selected_rows = rows[-limit:] if len(rows) > limit else rows
    lines = [
        "【长期记忆大纲索引】",
        "以下索引用于了解过往剧情阶段。需要具体细节时，以对应过往记忆条目为准；不要主动朗读索引。",
    ]
    for row in selected_rows:
        code = _row_code(int(row.get("source_index") or 0))
        title = _compact_text(row.get("title", ""), 44)
        summary = _compact_text(row.get("summary", ""), 80)
        lines.append(f"- {code}：{title}。{summary}")
    return [
        _base_entry(
            entry_id=f"{MANAGED_ID_PREFIX}outline-index",
            title="记忆投影：长期记忆大纲索引",
            content="\n".join(lines).strip(),
            entry_type="constant",
            prompt_layer="stable",
            order=9001,
            comment="Fantareal 记忆投影 index",
            metadata={
                "managed_by": MANAGED_SOURCE,
                "entry_kind": "index",
                "source_count": len(rows),
                "listed_count": len(selected_rows),
                "sync_hash": _stable_hash(selected_rows),
            },
        )
    ]


def build_memory_worldbook_entries(
    outline_items: list[dict[str, Any]],
    merged_items: list[dict[str, Any]],
    raw_options: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    options = sanitize_sync_options(raw_options)
    rows = _outline_rows(outline_items, merged_items)
    entries: list[dict[str, Any]] = []
    entries.extend(_build_core_entry(rows, options))
    entries.extend(_build_index_entry(rows, options))
    entries.extend(_build_detail_entries(rows, options))

    constant_count = sum(1 for entry in entries if entry.get("entry_type") == "constant")
    keyword_count = sum(1 for entry in entries if entry.get("entry_type") == "keyword")
    stats = {
        "source_outline_count": len(outline_items),
        "source_merged_count": len(merged_items),
        "source_row_count": len(rows),
        "generated_count": len(entries),
        "constant_count": constant_count,
        "keyword_count": keyword_count,
        "estimated_chars": sum(len(str(entry.get("content", ""))) for entry in entries),
        "options": options,
    }
    return entries, stats


def preview_memory_worldbook_sync(ctx: Any, raw_options: dict[str, Any] | None = None, slot_id: str | None = None) -> dict[str, Any]:
    active_slot = slot_id or ctx.get_active_slot_id()
    outline_items = get_memory_outline(ctx, active_slot)
    merged_items = get_merged_memories(ctx, active_slot)
    entries, stats = build_memory_worldbook_entries(outline_items, merged_items, raw_options)
    worldbook_store = ctx.get_worldbook_store(active_slot)
    existing_managed = [entry for entry in worldbook_store.get("entries", []) if is_managed_memory_worldbook_entry(entry)]
    stats["existing_managed_count"] = len(existing_managed)
    stats["will_replace_count"] = len(existing_managed) if stats["options"]["replace_existing"] else 0
    return {
        "ok": True,
        "active_slot": active_slot,
        "entries": entries,
        "stats": stats,
    }


def apply_memory_worldbook_sync(ctx: Any, raw_options: dict[str, Any] | None = None, slot_id: str | None = None) -> dict[str, Any]:
    preview = preview_memory_worldbook_sync(ctx, raw_options, slot_id)
    active_slot = preview["active_slot"]
    options = preview["stats"]["options"]
    existing_managed_count = int(preview["stats"].get("existing_managed_count") or 0)
    if options["replace_existing"] and existing_managed_count and not options["confirm_replace_existing"]:
        return {
            "ok": False,
            "requires_confirmation": True,
            "active_slot": active_slot,
            "stats": preview["stats"],
            "entries": preview["entries"],
            "items": [],
            "settings": {},
        }
    worldbook_store = ctx.get_worldbook_store(active_slot)
    current_entries = list(worldbook_store.get("entries", []))
    if options["replace_existing"]:
        kept_entries = [entry for entry in current_entries if not is_managed_memory_worldbook_entry(entry)]
    else:
        kept_entries = current_entries
    saved_store = ctx.save_worldbook_store(
        {
            "settings": worldbook_store.get("settings", {}),
            "entries": kept_entries + preview["entries"],
        },
        active_slot,
    )
    removed_count = len(current_entries) - len(kept_entries)
    return {
        "ok": True,
        "active_slot": active_slot,
        "stats": {
            **preview["stats"],
            "removed_managed_count": removed_count,
            "saved_worldbook_count": len(saved_store.get("entries", [])),
        },
        "items": saved_store.get("entries", []),
        "settings": saved_store.get("settings", {}),
        "entries": preview["entries"],
    }
