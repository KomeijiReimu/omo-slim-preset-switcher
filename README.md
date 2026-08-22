# OpenCode Preset Switcher

一个零第三方运行依赖的 Tkinter 桌面工具，用于快速切换
`oh-my-opencode-slim` preset。界面支持中文和 English 即时切换。

## 功能

- 自动读取 `~/.config/opencode/oh-my-opencode-slim.jsonc` 或 `.json`
- `.jsonc` 与 `.json` 同时存在时优先使用 `.jsonc`
- 搜索并查看 preset、Agent 数、模型数与 provider
- 进入 preset 详情查看完整 Agent 配置，包括 model、variant、推理档位和其他嵌套字段
- 单击选择后应用，双击或点击“详情”进入详情窗口
- 原样保留 JSONC 注释、尾随逗号、缩进和换行
- 原子写入配置，避免产生部分文件

## 配置路径

程序会在 Linux、Windows 和 macOS 上按以下顺序查找配置文件：

1. `OPENCODE_CONFIG_DIR` 指定的目录
2. `XDG_CONFIG_HOME/opencode`
3. `~/.config/opencode`

环境变量为空时会跳过对应路径。每个目录都优先读取
`oh-my-opencode-slim.jsonc`，然后才读取 `.json`。这是 OpenCode 当前使用的
配置目录规则；程序不会默认改用 Windows `%APPDATA%` 或 macOS
`Library/Application Support`。

## 运行

需要 Python 3.11+ 和 Tkinter。项目只使用 Python 标准库，不需要第三方 pip
依赖，因此没有 `requirements.txt`：

```bash
python3 main.py
```

也可以从项目目录运行：

```bash
python3 -m preset_switcher
```

如系统提示缺少 `tkinter`，请安装发行版提供的 Python Tk 软件包。

应用 preset 后，新配置会在下一次 OpenCode 运行时生效；需要立即生效时请重启 OpenCode。

## 测试

```bash
python3 -m unittest discover -v
```
