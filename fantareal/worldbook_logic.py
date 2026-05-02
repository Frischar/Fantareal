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
    "default_entry_type": "keyword",         # keyword / constant
    "default_group_operator": "and",         # and / or
    "default_chance": 100,                   # 0 ~ 100
    "default_sticky_turns": 0,               # >= 0
    "default_cooldown_turns": 0,             # >= 0

    # 节点版世界书注入默认值
    "default_insertion_position": "after_char_defs",  # before_char_defs / after_char_defs / in_chat
    "default_injection_depth": 0,                     # 仅 in_chat 时使用
    "default_injection_role": "system",               # 当前节点只真正支持 system
    "default_injection_order": 100,                   # 同位置内的二次排序

    # RP 分层：默认保持旧逻辑，不主动改变老词条位置
    "default_prompt_layer": "follow_position",       # follow_position / stable / current_state / dynamic / output_guard

    # 递归 V1
    "recursive_scan_enabled": False,
    "recursion_max_depth": 2,
}


def default_worldbook_store() -> dict[str, Any]:
    return {"settings": dict(DEFAULT_WORLDBOOK_SETTINGS), "entries": []}


def _clamp_int(value: Any, minimum: int, maximum: int, default: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return min(max(number, minimum), maximum)


def _normalize_yes_no_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"1", "true", "yes", "on"}:
            return True
        if text in {"0", "false", "no", "off"}:
            return False
    return bool(value)


def _normalize_match_mode(value: Any, default: str) -> str:
    text = str(value or "").strip().lower()
    return text if text in {"any", "all"} else default


def _normalize_entry_type(value: Any, default: str = "keyword") -> str:
    text = str(value or "").strip().lower()
    return text if text in {"keyword", "constant"} else default


def _normalize_group_operator(value: Any, default: str = "and") -> str:
    text = str(value or "").strip().lower()
    if text in {"and", "all"}:
        return "and"
    if text in {"or", "any"}:
        return "or"
    return default


def _normalize_insertion_position(value: Any, default: str = "after_char_defs") -> str:
    text = str(value or "").strip().lower()
    return text if text in {"before_char_defs", "after_char_defs", "in_chat"} else default


def _normalize_injection_role(value: Any, default: str = "system") -> str:
    text = str(value or "").strip().lower()
    if text in {"system", "user", "assistant"}:
        return text
    return default


def _normalize_injection_depth(value: Any, default: int = 0) -> int:
    return _clamp_int(value, 0, 3, default)


def _normalize_injection_order(value: Any, default: int = 100) -> int:
    return _clamp_int(value, 0, 999999, default)


def _normalize_prompt_layer(value: Any, default: str = "follow_position") -> str:
    text = str(value or "").strip().lower()
    return text if text in {"follow_position", "stable", "current_state", "dynamic", "output_guard"} else default


def _normalize_recursion_depth(value: Any, default: int = 2) -> int:
    return _clamp_int(value, 0, 5, default)


def sanitize_worldbook_settings(raw: Any) -> dict[str, Any]:
    settings = dict(DEFAULT_WORLDBOOK_SETTINGS)
    if not isinstance(raw, dict):
        return settings

    settings["enabled"] = _normalize_yes_no_bool(raw.get("enabled"), settings["enabled"])
    settings["debug_enabled"] = _normalize_yes_no_bool(raw.get("debug_enabled"), settings["debug_enabled"])
    settings["max_hits"] = _clamp_int(raw.get("max_hits"), 1, 20, DEFAULT_WORLDBOOK_SETTINGS["max_hits"])

    settings["default_case_sensitive"] = _normalize_yes_no_bool(
        raw.get("default_case_sensitive"),
        settings["default_case_sensitive"],
    )
    settings["default_whole_word"] = _normalize_yes_no_bool(
        raw.get("default_whole_word"),
        settings["default_whole_word"],
    )

    settings["default_match_mode"] = _normalize_match_mode(
        raw.get("default_match_mode"),
        settings["default_match_mode"],
    )
    settings["default_secondary_mode"] = _normalize_match_mode(
        raw.get("default_secondary_mode"),
        settings["default_secondary_mode"],
    )

    settings["default_entry_type"] = _normalize_entry_type(
        raw.get("default_entry_type"),
        settings["default_entry_type"],
    )
    settings["default_group_operator"] = _normalize_group_operator(
        raw.get("default_group_operator"),
        settings["default_group_operator"],
    )
    settings["default_chance"] = _clamp_int(
        raw.get("default_chance"),
        0,
        100,
        DEFAULT_WORLDBOOK_SETTINGS["default_chance"],
    )
    settings["default_sticky_turns"] = _clamp_int(
        raw.get("default_sticky_turns"),
        0,
        999,
        DEFAULT_WORLDBOOK_SETTINGS["default_sticky_turns"],
    )
    settings["default_cooldown_turns"] = _clamp_int(
        raw.get("default_cooldown_turns"),
        0,
        999,
        DEFAULT_WORLDBOOK_SETTINGS["default_cooldown_turns"],
    )
    settings["default_insertion_position"] = _normalize_insertion_position(
        raw.get("default_insertion_position"),
        settings["default_insertion_position"],
    )
    settings["default_injection_depth"] = _normalize_injection_depth(
        raw.get("default_injection_depth"),
        settings["default_injection_depth"],
    )
    settings["default_injection_role"] = _normalize_injection_role(
        raw.get("default_injection_role"),
        settings["default_injection_role"],
    )
    settings["default_injection_order"] = _normalize_injection_order(
        raw.get("default_injection_order"),
        settings["default_injection_order"],
    )
    settings["default_prompt_layer"] = _normalize_prompt_layer(
        raw.get("default_prompt_layer"),
        settings["default_prompt_layer"],
    )
    settings["recursive_scan_enabled"] = _normalize_yes_no_bool(
        raw.get("recursive_scan_enabled"),
        settings["recursive_scan_enabled"],
    )
    settings["recursion_max_depth"] = _normalize_recursion_depth(
        raw.get("recursion_max_depth"),
        settings["recursion_max_depth"],
    )
    return settings


def sanitize_worldbook_entry(raw: Any, *, index: int, settings: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None

    content = str(raw.get("content", "")).strip()
    if not content:
        return None

    entry_type = _normalize_entry_type(
        raw.get("entry_type"),
        str(settings.get("default_entry_type", "keyword")),
    )

    trigger = str(raw.get("trigger", "")).strip()
    secondary_trigger = str(raw.get("secondary_trigger", "")).strip()

    if entry_type == "keyword" and not trigger:
        return None

    title = str(raw.get("title", "")).strip() or f"词条 {index}"
    comment = str(raw.get("comment", "")).strip()
    entry_id = str(raw.get("id", "")).strip() or f"worldbook-{index}"

    match_mode = _normalize_match_mode(
        raw.get("match_mode"),
        str(settings.get("default_match_mode", "any")),
    )
    secondary_mode = _normalize_match_mode(
        raw.get("secondary_mode"),
        str(settings.get("default_secondary_mode", "all")),
    )

    group_operator = _normalize_group_operator(
        raw.get("group_operator"),
        str(settings.get("default_group_operator", "and")),
    )

    group = str(raw.get("group", raw.get("group_name", ""))).strip()

    chance = _clamp_int(
        raw.get("chance"),
        0,
        100,
        int(settings.get("default_chance", 100)),
    )
    sticky_turns = _clamp_int(
        raw.get("sticky_turns"),
        0,
        999,
        int(settings.get("default_sticky_turns", 0)),
    )
    cooldown_turns = _clamp_int(
        raw.get("cooldown_turns"),
        0,
        999,
        int(settings.get("default_cooldown_turns", 0)),
    )

    raw_order = raw.get("order", raw.get("priority", 100))
    order = _clamp_int(raw_order, 0, 999999, 100)

    insertion_position = _normalize_insertion_position(
        raw.get("insertion_position"),
        str(settings.get("default_insertion_position", "after_char_defs")),
    )
    injection_depth = _normalize_injection_depth(
        raw.get("injection_depth"),
        int(settings.get("default_injection_depth", 0)),
    )
    injection_role = _normalize_injection_role(
        raw.get("injection_role"),
        str(settings.get("default_injection_role", "system")),
    )
    injection_order = _normalize_injection_order(
        raw.get("injection_order", raw_order),
        int(settings.get("default_injection_order", 100)),
    )
    prompt_layer = _normalize_prompt_layer(
        raw.get("prompt_layer"),
        str(settings.get("default_prompt_layer", "follow_position")),
    )

    recursive_enabled = _normalize_yes_no_bool(raw.get("recursive_enabled"), True)
    prevent_further_recursion = _normalize_yes_no_bool(raw.get("prevent_further_recursion"), False)

    enabled = _normalize_yes_no_bool(raw.get("enabled"), True)
    case_sensitive = _normalize_yes_no_bool(
        raw.get("case_sensitive"),
        bool(settings.get("default_case_sensitive", False)),
    )
    whole_word = _normalize_yes_no_bool(
        raw.get("whole_word"),
        bool(settings.get("default_whole_word", False)),
    )

    return {
        "id": entry_id,
        "title": title[:80],
        "trigger": trigger,
        "secondary_trigger": secondary_trigger,
        "entry_type": entry_type,
        "group_operator": group_operator,
        "match_mode": match_mode,
        "secondary_mode": secondary_mode,
        "content": content,
        "group": group[:80],
        "chance": chance,
        "sticky_turns": sticky_turns,
        "cooldown_turns": cooldown_turns,
        "order": order,
        "priority": order,
        "insertion_position": insertion_position,
        "injection_depth": injection_depth,
        "injection_role": injection_role,
        "injection_order": injection_order,
        "prompt_layer": prompt_layer,
        "recursive_enabled": recursive_enabled,
        "prevent_further_recursion": prevent_further_recursion,
        "enabled": enabled,
        "case_sensitive": case_sensitive,
        "whole_word": whole_word,
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
        trigger = str(item.get("trigger", "")).strip()
        content = str(item.get("content", "")).strip()
        if item.get("enabled", True) and trigger and content:
            cleaned[trigger] = content
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
