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
