"""Main window: sidebar navigation, top bar (game, setup and update status) and the page stack.

    ┌──────────┬──────────────────────────────────────────────┐
    │ Sidebar  │ Top bar: title · game status · setup · update│
    │  Gear    ├──────────────────────────────────────────────┤
    │  ...     │ Page (stack)                                 │
    │ Settings │ status line                                  │
    └──────────┴──────────────────────────────────────────────┘
"""
import os

from PySide6.QtCore import QByteArray, QObject, QRunnable, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QFileDialog, QFrame, QHBoxLayout, QMainWindow, QMessageBox, QPushButton,
    QStackedWidget, QVBoxLayout, QWidget,
)

from ..core import paths, setup_check, updater, windower
from . import theme, widgets
from .pages.addons import AddonsPage
from .pages.gear import GearPage
from .pages.hotkeys import HotkeysPage
from .pages.inventory import InventoryPage
from .pages.settings import SettingsPage
from .pages.wishlist import WishlistPage
from .setup_dialog import SetupDialog

NAV = [("⚔", GearPage), ("✦", WishlistPage), ("☰", InventoryPage), ("⧉", AddonsPage), ("⌨", HotkeysPage)]
COLLAPSE_BELOW = 1100


class _UpdateSignals(QObject):
    found = Signal(object)
    failed = Signal(str)


class _UpdateCheck(QRunnable):
    def __init__(self, version):
        super().__init__()
        self.version = version
        self.signals = _UpdateSignals()

    def run(self):
        try:
            self.signals.found.emit(updater.check(self.version))
        except Exception as e:  # network errors are expected offline
            self.signals.failed.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.update_info = None
        self.setWindowTitle("Vana'diel Nexus")
        self.setWindowIcon(QIcon(paths.resource_path("VanadielNexus.ico")))
        self.setMinimumSize(900, 600)

        root = QWidget()
        h = QHBoxLayout(root)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        self.setCentralWidget(root)

        # Sidebar
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        sb = QVBoxLayout(self.sidebar)
        sb.setContentsMargins(10, 16, 10, 16)
        sb.setSpacing(2)
        self.brand = widgets.label("Vana'diel Nexus", "Brand")
        sb.addWidget(self.brand)
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_buttons = []
        self.pages = []
        self.stack = QStackedWidget()
        for entry in NAV + [None, ("⚙", SettingsPage)]:
            if entry is None:
                sep = QFrame()
                sep.setObjectName("NavSeparator")
                sep.setFixedHeight(1)
                sb.addWidget(sep)
                continue
            icon, cls = entry
            page = cls(ctx)
            self.pages.append(page)
            self.stack.addWidget(page)
            btn = QPushButton()
            btn.setObjectName("NavButton")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("icon_text", icon)
            btn.setProperty("full_text", f"{icon}   {page.title}")
            btn.setText(btn.property("full_text"))
            btn.setToolTip(page.title)
            btn.clicked.connect(lambda _c=False, p=page: self.show_page(p.key))
            self.nav_group.addButton(btn)
            self.nav_buttons.append(btn)
            sb.addWidget(btn)
        sb.addStretch(1)
        h.addWidget(self.sidebar)

        # Right side: top bar + page + status line
        right = QWidget()
        right.setObjectName("Content")
        v = QVBoxLayout(right)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        top = QFrame()
        top.setObjectName("TopBar")
        top.setFixedHeight(54)
        t = QHBoxLayout(top)
        t.setContentsMargins(24, 0, 20, 0)
        t.setSpacing(10)
        self.page_title = widgets.label("", "PageTitle")
        self.game_pill = widgets.pill("Game not connected")
        self.setup_pill = widgets.pill("", "warning", clickable=True)
        self.setup_pill.clicked.connect(self.open_setup)
        self.update_pill = widgets.pill("", "accent", clickable=True)
        self.update_pill.clicked.connect(lambda: self._offer_update(self.update_info))
        self.update_pill.hide()
        t.addWidget(self.page_title)
        t.addStretch(1)
        for w in (self.game_pill, self.setup_pill, self.update_pill):
            t.addWidget(w)
        v.addWidget(top)
        v.addWidget(self.stack, 1)
        self.status_line = widgets.label("", "Caption")
        self.status_line.setContentsMargins(24, 0, 24, 8)
        v.addWidget(self.status_line)
        self._status_timer = QTimer(self, singleShot=True, interval=7000)
        self._status_timer.timeout.connect(lambda: self.status_line.setText(""))
        h.addWidget(right, 1)

        ctx.bridge.state_received.connect(self._on_game_state)
        ctx.windower_changed.connect(lambda _p: self.refresh_setup_pill())
        if not ctx.bridge.listening:
            self.show_status("Another program is using port 5017, so the game connection is off.")

        geometry = ctx.settings.get("window_geometry")
        if geometry:
            self.restoreGeometry(QByteArray.fromHex(geometry.encode()))
        else:
            self.resize(1180, 760)
        self.show_page(ctx.settings.get("last_page") or "gear")
        self.refresh_setup_pill()
        QTimer.singleShot(300, ctx.bridge.request_scan)
        if paths.IS_FROZEN:
            QTimer.singleShot(3000, self.check_for_updates)
        done, total = self.setup_summary()
        if done < total and not ctx.settings.get("setup_dismissed"):
            QTimer.singleShot(400, self.open_setup)

    # --- window behaviour -------------------------------------------------
    def showEvent(self, event):
        theme.dark_title_bar(self)
        super().showEvent(event)

    def resizeEvent(self, event):
        compact = self.width() < COLLAPSE_BELOW
        self.brand.setVisible(not compact)
        self.sidebar.setFixedWidth(64 if compact else 220)
        for b in self.nav_buttons:
            b.setText(b.property("icon_text") if compact else b.property("full_text"))
        super().resizeEvent(event)

    def closeEvent(self, event):
        self.ctx.settings.set("window_geometry", bytes(self.saveGeometry().toHex()).decode())
        super().closeEvent(event)

    def show_page(self, key: str) -> None:
        for i, page in enumerate(self.pages):
            if page.key == key:
                self.stack.setCurrentWidget(page)
                self.nav_buttons[i].setChecked(True)
                self.page_title.setText(page.title)
                self.ctx.settings.set("last_page", key)
                page.on_shown()
                return
        self.show_page("gear")

    def show_status(self, text: str) -> None:
        self.status_line.setText(text)
        self._status_timer.start()

    def apply_text_scale(self, scale: float) -> None:
        self.ctx.settings.set("text_scale", scale)
        QApplication.instance().setStyleSheet(theme.stylesheet(scale))

    # --- game, setup and Windower folder ----------------------------------
    def _on_game_state(self, state: dict) -> None:
        name, job, sub = state.get("player_name", ""), state.get("main_job", ""), state.get("sub_job", "")
        self.game_pill.setText(f"{name} · {job}/{sub}" if name else "Game connected")
        widgets.set_tone(self.game_pill, "success")

    def setup_summary(self) -> tuple:
        return setup_check.summary(setup_check.run_checks(self.ctx.windower_dir))

    def refresh_setup_pill(self) -> None:
        done, total = self.setup_summary()
        self.setup_pill.setText(f"Setup {done} of {total}")
        self.setup_pill.setVisible(done < total)

    def open_setup(self) -> None:
        SetupDialog(self).exec()
        self.ctx.settings.set("setup_dismissed", True)
        self.refresh_setup_pill()

    def choose_windower(self) -> None:
        start = self.ctx.windower_dir or os.path.expanduser("~")
        path = QFileDialog.getExistingDirectory(self, "Choose your Windower4 folder", start)
        if not path:
            return
        if not windower.is_windower_dir(path):
            QMessageBox.warning(self, "Not a Windower folder",
                                "That folder doesn't contain windower.exe or an addons folder.")
            return
        self.ctx.set_windower_dir(os.path.normpath(path))
        self.show_status(f"Using Windower at {path}")

    # --- updates ----------------------------------------------------------
    def check_for_updates(self, manual: bool = False) -> None:
        job = _UpdateCheck(self.ctx.version)
        job.signals.found.connect(lambda info: self._update_result(info, manual))
        job.signals.failed.connect(lambda err: manual and QMessageBox.warning(
            self, "Update check failed", f"Couldn't reach GitHub:\n\n{err}"))
        self._update_job = job
        QThreadPool.globalInstance().start(job)

    def _update_result(self, info, manual: bool) -> None:
        self.update_info = info
        if info:
            self.update_pill.setText(f"v{info['version']} available")
            self.update_pill.show()
            if manual:
                self._offer_update(info)
        elif manual:
            QMessageBox.information(self, "Up to date", f"You're on the latest version (v{self.ctx.version}).")

    def _offer_update(self, info) -> None:
        if not info:
            return
        notes = info["notes"].strip()[:600]
        answer = QMessageBox.question(
            self, "Update available",
            f"Vana'diel Nexus v{info['version']} is available (you have v{self.ctx.version}).\n\n"
            f"{notes + chr(10) * 2 if notes else ''}Update now? The app restarts. Your data is not touched.")
        if answer != QMessageBox.Yes:
            return
        self.show_status(f"Downloading v{info['version']}…")
        QApplication.processEvents()
        try:
            script = updater.download_and_stage(info["url"], os.path.abspath(os.sys.executable))
        except Exception as e:
            QMessageBox.critical(self, "Update failed", str(e))
            return
        updater.launch_swap(script)
        self.close()
