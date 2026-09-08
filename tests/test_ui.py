import os
import subprocess
import sys
import unittest
from typing import Any, cast
from unittest.mock import MagicMock, patch

from preset_switcher.ui import (
    TRANSLATIONS,
    _FOREGROUND_ENV,
    can_apply_preset,
    format_preset_details,
    main,
    summarize_preset,
)


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


class PresetDetailsTests(unittest.TestCase):
    def test_format_keeps_model_reasoning_and_nested_future_fields(self) -> None:
        preset = {
            "reviewer": {
                "model": "openai/gpt-5",
                "reasoningEffort": "high",
                "nested": {"futureFlag": True, "limits": {"tokens": 4096}},
            }
        }

        details = format_preset_details(preset)

        self.assertIn('"model": "openai/gpt-5"', details)
        self.assertIn('"reasoningEffort": "high"', details)
        self.assertIn('"futureFlag": true', details)
        self.assertIn('"tokens": 4096', details)

    def test_detail_and_apply_translations_exist_in_both_languages(self) -> None:
        for language in ("zh", "en"):
            with self.subTest(language=language):
                translations = TRANSLATIONS[language]
                self.assertTrue(translations["details_button"])
                self.assertTrue(translations["apply_button"])
                self.assertTrue(translations["close_button"])
                self.assertTrue(translations["detail_config"])

    def test_active_preset_cannot_be_applied_again(self) -> None:
        self.assertFalse(can_apply_preset("balanced", "balanced"))
        self.assertTrue(can_apply_preset("balanced", "fast"))
        self.assertFalse(can_apply_preset(None, None))
        self.assertFalse(can_apply_preset("balanced", None))


class DetachedLaunchTests(unittest.TestCase):
    @patch("preset_switcher.ui.PresetSwitcherApp")
    @patch("preset_switcher.ui.subprocess.Popen")
    def test_main_returns_after_starting_background_process(
        self,
        popen: MagicMock,
        app: MagicMock,
    ) -> None:
        popen.return_value = MagicMock()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(_FOREGROUND_ENV, None)
            main()

        popen.assert_called_once()
        app.assert_not_called()
        kwargs = popen.call_args.kwargs
        self.assertEqual(kwargs["env"][_FOREGROUND_ENV], "1")
        self.assertTrue(str(kwargs["args"][1]).endswith("main.py"))
        self.assertTrue(str(kwargs["cwd"]).endswith("omo-slim_preset_switch"))
        self.assertIs(kwargs["stdin"], subprocess.DEVNULL)
        self.assertIs(kwargs["stdout"], subprocess.DEVNULL)
        self.assertIs(kwargs["stderr"], subprocess.DEVNULL)
        if sys.platform != "win32":
            self.assertTrue(kwargs["start_new_session"])

    @patch("preset_switcher.ui.subprocess.Popen")
    @patch("preset_switcher.ui.PresetSwitcherApp")
    def test_main_runs_window_in_the_marked_child_process(
        self,
        app: MagicMock,
        popen: MagicMock,
    ) -> None:
        with patch.dict(os.environ, {_FOREGROUND_ENV: "1"}):
            main()

        popen.assert_not_called()
        app.assert_called_once_with()
        app.return_value.run.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
