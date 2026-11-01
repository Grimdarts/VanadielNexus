"""Guide sets compared with real inventory, with provenance and uncertain augments visible.

Sets are picked in three short steps: Purpose (what GearSwap would use it for) → Set → Version (gear tier).
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QButtonGroup, QComboBox, QMenu, QPushButton, QWidget
from ...core import gear_guides
from ..forms import Field, FormDialog
from .. import widgets, theme
from ..item_links import add_open_actions, open_item
from ..widgets import Column, DataTable
from .base import Page


class GuidesPage(Page):
    title = 'Guide upgrades'
    key = 'guides'

    def __init__(self, ctx):
        super().__init__(ctx)
        self.catalog = gear_guides.load_catalog()
        self.tree = {}
        self._sets_shown = []  # the chosen target's sets, best version first (one per version button)
        self.current_set = None
        self.job_combo = QComboBox()
        self.job_combo.addItems([g['job'] for g in self.catalog['guides']])
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
                tone=lambda r: theme.SUCCESS if r['status'] == 'Owned' else theme.WARNING),
            Column('Slot', 'slot', 75), Column('Target / assumptions', 'requirement', stretch=True),
            Column('Inventory check', 'detail', 280)], name='guide_upgrades')
        self.toolbar.text_changed.connect(self.table.proxy.set_needle)
        self.table.row_activated.connect(lambda row: open_item(self.ctx, row))
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        self.note = widgets.label('', 'Caption')
        self.note.setWordWrap(True)
        self.layout_.addWidget(self.toolbar)
        self.layout_.addWidget(self.versions)
        self.layout_.addWidget(self.purpose_help)
        self.layout_.addWidget(self.table, 1)
        self.layout_.addWidget(self.note)
        self.layout_.addLayout(widgets.hbox(
            widgets.button('Track this set', 'primary', self._track),
            widgets.button('Open equipment set ↗', on_click=self._open_set),
            widgets.button('Set augment target…', on_click=self._requirements),
            widgets.button('Open job guide ↗', on_click=self._open_guide), None))
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
        names = sorted({row.get('character', '') for row in self.ctx.all_inventory()} - {''})
        self.character_combo.addItems(names or ['No inventory snapshot'])
        preferred = self.ctx.bridge.state.get('player_name', '') or self.ctx.settings.get('guide_character') or 'Someonesmall'
        self.character_combo.setCurrentText(current if current in names else preferred if preferred in names else names[0] if names else 'No inventory snapshot')
        self.character_combo.blockSignals(False)
        self.refresh()

    def _character_picked(self, character):
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
        self.tree = gear_guides.picker_tree(self.catalog, self.job_combo.currentText())
        self._fill(self.purpose_combo, [(f'{purpose} ({sum(len(v) for v in targets.values())})', purpose)
                                        for purpose, targets in self.tree.items()], self._pick('purpose'))
        self._targets()

    def _targets(self, *_):
        targets = self.tree.get(self.purpose_combo.currentData(), {})
        self._fill(self.target_combo, [(target, target) for target in targets], self._pick('target'))
        self.purpose_help.setText(gear_guides.PURPOSES.get(self.purpose_combo.currentData(), ''))
        self._versions()

    def _versions(self, *_):
        sets = self.tree.get(self.purpose_combo.currentData(), {}).get(self.target_combo.currentData(), [])
        for button in self.version_group.buttons():
            self.version_group.removeButton(button)
            self.versions_row.removeWidget(button)
            button.deleteLater()
        saved = self._pick('versions') if isinstance(self._pick('versions'), dict) else {}
        wanted = next((i for i, e in enumerate(sets) if e['id'] == saved.get(self.target_combo.currentData())), 0)
        if len(sets) > 1:
            for i, entry in enumerate(sets):
                button = QPushButton(entry.get('version') or 'Standard')
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
        self.refresh()
        self._remember()

    def _version_picked(self, index):
        self.current_set = self._sets_shown[index]
        self.refresh()
        self._remember(version_picked=True)

    # -------------------------------------------------------------------------
    def refresh(self, *_):
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
        add_open_actions(menu, self.ctx, row)
        menu.addSeparator()
        menu.addAction('Set augment target…', self._requirements)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _track(self):
        row = self._merged_set()  # carries augment targets set before tracking into the wishlist
        if row:
            count = gear_guides.track_set(self.ctx.db.data, row, self.job_combo.currentText())
            self.ctx.save_db()
            self.status(f'{count} guide targets added to Wishlist; existing goals preserved.')

    def _requirements(self):
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
        if self.current_set:
            self.ctx.open_url(self.current_set['url'])

    def _open_guide(self):
        guide = next(g for g in self.catalog['guides'] if g['job'] == self.job_combo.currentText())
        self.ctx.open_url(guide['url'])
