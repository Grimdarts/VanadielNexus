"""Wishlist names come from the game's own item list; nothing falls back to a particular player's name."""
import os
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

FIXTURE = str(Path(__file__).parents[1] / 'fixtures' / 'gearswap')


def page_with(tmp_path, monkeypatch, windower_dir):
    monkeypatch.setenv('VN_DATA_DIR', str(tmp_path / 'data'))
    from vanadiel_nexus.ui.context import AppContext
    from vanadiel_nexus.ui.pages.wishlist import WishlistPage
    ctx = AppContext('test')
    ctx.windower_dir = windower_dir
    return ctx, WishlistPage(ctx)


def test_suggestions_are_game_equipment_plus_your_catalog(qtbot, tmp_path, monkeypatch):
    ctx, page = page_with(tmp_path, monkeypatch, FIXTURE)
    qtbot.addWidget(page)
    ctx.db.data['catalog_db']['My Custom Ring'] = {'slot': 'Ring', 'zone': 'Somewhere'}
    names = page._suggestions()
    assert 'Nyame Mail' in names and 'Moonshade Earring' in names and 'My Custom Ring' in names
    assert 'Aurgelmir Orb' in names  # ammo counts as equipment


def test_prefill_uses_your_catalog_first_then_the_games_slot(qtbot, tmp_path, monkeypatch):
    ctx, page = page_with(tmp_path, monkeypatch, FIXTURE)
    qtbot.addWidget(page)
    ctx.db.data['catalog_db']['Nyame Mail'] = {'slot': 'Body (mine)', 'zone': 'Odyssey'}
    assert page._catalog_prefill('Nyame Mail') == {'slot': 'Body (mine)', 'zone': 'Odyssey'}
    # A pasted wiki link loses capitals; the game's spelling comes back with the slot
    assert page._catalog_prefill("epaminondas's ring") == {'name': "Epaminondas's Ring", 'slot': 'Ring'}
    assert page._catalog_prefill('Not An Item') == {}


def test_without_a_windower_folder_nothing_breaks(qtbot, tmp_path, monkeypatch):
    _ctx, page = page_with(tmp_path, monkeypatch, '')
    qtbot.addWidget(page)
    assert page._suggestions() == []
    assert page._catalog_prefill('Nyame Mail') == {}


def test_guide_rows_with_no_known_character_check_every_character(qtbot, tmp_path, monkeypatch):
    ctx, page = page_with(tmp_path, monkeypatch, FIXTURE)
    qtbot.addWidget(page)
    ctx.inventory_snapshot = {'Alt': [{'name': 'Nyame Mail', 'count': 1, 'character': 'Alt', 'bag': 'Wardrobe'}]}
    row = {'name': 'Nyame Mail', 'guideTarget': {'name': 'Nyame Mail'}}
    assert ctx.settings.get('guide_character') in ('', None) and not ctx.bridge.state.get('player_name')
    assert page._ownership(row) == 'Owned'


def test_the_logged_in_character_beats_the_last_guide_pick(qtbot, tmp_path, monkeypatch):
    ctx, page = page_with(tmp_path, monkeypatch, FIXTURE)
    qtbot.addWidget(page)
    ctx.inventory_snapshot = {'Main': [{'name': 'Nyame Mail', 'count': 1, 'character': 'Main', 'bag': 'Wardrobe'}],
                              'Alt': []}
    ctx.settings.set('guide_character', 'Alt')
    ctx.bridge.state = {'player_name': 'Main'}
    ctx.db.data['wishlist'].append({'id': 'g1', 'name': 'Nyame Mail', 'job': 'All',
                                    'guideTarget': {'name': 'Nyame Mail'}})
    page.refresh()
    row = page.table.model_.rows[0]
    assert page._ownership(row) == 'Owned'
    ctx.bridge.state = {}
    page.on_shown()  # the character changed, so the Have column is worked out again (now for Alt)
    assert page._ownership(page.table.model_.rows[0]) == 'Other character'
