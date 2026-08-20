from __future__ import annotations

import json
import os
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ConfigError(Exception):
    """Raised when the preset configuration cannot be read or updated."""


@dataclass(frozen=True)
class ConfigSnapshot:
    path: Path
    active_preset: str
    presets: dict[str, dict[str, Any]]


_CONFIG_DIR = Path(".config") / "opencode"
_CONFIG_BASENAME = "oh-my-opencode-slim"


def resolve_config_path(path: Path | None = None) -> Path:
    """Return an explicit path or the first available default config path."""
    if path is not None:
        return Path(path).expanduser()

    config_dir = Path.home() / _CONFIG_DIR
    for suffix in (".jsonc", ".json"):
        candidate = config_dir / f"{_CONFIG_BASENAME}{suffix}"
        if candidate.is_file():
            return candidate

    expected = config_dir / f"{_CONFIG_BASENAME}.jsonc"
    raise ConfigError(f"configuration file not found: {expected}")


def load_config(path: Path | None = None) -> ConfigSnapshot:
    """Read, parse, and validate a preset configuration."""
    config_path = resolve_config_path(path)
    text = _read_config_text(config_path)
    payload = _parse_jsonc(text, config_path)
    return _make_snapshot(config_path, payload)


def set_active_preset(name: str, path: Path | None = None) -> ConfigSnapshot:
    """Change only the top-level preset string in a configuration file."""
    if not isinstance(name, str):
        raise ConfigError("preset name must be a string")

    config_path = resolve_config_path(path)
    text = _read_config_text(config_path)
    payload = _parse_jsonc(text, config_path)
    snapshot = _make_snapshot(config_path, payload)

    if name not in snapshot.presets:
        raise ConfigError(f"unknown preset: {name}")
    if name == snapshot.active_preset:
        return snapshot

    value_start, value_end = _find_top_level_preset_value(text)
    replacement = json.dumps(name, ensure_ascii=False)
    updated_text = text[:value_start] + replacement + text[value_end:]
    _atomic_write(config_path, updated_text, config_path.stat().st_mode)
    return load_config(config_path)


def _read_config_text(path: Path) -> str:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ConfigError(f"unable to read configuration {path}: {exc}") from exc

    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ConfigError(f"configuration is not valid UTF-8: {path}") from exc


def _parse_jsonc(text: str, path: Path) -> Any:
    # Keep comments as whitespace so all string contents remain untouched.
    parse_text = text[1:] if text.startswith("\ufeff") else text
    without_comments = _strip_jsonc_comments(parse_text)
    without_trailing_commas = _strip_trailing_commas(without_comments)
    try:
        return json.loads(without_trailing_commas)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid JSON in {path}: {exc.msg}") from exc


def _strip_jsonc_comments(text: str) -> str:
    result: list[str] = []
    index = 0
    length = len(text)

    while index < length:
        character = text[index]

        if character == '"':
            end = _string_end(text, index)
            if end is None:
                result.append(text[index:])
                break
            result.append(text[index:end])
            index = end
            continue

        if text.startswith("//", index):
            result.extend(" " for _ in range(2))
            index += 2
            while index < length and text[index] not in "\r\n":
                result.append(" ")
                index += 1
            continue

        if text.startswith("/*", index):
            result.extend(" " for _ in range(2))
            index += 2
            closed = False
            while index < length:
                if text.startswith("*/", index):
                    result.extend(" " for _ in range(2))
                    index += 2
                    closed = True
                    break
                if text[index] in "\r\n":
                    result.append(text[index])
                else:
                    result.append(" ")
                index += 1
            if not closed:
                raise ConfigError("unterminated block comment")
            continue

        result.append(character)
        index += 1

    return "".join(result)


def _strip_trailing_commas(text: str) -> str:
    result: list[str] = []
    index = 0
    length = len(text)

    while index < length:
        character = text[index]

        if character == '"':
            end = _string_end(text, index)
            if end is None:
                result.append(text[index:])
                break
            result.append(text[index:end])
            index = end
            continue

        if character == ",":
            lookahead = index + 1
            while lookahead < length and text[lookahead].isspace():
                lookahead += 1
            if lookahead < length and text[lookahead] in "]}":
                index += 1
                continue

        result.append(character)
        index += 1

    return "".join(result)


def _string_end(text: str, start: int) -> int | None:
    index = start + 1
    while index < len(text):
        character = text[index]
        if character == "\\":
            index += 2
            continue
        if character == '"':
            return index + 1
        index += 1
    return None


def _make_snapshot(path: Path, payload: Any) -> ConfigSnapshot:
    if not isinstance(payload, dict):
        raise ConfigError("configuration top level must be an object")

    active_preset = payload.get("preset")
    if not isinstance(active_preset, str):
        raise ConfigError("top-level preset must be a string")

    presets = payload.get("presets")
    if not isinstance(presets, dict):
        raise ConfigError("top-level presets must be an object")
    if active_preset not in presets:
        raise ConfigError(f"active preset is not defined: {active_preset}")
    if not all(isinstance(preset, str) for preset in presets):
        raise ConfigError("preset names must be strings")
    if not all(isinstance(value, dict) for value in presets.values()):
        raise ConfigError("each preset definition must be an object")

    return ConfigSnapshot(
        path=path,
        active_preset=active_preset,
        presets=presets,
    )


def _skip_ignored(text: str, start: int) -> int:
    index = start
    length = len(text)
    while index < length:
        while index < length and text[index].isspace():
            index += 1

        if text.startswith("//", index):
            index += 2
            while index < length and text[index] not in "\r\n":
                index += 1
            continue

        if text.startswith("/*", index):
            end = text.find("*/", index + 2)
            if end < 0:
                raise ConfigError("unterminated block comment")
            index = end + 2
            continue

        return index
    return index


def _find_top_level_preset_value(text: str) -> tuple[int, int]:
    depth = 0
    index = 0
    found: tuple[int, int] | None = None

    while index < len(text):
        character = text[index]

        if character == '"':
            end = _string_end(text, index)
            if end is None:
                raise ConfigError("invalid preset string")

            if depth == 1:
                try:
                    token = json.loads(text[index:end])
                except json.JSONDecodeError as exc:
                    raise ConfigError("invalid string in configuration") from exc

                colon = _skip_ignored(text, end)
                if token == "preset" and colon < len(text) and text[colon] == ":":
                    value_start = _skip_ignored(text, colon + 1)
                    if value_start < len(text) and text[value_start] == '"':
                        value_end = _string_end(text, value_start)
                        if value_end is None:
                            raise ConfigError("invalid preset string")
                        found = (value_start, value_end)
            index = end
            continue

        if text.startswith("//", index):
            index += 2
            while index < len(text) and text[index] not in "\r\n":
                index += 1
            continue

        if text.startswith("/*", index):
            end = text.find("*/", index + 2)
            if end < 0:
                raise ConfigError("unterminated block comment")
            index = end + 2
            continue

        if character in "[{":
            depth += 1
        elif character in "]}":
            depth -= 1
        index += 1

    if found is None:
        raise ConfigError("top-level preset string not found")
    return found


def _atomic_write(path: Path, text: str, source_mode: int) -> None:
    temporary_path: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        )
        temporary_path = Path(temporary_name)
        with os.fdopen(descriptor, "wb") as temporary_file:
            temporary_file.write(text.encode("utf-8"))
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.chmod(temporary_path, stat.S_IMODE(source_mode))
        os.replace(temporary_path, path)
    except OSError as exc:
        raise ConfigError(f"unable to update configuration {path}: {exc}") from exc
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass


__all__ = [
    "ConfigError",
    "ConfigSnapshot",
    "load_config",
    "resolve_config_path",
    "set_active_preset",
]
