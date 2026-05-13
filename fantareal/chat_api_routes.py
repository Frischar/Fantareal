import json
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from .app_models import ChatHistoryEditRequest, ChatHistoryRerollRequest, ChatRequest, SlotSummaryBufferPayload


def register_chat_api_routes(app: FastAPI, *, ctx: Any) -> None:
    @app.get("/api/history")
    async def api_get_history() -> list[dict[str, Any]]:
        return ctx.get_conversation()


    @app.post("/api/chat/history/message-meta")
    async def api_patch_message_metadata(payload: dict[str, Any]) -> dict[str, Any]:
        """Persist client-side chat message identity for mod hooks.

        The streaming endpoint saves chat history after the final SSE event. The
        browser already knows the stable turn/message identity used by mods, so
        it patches the latest user/assistant pair after the turn completes.
        """
        history = ctx.get_conversation()
        if not history:
            return {"ok": False, "reason": "empty_history", "patched": 0}

        turn_id = str(payload.get("turn_id") or payload.get("turnId") or "").strip()
        turn_index_raw = payload.get("turn_index", payload.get("turnIndex", 0))
        try:
            turn_index = int(turn_index_raw)
        except (TypeError, ValueError):
            turn_index = 0
        user_text = str(payload.get("user_text") or payload.get("userText") or "").strip()
        assistant_text = str(payload.get("assistant_text") or payload.get("assistantText") or "").strip()
        user_message_id = str(payload.get("user_message_id") or payload.get("userMessageId") or "").strip()
        assistant_message_id = str(payload.get("assistant_message_id") or payload.get("assistantMessageId") or payload.get("message_id") or payload.get("messageId") or "").strip()
        content_hash = str(payload.get("content_hash") or payload.get("contentHash") or payload.get("assistant_hash") or payload.get("assistantHash") or "").strip()
        user_hash = str(payload.get("user_hash") or payload.get("userHash") or "").strip()
        assistant_hash = str(payload.get("assistant_hash") or payload.get("assistantHash") or content_hash or "").strip()
        assistant_clean_text = str(payload.get("assistant_clean_text") or payload.get("assistantCleanText") or "").strip()
        source = str(payload.get("source") or payload.get("trigger_source") or payload.get("triggerSource") or "chat_hook").strip()

        def same_text(left: str, right: str) -> bool:
            return str(left or "").strip() == str(right or "").strip()

        assistant_index = -1
        if assistant_text:
            for idx in range(len(history) - 1, -1, -1):
                item = history[idx]
                if item.get("role") == "assistant" and same_text(item.get("content", ""), assistant_text):
                    assistant_index = idx
                    break
        if assistant_index < 0:
            for idx in range(len(history) - 1, -1, -1):
                if history[idx].get("role") == "assistant":
                    assistant_index = idx
                    break

        user_index = -1
        if assistant_index >= 0:
            for idx in range(assistant_index - 1, -1, -1):
                item = history[idx]
                if item.get("role") != "user":
                    continue
                if user_text and not same_text(item.get("content", ""), user_text):
                    continue
                user_index = idx
                break
            if user_index < 0:
                for idx in range(assistant_index - 1, -1, -1):
                    if history[idx].get("role") == "user":
                        user_index = idx
                        break

        patched = 0
        if user_index >= 0:
            user_item = dict(history[user_index])
            if user_message_id:
                user_item["message_id"] = user_message_id
            if turn_id:
                user_item["turn_id"] = turn_id
                user_item["state_journal_turn"] = turn_id
            if turn_index > 0:
                user_item["turn_index"] = turn_index
            if user_hash:
                user_item["content_hash"] = user_hash
                user_item["user_hash"] = user_hash
            if source:
                user_item["source"] = source
            history[user_index] = user_item
            patched += 1

        if assistant_index >= 0:
            assistant_item = dict(history[assistant_index])
            if assistant_message_id:
                assistant_item["message_id"] = assistant_message_id
            if turn_id:
                assistant_item["turn_id"] = turn_id
                assistant_item["state_journal_turn"] = turn_id
            if turn_index > 0:
                assistant_item["turn_index"] = turn_index
            if content_hash:
                assistant_item["content_hash"] = content_hash
                assistant_item["assistant_hash"] = assistant_hash or content_hash
            if assistant_text:
                assistant_item["raw_content"] = assistant_text
            if assistant_clean_text:
                assistant_item["assistant_clean_text"] = assistant_clean_text
            if source:
                assistant_item["source"] = source
            history[assistant_index] = assistant_item
            patched += 1

        if patched:
            ctx.persist_json(
                ctx.conversation_path(),
                history,
                detail="Chat message metadata save failed. Please check disk space or file permissions.",
            )
        return {
            "ok": bool(patched),
            "patched": patched,
            "user_index": user_index,
            "assistant_index": assistant_index,
            "turn_id": turn_id,
            "message_id": assistant_message_id,
            "content_hash": content_hash,
        }


    @app.post("/api/chat/history/edit-user")
    async def api_edit_user_message(payload: ChatHistoryEditRequest) -> dict[str, Any]:
        history = ctx.get_conversation()
        index = int(payload.message_index)
        if index < 0 or index >= len(history):
            raise HTTPException(status_code=404, detail="找不到要编辑的消息。")

        item = history[index]
        if item.get("role") != "user":
            raise HTTPException(status_code=400, detail="只能编辑用户消息。")

        content = str(payload.content or "").strip()
        if not content:
            raise HTTPException(status_code=400, detail="编辑后的消息不能为空。")

        ctx.persist_json(
            ctx.conversation_path(),
            history[:index],
            detail="Chat history edit failed. Please check disk space or file permissions.",
        )
        return {
            "ok": True,
            "message": content,
            "trimmed_from": index,
            "removed_count": len(history) - index,
        }

    @app.post("/api/chat/history/reroll")
    async def api_reroll_assistant_message(payload: ChatHistoryRerollRequest) -> dict[str, Any]:
        history = ctx.get_conversation()
        index = int(payload.message_index)
        if index < 0 or index >= len(history):
            raise HTTPException(status_code=404, detail="找不到要重 roll 的消息。")

        item = history[index]
        role = item.get("role")
        if role == "user":
            user_index = index
        elif role == "assistant":
            user_index = -1
            for cursor in range(index - 1, -1, -1):
                if history[cursor].get("role") == "user":
                    user_index = cursor
                    break
            if user_index < 0:
                raise HTTPException(status_code=400, detail="这条回复前没有可用于重 roll 的用户消息。")
        else:
            raise HTTPException(status_code=400, detail="只能从用户消息或助手回复开始重 roll。")

        message = str(history[user_index].get("content", "")).strip()
        if not message:
            raise HTTPException(status_code=400, detail="原用户消息为空，无法重 roll。")

        ctx.persist_json(
            ctx.conversation_path(),
            history[:user_index],
            detail="Chat history reroll failed. Please check disk space or file permissions.",
        )
        return {
            "ok": True,
            "message": message,
            "trimmed_from": user_index,
            "source_index": index,
            "removed_count": len(history) - user_index,
        }

    @app.post("/api/chat")
    async def api_chat(payload: ChatRequest) -> dict[str, Any]:
        message = payload.message.strip()
        if not message:
            raise HTTPException(status_code=400, detail="Message cannot be empty.")

        runtime_overrides = payload.runtime_config or {}
        (
            reply_result,
            retrieved_items,
            worldbook_matches,
            prompt_package,
            worldbook_debug_snapshot,
        ) = await ctx.generate_reply(message, runtime_overrides)
        reply = str(reply_result.get("reply", ""))
        entries = [("user", message)]
        if reply.strip():
            entries.append(("assistant", reply))
        ctx.append_messages(entries)

        worldbook_debug = ctx.build_worldbook_debug_payload(
            message,
            worldbook_matches,
            reply_result=reply_result,
            debug_snapshot=worldbook_debug_snapshot,
        )
        preset_debug = ctx.build_preset_debug_payload()

        return {
            "reply": reply,
            "retrieved_items": retrieved_items,
            "worldbook_hits": worldbook_matches,
            "worldbook_debug": worldbook_debug,
            "sprite_tag": reply_result.get("sprite_tag", ""),
            "memory_item": None,
            "preset_debug": preset_debug,
            "prompt_package": prompt_package,
        }

    @app.post("/api/chat/prompt-preview")
    async def api_chat_prompt_preview(payload: ChatRequest) -> dict[str, Any]:
        message = payload.message.strip()
        if not message:
            raise HTTPException(status_code=400, detail="Message cannot be empty.")

        runtime_overrides = payload.runtime_config or {}
        retrieved_items = await ctx.retrieve_memories(message, runtime_overrides)
        worldbook_matches = ctx.match_worldbook_entries(message)
        worldbook_debug_snapshot = ctx.get_worldbook_debug_snapshot()
        prompt_package = ctx.build_prompt_package(
            message,
            retrieved_items,
            runtime_overrides=runtime_overrides,
            worldbook_matches=worldbook_matches,
        )
        return {
            "retrieved_items": retrieved_items,
            "worldbook_hits": worldbook_matches,
            "worldbook_debug": ctx.build_worldbook_debug_payload(
                message,
                worldbook_matches,
                debug_snapshot=worldbook_debug_snapshot,
            ),
            "preset_debug": ctx.build_preset_debug_payload(),
            "prompt_package": prompt_package,
        }

    @app.post("/api/chat/stream")
    async def api_chat_stream(payload: ChatRequest) -> StreamingResponse:
        message = payload.message.strip()
        if not message:
            raise HTTPException(status_code=400, detail="Message cannot be empty.")

        runtime_overrides = payload.runtime_config or {}
        llm_config = ctx.get_runtime_chat_config(runtime_overrides)
        retrieved_items = await ctx.retrieve_memories(message, runtime_overrides)
        worldbook_matches = ctx.match_worldbook_entries(message)
        worldbook_debug_snapshot = ctx.get_worldbook_debug_snapshot()
        worldbook_debug = ctx.build_worldbook_debug_payload(
            message,
            worldbook_matches,
            debug_snapshot=worldbook_debug_snapshot,
        )
        preset_debug = ctx.build_preset_debug_payload()
        prompt_package = ctx.build_prompt_package(
            message,
            retrieved_items,
            runtime_overrides=runtime_overrides,
            worldbook_matches=worldbook_matches,
        )

        if not (llm_config["base_url"] and llm_config["model"]):
            if not llm_config["demo_mode"]:
                raise HTTPException(
                    status_code=400,
                    detail="Please configure the chat model API URL and model name first, or enable demo mode.",
                )

            async def demo_event_stream():
                ctx.append_messages([("user", message)])
                meta = {
                    "type": "meta",
                    "retrieved_items": retrieved_items,
                    "worldbook_hits": worldbook_matches,
                    "worldbook_debug": worldbook_debug,
                    "preset_debug": preset_debug,
                    "prompt_package": prompt_package,
                }
                yield f"data: {json.dumps(meta, ensure_ascii=False)}\n\n"
                done = {"type": "done", "reply": "", "sprite_tag": "", "worldbook_enforced": False}
                yield f"data: {json.dumps(done, ensure_ascii=False)}\n\n"

            return StreamingResponse(demo_event_stream(), media_type="text/event-stream")

        async def event_stream():
            meta = {
                "type": "meta",
                "retrieved_items": retrieved_items,
                "worldbook_hits": worldbook_matches,
                "worldbook_debug": worldbook_debug,
                "preset_debug": preset_debug,
                "prompt_package": prompt_package,
            }
            yield f"data: {json.dumps(meta, ensure_ascii=False)}\n\n"

            final_reply_result: dict[str, Any] | None = None
            try:
                async for item in ctx.stream_model_reply(
                    message,
                    retrieved_items,
                    runtime_overrides=runtime_overrides,
                    worldbook_matches=worldbook_matches,
                    prompt_package=prompt_package,
                ):
                    if item.get("type") == "done":
                        final_reply_result = item
                    yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
            except HTTPException as exc:
                error_event = {"type": "error", "detail": exc.detail if isinstance(exc.detail, str) else str(exc.detail)}
                yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
                return
            except Exception as exc:
                ctx.logger.exception("Stream reply failed")
                error_event = {"type": "error", "detail": str(exc)}
                yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
                return

            reply_text = str((final_reply_result or {}).get("reply", "")).strip()
            stored_reply_text = str((final_reply_result or {}).get("full_reply", "")).strip() or reply_text
            entries = [("user", message)]
            if stored_reply_text:
                entries.append(("assistant", stored_reply_text))
            ctx.append_messages(entries)

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.post("/api/conversation/end")
    async def api_end_conversation() -> dict[str, Any]:
        source_message_count = len(ctx.get_conversation(ctx.get_active_slot_id()))
        memory = await ctx.archive_current_conversation()
        if memory.get("_skipped"):
            return {"ok": True, "skipped": True}
        active_slot = ctx.get_active_slot_id()
        state = ctx.get_workshop_state(active_slot)
        state["temp"] = max(0, int(state.get("temp", 0) or 0) + 1)
        state["pending_temp"] = state["temp"]
        ctx.save_workshop_state(state, active_slot)
        slot_state = ctx.slot_runtime_service.upsert_summary_buffer(
            SlotSummaryBufferPayload(
                slot_id=active_slot,
                content=str(memory.get("content", "")).strip(),
                source_message_count=source_message_count,
            )
        )
        return {
            "ok": True,
            "memory_item": memory,
            "workshop_state": ctx.get_workshop_state(active_slot),
            "workshop_stage": ctx.get_workshop_stage(state.get("temp", 0)),
            "slot": slot_state.model_dump(mode="json"),
        }

    @app.post("/api/reset")
    async def api_reset() -> dict[str, Any]:
        ctx.reset_workshop_state()
        ctx.persist_json(
            ctx.conversation_path(),
            [],
            detail="Chat history clear failed. Please check disk space or file permissions.",
        )
        return {"ok": True}

    @app.get("/api/export/history")
    async def api_export_history() -> FileResponse:
        slot_id = ctx.get_active_slot_id()
        history = ctx.get_conversation(slot_id)
        ctx.EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        export_path = ctx.EXPORT_DIR / "chat_history_export.json"
        ctx.persist_json(
            export_path,
            history,
            detail="Chat history export failed. Please check disk space or file permissions.",
        )
        return FileResponse(
            path=export_path,
            filename="chat_history_export.json",
            media_type="application/json",
        )
