import json
import os
import stat
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from preset_switcher.config import (
    ConfigError,
    ConfigSnapshot,
    load_config,
    resolve_config_path,
    set_active_preset,
)


class ConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.config_path = self.root / "config.jsonc"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_config(self, text: str) -> None:
        self.config_path.write_text(text, encoding="utf-8")

    def test_default_discovery_prefers_jsonc_then_falls_back_to_json(self) -> None:
        home = self.root / "home"
        config_dir = home / ".config" / "opencode"
        config_dir.mkdir(parents=True)
        json_path = config_dir / "oh-my-opencode-slim.json"
        jsonc_path = config_dir / "oh-my-opencode-slim.jsonc"
        json_path.write_text("{}", encoding="utf-8")

        with patch.object(Path, "home", return_value=home):
            self.assertEqual(resolve_config_path(), json_path)
            jsonc_path.write_text("{}", encoding="utf-8")
            self.assertEqual(resolve_config_path(), jsonc_path)

    def test_load_json(self) -> None:
        self.write_config(
            '{"preset": "fast", "presets": {"fast": {"workers": 2}}}'
        )

        snapshot = load_config(self.config_path)

        self.assertIsInstance(snapshot, ConfigSnapshot)
        self.assertEqual(snapshot.path, self.config_path)
        self.assertEqual(snapshot.active_preset, "fast")
        self.assertEqual(snapshot.presets["fast"]["workers"], 2)

    def test_load_jsonc_comments_trailing_commas_and_comment_symbols_in_strings(self) -> None:
        self.write_config(
            """{
  // the active preset
  "preset": "fast",
  "presets": {
    "fast": {"url": "https://example.test/a//b",},
    "slow": {"pattern": "/* keep this */",}, /* trailing comment */
  },
}
"""
        )

        snapshot = load_config(self.config_path)

        self.assertEqual(snapshot.active_preset, "fast")
        self.assertEqual(snapshot.presets["fast"]["url"], "https://example.test/a//b")
        self.assertEqual(snapshot.presets["slow"]["pattern"], "/* keep this */")

    def test_unknown_target_does_not_change_file(self) -> None:
        original = '{\n  "preset": "fast",\n  "presets": {"fast": {}, "slow": {},},\n}\n'
        self.write_config(original)

        with self.assertRaises(ConfigError):
            set_active_preset("missing", self.config_path)

        self.assertEqual(self.config_path.read_text(encoding="utf-8"), original)

    def test_success_preserves_comments_trailing_commas_and_permissions(self) -> None:
        original = (
            "{\n"
            "  // keep this comment\n"
            "  \"preset\": \"fast\",\n"
            "  \"presets\": {\n"
            "    \"fast\": {},\n"
            "    \"slow\": {}, // keep this comma\n"
            "  },\n"
            "}\n"
        )
        self.write_config(original)
        os.chmod(self.config_path, 0o640)

        snapshot = set_active_preset("slow", self.config_path)
        updated = self.config_path.read_text(encoding="utf-8")

        self.assertEqual(snapshot.active_preset, "slow")
        self.assertEqual(
            updated,
            original.replace('"preset": "fast"', '"preset": "slow"'),
        )
        self.assertIn("// keep this comment", updated)
        self.assertIn("slow\": {}, // keep this comma", updated)
        self.assertEqual(stat.S_IMODE(self.config_path.stat().st_mode), 0o640)

    def test_nested_preset_is_not_changed(self) -> None:
        original = (
            '{\n'
            '  "metadata": {"preset": "nested"},\n'
            '  "preset": "fast",\n'
            '  "presets": {"fast": {}, "slow": {}},\n'
            '}\n'
        )
        self.write_config(original)

        set_active_preset("slow", self.config_path)

        updated = self.config_path.read_text(encoding="utf-8")
        self.assertIn('"metadata": {"preset": "nested"}', updated)
        self.assertIn('"preset": "slow"', updated)

    def test_invalid_structures_raise_config_error(self) -> None:
        invalid_payloads = (
            {"preset": ["fast"], "presets": {"fast": {}}},
            {"preset": "fast", "presets": []},
            {"preset": "missing", "presets": {"fast": {}}},
            {"preset": "fast", "presets": {"fast": []}},
            ["fast"],
        )

        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                self.config_path.write_text(
                    json.dumps(payload), encoding="utf-8"
                )
                with self.assertRaises(ConfigError):
                    load_config(self.config_path)

    def test_atomic_write_failure_cleans_up_temporary_file(self) -> None:
        self.write_config('{"preset": "fast", "presets": {"fast": {}, "slow": {}}}')
        original = self.config_path.read_bytes()

        with patch("preset_switcher.config.os.replace", side_effect=OSError("no replace")):
            with self.assertRaises(ConfigError):
                set_active_preset("slow", self.config_path)

        self.assertEqual(self.config_path.read_bytes(), original)
        self.assertEqual(list(self.root.glob(f".{self.config_path.name}.*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
