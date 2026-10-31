"""Guide sets compared with real inventory, with provenance and uncertain augments visible."""
from PySide6.QtWidgets import QComboBox
from ...core import gear_guides
from ..forms import Field, FormDialog
from .. import widgets, theme
from ..widgets import Column, DataTable
from .base import Page


class GuidesPage(Page):
    title = 'Guide upgrades'
    key = 'guides'

    def __init__(self, ctx):
        super().__init__(ctx)
        self.catalog = gear_guides.load_catalog()
        self.job_combo = QComboBox()
        self.job_combo.addItems([g['job'] for g in self.catalog['guides']])
        self.set_combo = QComboBox()
        self.set_combo.setMinimumWidth(280)
        self.set_combo.setMaximumWidth(440)
        self.set_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.set_combo.setMinimumContentsLength(32)
        self.character_combo = QComboBox()
        self.character_combo.setMaximumWidth(180)
        self.toolbar = widgets.SearchToolbar('Search guide equipment…')
        self.toolbar.add(self.job_combo, self.set_combo, self.character_combo)
        self.table = DataTable([
            Column('Item', 'name', 220), Column('Status', 'status', 150,
                tone=lambda r: theme.SUCCESS if r['status'] == 'Owned' else theme.WARNING),
            Column('Slot', 'slot', 75), Column('Target / assumptions', 'requirement', stretch=True),
            Column('Inventory check', 'detail', 280)], name='guide_upgrades')
        self.toolbar.text_changed.connect(self.table.proxy.set_needle)
        self.note = widgets.label('', 'Caption')
        self.note.setWordWrap(True)
        self.layout_.addWidget(self.toolbar)
        self.layout_.addWidget(self.table, 1)
        self.layout_.addWidget(self.note)
        self.layout_.addLayout(widgets.hbox(
            widgets.button('Track this set', 'primary', self._track),
            widgets.button('Open equipment set ↗', on_click=self._open_set),
            widgets.button('Set augment target…', on_click=self._requirements),
            widgets.button('Open job guide ↗', on_click=self._open_guide), None))
        self.job_combo.currentTextChanged.connect(self._sets)
        self.set_combo.currentIndexChanged.connect(self.refresh)
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

    def _sets(self):
        job = self.job_combo.currentText()
        self.set_combo.blockSignals(True)
        self.set_combo.clear()
        for row in self.catalog['sets']:
            if any(src['job'] == job for src in row['sources']):
                self.set_combo.addItem(f"{row['label']} · #{row['id']}", row)
        self.set_combo.blockSignals(False)
        self.refresh()

    def refresh(self, *_):
        row = self.set_combo.currentData()
        character = self.character_combo.currentText()
        if row:
            overrides=self.ctx.db.data.get('guide_requirements', {})
            items=[]
            for item in row['items']:
                key=f"{self.job_combo.currentText()}-{row['id']}-{item['item_id']}"
                items.append({**item, **overrides.get(key, {})})
            row={**row, 'items':items}
        self.current_set=row
        rows = gear_guides.set_rows(row, self.ctx.all_inventory(), character) if row else []
        self.table.set_rows(rows)
        owned = sum(r['status'] == 'Owned' for r in rows)
        missing = sum(r['status'] == 'Missing' for r in rows)
        unavailable = len(self.catalog.get('unavailable_sets', []))
        self.note.setText(f"{owned} verified owned · {missing} missing · {len(rows)-owned-missing} need checking. "
            f"Guide snapshot: {self.catalog['reviewed_on']}. Inventory is a saved snapshot until refreshed in game. "
            f"{unavailable} linked sets unavailable at collection. "
            + ('Source: '+next(src['guide_url'] for src in row['sources'] if src['job'] == self.job_combo.currentText()) if row else ''))

    def _track(self):
        row = self.current_set
        if row:
            count = gear_guides.track_set(self.ctx.db.data, row, self.job_combo.currentText())
            self.ctx.save_db()
            self.status(f'{count} guide targets added to Wishlist; existing goals preserved.')

    def _requirements(self):
        row=self.table.selected_row()
        equipment_set=self.set_combo.currentData()
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
        row = self.set_combo.currentData()
        if row:
            self.ctx.open_url(row['url'])

    def _open_guide(self):
        guide = next(g for g in self.catalog['guides'] if g['job'] == self.job_combo.currentText())
        self.ctx.open_url(guide['url'])
