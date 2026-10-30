"""Common page frame: optional sub-tabs, toolbar, content and a status line."""
from PySide6.QtWidgets import QMessageBox, QVBoxLayout, QWidget

from .. import theme, widgets


class Page(QWidget):
    title = ""
    key = ""

    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(24, 18, 24, 16)
        self.layout_.setSpacing(14)

    def on_shown(self) -> None:
        """Called each time the page is opened from the sidebar."""

    def confirm(self, title: str, text: str, action: str = "Remove") -> bool:
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(text)
        box.setIcon(QMessageBox.NoIcon)
        ok = box.addButton(action, QMessageBox.AcceptRole)
        ok.setProperty("kind", "danger-fill")
        box.addButton("Cancel", QMessageBox.RejectRole)
        box.show()
        theme.dark_title_bar(box)
        box.exec()
        return box.clickedButton() is ok

    def info(self, title: str, text: str) -> None:
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(text)
        box.setIcon(QMessageBox.NoIcon)
        box.show()
        theme.dark_title_bar(box)
        box.exec()

    def status(self, text: str) -> None:
        win = self.window()
        if hasattr(win, "show_status"):
            win.show_status(text)


def count_label() -> "widgets.QLabel":
    return widgets.label("", "Caption")
