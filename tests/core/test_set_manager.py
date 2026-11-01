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
