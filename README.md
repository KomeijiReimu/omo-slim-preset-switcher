# OpenCode Preset Switcher

[中文说明](README.zh-CN.md) | English

A lightweight bilingual desktop application for browsing and switching
[`oh-my-opencode-slim`](https://github.com/alvinunreal/oh-my-opencode-slim)
presets. It supports **Linux and Windows**.

## Features

- Switch the interface between English and Chinese at any time.
- Discover `oh-my-opencode-slim.jsonc` or `.json` automatically.
- Search presets and compare agent, model, and provider counts.
- Open a preset details window to inspect its complete configuration, including
  models, reasoning variants, skills, and MCPs.
- Apply a preset from the main window or its details window.
- Preserve JSONC comments and formatting when switching presets.

## Platform support

| Platform | Status | Notes |
| --- | --- | --- |
| Linux | Supported | Tkinter may need to be installed through the system package manager. |
| Windows | Supported | Tkinter is normally included with the official Python installer. |

## Requirements

- Python 3.11 or later
- Tkinter 8.6 or later

On Windows, install Python from [python.org](https://www.python.org/downloads/)
and select the **tcl/tk and IDLE** component during setup. On Linux, install
Tkinter through the system package manager:

```bash
# Debian / Ubuntu
sudo apt install python3-tk

# Fedora
sudo dnf install python3-tkinter

# Arch Linux
sudo pacman -S tk
```

## Run

From the project directory:

```bash
python3 main.py
```

On Windows, the launcher may be named `python` instead:

```powershell
python main.py
```

You can also run the package directly:

```bash
python3 -m preset_switcher
```

## Configuration discovery

The application checks these directories in order on Linux and Windows:

1. The directory specified by `OPENCODE_CONFIG_DIR`
2. `$XDG_CONFIG_HOME/opencode`
3. `~/.config/opencode`

Within each directory, `oh-my-opencode-slim.jsonc` takes precedence over
`oh-my-opencode-slim.json`.

> [!NOTE]
> A newly selected preset takes effect the next time OpenCode starts. Restart
> OpenCode if you want to use it immediately.

## Keyboard shortcuts

| Shortcut | Action |
| --- | --- |
| `Ctrl+F` | Focus preset search |
| `Ctrl+R` | Reload the configuration |
| `Enter` | Apply the selected preset |
| Double-click | Open the selected preset details |

## Tests

```bash
python3 -m unittest discover -v
```
