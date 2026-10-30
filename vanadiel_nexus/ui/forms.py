"""One reusable add/edit dialog driven by a field list, so every tracker table edits the same way."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QCompleter, QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QPlainTextEdit,
    QSpinBox, QVBoxLayout,
)

from ..core.materials import format_materials, parse_materials
from . import theme, widgets


class Field:
    """kind: 'text', 'long', 'int', 'bool', 'choice' (options), 'combo' (editable choice), 'materials'."""

    def __init__(self, key, label, kind="text", options=None, required=False, placeholder=""):
        self.key, self.label, self.kind = key, label, kind
        self.options, self.required, self.placeholder = options or [], required, placeholder


class FormDialog(QDialog):
    def __init__(self, parent, title: str, fields, values=None, completions=None, on_complete=None):
        """completions + on_complete: suggest names (e.g. from the catalog) and prefill other fields on pick."""
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(480)
        self.fields = fields
        self.inputs = {}
        values = values or {}

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 16)
        lay.setSpacing(14)
        lay.addWidget(widgets.label(title, "SectionTitle"))
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        for f in fields:
            w = self._make_input(f, values.get(f.key))
            self.inputs[f.key] = w
            form.addRow(f.label + (" *" if f.required else ""), w)
        lay.addLayout(form)

        if completions and "name" in self.inputs and isinstance(self.inputs["name"], QLineEdit):
            comp = QCompleter(sorted(completions))
            comp.setCaseSensitivity(Qt.CaseInsensitive)
            comp.setFilterMode(Qt.MatchContains)
            self.inputs["name"].setCompleter(comp)
            if on_complete:
                comp.activated.connect(lambda text: self.fill(on_complete(text)))

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setProperty("kind", "primary")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)
        self._save_button = buttons.button(QDialogButtonBox.Save)
        self._update_save_state()

    def showEvent(self, event):
        theme.dark_title_bar(self)
        super().showEvent(event)

    def _make_input(self, f: Field, value):
        if f.kind == "materials":
            w = QPlainTextEdit(format_materials(value) if isinstance(value, list) else str(value or ""))
            w.setPlaceholderText("One per line, e.g.\nPluton x1500\nVoidhead: BLU x3")
            w.setFixedHeight(110)
            w.setProperty("materials", True)
        elif f.kind == "long":
            w = QPlainTextEdit(str(value or ""))
            w.setFixedHeight(76)
            w.textChanged.connect(self._update_save_state)
        elif f.kind == "int":
            w = QSpinBox()
            w.setRange(0, 10_000_000)
            w.setGroupSeparatorShown(True)
            w.setValue(int(value or 0))
        elif f.kind == "bool":
            w = QCheckBox()
            w.setChecked(bool(value))
        elif f.kind in ("choice", "combo"):
            w = QComboBox()
            w.setEditable(f.kind == "combo")
            w.addItems(f.options)
            if value not in (None, ""):
                if w.findText(str(value)) < 0:
                    w.addItem(str(value))
                w.setCurrentText(str(value))
        else:
            w = QLineEdit(str(value or ""))
            w.setPlaceholderText(f.placeholder)
            w.textChanged.connect(self._update_save_state)
        return w

    def fill(self, values: dict) -> None:
        for key, val in (values or {}).items():
            w = self.inputs.get(key)
            if isinstance(w, QLineEdit) and not w.text():
                w.setText(str(val))
            elif isinstance(w, QPlainTextEdit) and not w.toPlainText():
                w.setPlainText(str(val))

    def _read(self, f: Field):
        w = self.inputs[f.key]
        if isinstance(w, QPlainTextEdit):
            if w.property("materials"):
                return parse_materials(w.toPlainText())
            return w.toPlainText().strip()
        if isinstance(w, QSpinBox):
            return w.value()
        if isinstance(w, QCheckBox):
            return w.isChecked()
        if isinstance(w, QComboBox):
            return w.currentText().strip()
        return w.text().strip()

    def _update_save_state(self) -> None:
        if hasattr(self, "_save_button"):
            ok = all(self._read(f) not in ("", None, []) for f in self.fields if f.required)
            self._save_button.setEnabled(ok)

    def _accept(self) -> None:
        self.result_values = {f.key: self._read(f) for f in self.fields}
        self.accept()

    @classmethod
    def ask(cls, parent, title, fields, values=None, **kw):
        dlg = cls(parent, title, fields, values, **kw)
        return dlg.result_values if dlg.exec() == QDialog.Accepted else None
