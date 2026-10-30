"""The Setup checklist: one row per step, each with a single Fix button."""
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QVBoxLayout

from ..core import setup_check, windower
from . import theme, widgets

FIX_LABELS = {"choose_windower": "Choose folder…", "install_addon": "Install", "enable_autoload": "Turn on"}


class SetupDialog(QDialog):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main = main_window
        self.ctx = main_window.ctx
        self.setWindowTitle("Setup")
        self.setMinimumWidth(560)
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(22, 18, 22, 18)
        self.lay.setSpacing(12)
        self.lay.addWidget(widgets.label("Get Vana'diel Nexus talking to the game", "SectionTitle"))
        self.lay.addWidget(widgets.label("Each step can be fixed with one click. Changes to Windower files always "
                                         "keep a backup.", "Caption", wrap=True))
        self.rows = QVBoxLayout()
        self.rows.setSpacing(8)
        self.lay.addLayout(self.rows)
        self.footer = widgets.label("", "Caption", wrap=True)
        self.lay.addWidget(self.footer)
        self.lay.addLayout(widgets.hbox(None, widgets.button("Done", "primary", self.accept)))
        self.rebuild()

    def showEvent(self, event):
        theme.dark_title_bar(self)
        super().showEvent(event)

    def rebuild(self) -> None:
        while self.rows.count():
            item = self.rows.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        steps = setup_check.run_checks(self.ctx.windower_dir)
        blocked = False
        for step in steps:
            card = QFrame()
            card.setObjectName("Card")
            row = QHBoxLayout(card)
            row.setContentsMargins(14, 10, 14, 10)
            mark = widgets.pill("Done" if step["ok"] else "To do", "success" if step["ok"] else "warning")
            text = QVBoxLayout()
            text.setSpacing(2)
            text.addWidget(widgets.label(step["label"]))
            text.addWidget(widgets.label(step["detail"], "Caption", wrap=True))
            row.addWidget(mark)
            row.addLayout(text, 1)
            if not step["ok"]:
                fix = widgets.button(FIX_LABELS[step["fix"]], on_click=lambda _c=False, s=step: self._fix(s["fix"]))
                fix.setEnabled(not blocked)
                row.addWidget(fix)
                blocked = blocked or step["id"] == "windower"
            self.rows.addWidget(card)
        done, total = setup_check.summary(steps)
        self.footer.setText("All set. Log in to FFXI and the app fills in your character and inventory."
                            if done == total else "After installing, type //lua r vanadielnexus in game "
                                                  "(or restart the game) to load the addon.")
        self.main.refresh_setup_pill()

    def _fix(self, fix: str) -> None:
        if fix == "choose_windower":
            self.main.choose_windower()
        elif fix == "install_addon":
            setup_check.install_addon(self.ctx.windower_dir)
        elif fix == "enable_autoload":
            windower.set_autoload(self.ctx.windower_dir, windower.ADDON_NAME, "addons", True)
        self.rebuild()
