"""Small building blocks shared by every page: buttons, pills, cards, toolbars and the dict-backed table."""
from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt, QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QProgressBar, QPushButton,
    QTableView, QVBoxLayout, QWidget,
)

from . import theme


def button(text: str, kind: str = "", on_click=None, tooltip: str = "") -> QPushButton:
    """kind: '' (secondary), 'primary', 'ghost', 'danger'. DESIGN.md: one primary per screen."""
    b = QPushButton(text)
    if kind:
        b.setProperty("kind", kind)
    if tooltip:
        b.setToolTip(tooltip)
    if on_click:
        b.clicked.connect(on_click)
    b.setCursor(Qt.PointingHandCursor)
    return b


def pill(text: str, tone: str = "", clickable: bool = False):
    w = QPushButton(text) if clickable else QLabel(text)
    w.setProperty("pill", "true")
    set_tone(w, tone)
    if clickable:
        w.setCursor(Qt.PointingHandCursor)
    w.setFixedHeight(26)
    return w


def set_tone(widget, tone: str) -> None:
    widget.setProperty("tone", tone)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def label(text: str = "", role: str = "", wrap: bool = False) -> QLabel:
    lab = QLabel(text)
    if role:
        lab.setObjectName(role)  # PageTitle, SectionTitle, Caption
    lab.setWordWrap(wrap)
    return lab


def hbox(*widgets, spacing: int = 8, margins=(0, 0, 0, 0), stretch_at=None) -> QHBoxLayout:
    lay = QHBoxLayout()
    lay.setSpacing(spacing)
    lay.setContentsMargins(*margins)
    for i, w in enumerate(widgets):
        if i == stretch_at:
            lay.addStretch(1)
        if w is None:
            lay.addStretch(1)
        elif isinstance(w, QWidget):
            lay.addWidget(w)
        else:
            lay.addLayout(w)
    return lay


class ProgressCard(QFrame):
    """A gold progress bar with a label, a big value and a caption (REMA stage, JSE set, goals)."""

    def __init__(self, title: str, value: str, pct: float, caption: str = ""):
        super().__init__()
        self.setObjectName("Card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(6)
        lay.addWidget(label(title, "Caption"))
        big = label(value, "CardValue")
        if pct >= 100:
            big.setStyleSheet(f"color: {theme.GOLD};")
        lay.addWidget(big)
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(int(max(0, min(100, pct))))
        bar.setTextVisible(False)
        lay.addWidget(bar)
        if caption:
            cap = label(caption, "Caption", wrap=True)
            lay.addWidget(cap)


class SearchToolbar(QWidget):
    """Search box with filters and actions beside it; in a narrow window the controls drop to a second line."""

    text_changed = Signal(str)

    def __init__(self, placeholder: str = "Search…"):
        super().__init__()
        self.search = QLineEdit()
        self.search.setPlaceholderText(placeholder)
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumWidth(200)
        self.search.textChanged.connect(self.text_changed)
        self.controls = QWidget()
        self.row = QHBoxLayout(self.controls)
        self.row.setContentsMargins(0, 0, 0, 0)
        self.row.setSpacing(8)
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(8)
        self.grid.setVerticalSpacing(8)
        self.grid.addWidget(self.search, 0, 0)
        self.grid.addWidget(self.controls, 0, 1)
        self.grid.setColumnStretch(0, 1)
        self._wrapped = False

    def add(self, *widgets) -> None:
        for w in widgets:
            self.row.addWidget(w)

    def resizeEvent(self, event):
        wrap = self.width() < self.search.minimumWidth() + self.controls.sizeHint().width() + 8
        if wrap != self._wrapped:
            self._wrapped = wrap
            self.grid.removeWidget(self.controls)
            if wrap:
                self.grid.addWidget(self.controls, 1, 0, 1, 2, Qt.AlignRight)
            else:
                self.grid.addWidget(self.controls, 0, 1)
        super().resizeEvent(event)


class EmptyState(QWidget):
    def __init__(self, title: str, detail: str = "", action: QPushButton = None):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.addStretch(1)
        t = label(title, "SectionTitle")
        t.setAlignment(Qt.AlignCenter)
        lay.addWidget(t)
        if detail:
            d = label(detail, "Caption", wrap=True)
            d.setAlignment(Qt.AlignCenter)
            lay.addWidget(d)
        if action:
            lay.addLayout(hbox(None, action, None))
        lay.addStretch(2)


# --- Tables -------------------------------------------------------------------
class Column:
    """key: dict key or callable(row) -> value. tone: callable(row) -> color hex for the text."""

    def __init__(self, title, key, width=None, align=Qt.AlignLeft, tone=None, stretch=False, tooltip=None):
        self.title, self.key, self.width, self.align = title, key, width, align
        self.tone, self.stretch, self.tooltip = tone, stretch, tooltip

    def value(self, row):
        v = self.key(row) if callable(self.key) else row.get(self.key, "")
        return "" if v is None else v


class DictTableModel(QAbstractTableModel):
    def __init__(self, columns):
        super().__init__()
        self.columns = columns
        self.rows = []

    def set_rows(self, rows) -> None:
        self.beginResetModel()
        self.rows = list(rows)
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.columns)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row, col = self.rows[index.row()], self.columns[index.column()]
        if role == Qt.DisplayRole:
            v = col.value(row)
            return f"{v:,}" if isinstance(v, int) and not isinstance(v, bool) else str(v)
        if role == Qt.UserRole:  # raw value for sorting
            return col.value(row)
        if role == Qt.TextAlignmentRole:
            return int(col.align | Qt.AlignVCenter)
        if role == Qt.ForegroundRole and col.tone:
            color = col.tone(row)
            return QColor(color) if color else None
        if role == Qt.ToolTipRole:
            return col.tooltip(row) if col.tooltip else str(col.value(row)) or None
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.columns[section].title
        if orientation == Qt.Horizontal and role == Qt.TextAlignmentRole:
            return int(self.columns[section].align | Qt.AlignVCenter)
        return None


class RowFilter(QSortFilterProxyModel):
    """Case-insensitive search across every column, plus an optional extra predicate."""

    def __init__(self):
        super().__init__()
        self.needle = ""
        self.predicate = None
        self.setSortRole(Qt.UserRole)

    def set_needle(self, text: str) -> None:
        self.needle = text.lower().strip()
        self.invalidate()

    def set_predicate(self, fn) -> None:
        self.predicate = fn
        self.invalidate()

    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()
        row = model.rows[source_row]
        if self.predicate and not self.predicate(row):
            return False
        if not self.needle:
            return True
        return any(self.needle in str(c.value(row)).lower() for c in model.columns)

    def lessThan(self, left, right):
        a, b = left.data(Qt.UserRole), right.data(Qt.UserRole)
        try:
            return a < b
        except TypeError:
            return str(a).lower() < str(b).lower()


class DataTable(QTableView):
    """A themed, sortable, searchable table of dicts. selected_row() returns the dict (or None).

    Every column divider can be dragged; the last column fills the rest of the window. When the table
    has a name and DataTable.store is set (the app's Settings), column widths are remembered.
    """

    row_activated = Signal(dict)
    store = None  # object with get(key) / set(key, value); set by the app at startup

    def __init__(self, columns, sort_column=None, name: str = ""):
        """sort_column: index to sort ascending by default; None keeps the order rows are given in."""
        super().__init__()
        self.name = name
        self.model_ = DictTableModel(columns)
        self.proxy = RowFilter()
        self.proxy.setSourceModel(self.model_)
        self.setModel(self.proxy)
        self.setSortingEnabled(True)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setShowGrid(False)
        self.setWordWrap(False)
        self.verticalHeader().hide()
        self.verticalHeader().setDefaultSectionSize(36)
        hdr = self.horizontalHeader()
        hdr.setHighlightSections(False)
        hdr.setSectionResizeMode(QHeaderView.Interactive)
        hdr.setStretchLastSection(True)
        hdr.setMinimumSectionSize(48)
        for i, c in enumerate(columns):
            self.setColumnWidth(i, c.width or (320 if c.stretch else 140))
        if sort_column is None:
            hdr.setSortIndicator(-1, Qt.AscendingOrder)
        else:
            self.sortByColumn(sort_column, Qt.AscendingOrder)
        self.doubleClicked.connect(lambda idx: self.row_activated.emit(self._row_at(idx)))
        self._restore_widths()
        self._save_timer = QTimer(self, singleShot=True, interval=600)
        self._save_timer.timeout.connect(self._save_widths)
        hdr.sectionResized.connect(lambda *_a: self._save_timer.start())

    def _key(self) -> str:
        return f"columns:{self.name}"

    def _restore_widths(self) -> None:
        if not (self.name and DataTable.store):
            return
        widths = DataTable.store.get(self._key())
        if isinstance(widths, list) and len(widths) == self.model_.columnCount():
            for i, w in enumerate(widths[:-1]):  # the last column always fills the remaining space
                self.setColumnWidth(i, int(w))

    def _save_widths(self) -> None:
        if self.name and DataTable.store:
            DataTable.store.set(self._key(), [self.columnWidth(i) for i in range(self.model_.columnCount())])

    def set_rows(self, rows) -> None:
        keep = self.selected_row()
        self.model_.set_rows(rows)
        if keep is not None:
            self.select_row(keep)

    def _row_at(self, proxy_index):
        return self.model_.rows[self.proxy.mapToSource(proxy_index).row()]

    def selected_row(self):
        idx = self.selectionModel().selectedRows()
        return self._row_at(idx[0]) if idx else None

    def select_row(self, row) -> None:
        for i, r in enumerate(self.model_.rows):
            if r is row or (row.get("id") and r.get("id") == row.get("id")):
                proxy_idx = self.proxy.mapFromSource(self.model_.index(i, 0))
                if proxy_idx.isValid():
                    self.selectRow(proxy_idx.row())
                return

    def visible_count(self) -> int:
        return self.proxy.rowCount()
