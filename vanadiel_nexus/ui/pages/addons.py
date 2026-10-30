"""Addons: every Windower addon and plugin you have, what starts with the game, and quick actions."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QMenu, QStackedWidget

from ...core import windower
from .. import theme, widgets
from ..widgets import Column, DataTable
from .base import Page


class AddonsPage(Page):
    title = "Addons"
    key = "addons"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.kind = QComboBox()
        self.kind.addItems(["Addons and plugins", "Addons", "Plugins"])
        self.autoload_only = QCheckBox("Starts with game")
        self.toolbar = widgets.SearchToolbar("Search addons…")
        self.toolbar.add(self.kind, self.autoload_only, widgets.button("Rescan folder", "ghost", self.refresh))

        self.table = DataTable([
            Column("Name", "name", 220, tone=lambda r: theme.ACCENT if r["name"] == windower.ADDON_NAME else None),
            Column("Type", lambda r: "Addon" if r["kind"] == "addons" else "Plugin", 90),
            Column("Starts with game", lambda r: "Yes" if r["autoload"] else "—", 140, Qt.AlignCenter,
                   tone=lambda r: theme.SUCCESS if r["autoload"] else theme.FAINT),
            Column("Settings", lambda r: "settings.xml" if r["settings_file"] else "—", 130,
                   tone=lambda r: None if r["settings_file"] else theme.FAINT),
            Column("Folder", "folder", stretch=True, tone=lambda _r: theme.FAINT),
        ], sort_column=0, name="addons")
        self.toolbar.text_changed.connect(self.table.proxy.set_needle)
        self.kind.currentTextChanged.connect(self._apply_filters)
        self.autoload_only.toggled.connect(self._apply_filters)
        self.table.selectionModel().selectionChanged.connect(self._update_buttons)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        self.table.row_activated.connect(lambda _r: self._open_settings())

        self.choose_btn = widgets.button("Choose Windower folder", "primary", self._choose_windower)
        self.empty = widgets.EmptyState("Windower folder not found",
                                        "Point the app at the folder that contains windower.exe.", self.choose_btn)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.table)
        self.stack.addWidget(self.empty)

        self.autoload_btn = widgets.button("Start with game", on_click=self._toggle_autoload)
        self.load_btn = widgets.button("Load", on_click=lambda: self._live("load"))
        self.unload_btn = widgets.button("Unload", on_click=lambda: self._live("unload"))
        self.reload_btn = widgets.button("Reload", on_click=lambda: self._live("reload"))
        self.settings_btn = widgets.button("Open settings", on_click=self._open_settings)
        self.count = widgets.label("", "Caption")
        self.hint = widgets.label("In-app settings editing is coming in a later update.", "Caption")

        self.layout_.addWidget(self.toolbar)
        self.layout_.addWidget(self.stack, 1)
        self.layout_.addLayout(widgets.hbox(self.count, None, self.load_btn, self.unload_btn, self.reload_btn,
                                            self.autoload_btn, self.settings_btn))
        self.layout_.addWidget(self.hint)
        ctx.windower_changed.connect(lambda _p: self.refresh())
        ctx.bridge.connection_changed.connect(lambda _c: self._update_buttons())
        self.refresh()

    def refresh(self) -> None:
        wd = self.ctx.windower_dir
        found = windower.is_windower_dir(wd)
        self.stack.setCurrentIndex(0 if found else 1)
        rows = (windower.list_addons(wd) + windower.list_plugins(wd)) if found else []
        self.table.set_rows(rows)
        self._apply_filters()

    def on_shown(self) -> None:
        self.refresh()

    def _apply_filters(self, *_args) -> None:
        kind = {"Addons": "addons", "Plugins": "plugins"}.get(self.kind.currentText())
        only_auto = self.autoload_only.isChecked()
        self.table.proxy.set_predicate(lambda r: (not kind or r["kind"] == kind) and (not only_auto or r["autoload"]))
        rows = self.table.model_.rows
        self.count.setText(f"{sum(1 for r in rows if r['kind'] == 'addons')} addons · "
                           f"{sum(1 for r in rows if r['kind'] == 'plugins')} plugins · "
                           f"{sum(1 for r in rows if r['autoload'])} start with the game")
        self._update_buttons()

    def _update_buttons(self, *_args) -> None:
        row = self.table.selected_row()
        live = self.ctx.bridge.connected
        for b in (self.load_btn, self.unload_btn):
            b.setEnabled(bool(row) and live)
            b.setToolTip("" if live else "Needs the game running with the Nexus addon loaded")
        self.reload_btn.setEnabled(bool(row) and live and row["kind"] == "addons")
        is_addon = bool(row) and row["kind"] == "addons"
        self.autoload_btn.setEnabled(is_addon)
        self.autoload_btn.setText("Don't start with game" if is_addon and row["autoload"] else "Start with game")
        self.autoload_btn.setToolTip("Edits scripts/init.txt (a backup is kept)" if is_addon
                                     else "Plugins are set in the Windower launcher profile")
        self.settings_btn.setEnabled(bool(row) and bool(row["settings_file"]))

    def _toggle_autoload(self) -> None:
        row = self.table.selected_row()
        if not row or row["kind"] != "addons":
            return
        windower.set_autoload(self.ctx.windower_dir, row["name"], "addons", not row["autoload"])
        self.status(f"{row['name']} will {'not ' if row['autoload'] else ''}start with the game.")
        self.refresh()

    def _live(self, action: str) -> None:
        row = self.table.selected_row()
        if not row:
            return
        if row["kind"] == "addons":
            self.ctx.bridge.addon(action, row["name"])
        else:
            self.ctx.bridge.plugin(action, row["name"])
        self.status(f"Sent '{action} {row['name']}' to the game.")

    def _open_settings(self) -> None:
        row = self.table.selected_row()
        if row and row["settings_file"]:
            self.ctx.open_path(row["settings_file"])

    def _choose_windower(self) -> None:
        win = self.window()
        if hasattr(win, "choose_windower"):
            win.choose_windower()

    def _context_menu(self, pos) -> None:
        row = self.table.selected_row()
        if row is None:
            return
        menu = QMenu(self)
        if row["kind"] == "addons":
            menu.addAction(self.autoload_btn.text(), self._toggle_autoload)
        if row["settings_file"]:
            menu.addAction("Open settings", self._open_settings)
        menu.addAction("Open folder", lambda: self.ctx.open_path(row["folder"]))
        menu.exec(self.table.viewport().mapToGlobal(pos))
