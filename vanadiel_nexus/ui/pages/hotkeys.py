"""Hotkeys: every key bind across the game, Windower, GearSwap and addons, with real conflicts first."""
from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtWidgets import QCheckBox, QComboBox, QFrame, QInputDialog, QMenu, QVBoxLayout

from ...core import hotkeys
from .. import theme, widgets
from ..widgets import Column, DataTable
from .base import Page

SYSTEMS = ["All sources", "FFXI Base Game", "Windower init.txt", "GearSwap", "Windower Core"]


class _ScanSignals(QObject):
    done = Signal(list)


class _Scan(QRunnable):
    """Scanning hundreds of GearSwap files takes a moment: keep the window responsive."""

    def __init__(self, windower_dir):
        super().__init__()
        self.windower_dir = windower_dir
        self.signals = _ScanSignals()

    def run(self):
        self.signals.done.emit(hotkeys.scan_all_hotkeys_and_conflicts(self.windower_dir))


def _status(e) -> str:
    if e.get("conflict"):
        return f"Conflict ({e.get('conflict_count', 2)})"
    return "Not loaded" if e.get("inactive") else "OK"


def _tone(e):
    if e.get("conflict"):
        return theme.WARNING
    return theme.FAINT if e.get("inactive") else theme.SUCCESS


class HotkeysPage(Page):
    title = "Hotkeys"
    key = "hotkeys"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.entries = []
        self.system = QComboBox()
        self.system.addItems(SYSTEMS)
        self.conflicts_only = QCheckBox("Conflicts only")
        self.hide_inactive = QCheckBox("Hide unloaded files")
        self.hide_inactive.setChecked(True)
        self.toolbar = widgets.SearchToolbar("Search keys, commands or files…")
        self.toolbar.add(self.system, self.conflicts_only, self.hide_inactive,
                         widgets.button("Rescan", "primary", self.rescan))

        self.table = DataTable([
            Column("Key", "norm_key", 160),
            Column("Status", _status, 120, tone=_tone),
            Column("Source", "system", 260),
            Column("Does", "action", stretch=True),
            Column("Line", lambda e: e.get("line_num") or "", 60, Qt.AlignRight),
        ])
        self.toolbar.text_changed.connect(self.table.proxy.set_needle)
        for w in (self.system, self.conflicts_only, self.hide_inactive):
            (w.currentTextChanged if isinstance(w, QComboBox) else w.toggled).connect(self._apply_filters)
        self.table.selectionModel().selectionChanged.connect(self._show_detail)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)

        panel = QFrame()
        panel.setObjectName("Panel")
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(16, 12, 16, 12)
        self.detail_title = widgets.label("Select a bind to see where it comes from and how to change it.",
                                          "SectionTitle")
        self.detail_body = widgets.label("", "Caption", wrap=True)
        self.detail_body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        pl.addWidget(self.detail_title)
        pl.addWidget(self.detail_body)

        self.open_btn = widgets.button("Open file", on_click=self._open_file)
        self.rebind_btn = widgets.button("Change key…", on_click=self._rebind)
        self.disable_btn = widgets.button("Turn off bind", "danger", self._disable)
        self.count = widgets.label("", "Caption")

        self.layout_.addWidget(self.toolbar)
        self.layout_.addWidget(self.table, 1)
        self.layout_.addWidget(panel)
        self.layout_.addLayout(widgets.hbox(self.count, None, self.open_btn, self.rebind_btn, self.disable_btn))
        ctx.windower_changed.connect(lambda _p: self.rescan())
        self._scanned = False
        self._show_detail()

    def on_shown(self) -> None:
        if not self._scanned:
            self.rescan()

    def rescan(self) -> None:
        self._scanned = True
        self.count.setText("Scanning…")
        job = _Scan(self.ctx.windower_dir)
        job.signals.done.connect(self._scan_done)
        self._job = job  # keep the signals object alive until it fires
        QThreadPool.globalInstance().start(job)

    def _scan_done(self, entries) -> None:
        self.entries = entries
        self.table.set_rows(entries)
        self._apply_filters()

    def _apply_filters(self, *_args) -> None:
        system = self.system.currentText()
        only_conf, hide_inactive = self.conflicts_only.isChecked(), self.hide_inactive.isChecked()
        self.table.proxy.set_predicate(lambda e: (system == "All sources" or system.lower() in e["system"].lower())
                                       and (not only_conf or e.get("conflict"))
                                       and (not hide_inactive or not e.get("inactive")))
        conflicts = sum(1 for e in self.entries if e.get("conflict"))
        keys = len({e["norm_key"] for e in self.entries if e.get("conflict")})
        self.count.setText(f"{self.table.visible_count()} binds shown · {conflicts} conflicting binds on {keys} keys")

    def _show_detail(self, *_args) -> None:
        e = self.table.selected_row()
        for b in (self.open_btn, self.rebind_btn, self.disable_btn):
            b.setEnabled(bool(e) and bool(e.get("editable_file")))
        if not e:
            return
        self.detail_title.setText(f"{e['norm_key']}  ·  {e['system']}")
        lines = [f"Does: {e['action']}"]
        if e.get("conflict"):
            lines.append(f"Clashes with: {e.get('conflict_summary')}")
        if e.get("inactive"):
            lines.append("This file is in a folder GearSwap never loads, so it can't clash with anything.")
        lines.append(e.get("how_to_fix", ""))
        self.detail_body.setText("\n".join(lines))

    def _open_file(self) -> None:
        e = self.table.selected_row()
        if e:
            self.ctx.open_path(e.get("source_file", ""))

    def _rebind(self) -> None:
        e = self.table.selected_row()
        if not e:
            return
        new_key, ok = QInputDialog.getText(self, "Change key", f"New key for '{e['action']}' (e.g. Ctrl+F7, Alt+7):")
        if ok and new_key.strip():
            if hotkeys.rebind(e, new_key.strip()):
                self.ctx.bridge.send(f"CMD|unbind {hotkeys.to_windower_bind_key(e['norm_key'])}")
                self.status(f"Moved to {new_key.strip()}. Reload the file in game (//gs r or restart) to apply.")
                self.rescan()
            else:
                self.info("Couldn't change that bind", "The bind wasn't found on that line. Try Open file.")

    def _disable(self) -> None:
        e = self.table.selected_row()
        if not e or not self.confirm("Turn off bind", f"Comment out {e['norm_key']} ({e['action']}) in "
                                                       f"{e['source_file']}?\nA backup copy is kept.", "Turn off"):
            return
        if hotkeys.disable_bind(e):
            self.ctx.bridge.send(f"CMD|unbind {hotkeys.to_windower_bind_key(e['norm_key'])}")
            self.status(f"Turned off {e['norm_key']}.")
            self.rescan()

    def _context_menu(self, pos) -> None:
        e = self.table.selected_row()
        if not e or not e.get("editable_file"):
            return
        menu = QMenu(self)
        menu.addAction("Open file", self._open_file)
        menu.addAction("Change key…", self._rebind)
        menu.addSeparator()
        menu.addAction("Turn off bind", self._disable)
        menu.exec(self.table.viewport().mapToGlobal(pos))
