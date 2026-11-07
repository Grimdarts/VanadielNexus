"""Guide sets compared with real inventory, with provenance and uncertain augments visible.

Sets are picked in three short steps: Purpose (what GearSwap would use it for) → Set → Version (gear tier).
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QButtonGroup, QComboBox, QMenu, QPushButton, QWidget
from ...core import gear_guides
from ..forms import Field, FormDialog
from .. import widgets, theme
from ..item_links import add_open_actions, open_item
from ..equipment_details import TableItemDetails
from ..widgets import Column, DataTable
from ..guide_revisions import RevisionGuideMixin
from .base import Page


class GuidesPage(RevisionGuideMixin, Page):
    title = 'Guide upgrades'
    key = 'guides'

    def on_shown(self):
        self.item_details.activate()

    def __init__(self, ctx, *, catalog=None, workspace=None, items=None, bags=None):
        super().__init__(ctx)
        self._init_workspace(workspace, items, bags)
        self.catalog_error = None
        try:
            # Explicit catalog injection is a prepared-candidate seam for offline
            # integration tests; bundled catalogs always pass the real loader.
            self.catalog = catalog if catalog is not None else gear_guides.load_catalog(windower_dir=ctx.windower_dir)
        except (OSError, ValueError) as error:
            self.catalog_error = str(error)
            message = widgets.label(f'Guide catalog unavailable: {error}', 'Caption')
            message.setWordWrap(True)
            self.layout_.addWidget(message)
            # Retained personal snapshots remain inspectable even when the
            # bundled catalog is unusable. New mutations fail closed.
            self.catalog = {'schema_version': 2, 'sets': [], 'revisions': [], 'sources': []}
        self.is_v2 = self.catalog['schema_version'] == 2
        self.tree = {}
        self._sets_shown = []  # the chosen target's sets, best version first (one per version button)
        self.current_set = None
        self.job_combo = QComboBox()
        jobs = sorted({j for s in self.catalog['sets'] for j in s['jobs']}) if self.is_v2 else [g['job'] for g in self.catalog['guides']]
        self.job_combo.addItems(jobs)
        self.purpose_combo = QComboBox()
        self.purpose_combo.setMinimumContentsLength(16)
        self.target_combo = QComboBox()
        self.target_combo.setMinimumWidth(220)
        self.target_combo.setMaximumWidth(380)
        self.target_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.target_combo.setMinimumContentsLength(24)
        self.character_combo = QComboBox()
        self.character_combo.setMaximumWidth(180)
        self.toolbar = widgets.SearchToolbar('Search guide equipment…')
        self.toolbar.add(self.job_combo, self.purpose_combo, self.target_combo, self.character_combo)
        self.versions = QWidget()
        self.versions_row = widgets.FlowLayout(self.versions)
        self.versions_row.addWidget(widgets.label('Version', 'Caption'))
        self.version_group = QButtonGroup(self)
        self.version_group.setExclusive(True)
        self.version_group.idClicked.connect(self._version_picked)
        self.purpose_help = widgets.label('', 'Caption')
        self.purpose_help.setWordWrap(True)
        self.table = DataTable([
            Column('Item', 'name', 220), Column('Status', 'status', 150,
                tone=lambda r: theme.SUCCESS if r['status'] in ('Owned', 'Ready in snapshot') else theme.WARNING),
            Column('Slot', 'slot', 75), Column('Target / assumptions', 'requirement', stretch=True),
            Column('Inventory check', 'detail', 280)], name='guide_upgrades')
        self.toolbar.text_changed.connect(self.table.proxy.set_needle)
        self.table.row_activated.connect(lambda row: open_item(self.ctx, row) if row.get('item_id') else None)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.item_details = TableItemDetails(self, ctx, (self.table,))
        self.table.customContextMenuRequested.connect(self._context_menu)
        self.note = widgets.label('', 'Caption')
        self.note.setWordWrap(True)
        self.layout_.addWidget(self.toolbar)
        self.layout_.addWidget(self.versions)
        self.layout_.addWidget(self.purpose_help)
        self._revision_controls()
        self.layout_.addWidget(self.table, 1)
        self.layout_.addWidget(self.note)
        actions = widgets.FlowLayout()
        self.track_button = widgets.button('Track this set', 'primary', self._track)
        self.source_button = widgets.button('Open equipment set ↗', on_click=self._open_set)
        self.edit_button = widgets.button('Set augment target…', on_click=self._requirements)
        self.item_details_btn = widgets.button('Item details', on_click=lambda: self.item_details.show(self.table))
        self.job_source_button = widgets.button('Open job guide ↗', on_click=self._open_guide)
        self.job_source_button.setVisible(not self.is_v2)
        for button in (self.track_button, self.source_button, self.edit_button, self.item_details_btn, self.job_source_button,
                       self.reload_workspace, self.recover_workspace):
            actions.addWidget(button)
        self.layout_.addLayout(actions)
        self.job_combo.currentTextChanged.connect(self._sets)
        self.purpose_combo.currentIndexChanged.connect(self._targets)
        self.target_combo.currentIndexChanged.connect(self._versions)
        self.character_combo.currentTextChanged.connect(self._character_picked)
        ctx.inventory_changed.connect(self._characters)
        ctx.job_changed.connect(self._job)
        self._characters()
        self._job(ctx.job)
        self._sets()

    def _job(self, job):
        if job in [self.job_combo.itemText(i) for i in range(self.job_combo.count())]:
            self.job_combo.setCurrentText(job)

    def _characters(self):
        current = self.character_combo.currentText()
        self.character_combo.blockSignals(True)
        self.character_combo.clear()
        saved = self.workspace.data or self.workspace.recovery or {}
        names = sorted(({row.get('character', '') for row in self.ctx.all_inventory()} |
                        {key for key in self.ctx.inventory_snapshot if not key.startswith('Imported: ')} |
                        {t['character_key'] for t in saved.get('targets', [])}) - {''})
        self.character_combo.addItems(names or ['No inventory snapshot'])
        preferred = self.ctx.bridge.state.get('player_name', '') or self.ctx.settings.get('guide_character') or ''
        self.character_combo.setCurrentText(current if current in names else preferred if preferred in names else names[0] if names else 'No inventory snapshot')
        self.character_combo.blockSignals(False)
        self.refresh()

    def _character_picked(self, character):
        self._browse_revision()
        if character and character!='No inventory snapshot':
            self.ctx.settings.set('guide_character', character)
        self.refresh()

    # --- Purpose → Set → Version -------------------------------------------
    def _job_picks(self) -> dict:
        """This job's saved picks: {"purpose", "target", "versions": {target: set id}}; tolerates a hand-edited file."""
        picks = self.ctx.settings.get('guide_picks')
        job = picks.get(self.job_combo.currentText()) if isinstance(picks, dict) else None
        return job if isinstance(job, dict) else {}

    def _pick(self, key):
        return self._job_picks().get(key)

    def _remember(self, version_picked: bool = False):
        """Saves the shown purpose and set; the version only when the player clicked one (never a default)."""
        entry = self.current_set
        if not entry:
            return
        job = dict(self._job_picks())
        job['purpose'], job['target'] = self.purpose_combo.currentData(), self.target_combo.currentData()
        if version_picked:
            versions = job.get('versions') if isinstance(job.get('versions'), dict) else {}
            job['versions'] = {**versions, job['target']: entry['id']}
        picks = self.ctx.settings.get('guide_picks')
        self.ctx.settings.set('guide_picks', {**(picks if isinstance(picks, dict) else {}),
                                              self.job_combo.currentText(): job})

    def _merged_set(self):
        """The chosen set with the player's saved augment targets applied to its items."""
        row = self.current_set
        if not row:
            return None
        overrides = self.ctx.db.data.get('guide_requirements', {})
        job = self.job_combo.currentText()
        return {**row, 'items': [{**item, **overrides.get(f"{job}-{row['id']}-{item['item_id']}", {})}
                                 for item in row['items']]}

    @staticmethod
    def _fill(combo, items, wanted):
        """items: [(text, data)]; selects wanted when present, otherwise the first item."""
        combo.blockSignals(True)
        combo.clear()
        for text, data in items:
            combo.addItem(text, data)
        combo.setCurrentIndex(max(0, combo.findData(wanted)))
        combo.blockSignals(False)

    def _sets(self, *_):
        self._browse_revision()
        self.tree = (gear_guides.revision_tree if self.is_v2 else gear_guides.picker_tree)(self.catalog, self.job_combo.currentText())
        self._fill(self.purpose_combo, [(f'{purpose} ({sum(len(v) for v in targets.values())})', purpose)
                                        for purpose, targets in self.tree.items()], self._pick('purpose'))
        self._targets()

    def _targets(self, *_):
        self._browse_revision()
        targets = self.tree.get(self.purpose_combo.currentData(), {})
        self._fill(self.target_combo, [(entries[0]['group']['target'] if self.is_v2 else target, target)
                                       for target, entries in targets.items()], self._pick('target'))
        self.purpose_help.setText(gear_guides.PURPOSES.get(self.purpose_combo.currentData(), ''))
        self._versions()

    def _versions(self, *_):
        self._browse_revision()
        sets = self.tree.get(self.purpose_combo.currentData(), {}).get(self.target_combo.currentData(), [])
        for button in self.version_group.buttons():
            self.version_group.removeButton(button)
            self.versions_row.removeWidget(button)
            button.deleteLater()
        saved = self._pick('versions') if isinstance(self._pick('versions'), dict) else {}
        wanted = next((i for i, e in enumerate(sets) if e['id'] == saved.get(self.target_combo.currentData())), 0)
        if len(sets) > 1:
            for i, entry in enumerate(sets):
                button = QPushButton(entry.get('equipment_version') or entry.get('version') or 'Standard')
                button.setProperty('pill', True)
                button.setCheckable(True)
                button.setCursor(Qt.PointingHandCursor)
                button.setToolTip(entry['label'])
                self.version_group.addButton(button, i)
                self.versions_row.addWidget(button)
            self.version_group.button(wanted).setChecked(True)
        self.versions.setVisible(len(sets) > 1)
        self._sets_shown = sets
        self.current_set = sets[wanted] if sets else None
        # Opening a conceptual set shows the user's retained snapshot. Choosing
        # an alternative version explicitly returns to catalog browsing.
        saved_target = self._matching_target()
        if saved_target:
            self.view_target_id = saved_target['id']
            retained = next((i for i, r in enumerate(sets) if r['id'] == saved_target['revision_id']), None)
            if retained is not None:
                self.current_set = sets[retained]
            self.version_group.setExclusive(False)
            for button in self.version_group.buttons():
                button.setChecked(self.version_group.id(button) == retained)
            self.version_group.setExclusive(True)
        self.refresh()
        self._remember()

    def _version_picked(self, index):
        self._browse_revision()
        self.current_set = self._sets_shown[index]
        self.refresh()
        self._remember(version_picked=True)

    # -------------------------------------------------------------------------
    def refresh(self, *_):
        if self._refresh_revision():
            return
        row = self._merged_set()
        character = self.character_combo.currentText()
        rows = gear_guides.set_rows(row, self.ctx.all_inventory(), character) if row else []
        self.table.set_rows(rows)
        owned = sum(r['status'] == 'Owned' for r in rows)
        missing = sum(r['status'] == 'Missing' for r in rows)
        unavailable = len(self.catalog.get('unavailable_sets', []))
        self.note.setText((f"Guide note: {row['note']}\n" if row and row.get('note') else '')
            + f"{owned} verified owned · {missing} missing · {len(rows)-owned-missing} need checking. "
            f"Guide snapshot: {self.catalog['reviewed_on']}. Inventory is a saved snapshot until refreshed in game. "
            f"{unavailable} linked sets unavailable at collection. "
            + (f"Guide title: \"{row['label']}\". Source: "
               + next(src['guide_url'] for src in row['sources'] if src['job'] == self.job_combo.currentText())
               if row else ''))

    def _context_menu(self, pos):
        row = self.table.selected_row()
        if row is None:
            return
        menu = QMenu(self)
        menu.addAction('Item details (Alt+I)', lambda: self.item_details.show(self.table))
        if row.get('item_id'):
            add_open_actions(menu, self.ctx, row)
        menu.addSeparator()
        action = menu.addAction(self.edit_button.text(), self._requirements)
        action.setEnabled(self.edit_button.isEnabled() and row.get('state', 'selected') == 'selected')
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _track(self):
        if self._track_revision():
            return
        row = self._merged_set()  # carries augment targets set before tracking into the wishlist
        if row:
            count = gear_guides.track_set(self.ctx.db.data, row, self.job_combo.currentText())
            self.ctx.save_db()
            self.status(f'{count} guide targets added to Wishlist; existing goals preserved.')

    def _requirements(self):
        if self._edit_revision():
            return
        row=self.table.selected_row()
        equipment_set=self.current_set
        if not row or not equipment_set:
            return
        current=row.get('requirements', {})
        values=FormDialog.ask(self, f"Augment target: {row['name']}", [
            Field('path','Required path','choice',['Unknown / any','A','B','C','D']),
            Field('rank','Minimum rank (0 = unspecified)','int'),
            Field('augments','Required augment text, one per line','long'),
        ], {'path':current.get('path','Unknown / any'),'rank':current.get('rank',0),
            'augments':'\n'.join(current.get('augments',[]))})
        if values is None:
            return
        requirements={}
        if values['path']!='Unknown / any': requirements['path']=values['path']
        if values['rank']>0: requirements['rank']=values['rank']
        augs=[line.strip() for line in values['augments'].splitlines() if line.strip()]
        if augs: requirements['augments']=augs
        override={'requirements':requirements,'augmentable':True,
                  'requirement_note':'Player target: '+str(requirements or 'augment details still unspecified')}
        key=f"{self.job_combo.currentText()}-{equipment_set['id']}-{row['item_id']}"
        self.ctx.db.data.setdefault('guide_requirements',{})[key]=override
        for target in self.ctx.db.data['wishlist']:
            if target.get('guideSet')==equipment_set['id'] and target.get('guideItemId')==row['item_id'] and target.get('job')==self.job_combo.currentText():
                target['guideTarget'].update(override)
                target['obtainHow']=override['requirement_note']
        self.ctx.save_db()
        self.refresh()

    def _open_set(self):
        if self._open_revision_sources():
            return
        if self.current_set:
            self.ctx.open_url(self.current_set['url'])

    def _open_guide(self):
        if self._revision_context()[0] is not None:
            self._open_revision_sources()
            return
        guide = next(g for g in self.catalog['guides'] if g['job'] == self.job_combo.currentText())
        self.ctx.open_url(guide['url'])
