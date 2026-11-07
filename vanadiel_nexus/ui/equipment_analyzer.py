"""Equipment-only analysis of two existing declarations in one offline scenario."""
from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtWidgets import QComboBox, QPlainTextEdit, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from ..core.equipment_analysis import allocated_copy, comparable_rows, declared_selection, observations
from ..core.equipment_effects import RULES
from ..core.equipment_matching import SLOTS, allocate_requirements, units
from . import widgets
from .equipment_details import ItemCard, equipment_service


class EquipmentAnalyzer(QWidget):
    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.service = equipment_service(ctx)
        self.read = None
        self.path = ''
        self.sets = {}
        self.selections = {}
        self.inventory = ()
        self.snapshot_available = False
        self.card = ItemCard(parent or self, self.service)
        self._closed = False
        self._context_key = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.addWidget(widgets.label('Known equipment contributions', 'SectionTitle'))
        self.status = widgets.label('Select an existing set to analyze.', wrap=True)
        self.status.setTextFormat(Qt.PlainText)
        self.status.setAccessibleName('Equipment analysis status')
        layout.addWidget(self.status)
        self.baseline = QComboBox()
        self.baseline.setAccessibleName('Compare existing read-only set')
        self.baseline.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.baseline.setMinimumContentsLength(12)
        self.unity = QComboBox()
        self.unity.setAccessibleName('Offline Unity membership and standing assumption for both sets')
        self.unity.addItems(['Unknown affiliation / standing', 'Verified member · first place',
                             'Verified member · another valid standing'])
        self.unity.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.unity.setMinimumContentsLength(12)
        self.refresh = widgets.button('Refresh item data', on_click=lambda: self.service.request(force=True))
        self.details_button = widgets.button('Item details', on_click=self.show_selected_item)
        layout.addLayout(widgets.hbox(self.details_button, self.refresh, None))
        for caption, control in (('Compare existing set', self.baseline), ('Unity scenario · both selections', self.unity)):
            label = widgets.label(caption, 'Caption')
            label.setBuddy(control)
            layout.addWidget(label)
            layout.addWidget(control)
        layout.addWidget(widgets.label('Manual offline assumptions · no live-state claim. '
                                       'Inyanga membership is derived once per selection.', 'Caption', wrap=True))
        self.table = QTreeWidget()
        self.table.setColumnCount(4)
        self.table.setHeaderLabels(['Recipient / contribution', 'Selected', 'Baseline', 'Known change'])
        self.table.setRootIsDecorated(False)
        self.table.setMinimumHeight(170)
        self.table.setAccessibleName('Known equipment contributions and same-scenario comparison')
        self.table.setWordWrap(True)
        layout.addWidget(self.table)
        self.trace_toggle = widgets.button('Contribution trail & unknown effects', on_click=self._toggle_trace)
        layout.addWidget(self.trace_toggle)
        self.trace = QPlainTextEdit()
        self.trace.setReadOnly(True)
        self.trace.setAccessibleName('Equipment contribution provenance and uncalculated effects')
        self.trace.setMinimumHeight(160)
        self.trace.hide()
        layout.addWidget(self.trace)
        layout.addWidget(widgets.label('Declared slots only; omissions are not empty. '
                                       'Partial support · no effective caps or upgrade verdict.', 'Caption', wrap=True))
        self.baseline.currentIndexChanged.connect(self.recalculate)
        self.unity.currentIndexChanged.connect(self.recalculate)
        self.service.changed.connect(self._source_changed)
        self.selected_slot = ''
        self.result = None
        self.comparison = None
        self.hover_timer = QTimer(self, singleShot=True, interval=350)
        self.hover_timer.timeout.connect(self._hover)
        self.hover_cell = None

    def attach_grid(self, grid):
        self.grid = grid
        for cell in grid.cells.values():
            cell.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Enter:
            self.hover_cell = obj
            if not (self.card.isVisible() and self.card.pinned):
                self.hover_timer.start()
        elif event.type() in (QEvent.Leave, QEvent.Hide):
            self.hover_timer.stop()
            self.hover_cell = None
            if event.type() == QEvent.Hide:
                self.card.invalidate()
        return False

    def _hover(self):
        if self.hover_cell is not None:
            self.show_item(self.hover_cell.slot, self.hover_cell, transient=True)

    def _toggle_trace(self):
        self.trace.setVisible(not self.trace.isVisible())

    def activate(self):
        if not self._closed:
            self.service.request()

    def invalidate(self, message='Selection changed; waiting for the current read'):
        self.hover_timer.stop()
        self.read = None
        self.path = ''
        self.inventory = ()
        self.snapshot_available = False
        self.selections = {}
        self.result = self.comparison = None
        self.table.clear()
        self.trace.clear()
        self.card.invalidate()
        self.status.setText(message)
        self.details_button.setEnabled(False)

    def set_selection(self, read, path):
        self.card.invalidate()
        old_key = self._context_key
        key = (read.character, read.job, read.sub_job)
        self._context_key = key
        old_baseline = self.baseline.currentData() if old_key == key else None
        self.read, self.path = read, path
        self.sets = {s.path: s for s in read.sets}
        self.baseline.blockSignals(True)
        self.baseline.clear()
        self.baseline.addItem('No comparison', None)
        for other in read.sets:
            self.baseline.addItem(other.path, other.path)
        if old_baseline in self.sets:
            self.baseline.setCurrentIndex(self.baseline.findData(old_baseline))
        self.baseline.blockSignals(False)
        self.recalculate()

    def _source_changed(self):
        self.card.invalidate()
        self.recalculate()

    def scenario(self):
        index = self.unity.currentIndex()
        return {} if index == 0 else {'unity_member': True, 'unity_verified': True,
                                     'unity_rank': 1 if index == 1 else 2}

    def recalculate(self, *_args):
        self.result = self.comparison = None
        self.selections = {}
        self.inventory = ()
        self.snapshot_available = False
        self.table.clear()
        self.trace.clear()
        self.details_button.setEnabled(False)
        self.card.invalidate()
        if self._closed or self.read is None or self.path not in self.sets:
            return
        self.details_button.setEnabled(True)
        source = self.service.source
        if source is None:
            self.status.setText('Preparing descriptions… contributions cleared' if self.service.preparation.loading else
                                'Item data unavailable. ' + (self.service.error or 'Refresh item data to retry.'))
            return
        try:
            self.inventory, self.snapshot_available = observations(self.ctx.inventory_snapshot, self.read.character,
                                                                   self.service.bags)
            paths = {self.path, self.baseline.currentData()} - {None}
            self.selections = {p: declared_selection(self.sets[p], source, self.service.names,
                                                     self.read.job, self.service.bags) for p in paths}
            # Only requested equipment can affect either alternative. Material
            # stacks and unrelated equipment must not expand into physical units
            # in the selected-loadout allocator on every recalculation.
            wanted_ids = {s['item_id'] for selection in self.selections.values()
                          for s in selection.slots if s['state'] == 'selected'}
            self.inventory = tuple(row for row in self.inventory if row['item_id'] in wanted_ids)
            self.details_button.setEnabled(True)
            if not self.snapshot_available:
                self.status.setText('No inventory snapshot · Owned contributions unavailable. Generic item details remain available.')
                return
            ready = tuple(b['id'] for b in self.service.bags if b.get('equippable') is True)
            def evaluate(path):
                selection = self.selections[path]
                return self.service.cache.evaluate(list(selection.slots), source, job=self.read.job, mode='owned',
                                                   scenario=self.scenario(), inventory=self.inventory,
                                                   character=self.read.character, bindings=selection.bindings,
                                                   snapshot_available=True, equippable_bag_ids=ready)
            self.result = evaluate(self.path)
            baseline = self.baseline.currentData()
            self.comparison = evaluate(baseline) if baseline else None
            self._publish()
        except (ValueError, KeyError, TypeError) as error:
            self.result = self.comparison = None
            self.status.setText('Analysis unavailable: ' + str(error))

    def _publish(self):
        left, right = self.result, self.comparison
        partial = left.partial or (right is not None and right.partial)
        self.status.setText(('Partial declaration · ' if partial else 'Declared equipment · ')
                            + 'supported subset only · saved inventory evidence'
                            + (' · runtime read was incomplete' if self.read.partial else ''))
        trace = []
        for key, selected, baseline, delta in comparable_rows(left, right):
            recipient, stat, unit = key
            def value(c, result):
                if c is None:
                    return 'Unavailable'
                complete = c.complete and not result.partial and not self.read.partial
                pending = [e for e in c.trace if e.value is None]
                ranges = ', '.join(f'{e.bounds[0]}–{e.bounds[1]}' if e.bounds else 'unknown' for e in pending)
                if pending and all(e.value is None for e in c.trace):
                    return f'Unresolved · {ranges}'
                return f'{c.known} known' + (f' · {ranges} unresolved' if pending else '') + \
                       (' · supported' if complete else ' · partial')
            comparable = delta is not None and selected.complete and baseline.complete and not partial and not self.read.partial
            change = ('No comparison' if right is None else 'Unavailable' if delta is None else
                      f'{delta:+d}' + ('' if comparable else ' · partial'))
            row = QTreeWidgetItem([f'{recipient.title()} · {stat.replace("_", " ")}\n{unit}',
                                   value(selected, left), value(baseline, right), change])
            for column in range(4):
                row.setToolTip(column, row.text(column))
            self.table.addTopLevelItem(row)
        for label, result, path in (('SELECTED', left, self.path), ('BASELINE', right, self.baseline.currentData())):
            if result is None:
                continue
            trace += [f'{label}: {path}', 'Scenario: ' + str(self.scenario() or 'unknown Unity'),
                      'Resource: ' + self.service.source.fingerprint,
                      'Saved snapshot character: ' + self.read.character,
                      'Snapshot timestamp: ' + str((self.ctx.settings.get('inventory_updated') or {}).get(self.read.character, 'unavailable'))]
            trace += [f'{slot}: {state}' for slot, state in result.slot_states]
            trace += [f'{slot}: omitted' for slot in SLOTS if slot not in dict(result.slot_states)]
            selection = self.selections[path]
            from ..core.equipment_hands import EVIDENCE_REVISION, hand_evidence
            for slot in selection.slots:
                if slot['slot'] in ('main', 'sub') and slot['state'] == 'selected':
                    item = self.service.source.items.get(slot['item_id'])
                    evidence = hand_evidence(item) if item else None
                    if evidence:
                        trace.append(f'{slot["slot"]}: hand evidence {EVIDENCE_REVISION} / '
                                     f'{evidence.item_id} / {evidence.hand_type} / '
                                     f'{evidence.url} / {evidence.locator}')
                    else:
                        trace.append(f'{slot["slot"]}: hand type evidence unavailable')
            allocation = allocate_requirements(selection.slots, self.inventory, self.read.character,
                                               selection.bindings, equippable_bag_ids=tuple(
                                                   b['id'] for b in self.service.bags if b.get('equippable') is True))
            copies = list(units(self.inventory))
            for slot, match in allocation.items():
                if not match['owned']:
                    trace.append(f'{slot}: distinct copy unavailable')
                elif match['ambiguous']:
                    trace.append(f'{slot}: matching observations ambiguous; no unique copy assertion')
                else:
                    copy = copies[match['unit']]
                    trace.append(f"{slot}: observed {copy.get('bag') or 'bag unavailable'} · "
                                 f"augments/rank/path {copy.get('augments') or 'none recorded'} · "
                                 + ('ready in saved snapshot' if match['ready'] else 'bag readiness unconfirmed'))
            for contribution in result.contributions:
                trace += [f'{contribution.recipient} / {contribution.stat}: known {contribution.known} {contribution.unit}']
                for effect in contribution.trace:
                    rule = RULES[effect.rule_id]
                    trace += [f'  {effect.slot or "loadout (once)"} · item {effect.item_id or "qualifying membership"} · '
                              f'{effect.value if effect.value is not None else effect.bounds} · {effect.condition} · '
                              f'{effect.rule_id} · evidence {", ".join(rule.evidence)} · {effect.raw}']
            trace += ['UNCALCULATED: ' + u.reason + ': ' + u.raw for u in result.unresolved]
            trace += list(result.diagnostics) + list(self.selections[path].diagnostics) + ['']
        if not left.contributions:
            self.status.setText(self.status.text() + ' · no supported contributions available; inspect diagnostics')
        self.trace.setPlainText('\n'.join(trace))
        self.table.resizeColumnToContents(0)

    def card_payload(self, slot):
        if not self.read or self.path not in self.sets:
            return None
        piece = self.sets[self.path].pieces.get(slot)
        if piece is None or piece.empty:
            return None
        selection = self.selections.get(self.path)
        record = next((r for r in selection.slots if r['slot'] == slot and r['state'] == 'selected'), None) if selection else None
        observed, status = (None, 'Declared identity / eligibility unresolved; generic information only')
        if record:
            observed, status = allocated_copy(selection, self.inventory, self.read.character, slot,
                                               tuple(b['id'] for b in self.service.bags if b.get('equippable') is True))
        updated = (self.ctx.settings.get('inventory_updated') or {}).get(self.read.character)
        return {'item_id': record['item_id'] if record else None, 'name': piece.name, 'observed': observed,
                'observations': [r for r in self.inventory if record and r['item_id'] == record['item_id']],
                'copy_status': 'No inventory snapshot; generic information only' if record and not self.snapshot_available else status,
                'requirement': f'{slot} · {piece.name}\nAugments: {piece.augments or "none specified"}\n'
                               f'Designated bag: {piece.bag or "none specified"}',
                'snapshot': f'{self.read.character} · snapshot timestamp {updated}' if updated else
                            f'{self.read.character} · snapshot time unavailable'}

    def show_item(self, slot, invoker, *, transient=False):
        if not transient:
            self.selected_slot = slot
        payload = self.card_payload(slot)
        if payload:
            self.card.present(payload, invoker, transient=transient)
        elif not transient:
            self.status.setText(self.status.text().split('\n')[0] + '\nChoose a declared item in the grid to inspect.')

    def show_selected_item(self):
        slot = self.grid.focused_slot() if hasattr(self, 'grid') else self.selected_slot
        self.show_item(slot, self.details_button)

    def closeEvent(self, event):
        self._closed = True
        self.invalidate('Analysis closed')
        super().closeEvent(event)
