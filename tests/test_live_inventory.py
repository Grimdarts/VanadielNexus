"""Isolated live snapshot regressions; never bind the game's fixed ports."""
import json
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QObject
from vanadiel_nexus.bridge.udp import GameBridge
from vanadiel_nexus.ui.context import AppContext


@pytest.fixture
def bridge(qapp):
    b = GameBridge(listen_port=0)
    # These tests isolate snapshot assembly/publication after activation.
    # test_bridge_handshake covers the real challenge boundary separately.
    b._session_id = 'session'
    b._session_challenge = 'test'
    b._highest_update_seq = 0
    b._published_update_seq = 0
    yield b


def feed(bridge, packet):
    """Frame synthetic peer messages; deliberately complete activation for reload tests."""
    packet = dict(packet)
    session = packet.setdefault('session_id', 'session')
    packet.setdefault('update_seq', getattr(bridge, '_highest_update_seq', 0) + 1)
    packet.setdefault('challenge', 'test')
    if session != getattr(bridge, '_session_id', None):
        bridge._challenges = {session: ('test', __import__('time').monotonic())}
    bridge._handle_payload(packet)


def chunks(state, scan='scan', stamp=1, size=80):
    message = dict(type='STATE_UPDATE', state=state, session_id='session', update_seq=int(stamp), challenge='test')
    data = json.dumps(message).encode().hex()
    parts = [data[i:i+size] for i in range(0, len(data), size)]
    return [dict(type='SNAPSHOT_CHUNK', scan_id=scan, scan_time=stamp,
                 session_id='session', update_seq=int(stamp), challenge='test',
                 index=i, total=len(parts), data=part) for i, part in enumerate(parts)]


def test_chunks_publish_only_complete_out_of_order_snapshot(bridge):
    seen = []
    bridge.state_received.connect(seen.append)
    state = dict(player_name='Alice', inventory=[dict(name='Ore', count=2)], snapshot_complete=True)
    packets = chunks(state)
    for packet in reversed(packets[1:]):
        feed(bridge, packet)
    assert not seen
    feed(bridge, packets[0])
    assert seen == [state]


class Settings:
    def __init__(self):
        self.data = {}
    def get(self, key):
        return self.data.get(key)
    def set(self, key, value):
        self.data[key] = value


@pytest.fixture
def ctx(tmp_path, bridge):
    from PySide6.QtCore import QObject
    obj = AppContext.__new__(AppContext)
    QObject.__init__(obj)
    obj.inventory_snapshot = {}
    obj.settings = Settings()
    obj.job = ''
    obj._snapshot_path = str(tmp_path / 'snapshot.json')
    bridge.state_received.connect(obj._on_state)
    return obj


def test_partial_update_does_not_refresh_saved_inventory(ctx, bridge):
    feed(bridge, dict(type='STATE_UPDATE', state=dict(player_name='Alice',
        snapshot_complete=True, inventory=[dict(name='Ore', count=2)])))
    old_stamp = dict(ctx.settings.get('inventory_updated'))
    ctx.inventory_snapshot['Alice'] = [dict(name='Old', count=1)]
    feed(bridge, dict(type='STATE_UPDATE', state=dict(player_name='Alice', snapshot_complete=False)))
    assert ctx.inventory_snapshot['Alice'][0]['name'] == 'Old'
    assert ctx.settings.get('inventory_updated') == old_stamp


def test_empty_completed_scan_clears_rows(ctx, bridge):
    ctx.inventory_snapshot['Alice'] = [dict(name='Ore', count=2)]
    feed(bridge, dict(type='STATE_UPDATE', state=dict(player_name='Alice', snapshot_complete=True, inventory=[])))
    assert ctx.inventory_snapshot['Alice'] == []
    assert ctx.settings.get('inventory_updated')['Alice'] > 0


def test_character_switch_never_borrows_inventory(ctx, bridge):
    feed(bridge, dict(type='STATE_UPDATE', state=dict(player_name='Alice', inventory=[dict(name='Ore', count=2)])))
    feed(bridge, dict(type='STATE_UPDATE', state=dict(player_name='Bob', inventory=[])))
    assert 'inventory' not in bridge.state
    assert 'Bob' not in ctx.inventory_snapshot


def test_live_snapshot_shadows_only_matching_import_character(ctx):
    ctx.inventory_snapshot = {
        'Imported: both.csv': [dict(name='Ore', count=8, character='alice'),
                               dict(name='Ore', count=3, character='Bob'),
                               dict(name='Ore', count=4, character='Imported')],
        'Alice': [dict(name='Ore', count=2)]}
    assert sum(r['count'] for r in ctx.all_inventory()) == 9
    ctx.inventory_snapshot['Alice'] = []
    assert sum(r['count'] for r in ctx.all_inventory()) == 7
    assert len(ctx.inventory_snapshot['Imported: both.csv']) == 3


def test_latest_csv_character_shadows_previous_without_losing_other_characters(ctx):
    ctx.inventory_snapshot = {
        'Imported: old.csv': [dict(name='Ore', count=8, character='Alice'), dict(name='Ore', count=3, character='Bob')],
        'Imported: new.csv': [dict(name='Ore', count=2, character='ALICE')]}
    assert sum(r['count'] for r in ctx.all_inventory()) == 5


def test_interleaved_missing_duplicate_and_stale_scans(bridge):
    seen = []
    bridge.state_received.connect(seen.append)
    old = chunks(dict(player_name='Alice', inventory=[], snapshot_complete=True), 'old', 1)
    new = chunks(dict(player_name='Bob', inventory=[], snapshot_complete=True), 'new', 2)
    feed(bridge, old[0])
    feed(bridge, old[0])
    for packet in new:
        feed(bridge, packet)
    for packet in old[1:] + new:
        feed(bridge, packet)
    assert len(seen) == 1
    assert seen[0]['player_name'] == 'Bob'


def test_delayed_full_scan_cannot_overwrite_newer_partial_metadata(ctx, bridge):
    old = chunks(dict(player_name='Alice', main_job='WAR', zone_name='Old',
                      inventory=[dict(name='Ore', count=1)], snapshot_complete=True))
    feed(bridge, old[0])
    feed(bridge, dict(type='STATE_UPDATE', state=dict(
        player_name='Bob', main_job='WHM', zone_name='New', snapshot_complete=False)))
    for packet in old[1:]:
        feed(bridge, packet)
    assert bridge.state['player_name'] == 'Bob'
    assert bridge.state['main_job'] == 'WHM'
    assert bridge.state['zone_name'] == 'New'
    assert 'Alice' not in ctx.inventory_snapshot


def ordered_chunks(state, session, sequence, stamp=1):
    message = dict(type='STATE_UPDATE', state=state, session_id=session, update_seq=sequence, challenge='test')
    data = json.dumps(message).encode().hex()
    parts = [data[i:i+80] for i in range(0, len(data), 80)]
    return [dict(type='SNAPSHOT_CHUNK', scan_id=f'{session}-{sequence}', scan_time=stamp,
                 session_id=session, update_seq=sequence, challenge='test', index=i, total=len(parts), data=part)
            for i, part in enumerate(parts)]


def test_session_reload_accepts_clock_rollback_and_rejects_retired_updates(bridge):
    for packet in ordered_chunks(dict(player_name='Alice', inventory=[], snapshot_complete=True), 'first', 5, 2000):
        feed(bridge, packet)
    for packet in ordered_chunks(dict(player_name='Bob', inventory=[], snapshot_complete=True), 'reload', 1, 1000):
        feed(bridge, packet)
    assert bridge.state['player_name'] == 'Bob'
    for packet in ordered_chunks(dict(player_name='Alice', inventory=[], snapshot_complete=True), 'first', 99, 3000):
        feed(bridge, packet)
    feed(bridge, dict(type='STATE_UPDATE', session_id='first', update_seq=100,
                               state=dict(player_name='Alice', snapshot_complete=False)))
    assert bridge.state['player_name'] == 'Bob'


def test_ordered_partial_rejects_delayed_scan_even_if_first_chunk_is_late(bridge):
    feed(bridge, dict(type='STATE_UPDATE', session_id='session', update_seq=2,
                               state=dict(player_name='Bob', main_job='WHM', zone_name='New', snapshot_complete=False)))
    for packet in ordered_chunks(dict(player_name='Alice', main_job='WAR', zone_name='Old',
                                      inventory=[], snapshot_complete=True), 'session', 1):
        feed(bridge, packet)
    assert bridge.state['player_name'] == 'Bob'


def test_session_retirement_is_bounded_without_eviction(bridge):
    del bridge._session_id
    for index in range(65):
        feed(bridge, dict(type='STATE_UPDATE', session_id=f'session-{index}', update_seq=1,
                                   state=dict(player_name=f'Player{index}', snapshot_complete=False)))
    assert len(bridge._retired_sessions) == 64
    assert bridge.state['player_name'] == 'Player64'
    for session in ('session-0', 'session-65'):
        feed(bridge, dict(type='STATE_UPDATE', session_id=session, update_seq=2,
                                   state=dict(player_name='Unwanted', snapshot_complete=False)))
    assert len(bridge._retired_sessions) == 64
    assert bridge.state['player_name'] == 'Player64'


def test_modern_session_orders_all_updates_without_wallclock(bridge):
    state = dict(player_name='Alice', inventory=[], snapshot_complete=True)
    for packet in ordered_chunks(state, 'session', 1, 2000):
        feed(bridge, packet)
    for packet in ordered_chunks({**state, 'main_job': 'WHM'}, 'session', 2, 1000):
        feed(bridge, packet)
    assert bridge.state['main_job'] == 'WHM'
    bridge._handle_payload(dict(type='STATE_UPDATE', state=dict(player_name='Legacy', inventory=[])))
    feed(bridge, dict(type='STATE_UPDATE', session_id='session', update_seq=1,
                               state=dict(player_name='Stale', snapshot_complete=False)))
    assert bridge.state['player_name'] == 'Alice'
    assert bridge.state['main_job'] == 'WHM'


def test_assembly_expiration_and_resource_bounds(bridge, monkeypatch):
    import vanadiel_nexus.bridge.udp as udp
    clock = [1.0]
    monkeypatch.setattr(udp.time, 'monotonic', lambda: clock[0])
    packets = chunks(dict(player_name='Alice', inventory=[], snapshot_complete=True))
    feed(bridge, packets[0])
    clock[0] = 20
    for packet in packets[1:]:
        feed(bridge, packet)
    assert not bridge.state
    for i in range(10):
        feed(bridge, {**packets[0], 'scan_id': str(i)})
    assert len(bridge._pending) <= udp.MAX_PENDING
    feed(bridge, {**packets[0], 'total': udp.MAX_CHUNKS + 1})
    assert len(bridge._pending) <= udp.MAX_PENDING


@pytest.mark.parametrize('bad', [None, [], {'type':'STATE_UPDATE', 'state':[]},
    {'type':'SNAPSHOT_CHUNK', 'scan_id':'x', 'scan_time':float('nan')},
    {'type':'STATE_UPDATE', 'state':dict(player_name='Alice', snapshot_complete=True, inventory=[dict(name='Ore', count=1, character=42)])}])
def test_malformed_packets_are_ignored(bridge, bad):
    bridge._handle_datagram(json.dumps(bad).encode())
    assert not bridge.state


def test_freshness_does_not_hide_stale_characters(ctx, monkeypatch):
    from vanadiel_nexus.ui.pages.inventory import InventoryPage
    import vanadiel_nexus.ui.pages.inventory as page_module
    ctx.inventory_snapshot = {'Alice': [dict(name='Ore', count=1)], 'Bob': [dict(name='Ore', count=1)]}
    ctx.settings.set('inventory_updated', {'Alice': 100, 'Bob': 1000})
    monkeypatch.setattr(page_module.time, 'time', lambda: 1000)
    text = InventoryPage._updated_text(SimpleNamespace(ctx=ctx), 'All characters')
    assert '15 min ago' in text
    ctx.settings.set('inventory_updated', {'Bob': 1000})
    text = InventoryPage._updated_text(SimpleNamespace(ctx=ctx), 'All characters')
    assert 'saved' in text


def test_csv_reimport_is_latest_for_named_characters(ctx, tmp_path, monkeypatch):
    from vanadiel_nexus.ui.pages.inventory import InventoryPage, QFileDialog
    path = tmp_path / 'old.csv'
    path.write_text('Character,Bag,Item,Count\nAlice,Inventory,Ore,7\nBob,Safe,Ore,3\n')
    ctx.inventory_snapshot = {
        'Imported: old.csv': [dict(name='Ore', count=1, character='Alice')],
        'Imported: new.csv': [dict(name='Ore', count=2, character='Alice')]}
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *args: (str(path), ''))
    page = SimpleNamespace(ctx=ctx, status=lambda text: None)
    InventoryPage._import_csv(page)
    assert sum(row['count'] for row in ctx.all_inventory()) == 10
    assert ctx.inventory_snapshot['Imported: new.csv'][0]['count'] == 2
