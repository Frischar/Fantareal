from __future__ import annotations

import importlib.util
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI


SLUG_SANITIZE_RE = re.compile(r"[^a-z0-9]+")
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModSpec:
    slug: str
    name: str
    label: str
    directory: Path
    route_path: str
    mount_path: str

    def to_dict(self) -> dict[str, str]:
        return {
            "slug": self.slug,
            "name": self.name,
            "label": self.label,
            "route_path": self.route_path,
            "mount_path": self.mount_path,
        }


def slugify_mod_name(name: str) -> str:
    normalized = SLUG_SANITIZE_RE.sub("-", name.strip().lower()).strip("-")
    return normalized or "mod"


def discover_mods(mods_dir: Path) -> list[ModSpec]:
    specs: list[ModSpec] = []
    if not mods_dir.exists():
        return specs
    for child in sorted(mods_dir.iterdir(), key=lambda item: item.name.lower()):
        if not child.is_dir():
            continue
        if not (child / "app.py").exists():
            continue
        slug = slugify_mod_name(child.name)
        label = child.name.title()
        specs.append(
            ModSpec(
                slug=slug,
                name=child.name,
                label=label,
                directory=child,
                route_path=f"/mods/{slug}",
                mount_path=f"/mods/{slug}/app",
            )
        )
    return specs


def load_mod_app(spec: ModSpec) -> FastAPI:
    module_name = f"xuqi_mod_{spec.slug.replace('-', '_')}"
    module_path = spec.directory / "app.py"
    module_spec = importlib.util.spec_from_file_location(module_name, module_path)
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError(f"Failed to load mod from {module_path}")

    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_name] = module
    module_spec.loader.exec_module(module)
    asgi_app = getattr(module, "app", None)
    if not isinstance(asgi_app, FastAPI):
        raise RuntimeError(f"Mod {spec.name} does not expose a FastAPI app")
    return asgi_app


def mount_discovered_mods(app: FastAPI, mods_dir: Path) -> list[ModSpec]:
    mounted_specs: list[ModSpec] = []
    for spec in discover_mods(mods_dir):
        try:
            app.mount(spec.mount_path, load_mod_app(spec))
        except Exception:
            logger.exception("Skipping broken mod during startup: %s", spec.name)
            continue
        mounted_specs.append(spec)
    return mounted_specs


def find_mod(mods: list[ModSpec], slug: str) -> ModSpec | None:
    for spec in mods:
        if spec.slug == slug:
            return spec
    return None
