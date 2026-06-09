from __future__ import annotations

import re
from typing import Any


_MACRO_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}|<\s*([A-Za-z_][A-Za-z0-9_]*)\s*>")

_ALIASES = {
    "user": "user_name",
    "user_name": "user_name",
    "char": "char_name",
    "char_name": "char_name",
}


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def build_macro_context(*, persona: dict[str, Any] | None = None, user_profile: dict[str, Any] | None = None) -> dict[str, str]:
    """Build the small v0.1 macro variable context from stable identity data."""
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

    context: dict[str, str] = {}
    if user_name:
        context["user_name"] = user_name
    if char_name:
        context["char_name"] = char_name
    return context


def render_macro_variables(text: Any, context: dict[str, str] | None = None) -> tuple[str, dict[str, Any]]:
    """Render v0.1 macro variables in a single text block.

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
    context: dict[str, str] | None = None,
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
        "used": sorted(used),
        "unresolved": sorted(unresolved),
        "replacement_count": replacements,
        "segments": touched_segments,
    }


def render_messages_with_macros(
    messages: list[dict[str, Any]],
    context: dict[str, str] | None = None,
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
