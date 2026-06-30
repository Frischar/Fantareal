from types import SimpleNamespace

from fantareal.memory_merge_logic import (
    get_memory_outline,
    repair_mojibake_text,
    save_memory_outline,
)


def mojibake(text: str) -> str:
    return text.encode("utf-8").decode("latin-1")


def test_repair_mojibake_text_repairs_utf8_as_latin1_text():
    assert repair_mojibake_text(mojibake("十年相逢")) == "十年相逢"
    assert repair_mojibake_text(mojibake("顾知微、苏怜烟")) == "顾知微、苏怜烟"


def test_repair_mojibake_text_keeps_normal_text_unchanged():
    assert repair_mojibake_text("十年相逢") == "十年相逢"
    assert repair_mojibake_text("Cafe déjà vu") == "Cafe déjà vu"
    assert repair_mojibake_text("plain ASCII") == "plain ASCII"


def test_get_memory_outline_repairs_stored_mojibake_fields(tmp_path):
    base_dir = tmp_path / "card_runtime"
    memories_file = base_dir / "memories.json"
    outline_file = base_dir / "memory_outline.json"

    stored_outline = [
        {
            "id": "outline-1",
            "title": mojibake("十年相逢"),
            "summary": mojibake("顾知微与苏怜烟重逢。"),
            "characters": mojibake("顾知微、苏怜烟"),
            "relationship_progress": mojibake("师徒旧识重逢"),
            "key_events": [mojibake("逆生渡炁续命"), "正常事件"],
            "next_hooks": mojibake("后续救治方案"),
        }
    ]

    ctx = SimpleNamespace(
        memories_path=lambda slot_id=None: memories_file,
        read_json=lambda path, default: stored_outline if path == outline_file else default,
        persist_json=lambda path, payload, detail: None,
    )

    items = get_memory_outline(ctx)

    assert items[0]["title"] == "十年相逢"
    assert items[0]["summary"] == "顾知微与苏怜烟重逢。"
    assert items[0]["characters"] == "顾知微、苏怜烟"
    assert items[0]["relationship_progress"] == "师徒旧识重逢"
    assert items[0]["key_events"] == ["逆生渡炁续命", "正常事件"]
    assert items[0]["next_hooks"] == "后续救治方案"


def test_save_memory_outline_writes_repaired_values(tmp_path):
    base_dir = tmp_path / "card_runtime"
    memories_file = base_dir / "memories.json"
    captured = {}

    def persist_json(path, payload, detail):
        captured["path"] = path
        captured["payload"] = payload

    ctx = SimpleNamespace(
        memories_path=lambda slot_id=None: memories_file,
        read_json=lambda path, default: default,
        persist_json=persist_json,
    )

    saved = save_memory_outline(
        ctx,
        [
            {
                "id": "outline-1",
                "title": mojibake("十年相逢"),
                "key_events": [mojibake("逆生渡炁续命")],
            }
        ],
    )

    assert saved[0]["title"] == "十年相逢"
    assert saved[0]["key_events"] == ["逆生渡炁续命"]
    assert captured["payload"][0]["title"] == "十年相逢"
    assert captured["path"] == base_dir / "memory_outline.json"
