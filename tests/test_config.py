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
    config_search_dirs,
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

    def test_search_dirs_use_env_priority_and_do_not_duplicate_opencode(self) -> None:
        home = self.root / "home"
        xdg_home = self.root / "xdg"
        explicit = xdg_home / "opencode"

        directories = config_search_dirs(
            system="Linux",
            env={
                "OPENCODE_CONFIG_DIR": str(explicit),
                "XDG_CONFIG_HOME": str(xdg_home),
            },
            home=home,
        )

        self.assertEqual(
            directories,
            (explicit, home / ".config" / "opencode"),
        )
        self.assertNotIn(explicit / "opencode", directories)

    def test_search_dirs_have_same_rules_on_windows_linux_and_darwin(self) -> None:
        home = self.root / "home"
        explicit = self.root / "explicit"
        env = {
            "OPENCODE_CONFIG_DIR": str(explicit),
            "XDG_CONFIG_HOME": str(self.root / "xdg"),
        }
        expected = (
            explicit,
            self.root / "xdg" / "opencode",
            home / ".config" / "opencode",
        )

        for system in ("Windows", "Linux", "Darwin"):
            with self.subTest(system=system):
                self.assertEqual(
                    config_search_dirs(system=system, env=env, home=home),
                    expected,
                )

    def test_search_dirs_expand_tilde_against_injected_home(self) -> None:
        home = self.root / "home"

        directories = config_search_dirs(
            env={"OPENCODE_CONFIG_DIR": "~/custom"},
            home=home,
        )

        self.assertEqual(directories[0], home / "custom")

    def test_default_discovery_prefers_directories_then_jsonc_then_json(self) -> None:
        home = self.root / "home"
        xdg_home = self.root / "xdg"
        explicit_dir = self.root / "explicit"
        for directory in (home / ".config" / "opencode", xdg_home / "opencode", explicit_dir):
            directory.mkdir(parents=True)
        json_name = "oh-my-opencode-slim.json"
        jsonc_name = "oh-my-opencode-slim.jsonc"
        explicit_json = explicit_dir / json_name
        explicit_jsonc = explicit_dir / jsonc_name
        xdg_jsonc = xdg_home / "opencode" / jsonc_name
        explicit_json.write_text("{}", encoding="utf-8")
        explicit_jsonc.write_text("{}", encoding="utf-8")
        xdg_jsonc.write_text("{}", encoding="utf-8")

        environment = {
            "OPENCODE_CONFIG_DIR": str(explicit_dir),
            "XDG_CONFIG_HOME": str(xdg_home),
        }
        with patch.dict(os.environ, environment, clear=True), patch.object(
            Path, "home", return_value=home
        ):
            self.assertEqual(resolve_config_path(), explicit_jsonc)
            explicit_jsonc.unlink()
            self.assertEqual(resolve_config_path(), explicit_json)
            explicit_json.unlink()
            self.assertEqual(resolve_config_path(), xdg_jsonc)

    def test_explicit_path_has_priority_over_discovery(self) -> None:
        explicit_path = self.root / "selected.json"
        explicit_path.write_text("{}", encoding="utf-8")

        with patch.dict(os.environ, {}, clear=True), patch.object(
            Path, "home", return_value=self.root / "missing-home"
        ):
            self.assertEqual(resolve_config_path(explicit_path), explicit_path)

    def test_missing_all_candidates_raises_config_error(self) -> None:
        with patch.dict(
            os.environ,
            {
                "OPENCODE_CONFIG_DIR": str(self.root / "explicit"),
                "XDG_CONFIG_HOME": str(self.root / "xdg"),
            },
            clear=True,
        ), patch.object(Path, "home", return_value=self.root / "home"):
            with self.assertRaises(ConfigError):
                resolve_config_path()

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
