from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.requests import Request


def register_page_routes(app: FastAPI, *, templates: Any, ctx: Any) -> None:
    def build_chat_template_context() -> dict[str, Any]:
        preset_store = ctx.get_preset_store()
        active_preset = ctx.get_active_preset_from_store(preset_store)
        preset_debug = ctx.build_preset_debug_payload()
        return {
            "persona": ctx.get_persona(),
            "history": ctx.get_conversation(),
            "settings": ctx.get_settings(),
            "worldbook_settings": ctx.get_worldbook_settings(),
            "user_profile": ctx.get_user_profile(),
            "role_avatar_url": ctx.get_role_avatar_url(),
            "preset_store": preset_store,
            "active_preset": active_preset,
            "active_preset_modules": preset_debug["active_modules"],
            "preset_debug": preset_debug,
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
