"""Bilingual Tkinter GUI for switching OpenCode presets.

Importing this module never creates a Tk root; call :func:`main` (or
``python -m preset_switcher``) to create the window and run the Tk loop.
"""

from __future__ import annotations

import locale
import json
import os
import tkinter as tk
from tkinter import ttk
from typing import Any

from .config import ConfigError, ConfigSnapshot, load_config, set_active_preset

__all__ = [
    "PresetDetailsWindow",
    "PresetSwitcherApp",
    "TRANSLATIONS",
    "can_apply_preset",
    "detect_language",
    "format_preset_details",
    "main",
    "summarize_preset",
]

TRANSLATIONS: dict[str, dict[str, str]] = {
    "zh": {
        "window_title": "OpenCode 预设切换器",
        "header_title": "OpenCode 预设切换器",
        "switch_language": "English",
        "current_preset": "当前预设：{name}",
        "config_path": "配置文件：{path}",
        "no_value": "-",
        "search_label": "搜索",
        "column_preset": "预设",
        "column_agents": "Agent 数",
        "column_models": "Model 数",
        "column_providers": "Providers",
        "refresh_button": "刷新",
        "details_button": "详情",
        "apply_button": "应用",
        "details_title": "预设详情：{name}",
        "detail_name": "预设：{name}",
        "detail_summary": "Agent {agents}  ·  Model {models}  ·  Provider {providers}",
        "detail_config": "完整配置",
        "close_button": "关闭",
        "status_loading": "正在加载配置…",
        "status_refreshed": "已刷新：共 {count} 个预设，当前为「{active}」",
        "status_applied": "已应用预设「{name}」，将在下次 OpenCode 运行时生效",
        "status_already_active": "「{name}」已是当前预设",
        "status_select": "请先选择一个预设",
        "status_no_config": "配置未加载，请先刷新",
        "status_refresh_error": "加载配置失败：{error}",
        "status_apply_error": "应用失败：{error}",
        "empty_all": "配置中没有预设",
        "empty_search": "没有匹配的预设",
    },
    "en": {
        "window_title": "OpenCode Preset Switcher",
        "header_title": "OpenCode Preset Switcher",
        "switch_language": "中文",
        "current_preset": "Current preset: {name}",
        "config_path": "Config file: {path}",
        "no_value": "-",
        "search_label": "Search",
        "column_preset": "Preset",
        "column_agents": "Agents",
        "column_models": "Models",
        "column_providers": "Providers",
        "refresh_button": "Refresh",
        "details_button": "Details",
        "apply_button": "Apply",
        "details_title": "Preset details: {name}",
        "detail_name": "Preset: {name}",
        "detail_summary": "Agents {agents}  ·  Models {models}  ·  Providers {providers}",
        "detail_config": "Complete configuration",
        "close_button": "Close",
        "status_loading": "Loading configuration...",
        "status_refreshed": "Refreshed: {count} presets, active: {active}",
        "status_applied": "Applied preset: {name}; it will take effect the next time OpenCode runs",
        "status_already_active": "{name} is already the active preset",
        "status_select": "Select a preset first",
        "status_no_config": "Configuration not loaded, refresh first",
        "status_refresh_error": "Failed to load configuration: {error}",
        "status_apply_error": "Failed to apply: {error}",
        "empty_all": "No presets in configuration",
        "empty_search": "No matching presets",
    },
}

_STATUS_COLORS = {"info": "#333333", "success": "#1a7f37", "error": "#c62828"}


def detect_language() -> str:
    """Detect the UI language from locale environment variables.

    Falls back to English when no locale information is available.
    """
    for variable in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(variable)
        if not value:
            continue
        base = value.split(".", 1)[0].lower()
        if base.startswith("zh"):
            return "zh"
        if base.startswith("en"):
            return "en"
    try:
        default = locale.getdefaultlocale()[0]
    except Exception:
        default = None
    if default and default.lower().startswith("zh"):
        return "zh"
    return "en"


def summarize_preset(preset_config: dict[str, Any]) -> tuple[str, str, str]:
    """Summarize agent blocks as display values for the preset list."""
    if not isinstance(preset_config, dict):
        return "-", "-", "-"

    agent_blocks = [value for value in preset_config.values() if isinstance(value, dict)]
    model_ids = {
        model.strip()
        for block in agent_blocks
        for model in (block.get("model"),)
        if isinstance(model, str) and model.strip()
    }
    providers = sorted(
        {
            model_id.split("/", 1)[0]
            for model_id in model_ids
            if "/" in model_id and model_id.split("/", 1)[0]
        }
    )
    return (
        str(len(agent_blocks)),
        str(len(model_ids)),
        ", ".join(providers) if providers else "-",
    )


def format_preset_details(preset_config: dict[str, Any]) -> str:
    """Return the complete preset configuration as readable JSON.

    The whole dictionary is serialized instead of selecting known fields. This
    keeps nested values and newly added configuration keys visible in the UI.
    """
    if not isinstance(preset_config, dict):
        preset_config = {}
    return json.dumps(
        preset_config,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


def can_apply_preset(active_preset: str | None, selected_preset: str | None) -> bool:
    """Return whether a selected preset is a different preset to the active one."""
    return bool(selected_preset and selected_preset != active_preset)


class PresetDetailsWindow:
    """A read-only, bilingual view of one preset's complete configuration."""

    def __init__(
        self,
        app: "PresetSwitcherApp",
        name: str,
        preset_config: dict[str, Any],
    ) -> None:
        self.app = app
        self.name = name
        self.preset_config = preset_config
        self.window = tk.Toplevel(app.root)
        self.window.minsize(620, 480)
        self.window.geometry("760x620")
        self.window.transient(app.root)
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        self._build_widgets()
        self._bind_events()
        self._apply_language()
        self.window.after_idle(self.close_button.focus_set)

    def _build_widgets(self) -> None:
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(3, weight=1)

        header = ttk.Frame(self.window, padding=(16, 14, 16, 8))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        self.title_label = ttk.Label(header, font=("TkDefaultFont", 14, "bold"))
        self.title_label.grid(row=0, column=0, sticky="w")
        self.language_button = ttk.Button(
            header,
            width=8,
            command=self.app._toggle_language,
        )
        self.language_button.grid(row=0, column=1, sticky="e")

        self.name_label = ttk.Label(
            self.window,
            padding=(16, 0, 16, 3),
            font=("TkDefaultFont", 11, "bold"),
        )
        self.name_label.grid(row=1, column=0, sticky="w")
        self.summary_label = ttk.Label(self.window, padding=(16, 0, 16, 8))
        self.summary_label.grid(row=2, column=0, sticky="w")

        text_frame = ttk.Frame(self.window, padding=(16, 0, 16, 8))
        text_frame.grid(row=3, column=0, sticky="nsew")
        text_frame.rowconfigure(1, weight=1)
        text_frame.columnconfigure(0, weight=1)
        self.config_label = ttk.Label(text_frame)
        self.config_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))
        self.config_text = tk.Text(
            text_frame,
            wrap="none",
            state="disabled",
            padx=10,
            pady=8,
            takefocus=True,
            undo=False,
        )
        self.config_text.grid(row=1, column=0, sticky="nsew")
        vertical_scrollbar = ttk.Scrollbar(
            text_frame,
            orient="vertical",
            command=self.config_text.yview,
        )
        vertical_scrollbar.grid(row=1, column=1, sticky="ns")
        horizontal_scrollbar = ttk.Scrollbar(
            text_frame,
            orient="horizontal",
            command=self.config_text.xview,
        )
        horizontal_scrollbar.grid(row=2, column=0, sticky="ew")
        self.config_text.configure(
            yscrollcommand=vertical_scrollbar.set,
            xscrollcommand=horizontal_scrollbar.set,
        )

        footer = ttk.Frame(self.window, padding=(16, 0, 16, 14))
        footer.grid(row=4, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        self.apply_button = ttk.Button(footer, command=self._apply)
        self.apply_button.grid(row=0, column=1, padx=(0, 8))
        self.close_button = ttk.Button(footer, command=self.close)
        self.close_button.grid(row=0, column=2)

    def _bind_events(self) -> None:
        self.window.bind("<Escape>", lambda _event: self.close())
        self.window.bind("<Control-w>", lambda _event: self.close())
        self.window.bind("<Return>", lambda _event: self._apply())

    def _apply_language(self) -> None:
        agents, models, providers = summarize_preset(self.preset_config)
        self.window.title(self.app.t("details_title", name=self.name))
        self.title_label.configure(text=self.app.t("details_title", name=self.name))
        self.language_button.configure(text=self.app.t("switch_language"))
        self.name_label.configure(text=self.app.t("detail_name", name=self.name))
        self.summary_label.configure(
            text=self.app.t(
                "detail_summary",
                agents=agents,
                models=models,
                providers=providers,
            )
        )
        self.config_label.configure(text=self.app.t("detail_config"))
        self.apply_button.configure(text=self.app.t("apply_button"))
        self.close_button.configure(text=self.app.t("close_button"))
        self._update_config_text()
        self._update_apply_state()

    def _update_config_text(self) -> None:
        self.config_text.configure(state="normal")
        self.config_text.delete("1.0", "end")
        self.config_text.insert("1.0", format_preset_details(self.preset_config))
        self.config_text.configure(state="disabled")

    def _update_apply_state(self) -> None:
        active = self.app.snapshot is not None and self.name == self.app.snapshot.active_preset
        self.apply_button.state(["disabled"] if active else ["!disabled"])

    def _apply(self) -> None:
        if self.app._apply_name(self.name):
            self.close()
        else:
            self._update_apply_state()

    def close(self) -> None:
        if self.window.winfo_exists():
            self.window.destroy()
        if self.app.detail_window is self:
            self.app.detail_window = None


class PresetSwitcherApp:
    """Tk application window for browsing and switching presets."""

    def __init__(self) -> None:
        self.language = detect_language()
        self.snapshot: ConfigSnapshot | None = None
        self.detail_window: PresetDetailsWindow | None = None
        self._status: tuple[str, dict[str, str], str] | None = None

        self.root = tk.Tk()
        self.root.minsize(720, 520)
        self.root.geometry("900x650")

        self._build_widgets()
        self._bind_events()
        self._apply_language()
        self._refresh()

    def run(self) -> None:
        """Start the Tk event loop."""
        self.root.mainloop()

    def t(self, key: str, **kwargs: str) -> str:
        """Return the translated template for *key* in the current language."""
        table = TRANSLATIONS.get(self.language, TRANSLATIONS["en"])
        template = table.get(key)
        if template is None:
            template = TRANSLATIONS["en"].get(key, key)
        return template.format(**kwargs) if kwargs else template

    # -- widget construction ---------------------------------------------

    def _build_widgets(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(3, weight=1)

        header = ttk.Frame(self.root, padding=(12, 10, 12, 6))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        self.header_label = ttk.Label(header, font=("TkDefaultFont", 14, "bold"))
        self.header_label.grid(row=0, column=0, sticky="w")
        self.language_button = ttk.Button(header, width=8, command=self._toggle_language)
        self.language_button.grid(row=0, column=1, sticky="e")

        info = ttk.Frame(self.root, padding=(12, 0, 12, 6))
        info.grid(row=1, column=0, sticky="ew")
        self.current_label = ttk.Label(info)
        self.current_label.grid(row=0, column=0, sticky="w")
        self.path_label = ttk.Label(info, foreground="#666666")
        self.path_label.grid(row=1, column=0, sticky="w")

        toolbar = ttk.Frame(self.root, padding=(12, 0, 12, 6))
        toolbar.grid(row=2, column=0, sticky="ew")
        toolbar.columnconfigure(1, weight=1)
        self.search_label = ttk.Label(toolbar)
        self.search_label.grid(row=0, column=0, padx=(0, 6))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._on_search())
        self.search_entry = ttk.Entry(toolbar, textvariable=self.search_var)
        self.search_entry.grid(row=0, column=1, sticky="ew")

        tree_frame = ttk.Frame(self.root, padding=(12, 0, 12, 6))
        tree_frame.grid(row=3, column=0, sticky="nsew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(
            tree_frame,
            columns=("preset", "agents", "models", "providers"),
            show="headings",
            selectmode="browse",
        )
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.column("preset", width=240, anchor="w")
        self.tree.column("agents", width=100, anchor="center")
        self.tree.column("models", width=100, anchor="center")
        self.tree.column("providers", width=120, anchor="center")
        self.tree.tag_configure("active", foreground="#1a7f37")
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.empty_label = ttk.Label(tree_frame, anchor="center", foreground="#888888")

        buttons = ttk.Frame(self.root, padding=(12, 0, 12, 10))
        buttons.grid(row=4, column=0, sticky="ew")
        self.refresh_button = ttk.Button(buttons, command=self._refresh)
        self.refresh_button.grid(row=0, column=0, padx=(0, 8))
        self.details_button = ttk.Button(
            buttons,
            command=self._open_details,
            state="disabled",
        )
        self.details_button.grid(row=0, column=1, padx=(0, 8))
        self.apply_button = ttk.Button(
            buttons, command=self._apply_selected, state="disabled"
        )
        self.apply_button.grid(row=0, column=2)

        self.status_label = tk.Label(
            self.root, anchor="w", relief=tk.SUNKEN, bd=1, padx=8, pady=3
        )
        self.status_label.grid(row=5, column=0, sticky="ew")

    def _bind_events(self) -> None:
        self.tree.bind("<<TreeviewSelect>>", lambda _event: self._on_selection())
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Return>", lambda _event: self._apply_selected())
        self.search_entry.bind("<Return>", lambda _event: self._apply_selected())
        self.root.bind("<Control-r>", lambda _event: self._refresh())
        self.root.bind("<Control-R>", lambda _event: self._refresh())
        self.root.bind("<Control-f>", lambda _event: self._focus_search())
        self.root.bind("<Control-F>", lambda _event: self._focus_search())
        self.root.bind("<Command-r>", lambda _event: self._refresh())
        self.root.bind("<Command-R>", lambda _event: self._refresh())
        self.root.bind("<Command-f>", lambda _event: self._focus_search())
        self.root.bind("<Command-F>", lambda _event: self._focus_search())

    # -- language / rendering --------------------------------------------

    def _apply_language(self) -> None:
        """Re-render every piece of text in the current language."""
        self.root.title(self.t("window_title"))
        self.header_label.configure(text=self.t("header_title"))
        self.language_button.configure(text=self.t("switch_language"))
        self.search_label.configure(text=self.t("search_label"))
        headings = (
            ("preset", "column_preset"),
            ("agents", "column_agents"),
            ("models", "column_models"),
            ("providers", "column_providers"),
        )
        for column, key in headings:
            self.tree.heading(column, text=self.t(key))
        self.refresh_button.configure(text=self.t("refresh_button"))
        self.details_button.configure(text=self.t("details_button"))
        self.apply_button.configure(text=self.t("apply_button"))
        self._update_info_labels()
        self._update_empty_state()
        if self._status is not None:
            key, kwargs, kind = self._status
            self._render_status(key, kwargs, kind)
        if self.detail_window is not None:
            self.detail_window._apply_language()

    def _toggle_language(self) -> None:
        self.language = "en" if self.language == "zh" else "zh"
        self._apply_language()

    def _set_status(self, key: str, kind: str = "info", **kwargs: str) -> None:
        self._status = (key, kwargs, kind)
        self._render_status(key, kwargs, kind)

    def _render_status(self, key: str, kwargs: dict[str, str], kind: str) -> None:
        self.status_label.configure(
            text=self.t(key, **kwargs),
            fg=_STATUS_COLORS.get(kind, _STATUS_COLORS["info"]),
        )

    def _update_info_labels(self) -> None:
        if self.snapshot is None:
            name = path = self.t("no_value")
        else:
            name = self.snapshot.active_preset
            path = str(self.snapshot.path)
        self.current_label.configure(text=self.t("current_preset", name=name))
        self.path_label.configure(text=self.t("config_path", path=path))

    def _update_empty_state(self, no_rows: bool = False) -> None:
        has_presets = bool(self.snapshot is not None and self.snapshot.presets)
        if no_rows or not self.tree.get_children():
            text = self.t("empty_search" if has_presets else "empty_all")
            self.empty_label.configure(text=text)
            self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
        else:
            self.empty_label.place_forget()

    # -- configuration interactions --------------------------------------

    def _refresh(self) -> None:
        """Reload the configuration through the real config API."""
        if self.detail_window is not None:
            self.detail_window.close()
        self._set_status("status_loading")
        self.root.update_idletasks()
        try:
            self.snapshot = load_config()
        except ConfigError as exc:
            self.snapshot = None
            self._populate_tree()
            self._update_info_labels()
            self._set_status("status_refresh_error", kind="error", error=str(exc))
            return
        self._populate_tree()
        self._update_info_labels()
        self._set_status(
            "status_refreshed",
            kind="success",
            count=str(len(self.snapshot.presets)),
            active=self.snapshot.active_preset,
        )

    def _populate_tree(self) -> None:
        self.tree.delete(*self.tree.get_children())
        if self.snapshot is None:
            self._update_empty_state()
            self._on_selection()
            return
        query = self.search_var.get().strip().lower()
        visible = 0
        for name, preset_config in self.snapshot.presets.items():
            if query and query not in name.lower():
                continue
            values = (name, *summarize_preset(preset_config))
            tags = ("active",) if name == self.snapshot.active_preset else ()
            self.tree.insert("", "end", iid=name, values=values, tags=tags)
            visible += 1
        self._update_empty_state(visible == 0)
        self._on_selection()

    def _apply_selected(self) -> None:
        selection = self.tree.selection()
        if not selection:
            self._set_status("status_select")
            return
        self._apply_name(selection[0])

    def _apply_name(self, name: str) -> bool:
        if self.snapshot is None:
            self._set_status("status_no_config", kind="error")
            return False
        if name == self.snapshot.active_preset:
            self._set_status("status_already_active", name=name)
            return False
        try:
            self.snapshot = set_active_preset(name, self.snapshot.path)
        except ConfigError as exc:
            self._set_status("status_apply_error", kind="error", error=str(exc))
            return False
        self._populate_tree()
        self._update_info_labels()
        if self.tree.exists(name):
            self.tree.selection_set(name)
            self.tree.focus(name)
            self.tree.see(name)
        self._set_status("status_applied", kind="success", name=name)
        return True

    # -- event handlers ---------------------------------------------------

    def _on_selection(self) -> None:
        selection = self.tree.selection()
        if not selection:
            self.details_button.state(["disabled"])
            self.apply_button.state(["disabled"])
            if self.detail_window is not None:
                self.detail_window._update_apply_state()
            return
        name = selection[0]
        self.details_button.state(["!disabled"])
        self.apply_button.state(
            ["!disabled"] if can_apply_preset(
                self.snapshot.active_preset if self.snapshot is not None else None,
                name,
            ) else ["disabled"]
        )
        if self.detail_window is not None:
            self.detail_window._update_apply_state()

    def _on_double_click(self, event: tk.Event) -> None:
        row = self.tree.identify_row(event.y)
        if not row:
            return
        self.tree.selection_set(row)
        self.tree.focus(row)
        self._open_details()

    def _open_details(self) -> None:
        selection = self.tree.selection()
        if not selection:
            self._set_status("status_select")
            return
        if self.snapshot is None:
            self._set_status("status_no_config", kind="error")
            return

        name = selection[0]
        if self.detail_window is not None:
            if self.detail_window.window.winfo_exists() and self.detail_window.name == name:
                self.detail_window.window.deiconify()
                self.detail_window.window.lift()
                self.detail_window.window.focus_force()
                return
            self.detail_window.close()
        self.detail_window = PresetDetailsWindow(self, name, self.snapshot.presets[name])

    def _on_search(self) -> None:
        self._populate_tree()

    def _focus_search(self) -> None:
        self.search_entry.focus_set()
        self.search_entry.selection_range(0, "end")


def main() -> None:
    """Create the application window and run the Tk event loop."""
    PresetSwitcherApp().run()


if __name__ == "__main__":
    main()
