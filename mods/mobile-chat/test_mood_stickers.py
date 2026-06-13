from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch


APP_PATH = Path(__file__).with_name("app.py")
SPEC = importlib.util.spec_from_file_location("mobile_chat_app_mood_test", APP_PATH)
assert SPEC and SPEC.loader
APP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(APP)


class MoodStickerTests(unittest.TestCase):
    def test_every_mood_tag_is_removed_and_recognized(self) -> None:
        self.assertGreater(len(APP.MOOD_STICKER_TAGS), 1)
        for tag in APP.MOOD_STICKER_TAGS:
            with self.subTest(tag=tag):
                content, mood = APP.extract_mood_tag(f"测试回复 {{{tag}}}")
                self.assertEqual(content, "测试回复")
                self.assertEqual(mood, tag)

    def test_prompt_lists_every_supported_tag(self) -> None:
        for tag in APP.MOOD_STICKER_TAGS:
            self.assertIn(f"{{{tag}}}", APP.MOOD_TAG_PROMPT)

    def test_prompt_is_injected_at_end_of_group_context(self) -> None:
        group = APP.default_group()
        messages = APP.build_mobile_model_messages(group, [], "你好")
        self.assertEqual(messages[-1]["role"], "user")
        self.assertTrue(messages[-1]["content"].endswith(APP.MOOD_TAG_PROMPT))
        self.assertNotIn("available_stickers", messages[-1]["content"])
        self.assertNotIn("涩图", messages[-1]["content"])

    def test_legacy_sticker_prompt_block_is_migrated(self) -> None:
        payload = APP.sanitize_prompt_blocks(
            {
                "blocks": [
                    {
                        "block_id": "sticker_contract",
                        "label": "Sticker Contract",
                        "order": 40,
                        "enabled": True,
                        "locked": False,
                        "scope": ["group_chat"],
                        "content": "Choose ids from available_stickers.",
                    }
                ]
            }
        )
        block = next(item for item in payload["blocks"] if item["block_id"] == "sticker_contract")
        self.assertEqual(block["content"], APP.MOOD_TAG_PROMPT)

    def test_every_mood_tag_has_a_matching_sticker_pack(self) -> None:
        for tag in APP.MOOD_STICKER_TAGS:
            with self.subTest(tag=tag):
                self.assertTrue(APP.custom_sticker_files(tag))

    def test_every_mood_sticker_uses_matching_pack_when_roll_hits(self) -> None:
        message = {
            "speaker_id": "role_test",
            "speaker_name": "测试角色",
        }
        for tag in APP.MOOD_STICKER_TAGS:
            with self.subTest(tag=tag):
                sticker = APP.mood_sticker_message(
                    message,
                    tag,
                    random_value=lambda: 0.0,
                    choose=lambda files: files[0],
                )
                self.assertIsNotNone(sticker)
                assert sticker is not None
                self.assertEqual(sticker["type"], "sticker")
                self.assertTrue(sticker["content"].startswith(f"{tag}:"))
                self.assertEqual(sticker["speaker_id"], message["speaker_id"])

    def test_probability_is_exactly_twenty_five_percent_boundary(self) -> None:
        message = {
            "speaker_id": "role_test",
            "speaker_name": "测试角色",
        }
        below = APP.mood_sticker_message(
            message,
            "angry",
            random_value=lambda: 0.249999,
            choose=lambda files: files[0],
        )
        at_boundary = APP.mood_sticker_message(
            message,
            "angry",
            random_value=lambda: 0.25,
            choose=lambda files: files[0],
        )
        self.assertIsNotNone(below)
        self.assertIsNone(at_boundary)

    def test_unknown_braced_text_is_not_treated_as_mood(self) -> None:
        content, mood = APP.extract_mood_tag("保留 {unknown} 内容")
        self.assertEqual(content, "保留 {unknown} 内容")
        self.assertEqual(mood, "")

    def test_parser_hides_tag_and_appends_matching_sticker(self) -> None:
        group = APP.default_group()
        role = next(member for member in group["members"] if member["type"] == "character")
        raw = json.dumps(
            {
                "messages": [
                    {
                        "speaker": role["name"],
                        "type": "text",
                        "content": "这句话有点生气。{angry}",
                    }
                ]
            },
            ensure_ascii=False,
        )
        with patch.object(APP.random, "random", return_value=0.0), patch.object(
            APP.random,
            "choice",
            side_effect=lambda files: files[0],
        ):
            parsed = APP.parse_model_mobile_messages(raw, group)
        self.assertEqual([message["type"] for message in parsed], ["text", "sticker"])
        self.assertEqual(parsed[0]["content"], "这句话有点生气。")
        self.assertNotIn("{angry}", parsed[0]["content"])
        self.assertTrue(parsed[1]["content"].startswith("angry:"))


if __name__ == "__main__":
    unittest.main()
