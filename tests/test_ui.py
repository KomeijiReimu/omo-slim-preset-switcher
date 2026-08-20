import unittest
from typing import Any, cast

from preset_switcher.ui import TRANSLATIONS, summarize_preset


class SummarizePresetTests(unittest.TestCase):
    def test_real_preset_shape_counts_agents_models_and_providers(self) -> None:
        preset = {
            "alpha": {"model": "openai/gpt-4.1"},
            "beta": {"model": "anthropic/claude-3-7-sonnet"},
            "gamma": {"model": "openai/gpt-4.1"},
        }

        self.assertEqual(summarize_preset(preset), ("3", "2", "anthropic, openai"))

    def test_duplicate_model_is_counted_once(self) -> None:
        preset = {
            "alpha": {"model": "provider/model"},
            "beta": {"model": "provider/model"},
            "gamma": {"model": "provider/other"},
        }

        self.assertEqual(summarize_preset(preset), ("3", "2", "provider"))

    def test_invalid_entries_are_ignored_without_raising(self) -> None:
        preset = {
            "valid": {"model": "provider/model"},
            "missing": {},
            "empty": {"model": ""},
            "whitespace": {"model": "   "},
            "wrong_type": {"model": 42},
            "not_an_agent": "invalid",
            "none_agent": None,
        }

        self.assertEqual(summarize_preset(preset), ("5", "1", "provider"))
        self.assertEqual(summarize_preset({"invalid": []}), ("0", "0", "-"))
        self.assertEqual(summarize_preset(cast(Any, None)), ("-", "-", "-"))

    def test_empty_config_returns_placeholders(self) -> None:
        self.assertEqual(summarize_preset({}), ("0", "0", "-"))

    def test_applied_status_explains_next_run_timing(self) -> None:
        self.assertIn("将在下次 OpenCode 运行时生效", TRANSLATIONS["zh"]["status_applied"])
        self.assertIn("next time OpenCode runs", TRANSLATIONS["en"]["status_applied"])


if __name__ == "__main__":
    unittest.main()
