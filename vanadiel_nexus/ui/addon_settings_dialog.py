"""Edit a Windower addon's settings file in place: a tree of its settings with the right control for each
value (switch, number, text, color), then save (with a backup) and optionally reload it in game."""
import os

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QColorDialog, QComboBox, QDialog, QDoubleSpinBox, QLineEdit, QPushButton, QSpinBox, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout,
)

from ..core import addon_settings as xs
from . import theme, widgets


def pretty(tag: str) -> str:
    t = xs.display_tag(tag)
    return t.replace("_", " ").strip().capitalize() if not t.isdigit() else f"#{t}"


class AddonSettingsDialog(QDialog):
    def __init__(self, parent, ctx, addon: dict):
        super().__init__(parent)
        self.ctx = ctx
        self.addon = addon
        self.file = None
        self.editors = []  # (element, read_fn)
        self.setWindowTitle(f"{addon['name']} settings")
        self.resize(760, 640)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(10)
        lay.addWidget(widgets.label(f"{addon['name']} settings", "SectionTitle"))
        self.note = widgets.label("", "Caption", wrap=True)
        lay.addWidget(self.note)

        self.file_combo = QComboBox()
        self.files = xs.settings_files(addon["folder"])
        self.file_combo.addItems([os.path.basename(p) for p in self.files])
        self.file_combo.currentIndexChanged.connect(self._load)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Find a setting…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._filter)
        lay.addLayout(widgets.hbox(self.search, self.file_combo))
        self.file_combo.setVisible(len(self.files) > 1)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["Setting", "Value"])
        self.tree.setColumnWidth(0, 340)
        self.tree.setAlternatingRowColors(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setStyleSheet("QTreeView::item { height: 34px; }")
        lay.addWidget(self.tree, 1)

        live = ctx.bridge.connected
        self.save_btn = widgets.button("Save and reload in game" if live else "Save", "primary", self._save)
        lay.addLayout(widgets.hbox(
            widgets.button("Open file", "ghost", lambda: self.file and ctx.open_path(self.file.path)),
            None, widgets.button("Cancel", on_click=self.reject), self.save_btn))
        if self.files:
            start = self._preferred_index()
            self.file_combo.setCurrentIndex(start)
            if start == 0:
                self._load(0)
        else:
            self.note.setText("This addon has no settings file yet. Most addons create one the first time they run.")
            self.save_btn.setEnabled(False)

    def _preferred_index(self) -> int:
        """Addons like GearInfo keep one file per character: open the one for the character you play."""
        names = [self.ctx.bridge.state.get("player_name", "")] + list(self.ctx.inventory_snapshot.keys())
        for name in (n.lower() for n in names if n):
            for i, path in enumerate(self.files):
                if os.path.basename(path).lower().startswith(name):
                    return i
        return 0

    def showEvent(self, event):
        theme.dark_title_bar(self)
        super().showEvent(event)

    # --- building the tree ------------------------------------------------
    def _load(self, index: int) -> None:
        self.tree.clear()
        self.editors = []
        try:
            self.file = xs.SettingsFile(self.files[index])
        except Exception as e:  # a file we can't parse must never be overwritten
            self.file = None
            self.note.setText(f"Couldn't read {os.path.basename(self.files[index])}: {e}. Use Open file instead.")
            self.save_btn.setEnabled(False)
            return
        self.save_btn.setEnabled(True)
        self.note.setText("'Global' applies to every character; a character's section overrides it. "
                          "A backup is saved before every change.")
        for section in self.file.sections():
            el = self.file.root.find(section)
            item = QTreeWidgetItem([pretty(section) if section.lower() == "global" else section, ""])
            item.setFirstColumnSpanned(True)
            font = item.font(0)
            font.setBold(True)
            item.setFont(0, font)
            self.tree.addTopLevelItem(item)
            self._add_children(item, el)
            item.setExpanded(section.lower() == "global")

    def _add_children(self, parent_item, el) -> None:
        for child in el:
            if not isinstance(child.tag, str):
                continue
            item = QTreeWidgetItem([pretty(child.tag), ""])
            item.setToolTip(0, xs.display_tag(child.tag))
            parent_item.addChild(item)
            if xs.is_color_group(child):
                self.tree.setItemWidget(item, 1, self._fit(self._color_button(child)))
            elif xs.is_leaf(child):
                self.tree.setItemWidget(item, 1, self._fit(self._editor_for(child)))
            else:
                self._add_children(item, child)

    @staticmethod
    def _fit(w):
        w.setFixedHeight(28)
        w.setMaximumWidth(320)
        return w

    def _editor_for(self, el):
        text = (el.text or "").strip()
        kind = xs.value_kind(text)
        if kind == "bool":
            w = QCheckBox()
            w.setChecked(text.lower() == "true")
            w.setText("On" if w.isChecked() else "Off")
            w.toggled.connect(lambda on, w=w: w.setText("On" if on else "Off"))
            self.editors.append((el, lambda w=w: "true" if w.isChecked() else "false"))
        elif kind == "int":
            w = QSpinBox()
            w.setRange(-1_000_000_000, 1_000_000_000)
            w.setValue(int(text))
            self.editors.append((el, lambda w=w: str(w.value())))
        elif kind == "float":
            w = QDoubleSpinBox()
            w.setRange(-1e9, 1e9)
            w.setDecimals(max(1, len(text.split(".")[1])))
            w.setValue(float(text))
            self.editors.append((el, lambda w=w: f"{w.value():.{w.decimals()}f}"))
        else:
            w = QLineEdit(el.text or "")
            self.editors.append((el, lambda w=w: w.text()))
        return w

    def _color_button(self, group):
        parts = {c.tag.lower(): c for c in group if isinstance(c.tag, str)}

        def current():
            return QColor(*(int((parts[k].text or "0").strip() or 0) for k in ("red", "green", "blue")),
                          int((parts["alpha"].text or "255").strip()) if "alpha" in parts else 255)

        btn = QPushButton()
        btn.setCursor(Qt.PointingHandCursor)

        def paint():
            c = current()
            swatch = QPixmap(16, 16)
            swatch.fill(QColor(c.red(), c.green(), c.blue()))
            btn.setIcon(QIcon(swatch))
            btn.setText(f"R {c.red()}  G {c.green()}  B {c.blue()}" + (f"  A {c.alpha()}" if "alpha" in parts else ""))
            btn.setStyleSheet("text-align: left; padding-left: 8px;")

        def pick():
            opts = QColorDialog.ShowAlphaChannel if "alpha" in parts else QColorDialog.ColorDialogOption(0)
            c = QColorDialog.getColor(current(), self, "Pick a color", opts)
            if c.isValid():
                for key, val in (("red", c.red()), ("green", c.green()), ("blue", c.blue()), ("alpha", c.alpha())):
                    if key in parts:
                        parts[key].text = str(val)
                paint()

        btn.clicked.connect(pick)
        paint()
        return btn

    def _filter(self, text: str) -> None:
        needle = text.lower().strip()

        def visit(item) -> bool:
            match = not needle or needle in item.text(0).lower() or needle in (item.toolTip(0) or "").lower()
            child_match = any([visit(item.child(i)) for i in range(item.childCount())])
            item.setHidden(not (match or child_match))
            if needle and child_match:
                item.setExpanded(True)
            return match or child_match

        for i in range(self.tree.topLevelItemCount()):
            visit(self.tree.topLevelItem(i))

    # --- saving -----------------------------------------------------------
    def _write(self) -> None:
        for el, read in self.editors:
            el.text = read()
        self.file.save()

    def _save(self) -> None:
        if not self.file:
            return
        name = self.addon["name"]
        if self.ctx.bridge.connected:
            # Unload first so the addon can't save its old values over ours, then load the new file
            self.ctx.bridge.addon("unload", name)
            self.save_btn.setEnabled(False)
            QTimer.singleShot(800, lambda: (self._write(), self.ctx.bridge.addon("load", name), self.accept()))
        else:
            self._write()
            self.accept()
