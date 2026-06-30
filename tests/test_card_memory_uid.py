from __future__ import annotations

import os
from pathlib import Path
import importlib
import sys

from fantareal.config_api_routes import resolve_workspace_import_card_uid


def _load_app_module(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[1]
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)
    fake_executable = tmp_path / "fake-runtime" / "app.exe"
    fake_executable.parent.mkdir(parents=True, exist_ok=True)
    sys.frozen = True
    sys.executable = str(fake_executable)
    return importlib.import_module("fantareal.app")


def test_current_memory_card_uid_stays_stable_for_same_card(monkeypatch, tmp_path):
    app = _load_app_module(tmp_path)
    data_dir = tmp_path / "data"
    card_runtime_dir = data_dir / "card_runtime" / "cards"
    current_card_path = data_dir / "current_role_card.json"

    monkeypatch.setattr(app, "DATA_DIR", data_dir, raising=False)
    monkeypatch.setattr(app, "CARD_RUNTIME_DIR", card_runtime_dir, raising=False)
    monkeypatch.setattr(app, "LEGACY_CURRENT_CARD_PATH", current_card_path, raising=False)
    monkeypatch.setattr(app, "BASE_DIR", tmp_path, raising=False)
    monkeypatch.setattr(app, "global_current_card_path", lambda: current_card_path, raising=False)
    monkeypatch.setattr(app, "get_active_slot_id", lambda: "slot_a", raising=False)

    first_card = {
        "source_name": "demo.json",
        "card_uid": "card_demo_1",
        "raw": {
            "name": "Demo",
            "stateJournal": {"card_uid": "card_demo_1"},
            "personas": {},
        },
    }
    app.persist_json(current_card_path, first_card, detail="test")

    assert app.current_memory_card_uid("slot_a") == "card_demo_1"

    updated_card = {
        "source_name": "demo.json",
        "card_uid": "card_demo_1",
        "raw": {
            "name": "Demo",
            "description": "edited",
            "stateJournal": {"card_uid": "card_demo_1"},
            "personas": {"1": {"name": "A", "description": "x", "personality": "", "scenario": "", "creator_notes": ""}},
        },
    }
    app.persist_json(current_card_path, updated_card, detail="test")

    assert app.current_memory_card_uid("slot_a") == "card_demo_1"
    assert app.memories_path("slot_a") == card_runtime_dir / "card_demo_1" / "memories.json"


def test_current_memory_card_uid_falls_back_to_legacy_hash_and_new_uid(monkeypatch, tmp_path):
    app = _load_app_module(tmp_path)
    data_dir = tmp_path / "data"
    card_runtime_dir = data_dir / "card_runtime" / "cards"
    current_card_path = data_dir / "current_role_card.json"

    monkeypatch.setattr(app, "DATA_DIR", data_dir, raising=False)
    monkeypatch.setattr(app, "CARD_RUNTIME_DIR", card_runtime_dir, raising=False)
    monkeypatch.setattr(app, "LEGACY_CURRENT_CARD_PATH", current_card_path, raising=False)
    monkeypatch.setattr(app, "BASE_DIR", tmp_path, raising=False)
    monkeypatch.setattr(app, "global_current_card_path", lambda: current_card_path, raising=False)
    monkeypatch.setattr(app, "get_active_slot_id", lambda: "slot_a", raising=False)

    legacy_card = {
        "source_name": "legacy.json",
        "raw": {
            "name": "Legacy",
            "personas": {"1": {"name": "Alpha", "description": "", "personality": "", "scenario": "", "creator_notes": ""}},
        },
    }
    app.persist_json(current_card_path, legacy_card, detail="test")
    legacy_uid = app.current_memory_card_uid("slot_a")
    assert legacy_uid.startswith("card_")
    assert legacy_uid == app._legacy_card_runtime_uid(legacy_card)

    new_card = {
        "source_name": "new.json",
        "raw": {
            "name": "New",
            "personas": {"1": {"name": "Beta", "description": "", "personality": "", "scenario": "", "creator_notes": ""}},
        },
    }
    generated_uid = app._build_current_card_uid(new_card, "new.json")
    assert generated_uid.startswith("card_")
    assert generated_uid != legacy_uid
    assert generated_uid == app._legacy_card_runtime_uid(new_card)


def test_build_current_card_uid_reuses_current_uid_for_same_source_edit(monkeypatch, tmp_path):
    app = _load_app_module(tmp_path)
    current_card = {
        "source_name": "demo.json",
        "card_uid": "card_demo_1",
        "raw": {
            "name": "Demo",
            "personas": {
                "1": {"name": "Alpha", "description": "", "personality": "", "scenario": "", "creator_notes": ""}
            },
        },
    }
    edited_target = {
        "name": "Demo",
        "personas": {
            "1": {"name": "Alpha", "description": "", "personality": "", "scenario": "", "creator_notes": ""},
            "2": {"name": "Beta", "description": "new", "personality": "", "scenario": "", "creator_notes": ""},
        },
    }

    assert app._build_current_card_uid(current_card, "demo.json", edited_target) == "card_demo_1"


def test_build_current_card_uid_uses_target_when_switching_back(monkeypatch, tmp_path):
    app = _load_app_module(tmp_path)
    current_card = {
        "source_name": "b.json",
        "card_uid": "card_b",
        "raw": {
            "name": "B",
            "personas": {
                "1": {"name": "Beta", "description": "", "personality": "", "scenario": "", "creator_notes": ""}
            },
        },
    }
    target_card = {
        "name": "A",
        "personas": {
            "1": {"name": "Alpha", "description": "", "personality": "", "scenario": "", "creator_notes": ""}
        },
    }
    target_payload = {"source_name": "a.json", "raw": target_card}

    assert app._build_current_card_uid(current_card, "a.json", target_card) == app._legacy_card_runtime_uid(target_payload)


def test_build_current_card_uid_prefers_target_identity(monkeypatch, tmp_path):
    app = _load_app_module(tmp_path)
    current_card = {
        "source_name": "old.json",
        "card_uid": "card_old",
        "raw": {"name": "Old", "personas": {}},
    }

    assert (
        app._build_current_card_uid(current_card, "target.json", {"name": "Target", "uid": "Imported Target UID"})
        == "imported_target_uid"
    )
    assert (
        app._build_current_card_uid(
            current_card,
            "target.json",
            {
                "name": "Target",
                "card_uid": "Target Card UID",
                "stateJournal": {"card_uid": "State Journal UID"},
            },
        )
        == "target_card_uid"
    )
    assert (
        app._build_current_card_uid(
            current_card,
            "target.json",
            {"name": "Target", "stateJournal": {"card_uid": "State Journal UID"}},
        )
        == "state_journal_uid"
    )


def test_workspace_import_uid_prefers_imported_identity_over_existing(monkeypatch, tmp_path):
    app = _load_app_module(tmp_path)
    existing_card = {
        "source_name": "old.json",
        "card_uid": "card_existing",
        "raw": {"name": "Old", "personas": {}},
    }
    imported_with_uid = {
        "source_name": "new.json",
        "raw": {
            "name": "New",
            "uid": "Imported UID",
            "personas": {},
        },
    }
    imported_without_uid = {
        "source_name": "legacy-new.json",
        "raw": {
            "name": "Legacy New",
            "personas": {
                "1": {"name": "Gamma", "description": "", "personality": "", "scenario": "", "creator_notes": ""}
            },
        },
    }

    assert resolve_workspace_import_card_uid(imported_with_uid, existing_card) == "imported_uid"
    assert resolve_workspace_import_card_uid(imported_without_uid, existing_card) == app._legacy_card_runtime_uid(imported_without_uid)
