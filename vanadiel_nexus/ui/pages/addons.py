"""Addons: every Windower addon and plugin you have, what starts with the game, and quick actions."""
import os

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtWidgets import (
    QInputDialog,
    QCheckBox, QComboBox, QFrame, QHBoxLayout, QMenu, QStackedWidget, QTabBar, QVBoxLayout, QWidget,
)

from ...core import addon_info, addon_updates, windower
from .. import theme, widgets
from ..addon_settings_dialog import AddonSettingsDialog
from ..my_addons_view import MyAddonsView
from ..widgets import Column, DataTable
from .base import Page


UPDATE_LABELS = {"up_to_date": "Up to date", "update_available": "Update available",
                 "no_source": "—", "error": "Check failed"}


class _ScanSignals(QObject):
    done = Signal(dict)


class _Scan(QRunnable):
    def __init__(self, addons, sources):
        super().__init__()
        self.addons, self.sources = addons, sources
        self.signals = _ScanSignals()

    def run(self):
        self.signals.done.emit(addon_updates.scan(self.addons, self.sources))


class AddonsPage(Page):
    title = "Addons"
    key = "addons"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.kind = QComboBox()
        self.kind.addItems(["Addons and plugins", "Addons", "Plugins"])
        self.autoload_only = QCheckBox("Starts with game")
        self.toolbar = widgets.SearchToolbar("Search addons…")
        self.updates = {}
        self.scan_btn = widgets.button("Scan for updates", "primary", self._scan_updates,
                                       tooltip="Compares each addon with its source on GitHub")
        self.update_all_btn = widgets.button("Update all", on_click=self._update_all)
        self.update_all_btn.hide()
        self.toolbar.add(self.kind, self.autoload_only, widgets.button("Rescan folder", "ghost", self.refresh),
                         self.update_all_btn, self.scan_btn)

        self.table = DataTable([
            Column("Name", "name", 220, tone=lambda r: theme.ACCENT if r["name"] == windower.ADDON_NAME else None),
            Column("Type", lambda r: "Addon" if r["kind"] == "addons" else "Plugin", 90),
            Column("Updates", self._update_label, 150, tone=self._update_tone, tooltip=self._update_tooltip),
            Column("Starts with game", lambda r: "Yes" if r["autoload"] else "—", 140, Qt.AlignCenter,
                   tone=lambda r: theme.SUCCESS if r["autoload"] else theme.FAINT),
            Column("Startup source", lambda r: ", ".join(r.get("autoload_sources", [])) or "—", 180),
            Column("Settings", lambda r: "Editable" if r["settings_file"] else "—", 110,
                   tone=lambda r: None if r["settings_file"] else theme.FAINT),
            Column("Description", lambda r: r.get("description") or "—", 380,
                   tone=lambda r: None if r.get("description") else theme.FAINT),
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
        self.settings_btn = widgets.button("Edit settings", on_click=self._open_settings)
        self.update_btn = widgets.button("Update", on_click=self._update_selected)
        self.update_btn.hide()
        self.count = widgets.label("", "Caption")
        self.hint = widgets.label("Startup is configured, not live loaded state. Double-click an addon to edit its settings. "
                                  "Load, Unload and Reload need the game "
                                  "running with the Nexus addon loaded.", "Caption")

        self.gearinfo = self._build_gearinfo_card()
        installed = QWidget()
        il = QVBoxLayout(installed)
        il.setContentsMargins(0, 0, 0, 0)
        il.setSpacing(14)
        il.addWidget(self.gearinfo)
        il.addWidget(self.toolbar)
        il.addWidget(self.stack, 1)
        il.addLayout(widgets.hbox(self.count, None, self.update_btn, self.load_btn, self.unload_btn, self.reload_btn,
                                  self.autoload_btn, self.settings_btn))
        il.addWidget(self.hint)

        self.tabs = QTabBar()
        self.tabs.setExpanding(False)
        self.tabs.setDrawBase(False)
        self.tabs.addTab("Installed")
        self.tabs.addTab("My Addons")
        self.views = QStackedWidget()
        self.views.addWidget(installed)
        self.my_addons = MyAddonsView(self)
        self.views.addWidget(self.my_addons)
        self.tabs.currentChanged.connect(self._switch_view)
        self.layout_.addLayout(widgets.hbox(self.tabs, None))
        self.layout_.addWidget(self.views, 1)
        ctx.windower_changed.connect(lambda _p: self.refresh())
        ctx.bridge.connection_changed.connect(lambda _c: (self._update_buttons(), self._refresh_gearinfo()))
        self.refresh()

    # --- GearInfo card ------------------------------------------------------
    def _build_gearinfo_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        row = QHBoxLayout(card)
        row.setContentsMargins(16, 12, 16, 12)
        text = QVBoxLayout()
        text.setSpacing(2)
        self.gi_title = widgets.label("GearInfo", "SectionTitle")
        self.gi_detail = widgets.label("", "Caption", wrap=True)
        text.addWidget(self.gi_title)
        text.addWidget(self.gi_detail)
        self.gi_pill = widgets.pill("")
        row.addWidget(self.gi_pill)
        row.addLayout(text, 1)
        row.addWidget(widgets.button("Edit settings", on_click=self._gearinfo_settings))
        self.gi_reload = widgets.button("Reload in game", on_click=lambda: self._gearinfo_live("reload"))
        row.addWidget(self.gi_reload)
        return card

    def _gearinfo_row(self):
        return next((r for r in self.table.model_.rows if r["name"].lower() == "gearinfo"), None)

    def _refresh_gearinfo(self) -> None:
        row = self._gearinfo_row()
        self.gearinfo.setVisible(row is not None)
        if row is None:
            return
        patched = False
        try:
            with open(os.path.join(row["folder"], "Buff_Processing.lua"), encoding="utf-8", errors="ignore") as f:
                patched = "apply_unknown_haste_buffs" in f.read()
        except OSError:
            pass
        self.gi_pill.setText("Haste fix on" if patched else "Original")
        widgets.set_tone(self.gi_pill, "success" if patched else "")
        self.gi_detail.setText(
            "In-game overlay for haste, Dual Wield and stats. Buffs it can't match to a caster now count: "
            "Haste as Haste II, Marches and Geo-Haste using the bard and geomancer bonuses under "
            "'Assume' in Edit settings." if patched else
            "In-game overlay for haste, Dual Wield and stats. This copy doesn't have the haste fix.")
        self.gi_reload.setEnabled(self.ctx.bridge.connected)
        self.gi_reload.setToolTip("" if self.ctx.bridge.connected else "Needs the game running with the Nexus addon")

    def _gearinfo_settings(self) -> None:
        row = self._gearinfo_row()
        if row and AddonSettingsDialog(self, self.ctx, row).exec():
            self.status("Saved GearInfo settings" + (" and reloaded it." if self.ctx.bridge.connected
                                                     else ". Reload GearInfo in game to apply."))

    def _gearinfo_live(self, action: str) -> None:
        self.ctx.bridge.addon(action, "GearInfo")
        self.status("Reloading GearInfo in game.")

    def refresh(self) -> None:
        wd = self.ctx.windower_dir
        found = windower.is_windower_dir(wd)
        self.stack.setCurrentIndex(0 if found else 1)
        rows = (windower.list_addons(wd) + windower.list_plugins(wd)) if found else []
        for r in rows:
            r["description"] = addon_info.describe(r["name"], r["kind"], r["folder"] if r["kind"] == "addons" else "")
        self.table.set_rows(rows)
        self._apply_filters()
        self._refresh_gearinfo()

    def on_shown(self) -> None:
        self.refresh()
        self.my_addons.refresh()

    def _switch_view(self, index: int) -> None:
        self.views.setCurrentIndex(index)
        if index == 1:
            self.my_addons.refresh()

    def edit_settings_for(self, row: dict) -> None:
        if row.get("settings_file") and AddonSettingsDialog(self, self.ctx, row).exec():
            self.status(f"Saved {row['name']} settings" +
                        (" and reloaded it in game." if self.ctx.bridge.connected else ". Reload it in game to apply."))
        elif not row.get("settings_file"):
            self.info("No settings yet", f"{row['name']} hasn't saved a settings file yet. Load it in game once, "
                                         "then its settings show up here.")

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
        managed = [s for s in row.get("autoload_sources", []) if s != "scripts/init.txt"] if row else []
        self.autoload_btn.setEnabled(is_addon and not managed)
        self.autoload_btn.setText("Don't start with game" if is_addon and row["autoload"] else "Start with game")
        self.autoload_btn.setToolTip("Managed by " + ", ".join(managed) + "; edit that source instead."
                                     if managed else "Edits scripts/init.txt (a backup is kept)" if is_addon
                                     else "Plugins are set in the Windower launcher profile")
        self.settings_btn.setEnabled(bool(row) and bool(row["settings_file"]))
        result = self.updates.get(row["name"]) if row else None
        self.update_btn.setVisible(bool(result) and result["status"] == "update_available")

    def _toggle_autoload(self) -> None:
        row = self.table.selected_row()
        if not row or row["kind"] != "addons":
            return
        try:
            windower.set_autoload(self.ctx.windower_dir, row["name"], "addons", not row["autoload"])
        except (ValueError, OSError) as exc:
            self.status(f"Startup unchanged: {exc}")
            self.refresh()
            return
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
            self.edit_settings_for(row)

    # --- updates ------------------------------------------------------------
    def _sources(self) -> dict:
        return dict(self.ctx.settings.get("addon_sources") or {})

    def _update_label(self, r) -> str:
        if r["kind"] != "addons":
            return ""
        res = self.updates.get(r["name"])
        return UPDATE_LABELS.get(res["status"], "") if res else ""

    def _update_tone(self, r):
        res = self.updates.get(r["name"])
        return {"up_to_date": theme.SUCCESS, "update_available": theme.WARNING,
                "error": theme.DANGER}.get(res["status"], theme.FAINT) if res else None

    def _update_tooltip(self, r):
        res = self.updates.get(r["name"])
        if not res:
            return "Click Scan for updates to check" if r["kind"] == "addons" else None
        if res["status"] == "update_available":
            return "Changed files: " + ", ".join(res["changed"][:12]) + (" …" if len(res["changed"]) > 12 else "")
        if res["status"] == "no_source":
            return "Not an official Windower addon. Right-click > Set update source… to add its GitHub page."
        if res["status"] == "error":
            return res.get("error", "")
        src = res.get("source", {})
        return f"Matches {src.get('owner')}/{src.get('repo')} ({src.get('branch')})"

    def _scan_updates(self) -> None:
        addons = [r for r in self.table.model_.rows if r["kind"] == "addons"]
        if not addons:
            return
        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("Checking…")
        self.status(f"Checking {len(addons)} addons against GitHub…")
        job = _Scan(addons, self._sources())
        job.signals.done.connect(self._scan_done)
        self._scan_job = job  # keep the signals object alive until it fires
        QThreadPool.globalInstance().start(job)

    def _refresh_update_count(self) -> list:
        pending = [n for n, r in self.updates.items() if r["status"] == "update_available"]
        self.update_all_btn.setText(f"Update all ({len(pending)})")
        self.update_all_btn.setVisible(bool(pending))
        self.table.model_.layoutChanged.emit()
        self._update_buttons()
        return pending

    def _scan_done(self, results: dict) -> None:
        self.updates = results
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("Scan for updates")
        pending = self._refresh_update_count()
        errors = [n for n, r in results.items() if r["status"] == "error"]
        msg = (f"{len(pending)} update{'s' if len(pending) != 1 else ''} available" if pending
               else "Every addon with a known source is up to date")
        if errors:
            msg += f" · {len(errors)} couldn't be checked ({results[errors[0]].get('error', '')[:80]})"
        self.status(msg + ".")

    def _confirm_update(self, names: list) -> bool:
        files = sum(len(self.updates[n]["changed"]) for n in names)
        after = ("Updated addons are reloaded in game." if self.ctx.bridge.connected
                 else "Reload them in game afterwards, or restart the game.")
        return self.confirm(
            "Update addons",
            f"Update {', '.join(names)} ({files} file{'s' if files != 1 else ''})?\n\n"
            "Each addon folder is zipped to your data\\backups folder first, and its saved settings "
            f"(the data folder) are never touched.\n\n{after}", "Update")

    def _run_updates(self, names: list) -> None:
        rows = {r["name"]: r for r in self.table.model_.rows}
        backup_dir = os.path.join(self.ctx.data_dir, "backups")
        done, failed = [], []
        for name in names:
            try:
                addon_updates.apply_update(rows[name]["folder"], self.updates[name], backup_dir)
                self.updates[name] = {**self.updates[name], "status": "up_to_date", "changed": []}
                done.append(name)
                if self.ctx.bridge.connected:
                    self.ctx.bridge.addon("reload", name)
            except Exception as e:  # keep going; report what didn't update
                failed.append(f"{name} ({e})")
        self.refresh()
        self._refresh_update_count()
        self.status((f"Updated {', '.join(done)}." if done else "") +
                    (f" Couldn't update: {'; '.join(failed)}" if failed else ""))

    def _update_selected(self) -> None:
        row = self.table.selected_row()
        if row and self.updates.get(row["name"], {}).get("status") == "update_available" \
                and self._confirm_update([row["name"]]):
            self._run_updates([row["name"]])

    def _update_all(self) -> None:
        names = [n for n, r in self.updates.items() if r["status"] == "update_available"]
        if names and self._confirm_update(names):
            self._run_updates(names)

    def _set_source(self, row: dict, clear: bool = False) -> None:
        sources = self._sources()
        key = row["name"].lower()
        if clear:
            sources.pop(key, None)
        else:
            text, ok = QInputDialog.getText(
                self, "Update source", f"GitHub page for {row['name']} "
                                       "(e.g. https://github.com/owner/repo or owner/repo/folder):",
                text=sources.get(key, ""))
            if not ok:
                return
            if text.strip() and not addon_updates.parse_source(text):
                self.info("Couldn't read that", "Use a GitHub link like https://github.com/owner/repo, "
                                                "or owner/repo/folder.")
                return
            if text.strip():
                sources[key] = text.strip()
            else:
                sources.pop(key, None)
        self.ctx.settings.set("addon_sources", sources)
        self.updates.pop(row["name"], None)
        self._refresh_update_count()
        self.status(f"Update source for {row['name']} saved. Click Scan for updates to check it.")

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
            action = menu.addAction(self.autoload_btn.text(), self._toggle_autoload)
            action.setEnabled(self.autoload_btn.isEnabled())
            action.setToolTip(self.autoload_btn.toolTip())
        if row["settings_file"]:
            menu.addAction("Edit settings", self._open_settings)
            menu.addAction("Open settings file", lambda: self.ctx.open_path(row["settings_file"]))
        menu.addAction("Open folder", lambda: self.ctx.open_path(row["folder"]))
        if row["kind"] == "addons":
            menu.addSeparator()
            menu.addAction("Set update source…", lambda: self._set_source(row))
            if self._sources().get(row["name"].lower()):
                menu.addAction("Use the official Windower source", lambda: self._set_source(row, clear=True))
        menu.exec(self.table.viewport().mapToGlobal(pos))
