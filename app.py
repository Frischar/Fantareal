"""Compatibility entrypoint for `uvicorn app:app`."""

from fantareal.app import BASE_DIR, app

__all__ = ["BASE_DIR", "app"]
