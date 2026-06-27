from __future__ import annotations

import re
import unicodedata
from typing import Any


_MACRO_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*(?::[A-Za-z0-9_\-]+(?:\.[A-Za-z0-9_\-]+)*)?(?:\.[A-Za-z0-9_\-]+)?)\s*\}\}|<\s*(user|user_name|char|char_name|cast|protagonists)\s*>")

_ALIASES = {
    "user": "user_name",
    "user_name": "user_name",
    "char": "char_name",
    "char_name": "char_name",
}


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_role_id(value: Any, fallback: str = "") -> str:
    text = unicodedata.normalize("NFKC", str(value or fallback or "")).strip().lower()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^a-z0-9_\-]+", "", text)
    text = re.sub(r"[_\-]{2,}", "_", text).strip("_-")
    return text or fallback


def _split_aliases(value: Any) -> list[str]:
    if isinstance(value, list):
        raw_items = value
    elif isinstance(value, tuple):
        raw_items = list(value)
    else:
        raw_items = re.split(r"[\n,，、;；|]+", str(value or ""))
    aliases: list[str] = []
    for item in raw_items:
        text = _clean_text(item)
        if text and text not in aliases:
            aliases.append(text[:80])
    return aliases[:24]


def _format_macro_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return _clean_text(value)


def _role_from_persona(persona: dict[str, Any], *, fallback_id: str) -> dict[str, Any] | None:
    name = _clean_text(persona.get("name"))
    if not name:
        return None
    role_id = _normalize_role_id(persona.get("role_id") or persona.get("id"), fallback_id)
    aliases = [item for item in _split_aliases(persona.get("aliases")) if item != name]
    return {"role_id": role_id, "name": name, "aliases": aliases}


def _roles_from_card(role_card: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(role_card, dict):
        return []
    raw = role_card.get("raw") if isinstance(role_card.get("raw"), dict) else role_card
    roles: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    personas = raw.get("personas")
    if isinstance(personas, dict):
        persona_items = list(personas.items())
    elif isinstance(personas, list):
        persona_items = [(str(index), item) for index, item in enumerate(personas, start=1)]
    else:
        persona_items = []

    for index, (key, value) in enumerate(persona_items, start=1):
        if not isinstance(value, dict):
            continue
        fallback_id = _normalize_role_id(f"current_card_{key}_{value.get('name')}", f"current_card_role_{index}")
        role = _role_from_persona(value, fallback_id=fallback_id)
        if not role or role["role_id"] in seen_ids:
            continue
        seen_ids.add(role["role_id"])
        roles.append(role)

    if roles:
        return roles

    main_role = _role_from_persona(raw, fallback_id=_normalize_role_id(raw.get("name"), "main_card"))
    return [main_role] if main_role else []


def _format_cast(roles: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for role in roles:
        name = _clean_text(role.get("name"))
        role_id = _clean_text(role.get("role_id"))
        aliases = _split_aliases(role.get("aliases"))
        if not name:
            continue
        alias_text = f"；别名：{'、'.join(aliases)}" if aliases else ""
        id_text = f"role_id: {role_id}" if role_id else "role_id: unknown"
        lines.append(f"- {name}（{id_text}{alias_text}）")
    return "\n".join(lines)


def build_macro_context(
    *,
    persona: dict[str, Any] | None = None,
    user_profile: dict[str, Any] | None = None,
    role_card: dict[str, Any] | None = None,
    state_journal_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build macro variable context from stable user, character, and cast data."""
    profile = user_profile if isinstance(user_profile, dict) else {}
    character = persona if isinstance(persona, dict) else {}

    user_name = (
        _clean_text(profile.get("display_name"))
        or _clean_text(profile.get("nickname"))
        or _clean_text(profile.get("name"))
    )
    char_name = (
        _clean_text(character.get("name"))
        or _clean_text(character.get("card_name"))
    )

    context: dict[str, Any] = {}
    if user_name:
        context["user_name"] = user_name
    if char_name:
        context["char_name"] = char_name
    roles = _roles_from_card(role_card)
    if roles:
        context["roles"] = roles
        context["role_map"] = {str(role.get("role_id")): role for role in roles if role.get("role_id")}
        context["cast"] = _format_cast(roles)
    if isinstance(state_journal_context, dict):
        context["state_journal"] = state_journal_context
    return context


def render_macro_variables(text: Any, context: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
    """Render macro variables in a single text block.

    Unknown variables are preserved verbatim and reported in debug metadata.
    """
    raw = str(text or "")
    values = context if isinstance(context, dict) else {}
    used: set[str] = set()
    unresolved: set[str] = set()
    replacement_details: list[dict[str, Any]] = []
    unresolved_details: list[dict[str, Any]] = []
    replacements = 0

    def mark_unresolved(raw_key: str, raw_macro: str, reason: str) -> str:
        unresolved.add(raw_key)
        unresolved_details.append({"key": raw_key, "raw": raw_macro, "reason": reason})
        return raw_macro

    def mark_resolved(raw_key: str, raw_macro: str, value: Any, source: str) -> str:
        nonlocal replacements
        rendered_value = _format_macro_value(value)
        if not rendered_value:
            return mark_unresolved(raw_key, raw_macro, "value_empty")
        used.add(raw_key)
        replacements += 1
        replacement_details.append(
            {
                "key": raw_key,
                "raw": raw_macro,
                "rendered": rendered_value,
                "source": source,
            }
        )
        return rendered_value

    def resolve_story_time(raw_key: str, raw_macro: str) -> str | None:
        if raw_key != "story_time" and not raw_key.startswith("story_time."):
            return None
        state = values.get("state_journal") if isinstance(values.get("state_journal"), dict) else {}
        story_time = state.get("story_time") if isinstance(state.get("story_time"), dict) else {}
        if not story_time:
            return mark_unresolved(raw_key, raw_macro, "story_time_missing")
        field = raw_key.partition(".")[2]
        if not field:
            value = story_time.get("display") or story_time.get("current")
        elif field == "current":
            value = story_time.get("current")
        else:
            value = story_time.get(field)
        return mark_resolved(raw_key, raw_macro, value, "story_time")

    def resolve_stage(raw_key: str, raw_macro: str) -> str | None:
        if not raw_key.startswith("stage:"):
            return None
        state = values.get("state_journal") if isinstance(values.get("state_journal"), dict) else {}
        stage_map = state.get("stage_map") if isinstance(state.get("stage_map"), dict) else {}
        role_expr = raw_key[6:].strip()
        role_id, _, field = role_expr.partition(".")
        role_id = _normalize_role_id(role_id)
        stage = stage_map.get(role_id)
        if not isinstance(stage, dict):
            return mark_unresolved(raw_key, raw_macro, "stage_missing")
        if not field:
            value = stage.get("stage_name")
        elif field == "key":
            value = stage.get("stage_key")
        elif field == "tag":
            value = stage.get("activation_tag") or stage.get("tag")
        else:
            return mark_unresolved(raw_key, raw_macro, "stage_field_unknown")
        return mark_resolved(raw_key, raw_macro, value, "state_journal.stage")

    def resolve_state(raw_key: str, raw_macro: str) -> str | None:
        if not raw_key.startswith("state:"):
            return None
        state = values.get("state_journal") if isinstance(values.get("state_journal"), dict) else {}
        state_map = state.get("state_map") if isinstance(state.get("state_map"), dict) else {}
        parts = [part.strip() for part in raw_key[6:].split(".") if part.strip()]
        if len(parts) < 2:
            return mark_unresolved(raw_key, raw_macro, "state_syntax_invalid")
        role_id = _normalize_role_id(parts[0])
        metric_key = _normalize_role_id(parts[1])
        field = parts[2] if len(parts) >= 3 else "value"
        metrics = state_map.get(role_id)
        metric = metrics.get(metric_key) if isinstance(metrics, dict) else None
        if not isinstance(metric, dict):
            return mark_unresolved(raw_key, raw_macro, "state_metric_missing")
        if field in {"value", "current"}:
            value = metric.get("value")
        elif field == "raw":
            value = metric.get("raw")
        elif field == "max":
            value = metric.get("max")
        else:
            return mark_unresolved(raw_key, raw_macro, "state_field_unknown")
        return mark_resolved(raw_key, raw_macro, value, "state_journal.state")

    def resolve_ledger(raw_key: str, raw_macro: str) -> str | None:
        if not raw_key.startswith("ledger:"):
            return None
        state = values.get("state_journal") if isinstance(values.get("state_journal"), dict) else {}
        ledger_map = state.get("ledger_map") if isinstance(state.get("ledger_map"), dict) else {}
        entry_expr = raw_key[7:].strip()
        entry_id, _, field = entry_expr.partition(".")
        entry_id = _normalize_role_id(entry_id)
        entry = ledger_map.get(entry_id)
        if not isinstance(entry, dict):
            return mark_unresolved(raw_key, raw_macro, "ledger_not_available")
        value = entry.get(field or "status")
        return mark_resolved(raw_key, raw_macro, value, "plot_ledger")

    def replace(match: re.Match[str]) -> str:
        raw_key = (match.group(1) or match.group(2) or "").strip()
        raw_macro = match.group(0)
        for resolver in (resolve_story_time, resolve_stage, resolve_state, resolve_ledger):
            resolved = resolver(raw_key, raw_macro)
            if resolved is not None:
                return resolved
        if raw_key == "cast" or raw_key == "protagonists":
            value = _clean_text(values.get("cast"))
            return mark_resolved(raw_key, raw_macro, value, "identity.cast")
        if raw_key.startswith("role:"):
            role_expr = raw_key[5:].strip()
            role_id, _, field = role_expr.partition(".")
            role_id = _normalize_role_id(role_id)
            role_map = values.get("role_map") if isinstance(values.get("role_map"), dict) else {}
            role = role_map.get(role_id)
            if not isinstance(role, dict):
                return mark_unresolved(raw_key, raw_macro, "role_missing")
            aliases = _split_aliases(role.get("aliases"))
            if not field or field == "name":
                value = _clean_text(role.get("name"))
            elif field == "aliases":
                value = "、".join(aliases)
            elif field == "names":
                names = [_clean_text(role.get("name")), *aliases]
                value = "、".join(item for item in names if item)
            else:
                return mark_unresolved(raw_key, raw_macro, "role_field_unknown")
            return mark_resolved(raw_key, raw_macro, value, "identity.role")
        canonical = _ALIASES.get(raw_key)
        if not canonical:
            return mark_unresolved(raw_key, raw_macro, "macro_unknown")
        value = _clean_text(values.get(canonical))
        return mark_resolved(canonical, raw_macro, value, "identity")

    rendered = _MACRO_RE.sub(replace, raw)
    return rendered, {
        "enabled": True,
        "replacements": replacements,
        "used": sorted(used),
        "unresolved": sorted(unresolved),
        "replacement_details": replacement_details,
        "unresolved_details": unresolved_details,
    }


def render_prompt_segments_with_macros(
    segments: list[dict[str, Any]],
    context: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rendered_segments: list[dict[str, Any]] = []
    used: set[str] = set()
    unresolved: set[str] = set()
    touched_segments: list[dict[str, Any]] = []
    replacement_details: list[dict[str, Any]] = []
    unresolved_details: list[dict[str, Any]] = []
    replacements = 0

    for segment in segments:
        next_segment = dict(segment)
        original = str(next_segment.get("content", "") or "")
        if str(next_segment.get("kind", "") or "").strip() == "dialogue":
            rendered_segments.append(next_segment)
            continue
        rendered, debug = render_macro_variables(original, context)
        if rendered != original:
            next_segment["content"] = rendered
            touched_segments.append(
                {
                    "id": str(next_segment.get("id", "") or ""),
                    "source": str(next_segment.get("source", "") or ""),
                    "placement": str(next_segment.get("placement", "") or ""),
                    "replacement_count": int(debug.get("replacements", 0) or 0),
                    "raw": original,
                    "rendered": rendered,
                }
            )
        replacements += int(debug.get("replacements", 0) or 0)
        used.update(str(item) for item in debug.get("used", []) if item)
        unresolved.update(str(item) for item in debug.get("unresolved", []) if item)
        for item in debug.get("replacement_details", []) if isinstance(debug.get("replacement_details"), list) else []:
            if isinstance(item, dict):
                replacement_details.append({**item, "location": str(next_segment.get("id", "") or ""), "source_segment": str(next_segment.get("source", "") or "")})
        for item in debug.get("unresolved_details", []) if isinstance(debug.get("unresolved_details"), list) else []:
            if isinstance(item, dict):
                unresolved_details.append({**item, "location": str(next_segment.get("id", "") or ""), "source_segment": str(next_segment.get("source", "") or "")})
        rendered_segments.append(next_segment)

    return rendered_segments, {
        "enabled": True,
        "resolved": {
            key: value
            for key, value in sorted((context or {}).items())
            if key in {"user_name", "char_name"} and _clean_text(value)
        },
        "roles": [
            {"role_id": role.get("role_id"), "name": role.get("name"), "aliases": role.get("aliases", [])}
            for role in (context or {}).get("roles", [])
            if isinstance(role, dict)
        ],
        "used": sorted(used),
        "unresolved": sorted(unresolved),
        "replacement_count": replacements,
        "replacements": replacement_details,
        "unresolved_details": unresolved_details,
        "segments": touched_segments,
    }


def render_messages_with_macros(
    messages: list[dict[str, Any]],
    context: dict[str, Any] | None = None,
    *,
    skip_roles: set[str] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    skipped = skip_roles or {"user"}
    rendered_messages: list[dict[str, Any]] = []
    used: set[str] = set()
    unresolved: set[str] = set()
    replacement_details: list[dict[str, Any]] = []
    unresolved_details: list[dict[str, Any]] = []
    replacements = 0

    for index, message in enumerate(messages):
        next_message = dict(message)
        role = str(next_message.get("role", "") or "")
        if role in skipped:
            rendered_messages.append(next_message)
            continue
        rendered, debug = render_macro_variables(next_message.get("content", ""), context)
        next_message["content"] = rendered
        replacements += int(debug.get("replacements", 0) or 0)
        used.update(str(item) for item in debug.get("used", []) if item)
        unresolved.update(str(item) for item in debug.get("unresolved", []) if item)
        for item in debug.get("replacement_details", []) if isinstance(debug.get("replacement_details"), list) else []:
            if isinstance(item, dict):
                replacement_details.append({**item, "location": f"message.{index}", "message_role": role})
        for item in debug.get("unresolved_details", []) if isinstance(debug.get("unresolved_details"), list) else []:
            if isinstance(item, dict):
                unresolved_details.append({**item, "location": f"message.{index}", "message_role": role})
        rendered_messages.append(next_message)

    return rendered_messages, {
        "replacements": replacements,
        "used": sorted(used),
        "unresolved": sorted(unresolved),
        "replacement_details": replacement_details,
        "unresolved_details": unresolved_details,
    }


def build_macro_catalog(context: dict[str, Any] | None = None) -> dict[str, Any]:
    values = context if isinstance(context, dict) else {}
    state = values.get("state_journal") if isinstance(values.get("state_journal"), dict) else {}
    story_time = state.get("story_time") if isinstance(state.get("story_time"), dict) else {}
    stages = state.get("stages") if isinstance(state.get("stages"), list) else []
    metrics = state.get("metrics") if isinstance(state.get("metrics"), list) else []
    ledger_rows = state.get("ledger") if isinstance(state.get("ledger"), list) else []

    def preview(value: Any, fallback: str = "未解析") -> str:
        text = re.sub(r"\s+", " ", _format_macro_value(value)).strip()
        if not text:
            text = fallback
        return text[:80] + ("..." if len(text) > 80 else "")

    groups: list[dict[str, Any]] = [
        {
            "id": "identity",
            "title": "基础身份",
            "items": [
                {"label": "用户名", "macro": "{{user}}", "preview": preview(values.get("user_name")), "description": "当前用户显示名"},
                {"label": "用户名完整写法", "macro": "{{user_name}}", "preview": preview(values.get("user_name")), "description": "当前用户显示名"},
                {"label": "当前主角色", "macro": "{{char}}", "preview": preview(values.get("char_name")), "description": "当前角色名"},
                {"label": "当前主角色完整写法", "macro": "{{char_name}}", "preview": preview(values.get("char_name")), "description": "当前角色名"},
                {"label": "群像角色列表", "macro": "{{cast}}", "preview": preview(values.get("cast"), "当前卡暂无角色列表"), "description": "当前卡中的角色列表"},
                {"label": "群像角色列表别名", "macro": "{{protagonists}}", "preview": preview(values.get("cast"), "当前卡暂无角色列表"), "description": "与 cast 等价"},
            ],
        }
    ]

    role_items: list[dict[str, Any]] = []
    for role in values.get("roles", []) if isinstance(values.get("roles"), list) else []:
        if not isinstance(role, dict):
            continue
        role_id = _clean_text(role.get("role_id"))
        role_name = _clean_text(role.get("name"))
        if not role_id:
            continue
        role_items.append({"label": f"{role_name or role_id} 名称", "macro": f"{{{{role:{role_id}.name}}}}", "preview": preview(role_name), "description": "指定角色名"})
        role_items.append({"label": f"{role_name or role_id} 别名", "macro": f"{{{{role:{role_id}.aliases}}}}", "preview": preview("、".join(_split_aliases(role.get("aliases"))), "暂无别名"), "description": "指定角色别名"})
        role_items.append({"label": f"{role_name or role_id} 所有称呼", "macro": f"{{{{role:{role_id}.names}}}}", "preview": preview("、".join([role_name, *_split_aliases(role.get("aliases"))]), "暂无别名"), "description": "角色名 + 别名"})
    if role_items:
        groups.append({"id": "roles", "title": "角色称呼", "items": role_items[:36]})

    groups.append(
        {
            "id": "story_time",
            "title": "剧情时间",
            "items": [
                {"label": "当前剧情时间", "macro": "{{story_time}}", "preview": preview(story_time.get("display"), "剧情时间未启用"), "description": "按心笺配置格式输出"},
                {"label": "当前时间原始值", "macro": "{{story_time.current}}", "preview": preview(story_time.get("current"), "剧情时间未启用"), "description": "YYYY-MM-DD HH:mm:ss"},
                {"label": "已经过时间秒数", "macro": "{{story_time.elapsed_seconds}}", "preview": preview(story_time.get("elapsed_seconds"), "0"), "description": "数字文本"},
                {"label": "当前时段", "macro": "{{story_time.time_slot}}", "preview": preview(story_time.get("time_slot"), "剧情时间未启用"), "description": "当前时段"},
                {"label": "当前季节", "macro": "{{story_time.season}}", "preview": preview(story_time.get("season"), "剧情时间未启用"), "description": "当前季节"},
            ],
        }
    )

    stage_items: list[dict[str, Any]] = []
    for row in stages:
        if not isinstance(row, dict):
            continue
        role_id = _clean_text(row.get("role_id"))
        role_name = _clean_text(row.get("role_name")) or role_id
        if not role_id:
            continue
        stage_items.extend(
            [
                {"label": f"{role_name} 当前阶段", "macro": f"{{{{stage:{role_id}}}}}", "preview": preview(row.get("stage_name")), "description": "当前阶段名"},
                {"label": f"{role_name} 阶段 Key", "macro": f"{{{{stage:{role_id}.key}}}}", "preview": preview(row.get("stage_key")), "description": "当前阶段 key"},
                {"label": f"{role_name} 阶段标签", "macro": f"{{{{stage:{role_id}.tag}}}}", "preview": preview(row.get("activation_tag") or row.get("tag")), "description": "active_tag"},
            ]
        )
    groups.append({"id": "stage", "title": "角色阶段", "items": stage_items[:45]})

    state_items: list[dict[str, Any]] = []
    for row in metrics:
        if not isinstance(row, dict):
            continue
        role_id = _clean_text(row.get("role_id"))
        metric_key = _clean_text(row.get("metric_key"))
        role_name = _clean_text(row.get("role_name")) or role_id
        label = _clean_text(row.get("label")) or metric_key
        if not role_id or not metric_key:
            continue
        state_items.append({"label": f"{role_name} · {label}", "macro": f"{{{{state:{role_id}.{metric_key}}}}}", "preview": preview(row.get("value")), "description": "角色变量当前值"})
        state_items.append({"label": f"{role_name} · {label} 上限", "macro": f"{{{{state:{role_id}.{metric_key}.max}}}}", "preview": preview(row.get("max")), "description": "角色变量上限"})
    groups.append({"id": "state", "title": "心笺变量", "items": state_items[:60]})

    ledger_items: list[dict[str, Any]] = []
    for row in ledger_rows:
        if not isinstance(row, dict):
            continue
        entry_id = _normalize_role_id(row.get("safe_entry_id") or row.get("entry_id"), "")
        if not entry_id:
            continue
        title = _clean_text(row.get("title")) or entry_id
        ledger_items.append({"label": f"{title} 状态", "macro": f"{{{{ledger:{entry_id}.status}}}}", "preview": preview(row.get("status"), "暂无状态"), "description": "剧情账本状态"})
        ledger_items.append({"label": f"{title} 摘要", "macro": f"{{{{ledger:{entry_id}.summary}}}}", "preview": preview(row.get("summary"), "暂无摘要"), "description": "剧情账本摘要"})
        if row.get("condition"):
            ledger_items.append({"label": f"{title} 条件", "macro": f"{{{{ledger:{entry_id}.condition}}}}", "preview": preview(row.get("condition")), "description": "剧情账本推进条件"})
        if row.get("evidence"):
            ledger_items.append({"label": f"{title} 依据", "macro": f"{{{{ledger:{entry_id}.evidence}}}}", "preview": preview(row.get("evidence")), "description": "剧情账本判断依据"})
    if not ledger_items:
        ledger_items = [
            {"label": "账本状态", "macro": "{{ledger:<entry_id>.status}}", "preview": "暂无剧情账本条目", "description": "剧情账本状态"},
            {"label": "账本摘要", "macro": "{{ledger:<entry_id>.summary}}", "preview": "暂无剧情账本条目", "description": "剧情账本摘要"},
        ]
    groups.append({"id": "ledger", "title": "剧情账本", "items": ledger_items[:60]})
    return {"groups": groups}


__all__ = [
    "build_macro_context",
    "build_macro_catalog",
    "render_messages_with_macros",
    "render_macro_variables",
    "render_prompt_segments_with_macros",
]
