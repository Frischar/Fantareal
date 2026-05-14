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


def _safe_text(value: Any, limit: int = 2000) -> str:
    return str(value or "").strip()[:limit]


WORKSHOP_OPENING_ANIMATIONS = {"fade", "push", "black", "dream", "curtain", "still"}
WORKSHOP_OPENING_AFTER_MODES = {"connect_ambience", "continue_opening", "fade_stop"}
WORKSHOP_DYNAMIC_TRIGGER_TYPES = {"round", "progress", "model", "manual"}
WORKSHOP_DYNAMIC_REPEAT_MODES = {"once", "session", "always"}
WORKSHOP_DYNAMIC_CONTENT_TYPES = {"image", "sound", "background"}
WORKSHOP_DYNAMIC_PRESENTATION_MODES = {"light", "standard", "immersive"}


def normalize_workshop_opening_animation(value: Any) -> str:
    animation = str(value or "fade").strip().lower()
    return animation if animation in WORKSHOP_OPENING_ANIMATIONS else "fade"


def normalize_workshop_opening_after_mode(value: Any) -> str:
    mode = str(value or "connect_ambience").strip().lower()
    return mode if mode in WORKSHOP_OPENING_AFTER_MODES else "connect_ambience"


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
        "holdSeconds": 3,
        "afterMode": "connect_ambience",
        "autoPlayMusic": False,
        "fadeInSeconds": 2,
        "fadeOutSeconds": 2,
        "transitionSeconds": 2,
        "typewriterEnabled": False,
        "typewriterSpeed": "normal",
    }


def default_workshop_ambience() -> dict[str, Any]:
    return {
        "enabled": False,
        "name": "默认氛围",
        "startMode": "after_opening",
        "background": {
            "enabled": False,
            "imageUrl": "",
            "overlay": 0.35,
        },
        "music": {
            "enabled": False,
            "preset": "off",
            "url": "",
            "volume": 0.6,
            "loop": True,
        },
        "ambient": {
            "enabled": False,
            "preset": "off",
            "url": "",
            "volume": 0.35,
            "loop": True,
        },
    }


def default_dynamic_scene() -> dict[str, Any]:
    return {
        "id": "",
        "name": "动态演出",
        "enabled": True,
        "trigger": {
            "type": "model",
            "round": 1,
            "progress": 0,
            "event": "",
            "repeat": "once",
        },
        "content": {
            "type": "image",
            "title": "",
            "imageUrl": "",
            "caption": "",
            "soundUrl": "",
            "backgroundUrl": "",
        },
        "presentation": {
            "mode": "standard",
            "duration": 6,
            "autoClose": True,
        },
        "audio": {
            "enabled": False,
            "url": "",
            "volume": 0.5,
            "duckAmbience": True,
        },
        "note": "",
    }


def default_creative_workshop() -> dict[str, Any]:
    return {
        "version": 2,
        "enabled": True,
        "opening": default_workshop_opening(),
        "ambience": default_workshop_ambience(),
        "dynamicScenes": [],
    }


def normalize_workshop_stage(value: Any) -> str:
    stage = str(value or "A").strip().upper()
    return stage if stage in {"A", "B", "C"} else "A"


def normalize_dynamic_trigger_type(value: Any) -> str:
    trigger_type = str(value or "model").strip().lower()
    return trigger_type if trigger_type in WORKSHOP_DYNAMIC_TRIGGER_TYPES else "model"


def normalize_dynamic_repeat_mode(value: Any) -> str:
    repeat = str(value or "once").strip().lower()
    return repeat if repeat in WORKSHOP_DYNAMIC_REPEAT_MODES else "once"


def normalize_dynamic_content_type(value: Any) -> str:
    content_type = str(value or "image").strip().lower()
    return content_type if content_type in WORKSHOP_DYNAMIC_CONTENT_TYPES else "image"


def normalize_dynamic_presentation_mode(value: Any) -> str:
    mode = str(value or "standard").strip().lower()
    return mode if mode in WORKSHOP_DYNAMIC_PRESENTATION_MODES else "standard"


def sanitize_workshop_opening(raw: Any) -> dict[str, Any]:
    base = default_workshop_opening()
    if not isinstance(raw, dict):
        return base

    button_text = str(raw.get("buttonText", "") or "").strip()[:24]
    base.update(
        {
            "enabled": _parse_bool(raw.get("enabled"), False),
            "title": _safe_text(raw.get("title"), 80),
            "subtitle": _safe_text(raw.get("subtitle"), 160),
            "coverImage": str(raw.get("coverImage", "") or raw.get("coverUrl", "") or "").strip(),
            "musicUrl": str(raw.get("musicUrl", "") or "").strip(),
            "buttonText": button_text or "进入故事",
            "volume": _clamp_float(raw.get("volume"), 0.0, 1.0, 0.65),
            "animation": normalize_workshop_opening_animation(raw.get("animation")),
            "holdSeconds": _clamp_float(raw.get("holdSeconds"), 0.0, 20.0, 3.0),
            "afterMode": normalize_workshop_opening_after_mode(raw.get("afterMode")),
            "autoPlayMusic": _parse_bool(raw.get("autoPlayMusic"), False),
            "fadeInSeconds": _clamp_float(raw.get("fadeInSeconds"), 0.0, 8.0, 2.0),
            "fadeOutSeconds": _clamp_float(raw.get("fadeOutSeconds"), 0.0, 8.0, 2.0),
            "transitionSeconds": _clamp_float(raw.get("transitionSeconds"), 0.0, 8.0, 2.0),
            "typewriterEnabled": _parse_bool(raw.get("typewriterEnabled"), False),
            "typewriterSpeed": str(raw.get("typewriterSpeed", "normal") or "normal").strip().lower() if str(raw.get("typewriterSpeed", "normal") or "normal").strip().lower() in {"slow", "normal", "fast"} else "normal",
        }
    )
    return base


def sanitize_workshop_ambience(raw: Any) -> dict[str, Any]:
    base = default_workshop_ambience()
    if not isinstance(raw, dict):
        return base

    background = raw.get("background", {}) if isinstance(raw.get("background"), dict) else {}
    music = raw.get("music", {}) if isinstance(raw.get("music"), dict) else {}
    ambient = raw.get("ambient", {}) if isinstance(raw.get("ambient"), dict) else {}
    start_mode = str(raw.get("startMode", "after_opening") or "after_opening").strip().lower()
    if start_mode not in {"manual", "after_opening"}:
        start_mode = "after_opening"

    base.update(
        {
            "enabled": _parse_bool(raw.get("enabled"), False),
            "name": _safe_text(raw.get("name"), 40) or "默认氛围",
            "startMode": start_mode,
            "background": {
                "enabled": _parse_bool(background.get("enabled"), False),
                "imageUrl": str(background.get("imageUrl", "") or "").strip(),
                "overlay": _clamp_float(background.get("overlay"), 0.0, 0.85, 0.35),
            },
            "music": {
                "enabled": _parse_bool(music.get("enabled"), False),
                "preset": str(music.get("preset", "off") or "off").strip() or "off",
                "url": str(music.get("url", "") or "").strip(),
                "volume": _clamp_float(music.get("volume"), 0.0, 1.0, 0.6),
                "loop": _parse_bool(music.get("loop"), True),
            },
            "ambient": {
                "enabled": _parse_bool(ambient.get("enabled"), False),
                "preset": str(ambient.get("preset", "off") or "off").strip() or "off",
                "url": str(ambient.get("url", "") or "").strip(),
                "volume": _clamp_float(ambient.get("volume"), 0.0, 1.0, 0.35),
                "loop": _parse_bool(ambient.get("loop"), True),
            },
        }
    )
    return base


def sanitize_dynamic_scene(raw: Any, *, index: int) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    base = default_dynamic_scene()
    trigger = raw.get("trigger", {}) if isinstance(raw.get("trigger"), dict) else {}
    content = raw.get("content", {}) if isinstance(raw.get("content"), dict) else {}
    presentation = raw.get("presentation", {}) if isinstance(raw.get("presentation"), dict) else {}
    audio = raw.get("audio", {}) if isinstance(raw.get("audio"), dict) else {}
    scene_id = _safe_text(raw.get("id"), 64) or f"dynamic_scene_{index}"
    base.update(
        {
            "id": scene_id,
            "name": _safe_text(raw.get("name"), 64) or f"动态演出 {index}",
            "enabled": _parse_bool(raw.get("enabled"), True),
            "trigger": {
                "type": normalize_dynamic_trigger_type(trigger.get("type")),
                "round": _clamp_int(trigger.get("round"), 1, 9999, 1),
                "progress": _clamp_int(trigger.get("progress"), 0, 9999, 0),
                "event": _safe_text(trigger.get("event"), 64),
                "repeat": normalize_dynamic_repeat_mode(trigger.get("repeat")),
            },
            "content": {
                "type": normalize_dynamic_content_type(content.get("type")),
                "title": _safe_text(content.get("title"), 80),
                "imageUrl": str(content.get("imageUrl", "") or "").strip(),
                "caption": _safe_text(content.get("caption"), 240),
                "soundUrl": str(content.get("soundUrl", "") or "").strip(),
                "backgroundUrl": str(content.get("backgroundUrl", "") or "").strip(),
            },
            "presentation": {
                "mode": normalize_dynamic_presentation_mode(presentation.get("mode")),
                "duration": _clamp_float(presentation.get("duration"), 0.0, 60.0, 6.0),
                "autoClose": _parse_bool(presentation.get("autoClose"), True),
            },
            "audio": {
                "enabled": _parse_bool(audio.get("enabled"), False),
                "url": str(audio.get("url", "") or "").strip(),
                "volume": _clamp_float(audio.get("volume"), 0.0, 1.0, 0.5),
                "duckAmbience": _parse_bool(audio.get("duckAmbience"), True),
            },
            "note": _safe_text(raw.get("note"), 800),
        }
    )
    return base


def sanitize_creative_workshop(raw: Any) -> dict[str, Any]:
    base = default_creative_workshop()
    if not isinstance(raw, dict):
        return base

    dynamic_scenes: list[dict[str, Any]] = []
    raw_scenes = raw.get("dynamicScenes", [])
    if isinstance(raw_scenes, list):
        for index, scene in enumerate(raw_scenes, start=1):
            cleaned_scene = sanitize_dynamic_scene(scene, index=index)
            if cleaned_scene:
                dynamic_scenes.append(cleaned_scene)

    base["version"] = _clamp_int(raw.get("version"), 1, 99, 2)
    base["enabled"] = _parse_bool(raw.get("enabled"), True)
    base["opening"] = sanitize_workshop_opening(raw.get("opening", {}))
    base["ambience"] = sanitize_workshop_ambience(raw.get("ambience", {}))
    base["dynamicScenes"] = dynamic_scenes[:64]
    return base


def default_workshop_state() -> dict[str, Any]:
    return {
        "temp": 0,
        "last_signature": "",
        "pending_temp": -1,
        "trigger_history": [],
        "round_count": 0,
        "progress": 0,
        "current_stage": "A",
        "triggered_scenes": [],
    }


def sanitize_workshop_state(raw: Any) -> dict[str, Any]:
    base = default_workshop_state()
    if not isinstance(raw, dict):
        return base
    base["temp"] = _clamp_int(raw.get("temp"), 0, 9999, 0)
    base["last_signature"] = str(raw.get("last_signature", "")).strip()
    base["pending_temp"] = _clamp_int(raw.get("pending_temp"), -1, 9999, -1)
    base["round_count"] = _clamp_int(raw.get("round_count"), 0, 9999, 0)
    base["progress"] = _clamp_int(raw.get("progress", raw.get("temp")), 0, 9999, base["temp"])
    base["current_stage"] = normalize_workshop_stage(raw.get("current_stage") or get_workshop_stage(base["progress"]))
    history = raw.get("trigger_history", [])
    if isinstance(history, list):
        normalized_history: list[str] = []
        for item in history:
            token = str(item or "").strip()
            if token and token not in normalized_history:
                normalized_history.append(token)
        base["trigger_history"] = normalized_history[-128:]
    scenes = raw.get("triggered_scenes", [])
    if isinstance(scenes, list):
        normalized_scenes: list[str] = []
        for item in scenes:
            token = str(item or "").strip()
            if token and token not in normalized_scenes:
                normalized_scenes.append(token)
        base["triggered_scenes"] = normalized_scenes[-256:]
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
