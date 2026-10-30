"""Settings: Windower folder, text size, where your data lives, version and updates."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QSlider, QVBoxLayout

from ...core import paths
from .. import widgets
from .base import Page


def _section(title: str) -> tuple:
    frame = QFrame()
    frame.setObjectName("Panel")
    outer = QVBoxLayout(frame)
    outer.setContentsMargins(18, 14, 18, 16)
    outer.setSpacing(10)
    outer.addWidget(widgets.label(title, "SectionTitle"))
    grid = QGridLayout()
    grid.setHorizontalSpacing(16)
    grid.setVerticalSpacing(10)
    grid.setColumnStretch(1, 1)
    outer.addLayout(grid)
    return frame, grid


class SettingsPage(Page):
    title = "Settings"
    key = "settings"

    def __init__(self, ctx):
        super().__init__(ctx)
        win_frame, g = _section("Game")
        self.windower_label = widgets.label("", wrap=True)
        g.addWidget(widgets.label("Windower folder", "Caption"), 0, 0)
        g.addWidget(self.windower_label, 0, 1)
        g.addWidget(widgets.button("Change…", on_click=self._choose_windower), 0, 2)
        g.addWidget(widgets.label("Setup", "Caption"), 1, 0)
        self.setup_label = widgets.label("")
        g.addWidget(self.setup_label, 1, 1)
        g.addWidget(widgets.button("Open checklist", on_click=self._open_setup), 1, 2)

        look_frame, g = _section("Appearance")
        self.scale = QSlider(Qt.Horizontal)
        self.scale.setRange(90, 130)
        self.scale.setSingleStep(5)
        self.scale.setPageStep(10)
        self.scale.setValue(round(float(ctx.settings.get("text_scale") or 1.0) * 100))
        self.scale_label = widgets.label(f"{self.scale.value()}%")
        self.scale.sliderReleased.connect(self._apply_scale)
        self.scale.valueChanged.connect(lambda v: self.scale_label.setText(f"{v}%"))
        g.addWidget(widgets.label("Text size", "Caption"), 0, 0)
        g.addWidget(self.scale, 0, 1)
        g.addWidget(self.scale_label, 0, 2)

        data_frame, g = _section("Your data")
        g.addWidget(widgets.label("Data folder", "Caption"), 0, 0)
        g.addWidget(widgets.label(ctx.data_dir, wrap=True), 0, 1)
        g.addWidget(widgets.button("Open", on_click=lambda: ctx.open_path(ctx.data_dir)), 0, 2)
        note = widgets.label("Your tracker, wishlist and inventory live here. Updates never change this folder; "
                             "every save keeps the previous copy as a .bak file.", "Caption", wrap=True)
        g.addWidget(note, 1, 0, 1, 3)
        if ctx.db.recovered_from_backup:
            warn = widgets.label("Your database couldn't be read at startup, so the last good copy was loaded. "
                                 "The unreadable file was kept next to it.", wrap=True)
            warn.setStyleSheet("color: #F59E0B;")
            g.addWidget(warn, 2, 0, 1, 3)

        about_frame, g = _section("About")
        g.addWidget(widgets.label("Version", "Caption"), 0, 0)
        g.addWidget(widgets.label(f"v{ctx.version}" + ("" if paths.IS_FROZEN else " (running from source)")), 0, 1)
        self.update_btn = widgets.button("Check for updates", on_click=self._check_updates)
        self.update_btn.setEnabled(paths.IS_FROZEN)
        g.addWidget(self.update_btn, 0, 2)
        g.addWidget(widgets.label("Project", "Caption"), 1, 0)
        g.addWidget(widgets.button("github.com/Grimdarts/VanadielNexus ↗", "ghost",
                                   lambda: ctx.open_url("https://github.com/Grimdarts/VanadielNexus")), 1, 1,
                    Qt.AlignLeft)

        for f in (win_frame, look_frame, data_frame, about_frame):
            self.layout_.addWidget(f)
        self.layout_.addStretch(1)
        ctx.windower_changed.connect(lambda _p: self.on_shown())
        self.on_shown()

    def on_shown(self) -> None:
        self.windower_label.setText(self.ctx.windower_dir or "Not found")
        win = self.window()
        if hasattr(win, "setup_summary"):
            done, total = win.setup_summary()
            self.setup_label.setText("Complete" if done == total else f"{done} of {total} steps done")

    def _choose_windower(self) -> None:
        win = self.window()
        if hasattr(win, "choose_windower"):
            win.choose_windower()

    def _open_setup(self) -> None:
        win = self.window()
        if hasattr(win, "open_setup"):
            win.open_setup()

    def _apply_scale(self) -> None:
        win = self.window()
        if hasattr(win, "apply_text_scale"):
            win.apply_text_scale(self.scale.value() / 100)

    def _check_updates(self) -> None:
        win = self.window()
        if hasattr(win, "check_for_updates"):
            win.check_for_updates(manual=True)
