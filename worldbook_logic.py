import re
import unicodedata
from typing import Any

DEFAULT_WORLDBOOK_SETTINGS = {
    "enabled": True,
    "debug_enabled": False,
    "max_hits": 3,
    "default_case_sensitive": False,
    "default_whole_word": False,
    "default_match_mode": "any",
    "default_secondary_mode": "all",
}


def default_worldbook_store() -> dict[str, Any]:
    return {"settings": dict(DEFAULT_WORLDBOOK_SETTINGS), "entries": []}


def sanitize_worldbook_settings(raw: Any) -> dict[str, Any]:
    settings = dict(DEFAULT_WORLDBOOK_SETTINGS)
    if not isinstance(raw, dict):
        return settings

    settings["enabled"] = bool(raw.get("enabled", settings["enabled"]))
    settings["debug_enabled"] = bool(raw.get("debug_enabled", settings["debug_enabled"]))
    try:
        settings["max_hits"] = max(1, min(20, int(raw.get("max_hits", settings["max_hits"]))))
    except (TypeError, ValueError):
        settings["max_hits"] = DEFAULT_WORLDBOOK_SETTINGS["max_hits"]

    settings["default_case_sensitive"] = bool(raw.get("default_case_sensitive", settings["default_case_sensitive"]))
    settings["default_whole_word"] = bool(raw.get("default_whole_word", settings["default_whole_word"]))

    default_match_mode = str(raw.get("default_match_mode", settings["default_match_mode"])).strip().lower()
    settings["default_match_mode"] = default_match_mode if default_match_mode in {"any", "all"} else "any"

    default_secondary_mode = str(raw.get("default_secondary_mode", settings["default_secondary_mode"])).strip().lower()
    settings["default_secondary_mode"] = default_secondary_mode if default_secondary_mode in {"any", "all"} else "all"
    return settings


def sanitize_worldbook_entry(raw: Any, *, index: int, settings: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None

    trigger = str(raw.get("trigger", "")).strip()
    content = str(raw.get("content", "")).strip()
    if not trigger or not content:
        return None

    title = str(raw.get("title", "")).strip() or f"词条 {index}"
    secondary_trigger = str(raw.get("secondary_trigger", "")).strip()
    comment = str(raw.get("comment", "")).strip()
    entry_id = str(raw.get("id", "")).strip() or f"worldbook-{index}"

    match_mode = str(raw.get("match_mode", settings["default_match_mode"])).strip().lower()
    if match_mode not in {"any", "all"}:
        match_mode = settings["default_match_mode"]

    secondary_mode = str(raw.get("secondary_mode", settings["default_secondary_mode"])).strip().lower()
    if secondary_mode not in {"any", "all"}:
        secondary_mode = settings["default_secondary_mode"]

    try:
        priority = int(raw.get("priority", 100))
    except (TypeError, ValueError):
        priority = 100

    return {
        "id": entry_id,
        "title": title[:80],
        "trigger": trigger,
        "secondary_trigger": secondary_trigger,
        "content": content,
        "enabled": bool(raw.get("enabled", True)),
        "priority": max(0, min(9999, priority)),
        "case_sensitive": bool(raw.get("case_sensitive", settings["default_case_sensitive"])),
        "whole_word": bool(raw.get("whole_word", settings["default_whole_word"])),
        "match_mode": match_mode,
        "secondary_mode": secondary_mode,
        "comment": comment[:240],
    }


def sanitize_worldbook_store(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict) and ("settings" in raw or "entries" in raw):
        settings = sanitize_worldbook_settings(raw.get("settings", {}))
        raw_entries = raw.get("entries", [])
    elif isinstance(raw, dict):
        settings = sanitize_worldbook_settings({})
        raw_entries = [{"trigger": key, "content": value} for key, value in raw.items()]
    elif isinstance(raw, list):
        settings = sanitize_worldbook_settings({})
        raw_entries = raw
    else:
        return default_worldbook_store()

    entries: list[dict[str, Any]] = []
    if isinstance(raw_entries, list):
        for index, item in enumerate(raw_entries, start=1):
            cleaned = sanitize_worldbook_entry(item, index=index, settings=settings)
            if cleaned:
                entries.append(cleaned)

    return {"settings": settings, "entries": entries}


def sanitize_worldbook(raw: Any) -> dict[str, str]:
    store = sanitize_worldbook_store(raw)
    cleaned: dict[str, str] = {}
    for item in store["entries"]:
        if item.get("enabled", True):
            cleaned[str(item["trigger"]).strip()] = str(item["content"]).strip()
    return cleaned


def normalize_match_text(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = text.strip().lower()
    return re.sub(r"\s+", "", text)


def split_trigger_aliases(trigger: Any) -> list[str]:
    text = unicodedata.normalize("NFKC", str(trigger or ""))
    aliases = [part.strip() for part in re.split(r"[|,，、/\n]+", text) if part.strip()]
    return aliases or ([text.strip()] if text.strip() else [])


def keyword_matches_query(query_text: str, keyword: str, *, case_sensitive: bool, whole_word: bool) -> bool:
    query = unicodedata.normalize("NFKC", str(query_text or ""))
    target = unicodedata.normalize("NFKC", str(keyword or "")).strip()
    if not query or not target:
        return False

    if not case_sensitive:
        query = query.lower()
        target = target.lower()

    if not whole_word:
        return target in query

    if re.search(r"[\u4e00-\u9fff]", target):
        return target in query

    return bool(re.search(rf"(?<![0-9A-Za-z_]){re.escape(target)}(?![0-9A-Za-z_])", query))
