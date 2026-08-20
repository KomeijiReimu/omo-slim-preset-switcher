# OpenCode Preset Switcher

一个零第三方运行依赖的 Tkinter 桌面工具，用于快速切换
`oh-my-opencode-slim` preset。界面支持中文和 English 即时切换。

## 功能

- 自动读取 `~/.config/opencode/oh-my-opencode-slim.jsonc` 或 `.json`
- `.jsonc` 与 `.json` 同时存在时优先使用 `.jsonc`
- 搜索并查看 preset、Agent 数、模型数与 provider
- 单击选择后应用，或双击 preset 快速应用
- 原样保留 JSONC 注释、尾随逗号、缩进和换行
- 原子写入配置，避免产生部分文件

## 运行

需要 Python 3.11+ 和 Tkinter：

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
