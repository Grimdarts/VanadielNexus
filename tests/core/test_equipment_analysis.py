from types import MappingProxyType

import pytest

from vanadiel_nexus.core.equipment_analysis import (
    allocated_copy, comparable_rows, declared_selection, name_index, observations,
)
from vanadiel_nexus.core.equipment_effects import SourceSnapshot, evaluate
from vanadiel_nexus.core.equipment_matching import allocate_requirements
from vanadiel_nexus.core.gearswap_reader import Piece, SetRead
from vanadiel_nexus.core.item_res import Item

DESCRIPTION = 'MND+8 Magic Accuracy+11\nAll magic skills +8\n"Refresh"+1'
BAGS = ({'id': 10, 'en': 'Wardrobe 2', 'equippable': True},
        {'id': 1, 'en': 'Mog Safe', 'equippable': False})


def source():
    return SourceSnapshot('fictional', (), 'fictional-v1',
                          MappingProxyType({26184: Item(26184, 'Stikini Ring +1', enl='stikini ring +1', slots=24576, jobs=8)}),
                          MappingProxyType({26184: DESCRIPTION}))


def test_real_job_bit_order_empty_omission_and_unresolved_identity():
    read = SetRead('sets.idle', ['idle'], {'ring1': Piece('ring1', 'left_ring', 'Stikini Ring +1'),
                                         'ring2': Piece('ring2', 'right_ring', empty=True),
                                         'head': Piece('head', 'head', 'Unknown')})
    selection = declared_selection(read, source(), name_index(source().items), 'WHM')
    assert selection.slots == ({'slot': 'head', 'state': 'unknown', 'diagnostic': 'Item name/slot/job identity is unresolved'},
                               {'slot': 'ring1', 'state': 'selected', 'item_id': 26184, 'requirements': {}},
                               {'slot': 'ring2', 'state': 'empty'})
    assert not any(r['slot'] == 'main' for r in selection.slots)
    wrong_job = declared_selection(read, source(), name_index(source().items), 'BLU')
    assert next(s for s in wrong_job.slots if s['slot'] == 'ring1')['state'] == 'unknown'


def test_snapshot_character_isolation_empty_absent_and_no_input_mutation():
    raw = {'Alice': [{'item_id': 26184, 'bag': 'Wardrobe 2', 'augments': 'MND+1, Rank 15', 'rank': 15}],
           'Bob': [{'item_id': 26184}]}
    rows, available = observations(raw, 'alice', BAGS)
    assert available and len(rows) == 1 and rows[0]['bag_id'] == 10
    assert rows[0]['character_key'] == 'alice'
    assert rows[0]['augments'][0] == 'MND+1'
    assert raw['Alice'][0]['augments'] == 'MND+1, Rank 15'
    assert observations({'Alice': []}, 'Alice') == ((), True)
    assert observations({}, 'Alice') == ((), False)
    assert observations({'Imported: Alice': []}, 'Alice') == ((), False)
    with pytest.raises(ValueError, match='quantity'):
        observations({'Alice': [{'count': -1}]}, 'Alice')


def test_unknown_designated_bag_excludes_asserted_selection():
    read = SetRead('sets.idle', [], {'ring1': Piece('ring1', 'ring1', 'Stikini Ring +1', bag='Unknown')})
    selected = declared_selection(read, source(), name_index(source().items), 'WHM', BAGS)
    assert selected.slots[0]['state'] == 'unknown' and selected.diagnostics


def test_stored_duplicate_copies_are_not_unique_and_quantity_is_not_reused():
    slots = ({'slot': 'ring1', 'state': 'selected', 'item_id': 26184, 'requirements': {}},)
    rows = ({'item_id': 26184, 'character_key': 'Alice', 'bag_id': 1, 'count': 2},)
    assert allocate_requirements(slots, rows, 'Alice', equippable_bag_ids=(10,))['ring1']['ambiguous']
    read = SetRead('sets.idle', [], {'ring1': Piece('ring1', 'ring1', 'Stikini Ring +1')})
    selection = declared_selection(read, source(), name_index(source().items), 'WHM', BAGS)
    copy, status = allocated_copy(selection, rows, 'Alice', 'ring1', (10,))
    assert copy is None and 'ambiguous' in status
    pair = slots + ({**slots[0], 'slot': 'ring2'},)
    one = ({**rows[0], 'count': 1},)
    assert sum(r['owned'] for r in allocate_requirements(pair, one, 'Alice').values()) == 1


def test_absent_comparison_stat_is_unavailable_never_zero():
    slots = [{'slot': 'ring1', 'state': 'selected', 'item_id': 26184, 'requirements': {}}]
    left, right = evaluate(slots, source(), job='WHM'), evaluate([], source(), job='WHM')
    assert all(b is None and delta is None for _, a, b, delta in comparable_rows(left, right))
    assert all(delta == 0 for _, a, b, delta in comparable_rows(left, left))
