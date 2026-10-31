from vanadiel_nexus.core.gear_guides import equipment_status, set_rows, track_set


def test_same_name_is_not_proof_of_augmented_target():
    target = {'item_id': 1, 'name': 'Nyame Mail', 'augmentable': True}
    inventory = [{'id': 1, 'name': 'Nyame Mail', 'character': 'Me', 'count': 1}]
    assert equipment_status(target, inventory, 'Me')[0] == 'Verify augments'


def test_short_resource_name_and_character_identity():
    target = {'item_id': 1, 'name': 'Adhemar Wristbands +1', 'aliases': ['Adhemar Wrist. +1']}
    inventory = [{'name': 'Adhemar Wrist. +1', 'character': 'ME', 'count': 1}]
    assert equipment_status(target, inventory, 'Me')[0] == 'Owned'
    assert equipment_status(target, inventory, 'Other')[0] == 'Other character'


def test_requirements_must_be_on_same_physical_copy():
    target = {'item_id': 1, 'name': 'Cape', 'requirements': {'augments': ['STR+30', 'Weapon skill damage +10%']}}
    inventory = [{'id': 1, 'name': 'Cape', 'count': 1, 'augments': 'STR+30'},
                 {'id': 1, 'name': 'Cape', 'count': 1, 'augments': 'Weapon skill damage +10%'}]
    assert equipment_status(target, inventory)[0] == 'Upgrade / verify'


def test_rank_not_reported_cannot_complete_target():
    target = {'name': 'Nyame Mail', 'requirements': {'rank': 25, 'path': 'B'}}
    inventory = [{'name': 'Nyame Mail', 'count': 1, 'augments': 'Rank 25'}]
    assert equipment_status(target, inventory)[0] == 'Upgrade / verify'
    inventory[0]['path'] = 'B'
    assert equipment_status(target, inventory)[0] == 'Owned'


def test_two_ring_slots_require_two_copies():
    target = {'item_id': 1, 'name': 'Ring'}
    rows = set_rows({'items': [target, target]}, [{'id': 1, 'name': 'Ring', 'count': 1}])
    assert all(row['status'] == 'Missing' for row in rows)


def test_import_is_idempotent_and_preserves_personal_goals():
    original = {'id': 'mine', 'name': 'My item'}
    db = {'wishlist': [original]}
    target = {'id': '123', 'url': 'https://www.ffxiah.com/item-sets/123', 'items': [{'item_id': 1, 'name': 'Piece'}]}
    assert track_set(db, target, 'NIN') == 1
    assert track_set(db, target, 'NIN') == 0
    assert db['wishlist'][0] is original


def test_previous_tier_is_an_upgrade_not_completed_target():
    target={'item_id':2,'name':'Hat +3','tier_family':[{'item_id':1,'name':'Hat +2'}]}
    status,detail=equipment_status(target,[{'item_id':1,'name':'Hat +2','character':'Me','count':1}],'Me')
    assert status=='Upgrade tier'
    assert 'Hat +2' in detail
