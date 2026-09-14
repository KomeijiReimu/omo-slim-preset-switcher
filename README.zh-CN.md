# OpenCode Preset Switcher

中文说明 | [English](README.md)

[![许可证：MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) [![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/) [![平台：Linux | Windows](https://img.shields.io/badge/Platforms-Linux%20%7C%20Windows-lightgrey.svg)](#系统支持)

一个用于浏览和快速切换
[`oh-my-opencode-slim`](https://github.com/alvinunreal/oh-my-opencode-slim)
预设的轻量双语桌面程序，支持 **Linux 和 Windows**。

oh-my-opencode-slim 官方仓库：<https://github.com/alvinunreal/oh-my-opencode-slim>

## 功能

- 随时切换中文和 English 界面。
- 自动查找 `oh-my-opencode-slim.jsonc` 或 `.json`。
- 搜索预设，并对比 Agent、模型和 provider 数量。
- 进入预设详情窗口，查看模型、推理档位、skills 和 MCP 等完整配置。
- 可以从主窗口或详情窗口应用预设。
- 切换预设时保留 JSONC 注释和原有格式。

## 系统支持

| 系统 | 状态 | 说明 |
| --- | --- | --- |
| Linux | 支持 | Tkinter 可能需要通过系统包管理器单独安装。 |
| Windows | 支持 | 官方 Python 安装程序通常自带 Tkinter。 |

## 运行要求

- Python 3.11 或更高版本
- Tkinter 8.6 或更高版本

Windows 用户可从 [python.org](https://www.python.org/downloads/) 安装 Python，
安装时勾选 **tcl/tk and IDLE** 组件。Linux 用户可通过系统包管理器安装 Tkinter：

```bash
# Debian / Ubuntu
sudo apt install python3-tk

# Fedora
sudo dnf install python3-tkinter

# Arch Linux
sudo pacman -S tk
```

## 启动

在项目目录中运行：

```bash
python3 main.py
```

窗口打开后，终端会立即回到可用状态。

Windows 上的命令通常是：

```powershell
python main.py
```

也可以直接运行 Python 包：

```bash
python3 -m preset_switcher
```

## 配置文件查找顺序

程序会在 Linux 和 Windows 上依次检查：

1. `OPENCODE_CONFIG_DIR` 指定的目录
2. `$XDG_CONFIG_HOME/opencode`
3. `~/.config/opencode`

每个目录中都会优先读取 `oh-my-opencode-slim.jsonc`，其次是
`oh-my-opencode-slim.json`。

> [!NOTE]
> 应用新预设后，会在下一次启动 OpenCode 时生效；如需立即使用，请重启 OpenCode。

## 快捷键

| 快捷键 | 功能 |
| --- | --- |
| `Ctrl+F` | 聚焦预设搜索框 |
| `Ctrl+R` | 重新读取配置 |
| `Enter` | 应用当前选择的预设 |
| 双击 | 打开所选预设的详情窗口 |

## 测试

```bash
python3 -m unittest discover -v
```

## 许可证

MIT。详见 [LICENSE](LICENSE)。
