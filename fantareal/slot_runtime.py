import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from .app_models import (
    DynamicWorldbookPreviewPayload,
    ScenarioBundle,
    SlotActivePreset,
    SlotChatMessage,
    SlotEnvironmentState,
    SlotForkPayload,
    SlotMetadata,
    SlotRuntimeMedia,
    SlotState,
    SlotSummaryBuffer,
    SlotSummaryBufferPayload,
    SlotVariablePatchPayload,
    SlotVariableStore,
    SlotWorldbookContext,
)
from .worldbook_logic import keyword_matches_query, sanitize_worldbook_store, split_trigger_aliases
from .workshop_logic import get_workshop_stage, sanitize_creative_workshop, select_workshop_match


class SlotRuntimeService:
    SNAPSHOT_FILENAME = "slot_state.json"

    def __init__(self, ctx: Any):
        self.ctx = ctx

    def _now_iso(self) -> str:
        return datetime.now().isoformat(timespec="seconds")

    def _slot_id(self, slot_id: str | None = None) -> str:
        return self.ctx.sanitize_slot_id(slot_id, self.ctx.get_active_slot_id())

    def slot_state_path(self, slot_id: str | None = None) -> Path:
        return self.ctx.get_slot_dir(self._slot_id(slot_id)) / self.SNAPSHOT_FILENAME

    def _read_snapshot(self, slot_id: str | None = None) -> SlotState | None:
        path = self.slot_state_path(slot_id)
        raw = self.ctx.read_json(path, {})
        if not isinstance(raw, dict) or not raw:
            return None
        try:
            return SlotState.model_validate(raw)
        except Exception as exc:  # noqa: BLE001
            self.ctx.logger.warning("槽位运行快照解析失败，改从旧文件重建：%s", exc)
            return None

    def _guess_created_at(self, slot_id: str) -> str:
        candidates: list[float] = []
        slot_dir = self.ctx.get_slot_dir(slot_id)
        for path in slot_dir.glob("*.json"):
            try:
                candidates.append(path.stat().st_mtime)
            except OSError:
                continue
        if not candidates:
            return self._now_iso()
        return datetime.fromtimestamp(min(candidates)).isoformat(timespec="seconds")

    def _normalize_chat_history(self, history: list[dict[str, Any]]) -> list[SlotChatMessage]:
        items: list[SlotChatMessage] = []
        for item in history:
            if not isinstance(item, dict):
                continue
            items.append(
                SlotChatMessage(
                    role=str(item.get("role", "")).strip() or "user",
                    content=str(item.get("content", "")).strip(),
                    timestamp=str(item.get("created_at", "")).strip() or self._now_iso(),
                )
            )
        return items

    def _build_summary_buffer(
        self,
        *,
        slot_id: str,
        saved_state: SlotState | None,
        history: list[SlotChatMessage],
    ) -> SlotSummaryBuffer:
        if saved_state and saved_state.summary_buffer.content.strip():
            summary = saved_state.summary_buffer.model_copy(deep=True)
            if not summary.updated_at:
                summary.updated_at = self._now_iso()
            if summary.source_message_count <= 0:
                summary.source_message_count = len(history)
            return summary

        memories = self.ctx.get_memories(slot_id)
        summary_candidates: list[str] = []
        for item in memories[-6:]:
            if not isinstance(item, dict):
                continue
            tags = item.get("tags", [])
            normalized_tags = {str(tag).strip().lower() for tag in tags if str(tag).strip()}
            if {"auto-memory", "summary"} & normalized_tags:
                content = str(item.get("content", "")).strip()
                if content:
                    summary_candidates.append(content)
        summary_text = "\n\n".join(summary_candidates[-3:]).strip()
        return SlotSummaryBuffer(
            content=summary_text,
            updated_at=self._now_iso() if summary_text else "",
            source_message_count=len(history),
        )

    def _collect_preset_fragments(self, preset: dict[str, Any]) -> list[str]:
        fragments: list[str] = []
        base_prompt = str(preset.get("base_system_prompt", "")).strip()
        if base_prompt:
            fragments.append(base_prompt)
        extra_prompts = preset.get("extra_prompts", [])
        if isinstance(extra_prompts, list):
            for item in extra_prompts:
                if not isinstance(item, dict):
                    continue
                if not item.get("enabled", True):
                    continue
                content = str(item.get("content", "")).strip()
                if content:
                    fragments.append(content)
        return fragments

    def _build_active_preset(self, slot_id: str, settings: dict[str, Any]) -> SlotActivePreset:
        store = self.ctx.get_preset_store(slot_id)
        preset = self.ctx.get_active_preset_from_store(store)
        fragments = self._collect_preset_fragments(preset)
        return SlotActivePreset(
            preset_id=str(preset.get("id", "")).strip(),
            name=str(preset.get("name", "")).strip(),
            enabled=bool(preset.get("enabled", False)),
            generation_params={
                "temperature": settings.get("temperature", 0.85),
                "history_limit": settings.get("history_limit", 20),
                "request_timeout": settings.get("request_timeout", 120),
                "llm_model": settings.get("llm_model", ""),
            },
            system_prompt_filter="\n\n".join(fragments).strip(),
            prompt_fragments=fragments,
            modules=preset.get("modules", {}) if isinstance(preset.get("modules", {}), dict) else {},
        )

    def _build_variable_store(
        self,
        *,
        saved_state: SlotState | None,
        workshop_state: dict[str, Any],
    ) -> SlotVariableStore:
        base = (
            saved_state.environment_state.variable_store.model_dump()
            if saved_state
            else SlotVariableStore().model_dump()
        )
        temp = int(workshop_state.get("temp", 0) or 0)
        base.setdefault("favorability", 0.0)
        base["current_stage"] = str(base.get("current_stage", "")).strip().upper() or get_workshop_stage(temp)
        base.setdefault("virtual_time", "Day 1 08:00")
        base["workshop_temp"] = temp
        base["pending_workshop_temp"] = int(workshop_state.get("pending_temp", -1) or -1)
        return SlotVariableStore.model_validate(base)

    def _build_runtime_media(
        self,
        *,
        saved_state: SlotState | None,
        settings: dict[str, Any],
        current_card: dict[str, Any],
        workshop_state: dict[str, Any],
    ) -> SlotRuntimeMedia:
        base = (
            saved_state.environment_state.runtime_media.model_dump()
            if saved_state
            else SlotRuntimeMedia().model_dump()
        )
        base["background_image_url"] = str(settings.get("background_image_url", "")).strip()
        try:
            base["background_overlay"] = float(settings.get("background_overlay", base.get("background_overlay", 0.42)))
        except (TypeError, ValueError):
            base["background_overlay"] = 0.42

        raw_workshop = current_card.get("raw", {}).get("creativeWorkshop", {}) if isinstance(current_card, dict) else {}
        workshop = sanitize_creative_workshop(raw_workshop)
        temp = int(workshop_state.get("temp", 0) or 0)
        stage = get_workshop_stage(temp)
        match = select_workshop_match(workshop, temp=temp, stage=stage)
        if isinstance(match, dict):
            action_type = str(match.get("actionType", "")).strip().lower()
            if action_type == "music":
                base["bgm_url"] = str(match.get("musicUrl", "")).strip()
                base["bgm_preset"] = str(match.get("musicPreset", "")).strip()
                base["media_note"] = str(match.get("note", "")).strip()
            elif action_type == "image":
                image_url = str(match.get("imageUrl", "")).strip()
                if image_url:
                    base["media_note"] = str(match.get("note", "")).strip()
        return SlotRuntimeMedia.model_validate(base)

    def build_slot_state(self, slot_id: str | None = None, *, persist_snapshot: bool = False) -> SlotState:
        target_slot = self._slot_id(slot_id)
        saved_state = self._read_snapshot(target_slot)
        current_card = self.ctx.get_current_card(target_slot)
        history = self._normalize_chat_history(self.ctx.get_conversation(target_slot))
        settings = self.ctx.get_settings(target_slot)
        workshop_state = self.ctx.get_workshop_state(target_slot)

        created_at = (
            saved_state.metadata.created_at
            if saved_state and saved_state.metadata.created_at
            else self._guess_created_at(target_slot)
        )
        metadata = SlotMetadata(
            slot_id=target_slot,
            slot_name=self.ctx.get_slot_name(target_slot),
            created_at=created_at,
            last_updated=self._now_iso(),
            card_id=str(current_card.get("source_name", "")).strip(),
        )
        summary_buffer = self._build_summary_buffer(
            slot_id=target_slot,
            saved_state=saved_state,
            history=history,
        )
        environment_state = SlotEnvironmentState(
            active_preset=self._build_active_preset(target_slot, settings),
            variable_store=self._build_variable_store(saved_state=saved_state, workshop_state=workshop_state),
            runtime_media=self._build_runtime_media(
                saved_state=saved_state,
                settings=settings,
                current_card=current_card,
                workshop_state=workshop_state,
            ),
        )
        worldbook_context = (
            saved_state.worldbook_context.model_copy(deep=True)
            if saved_state
            else SlotWorldbookContext()
        )
        slot_state = SlotState(
            metadata=metadata,
            chat_history=history,
            summary_buffer=summary_buffer,
            environment_state=environment_state,
            worldbook_context=worldbook_context,
        )
        if persist_snapshot:
            self.persist_slot_state(slot_state)
        return slot_state

    def persist_slot_state(self, slot_state: SlotState) -> SlotState:
        self.ctx.persist_json(
            self.slot_state_path(slot_state.metadata.slot_id),
            slot_state.model_dump(mode="json"),
            detail="Slot runtime snapshot save failed. Please check disk space or file permissions.",
        )
        return slot_state

    def upsert_summary_buffer(self, payload: SlotSummaryBufferPayload) -> SlotState:
        slot_state = self.build_slot_state(payload.slot_id, persist_snapshot=False)
        slot_state.summary_buffer = SlotSummaryBuffer(
            content=str(payload.content or "").strip(),
            updated_at=self._now_iso(),
            source_message_count=payload.source_message_count or len(slot_state.chat_history),
        )
        slot_state.metadata.last_updated = self._now_iso()
        return self.persist_slot_state(slot_state)

    def patch_variable_store(self, payload: SlotVariablePatchPayload) -> SlotState:
        slot_state = self.build_slot_state(payload.slot_id, persist_snapshot=False)
        merged = slot_state.environment_state.variable_store.model_dump()
        merged.update(payload.variables or {})
        slot_state.environment_state.variable_store = SlotVariableStore.model_validate(merged)
        slot_state.metadata.last_updated = self._now_iso()
        return self.persist_slot_state(slot_state)

    def _match_aliases(
        self,
        query_text: str,
        aliases: list[str],
        *,
        mode: str,
        case_sensitive: bool,
        whole_word: bool,
    ) -> tuple[bool, list[str]]:
        if not aliases:
            return True, []
        hits = [
            alias
            for alias in aliases
            if keyword_matches_query(
                query_text,
                alias,
                case_sensitive=case_sensitive,
                whole_word=whole_word,
            )
        ]
        if mode == "all":
            return len(hits) == len(aliases), hits
        return bool(hits), hits

    def resolve_dynamic_worldbook_context(self, payload: DynamicWorldbookPreviewPayload) -> dict[str, Any]:
        target_slot = self._slot_id(payload.slot_id)
        slot_state = self.build_slot_state(target_slot, persist_snapshot=False)
        worldbook_store = sanitize_worldbook_store(self.ctx.get_worldbook_store(target_slot))
        settings = worldbook_store["settings"]
        if not settings.get("enabled", True):
            return {
                "slot_state": slot_state.model_dump(mode="json"),
                "matched_entries": [],
                "prompt": "",
            }

        recent_window = max(1, min(48, int(payload.recent_window or 12)))
        recent_messages = slot_state.chat_history[-recent_window:]
        recent_text = "\n".join(item.content for item in recent_messages if item.content.strip())
        summary_text = slot_state.summary_buffer.content.strip()
        current_message = str(payload.message or "").strip()
        query_text = "\n".join(part for part in (recent_text, summary_text, current_message) if part)

        unlocked = set(slot_state.worldbook_context.unlocked_entry_ids)
        candidates: list[tuple[tuple[int, int, int, str], dict[str, Any], list[str]]] = []
        for entry in worldbook_store["entries"]:
            if not entry.get("enabled", True):
                continue

            primary_aliases = split_trigger_aliases(entry.get("trigger", ""))
            secondary_aliases = split_trigger_aliases(entry.get("secondary_trigger", ""))
            primary_mode = str(entry.get("match_mode", "any")).strip().lower()
            secondary_mode = str(entry.get("secondary_mode", "all")).strip().lower()
            case_sensitive = bool(entry.get("case_sensitive", False))
            whole_word = bool(entry.get("whole_word", False))

            primary_ok, primary_hits = self._match_aliases(
                query_text,
                primary_aliases,
                mode=primary_mode,
                case_sensitive=case_sensitive,
                whole_word=whole_word,
            )
            if not primary_ok:
                continue

            secondary_ok, secondary_hits = self._match_aliases(
                query_text,
                secondary_aliases,
                mode=secondary_mode,
                case_sensitive=case_sensitive,
                whole_word=whole_word,
            )
            if not secondary_ok:
                continue

            current_ok, current_hits = self._match_aliases(
                current_message,
                primary_aliases,
                mode="any",
                case_sensitive=case_sensitive,
                whole_word=whole_word,
            )
            matched_terms = []
            for token in [*primary_hits, *secondary_hits, *current_hits]:
                if token and token not in matched_terms:
                    matched_terms.append(token)

            priority = int(entry.get("priority", 100) or 100)
            unlocked_bonus = 1 if str(entry.get("id", "")).strip() in unlocked else 0
            current_bonus = 1 if current_ok else 0
            score = (-current_bonus, -unlocked_bonus, priority, str(entry.get("id", "")).strip())
            candidates.append((score, entry, matched_terms))

        max_hits = max(1, min(20, int(settings.get("max_hits", 3) or 3)))
        matched_entries = [item for _, item, _ in sorted(candidates, key=lambda row: row[0])[:max_hits]]
        matched_terms: list[str] = []
        for _, _, terms in sorted(candidates, key=lambda row: row[0])[:max_hits]:
            for term in terms:
                if term not in matched_terms:
                    matched_terms.append(term)

        slot_state.worldbook_context.active_entry_ids = [
            str(item.get("id", "")).strip()
            for item in matched_entries
            if str(item.get("id", "")).strip()
        ]
        slot_state.worldbook_context.unlocked_entry_ids = [
            entry_id
            for entry_id in [*slot_state.worldbook_context.unlocked_entry_ids, *slot_state.worldbook_context.active_entry_ids]
            if entry_id
        ]
        slot_state.worldbook_context.unlocked_entry_ids = list(dict.fromkeys(slot_state.worldbook_context.unlocked_entry_ids))
        slot_state.worldbook_context.last_trigger_terms = matched_terms
        slot_state.worldbook_context.last_injected_at = self._now_iso() if matched_entries else ""
        slot_state.metadata.last_updated = self._now_iso()
        self.persist_slot_state(slot_state)

        prompt_lines: list[str] = []
        if matched_entries:
            prompt_lines.append("Inject the following slot-triggered worldbook facts only when they are relevant.")
            for index, item in enumerate(matched_entries, start=1):
                title = str(item.get("title", "")).strip() or str(item.get("trigger", "")).strip()
                content = str(item.get("content", "")).strip()
                prompt_lines.append(f"{index}. {title}: {content}")

        return {
            "slot_state": slot_state.model_dump(mode="json"),
            "matched_entries": matched_entries,
            "matched_entry_ids": slot_state.worldbook_context.active_entry_ids,
            "matched_terms": matched_terms,
            "prompt": "\n".join(prompt_lines).strip(),
        }

    def build_slot_injection_payload(self, payload: DynamicWorldbookPreviewPayload) -> dict[str, Any]:
        worldbook_payload = self.resolve_dynamic_worldbook_context(payload)
        slot_state = SlotState.model_validate(worldbook_payload["slot_state"])
        preset_filter = slot_state.environment_state.active_preset.system_prompt_filter.strip()
        summary_text = slot_state.summary_buffer.content.strip()

        system_sections: list[str] = []
        if preset_filter:
            system_sections.append(f"[Preset Override]\n{preset_filter}")
        if summary_text:
            system_sections.append(f"[Summary Buffer]\n{summary_text}")
        if worldbook_payload["prompt"]:
            system_sections.append(f"[Dynamic Worldbook]\n{worldbook_payload['prompt']}")

        return {
            "slot_state": slot_state.model_dump(mode="json"),
            "matched_entries": worldbook_payload["matched_entries"],
            "matched_entry_ids": worldbook_payload["matched_entry_ids"],
            "system_sections": system_sections,
            "prompt": "\n\n".join(section for section in system_sections if section).strip(),
        }

    def _resolve_fork_target(self, source_slot_id: str, preferred_target: str = "") -> str:
        target = self._slot_id(preferred_target or source_slot_id)
        if target != source_slot_id:
            return target
        for item in self.ctx.get_slot_registry()["slots"]:
            slot_id = self._slot_id(item.get("id", ""))
            if slot_id != source_slot_id:
                return slot_id
        raise ValueError("No available target slot for forking.")

    def _rename_slot_if_needed(self, slot_id: str, target_name: str) -> None:
        next_name = str(target_name or "").strip()
        if not next_name:
            return
        registry = deepcopy(self.ctx.get_slot_registry())
        for item in registry.get("slots", []):
            if item.get("id") == slot_id:
                item["name"] = next_name[:32]
                break
        self.ctx.save_slot_registry(registry)

    def fork_slot(self, payload: SlotForkPayload) -> SlotState:
        source_slot_id = self._slot_id(payload.source_slot_id)
        target_slot_id = self._resolve_fork_target(source_slot_id, payload.target_slot_id)
        source_state = self.build_slot_state(source_slot_id, persist_snapshot=True)
        forked_state = SlotState.model_validate(source_state.model_dump(mode="python"))

        if payload.chat_index is not None:
            limit = max(0, min(int(payload.chat_index), len(forked_state.chat_history)))
            forked_state.chat_history = forked_state.chat_history[:limit]
            if forked_state.summary_buffer.source_message_count > limit:
                forked_state.summary_buffer.source_message_count = limit

        self.ctx.persist_json(
            self.ctx.conversation_path(target_slot_id),
            [
                {"role": item.role, "content": item.content, "created_at": item.timestamp}
                for item in forked_state.chat_history
            ],
            detail="Slot fork failed while copying chat history.",
        )
        self.ctx.persist_json(
            self.ctx.settings_path(target_slot_id),
            self.ctx.sanitize_settings(self.ctx.get_settings(source_slot_id), slot_id=target_slot_id),
            detail="Slot fork failed while copying settings.",
        )
        self.ctx.save_memories(self.ctx.get_memories(source_slot_id), target_slot_id)
        self.ctx.save_worldbook_store(self.ctx.get_worldbook_store(source_slot_id), target_slot_id)
        self.ctx.persist_json(
            self.ctx.user_profile_path(target_slot_id),
            self.ctx.get_user_profile(source_slot_id),
            detail="Slot fork failed while copying user profile.",
        )
        self.ctx.save_workshop_state(self.ctx.get_workshop_state(source_slot_id), target_slot_id)
        self.ctx.save_preset_store(self.ctx.get_preset_store(source_slot_id), target_slot_id)

        self._rename_slot_if_needed(target_slot_id, payload.target_name)
        forked_state.metadata.slot_id = target_slot_id
        forked_state.metadata.slot_name = self.ctx.get_slot_name(target_slot_id)
        forked_state.metadata.created_at = self._now_iso()
        forked_state.metadata.last_updated = self._now_iso()
        self.persist_slot_state(forked_state)
        return self.build_slot_state(target_slot_id, persist_snapshot=True)

    def export_campaign_bundle(self, slot_id: str | None = None) -> ScenarioBundle:
        target_slot = self._slot_id(slot_id)
        slot_state = self.build_slot_state(target_slot, persist_snapshot=True)
        current_card = self.ctx.get_current_card(target_slot)
        return ScenarioBundle(
            version=1,
            bundle_type="campaign",
            exported_at=self._now_iso(),
            card_id=str(current_card.get("source_name", "")).strip(),
            card_payload=self.ctx.normalize_role_card(current_card.get("raw", {})),
            worldbook_asset=self.ctx.get_worldbook_store(target_slot),
            slot_state=slot_state,
            seed_memories=self.ctx.get_memories(target_slot),
            settings_payload=self.ctx.get_settings(target_slot),
            preset_store=self.ctx.get_preset_store(target_slot),
            user_profile=self.ctx.get_user_profile(target_slot),
            workshop_state=self.ctx.get_workshop_state(target_slot),
        )

    def import_campaign_bundle(self, bundle: ScenarioBundle, *, target_slot_id: str, load_card: bool = True) -> SlotState:
        target_slot = self._slot_id(target_slot_id)
        self.ctx.persist_json(
            self.ctx.settings_path(target_slot),
            self.ctx.sanitize_settings(bundle.settings_payload, slot_id=target_slot),
            detail="Campaign import failed while applying slot settings.",
        )
        self.ctx.save_memories([item.model_dump() for item in bundle.seed_memories], target_slot)
        self.ctx.save_worldbook_store(bundle.worldbook_asset, target_slot)
        self.ctx.persist_json(
            self.ctx.user_profile_path(target_slot),
            bundle.user_profile,
            detail="Campaign import failed while applying user profile.",
        )
        self.ctx.save_workshop_state(bundle.workshop_state, target_slot)
        self.ctx.save_preset_store(bundle.preset_store, target_slot)

        imported_state = SlotState.model_validate(bundle.slot_state.model_dump(mode="python"))
        imported_state.metadata.slot_id = target_slot
        imported_state.metadata.slot_name = self.ctx.get_slot_name(target_slot)
        imported_state.metadata.created_at = self._now_iso()
        imported_state.metadata.last_updated = self._now_iso()
        self.ctx.persist_json(
            self.ctx.conversation_path(target_slot),
            [
                {"role": item.role, "content": item.content, "created_at": item.timestamp}
                for item in imported_state.chat_history
            ],
            detail="Campaign import failed while applying chat history.",
        )
        self.persist_slot_state(imported_state)

        if load_card and bundle.card_payload:
            filename = Path(str(bundle.card_id or "campaign_card.json").strip() or "campaign_card.json").name
            if not filename.lower().endswith(".json"):
                filename += ".json"
            self.ctx.persist_json(
                self.ctx.CARDS_DIR / filename,
                self.ctx.normalize_role_card(bundle.card_payload),
                detail="Campaign import failed while saving the bundled card file.",
            )
            self.ctx.apply_role_card(bundle.card_payload, source_name=filename, slot_id=target_slot)

        return self.build_slot_state(target_slot, persist_snapshot=True)

    def import_campaign_bundle_json(self, raw_json: str, *, target_slot_id: str, load_card: bool = True) -> SlotState:
        data = json.loads(str(raw_json or "").strip())
        bundle = ScenarioBundle.model_validate(data)
        return self.import_campaign_bundle(bundle, target_slot_id=target_slot_id, load_card=load_card)
