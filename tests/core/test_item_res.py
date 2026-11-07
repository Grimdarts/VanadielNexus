import os
import shutil
from pathlib import Path

from vanadiel_nexus.core import item_res, wiki

FIXTURE = str(Path(__file__).parents[1] / 'fixtures' / 'gearswap')


def test_items_keep_equipment_rows_with_every_field():
    items = item_res.items(FIXTURE)
    assert 1 not in items and 3000 not in items  # non-equipment rows filtered
    kavuk = items[23100]
    assert (kavuk.en, kavuk.enl, kavuk.slots, kavuk.jobs, kavuk.level) == (
        'Hashishin Kavuk +2', 'hashishin kavuk +2', 16, 65536, 99)
    assert kavuk.races == item_res.ALL_RACES and kavuk.superior_level == 0 and kavuk.rare  # flags 0xF840: Rare
    assert item_res.all_items(FIXTURE)[134].enl == 'copy of "Emeralda"'  # escaped quotes unescaped


def test_races_superior_level_and_rare_are_parsed():
    items = item_res.items(FIXTURE)
    assert items[23115].races == 256 and item_res.race_limited(items[23115])
    assert not item_res.race_limited(items[23100])
    assert items[23116].superior_level == 3
    assert items[23111].rare and not items[23110].rare


def test_slot_bits_and_ear_ring_pairs():
    items = item_res.items(FIXTURE)
    assert item_res.fits(items[23100], 'head') and not item_res.fits(items[23100], 'body')
    assert item_res.fits(items[16000], 'main') and item_res.fits(items[16000], 'sub')
    for slot in ('ear1', 'ear2'):
        assert item_res.fits(items[23108], slot)
    for slot in ('ring1', 'ring2'):
        assert item_res.fits(items[23110], slot)
    only_left = item_res.Item(id=9, en='x', slots=1 << item_res.SLOT_BITS['ring1'])
    assert item_res.fits(only_left, 'ring2')  # either bit of the pair


def test_wearable_checks_job_and_level():
    items = item_res.items(FIXTURE)
    assert item_res.wearable(items[23100], 16)        # BLU
    assert not item_res.wearable(items[23100], 1)     # WAR
    assert not item_res.wearable(items[23100], 16, level=98)


def test_by_name_maps_both_names_to_ids():
    names = item_res.by_name(FIXTURE)
    assert names['hashishin kavuk +2'] == [23100]
    assert names['taru. maillot +1'] == [23115] and names['tarutaru maillot +1'] == [23115]
    assert 'chocobo bedding' not in names


def test_jobs_ws_and_ja_names():
    assert item_res.jobs(FIXTURE)['BLU'] == (16, 'Blue Mage')
    assert 'savageblade' in item_res.ws_names(FIXTURE)
    ja = item_res.ja_names(FIXTURE)
    assert {'efflux', 'parsimony', 'mightystrikes'} <= ja
    assert 'searinglight' not in ja  # Blood Pacts are not job abilities


def test_bags_map_bag_keys_to_gearswap_names():
    bags = item_res.bags(FIXTURE)
    assert bags['wardrobe'] == 'Wardrobe' and bags['wardrobe2'] == 'Wardrobe 2'
    assert bags[item_res.bag_key('Wardrobe 1')] == 'Wardrobe'
    assert item_res.bag_key('Wardrobe 3') == 'wardrobe3' and item_res.bag_key('Mog Safe 1') == 'mogsafe1'


def test_items_lua_change_invalidates_the_cache(tmp_path):
    shutil.copytree(Path(FIXTURE) / 'res', tmp_path / 'res')
    assert 99999 not in item_res.items(str(tmp_path))
    path = tmp_path / 'res' / 'items.lua'
    text = path.read_text(encoding='utf-8').replace(
        '}, {"id"', '    [99999] = {id=99999,en="New Ring",ja="x",enl="new ring",jal="x",category="Armor",'
        'flags=0,jobs=2,level=1,races=510,slots=24576,stack=1,targets=0,type=5},\n}, {"id"')
    path.write_text(text, encoding='utf-8')
    os.utime(path, ns=(path.stat().st_atime_ns, path.stat().st_mtime_ns + 2_000_000_000))
    assert item_res.items(str(tmp_path))[99999].en == 'New Ring'
    assert item_res.by_name(str(tmp_path))['new ring'] == [99999]


def test_missing_windower_gives_empty_results(tmp_path):
    assert item_res.items(str(tmp_path)) == {} and item_res.jobs(str(tmp_path)) == {}
    assert item_res.bags(str(tmp_path)) == {}


def test_full_names_keep_non_equipment_shortened_names():
    names = wiki.full_names(FIXTURE)
    assert names[3000] == 'Tarutaru Folding Screen'  # not equipment, still kept (eng review D23)
    assert names[23115] == 'Tarutaru Maillot +1'
    assert 23100 not in names  # not shortened


def test_slot_label_names_each_slot_once():
    items = item_res.items(FIXTURE)
    assert item_res.slot_label(items[16000]) == 'Main / Sub'
    assert item_res.slot_label(items[23100]) == 'Head'
    assert item_res.slot_label(items[23108]) == 'Earring'
    assert item_res.slot_label(items[23110]) == 'Ring'
    assert item_res.slot_label(item_res.Item(id=1, en='Potion')) == ''


def test_equipment_names_use_the_game_spelling_and_skip_non_equipment():
    names = item_res.equipment_names(FIXTURE)
    assert names['Nyame Mail'].id == 23102 and "Epaminondas's Ring" in names
    assert not any(item.slots == 0 for item in names.values())
    assert item_res.equipment_names(FIXTURE + '-missing') == {}
