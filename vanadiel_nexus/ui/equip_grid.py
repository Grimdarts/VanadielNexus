"""The in-game 4×4 equipment grid as a reusable widget. Knows nothing about GearSwap.

    ┌──────┐┌──────┐┌──────┐┌──────┐   Main  Sub   Range Ammo
    │ MAIN ││ SUB  ││RANGE ││ AMMO │   Head  Neck  Ear 1 Ear 2
    └──────┘└──────┘└──────┘└──────┘   Body  Hands Ring 1 Ring 2
    … 4 rows of 4 cells, 112×128 × text scale, gap 8      Back  Waist Legs  Feet

One Tab stop: arrow keys move the keyboard focus in that order, Enter or Space opens the slot (same as a
click). Focus (1 px dotted ring) and selection (2 px ring) never share a look. Every state reads in words;
colour only reinforces it (docs/SET-MANAGER-DESIGN-REVIEW.md section 4).
"""
from dataclasses import dataclass

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QGridLayout, QSizePolicy, QWidget

from . import theme

STATES = ('owned', 'unreachable', 'missing', 'other_character', 'unknown', 'no_snapshot', 'empty', 'not_set')
SLOT_LABELS = {'main': 'Main', 'sub': 'Sub', 'range': 'Range', 'ammo': 'Ammo', 'head': 'Head', 'neck': 'Neck',
               'ear1': 'Ear 1', 'ear2': 'Ear 2', 'body': 'Body', 'hands': 'Hands', 'ring1': 'Ring 1',
               'ring2': 'Ring 2', 'back': 'Back', 'waist': 'Waist', 'legs': 'Legs', 'feet': 'Feet'}
CELL_W, CELL_H, GAP = 112, 128, 8

# state -> (name colour, caption colour)
_COLOURS = {
    'owned': (theme.GOLD, theme.MUTED),
    'unreachable': (theme.TEXT, theme.WARNING),
    'missing': (theme.FAINT, theme.MUTED),
    'other_character': (theme.FAINT, theme.MUTED),
    'unknown': (theme.TEXT, theme.DANGER),
    'no_snapshot': (theme.FAINT, theme.MUTED),
    'empty': (theme.FAINT, theme.MUTED),
    'not_set': (theme.FAINT, theme.MUTED),
}


@dataclass
class CellData:
    slot: str
    name: str = ''
    state: str = 'not_set'         # exactly one of STATES
    caption: str = ''              # bag, "⚠ Mog Safe 1", "from SavageBlade"...
    tooltip: str = ''
    badge: str = ''                # '↑' when a tier upgrade exists
    icon: QPixmap | None = None    # slice 2; None draws the slot-label tile
    note: str = ''                 # requirements the app can't check: amber dot on the tile
    changed: bool = False          # differs from the previous read: 1 px accent outline for one cycle
    accessible_name: str = ''


def describe(cell: CellData) -> str:
    """'Head: Hashishin Kavuk +2, owned, Wardrobe 3, upgrade available'."""
    label = SLOT_LABELS.get(cell.slot, cell.slot)
    if cell.state == 'not_set':
        return f'{label}: not specified'
    if cell.state == 'empty':
        return f'{label}: unequip'
    parts = [f'{label}: {cell.name}', cell.state.replace('_', ' ')]
    if cell.caption:
        parts.append(cell.caption.lstrip('⚠✕ '))
    if cell.badge:
        parts.append('upgrade available')
    if cell.note:
        parts.append('requirements unverified')
    return ', '.join(parts)


def elide_two_lines(text: str, metrics: QFontMetrics, width: int) -> list[str]:
    """Wrap at spaces into at most two lines; elide the second in the middle so a "+3" suffix stays."""
    if metrics.horizontalAdvance(text) <= width:
        return [text]
    words = text.split(' ')
    first = words[0]
    i = 1
    while i < len(words) and metrics.horizontalAdvance(first + ' ' + words[i]) <= width:
        first += ' ' + words[i]
        i += 1
    if metrics.horizontalAdvance(first) > width:  # one long first word
        first = metrics.elidedText(first, Qt.ElideRight, width)
    rest = ' '.join(words[i:])
    if not rest:
        return [first]
    return [first, metrics.elidedText(rest, Qt.ElideMiddle, width)]


class Cell(QWidget):
    clicked = Signal(str)

    def __init__(self, slot: str, scale: float = 1.0):
        super().__init__()
        self.slot = slot
        self.data = CellData(slot)
        self.selected = False
        self.focused = False
        self.dimmed = False
        self.scale = scale
        self.setFocusPolicy(Qt.NoFocus)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.set_data(CellData(slot))

    def sizeHint(self):
        return QSize(round(CELL_W * self.scale), round(CELL_H * self.scale))

    def set_scale(self, scale: float) -> None:
        self.scale = scale
        self.setFixedSize(self.sizeHint())
        self.update()

    def set_data(self, data: CellData) -> None:
        self.data = data
        self.setToolTip(data.tooltip or data.name)
        self.setAccessibleName(data.accessible_name or describe(data))
        self.setFixedSize(self.sizeHint())
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.slot)
        super().mousePressEvent(event)

    def _font(self, px: float, weight=QFont.Normal, italic=False) -> QFont:
        font = QFont(theme.UI_FONT)
        font.setPixelSize(max(1, round(px * self.scale)))
        font.setWeight(weight)
        font.setItalic(italic)
        return font

    def paintEvent(self, _event):
        s = self.scale
        data = self.data
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        ring = 3 * s
        frame = QRectF(self.rect()).adjusted(ring, ring, -ring, -ring)
        radius = 10 * s

        # Frame: the slot cell is the only framed element (design D14).
        border = QColor(theme.WARNING if data.state == 'unreachable' else theme.BORDER)
        pen = QPen(border, 1)
        if data.state == 'not_set':
            pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        painter.setBrush(QColor(theme.SURFACE))
        painter.drawRoundedRect(frame.adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)
        if self.selected:
            painter.setPen(QPen(QColor(theme.ACCENT), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), radius + ring - 1, radius + ring - 1)
        elif data.changed:
            painter.setPen(QPen(QColor(theme.ACCENT), 1))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5), radius + ring - 1, radius + ring - 1)
        if self.focused:
            focus_pen = QPen(QColor(theme.ACCENT), 1, Qt.DotLine)
            painter.setPen(focus_pen)
            painter.setBrush(Qt.NoBrush)
            inner = frame.adjusted(3 * s, 3 * s, -3 * s, -3 * s)
            painter.drawRoundedRect(inner, radius - 3 * s, radius - 3 * s)

        pad = 8 * s
        content = frame.adjusted(pad, pad, -pad, -pad)

        # Icon tile, doubling as the slot label until slice 2 adds icons.
        label = SLOT_LABELS.get(data.slot, data.slot).upper()
        label_font = self._font(12, QFont.Medium)
        label_metrics = QFontMetrics(label_font)
        tile_h = 32 * s
        tile_w = max(32 * s, label_metrics.horizontalAdvance(label) + 12 * s)
        tile = QRectF(content.left(), content.top(), tile_w, tile_h)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(theme.SURFACE_2))
        painter.drawRoundedRect(tile, 6 * s, 6 * s)
        if data.icon is not None:
            painter.drawPixmap(tile.toRect(), data.icon)
        else:
            painter.setFont(label_font)
            painter.setPen(QColor(theme.FAINT))
            painter.drawText(tile, Qt.AlignCenter, label)
        if data.badge:
            badge_font = self._font(12, QFont.Bold)
            painter.setFont(badge_font)
            size = 16 * s
            spot = QRectF(tile.right() + 4 * s, tile.top(), size, size)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(theme.GOLD))
            painter.drawEllipse(spot)
            painter.setPen(QColor(theme.BG))
            painter.drawText(spot, Qt.AlignCenter, data.badge)
        if data.note:
            dot = 7 * s
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(theme.WARNING))
            painter.drawEllipse(QRectF(content.right() - dot, content.top() + 2 * s, dot, dot))

        name_colour, caption_colour = _COLOURS.get(data.state, (theme.TEXT, theme.MUTED))
        if self.dimmed:
            name_colour = caption_colour = theme.FAINT
        if data.state == 'not_set':
            name, italic = 'Not specified', False
        elif data.state == 'empty':
            name, italic = 'Unequip', True
        else:
            name, italic = data.name, False
        name_font = self._font(13, QFont.Medium if data.state == 'owned' else QFont.Normal, italic)
        name_metrics = QFontMetrics(name_font)
        lines = elide_two_lines(name, name_metrics, int(content.width()))
        painter.setFont(name_font)
        painter.setPen(QColor(name_colour))
        y = tile.bottom() + 8 * s
        for line in lines:
            painter.drawText(QRectF(content.left(), y, content.width(), name_metrics.height()),
                             Qt.AlignLeft | Qt.AlignVCenter, line)
            y += name_metrics.height()
        if data.caption and data.state not in ('empty', 'not_set'):
            caption_font = self._font(12)
            caption_metrics = QFontMetrics(caption_font)
            painter.setFont(caption_font)
            painter.setPen(QColor(caption_colour))
            text = data.caption
            if text.startswith('from '):  # keep the word, shorten the path: "from Black…Attack"
                text = 'from ' + caption_metrics.elidedText(
                    text[5:], Qt.ElideMiddle, int(content.width() - caption_metrics.horizontalAdvance('from ')))
            else:
                text = caption_metrics.elidedText(text, Qt.ElideMiddle, int(content.width()))
            painter.drawText(QRectF(content.left(), content.bottom() - caption_metrics.height(), content.width(),
                                    caption_metrics.height()), Qt.AlignLeft | Qt.AlignVCenter, text)
        painter.end()


class EquipGrid(QWidget):
    SLOT_ORDER = ('main', 'sub', 'range', 'ammo', 'head', 'neck', 'ear1', 'ear2',
                  'body', 'hands', 'ring1', 'ring2', 'back', 'waist', 'legs', 'feet')
    cell_clicked = Signal(str)

    def __init__(self, scale: float = 1.0):
        super().__init__()
        self.scale = scale
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAccessibleName('Equipment grid')
        self.cells = {}
        self._selected = ''
        self._focus = 0
        self._keyboard = False  # the focus ring shows for keyboard use, not after a click
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        for index, slot in enumerate(self.SLOT_ORDER):
            cell = Cell(slot, scale)
            cell.clicked.connect(self._clicked)
            self.cells[slot] = cell
            self.grid.addWidget(cell, index // 4, index % 4)
        self.set_scale(scale)

    def set_scale(self, scale: float) -> None:
        self.scale = scale
        self.grid.setSpacing(max(2, round(GAP * scale - 6 * scale)))  # cells carry 3 px of ring room each side
        for cell in self.cells.values():
            cell.set_scale(scale)
        self.setFixedSize(self.grid.sizeHint())

    def set_cells(self, cells: dict) -> None:
        """Slots missing from `cells` render not_set."""
        for slot, cell in self.cells.items():
            data = cells.get(slot) or CellData(slot)
            if data.state not in STATES:
                data.state = 'not_set'
            cell.set_data(data)
        self._update_accessible()

    def cell(self, slot: str) -> CellData:
        return self.cells[slot].data

    def select(self, slot: str) -> None:
        self._selected = slot if slot in self.cells else ''
        for name, cell in self.cells.items():
            cell.selected = name == self._selected
            cell.update()
        if self._selected:
            self._set_focus(self.SLOT_ORDER.index(self._selected))

    def selected(self) -> str:
        return self._selected

    def focused_slot(self) -> str:
        return self.SLOT_ORDER[self._focus]

    def set_dimmed(self, dimmed: bool) -> None:
        for cell in self.cells.values():
            cell.dimmed = dimmed
            cell.update()

    def _clicked(self, slot: str) -> None:
        self._keyboard = False
        self.setFocus(Qt.MouseFocusReason)
        self.select(slot)
        self.cell_clicked.emit(slot)

    def _set_focus(self, index: int) -> None:
        self._focus = index
        self._paint_focus()
        self._update_accessible()

    def _paint_focus(self) -> None:
        for i, slot in enumerate(self.SLOT_ORDER):
            self.cells[slot].focused = self._keyboard and self.hasFocus() and i == self._focus
            self.cells[slot].update()

    def _update_accessible(self) -> None:
        cell = self.cells[self.SLOT_ORDER[self._focus]]
        self.setAccessibleName(cell.accessibleName())

    def focusInEvent(self, event):
        if event.reason() in (Qt.TabFocusReason, Qt.BacktabFocusReason, Qt.ShortcutFocusReason):
            self._keyboard = True
        self._paint_focus()
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self._paint_focus()
        super().focusOutEvent(event)

    def keyPressEvent(self, event):
        key = event.key()
        self._keyboard = True
        row, col = divmod(self._focus, 4)
        moves = {Qt.Key_Left: (0, -1), Qt.Key_Right: (0, 1), Qt.Key_Up: (-1, 0), Qt.Key_Down: (1, 0)}
        if key in moves:
            dr, dc = moves[key]
            self._set_focus(max(0, min(3, row + dr)) * 4 + max(0, min(3, col + dc)))
            return
        if key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self.select(self.SLOT_ORDER[self._focus])
            self.cell_clicked.emit(self._selected)
            return
        super().keyPressEvent(event)
