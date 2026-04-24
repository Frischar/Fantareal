from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException


def register_mod_api_routes(app: FastAPI, *, ctx: Any) -> None:
    @app.get("/api/mods")
    async def list_mods() -> dict[str, Any]:
        return {"mods": ctx.list_mods()}

    @app.get("/api/mods/{mod_slug}")
    async def get_mod(mod_slug: str) -> dict[str, Any]:
        mod = ctx.get_mod(mod_slug)
        if mod is None:
            raise HTTPException(status_code=404, detail="Mod not found.")
        return {"mod": mod}
