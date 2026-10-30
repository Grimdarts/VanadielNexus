"""My Addons tab: your own addons, kept in your folder and installed into Windower with one click."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMenu, QVBoxLayout, QWidget

from ..core import my_addons, windower
from . import theme, widgets
from .widgets import Column, DataTable


def _status(r) -> str:
    if not r["installed"]:
        return "Not installed"
    return "Up to date" if r["up_to_date"] else "Changes not installed"


def _tone(r):
    if not r["installed"]:
        return theme.FAINT
    return theme.SUCCESS if r["up_to_date"] else theme.WARNING


class MyAddonsView(QWidget):
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.ctx = page.ctx
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        self.folder_label = widgets.label("", "Caption", wrap=True)
        lay.addLayout(widgets.hbox(self.folder_label, None,
                                   widgets.button("Change folder…", "ghost", self._choose_folder),
                                   widgets.button("Open folder", "ghost", lambda: self._open(self.folder())),
                                   widgets.button("New addon…", "primary", self._new)))

        self.table = DataTable([
            Column("Name", "name", 220),
            Column("Status", _status, 200, tone=_tone),
            Column("Your copy", "folder", stretch=True, tone=lambda _r: theme.FAINT),
        ], sort_column=0, name="my-addons")
        self.table.row_activated.connect(lambda _r: self._install(reload=False))
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        self.table.selectionModel().selectionChanged.connect(self._update_buttons)

        self.empty = widgets.EmptyState(
            "No addons of your own yet",
            "Click New addon to start one from a ready-to-run template, or copy an addon folder into "
            "your My Addons folder.")
        lay.addWidget(self.table, 1)
        lay.addWidget(self.empty, 1)

        self.install_btn = widgets.button("Install / update", on_click=lambda: self._install(reload=False))
        self.reload_btn = widgets.button("Install and reload in game", on_click=lambda: self._install(reload=True))
        self.edit_btn = widgets.button("Edit settings", on_click=self._settings)
        lay.addLayout(widgets.hbox(
            widgets.label("Installing copies your files into Windower and never touches the addon's saved "
                          "settings (its data folder).", "Caption", wrap=True),
            None, self.edit_btn, self.install_btn, self.reload_btn))
        self.ctx.bridge.connection_changed.connect(lambda _c: self._update_buttons())
        self.refresh()

    def folder(self) -> str:
        return self.ctx.settings.get("my_addons_dir") or my_addons.default_dir()

    def refresh(self) -> None:
        folder = self.folder()
        self.folder_label.setText(f"Your addons live in {folder}")
        rows = my_addons.list_my_addons(folder, self.ctx.windower_dir)
        self.table.set_rows(rows)
        self.table.setVisible(bool(rows))
        self.empty.setVisible(not rows)
        self._update_buttons()

    def _update_buttons(self, *_args) -> None:
        row = self.table.selected_row()
        found = windower.is_windower_dir(self.ctx.windower_dir)
        self.install_btn.setEnabled(bool(row) and found)
        self.reload_btn.setEnabled(bool(row) and found and self.ctx.bridge.connected)
        self.reload_btn.setToolTip("" if self.ctx.bridge.connected else "Needs the game running with the Nexus addon")
        self.edit_btn.setEnabled(bool(row) and row["installed"])

    def _open(self, path: str) -> None:
        os.makedirs(path, exist_ok=True)
        self.ctx.open_path(path)

    def _choose_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose your My Addons folder", self.folder())
        if path:
            self.ctx.settings.set("my_addons_dir", os.path.normpath(path))
            self.refresh()

    def _new(self) -> None:
        name, ok = QInputDialog.getText(self, "New addon", "Addon name (letters, numbers or _):")
        if not ok or not name.strip():
            return
        try:
            folder = my_addons.create(self.folder(), name.strip(), self.ctx.bridge.state.get("player_name", ""))
        except (ValueError, FileExistsError) as e:
            self.page.info("Couldn't create the addon", str(e))
            return
        self.refresh()
        self.page.status(f"Created {name.strip()}. Edit {name.strip()}.lua, then Install.")
        self._open(folder)

    def _install(self, reload: bool) -> None:
        row = self.table.selected_row()
        if not row or not windower.is_windower_dir(self.ctx.windower_dir):
            return
        copied = my_addons.install(row["folder"], self.ctx.windower_dir)
        if reload and self.ctx.bridge.connected:
            self.ctx.bridge.addon("reload" if row["installed"] else "load", row["name"])
        verb = "Installed" if not row["installed"] else ("Updated" if copied else "Already up to date:")
        self.page.status(f"{verb} {row['name']}" + (" and reloaded it in game." if reload else "."))
        self.refresh()
        self.page.refresh()

    def _settings(self) -> None:
        row = self.table.selected_row()
        if not row:
            return
        installed = next((a for a in self.page.table.model_.rows if a["name"].lower() == row["name"].lower()), None)
        if installed:
            self.page.edit_settings_for(installed)

    def _context_menu(self, pos) -> None:
        row = self.table.selected_row()
        if not row:
            return
        menu = QMenu(self)
        menu.addAction("Install / update", lambda: self._install(reload=False))
        menu.addAction("Open your copy", lambda: self._open(row["folder"]))
        if row["installed"]:
            menu.addAction("Open installed copy",
                           lambda: self._open(os.path.join(self.ctx.windower_dir, "addons", row["name"])))
        menu.exec(self.table.viewport().mapToGlobal(pos))
