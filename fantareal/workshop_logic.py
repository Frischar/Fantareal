from typing import Any

DEFAULT_WORKSHOP_STAGE_LIMITS = {"aMax": 2, "bMax": 5}


def _parse_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if value is None:
        return default
    return bool(value)


def _clamp_int(value: Any, minimum: int, maximum: int, default: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return min(max(number, minimum), maximum)


def _clamp_float(value: Any, minimum: float, maximum: float, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return min(max(number, minimum), maximum)


WORKSHOP_OPENING_ANIMATIONS = {"fade", "push", "black", "dream", "curtain", "still"}


def normalize_workshop_opening_animation(value: Any) -> str:
    animation = str(value or "fade").strip().lower()
    return animation if animation in WORKSHOP_OPENING_ANIMATIONS else "fade"


def default_workshop_opening() -> dict[str, Any]:
    return {
        "enabled": False,
        "title": "",
        "subtitle": "",
        "coverImage": "",
        "musicUrl": "",
        "buttonText": "进入故事",
        "volume": 0.65,
        "animation": "fade",
    }


def default_creative_workshop() -> dict[str, Any]:
    return {
        "enabled": True,
        "opening": default_workshop_opening(),
        "items": [
            {
                "id": "workshop_stage_a",
                "name": "A阶段规则",
                "enabled": True,
                "triggerMode": "stage",
                "triggerStage": "A",
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
            }
        ],
    }


def normalize_workshop_stage(value: Any) -> str:
    stage = str(value or "A").strip().upper()
    return stage if stage in {"A", "B", "C"} else "A"


def normalize_workshop_trigger_mode(value: Any) -> str:
    mode = str(value or "stage").strip().lower()
    return "temp" if mode == "temp" else "stage"


def normalize_workshop_action_type(value: Any) -> str:
    action_type = str(value or "music").strip().lower()
    return "image" if action_type == "image" else "music"


def sanitize_workshop_opening(raw: Any) -> dict[str, Any]:
    base = default_workshop_opening()
    if not isinstance(raw, dict):
        return base

    button_text = str(raw.get("buttonText", "") or "").strip()[:24]
    base.update(
        {
            "enabled": _parse_bool(raw.get("enabled"), False),
            "title": str(raw.get("title", "") or "").strip()[:80],
            "subtitle": str(raw.get("subtitle", "") or "").strip()[:160],
            "coverImage": str(raw.get("coverImage", "") or raw.get("coverUrl", "") or "").strip(),
            "musicUrl": str(raw.get("musicUrl", "") or "").strip(),
            "buttonText": button_text or "进入故事",
            "volume": _clamp_float(raw.get("volume"), 0.0, 1.0, 0.65),
            "animation": normalize_workshop_opening_animation(raw.get("animation")),
        }
    )
    return base


def sanitize_creative_workshop_item(raw: Any, *, index: int) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    return {
        "id": str(raw.get("id", "")).strip() or f"workshop-item-{index}",
        "name": str(raw.get("name", "")).strip()[:64] or f"规则 {index}",
        "enabled": _parse_bool(raw.get("enabled"), True),
        "triggerMode": normalize_workshop_trigger_mode(raw.get("triggerMode")),
        "triggerStage": normalize_workshop_stage(raw.get("triggerStage")),
        "triggerTempMin": _clamp_int(raw.get("triggerTempMin"), 0, 9999, 0),
        "triggerTempMax": _clamp_int(raw.get("triggerTempMax"), 0, 9999, 0),
        "actionType": normalize_workshop_action_type(raw.get("actionType")),
        "popupTitle": str(raw.get("popupTitle", "")).strip()[:80],
        "musicPreset": str(raw.get("musicPreset", "off")).strip() or "off",
        "musicUrl": str(raw.get("musicUrl", "")).strip(),
        "autoplay": _parse_bool(raw.get("autoplay"), True),
        "loop": _parse_bool(raw.get("loop"), True),
        "volume": _clamp_float(raw.get("volume"), 0.0, 1.0, 0.85),
        "imageUrl": str(raw.get("imageUrl", "")).strip(),
        "imageAlt": str(raw.get("imageAlt", "")).strip()[:120],
        "note": str(raw.get("note", "")).strip()[:2000],
    }


def sanitize_creative_workshop(raw: Any) -> dict[str, Any]:
    base = default_creative_workshop()
    if not isinstance(raw, dict):
        return base

    items: list[dict[str, Any]] = []
    raw_items = raw.get("items", [])
    if isinstance(raw_items, list):
        for index, item in enumerate(raw_items, start=1):
            cleaned = sanitize_creative_workshop_item(item, index=index)
            if cleaned:
                items.append(cleaned)

    stage_items: dict[str, dict[str, Any]] = {}
    extras: list[dict[str, Any]] = []
    for item in items:
        mode = normalize_workshop_trigger_mode(item.get("triggerMode"))
        item["triggerMode"] = mode
        stage = normalize_workshop_stage(item.get("triggerStage"))
        item["triggerStage"] = stage
        item["triggerTempMin"] = _clamp_int(item.get("triggerTempMin"), 0, 9999, 0)
        item["triggerTempMax"] = _clamp_int(item.get("triggerTempMax"), 0, 9999, item["triggerTempMin"])
        if item["triggerTempMax"] < item["triggerTempMin"]:
            item["triggerTempMin"], item["triggerTempMax"] = item["triggerTempMax"], item["triggerTempMin"]
        if mode == "stage" and stage in {"A", "B", "C"} and stage not in stage_items:
            stage_items[stage] = item
        else:
            extras.append(item)

    normalized_items = []
    template_item = default_creative_workshop()["items"][0]
    for stage in ("A", "B", "C"):
        existing = stage_items.get(stage)
        if existing:
            normalized_items.append(existing)
            continue
        normalized_items.append(
            {
                **template_item,
                "id": f"workshop_stage_{stage.lower()}",
                "name": f"{stage}阶段规则",
                "enabled": False,
                "triggerMode": "stage",
                "triggerStage": stage,
                "triggerTempMin": 0,
                "triggerTempMax": 0,
            }
        )

    base["enabled"] = _parse_bool(raw.get("enabled"), True)
    base["opening"] = sanitize_workshop_opening(raw.get("opening", {}))
    base["items"] = normalized_items + extras
    return base


def workshop_effective_fields(item: dict[str, Any]) -> dict[str, Any]:
    action_type = normalize_workshop_action_type(item.get("actionType"))
    payload: dict[str, Any] = {
        "id": str(item.get("id", "")).strip(),
        "enabled": bool(item.get("enabled", False)),
        "triggerMode": normalize_workshop_trigger_mode(item.get("triggerMode")),
        "triggerStage": normalize_workshop_stage(item.get("triggerStage")),
        "triggerTempMin": _clamp_int(item.get("triggerTempMin"), 0, 9999, 0),
        "triggerTempMax": _clamp_int(item.get("triggerTempMax"), 0, 9999, 0),
        "actionType": action_type,
        "note": str(item.get("note", "")).strip(),
    }
    if action_type == "image":
        payload.update(
            {
                "popupTitle": str(item.get("popupTitle", "")).strip(),
                "imageUrl": str(item.get("imageUrl", "")).strip(),
                "imageAlt": str(item.get("imageAlt", "")).strip(),
            }
        )
    else:
        payload.update(
            {
                "musicPreset": str(item.get("musicPreset", "off")).strip() or "off",
                "musicUrl": str(item.get("musicUrl", "")).strip(),
                "autoplay": _parse_bool(item.get("autoplay"), True),
                "loop": _parse_bool(item.get("loop"), True),
                "volume": _clamp_float(item.get("volume"), 0.0, 1.0, 0.85),
            }
        )
    return payload


def default_workshop_state() -> dict[str, Any]:
    return {"temp": 0, "last_signature": "", "pending_temp": -1, "trigger_history": []}


def sanitize_workshop_state(raw: Any) -> dict[str, Any]:
    base = default_workshop_state()
    if not isinstance(raw, dict):
        return base
    base["temp"] = _clamp_int(raw.get("temp"), 0, 9999, 0)
    base["last_signature"] = str(raw.get("last_signature", "")).strip()
    base["pending_temp"] = _clamp_int(raw.get("pending_temp"), -1, 9999, -1)
    history = raw.get("trigger_history", [])
    if isinstance(history, list):
        normalized_history: list[str] = []
        for item in history:
            token = str(item or "").strip()
            if token and token not in normalized_history:
                normalized_history.append(token)
        base["trigger_history"] = normalized_history[-128:]
    return base


def get_workshop_stage(temp: Any, stage_limits: dict[str, int] | None = None) -> str:
    limits = stage_limits or DEFAULT_WORKSHOP_STAGE_LIMITS
    count = _clamp_int(temp, 0, 9999, 0)
    if count <= limits["aMax"]:
        return "A"
    if count <= limits["bMax"]:
        return "B"
    return "C"


def get_workshop_stage_label(stage: str) -> str:
    normalized_stage = normalize_workshop_stage(stage)
    return f"{normalized_stage}阶段"


def workshop_rule_matches_trigger(item: dict[str, Any], *, temp: int, stage: str) -> bool:
    mode = normalize_workshop_trigger_mode(item.get("triggerMode"))
    if mode == "temp":
        minimum = _clamp_int(item.get("triggerTempMin"), 0, 9999, 0)
        maximum = _clamp_int(item.get("triggerTempMax"), 0, 9999, minimum)
        if maximum < minimum:
            minimum, maximum = maximum, minimum
        return minimum <= temp <= maximum
    return normalize_workshop_stage(item.get("triggerStage")) == normalize_workshop_stage(stage)


def build_workshop_trigger_token(item: dict[str, Any], *, temp: int, stage: str) -> str:
    mode = normalize_workshop_trigger_mode(item.get("triggerMode"))
    item_id = str(item.get("id", "")).strip() or "workshop-item"
    if mode == "temp":
        minimum = _clamp_int(item.get("triggerTempMin"), 0, 9999, 0)
        maximum = _clamp_int(item.get("triggerTempMax"), 0, 9999, minimum)
        if maximum < minimum:
            minimum, maximum = maximum, minimum
        if minimum == maximum:
            return f"temp:{item_id}:{minimum}"
        return f"temp:{item_id}:{temp}:{minimum}-{maximum}"
    return f"stage:{item_id}:{normalize_workshop_stage(stage)}"


def get_workshop_trigger_label(item: dict[str, Any], *, temp: int, stage: str) -> str:
    mode = normalize_workshop_trigger_mode(item.get("triggerMode"))
    if mode == "temp":
        minimum = _clamp_int(item.get("triggerTempMin"), 0, 9999, 0)
        maximum = _clamp_int(item.get("triggerTempMax"), 0, 9999, minimum)
        if maximum < minimum:
            minimum, maximum = maximum, minimum
        if minimum == maximum:
            return f"Temp {minimum}"
        return f"Temp {minimum}-{maximum}"
    return get_workshop_stage_label(stage)


def select_workshop_match(workshop: dict[str, Any], *, temp: int, stage: str) -> dict[str, Any] | None:
    candidates = [
        item
        for item in workshop.get("items", [])
        if isinstance(item, dict)
        and item.get("enabled", True)
        and workshop_rule_matches_trigger(item, temp=temp, stage=stage)
    ]
    if not candidates:
        return None

    def sort_key(item: dict[str, Any]) -> tuple[int, int]:
        mode_priority = 0 if normalize_workshop_trigger_mode(item.get("triggerMode")) == "temp" else 1
        core_priority = 1 if str(item.get("id", "")).startswith("workshop_stage_") else 0
        return (mode_priority, core_priority)

    return sorted(candidates, key=sort_key)[0]
