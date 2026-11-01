from pathlib import Path

import pytest

from vanadiel_nexus.core import item_res, set_manager as sm
from vanadiel_nexus.core.gearswap_reader import JobRead, Piece, SetRead

FIXTURE = str(Path(__file__).parents[1] / 'fixtures' / 'gearswap')


@pytest.fixture(scope='module')
def game():
    return sm.GameData.load(FIXTURE)


def row(item_id, name, bag='Wardrobe 3', augments='', count=1, character='Alice'):
    return {'item_id': item_id, 'name': name, 'bag': bag, 'augments': augments, 'count': count,
            'character': character}


def make_set(**pieces):
    return SetRead('sets.Test', ['Test'], {slot: Piece(slot=slot, original_key=slot, **spec) if isinstance(spec, dict)
                                          else Piece(slot=slot, original_key=slot, name=spec)
                                          for slot, spec in pieces.items()})


def allocate(game, set_read, rows, rows_all=None, job='BLU', state='ok'):
    return sm.allocate(set_read, rows, rows_all if rows_all is not None else rows, game, job, state, 'Alice')


# ---------------------------------------------------------------- bags

def test_bag_key_treats_wardrobe_1_as_wardrobe():
    assert sm.bag_key('Wardrobe') == sm.bag_key('Wardrobe 1') == 'wardrobe'
    assert sm.bag_key('Wardrobe 3') == 'wardrobe3' and sm.bag_key('wardrobe3') == 'wardrobe3'
    assert sm.reachable('Inventory') and sm.reachable('Wardrobe 1') and sm.reachable('Wardrobe 8')
    assert not sm.reachable('Mog Safe 1') and not sm.reachable('Mog Satchel') and not sm.reachable('Storage Slip 06')


def test_bags_decide_owned_or_unreachable(game):
    rows = [row(23100, 'Hashishin Kavuk +2', 'Mog Safe 1')]
    assert allocate(game, make_set(head='Hashishin Kavuk +2'), rows)['head'].kind == 'unreachable'
    assert allocate(game, make_set(head='Hashishin Kavuk +2'), rows)['head'].detail == 'Mog Safe 1'
    slip = allocate(game, make_set(head='Hashishin Kavuk +2'), [row(23100, 'x', 'Storage Slip 06')])['head']
    assert (slip.kind, slip.detail) == ('unreachable', 'on a slip')
    owned = allocate(game, make_set(head='Hashishin Kavuk +2'), [row(23100, 'x', 'Wardrobe 3')])['head']
    assert (owned.kind, owned.bag, owned.detail) == ('owned', 'Wardrobe 3', 'Wardrobe 3')


def test_reachable_copy_wins_over_a_stored_one(game):
    rows = [row(23110, 'Sroda Ring', 'Mog Safe 1'), row(23110, 'Sroda Ring', 'Wardrobe 2')]
    status = allocate(game, make_set(ring1='Sroda Ring'), rows)['ring1']
    assert (status.kind, status.bag) == ('owned', 'Wardrobe 2')


def test_designated_wardrobe_matches_a_wardrobe_1_row(game):
    rows = [row(23110, 'Sroda Ring', 'Wardrobe 1')]
    status = allocate(game, make_set(ring1={'name': 'Sroda Ring', 'bag': 'Wardrobe'}), rows)['ring1']
    assert status.kind == 'owned'


def test_snapshot_states():
    assert sm.snapshot_state({}, 'Alice') == 'absent'
    assert sm.snapshot_state({'alice': []}, 'Alice') == 'empty'
    assert sm.snapshot_state({'Alice': [row(1, 'x')]}, 'alice') == 'ok'
    assert sm.snapshot_state({'Imported: x': [row(1, 'x')]}, 'Imported: x') == 'absent'


def test_no_snapshot_and_empty_and_not_set(game):
    statuses = allocate(game, make_set(head='Hashishin Kavuk +2', body={'name': '', 'empty': True}), [], state='absent')
    assert statuses['head'].kind == 'no_snapshot'
    assert statuses['body'].kind == 'empty'
    assert statuses['legs'].kind == 'not_set'
    assert list(statuses) == list(sm.SLOT_ORDER)


# ---------------------------------------------------------------- augments

def test_augment_key_ignores_order_and_rank_but_keeps_path():
    assert sm.augment_key(['DEX+12', 'AGI+12', 'Accuracy+20']) == sm.augment_key('Accuracy+20, AGI+12, DEX+12')
    assert sm.augment_key('Rank 15, Path: B, DEX+12') == sm.augment_key(['Path: B', 'DEX+12'])
    assert sm.augment_key('Path: B') != sm.augment_key('Path: A')
    assert sm.augment_key(['"Fast Cast"+5']) == sm.augment_key(["'Fast Cast'+5"])


def test_equip_match_mirrors_compare_augments():
    assert sm.equip_match(['DEX+12'], 'DEX+12, AGI+12')                 # subset
    assert not sm.equip_match(['DEX+12', 'STR+5'], 'DEX+12, AGI+12')
    assert sm.equip_match(['"Fast Cast"+5'], 'Fast Cast+5')            # quotes and + stripped
    assert sm.equip_match(['Mag. Acc.+8'], 'Mag.Acc.+8')
    assert sm.equip_match(['Accuracy+20'], 'Rank 15, Accuracy+20')     # synthetic Rank ignored
    assert sm.equip_match(['Path: B'], 'Path: B') and not sm.equip_match(['Path: A'], 'Path: B')
    assert sm.equip_match(['DEX+5', 'DEX+5'], 'DEX+5, DEX+5') and not sm.equip_match(['DEX+5', 'DEX+5'], 'DEX+5')
    assert sm.equip_match(['DEX+5'], '', rare=True)                    # Rare items always match
    assert sm.equip_match([], 'anything') and sm.equip_match([], '')


# ---------------------------------------------------------------- allocation (criterion 8, D20)

def test_one_ring_in_two_slots(game):
    statuses = allocate(game, make_set(ring1='Sroda Ring', ring2='Sroda Ring'), [row(23110, 'Sroda Ring')])
    assert statuses['ring1'].kind == 'owned'
    assert (statuses['ring2'].kind, statuses['ring2'].detail) == ('missing', 'only 1 owned')


def test_count_two_fills_both(game):
    statuses = allocate(game, make_set(ring1='Sroda Ring', ring2='Sroda Ring'), [row(23110, 'Sroda Ring', count=2)])
    assert statuses['ring1'].kind == statuses['ring2'].kind == 'owned'


def test_augmented_and_plain_piece_of_one_id(game):
    rows = [row(23114, 'Chirich Ring +1', augments='DEX+5, STR+5'), row(23114, 'Chirich Ring +1')]
    statuses = allocate(game, make_set(ring1='Chirich Ring +1',
                                       ring2={'name': 'Chirich Ring +1', 'augments': ['DEX+5']}), rows)
    assert statuses['ring1'].kind == statuses['ring2'].kind == 'owned'
    assert statuses['ring1'].row['augments'] == ''  # the plain piece takes the plain copy


def test_designated_bag_excludes_other_copies(game):
    status = allocate(game, make_set(ring1={'name': 'Sroda Ring', 'bag': 'Wardrobe 3'}),
                      [row(23110, 'Sroda Ring', 'Wardrobe 2')])['ring1']
    assert (status.kind, status.detail) == ('missing', 'not in Wardrobe 3')


def test_bag_only_piece_takes_the_plain_copy(game):
    rows = [row(23114, 'Chirich Ring +1', 'Wardrobe 1', 'DEX+5'), row(23114, 'Chirich Ring +1', 'Wardrobe 1')]
    statuses = allocate(game, make_set(ring1={'name': 'Chirich Ring +1', 'bag': 'Wardrobe 1'},
                                       ring2={'name': 'Chirich Ring +1', 'augments': ['DEX+5']}), rows)
    assert statuses['ring1'].kind == statuses['ring2'].kind == 'owned'
    assert statuses['ring1'].row['augments'] == ''


def test_overlap_case_both_owned_by_maximum_matching(game):
    # ring1 asks for augment X anywhere, ring2 for X in Wardrobe; copies in Wardrobe and Wardrobe 2 (Codex D20).
    rows = [row(23114, 'Chirich Ring +1', 'Wardrobe 1', 'DEX+5'), row(23114, 'Chirich Ring +1', 'Wardrobe 2', 'DEX+5')]
    statuses = allocate(game, make_set(ring1={'name': 'Chirich Ring +1', 'augments': ['DEX+5']},
                                       ring2={'name': 'Chirich Ring +1', 'augments': ['DEX+5'], 'bag': 'Wardrobe'}),
                        rows)
    assert statuses['ring1'].kind == statuses['ring2'].kind == 'owned'
    assert statuses['ring2'].bag == 'Wardrobe 1' and statuses['ring1'].bag == 'Wardrobe 2'


def test_other_character_and_not_wearable_and_unknown(game):
    rows_all = [row(23110, 'Sroda Ring', character='Aynon')]
    other = allocate(game, make_set(ring1='Sroda Ring'), [], rows_all)['ring1']
    assert (other.kind, other.detail) == ('other_character', 'On Aynon')
    cant = allocate(game, make_set(head="Warrior's Mask"), [row(23117, "Warrior's Mask")])['head']
    assert (cant.kind, cant.detail) == ('missing', "BLU can't wear this")
    assert allocate(game, make_set(head='No Such Item'), [])['head'].detail == 'Unknown item'
    wrong = allocate(game, make_set(head='Sroda Ring'), [])['head']
    assert (wrong.kind, wrong.detail) == ('unknown', 'Wrong slot')
    assert allocate(game, make_set(head='Hashishin Kavuk +2'), [])['head'].detail == 'Not owned'


def test_other_augments_owned_says_so(game):
    status = allocate(game, make_set(head={'name': 'Herculean Helm', 'augments': ['STR+10']}),
                      [row(23113, 'Herculean Helm', augments='DEX+10')])['head']
    assert (status.kind, status.detail) == ('missing', 'augments differ')


def test_rare_items_ignore_augments(game):
    status = allocate(game, make_set(ring1={'name': "Epaminondas's Ring", 'augments': ['DEX+99']}),
                      [row(23111, "Epaminondas's Ring")])['ring1']
    assert status.kind == 'owned'


def test_race_limited_and_superior_level_stay_owned_with_a_note(game):
    race = allocate(game, make_set(body='Taru. Maillot +1'), [row(23115, 'Taru. Maillot +1')])['body']
    assert race.kind == 'owned' and race.note == 'race-limited: check your race'
    sl = allocate(game, make_set(head='Hope Masque'), [row(23116, 'Hope Masque')])['head']
    assert sl.kind == 'owned' and sl.note == 'needs superior level 3'
    assert allocate(game, make_set(head='Hashishin Kavuk +2'), [row(23100, 'x')])['head'].note == ''


def test_build_views_uses_the_characters_rows(game):
    read = JobRead('Alice', 'BLU', '', 'x.lua', False, {}, sets=[make_set(head='Hashishin Kavuk +2', ring1='Sroda Ring')])
    snapshot = {'Alice': [row(23100, 'x')], 'Aynon': [row(23110, 'Sroda Ring', character='Aynon')]}
    view = sm.build_views(read, snapshot, FIXTURE)[0]
    assert view.statuses['head'].kind == 'owned'
    assert view.statuses['ring1'].kind == 'other_character'
    assert view.attention == 1 and view.filled == 2
    assert view.purpose == 'Other'


# ---------------------------------------------------------------- purposes (criterion 13)

@pytest.mark.parametrize('keys, purpose', [
    (['Avatar'], 'Pet'),
    (['BlueMagic', 'Battery'], 'Midcast: blue magic'),
    (['BlueMagic', 'Cures'], 'Midcast: blue magic'),
    (['CP'], 'Other'),
    (['DT', 'MDTV'], 'Defense'),
    (['Enhancing'], 'Midcast: enhancing'),
    (['Expiacion', 'Attack'], 'Weapon skill'),
    (['Idle', 'DTRefresh'], 'Idle'),
    (['Idle', 'Standard'], 'Idle'),
    (['JA', 'Efflux'], 'Job ability'),
    (['OneHandedTP', 'AccuracyLite'], 'Melee / TP'),
    (['Requiescat'], 'Weapon skill'),
    (['TankingTP', 'Tank'], 'Melee / TP'),
    (['buff', 'Parsimony'], 'Job ability'),
    (['damagetaken', 'DT'], 'Defense'),
    (['engaged', 'Melee'], 'Melee / TP'),
    (['idle', 'Avatar'], 'Idle'),
    (['latent_refresh'], 'Other'),
    (['midcast', 'CureAurora'], 'Midcast: healing'),
    (['midcast', 'EnhancingDuration'], 'Midcast: enhancing'),
    (['midcast', 'Pet', 'PhysicalBloodPactRage'], 'Pet'),
    (['midcast', 'Pet', 'MagicalBloodPactRage'], 'Pet'),
    (['midcast', 'Protectra'], 'Midcast: enhancing'),
    (['midcast', 'Elemental Magic', 'Seidr'], 'Midcast: nuking'),
    (['physicalpact'], 'Pet'),
    (['precast', 'FC', 'PDT'], 'Precast'),
    (['precast', 'WS', 'Shining Strike'], 'Weapon skill'),
    (['SavageBlade', 'Attack'], 'Weapon skill'),
])
def test_classify_real_paths(keys, purpose):
    assert sm.classify(keys, item_res.ws_names(FIXTURE), item_res.ja_names(FIXTURE)) == purpose


def test_key_words_split_camel_case_digits_and_punctuation():
    assert sm.key_words('OneHandedTP') == ['one', 'handed', 'tp']
    assert sm.key_words('DTRefresh') == ['dt', 'refresh']
    assert sm.key_words('Wardrobe3_test') == ['wardrobe', '3', 'test']
    assert sm.classify(['ra']) == 'Other' and sm.classify(['midcast', 'RA']) == 'Ranged'  # gated short token


# ---------------------------------------------------------------- fixes (slice 1, commit 2)

def test_tier_upgrades_use_res_names_fit_job_and_sort(game):
    from dataclasses import replace
    items = dict(game.items)
    items[9] = replace(items[23101], id=9, en='Hashishin Kavuk +4')
    items[10] = replace(items[23101], id=10, en='Hashishin Kavuk')
    expanded = sm.GameData(items, {**game.by_name, 'hashishin kavuk': [10]}, game.job_ids, game.bag_names)
    rows = [row(23101, 'wrong snapshot name', 'Mog Safe 1'), row(23101, 'x', 'Wardrobe 3'),
            row(9, 'x', 'Mog Safe 1'), row(23100, 'x'), row(23113, 'Herculean Helm')]
    p = make_set(head='Hashishin Kavuk +2').pieces['head']
    assert [r['item_id'] for r in sm.tier_upgrades(p, expanded, rows, 16)] == [9, 23101, 23101]
    assert sm.tier_upgrades(p, expanded, rows, 1) == []
    assert sm.tier_upgrades(make_set(ring1='Hashishin Kavuk +2').pieces['ring1'], expanded, rows, 16) == []
    assert len(sm.tier_upgrades(make_set(head='Hashishin Kavuk').pieces['head'], expanded, rows, 16)) == 4
    assert sm.tier_upgrades(make_set(head='Herculean Helm').pieces['head'], expanded, rows, 16) == []


@pytest.fixture
def lua():
    # Same optional runtime convention as the existing Lua tests.
    import sys
    import os
    runtime = os.environ.get('VN_LUA_RUNTIME')
    if runtime and runtime not in sys.path:
        sys.path.insert(0, runtime)
    return pytest.importorskip('lupa.luajit21').LuaRuntime()


@pytest.mark.parametrize('value', ['simple', "Epaminondas's Ring", '"Fast Cast"+5',
                                  'a\\b\n\r\t\x00123\x7f', 'both\'"quotes', 'é'])
@pytest.mark.parametrize('quote', ['"', "'"])
def test_lua_str_round_trips_controls_quotes_and_backslashes(lua, value, quote):
    assert lua.eval(sm.lua_str(value, quote)) == value


def test_fix_snippet_forms_key_priority_bag_rank_and_path(lua, game):
    p = Piece('head', 'HEAD', 'Hashishin Kavuk +2')
    assert sm.fix_snippet(p, row(23101, 'Hashishin Kavuk +3')) == 'HEAD="Hashishin Kavuk +3",'
    p.priority, p.bag = 10, 'Wardrobe 2'
    snippet = sm.fix_snippet(p, row(23101, 'Hashishin Kavuk +3', 'Wardrobe 1'), game.bag_names)
    assert snippet == 'HEAD={ name="Hashishin Kavuk +3", priority=10, bag="Wardrobe" },'
    p = Piece('ring1', 'left_ring', "Epaminondas's Ring")
    r = row(23111, "Epaminondas's Ring", augments='Rank 15, Path: B, "Fast Cast"+5, DEX+12')
    snippet = sm.fix_snippet(p, r)
    table = lua.execute('return {' + snippet + '}')['left_ring']
    assert 'Rank' not in snippet and table['name'] == r['name']
    assert sm.equip_match(list(table['augments'].values()), r['augments'])
    assert table['augments'][1] == 'Path: B'
    p.original_key = 'odd\'"\\key'
    assert lua.execute('return {' + sm.fix_snippet(p, r) + '}')[p.original_key]['name'] == r['name']


def test_find_line_strips_comments_verifies_path_and_alias_not_first_hit(tmp_path):
    source = tmp_path / 'sets.lua'
    source.write_text('''-- sets.Test = {head="Hashishin Kavuk +2"}
--[[ sets.Test = {head="Hashishin Kavuk +2"} ]]
local fake = "sets.Test = {"
sets.Other = {head="Hashishin Kavuk +2"}
sets['Test'] = {
  head="Hashishin Kavuk +2",
}
sets.Alias = sets.Test
''')
    loc = sm.find_line([str(source)], 'sets.Test', 'Hashishin Kavuk +2')
    assert loc.verified and loc.line == 6 and loc.file == str(source)
    assert not sm.find_line([str(source)], 'sets.Alias', 'Hashishin Kavuk +2').verified
    assert not sm.find_line([str(source)], 'sets.Absent', 'Hashishin Kavuk +2').candidates
    with source.open('a') as f:
        f.write('sets.Test = {head="Hashishin Kavuk +2"}\n')
    loc = sm.find_line([str(source)], 'sets.Test', 'Hashishin Kavuk +2')
    assert not loc.verified and len(loc.candidates) == 2


def test_find_shared_definition_requires_all_augments_in_one_table(tmp_path):
    source = tmp_path / 'gear.lua'
    source.write_text('''-- gear.fake = {name="Herculean Helm", augments={'DEX+10','STR+5'}}
gear.a = {name="Herculean Helm", augments={'DEX+10','AGI+5'}}
gear.b = {name="Herculean Helm", augments={'DEX+10','STR+5'}}
''')
    loc = sm.find_line([str(source)], '', 'Herculean Helm', ['DEX+10', 'STR+5'])
    assert loc.verified and loc.line == 3
    with source.open('a') as f:
        f.write('gear.c = {name="Herculean Helm", augments={"DEX+10","STR+5"}}\n')
    assert len(sm.find_line([str(source)], '', 'Herculean Helm', ['DEX+10', 'STR+5']).candidates) == 2
    assert not sm.find_line([str(source)], '', 'Herculean Helm', ['DEX+10', 'STR+6']).candidates


def read_sets(sets, files=()):
    return JobRead('Alice', 'BLU', '', 'job.lua', False, dict.fromkeys(files, 0), sets=sets)


@pytest.mark.parametrize('table_id', [0, 7])
def test_fix_plan_inheritance_dedupes_at_root_and_aliases_skipped(game, lua, table_id):
    root = make_set(head={'name': 'Herculean Helm', 'augments': ['DEX+10'], 'table_id': table_id})
    sets = [root]
    for i in range(3):
        sets.append(SetRead(f'sets.Child{i}', [f'Child{i}'], {'head': Piece('head', 'head', 'Herculean Helm',
                            ['DEX+10'], table_id=table_id, inherited_from=sets[-1].path, origin_path=root.path)}))
    root.aliases = ['sets.Shortcut']
    plan = sm.fix_plan(read_sets(sets), 23113, sm.augment_key(['DEX+10']),
                       row(23113, 'Herculean Helm', augments='STR+10'), game)
    assert len(plan.targets) == 1
    target = plan.targets[0]
    assert target.key == ('set', root.path, 'head') and len(target.affected_sets) == 4
    assert lua.execute('return {' + target.snippet + '}')['head']['augments'][1] == 'STR+10'


def test_fix_plan_shared_table_literal_and_direct_targets(game, lua, tmp_path):
    source = tmp_path / 'gear.lua'
    source.write_text('gear.helm={name="Herculean Helm",augments={"DEX+10"}}')
    sets = [SetRead(f'sets.S{i}', [f'S{i}'], {'head': Piece('head', 'head', 'Herculean Helm',
                    ['DEX+10'], table_id=7, shared_count=4)}) for i in range(4)]
    plan = sm.fix_plan(read_sets(sets, [str(source)]), 23113, sm.augment_key(['DEX+10']),
                       row(23113, 'Herculean Helm', augments='STR+10'), game)
    assert len(plan.targets) == 1 and plan.targets[0].key == ('table', 7)
    assert len(plan.targets[0].affected_sets) == 4 and plan.targets[0].location.verified
    assert lua.eval(plan.targets[0].snippet)['augments'][1] == 'STR+10'
    sets.append(SetRead('sets.Different', ['Different'], {'head': Piece('head', 'head', 'Herculean Helm', ['AGI+10'])}))
    assert len(sm.fix_plan(read_sets(sets), 23113, sm.augment_key(['DEX+10']), row(23113, 'Herculean Helm'), game).targets) == 1
    plain = [SetRead(f'sets.P{i}', [f'P{i}'], {'head': Piece('head', 'head', 'Hashishin Kavuk +2')}) for i in range(3)]
    plan = sm.fix_plan(read_sets(plain), 23100, frozenset(), row(23101, 'Hashishin Kavuk +3'), game)
    assert len(plan.targets) == 3 and '(3 places)' in plan.text()
    assert plan.text().count('head="Hashishin Kavuk +3",') == 3


def test_build_views_adds_upgrade_badges_without_changing_owned_status(game):
    read = read_sets([make_set(head='Hashishin Kavuk +2')])
    snapshot = {'Alice': [row(23100, 'Hashishin Kavuk +2'), row(23101, 'Hashishin Kavuk +3')]}
    view = sm.build_views(read, snapshot, FIXTURE)[0]
    assert view.statuses['head'].kind == 'owned' and len(view.upgrades['head']) == 1


def test_find_line_does_not_claim_unrelated_strings_after_assignment(tmp_path):
    source = tmp_path / 'sets.lua'
    source.write_text('sets.Test = gear.helm\nlocal unrelated="Herculean Helm"\n')
    assert not sm.find_line([str(source)], 'sets.Test', 'Herculean Helm').candidates


@pytest.mark.parametrize('shared', [False, True])
def test_fix_plan_does_not_replace_an_incompatible_other_slot(game, shared):
    from dataclasses import replace
    item = replace(game.items[16000], id=99, en='Main only', slots=1)
    expanded = sm.GameData({**game.items, 99: item}, game.by_name, game.job_ids, game.bag_names)
    sets = [make_set(main='Naegling'), SetRead('sets.Sub', ['Sub'], {'sub': Piece('sub', 'sub', 'Naegling')})]
    if shared:
        for s in sets:
            for p in s.pieces.values():
                p.table_id = 7
    read = read_sets(sets)
    plan = sm.fix_plan(read, 16000, frozenset(), row(99, 'Main only'), expanded)
    assert [t.slot for t in plan.targets] == ['main']
    assert plan.targets[0].key == ('set', 'sets.Test', 'main')


@pytest.mark.parametrize('priority, bag', [(None, ''), (10, ''), (None, 'Wardrobe 2'), (10, 'Wardrobe 2')])
@pytest.mark.parametrize('augments', ['', 'Rank 15', 'Rank 15, Path: B, "Fast Cast"+5, DEX+12', 'a\'b\\c\n123'])
def test_every_snippet_form_compiles_and_matches_its_copy(lua, game, priority, bag, augments):
    p = Piece('back', 'back', 'old', priority=priority, bag=bag)
    r = row(23112, "Rosmerta's Cape", 'Wardrobe 1', augments)
    value = lua.execute('return {' + sm.fix_snippet(p, r, game.bag_names) + '}')['back']
    if isinstance(value, str):
        assert value == r['name']
    else:
        generated = list(value['augments'].values()) if value['augments'] is not None else []
        assert value['name'] == r['name'] and sm.equip_match(generated, augments)
        assert value['priority'] == priority
        assert value['bag'] == ('Wardrobe' if bag else None)


def test_unknown_name_correction_only_targets_selected_set_and_verified_descendants(game):
    p = Piece('body', 'body', "Runeist's Coat +3")
    root = SetRead('sets.Idle', ['Idle'], {'body': p})
    child = SetRead('sets.Child', ['Child'], {'body': Piece('body', 'body', p.name, inherited_from=root.path)})
    grandchild = SetRead('sets.Grandchild', ['Grandchild'], {'body': Piece('body', 'body', p.name,
                          inherited_from=child.path, origin_path=root.path)})
    other = SetRead('sets.Other', ['Other'], {'body': Piece('body', 'body', p.name)})
    read = read_sets([root, child, grandchild, other])
    plan = sm.slot_fix_plan(read, root, p, row(23102, 'Nyame Mail'), game)
    assert len(plan.targets) == 1
    assert plan.targets[0].affected_sets == [root.path, child.path, grandchild.path]
    assert plan.targets[0].snippet == 'body="Nyame Mail",'
    assert not plan.targets[0].location.verified
    assert not sm.slot_fix_plan(read, root, p, row(23110, 'Sroda Ring'), game).targets
    assert sm.resolve(p, game, 'BLU')[1] == 'unknown'  # no fuzzy ownership matching


@pytest.mark.parametrize('key', ['left_ring', 'ring1', 'LEFT_RING'])
def test_fix_location_never_uses_another_slots_item_literal(game, tmp_path, key):
    source = tmp_path / 'sets.lua'
    source.write_text('sets.Test = {\n  ' + key + '=gear.ring,\n  right_ring="Chirich Ring +1",\n}\n')
    p = Piece('ring1', key, 'Chirich Ring +1', table_id=7)
    s = SetRead('sets.Test', ['Test'], {'ring1': p, 'ring2': Piece('ring2', 'right_ring', p.name)})
    plan = sm.fix_plan(read_sets([s], [str(source)]), 23114, frozenset(), row(23110, 'Sroda Ring'), game)
    target = next(t for t in plan.targets if t.slot == 'ring1')
    assert not target.location.verified and not target.location.candidates
    assert next(t for t in plan.targets if t.slot == 'ring2').location.line == 3


@pytest.mark.parametrize('definition', [
    'sets.Test = {\n  left_ring="Chirich Ring +1",\n  right_ring="Chirich Ring +1",\n}',
    'sets.Test = set_combine(sets.Base, {\n  ["left_ring"]={name="Chirich Ring +1",\n    augments={"DEX+5"}},\n  right_ring="Chirich Ring +1",\n})',
])
def test_fix_location_verifies_the_original_slot_field(tmp_path, definition):
    source = tmp_path / 'sets.lua'
    source.write_text(definition)
    loc = sm.find_line([str(source)], 'sets.Test', 'Chirich Ring +1', slot='left_ring')
    assert loc.verified and loc.line == 2


def test_standalone_assignment_is_not_verified_for_a_table_field_snippet(tmp_path):
    source = tmp_path / 'sets.lua'
    source.write_text('sets.Test = {}\nsets.Test.head="Hashishin Kavuk +2"\n')
    assert not sm.find_line([str(source)], 'sets.Test', 'Hashishin Kavuk +2', slot='head').verified


@pytest.mark.parametrize('later', ['{head=gear.old}', 'sets.Other'])
def test_set_combine_later_unknown_override_invalidates_earlier_literal(tmp_path, later):
    source = tmp_path / 'sets.lua'
    source.write_text('sets.Test=set_combine(\n  {head="Herculean Helm"},\n  ' + later + ')\n')
    assert not sm.find_line([str(source)], 'sets.Test', 'Herculean Helm', slot='head').verified


def test_set_combine_last_literal_wins_and_unrelated_fields_do_not_override(tmp_path):
    source = tmp_path / 'sets.lua'
    source.write_text('sets.Test=set_combine(\n  sets.Base,\n  {head=gear.old},\n  {head="Herculean Helm"},\n  {body="Nyame Mail"})\n')
    loc = sm.find_line([str(source)], 'sets.Test', 'Herculean Helm', slot='head')
    assert loc.verified and loc.line == 4


@pytest.mark.parametrize('separate_file', [False, True])
def test_direct_slot_assignment_invalidates_literal_destination(tmp_path, separate_file):
    source = tmp_path / 'sets.lua'
    source.write_text('sets.Test={head="Herculean Helm"}\n')
    override = tmp_path / 'override.lua' if separate_file else source
    with override.open('a') as f:
        f.write('sets.Test["head"]=gear.helm\n')
    loc = sm.find_line(list(dict.fromkeys([str(source), str(override)])), 'sets.Test', 'Herculean Helm', slot='head')
    assert not loc.verified


def test_source_locations_keep_lua_set_path_case(tmp_path):
    source = tmp_path / 'sets.lua'
    source.write_text('sets.idle={head=gear.helm}\nsets.Idle={head="Herculean Helm"}\n')
    assert not sm.find_line([str(source)], 'sets.idle', 'Herculean Helm', slot='head').verified
    assert sm.find_line([str(source)], 'sets.Idle', 'Herculean Helm', slot='head').line == 2


def test_blocked_designated_target_does_not_cancel_other_fixes(game):
    plain = make_set(head='Hashishin Kavuk +2')
    constrained = SetRead('sets.WS', ['WS'], {'head': Piece('head', 'head', plain.pieces['head'].name, bag='Wardrobe 2')})
    plan = sm.fix_plan(read_sets([plain, constrained]), 23100, frozenset(),
                       row(23101, 'Hashishin Kavuk +3', 'Mog Safe 1'), game)
    assert len(plan.targets) == 2 and len(plan.copyable_targets) == 1
    assert plan.targets[0].snippet == 'head="Hashishin Kavuk +3",'
    assert plan.targets[1].blocked_reason and not plan.targets[1].snippet
    assert '(1 places)' in plan.text() and '-- Skipped: Move this copy' in plan.text()
    assert 'bag="Mog Safe 1"' not in plan.text()


@pytest.mark.parametrize('shared', [False, True])
def test_copy_shortage_warns_for_one_copy_in_paired_slots(game, shared):
    sets = [SetRead('sets.Test', ['Test'], {slot: Piece(slot, slot, 'Chirich Ring +1', table_id=7 if shared else 0)
                                         for slot in ('ring1', 'ring2')})]
    if shared:
        sets.append(SetRead('sets.Other', ['Other'], {'ring1': Piece('ring1', 'ring1', 'Chirich Ring +1', table_id=7)}))
    read = read_sets(sets)
    replacement = row(23110, 'Sroda Ring')
    plan = sm.fix_plan(read, 23114, frozenset(), replacement, game)
    warnings = sm.copy_shortages(read, plan.copyable_targets, replacement, [replacement], game)
    assert len(warnings) == 1 and 'Ring 1 / Ring 2' in warnings[0]
    assert not sm.copy_shortages(read, plan.copyable_targets, replacement, [{**replacement, 'count': 2}], game)
    if not shared:
        assert not sm.copy_shortages(read, [plan.targets[0]], replacement, [replacement], game)


def test_copy_shortage_counts_an_unchanged_paired_slot_using_the_replacement(game):
    read = read_sets([make_set(ring1='Sroda Ring', ring2='Chirich Ring +1')])
    replacement = row(23110, 'Sroda Ring')
    plan = sm.fix_plan(read, 23114, frozenset(), replacement, game)
    assert len(sm.copy_shortages(read, plan.copyable_targets, replacement, [replacement], game)) == 1


def test_copy_shortage_accepts_raw_rows_without_character_metadata(game):
    read = read_sets([make_set(ring1='Chirich Ring +1', ring2='Chirich Ring +1')])
    replacement = row(23110, 'Sroda Ring')
    replacement.pop('character')
    plan = sm.fix_plan(read, 23114, frozenset(), replacement, game)
    assert len(sm.copy_shortages(read, plan.copyable_targets, replacement, [replacement], game)) == 1


@pytest.mark.parametrize('separate_file', [False, True])
def test_whole_set_reassignment_keeps_an_old_literal_unverified(tmp_path, separate_file):
    source = tmp_path / 'sets.lua'
    source.write_text('sets.Test={head="Herculean Helm"}\n')
    override = tmp_path / 'override.lua' if separate_file else source
    with override.open('a') as f:
        f.write('sets.Test=build_idle()\n')
    files = list(dict.fromkeys([str(source), str(override)]))
    assert not sm.find_line(files, 'sets.Test', 'Herculean Helm', slot='head').verified


@pytest.mark.parametrize('bag', ['Mog Safe 1', 'Mog Safe 2', 'Mog Sack', 'Mog Satchel', 'Mog Case',
                                 'Mog Locker', 'Mog Storage', 'Storage Slip 06', ''])
def test_designated_bag_fix_requires_a_reachable_destination(game, bag):
    p = Piece('head', 'head', 'Hashishin Kavuk +2', bag='Wardrobe 1')
    with pytest.raises(ValueError, match='Move this copy'):
        sm.fix_snippet(p, row(23101, 'Hashishin Kavuk +3', bag), game.bag_names)
