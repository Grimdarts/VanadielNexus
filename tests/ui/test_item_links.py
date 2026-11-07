"""Item links behave the same on every item page; the guide picker narrows sets in three steps."""
import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

# Legacy item-target settings and tier-picker regressions use the exact v1 snapshot.
# Current production v2 loader/page/adoption are exercised in test_guide_production_v2.
import pytest
from tests.guide_bundle_fixtures import LEGACY

@pytest.fixture(autouse=True)
def retained_v1_bundle(monkeypatch):
    from vanadiel_nexus.core import gear_guides
    monkeypatch.setattr(gear_guides, 'resource_path', lambda *_: str(LEGACY))

SITE_ACTIONS = ['Open on BG-Wiki ↗', 'Open on FFXIAH ↗', 'Open on FFXIclopedia ↗']


def context(tmp_path, monkeypatch):
    monkeypatch.setenv('VN_DATA_DIR', str(tmp_path / 'data'))
    from vanadiel_nexus.ui.context import AppContext
    ctx = AppContext('test')
    ctx.windower_dir = str(tmp_path / 'windower')
    ctx.opened = []
    ctx.open_url = ctx.opened.append
    ctx.inventory_snapshot = {'Someonesmall': [{'name': 'Nyame Helm', 'item_id': 23761, 'count': 1,
                                                'character': 'Someonesmall', 'bag': 'Wardrobe'}]}
    return ctx


def menu_texts(monkeypatch, page, table):
    """The texts of the page's right-click menu, captured instead of shown (exec would block)."""
    import sys
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QMenu
    shown = []

    class CapturedMenu(QMenu):
        def exec(self, *_a):
            shown.append([a.text() for a in self.actions()])

    monkeypatch.setattr(sys.modules[type(page).__module__], 'QMenu', CapturedMenu)
    table.selectRow(0)
    page._context_menu(QPoint(1, 1))
    return shown[0]


def test_every_item_page_offers_all_sites_and_double_click_rules(qtbot, tmp_path, monkeypatch):
    from vanadiel_nexus.ui.pages.guides import GuidesPage
    from vanadiel_nexus.ui.pages.inventory import InventoryPage
    from vanadiel_nexus.ui.pages.wishlist import WishlistPage
    from vanadiel_nexus.ui.pages.gear import GearPage
    ctx = context(tmp_path, monkeypatch)
    ctx.db.data['wishlist'].append({'id': 'w1', 'name': 'Nyame Helm', 'job': 'All',
                                    'wikiUrl': 'https://www.ffxiah.com/item-sets/1'})
    ctx.db.data['checkpoints'].append({'id': 'c1', 'job': 'All', 'category': 'Goal', 'title': 'Nyame Helm',
                                       'current': 0, 'target': 1})
    inventory, wishlist, guides, gear = InventoryPage(ctx), WishlistPage(ctx), GuidesPage(ctx), GearPage(ctx)
    for page in (inventory, wishlist, guides, gear):
        qtbot.addWidget(page)
    gear.tabs.setCurrentIndex(2)
    for page, table in ((inventory, inventory.table), (wishlist, wishlist.table), (guides, guides.table),
                        (gear, gear.goals)):
        texts = menu_texts(monkeypatch, page, table)
        assert [t for t in texts if t.startswith('Open on')] == SITE_ACTIONS, type(page).__name__

    inventory.table.row_activated.emit(inventory.table.model_.rows[0])
    assert ctx.opened[-1] == 'https://www.bg-wiki.com/ffxi/Nyame_Helm'
    ctx.settings.set('wiki_site', 'ffxiah')
    inventory.table.row_activated.emit(inventory.table.model_.rows[0])
    assert ctx.opened[-1] == 'https://www.ffxiah.com/item/23761'
    guide_row = guides.table.model_.rows[0]
    guides.table.row_activated.emit(guide_row)
    assert ctx.opened[-1].startswith('https://www.ffxiah.com/item/')

    edits = []
    monkeypatch.setattr(wishlist, '_edit', lambda *a: edits.append(a))
    wishlist.table.selectRow(0)
    count = len(ctx.opened)
    wishlist.table.doubleClicked.emit(wishlist.table.model().index(0, 0))
    assert len(ctx.opened) == count  # double-click on Wishlist still edits, it doesn't open a site
    wishlist.table.select_row(next(r for r in wishlist.table.model_.rows if r.get('id') == 'w1'))
    ctx.settings.set('wiki_site', 'bgwiki')
    wishlist._open_wiki()
    assert ctx.opened[-1] == 'https://www.bg-wiki.com/ffxi/Nyame_Helm'  # stored FFXIAH link isn't used for BG-Wiki


def test_default_site_setting_persists(qtbot, tmp_path, monkeypatch):
    from vanadiel_nexus.ui.pages.settings import SettingsPage
    ctx = context(tmp_path, monkeypatch)
    page = SettingsPage(ctx)
    qtbot.addWidget(page)
    page.wiki_site.setCurrentIndex(page.wiki_site.findData('ffxiclopedia'))
    from vanadiel_nexus.core.settings import Settings
    assert Settings(ctx.data_dir).get('wiki_site') == 'ffxiclopedia'


def test_picker_narrows_purpose_set_version_and_remembers_per_job(qtbot, tmp_path, monkeypatch):
    from vanadiel_nexus.ui.pages.guides import GuidesPage
    ctx = context(tmp_path, monkeypatch)
    page = GuidesPage(ctx)
    qtbot.addWidget(page)
    page.job_combo.setCurrentText('COR')
    purposes = [page.purpose_combo.itemData(i) for i in range(page.purpose_combo.count())]
    assert 'Weapon skill' in purposes and len(purposes) <= 10
    assert page.purpose_combo.itemText(purposes.index('Weapon skill')).startswith('Weapon skill (')
    page.purpose_combo.setCurrentIndex(purposes.index('Weapon skill'))
    page.target_combo.setCurrentIndex(page.target_combo.findData('Savage Blade'))
    buttons = page.version_group.buttons()
    assert page.versions.isVisibleTo(page) and buttons[0].text() == 'Dream tier' and buttons[0].isChecked()
    mid = next(b for b in buttons if b.text() == 'Mid tier')
    mid.click()
    assert page.current_set['version'] == 'Mid tier' and page.current_set['target'] == 'Savage Blade'
    assert {r['item_id'] for r in page.table.model_.rows} == {i['item_id'] for i in page.current_set['items']}
    assert 'weapon skill' in page.purpose_help.text()
    chosen = page.current_set['id']

    page.job_combo.setCurrentText('BLU')
    page.job_combo.setCurrentText('COR')
    assert page.current_set['id'] == chosen

    page.purpose_combo.setCurrentIndex(purposes.index('Idle'))
    if page.target_combo.count() and len(page.tree['Idle'][page.target_combo.currentData()]) == 1:
        assert not page.versions.isVisibleTo(page)


def test_saved_augment_target_survives_the_new_picker(qtbot, tmp_path, monkeypatch):
    from vanadiel_nexus.ui.pages.guides import GuidesPage
    ctx = context(tmp_path, monkeypatch)
    page = GuidesPage(ctx)
    qtbot.addWidget(page)
    page.job_combo.setCurrentText('COR')
    entry = page.current_set
    item = entry['items'][0]
    ctx.db.data['guide_requirements'] = {f"COR-{entry['id']}-{item['item_id']}": {
        'requirement_note': 'Player target: rank 15', 'requirements': {'rank': 15}, 'augmentable': True}}
    page.refresh()
    row = next(r for r in page.table.model_.rows if r['item_id'] == item['item_id'])
    assert row['requirement'] == 'Player target: rank 15'


def test_track_carries_augment_targets_set_before_tracking(qtbot, tmp_path, monkeypatch):
    from vanadiel_nexus.ui.pages.guides import GuidesPage
    ctx = context(tmp_path, monkeypatch)
    page = GuidesPage(ctx)
    qtbot.addWidget(page)
    page.job_combo.setCurrentText('COR')
    entry, item = page.current_set, page.current_set['items'][0]
    ctx.db.data['guide_requirements'] = {f"COR-{entry['id']}-{item['item_id']}": {
        'requirement_note': 'Player target: rank 15', 'requirements': {'rank': 15}, 'augmentable': True}}
    page._track()
    tracked = next(w for w in ctx.db.data['wishlist'] if w.get('guideItemId') == item['item_id']
                   and w.get('guideSet') == entry['id'])
    assert tracked['obtainHow'] == 'Player target: rank 15'
    assert tracked['guideTarget']['requirements'] == {'rank': 15}


def test_version_pills_wrap_instead_of_widening_the_window(qtbot, tmp_path, monkeypatch):
    from vanadiel_nexus.ui.pages.guides import GuidesPage
    ctx = context(tmp_path, monkeypatch)
    page = GuidesPage(ctx)
    qtbot.addWidget(page)
    for job in [page.job_combo.itemText(i) for i in range(page.job_combo.count())]:
        page.job_combo.setCurrentText(job)
        for p in range(page.purpose_combo.count()):
            page.purpose_combo.setCurrentIndex(p)
            for t in range(page.target_combo.count()):
                page.target_combo.setCurrentIndex(t)
                assert page.versions.minimumSizeHint().width() < 600, (job, page.target_combo.currentText())
    labels = [w for w in page.versions.findChildren(type(page.purpose_help)) if not w.isHidden()]
    assert len(labels) == 1  # the one "Version" caption, not one per refill


def test_hand_edited_settings_do_not_break_startup(qtbot, tmp_path, monkeypatch):
    from vanadiel_nexus.ui.pages.guides import GuidesPage
    from vanadiel_nexus.ui.pages.settings import SettingsPage
    ctx = context(tmp_path, monkeypatch)
    for picks in (['x', 'y'], {'COR': None}, {'COR': 'Idle'}, {'COR': {'versions': []}}):
        ctx.settings.set('guide_picks', picks)
        ctx.settings.set('wiki_site', [])
        page, settings = GuidesPage(ctx), SettingsPage(ctx)
        qtbot.addWidget(page)
        qtbot.addWidget(settings)
        page.job_combo.setCurrentText('COR')
        assert page.current_set


def test_version_is_remembered_per_set_and_only_when_clicked(qtbot, tmp_path, monkeypatch):
    from vanadiel_nexus.ui.pages.guides import GuidesPage
    ctx = context(tmp_path, monkeypatch)
    page = GuidesPage(ctx)
    qtbot.addWidget(page)
    page.job_combo.setCurrentText('RUN')
    purposes = [page.purpose_combo.itemData(i) for i in range(page.purpose_combo.count())]
    page.purpose_combo.setCurrentIndex(purposes.index('Defense'))
    page.target_combo.setCurrentIndex(page.target_combo.findData('Tank'))
    next(b for b in page.version_group.buttons() if b.text() == 'Starter #2').click()
    chosen = page.current_set['id']
    page.purpose_combo.setCurrentIndex(purposes.index('Idle'))
    page.purpose_combo.setCurrentIndex(purposes.index('Defense'))
    page.target_combo.setCurrentIndex(page.target_combo.findData('Tank'))
    assert page.current_set['id'] == chosen
