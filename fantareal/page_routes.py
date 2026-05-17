import importlib.util
import json
import sys
import types
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request


def register_page_routes(app: FastAPI, *, templates: Any, ctx: Any) -> None:
    challenge_cards_dir = Path(__file__).resolve().parent.parent / "challenge_cards"

    def _read_challenge_card_json(filename: str) -> dict[str, Any]:
        target = challenge_cards_dir / filename
        try:
            with target.open("r", encoding="utf-8-sig") as handle:
                payload = json.load(handle)
        except OSError as exc:
            raise HTTPException(status_code=500, detail=f"挑战模式四卡缺失：{filename}") from exc
        except ValueError as exc:
            raise HTTPException(status_code=500, detail=f"挑战模式四卡 JSON 解析失败：{filename}") from exc
        if not isinstance(payload, dict):
            raise HTTPException(status_code=500, detail=f"挑战模式四卡格式错误：{filename}")
        return payload

    def _apply_challenge_four_cards() -> None:
        active_slot = ctx.get_active_slot_id()
        card_filename = "绪亓的人设.json"
        card = _read_challenge_card_json(card_filename)
        memories = _read_challenge_card_json("绪亓的记忆.json")
        worldbook = _read_challenge_card_json("绪亓的世界书.json")
        preset = _read_challenge_card_json("绪亓的预设.json")

        try:
            ctx.CARDS_DIR.mkdir(parents=True, exist_ok=True)
            ctx.persist_json(
                ctx.CARDS_DIR / card_filename,
                ctx.normalize_role_card(card),
                detail="挑战模式人设卡保存失败。",
            )
            ctx.apply_role_card(card, source_name=card_filename, slot_id=active_slot)
            ctx.save_memories(memories.get("items", []), active_slot)
            ctx.save_worldbook_store(worldbook, active_slot)
            ctx.save_preset_store(preset, active_slot)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"挑战模式四卡加载失败：{exc}") from exc

    def _opening_message_from_persona(persona: dict[str, Any]) -> str:
        if not isinstance(persona, dict):
            return ""
        return str(
            persona.get("opening_message")
            or persona.get("first_mes")
            or persona.get("first_message")
            or persona.get("greeting")
            or ""
        ).strip()

    def _summary_buffer_content(slot_id: str | None = None) -> str:
        service = getattr(ctx, "slot_runtime_service", None)
        if service is None or not hasattr(service, "build_slot_state"):
            return ""
        try:
            slot_state = service.build_slot_state(slot_id, persist_snapshot=False)
            summary_buffer = getattr(slot_state, "summary_buffer", None)
            if summary_buffer is None:
                return ""
            if isinstance(summary_buffer, dict):
                return str(summary_buffer.get("content", "") or "").strip()
            return str(getattr(summary_buffer, "content", "") or "").strip()
        except Exception:
            # 开场白只是 UI 展示，不应因为运行时快照读取异常影响聊天页打开。
            return ""

    def _has_workshop_progress(workshop_state: dict[str, Any]) -> bool:
        if not isinstance(workshop_state, dict):
            return False
        try:
            temp = int(workshop_state.get("temp", 0) or 0)
        except (TypeError, ValueError):
            temp = 0
        trigger_history = workshop_state.get("trigger_history", [])
        return temp > 0 or (isinstance(trigger_history, list) and len(trigger_history) > 0)

    def _should_show_opening_message(
        *,
        opening_message: str,
        history: list[dict[str, Any]],
        memories: list[dict[str, Any]],
        summary_buffer: str,
        workshop_state: dict[str, Any],
    ) -> bool:
        return bool(
            opening_message
            and not history
            and not memories
            and not summary_buffer
            and not _has_workshop_progress(workshop_state)
        )

    def _should_show_workshop_opening(
        *,
        opening: dict[str, Any],
        history: list[dict[str, Any]],
        memories: list[dict[str, Any]],
        summary_buffer: str,
        workshop_state: dict[str, Any],
    ) -> bool:
        return bool(
            isinstance(opening, dict)
            and opening.get("enabled") is True
            and not history
            and not memories
            and not summary_buffer
            and not _has_workshop_progress(workshop_state)
        )

    def build_chat_template_context() -> dict[str, Any]:
        active_slot = ctx.get_active_slot_id() if hasattr(ctx, "get_active_slot_id") else None
        persona = ctx.get_persona()
        history = ctx.get_conversation()
        memories = ctx.get_memories()
        workshop_state = ctx.get_workshop_state(active_slot) if active_slot is not None else ctx.get_workshop_state()
        current_card = ctx.get_current_card(active_slot) if active_slot is not None else ctx.get_current_card()
        creative_workshop = ctx.sanitize_creative_workshop(current_card.get("raw", {}).get("creativeWorkshop", {}))
        workshop_opening = creative_workshop.get("opening", {}) if isinstance(creative_workshop, dict) else {}
        workshop_ambience = creative_workshop.get("ambience", {}) if isinstance(creative_workshop, dict) else {}
        workshop_dynamic_scenes = creative_workshop.get("dynamicScenes", []) if isinstance(creative_workshop, dict) else []
        summary_buffer = _summary_buffer_content(active_slot)
        opening_message = _opening_message_from_persona(persona)
        show_opening_message = _should_show_opening_message(
            opening_message=opening_message,
            history=history,
            memories=memories,
            summary_buffer=summary_buffer,
            workshop_state=workshop_state,
        )
        preset_store = ctx.get_preset_store()
        active_preset = ctx.get_active_preset_from_store(preset_store)
        preset_debug = ctx.build_preset_debug_payload()
        return {
            "persona": persona,
            "history": history,
            "settings": ctx.get_settings(),
            "worldbook_settings": ctx.get_worldbook_settings(),
            "user_profile": ctx.get_user_profile(),
            "role_avatar_url": ctx.get_role_avatar_url(),
            "preset_store": preset_store,
            "active_preset": active_preset,
            "active_preset_modules": preset_debug["active_modules"],
            "preset_debug": preset_debug,
            "opening_message": opening_message,
            "show_opening_message": show_opening_message,
            "workshop_opening": workshop_opening,
            "workshop_ambience": workshop_ambience,
            "workshop_dynamic_scenes": workshop_dynamic_scenes,
            "workshop_state": workshop_state,
            "show_workshop_opening": _should_show_workshop_opening(
                opening=workshop_opening,
                history=history,
                memories=memories,
                summary_buffer=summary_buffer,
                workshop_state=workshop_state,
            ),
        }

    @app.get("/", include_in_schema=False)
    async def root_redirect() -> RedirectResponse:
        return RedirectResponse(url="/chat", status_code=307)

    @app.get("/chat", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "index.html",
            build_chat_template_context(),
        )

    @app.get("/config", response_class=HTMLResponse)
    async def config_page(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "config.html",
            {
                "settings": ctx.get_settings(),
                "memory_count": len(ctx.get_memories()),
                "current_card": ctx.get_current_card(),
            },
        )

    @app.get("/config/preset", response_class=HTMLResponse)
    async def preset_config_page(request: Request) -> HTMLResponse:
        preset_store = ctx.get_preset_store()
        active_preset = ctx.get_active_preset_from_store(preset_store)
        preset_modules = [
            {"key": key, "label": meta.get("label", key)}
            for key, meta in ctx.preset_module_rules.items()
        ]
        return templates.TemplateResponse(
            request,
            "preset.html",
            {
                "settings": ctx.get_settings(),
                "preset_store": preset_store,
                "active_preset": active_preset,
                "preset_count": len(preset_store.get("presets", [])),
                "preset_modules": preset_modules,
            },
        )

    @app.get("/config/user", response_class=HTMLResponse)
    async def user_config_page(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "user_config.html",
            {
                "settings": ctx.get_settings(),
                "user_profile": ctx.get_user_profile(),
            },
        )

    @app.get("/config/card", response_class=HTMLResponse)
    async def card_config_page(request: Request) -> HTMLResponse:
        current_card = ctx.get_current_card()
        workshop_state = ctx.get_workshop_state()
        card_template = ctx.normalize_role_card(
            current_card.get("normalized") or current_card.get("raw", {})
        )
        return templates.TemplateResponse(
            request,
            "card_config.html",
            {
                "settings": ctx.get_settings(),
                "cards": ctx.list_role_card_files(),
                "current_card": current_card,
                "card_template": card_template,
                "stage_items": list(card_template.get("plotStages", {}).items()),
                "persona_items": list(card_template.get("personas", {}).items()),
                "workshop_state": workshop_state,
                "workshop_stage": ctx.get_workshop_stage(workshop_state.get("temp", 0)),
            },
        )

    @app.get("/config/workshop", response_class=HTMLResponse)
    async def workshop_config_page(request: Request) -> HTMLResponse:
        current_card = ctx.get_current_card()
        workshop_state = ctx.get_workshop_state()
        card_template = ctx.normalize_role_card(
            current_card.get("normalized") or current_card.get("raw", {})
        )
        return templates.TemplateResponse(
            request,
            "workshop_config.html",
            {
                "settings": ctx.get_settings(),
                "current_card": current_card,
                "card_template": card_template,
                "workshop_state": workshop_state,
                "workshop_stage": ctx.get_workshop_stage(workshop_state.get("temp", 0)),
            },
        )

    @app.get("/config/route-forwarding", response_class=HTMLResponse)
    async def route_forwarding_config_page(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "route_forwarding_config.html",
            {
                "settings": ctx.get_settings(),
                "route_forwarding": ctx.get_route_forwarding_config(),
                "route_forwarding_stats": ctx.get_route_forwarding_runtime_stats(),
            },
        )

    @app.get("/config/memory", response_class=HTMLResponse)
    async def memory_config_page(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "memory_config.html",
            {
                "settings": ctx.get_settings(),
                "memories": ctx.get_memories(),
                "memory_count": len(ctx.get_memories()),
            },
        )

    @app.get("/config/worldbook", response_class=HTMLResponse)
    async def worldbook_config_page(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "worldbook_config.html",
            {
                "settings": ctx.get_settings(),
                "worldbook_settings": ctx.get_worldbook_settings(),
            },
        )

    @app.get("/config/worldbook/entries", response_class=HTMLResponse)
    async def worldbook_manager_page(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "worldbook_manager.html",
            {
                "settings": ctx.get_settings(),
                "worldbook_settings": ctx.get_worldbook_settings(),
                "worldbook_entries": ctx.get_worldbook_entries(),
                "worldbook_count": len(ctx.get_worldbook_entries()),
            },
        )

    @app.get("/config/sprite", response_class=HTMLResponse)
    async def sprite_config_page(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "sprite_config.html",
            {
                "settings": ctx.get_settings(),
                "sprites": ctx.list_sprite_assets(),
                "sprite_count": len(ctx.list_sprite_assets()),
                "sprite_base_path": ctx.default_sprite_base_path_for_slot(),
                "role_avatar_url": ctx.get_role_avatar_url(),
            },
        )

    @app.get("/config/about", response_class=HTMLResponse)
    async def about_config_page(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "about.html",
            {
                "settings": ctx.get_settings(),
            },
        )

    @app.get("/mods/challenge-mode", response_class=HTMLResponse)
    async def challenge_mode_page(request: Request) -> HTMLResponse:
        _apply_challenge_four_cards()
        return templates.TemplateResponse(
            request,
            "challenge_mode.html",
            {
                "settings": ctx.get_settings(),
            },
        )

    @app.post("/api/challenge-mode/clear")
    async def clear_challenge_mode_cards() -> dict[str, Any]:
        active_slot = ctx.get_active_slot_id()
        try:
            ctx.apply_role_card({}, source_name="", slot_id=active_slot)
            ctx.save_memories([], active_slot)
            ctx.save_worldbook_store({}, active_slot)
            ctx.save_preset_store(ctx.sanitize_preset_store({}), active_slot)
            ctx.reset_workshop_state(active_slot)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"挑战模式四卡清空失败：{exc}") from exc
        return {"ok": True}

    _game_dir = Path(__file__).resolve().parent.parent / "game" / "Tea Party"

    def _setup_tea_party() -> types.ModuleType:
        if "tea_party" in sys.modules:
            return sys.modules["tea_party"]

        tp = types.ModuleType("tea_party")
        tp.__path__ = [str(_game_dir)]
        tp.__package__ = "tea_party"
        sys.modules["tea_party"] = tp

        for mod_name, filename in [
            ("tea_party.models", "models.py"),
            ("tea_party.engine", "engine.py"),
            ("tea_party.ai_instructions", "ai_instructions.py"),
            ("tea_party.ai_opponent", "ai_opponent.py"),
        ]:
            spec = importlib.util.spec_from_file_location(mod_name, _game_dir / filename)
            if spec is None or spec.loader is None:
                raise HTTPException(status_code=500, detail=f"游戏模块加载失败：{filename}")
            mod = importlib.util.module_from_spec(spec)
            mod.__package__ = "tea_party"
            sys.modules[mod_name] = mod
            spec.loader.exec_module(mod)

        for mn in ["tea_party.models", "tea_party.engine"]:
            m = sys.modules[mn]
            for attr in dir(m):
                if not attr.startswith("_"):
                    setattr(tp, attr, getattr(m, attr))
        return tp

    def _get_game_or_404(tp: types.ModuleType) -> Any:
        game = tp.get_session()
        if game is None:
            raise HTTPException(status_code=404, detail="没有活跃的游戏，请先开始新游戏。")
        return game

    _pictures_dir = _game_dir / "pictures"
    if _pictures_dir.is_dir():
        app.mount("/game/pictures", StaticFiles(directory=str(_pictures_dir)), name="game_pictures")
    _sounds_dir = _game_dir / "sounds"
    if _sounds_dir.is_dir():
        app.mount("/game/Tea Party/sounds", StaticFiles(directory=str(_sounds_dir)), name="game_sounds")

    @app.get("/game", response_class=HTMLResponse)
    async def game_page(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "game.html",
            {
                "settings": ctx.get_settings(),
                "role_avatar_url": ctx.get_role_avatar_url(),
            },
        )

    @app.get("/api/game/state")
    async def game_state() -> dict[str, Any]:
        tp = _setup_tea_party()
        game = tp.get_session()
        if game is None:
            return {"phase": "none"}
        return game.get_state()

    @app.post("/api/game/new")
    async def game_new(request: Request) -> dict[str, Any]:
        tp = _setup_tea_party()
        body = await request.json()
        mode = body.get("mode", "classic")
        difficulty = body.get("difficulty", "normal")
        p1_name = body.get("p1_name", "你")

        persona = ctx.get_persona()
        p2_name = persona.get("name", "对手") if persona else "对手"

        game = tp.reset_session(mode=mode, difficulty=difficulty, p1_name=p1_name, p2_name=p2_name)
        return game.get_state()

    @app.post("/api/game/shoot")
    async def game_shoot(request: Request) -> dict[str, Any]:
        tp = _setup_tea_party()
        game = _get_game_or_404(tp)
        body = await request.json()
        result = game.shoot(body["player_index"], body["target"])
        d = result.to_dict()
        if result.success and result.phase != tp.GamePhase.GAME_OVER:
            d["ai_extra_turn"] = False
        return d

    @app.post("/api/game/skip-turn")
    async def game_skip_turn(request: Request) -> dict[str, Any]:
        tp = _setup_tea_party()
        game = _get_game_or_404(tp)
        body = await request.json()
        result = game.skip_turn(body["player_index"])
        return result.to_dict()

    @app.post("/api/game/use-item")
    async def game_use_item(request: Request) -> dict[str, Any]:
        tp = _setup_tea_party()
        game = _get_game_or_404(tp)
        body = await request.json()
        target = body.get("target_item_type", None)
        result = game.use_item(body["player_index"], body["item_type"], target)
        return result.to_dict()

    @app.post("/api/game/discard-item")
    async def game_discard_item(request: Request) -> dict[str, Any]:
        tp = _setup_tea_party()
        game = _get_game_or_404(tp)
        body = await request.json()
        result = game.discard_item(body["player_index"], body["item_type"])
        return result.to_dict()

    @app.get("/api/game/check-ready")
    async def game_check_ready() -> dict[str, Any]:
        llm_config = ctx.get_runtime_chat_config()
        persona = ctx.get_persona()
        model_ok = bool(llm_config.get("model", ""))
        persona_ok = bool(persona and persona.get("system_prompt", ""))
        return {
            "model_ready": model_ok,
            "persona_ready": persona_ok,
            "model_name": llm_config.get("model", ""),
            "persona_name": persona.get("name", "") if persona else "",
        }

    @app.post("/api/game/reset")
    async def game_reset() -> dict[str, Any]:
        tp = _setup_tea_party()
        tp.reset_session(mode="classic", difficulty="normal", p1_name="玩家", p2_name="对手")
        engine_mod = sys.modules.get("tea_party.engine")
        if engine_mod:
            engine_mod._active_game = None  # type: ignore[attr-defined]
        return {"ok": True}

    @app.post("/api/game/no-ai-turn")
    async def game_no_ai_turn(request: Request) -> dict[str, Any]:
        try:
            tp = _setup_tea_party()
            game = _get_game_or_404(tp)
            if game.phase == tp.GamePhase.GAME_OVER:
                return {"success": False, "message": "游戏已结束"}
            if game.current_player != 1:
                return {"success": False, "message": "不是对手的回合"}

            sanitized = game.get_sanitized_state()
            decision = tp.no_ai_decision(sanitized)

            events: list[dict[str, Any]] = []
            for item_name in decision.get("items_to_use", []):
                result = game.use_item(1, item_name)
                if result.success:
                    events.extend([{"type": e.event_type, **e.data} for e in result.events])

            target = decision.get("target", "opponent")
            shoot_result = game.shoot(1, target)
            if shoot_result.success:
                events.extend([{"type": e.event_type, **e.data} for e in shoot_result.events])

            ai_extra_turn = game.phase == tp.GamePhase.PLAYING and game.current_player == 1

            return {
                "success": True,
                "message": f"对手向{'自己' if target == 'self' else '对方'}开火",
                "events": events,
                "dialogue": decision.get("dialogue", ""),
                "ai_extra_turn": ai_extra_turn,
                "phase": game.phase.value,
                "winner": game.winner,
                "state": game.get_state(),
            }
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"游戏对手回合处理失败：{exc}") from exc

    @app.post("/api/game/ai-turn")
    async def game_ai_turn(request: Request) -> dict[str, Any]:
        tp = _setup_tea_party()
        game = _get_game_or_404(tp)

        if game.phase == tp.GamePhase.GAME_OVER:
            return {"success": False, "message": "游戏已结束"}
        if game.current_player != 1:
            return {"success": False, "message": "不是 AI 的回合"}

        body = await request.json() if await request.body() else {}
        party_chat_message = body.get("message", "")
        _ = party_chat_message

        llm_config = ctx.get_runtime_chat_config()
        persona = ctx.get_persona() or {"name": "对手", "system_prompt": "", "greeting": ""}

        sanitized = game.get_sanitized_state()

        ai_mod = sys.modules.get("tea_party.ai_opponent")
        if ai_mod is None:
            return {"success": False, "message": "AI 模块未加载"}

        from fantareal.app import request_json as _request_json

        decision = await ai_mod.request_ai_action(
            sanitized_state=sanitized,
            persona=persona,
            llm_config=llm_config,
            request_json_func=_request_json,
        )

        events: list[dict[str, Any]] = []
        for item_name in decision.get("items_to_use", []):
            result = game.use_item(1, item_name)
            if result.success:
                events.extend([{"type": e.event_type, **e.data} for e in result.events])

        target = decision.get("target", "opponent")
        shoot_result = game.shoot(1, target)
        if shoot_result.success:
            events.extend([{"type": e.event_type, **e.data} for e in shoot_result.events])

        ai_extra_turn = game.phase == tp.GamePhase.PLAYING and game.current_player == 1

        return {
            "success": True,
            "message": f"AI 向{'自己' if target == 'self' else '对方'}开火",
            "events": events,
            "dialogue": decision.get("dialogue", ""),
            "ai_extra_turn": ai_extra_turn,
            "phase": game.phase.value,
            "winner": game.winner,
            "state": game.get_state(),
        }

    @app.get("/mods/{mod_slug}", response_class=HTMLResponse)
    async def mod_host_page(request: Request, mod_slug: str) -> HTMLResponse:
        mod = ctx.get_mod(mod_slug)
        if mod is None:
            raise HTTPException(status_code=404, detail="Mod not found.")
        return templates.TemplateResponse(
            request,
            "mod_host.html",
            {
                "settings": ctx.get_settings(),
                "mod": mod,
            },
        )
