"""Shared lazy item sources and a reusable, keyboard-accessible detail card."""
from copy import deepcopy
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QCursor, QKeySequence, QShortcut
from PySide6.QtWidgets import QComboBox, QDialog, QFrame, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from ..core import equipment_effects as effects, item_res
from ..core.equipment_analysis import name_index
from ..core.equipment_matching import identity
from ..core.guide_catalog import JOBS
from . import widgets
from .equipment_preparation import EquipmentPreparation


class EquipmentService(QObject):
    changed = Signal()

    def __init__(self, ctx):
        super().__init__(ctx)
        self.ctx = ctx
        self.source = None
        self.names = {}
        self.bags = ()
        self.error = ''
        self._attempted_root = None
        self.cache = effects.EvaluationCache()
        self.preparation = EquipmentPreparation(self)
        self.preparation.ready.connect(self._ready)
        self.preparation.failed.connect(self._failed)
        self.preparation.loading_changed.connect(self._loading)
        ctx.windower_changed.connect(self._root_changed)

    def request(self, force=False):
        root = str(Path(self.ctx.windower_dir).resolve())
        if not force and self._attempted_root == root and self.error:
            return
        if force or self._attempted_root != root:
            self.source = None
            self.names = {}
            self.bags = ()
            self.cache.clear()
        self._attempted_root = root
        self.preparation.request(self.ctx.windower_dir, force=force)

    def _loading(self, loading):
        if loading:
            self.source = None
            self.names = {}
            self.bags = ()
            self.error = ''
            self.cache.clear()
        self.changed.emit()

    def _ready(self, source):
        if source is self.source:
            return
        self.source = source
        # Production snapshots already prepare the complete name index on the
        # worker. Only tiny explicitly injected test snapshots need a fallback.
        self.names = source.names if source.names is not None else name_index(source.items)
        self.bags = tuple(b for b in item_res.parse_rows(str(Path(source.root) / 'res' / 'bags.lua'))
                          if type(b.get('id')) is int and isinstance(b.get('en'), str))
        self.error = ''
        self.cache.clear()
        self.changed.emit()

    def _failed(self, error):
        self.source = None
        self.error = error
        self.changed.emit()

    def _root_changed(self, _root):
        self.source = None
        self.names = {}
        self.bags = ()
        self.cache.clear()
        self.error = 'Equipment source changed; refresh item data'
        self._attempted_root = None
        self.preparation.cancel()
        self.changed.emit()

    def close(self):
        self.preparation.close()
        self.source = None
        self.names = {}
        self.cache.clear()


def equipment_service(ctx):
    service = getattr(ctx, '_equipment_service', None)
    if service is None:
        service = ctx._equipment_service = EquipmentService(ctx)
    return service


class ItemCard(QDialog):
    """One nonmodal tool per consumer, bounded to the invoking app window."""
    def __init__(self, owner, service):
        super().__init__(owner, Qt.Tool)
        self.owner, self.service = owner, service
        self.payload = None
        self.invoker = None
        self.pinned = False
        self.setWindowTitle('Item details')
        self.setModal(False)
        self.setMinimumWidth(260)
        layout = QVBoxLayout(self)
        self.name = widgets.label('', 'SectionTitle', wrap=True)
        self.name.setTextFormat(Qt.PlainText)
        self.pin = widgets.button('Keep open', on_click=self._pin)
        self.pin.setCheckable(True)
        close = widgets.button('Close', on_click=self.dismiss)
        refresh = widgets.button('Refresh item data', on_click=lambda: service.request(force=True))
        controls = widgets.FlowLayout()
        for control in (self.pin, refresh, close):
            controls.addWidget(control)
        layout.addLayout(controls)
        layout.addWidget(self.name)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        body = QVBoxLayout(content)
        self.text = widgets.label('', wrap=True)
        self.text.setTextFormat(Qt.PlainText)
        self.text.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.text.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.copies = QComboBox()
        self.copies.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.copies.setMinimumContentsLength(12)
        self.copies.setAccessibleName('Inspect saved observation; does not change set')
        self.copies.currentIndexChanged.connect(self._render)
        body.addWidget(self.copies)
        body.addWidget(self.text)
        body.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        self.leave_timer = QTimer(self, singleShot=True, interval=250)
        self.leave_timer.timeout.connect(self._leave_check)
        self.service.changed.connect(self._render)
        QShortcut(QKeySequence('Escape'), self, activated=self.dismiss)

    def _pin(self):
        self.pinned = self.pin.isChecked()
        self.pin.setText('Kept open' if self.pinned else 'Keep open')

    def present(self, payload, invoker, *, transient=False):
        self.payload = deepcopy(payload)
        self.invoker = invoker
        self.pinned = not transient
        self.pin.setChecked(self.pinned)
        self.pin.setText('Kept open' if self.pinned else 'Keep open')
        self.copies.blockSignals(True)
        self.copies.clear()
        self.copies.addItem('Declared / allocated copy', None)
        for n, row in enumerate(self.payload.get('observations', ())):
            self.copies.addItem(f"Observation {n+1} · {row.get('bag') or 'bag unknown'} · "
                                f"{row.get('augments') or 'no augments recorded'}", row)
        self.copies.setVisible(self.copies.count() > 1)
        self.copies.blockSignals(False)
        self._render()
        window = self.owner.window()
        available = window.screen().availableGeometry()
        bounds = window.frameGeometry().intersected(available)
        self.resize(min(420, max(260, bounds.width() - 24)), min(640, max(180, bounds.height() - 48)))
        self.move(max(available.left(), bounds.right() - self.width() - 12),
                  max(available.top(), bounds.top() + 24))
        self.setAttribute(Qt.WA_ShowWithoutActivating, transient)
        self.show()
        if not transient:
            self.raise_()
            self.pin.setFocus(Qt.OtherFocusReason)
        else:
            self.leave_timer.start()

    def invalidate(self):
        self.leave_timer.stop()
        self.payload = None
        self.hide()

    def dismiss(self):
        invoker = self.invoker
        self.invalidate()
        if invoker is not None and invoker.isVisible():
            invoker.setFocus(Qt.OtherFocusReason)

    def reject(self):
        self.dismiss()

    def enterEvent(self, event):
        self.leave_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.pinned:
            self.leave_timer.start()
        super().leaveEvent(event)

    def _leave_check(self):
        if self.pinned:
            return
        point = QCursor.pos()
        over_card = self.frameGeometry().contains(point)
        over_invoker = self.invoker is not None and self.invoker.rect().contains(self.invoker.mapFromGlobal(point))
        if over_card or over_invoker:
            self.leave_timer.start()
        else:
            self.invalidate()

    def _render(self, *_args):
        if not self.payload:
            return
        payload, service = self.payload, self.service
        item_id = payload.get('item_id')
        if not item_id and service.source:
            ids = service.names.get(identity(payload.get('name')), ())
            item_id = ids[0] if len(ids) == 1 else None
        item = service.source.items.get(item_id) if service.source else None
        self.name.setText(item.en if item else payload.get('name') or 'Unknown item')
        lines = [f"Item {item_id or 'identity unavailable'}"]
        if item:
            jobs = [j for i, j in enumerate(JOBS, 1) if item.jobs & (1 << i)]
            lines += [f"Level {item.level} · Jobs: {', '.join(jobs) or 'unavailable'}",
                      'Slots: ' + ', '.join(s for s in item_res.SLOT_BITS if item_res.fits(item, s))]
        lines += ['', 'SOURCE-DESCRIBED BASE EFFECTS']
        description = service.source.descriptions.get(item_id) if service.source else None
        if description:
            interpreted = effects.interpret(item_id, description, service.source.fingerprint)
            lines += [f'{e.recipient.title()} · {e.stat.replace("_", " ")}: '
                      f'{e.value if e.value is not None else "unresolved"} {e.unit}' for e in interpreted.effects]
            if interpreted.unresolved:
                lines += ['Partial support · other text is uncalculated']
            lines += ['', 'FULL ORIGINAL DESCRIPTION', description,
                      '', 'Resource fingerprint:', service.source.fingerprint[:32], service.source.fingerprint[32:]]
        else:
            lines += ['Preparing descriptions…' if service.preparation.loading else
                      'Description unavailable. ' + service.error]
        lines += ['', 'DECLARED REQUIREMENT', payload.get('requirement') or
                  'Generic item information; no exact observed copy implied']
        copy = self.copies.currentData() or payload.get('observed')
        lines += ['', 'OBSERVED COPY' if self.copies.currentIndex() == 0 else
                  'INSPECTED OBSERVATION · DOES NOT CHANGE SELECTION', payload.get('snapshot') or 'Snapshot age unavailable']
        if copy:
            lines += [f"{copy.get('character_key') or copy.get('character') or 'Character unavailable'} · "
                      f"{copy.get('bag') or 'bag unknown'} · quantity {copy.get('count', 1)}",
                      'Augments / rank / path: ' + str(copy.get('augments') or 'None recorded'),
                      f"Rank: {copy.get('rank', 'unreported')} · Path: {copy.get('path') or 'unreported'}",
                      'Unsupported augment/rank/path magnitudes remain uncalculated.']
        else:
            lines += [payload.get('copy_status') or 'No uniquely bound observed copy. Generic information only.']
        lines += ['', 'Saved evidence does not prove current game readiness. Equipment contributions are not character totals.']
        self.text.setText('\n'.join(lines))


class TableItemDetails(QObject):
    """Adds explicit details plus hover without changing activation/edit gestures."""
    def __init__(self, owner, ctx, tables):
        super().__init__(owner)
        self.owner, self.ctx = owner, ctx
        self.service = equipment_service(ctx)
        self.card = ItemCard(owner, self.service)
        self.tables = tables
        self.pending = None
        self.timer = QTimer(self, singleShot=True, interval=350)
        self.timer.timeout.connect(self._hover)
        for table in tables:
            table.setMouseTracking(True)
            table.viewport().installEventFilter(self)
            table.model_.modelReset.connect(self.invalidate)
            table.selectionModel().selectionChanged.connect(self.invalidate)
            QShortcut(QKeySequence('Alt+I'), table, activated=lambda t=table: self.show(t))
        ctx.windower_changed.connect(self.invalidate)
        ctx.inventory_changed.connect(self.invalidate)

    def invalidate(self, *_args):
        self.timer.stop()
        self.pending = None
        self.card.invalidate()

    def activate(self):
        self.service.request()

    def show(self, table, row=None, *, transient=False):
        row = row if row is not None else table.selected_row()
        if not row or not (row.get('item_id') or row.get('name')):
            return
        self.service.request()
        self.card.present({'item_id': row.get('item_id'), 'name': row.get('name'),
                           'requirement': row.get('requirement') or 'Generic item / target; no observed binding'},
                          table, transient=transient)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseMove:
            table = next((t for t in self.tables if t.viewport() is obj), None)
            index = table.indexAt(event.position().toPoint())
            row = table._row_at(index) if index.isValid() else None
            pending = (table, row)
            if self.pending != pending:
                self.timer.stop()
                self.pending = pending
                if row and not (self.card.isVisible() and self.card.pinned):
                    self.timer.start()
        elif event.type() in (QEvent.Leave, QEvent.Hide):
            self.timer.stop()
            self.pending = None
            if event.type() == QEvent.Hide:
                self.card.invalidate()
        return False

    def _hover(self):
        if self.pending:
            table, row = self.pending
            self.show(table, row, transient=True)
