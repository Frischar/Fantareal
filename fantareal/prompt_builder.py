
from __future__ import annotations

import re
from typing import Any, Callable

_DEPS: dict[str, Callable[..., Any]] = {}

V4F_OUTPUT_GUARD_MARKER = "[[RUNTIME_ONLY:V4F_OUTPUT_GUARD]]"
LAYERED_PRESET_EFFECTIVE_PLACEMENTS = {"system_core", "system_format", "before_history", "output_guard"}
LAYERED_PRESET_OBSERVATION_ONLY_PLACEMENTS = {
    "before_character",
    "after_character",
    "lore_context",
    "memory_context",
    "near_latest_user",
    "at_depth",
}
V4F_OUTPUT_GUARD_PROMPT = (
    "【V4F稳定器】\n"
    "本段是本轮回复前的临近约束，只用于稳定 DeepSeek V4-Flash 的 RP 输出，不要在回复中提及这些规则。\n"
    "严格遵守当前角色卡、预设、世界书、记忆和用户指定的输出格式。\n"
    "禁止输出规则解释、分析标题、总结列表、自我说明或与剧情无关的补充说明。\n"
    "严禁替用户补写未在本轮输入中明确出现的动作、台词、心理、决定、情绪结论和身体反应。\n"
    "可以承接或引用用户已经明确写出的动作、姿态、位置和可见状态，但不得新增、改写或推进用户未写出的行为。\n"
    "用户只能由用户自己推进；你的主要描写对象应是非用户角色、环境和当前场景变化。\n"
    "优先通过非用户角色的细微反应承接当前情绪，例如眼神、停顿、呼吸、手指动作、身体距离、语气变化。\n"
    "若场景不适合，不要强行堆叠动作描写。\n"
    "不要直接用“她很感动 / 她很害羞 / 她很难过”等情绪结论替代描写。\n"
    "优先通过动作、对白、停顿和场景互动表现情绪。\n"
    "避免反复使用同一种细微动作或固定句式。\n"
    "不要频繁重复“浅笑、垂眸、指尖、呼吸一滞、偏了偏头”等相似表达。\n"
    "保持角色原本的语气、性格和当前预设文风。\n"
    "不要为了执行本规则，把所有角色都写成温柔、克制、含蓄的同一种口吻。\n"
    "若当前角色卡、预设或用户输入中要求输出状态变量、好感变量、信任变量或类似结尾标签，则这些标签视为强制输出格式，每轮不得省略。 \n"
    "状态变量必须放在整条回复的最后，作为独立区块输出，不得混入正文叙述、旁白或角色台词中。 \n"
    "即使本轮关系没有明显变化，也必须按既定格式输出无变化状态，例如使用+0或原角色卡指定的无变化写法。 \n"
    "不得用“她更加信任你了 / 好感提升 / 关系变近了”等正文描述替代状态变量标签。 \n"
    "如果角色卡或预设已经指定了状态变量格式，必须优先沿用原格式，不得自行改名、改格式或省略字段。 \n"
    "若当前预设要求输出TTS标签，则只有角色直接台词可以附带TTS标签，旁白、动作、环境描写和心理描写不得附带TTS标签。 \n"
    "TTS标签必须严格使用预设指定格式，不得解释标签含义，不得把隐藏标签当作正文内容复述。 \n"
    "结尾应停在仍可继续互动的位置，不要写成总结、落幕、升华、回顾或明显收束。"
)
BASE_KERNEL_MARKERS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("worker_persona", "幕后工作人格", ("幕后工作人格",)),
    ("turn_extraction", "本轮提取格式", ("本轮提取格式",)),
    ("injection_reading", "注入内容读取规则", ("注入内容读取规则",)),
    ("priority_rules", "冲突优先级", ("冲突优先级",)),
    ("body_isolation", "正文隔离规则", ("正文隔离规则",)),
    ("plot_direction", "剧情走向", ("剧情走向",)),
    ("style_taboo", "文风与禁忌", ("文风与禁忌",)),
    ("physical_engine", "物理引擎", ("物理引擎",)),
    ("user_input_truth", "用户输入真实性边界", ("用户输入真实性边界",)),
)


def build_base_kernel_metadata(content: Any) -> dict[str, Any]:
    text = str(content or "").strip()
    markers: list[str] = []
    marker_labels: list[str] = []
    for key, label, keywords in BASE_KERNEL_MARKERS:
        if any(keyword in text for keyword in keywords):
            markers.append(key)
            marker_labels.append(label)
    return {
        "enabled": bool(text),
        "char_count": len(text),
        "markers": markers,
        "marker_labels": marker_labels,
    }


def build_base_thinking_protocol_metadata(content: Any, *, source: str = "base_system_prompt") -> dict[str, Any]:
    text = str(content or "").strip()
    return {
        "enabled": bool(text),
        "mode": "base_as_thinking_protocol",
        "source": source,
        "role_boundary": "think_as_worker_persona_body_as_character",
    }


def _is_base_thinking_protocol_segment(segment: dict[str, Any]) -> bool:
    segment_id = str(segment.get("id", "")).strip()
    metadata = segment.get("metadata") if isinstance(segment.get("metadata"), dict) else {}
    return segment_id in {"preset.base_system_prompt", "preset.rules"} or bool(metadata.get("thinking_protocol"))


def _empty_layered_injection_state(enabled: bool) -> dict[str, Any]:
    mode = "layered" if enabled else "legacy"
    return {
        "enabled": enabled,
        "mode": mode,
        "status": mode,
        "fallback": False,
        "fallback_reason": "",
        "scope": "preset_segments_first_pass",
        "effective_placements": sorted(LAYERED_PRESET_EFFECTIVE_PLACEMENTS),
        "observation_only_placements": sorted(LAYERED_PRESET_OBSERVATION_ONLY_PLACEMENTS),
        "applied_segment_ids": [],
        "observed_segment_ids": [],
        "segment_effects": {},
    }


def _message(role: str, content: str) -> dict[str, str] | None:
    text = str(content or "").strip()
    if not text:
        return None
    normalized_role = str(role or "system").strip() or "system"
    return {"role": normalized_role, "content": text}


def _append_joined_message(messages: list[dict[str, str]], role: str, sections: list[str]) -> None:
    content = "\n\n".join(str(part or "").strip() for part in sections if str(part or "").strip()).strip()
    message = _message(role, content)
    if message:
        messages.append(message)


def _director_note_placement(position: Any) -> str:
    value = str(position or "").strip()
    if value == "before_char_defs":
        return "before_character"
    if value == "before_user_input":
        return "near_latest_user"
    return "after_character"


def _format_director_note(note: dict[str, Any], index: int) -> str:
    content = str(note.get("content", "") or "").strip()
    if not content:
        return ""
    remaining_turns = note.get("remaining_turns", 1)
    return (
        f"【临时导演注 {index}】\n"
        "以下内容是用户临时添加的本轮/短期提示，只用于辅助当前 Chat 组包；"
        "不得覆盖 BASE、角色卡、世界书、记忆或输出守卫。\n"
        f"剩余生效回合：{remaining_turns}\n"
        f"内容：{content}"
    )


def _bucket_director_notes(notes: list[dict[str, Any]] | None) -> dict[str, list[dict[str, Any]]]:
    buckets = {"before_character": [], "after_character": [], "near_latest_user": []}
    for index, note in enumerate(notes or [], start=1):
        if not isinstance(note, dict):
            continue
        content = str(note.get("content", "") or "").strip()
        if not content:
            continue
        item = dict(note)
        item["_prompt_text"] = _format_director_note(item, index)
        placement = _director_note_placement(item.get("position"))
        buckets.setdefault(placement, []).append(item)
    return buckets


def _director_note_sections(buckets: dict[str, list[dict[str, Any]]], placement: str) -> list[str]:
    return [str(item.get("_prompt_text", "") or "").strip() for item in buckets.get(placement, []) if str(item.get("_prompt_text", "") or "").strip()]


def _is_layerable_preset_segment(segment: dict[str, Any]) -> bool:
    source = str(segment.get("source", "")).strip()
    segment_id = str(segment.get("id", "")).strip()
    return source == "preset" and (segment_id.startswith("preset.") or segment_id == "preset.rules")


def _set_layered_effect(
    state: dict[str, Any],
    segment: dict[str, Any],
    *,
    applied: bool,
    final_role: str,
    final_position: str,
    reason: str,
) -> None:
    segment_id = str(segment.get("id", "")).strip() or f"segment_{len(state.get('segment_effects', {})) + 1}"
    effect = {
        "applied": applied,
        "source": str(segment.get("source", "")).strip(),
        "placement": str(segment.get("placement", "")).strip(),
        "final_role": final_role,
        "final_position": final_position,
        "reason": reason,
    }
    state.setdefault("segment_effects", {})[segment_id] = effect
    metadata = dict(segment.get("metadata") or {})
    metadata["layered_injection"] = effect
    segment["metadata"] = metadata
    if applied:
        state.setdefault("applied_segment_ids", []).append(segment_id)
    else:
        state.setdefault("observed_segment_ids", []).append(segment_id)


def _build_layered_messages(
    *,
    prompt_segments: list[dict[str, Any]],
    worldbook_before_char_defs_prompt: str,
    system_prompt: str,
    worldbook_stable_prompt: str,
    worldbook_after_char_defs_prompt: str,
    memory_recap_prompt: str,
    user_profile_prompt: str,
    worldbook_current_state_prompt: str,
    retrieval_prompt: str,
    worldbook_dynamic_prompt: str,
    worldbook_answer_guard: str,
    director_note_buckets: dict[str, list[dict[str, Any]]],
    sprite_prompt: str,
    worldbook_output_guard_prompt: str,
    recent_history: list[dict[str, Any]],
    persona: dict[str, Any],
    in_chat_buckets: Any,
    normalize_worldbook_injection_role: Callable[..., Any],
    build_worldbook_prompt_fn: Callable[..., str],
    clean_user_message: str,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    state = _empty_layered_injection_state(True)
    messages: list[dict[str, str]] = []
    applied_by_placement: dict[str, list[dict[str, Any]]] = {placement: [] for placement in LAYERED_PRESET_EFFECTIVE_PLACEMENTS}
    legacy_preset_sections: list[str] = []

    for segment in prompt_segments:
        placement = str(segment.get("placement", "")).strip()
        if not _is_layerable_preset_segment(segment):
            continue
        is_base_thinking_protocol = _is_base_thinking_protocol_segment(segment)
        if placement in LAYERED_PRESET_EFFECTIVE_PLACEMENTS or is_base_thinking_protocol:
            final_placement = "system_core" if is_base_thinking_protocol else placement
            applied_by_placement.setdefault(final_placement, []).append(segment)
            reason = "实验开关开启：该预设 placement 已进入真实分层编排。"
            if is_base_thinking_protocol:
                reason = "BASE 兼任 thinking_protocol，已作为系统核心优先进入真实分层编排。"
            _set_layered_effect(
                state,
                segment,
                applied=True,
                final_role=str(segment.get("role", "system") or "system"),
                final_position=final_placement,
                reason=reason,
            )
        else:
            text = str(segment.get("content", "")).strip()
            if text:
                legacy_preset_sections.append(text)
            _set_layered_effect(
                state,
                segment,
                applied=False,
                final_role=str(segment.get("role", "system") or "system"),
                final_position="legacy_observation",
                reason="阶段 7 第一版暂不让该 placement 真实生效，仅保留观察。",
            )

    def preset_sections(placement: str) -> list[str]:
        sections: list[str] = []
        seen: set[str] = set()
        segments = list(applied_by_placement.get(placement, []))
        if placement == "system_core":
            segments.sort(key=lambda item: (0 if _is_base_thinking_protocol_segment(item) else 1, int(item.get("order", 0) or 0)))
        for segment in segments:
            text = str(segment.get("content", "")).strip()
            if not text or text in seen:
                continue
            seen.add(text)
            sections.append(text)
        return sections

    system_core_sections = preset_sections("system_core") + legacy_preset_sections
    _append_joined_message(messages, "system", system_core_sections)
    _append_joined_message(
        messages,
        "system",
        [
            worldbook_before_char_defs_prompt,
            *_director_note_sections(director_note_buckets, "before_character"),
            system_prompt,
            worldbook_stable_prompt,
            worldbook_after_char_defs_prompt,
            *_director_note_sections(director_note_buckets, "after_character"),
            memory_recap_prompt,
            user_profile_prompt,
            worldbook_current_state_prompt,
            retrieval_prompt,
            worldbook_dynamic_prompt,
            worldbook_answer_guard,
        ],
    )
    _append_joined_message(messages, "system", preset_sections("system_format") + [sprite_prompt])
    _append_joined_message(messages, "system", preset_sections("before_history"))

    history_count = len(recent_history)

    def append_in_chat_bucket(depth: int) -> None:
        bucket = in_chat_buckets.get(depth, []) if hasattr(in_chat_buckets, "get") else []
        if not bucket:
            return
        role_groups: list[tuple[str, list[dict[str, Any]]]] = []
        for item in bucket:
            role = normalize_worldbook_injection_role(item.get("injection_role", "system"), "system")
            if not role_groups or role_groups[-1][0] != role:
                role_groups.append((role, [item]))
            else:
                role_groups[-1][1].append(item)
        for role, role_items in role_groups:
            content = build_worldbook_prompt_fn(
                role_items,
                heading=f"The following are in-chat worldbook notes at depth {depth}.",
            )
            message = _message(role, content)
            if message:
                messages.append(message)

    for index, item in enumerate(recent_history):
        tail_depth = history_count - index
        append_in_chat_bucket(tail_depth)
        role = str(item.get("role", "assistant")).strip() or "assistant"
        message = _message(role, strip_thought_blocks(item.get("content", "")))
        if message:
            messages.append(message)

    append_in_chat_bucket(0)
    _append_joined_message(messages, "system", preset_sections("output_guard") + [worldbook_output_guard_prompt])
    _append_joined_message(messages, "system", _director_note_sections(director_note_buckets, "near_latest_user"))
    message = _message("user", clean_user_message)
    if message:
        messages.append(message)
    return messages, state


def configure_prompt_builder(**deps: Callable[..., Any]) -> None:
    _DEPS.update({key: value for key, value in deps.items() if callable(value)})


def _dep(name: str) -> Callable[..., Any]:
    fn = _DEPS.get(name)
    if not callable(fn):
        raise RuntimeError(
            f"prompt_builder dependency '{name}' is not configured. "
            "Call configure_prompt_builder(...) during app startup."
        )
    return fn


def _optional_dep(name: str) -> Callable[..., Any] | None:
    fn = _DEPS.get(name)
    return fn if callable(fn) else None


def _extract_runtime_guard_from_preset(preset_prompt: str) -> tuple[str, str]:
    text = str(preset_prompt or "")
    if V4F_OUTPUT_GUARD_MARKER not in text:
        return text.strip(), ""
    cleaned = text.replace(V4F_OUTPUT_GUARD_MARKER, "").strip()
    return cleaned, V4F_OUTPUT_GUARD_PROMPT.strip()


def _build_prompt_segment(
    segment_id: str,
    *,
    source: str,
    kind: str,
    role: str,
    content: str,
    placement: str,
    order: int,
    required: bool = False,
    strength: str = "soft",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    text = str(content or "").strip()
    if not text:
        return None
    segment: dict[str, Any] = {
        "id": segment_id,
        "source": source,
        "kind": kind,
        "role": role,
        "content": text,
        "enabled": True,
        "placement": placement,
        "order": order,
        "required": required,
        "strength": strength,
        "char_count": len(text),
    }
    if metadata:
        segment["metadata"] = metadata
    return segment


def _sanitize_segment_activation_tags(value: Any) -> list[str]:
    raw_items = value if isinstance(value, list) else [value]
    tags: list[str] = []
    for item in raw_items:
        tag = str(item or "").strip()[:128]
        if tag and tag not in tags:
            tags.append(tag)
    return tags[:32]


def _preset_segment_title(segment: dict[str, Any]) -> str:
    metadata = segment.get("metadata", {}) if isinstance(segment.get("metadata"), dict) else {}
    group_name = str(metadata.get("group_name", "")).strip()
    item_name = str(metadata.get("item_name", "")).strip()
    if group_name and item_name:
        return f"{group_name} / {item_name}"
    for key in ("module_label", "item_name", "preset_name"):
        value = str(metadata.get(key, "")).strip()
        if value:
            return value
    return str(segment.get("id", "")).strip() or "preset segment"


def collect_preset_activation_tags(prompt_segments: list[dict[str, Any]]) -> dict[str, Any]:
    tags: list[str] = []
    segments: list[dict[str, Any]] = []
    for segment in prompt_segments:
        if not isinstance(segment, dict):
            continue
        segment_id = str(segment.get("id", "")).strip()
        source = str(segment.get("source", "")).strip()
        if source != "preset" and not segment_id.startswith("preset."):
            continue
        segment_tags = _sanitize_segment_activation_tags(segment.get("activation_tags", []))
        if not segment_tags:
            continue
        for tag in segment_tags:
            if tag not in tags:
                tags.append(tag)
        segments.append(
            {
                "id": segment_id,
                "title": _preset_segment_title(segment),
                "placement": str(segment.get("placement", "")).strip(),
                "kind": str(segment.get("kind", "")).strip(),
                "tags": segment_tags,
            }
        )
    return {"tags": tags, "count": len(tags), "segments": segments}


def _estimate_prompt_tokens(text: Any) -> int:
    """Very rough cross-model estimate for debug display, not tokenizer-accurate."""
    content = str(text or "")
    if not content:
        return 0
    cjk_chars = len(re.findall(r"[㐀-䶿一-鿿豈-﫿]", content))
    non_cjk_chars = max(0, len(content) - cjk_chars)
    return max(1, int(round(cjk_chars + (non_cjk_chars / 4))))


def _read_segment_token_budget(segment: dict[str, Any]) -> int | None:
    raw = segment.get("tokenBudget", segment.get("token_budget"))
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _segment_budget_title(segment: dict[str, Any]) -> str:
    metadata = segment.get("metadata") if isinstance(segment.get("metadata"), dict) else {}
    for key in ("module_label", "group_name", "item_name", "character_name", "layer_id"):
        value = str(metadata.get(key, "")).strip()
        if value:
            if key == "group_name" and str(metadata.get("item_name", "")).strip():
                return f"{value} / {str(metadata.get('item_name', '')).strip()}"
            return value
    return str(segment.get("id", "")).strip() or "segment"


def _budget_bucket_totals(items: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}
    for item in items:
        bucket_key = str(item.get(key, "unknown") or "unknown").strip() or "unknown"
        bucket = buckets.setdefault(bucket_key, {key: bucket_key, "char_count": 0, "estimated_tokens": 0, "segment_count": 0})
        bucket["char_count"] += int(item.get("char_count", 0) or 0)
        bucket["estimated_tokens"] += int(item.get("estimated_tokens", 0) or 0)
        bucket["segment_count"] += 1
    return sorted(buckets.values(), key=lambda row: row["char_count"], reverse=True)


def _build_prompt_budget_dry_run(
    *,
    messages: list[dict[str, str]],
    prompt_segments: list[dict[str, Any]],
    layers: list[dict[str, Any]],
    token_limit: int = 100000,
) -> dict[str, Any]:
    segment_rows: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    would_trim: list[dict[str, Any]] = []
    would_keep: list[dict[str, Any]] = []

    protected_ids = {"runtime.user_input", "preset.base_system_prompt", "preset.rules", "character.definition"}
    protected_sources = {"character"}
    trim_kinds = {"style", "tone", "reference", "director_note"}

    for segment in prompt_segments:
        text = str(segment.get("content", "") or "")
        char_count = len(text)
        estimated_tokens = _estimate_prompt_tokens(text)
        token_budget = _read_segment_token_budget(segment)
        required = bool(segment.get("required", False))
        strength = str(segment.get("strength", "") or "").strip() or "soft"
        source = str(segment.get("source", "") or "").strip() or "unknown"
        kind = str(segment.get("kind", "") or "").strip() or "unknown"
        segment_id = str(segment.get("id", "") or "").strip()
        over_segment_budget = bool(token_budget and estimated_tokens > token_budget)
        metadata = dict(segment.get("metadata") or {})
        metadata["budget"] = {
            "char_count": char_count,
            "estimated_tokens": estimated_tokens,
            "token_budget": token_budget,
            "over_segment_budget": over_segment_budget,
            "required": required,
            "strength": strength,
        }
        segment["metadata"] = metadata
        segment["char_count"] = char_count
        segment["estimated_tokens"] = estimated_tokens

        row = {
            "id": segment_id,
            "title": _segment_budget_title(segment),
            "source": source,
            "placement": str(segment.get("placement", "") or "").strip() or "unknown",
            "kind": kind,
            "required": required,
            "strength": strength,
            "char_count": char_count,
            "estimated_tokens": estimated_tokens,
            "token_budget": token_budget,
            "over_segment_budget": over_segment_budget,
        }
        segment_rows.append(row)
        if over_segment_budget:
            warnings.append(
                {
                    "level": "warning",
                    "segment_id": segment_id,
                    "title": row["title"],
                    "message": f"单段估算 {estimated_tokens} tokens，超过 tokenBudget {token_budget}。",
                }
            )

        protected = required or source in protected_sources or segment_id in protected_ids or bool(metadata.get("thinking_protocol"))
        if protected:
            would_keep.append({**row, "reason": "必需 / 核心片段，dry-run 不建议裁剪。"})
        elif source == "preset" and strength != "hard" and (kind in trim_kinds or over_segment_budget):
            reason = "soft 预设片段，可作为未来预算裁剪候选。"
            if over_segment_budget:
                reason = "超过单段 tokenBudget，可作为未来预算裁剪候选。"
            would_trim.append({**row, "reason": reason})
        elif source in {"memory", "worldbook"} and char_count >= 1500:
            warnings.append(
                {
                    "level": "notice",
                    "segment_id": segment_id,
                    "title": row["title"],
                    "message": "该上下文来源占用较高；8-A 仅提示，不裁剪世界书或记忆。",
                }
            )

    message_rows = []
    for index, message in enumerate(messages, start=1):
        content = str(message.get("content", "") or "")
        message_rows.append(
            {
                "index": index,
                "role": str(message.get("role", "") or "unknown"),
                "char_count": len(content),
                "estimated_tokens": _estimate_prompt_tokens(content),
            }
        )

    layer_rows = []
    for layer in layers:
        content = str(layer.get("content", "") or "")
        layer_rows.append(
            {
                "id": str(layer.get("id", "") or "").strip() or "layer",
                "title": str(layer.get("title", "") or "").strip() or "未命名层",
                "char_count": len(content),
                "estimated_tokens": _estimate_prompt_tokens(content),
            }
        )
    layer_rows.sort(key=lambda row: row["char_count"], reverse=True)

    required_rows = [row for row in segment_rows if row["required"]]
    hard_rows = [row for row in segment_rows if row["strength"] == "hard"]
    soft_rows = [row for row in segment_rows if row["strength"] != "hard"]
    actual_message_chars = sum(row["char_count"] for row in message_rows)
    actual_message_estimated_tokens = sum(row["estimated_tokens"] for row in message_rows)
    normalized_token_limit = max(0, min(200000, int(token_limit or 0)))
    over_budget = bool(normalized_token_limit and actual_message_estimated_tokens > normalized_token_limit)
    over_by_estimated_tokens = max(0, actual_message_estimated_tokens - normalized_token_limit) if normalized_token_limit else 0
    usage_ratio = (actual_message_estimated_tokens / normalized_token_limit) if normalized_token_limit else None

    if over_budget:
        warnings.insert(
            0,
            {
                "level": "warning",
                "message": f"当前上下文估算 {actual_message_estimated_tokens} tokens，超过预算上限 {normalized_token_limit}，超出约 {over_by_estimated_tokens} tokens。",
            },
        )

    return {
        "enabled": True,
        "mode": "dry_run",
        "applied": False,
        "estimator": "cjk_chars_plus_non_cjk_div_4",
        "notes": "估算仅用于 Prompt Debug；本阶段不真实裁剪，不改变 messages。",
        "budget_limit": normalized_token_limit,
        "over_budget": over_budget,
        "over_by_estimated_tokens": over_by_estimated_tokens,
        "usage_ratio": usage_ratio,
        "actual_message_chars": actual_message_chars,
        "actual_message_estimated_tokens": actual_message_estimated_tokens,
        "total_segment_chars": sum(row["char_count"] for row in segment_rows),
        "total_segment_estimated_tokens": sum(row["estimated_tokens"] for row in segment_rows),
        "required_chars": sum(row["char_count"] for row in required_rows),
        "required_estimated_tokens": sum(row["estimated_tokens"] for row in required_rows),
        "hard_chars": sum(row["char_count"] for row in hard_rows),
        "hard_estimated_tokens": sum(row["estimated_tokens"] for row in hard_rows),
        "soft_chars": sum(row["char_count"] for row in soft_rows),
        "soft_estimated_tokens": sum(row["estimated_tokens"] for row in soft_rows),
        "message_totals": message_rows,
        "layer_totals": layer_rows,
        "source_totals": _budget_bucket_totals(segment_rows, "source"),
        "placement_totals": _budget_bucket_totals(segment_rows, "placement"),
        "largest_segments": sorted(segment_rows, key=lambda row: row["char_count"], reverse=True)[:12],
        "over_budget_segments": [row for row in segment_rows if row["over_segment_budget"]],
        "would_keep": sorted(would_keep, key=lambda row: row["char_count"], reverse=True)[:12],
        "would_trim": sorted(would_trim, key=lambda row: row["char_count"], reverse=True)[:12],
        "would_drop": [],
        "warnings": warnings[:20],
    }


def _append_prompt_segment(segments: list[dict[str, Any]], *args: Any, **kwargs: Any) -> None:
    segment = _build_prompt_segment(*args, **kwargs)
    if segment:
        segments.append(segment)


def _worldbook_direct_question(user_message: str) -> bool:
    text = str(user_message or "").strip().lower()
    if not text:
        return False
    markers = (
        "what", "who", "why", "how", "tell me", "explain", "?", "？",
        "什么", "是谁", "为啥", "为什么", "怎么", "如何", "解释", "告诉我", "说说", "介绍",
    )
    return any(marker in text for marker in markers)


def build_worldbook_prompt(
    matches: list[dict[str, Any]],
    *,
    heading: str = "The following are the worldbook notes matched in this turn.",
) -> str:
    if not matches:
        return ""

    blocks = [
        heading,
        "These are high-priority factual backdrops for the current conversation.",
        "If the user is asking about any of these items directly, answer from these notes first.",
        "Do not mention that you saw the worldbook notes in your answer.",
    ]
    for index, item in enumerate(matches, start=1):
        matched = item.get("matched", "")
        title = str(item.get("title", "")).strip()
        lines = [f"{index}. Title: {title or item['trigger']}"]
        source = str(item.get("source", "keyword")).strip()
        if source:
            lines.append(f"Source: {source}")
        group = str(item.get("group", "")).strip()
        if group:
            lines.append(f"Group: {group}")
        if item.get("trigger"):
            lines.append(f"Trigger: {item['trigger']}")
        if matched:
            lines.append(f"Matched: {matched}")
        if item.get("secondary_trigger"):
            lines.append(f"Secondary trigger: {item['secondary_trigger']}")
        lines.append(f"Content: {item['content']}")
        if item.get("comment"):
            lines.append(f"Comment: {item['comment']}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def build_worldbook_answer_guard(user_message: str, matches: list[dict[str, Any]]) -> str:
    if not matches:
        return ""

    text = str(user_message or "").strip()
    if not text or not _worldbook_direct_question(text):
        return ""

    primary_match = matches[0]
    subject = primary_match.get("matched") or primary_match.get("title") or primary_match.get("trigger") or "this item"
    fact = str(primary_match.get("content", "")).strip()
    if not fact:
        return ""

    return (
        f'The user may be asking about "{subject}".\n'
        "Use the matched notes as private reference.\n"
        "Answer naturally in character.\n"
        "Do not quote or dump the worldbook note verbatim unless the user explicitly asks for raw setting text."
    )


def build_retrieval_prompt(retrieved_items: list[dict[str, Any]]) -> str:
    if not retrieved_items:
        return ""

    blocks = [
        "The following are the most relevant long-term memories for the current message.",
        "Use them as supporting context, but do not hallucinate details that are not present.",
    ]
    for index, item in enumerate(retrieved_items, start=1):
        title = str(item.get("title", "")).strip() or f"Memory {index}"
        blocks.append(f"{index}. {title}\n{item.get('text', '')}")
    return "\n\n".join(blocks)


def build_memory_recap_prompt(memories: list[dict[str, Any]]) -> str:
    if not memories:
        return ""

    sanitize_tags = _dep("sanitize_tags")
    blocks = [
        "The following are long-term memories that should stay consistent over time.",
        "Treat them as durable background facts unless the user explicitly asks to revise them.",
    ]
    for index, item in enumerate(memories, start=1):
        title = str(item.get("title", "")).strip() or f"Memory {index}"
        content = str(item.get("content", "")).strip()
        tags = ", ".join(sanitize_tags(item.get("tags", [])))
        notes = str(item.get("notes", "")).strip()
        lines = [f"{index}. {title}"]
        if content:
            lines.append(f"Content: {content}")
        if tags:
            lines.append(f"Tags: {tags}")
        if notes:
            lines.append(f"Notes: {notes}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def build_user_profile_prompt(user_profile: dict[str, Any]) -> str:
    if not isinstance(user_profile, dict):
        return ""

    display_name = str(user_profile.get("display_name", "")).strip()
    nickname = str(user_profile.get("nickname", "")).strip()
    profile_text = str(user_profile.get("profile_text", "")).strip()
    notes = str(user_profile.get("notes", "")).strip()

    if display_name == "" and not any([nickname, profile_text, notes]):
        return ""

    blocks = [
        "The following are the user profile details bound to the current slot.",
        "Treat them as stable background information for addressing and understanding the user.",
        "Do not rewrite these details as if they were your own persona settings.",
    ]
    if display_name:
        blocks.append(f"Display name: {display_name}")
    if nickname:
        blocks.append(f"Nickname: {nickname}")
    if profile_text:
        blocks.append(f"Profile text: {profile_text}")
    if notes:
        blocks.append(f"Notes: {notes}")
    return "\n".join(blocks)


def build_sprite_prompt(llm_config: dict[str, Any]) -> str:
    if not llm_config.get("sprite_enabled", False):
        return ""

    return (
        "Always start every reply with a single sprite tag on the first line in the format [expression:tag].\n"
        "Do not omit the tag. Do not place anything before it.\n"
        "Keep the tag short and simple, such as happy, calm, angry, sad, or surprised.\n"
        "After the tag, write the normal reply. Do not explain the rule.\n"
    )


def strip_thought_blocks(text: Any) -> str:
    """Keep stored chat intact, but remove <think>...</think> blocks before building prompts."""
    content = str(text or "")

    # Remove completed thinking blocks.
    content = re.sub(
        r"<think\b[^>]*>.*?</think>",
        "",
        content,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # Remove an unfinished thinking block if a streamed reply was interrupted.
    content = re.sub(
        r"<think\b[^>]*>.*$",
        "",
        content,
        flags=re.IGNORECASE | re.DOTALL,
    )

    return content.strip()


def _same_normalized_text(left: Any, right: Any) -> bool:
    """Compare long opening text safely without being too sensitive to whitespace."""
    left_text = re.sub(r"\s+", "\n", str(left or "").strip())
    right_text = re.sub(r"\s+", "\n", str(right or "").strip())
    return bool(left_text and right_text and left_text == right_text)


def _is_opening_only_message(item: dict[str, Any], persona: dict[str, Any] | None = None) -> bool:
    """Opening/greeting is UI-only. It must not be sent back as chat history context."""
    if not isinstance(item, dict):
        return False

    if item.get("source") in {"character_opening", "opening_message", "first_mes", "greeting"}:
        return True

    if item.get("is_opening") is True or item.get("opening_message") is True:
        return True

    if str(item.get("role", "")).strip() != "assistant":
        return False

    opening_text = ""
    if isinstance(persona, dict):
        opening_text = str(
            persona.get("opening_message")
            or persona.get("first_mes")
            or persona.get("first_message")
            or persona.get("greeting")
            or ""
        ).strip()

    return bool(opening_text and _same_normalized_text(item.get("content", ""), opening_text))


def filter_prompt_history(history: list[dict[str, Any]], persona: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Remove UI-only opening messages before building model prompts."""
    return [item for item in history if not _is_opening_only_message(item, persona)]


def build_conversation_transcript(history: list[dict[str, Any]], persona: dict[str, Any] | None = None) -> str:
    lines: list[str] = []
    for item in filter_prompt_history(history, persona):
        role = item.get("role", "")
        content = strip_thought_blocks(item.get("content", ""))
        if role not in {"user", "assistant"} or not content:
            continue
        speaker = "User" if role == "user" else "AI"
        lines.append(f"{speaker}: {content}")
    return "\n".join(lines)


def build_prompt_package(
    user_message: str,
    retrieved_items: list[dict[str, Any]] | None = None,
    *,
    runtime_overrides: dict[str, Any] | None = None,
    worldbook_matches: list[dict[str, Any]] | None = None,
    preset_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    get_persona = _dep("get_persona")
    get_conversation = _dep("get_conversation")
    get_memories = _dep("get_memories")
    get_user_profile = _dep("get_user_profile")
    get_runtime_chat_config = _dep("get_runtime_chat_config")
    bucket_worldbook_matches = _dep("bucket_worldbook_matches")
    normalize_worldbook_injection_role = _dep("normalize_worldbook_injection_role")
    build_preset_prompt = _dep("build_preset_prompt")
    build_preset_observation_segments = _optional_dep("build_preset_observation_segments")
    build_preset_output_guard = _optional_dep("build_preset_output_guard")
    get_director_notes = _optional_dep("get_director_notes")

    persona = get_persona()
    history = get_conversation()
    memories = get_memories()
    user_profile = get_user_profile()
    director_notes = get_director_notes() if get_director_notes else []
    director_note_buckets = _bucket_director_notes(director_notes)
    llm_config = get_runtime_chat_config(runtime_overrides)

    matched_worldbook_entries = worldbook_matches or []
    recalled_memories = retrieved_items or []
    worldbook_buckets = bucket_worldbook_matches(matched_worldbook_entries)

    if isinstance(preset_context, dict):
        preset_prompt = str(preset_context.get("prompt", "")).strip()
        preset_observation_segments = (
            preset_context.get("observation_segments", [])
            if isinstance(preset_context.get("observation_segments", []), list)
            else []
        )
    else:
        preset_prompt = build_preset_prompt()
        preset_observation_segments = build_preset_observation_segments() if build_preset_observation_segments else []
    preset_prompt, marker_output_guard_prompt = _extract_runtime_guard_from_preset(preset_prompt)
    system_prompt = str(persona.get("system_prompt", "")).strip()
    memory_recap_prompt = build_memory_recap_prompt(memories)
    user_profile_prompt = build_user_profile_prompt(user_profile)
    worldbook_stable_prompt = build_worldbook_prompt(
        worldbook_buckets.get("stable", []),
        heading="The following are stable worldbook notes for durable setting, character grounding, and long-running RP consistency.",
    )
    worldbook_current_state_prompt = build_worldbook_prompt(
        worldbook_buckets.get("current_state", []),
        heading="The following worldbook notes describe the current chapter, location, relationship, or temporary state.",
    )
    worldbook_before_char_defs_prompt = build_worldbook_prompt(
        worldbook_buckets.get("before_char_defs", []),
        heading="The following worldbook notes must be considered before the character definition.",
    )
    worldbook_after_char_defs_prompt = build_worldbook_prompt(
        worldbook_buckets.get("after_char_defs", []),
        heading="The following worldbook notes refine or extend the character definition for this turn.",
    )
    worldbook_dynamic_prompt = build_worldbook_prompt(
        worldbook_buckets.get("dynamic", []),
        heading="The following worldbook notes are temporary turn-level hints for the current message.",
    )
    worldbook_output_guard_prompt = build_worldbook_prompt(
        worldbook_buckets.get("output_guard", []),
        heading="The following worldbook notes are final output-format rules for this turn.",
    )
    worldbook_answer_guard = build_worldbook_answer_guard(user_message, matched_worldbook_entries)
    retrieval_prompt = build_retrieval_prompt(recalled_memories)
    sprite_prompt = build_sprite_prompt(llm_config)
    dependency_output_guard_prompt = str(build_preset_output_guard()).strip() if build_preset_output_guard else ""
    preset_output_guard_prompt = dependency_output_guard_prompt or marker_output_guard_prompt

    history_limit = max(1, int(llm_config["history_limit"]))
    prompt_history = filter_prompt_history(history, persona)
    conversation_turn_number = sum(1 for item in prompt_history if str(item.get("role", "")).strip() == "user") + 1
    recent_history = prompt_history[-history_limit:]
    recent_history_text = build_conversation_transcript(recent_history, persona)

    actual_system_sections = [
        prompt
        for prompt in [
            preset_prompt,
            worldbook_before_char_defs_prompt,
            *_director_note_sections(director_note_buckets, "before_character"),
            system_prompt,
            worldbook_stable_prompt,
            worldbook_after_char_defs_prompt,
            *_director_note_sections(director_note_buckets, "after_character"),
            memory_recap_prompt,
            user_profile_prompt,
            worldbook_current_state_prompt,
            retrieval_prompt,
            worldbook_dynamic_prompt,
            worldbook_answer_guard,
            sprite_prompt,
        ]
        if str(prompt or "").strip()
    ]

    messages: list[dict[str, str]] = []
    if actual_system_sections:
        messages.append({"role": "system", "content": "\n\n".join(actual_system_sections)})

    in_chat_buckets = worldbook_buckets.get("in_chat", {})

    def append_in_chat_bucket(depth: int) -> None:
        bucket = in_chat_buckets.get(depth, [])
        if not bucket:
            return

        role_groups: list[tuple[str, list[dict[str, Any]]]] = []
        for item in bucket:
            role = normalize_worldbook_injection_role(item.get("injection_role", "system"), "system")
            if not role_groups or role_groups[-1][0] != role:
                role_groups.append((role, [item]))
            else:
                role_groups[-1][1].append(item)

        for role, role_items in role_groups:
            content = build_worldbook_prompt(
                role_items,
                heading=f"The following are in-chat worldbook notes at depth {depth}.",
            )
            if content:
                messages.append({"role": role, "content": content})

    history_count = len(recent_history)
    for index, item in enumerate(recent_history):
        tail_depth = history_count - index
        append_in_chat_bucket(tail_depth)

        role = str(item.get("role", "assistant")).strip() or "assistant"
        content = strip_thought_blocks(item.get("content", ""))
        if content:
            messages.append({"role": role, "content": content})

    append_in_chat_bucket(0)

    final_guard_sections = [
        prompt
        for prompt in [
            preset_output_guard_prompt,
            worldbook_output_guard_prompt,
        ]
        if str(prompt or "").strip()
    ]
    if final_guard_sections:
        messages.append({"role": "system", "content": "\n\n".join(final_guard_sections)})

    near_user_director_sections = _director_note_sections(director_note_buckets, "near_latest_user")
    if near_user_director_sections:
        messages.append({"role": "system", "content": "\n\n".join(near_user_director_sections)})

    clean_user_message = str(user_message or "").strip()
    messages.append({"role": "user", "content": clean_user_message})

    prompt_segments: list[dict[str, Any]] = []
    segment_order = 0

    def append_segment(
        segment_id: str,
        *,
        source: str,
        kind: str,
        role: str,
        content: str,
        placement: str,
        required: bool = False,
        strength: str = "soft",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        nonlocal segment_order
        segment_order += 10
        _append_prompt_segment(
            prompt_segments,
            segment_id,
            source=source,
            kind=kind,
            role=role,
            content=content,
            placement=placement,
            order=segment_order,
            required=required,
            strength=strength,
            metadata=metadata,
        )

    if preset_observation_segments:
        for preset_segment in preset_observation_segments:
            segment_order += 10
            segment = dict(preset_segment)
            segment["order"] = segment_order
            metadata = dict(segment.get("metadata") or {})
            metadata.setdefault("layer_id", "preset_rules")
            if str(segment.get("id", "")).strip() == "preset.base_system_prompt":
                metadata.setdefault("base_kernel", build_base_kernel_metadata(segment.get("content", "")))
                metadata.setdefault("thinking_protocol", build_base_thinking_protocol_metadata(segment.get("content", "")))
                segment["placement"] = "system_core"
                segment["required"] = True
                segment["strength"] = "hard"
            segment["metadata"] = metadata
            prompt_segments.append(segment)
    else:
        append_segment(
            "preset.rules",
            source="preset",
            kind="base",
            role="system",
            content=preset_prompt,
            placement="system_core",
            required=True,
            strength="hard",
            metadata={
                "layer_id": "preset_rules",
                "base_kernel": build_base_kernel_metadata(preset_prompt),
                "thinking_protocol": build_base_thinking_protocol_metadata(preset_prompt, source="preset_rules"),
            },
        )
    append_segment(
        "worldbook.before_char_defs",
        source="worldbook",
        kind="lore_policy",
        role="system",
        content=worldbook_before_char_defs_prompt,
        placement="before_character",
        required=True,
        strength="hard",
        metadata={"layer_id": "worldbook_before_char_defs", "hit_count": len(worldbook_buckets.get("before_char_defs", []))},
    )
    for note in director_note_buckets.get("before_character", []):
        append_segment(
            str(note.get("id", "director_note")),
            source="runtime",
            kind="director_note",
            role="system",
            content=str(note.get("_prompt_text", "") or ""),
            placement="before_character",
            required=True,
            strength="soft",
            metadata={
                "layer_id": "director_notes",
                "note_id": str(note.get("id", "")),
                "position": str(note.get("position", "")),
                "remaining_turns": int(note.get("remaining_turns", 1) or 1),
            },
        )
    append_segment(
        "character.definition",
        source="character",
        kind="character_policy",
        role="system",
        content=system_prompt,
        placement="character",
        required=True,
        strength="hard",
        metadata={"layer_id": "character_definition", "character_name": str(persona.get("name", "")).strip()},
    )
    append_segment(
        "worldbook.stable",
        source="worldbook",
        kind="lore_policy",
        role="system",
        content=worldbook_stable_prompt,
        placement="lore_context",
        strength="hard",
        metadata={"layer_id": "stable_worldbook", "hit_count": len(worldbook_buckets.get("stable", []))},
    )
    append_segment(
        "worldbook.after_char_defs",
        source="worldbook",
        kind="lore_policy",
        role="system",
        content=worldbook_after_char_defs_prompt,
        placement="after_character",
        strength="hard",
        metadata={"layer_id": "worldbook_after_char_defs", "hit_count": len(worldbook_buckets.get("after_char_defs", []))},
    )
    for note in director_note_buckets.get("after_character", []):
        append_segment(
            str(note.get("id", "director_note")),
            source="runtime",
            kind="director_note",
            role="system",
            content=str(note.get("_prompt_text", "") or ""),
            placement="after_character",
            required=True,
            strength="soft",
            metadata={
                "layer_id": "director_notes",
                "note_id": str(note.get("id", "")),
                "position": str(note.get("position", "")),
                "remaining_turns": int(note.get("remaining_turns", 1) or 1),
            },
        )
    append_segment(
        "memory.recap",
        source="memory",
        kind="memory",
        role="system",
        content=memory_recap_prompt,
        placement="memory_context",
        metadata={"layer_id": "memory_and_user_profile", "stored_memory_count": len(memories)},
    )
    append_segment(
        "user_profile.current",
        source="user_profile",
        kind="memory",
        role="system",
        content=user_profile_prompt,
        placement="memory_context",
        metadata={"layer_id": "memory_and_user_profile"},
    )
    append_segment(
        "worldbook.current_state",
        source="worldbook",
        kind="lore_policy",
        role="system",
        content=worldbook_current_state_prompt,
        placement="lore_context",
        metadata={"layer_id": "current_state_context", "hit_count": len(worldbook_buckets.get("current_state", []))},
    )
    append_segment(
        "memory.retrieval",
        source="memory",
        kind="reference",
        role="system",
        content=retrieval_prompt,
        placement="memory_context",
        metadata={"layer_id": "retrieval_context", "recalled_memory_count": len(recalled_memories)},
    )
    append_segment(
        "worldbook.dynamic",
        source="worldbook",
        kind="lore_policy",
        role="system",
        content=worldbook_dynamic_prompt,
        placement="near_latest_user",
        metadata={"layer_id": "dynamic_worldbook", "hit_count": len(worldbook_buckets.get("dynamic", []))},
    )
    append_segment(
        "worldbook.answer_guard",
        source="worldbook",
        kind="output_guard",
        role="system",
        content=worldbook_answer_guard,
        placement="near_latest_user",
        strength="hard",
        metadata={"layer_id": "worldbook_answer_guard", "hit_count": len(matched_worldbook_entries)},
    )
    for note in director_note_buckets.get("near_latest_user", []):
        append_segment(
            str(note.get("id", "director_note")),
            source="runtime",
            kind="director_note",
            role="system",
            content=str(note.get("_prompt_text", "") or ""),
            placement="near_latest_user",
            required=True,
            strength="soft",
            metadata={
                "layer_id": "director_notes",
                "note_id": str(note.get("id", "")),
                "position": str(note.get("position", "")),
                "remaining_turns": int(note.get("remaining_turns", 1) or 1),
            },
        )
    append_segment(
        "runtime.sprite",
        source="runtime",
        kind="output_rule",
        role="system",
        content=sprite_prompt,
        placement="system_format",
        metadata={"layer_id": "final_output_guard", "sprite_enabled": bool(llm_config.get("sprite_enabled", False))},
    )

    def append_in_chat_segments(depth: int) -> None:
        bucket = in_chat_buckets.get(depth, [])
        if not bucket:
            return

        role_groups: list[tuple[str, list[dict[str, Any]]]] = []
        for item in bucket:
            role = normalize_worldbook_injection_role(item.get("injection_role", "system"), "system")
            if not role_groups or role_groups[-1][0] != role:
                role_groups.append((role, [item]))
            else:
                role_groups[-1][1].append(item)

        for group_index, (role, role_items) in enumerate(role_groups, start=1):
            append_segment(
                f"worldbook.in_chat.depth_{depth}.{group_index}",
                source="worldbook",
                kind="lore_policy",
                role=role,
                content=build_worldbook_prompt(
                    role_items,
                    heading=f"The following are in-chat worldbook notes at depth {depth}.",
                ),
                placement="at_depth",
                metadata={"layer_id": f"worldbook_in_chat_depth_{depth}", "depth": depth, "hit_count": len(role_items)},
            )

    for index, item in enumerate(recent_history, start=1):
        tail_depth = history_count - (index - 1)
        append_in_chat_segments(tail_depth)
        role = str(item.get("role", "assistant")).strip() or "assistant"
        append_segment(
            f"history.{index}",
            source="runtime",
            kind="dialogue",
            role=role,
            content=strip_thought_blocks(item.get("content", "")),
            placement="before_history",
            metadata={"layer_id": "recent_history", "tail_depth": tail_depth},
        )

    append_in_chat_segments(0)
    append_segment(
        "preset.output_guard",
        source="preset",
        kind="output_guard",
        role="system",
        content=preset_output_guard_prompt,
        placement="output_guard",
        required=True,
        strength="hard",
        metadata={"layer_id": "final_output_guard"},
    )
    append_segment(
        "worldbook.output_guard",
        source="worldbook",
        kind="output_guard",
        role="system",
        content=worldbook_output_guard_prompt,
        placement="output_guard",
        required=True,
        strength="hard",
        metadata={"layer_id": "final_output_guard", "hit_count": len(worldbook_buckets.get("output_guard", []))},
    )
    append_segment(
        "runtime.user_input",
        source="runtime",
        kind="dialogue",
        role="user",
        content=clean_user_message,
        placement="near_latest_user",
        required=True,
        strength="hard",
        metadata={"layer_id": "user_input", "char_count": len(clean_user_message)},
    )

    layered_enabled = bool(llm_config.get("layered_prompt_injection_enabled", False))
    layered_injection = _empty_layered_injection_state(layered_enabled)
    if layered_enabled:
        try:
            messages, layered_injection = _build_layered_messages(
                prompt_segments=prompt_segments,
                worldbook_before_char_defs_prompt=worldbook_before_char_defs_prompt,
                system_prompt=system_prompt,
                worldbook_stable_prompt=worldbook_stable_prompt,
                worldbook_after_char_defs_prompt=worldbook_after_char_defs_prompt,
                memory_recap_prompt=memory_recap_prompt,
                user_profile_prompt=user_profile_prompt,
                worldbook_current_state_prompt=worldbook_current_state_prompt,
                retrieval_prompt=retrieval_prompt,
                worldbook_dynamic_prompt=worldbook_dynamic_prompt,
                worldbook_answer_guard=worldbook_answer_guard,
                director_note_buckets=director_note_buckets,
                sprite_prompt=sprite_prompt,
                worldbook_output_guard_prompt=worldbook_output_guard_prompt,
                recent_history=recent_history,
                persona=persona,
                in_chat_buckets=in_chat_buckets,
                normalize_worldbook_injection_role=normalize_worldbook_injection_role,
                build_worldbook_prompt_fn=build_worldbook_prompt,
                clean_user_message=clean_user_message,
            )
        except Exception as exc:
            layered_injection = _empty_layered_injection_state(True)
            layered_injection["mode"] = "legacy"
            layered_injection["status"] = "fallback"
            layered_injection["fallback"] = True
            layered_injection["fallback_reason"] = str(exc)[:240]
            for segment in prompt_segments:
                if _is_layerable_preset_segment(segment):
                    _set_layered_effect(
                        layered_injection,
                        segment,
                        applied=False,
                        final_role=str(segment.get("role", "system") or "system"),
                        final_position="legacy_fallback",
                        reason="分层构造失败，已回退当前稳定拼装。",
                    )
    else:
        for segment in prompt_segments:
            if _is_layerable_preset_segment(segment):
                _set_layered_effect(
                    layered_injection,
                    segment,
                    applied=False,
                    final_role=str(segment.get("role", "system") or "system"),
                    final_position="legacy_observation",
                    reason="实验开关关闭：PromptSegment 仅用于观察，不改变真实 messages。",
                )

    layers: list[dict[str, Any]] = []

    def append_layer(layer_id: str, title: str, sections: list[str], **meta: Any) -> None:
        content = "\n\n".join(part for part in sections if str(part or "").strip()).strip()
        if not content:
            return
        layer: dict[str, Any] = {
            "id": layer_id,
            "title": title,
            "content": content,
        }
        if meta:
            layer["meta"] = meta
        layers.append(layer)

    append_layer(
        "preset_rules",
        "预设规则：基础系统规则 / 常用模块",
        [preset_prompt],
        preset_section_count=1 if preset_prompt else 0,
    )
    append_layer(
        "worldbook_before_char_defs",
        "角色定义前世界书：高优先级前置设定",
        [worldbook_before_char_defs_prompt],
        hit_count=len(worldbook_buckets.get("before_char_defs", [])),
    )
    append_layer(
        "director_notes_before_character",
        "临时导演注：角色前",
        _director_note_sections(director_note_buckets, "before_character"),
        note_count=len(director_note_buckets.get("before_character", [])),
        position="before_char_defs",
    )
    append_layer(
        "character_definition",
        "角色卡：人物设定 / 场景 / 示例对话",
        [system_prompt],
        character_name=str(persona.get("name", "")).strip(),
    )
    append_layer(
        "stable_worldbook",
        "稳定世界书：常驻设定 / 固定世界观",
        [worldbook_stable_prompt],
        stable_worldbook_count=len(worldbook_buckets.get("stable", [])),
    )
    append_layer(
        "worldbook_after_char_defs",
        "角色定义后世界书：角色补充设定",
        [worldbook_after_char_defs_prompt],
        hit_count=len(worldbook_buckets.get("after_char_defs", [])),
    )
    append_layer(
        "director_notes_after_character",
        "临时导演注：角色后",
        _director_note_sections(director_note_buckets, "after_character"),
        note_count=len(director_note_buckets.get("after_character", [])),
        position="after_char_defs",
    )
    append_layer(
        "memory_and_user_profile",
        "长期记忆与用户资料",
        [memory_recap_prompt, user_profile_prompt],
        stored_memory_count=len(memories),
        has_user_profile=bool(user_profile_prompt),
    )
    append_layer(
        "current_state_context",
        "当前状态区：地点 / 章节 / 关系状态",
        [worldbook_current_state_prompt],
        hit_count=len(worldbook_buckets.get("current_state", [])),
    )
    append_layer(
        "retrieval_context",
        "本轮相关记忆：检索召回",
        [retrieval_prompt],
        recalled_memory_count=len(recalled_memories),
    )
    append_layer(
        "dynamic_worldbook",
        "本轮命中世界书：关键词 / 递归 / 临时提示",
        [worldbook_dynamic_prompt],
        hit_count=len(worldbook_buckets.get("dynamic", [])),
    )
    for depth in sorted(in_chat_buckets):
        append_layer(
            f"worldbook_in_chat_depth_{depth}",
            f"聊天深度世界书：插入聊天记录附近 depth {depth}",
            [build_worldbook_prompt(in_chat_buckets[depth], heading=f"In-chat depth {depth}")],
            hit_count=len(in_chat_buckets[depth]),
            depth=depth,
        )
    append_layer(
        "worldbook_answer_guard",
        "设定问答提示：直接问设定时使用",
        [worldbook_answer_guard],
        hit_count=len(matched_worldbook_entries),
    )
    append_layer(
        "director_notes_near_latest_user",
        "临时导演注：用户输入前",
        _director_note_sections(director_note_buckets, "near_latest_user"),
        note_count=len(director_note_buckets.get("near_latest_user", [])),
        position="before_user_input",
    )
    append_layer(
        "recent_history",
        "最近聊天记录：已移除思考链",
        [recent_history_text],
        turn_count=len(recent_history),
    )
    append_layer(
        "final_output_guard",
        "输出格式规则：V4F稳定器 / TTS / 状态变量",
        [sprite_prompt, preset_output_guard_prompt, worldbook_output_guard_prompt],
        sprite_enabled=bool(llm_config.get("sprite_enabled", False)),
        preset_guard_enabled=bool(preset_output_guard_prompt),
        output_worldbook_count=len(worldbook_buckets.get("output_guard", [])),
    )
    append_layer(
        "user_input",
        "本轮用户输入：当前这句话",
        [clean_user_message],
        char_count=len(clean_user_message),
    )

    preview_blocks: list[str] = []
    for index, layer in enumerate(layers, start=1):
        preview_blocks.append(f"[{index}. {layer['title']}]\n{layer['content']}")

    preset_activation_tags = (
        preset_context.get("activation_tags")
        if isinstance(preset_context, dict) and isinstance(preset_context.get("activation_tags"), dict)
        else collect_preset_activation_tags(prompt_segments)
    )
    budget_dry_run = _build_prompt_budget_dry_run(
        messages=messages,
        prompt_segments=prompt_segments,
        layers=layers,
        token_limit=llm_config.get("prompt_budget_token_limit", 100000),
    )

    return {
        "layers": layers,
        "messages": messages,
        "prompt_segments": prompt_segments,
        "preset_activation_tags": preset_activation_tags,
        "layered_injection": layered_injection,
        "budget_dry_run": budget_dry_run,
        "prompt_segment_summary": {
            "segment_count": len(prompt_segments),
            "total_char_count": sum(int(segment.get("char_count", 0)) for segment in prompt_segments),
            "total_estimated_tokens": sum(int(segment.get("estimated_tokens", 0)) for segment in prompt_segments),
            "placements": sorted({str(segment.get("placement", "")) for segment in prompt_segments if segment.get("placement")}),
            "activation_tag_count": int(preset_activation_tags.get("count", 0)),
        },
        "preview_text": "\n\n".join(preview_blocks).strip(),
        "message_count": len(messages),
        "system_section_count": len(actual_system_sections),
        "director_notes": director_notes,
        "recent_history_turns": len(recent_history),
        "total_history_turns": len(prompt_history),
        "conversation_turn_number": conversation_turn_number,
    }


def build_messages(
    user_message: str,
    retrieved_items: list[dict[str, Any]] | None = None,
    *,
    runtime_overrides: dict[str, Any] | None = None,
    worldbook_matches: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    return build_prompt_package(
        user_message,
        retrieved_items,
        runtime_overrides=runtime_overrides,
        worldbook_matches=worldbook_matches,
    )["messages"]


__all__ = [
    "configure_prompt_builder",
    "build_conversation_transcript",
    "filter_prompt_history",
    "build_memory_recap_prompt",
    "build_messages",
    "build_prompt_package",
    "build_retrieval_prompt",
    "build_sprite_prompt",
    "build_user_profile_prompt",
    "strip_thought_blocks",
    "build_worldbook_answer_guard",
    "build_worldbook_prompt",
]
