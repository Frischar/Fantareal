from __future__ import annotations

import re
import unicodedata
from typing import Any


_MACRO_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*(?::[A-Za-z0-9_\-]+(?:\.[A-Za-z_][A-Za-z0-9_]*)?)?)\s*\}\}|<\s*([A-Za-z_][A-Za-z0-9_]*)\s*>")

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
    return context


def render_macro_variables(text: Any, context: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
    """Render macro variables in a single text block.

    Unknown variables are preserved verbatim and reported in debug metadata.
    """
    raw = str(text or "")
    values = context if isinstance(context, dict) else {}
    used: set[str] = set()
    unresolved: set[str] = set()
    replacements = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal replacements
        raw_key = (match.group(1) or match.group(2) or "").strip()
        if raw_key == "cast" or raw_key == "protagonists":
            value = _clean_text(values.get("cast"))
            if not value:
                unresolved.add(raw_key)
                return match.group(0)
            used.add(raw_key)
            replacements += 1
            return value
        if raw_key.startswith("role:"):
            role_expr = raw_key[5:].strip()
            role_id, _, field = role_expr.partition(".")
            role_id = _normalize_role_id(role_id)
            role_map = values.get("role_map") if isinstance(values.get("role_map"), dict) else {}
            role = role_map.get(role_id)
            if not isinstance(role, dict):
                unresolved.add(raw_key)
                return match.group(0)
            aliases = _split_aliases(role.get("aliases"))
            if not field or field == "name":
                value = _clean_text(role.get("name"))
            elif field == "aliases":
                value = "、".join(aliases)
            elif field == "names":
                names = [_clean_text(role.get("name")), *aliases]
                value = "、".join(item for item in names if item)
            else:
                unresolved.add(raw_key)
                return match.group(0)
            if not value:
                unresolved.add(raw_key)
                return match.group(0)
            used.add(raw_key)
            replacements += 1
            return value
        canonical = _ALIASES.get(raw_key)
        if not canonical:
            unresolved.add(raw_key)
            return match.group(0)
        value = _clean_text(values.get(canonical))
        if not value:
            unresolved.add(canonical)
            return match.group(0)
        used.add(canonical)
        replacements += 1
        return value

    rendered = _MACRO_RE.sub(replace, raw)
    return rendered, {
        "enabled": True,
        "replacements": replacements,
        "used": sorted(used),
        "unresolved": sorted(unresolved),
    }


def render_prompt_segments_with_macros(
    segments: list[dict[str, Any]],
    context: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rendered_segments: list[dict[str, Any]] = []
    used: set[str] = set()
    unresolved: set[str] = set()
    touched_segments: list[dict[str, Any]] = []
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
                }
            )
        replacements += int(debug.get("replacements", 0) or 0)
        used.update(str(item) for item in debug.get("used", []) if item)
        unresolved.update(str(item) for item in debug.get("unresolved", []) if item)
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
    replacements = 0

    for message in messages:
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
        rendered_messages.append(next_message)

    return rendered_messages, {
        "replacements": replacements,
        "used": sorted(used),
        "unresolved": sorted(unresolved),
    }


__all__ = [
    "build_macro_context",
    "render_messages_with_macros",
    "render_macro_variables",
    "render_prompt_segments_with_macros",
]
