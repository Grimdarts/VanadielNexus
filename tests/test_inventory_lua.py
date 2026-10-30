"""Run the actual addon in a sandboxed Lua VM, with no network or game access.

Set VN_LUA_RUNTIME to a scratch directory containing lupa when not installed.
"""
import json
import os
from pathlib import Path
import sys

import pytest

if os.environ.get('VN_LUA_RUNTIME'):
    sys.path.insert(0, os.environ['VN_LUA_RUNTIME'])


@pytest.fixture
def addon():
    lupa = pytest.importorskip('lupa.lua51', reason='Lua harness requires lupa (VN_LUA_RUNTIME supported)')
    lua = lupa.LuaRuntime(unpack_returned_tuples=True)
    lua.execute('''
        _addon = {}; events = {}; sent = {}; reads = {}; bag_failure = false
        bags = {}; for i=0,17 do bags[i] = {} end
        bags[0][1] = {id=1, count=2}
        bags[8][2] = {id=2, count=1}
        equipment = {main=2, main_bag=8}
        package.preload.socket = function() return {
            gettime=function() return 1000 end,
            udp=function() return {setsockname=function() end, settimeout=function() end,
                receive=function() if queued then local m=queued; queued=nil; return m end end, sendto=function(self, data) sent[#sent+1] = data; return #data end} end} end
        package.preload.resources = function() return {
            items={[1]={en='Ore', category='General'}, [2]={en='Sword', category='Weapon'}}, zones={}} end
        windower = {ffxi={
            get_player=function() return {name='Alice'} end,
            get_info=function() return {logged_in=true} end,
            get_items=function(id)
                if id == nil then return {inventory=bags[0], wardrobe=bags[8], equipment=equipment} end
                reads[id] = (reads[id] or 0) + 1
                if bag_failure and id == 1 then return nil end
                return bags[id]
            end},
            register_event=function(name, fn) events[name] = fn end,
            add_to_chat=function() end, send_command=function() end}
    ''')
    source = Path(__file__).parents[1] / 'vanadiel_nexus/resources/VanadielNexus.lua'
    lua.execute(source.read_text(encoding='utf-8'))
    return lua


def decode_sent(lua):
    packets = [json.loads(value) for _, value in lua.globals().sent.items()]
    if packets[0]['type'] == 'STATE_UPDATE':
        return packets, packets[0]['state']
    ordered = sorted(packets, key=lambda packet: packet['index'])
    raw = b''.join(bytes.fromhex(packet['data']) for packet in ordered)
    return packets, json.loads(raw)['state']


def test_numeric_bag_api_and_equipment_share_cached_reads(addon):
    addon.execute("events['load']()")
    packets, state = decode_sent(addon)
    assert {row['name'] for row in state['inventory']} == {'Ore', 'Sword'}
    assert state['equipped'] == [dict(slot='main', name='Sword', augments='')]
    assert addon.globals().reads[8] == 1
    assert state['snapshot_complete'] is True


def test_large_inventory_uses_bounded_roundtrippable_chunks(addon):
    addon.execute('''
        for bag=0,17 do for slot=1,80 do bags[bag][slot]={id=1, count=99} end end
        events['load']()
    ''')
    packets, state = decode_sent(addon)
    assert len(packets) > 1
    assert all(len(value.encode('utf-8')) <= 24000 for _, value in addon.globals().sent.items())
    assert len(state['inventory']) == 17 * 80
    assert all(packet['type'] == 'SNAPSHOT_CHUNK' for packet in packets)


def test_unavailable_bag_does_not_claim_complete_snapshot(addon):
    addon.execute("bag_failure = true; events['load']()")
    _, state = decode_sent(addon)
    assert state['snapshot_complete'] is False


def test_control_characters_and_utf8_roundtrip(addon):
    addon.execute("package.loaded.resources.items[1].en = 'Ore' .. string.char(1) .. '晶'")
    addon.execute("events['load']()")
    _, state = decode_sent(addon)
    assert state['inventory'][0]['name'] == 'Ore\x01晶'


def activate_addon(addon, bridge):
    """Exercise the real Lua receive path and bridge-issued targeted challenge."""
    requests = []
    bridge.send = requests.append
    addon.execute('sent={}; events["load"]()')
    bridge._handle_datagram(addon.globals().sent[1].encode())
    assert requests and requests[-1].startswith('SCAN|')
    addon.globals().queued = requests[-1]
    addon.execute('os.clock=function() return 100 end; sent={}; events["prerender"]()')


def test_large_lua_snapshot_over_actual_loopback_udp(addon, tmp_path, qtbot):
    from PySide6.QtNetwork import QHostAddress, QUdpSocket
    from vanadiel_nexus.bridge.udp import GameBridge
    bridge = GameBridge(listen_port=0)
    assert bridge.listening
    sender = QUdpSocket()
    seen = []
    bridge.state_received.connect(seen.append)
    addon.execute('for bag=0,17 do for slot=1,80 do bags[bag][slot]={id=1, count=99} end end')
    activate_addon(addon, bridge)
    for _, data in addon.globals().sent.items():
        raw = data.encode('utf-8')
        assert sender.writeDatagram(raw, QHostAddress(QHostAddress.LocalHost), bridge._sock.localPort()) == len(raw)
    qtbot.waitUntil(lambda: bool(seen), timeout=2000)
    assert len(seen[0]['inventory']) == 1360
    bridge._sock.close()


def test_lua_packets_feed_real_bridge_to_saved_snapshot(addon, tmp_path, qapp):
    from vanadiel_nexus.bridge.udp import GameBridge
    from vanadiel_nexus.ui.context import AppContext
    from tests.test_live_inventory import Settings
    from PySide6.QtCore import QObject
    bridge = GameBridge.__new__(GameBridge)
    QObject.__init__(bridge)
    bridge.connected = False
    bridge.state = {}
    ctx = AppContext.__new__(AppContext)
    QObject.__init__(ctx)
    ctx.settings = Settings()
    ctx.job = ''
    ctx._snapshot_path = str(tmp_path / 'snapshot.json')
    ctx.inventory_snapshot = {'Imported: old.csv': [dict(name='Ore', count=10, character='Alice')]}
    bridge.state_received.connect(ctx._on_state)
    activate_addon(addon, bridge)
    for _, data in addon.globals().sent.items():
        bridge._handle_datagram(data.encode('utf-8'))
    assert sum(row['count'] for row in ctx.all_inventory()) == 3
    assert json.loads((tmp_path / 'snapshot.json').read_text())['Alice'] == ctx.inventory_snapshot['Alice']


@pytest.mark.parametrize('bag', [
    '{[1]={id=999999,count=1},max=80,count=1,enabled=true}',
    '{max=80,count=1,enabled=true}',
    '{[1]={id=1,count=0},max=80,count=1,enabled=true}',
    '{[1]={id=1,count=0}}',
    '{[1]={id=0,count=1},max=80,count=0,enabled=true}',
])
def test_incomplete_occupied_bag_preserves_saved_inventory(addon, bag, qapp):
    from vanadiel_nexus.bridge.udp import GameBridge
    from PySide6.QtCore import QObject
    receiver = GameBridge.__new__(GameBridge)
    QObject.__init__(receiver)
    receiver.connected = False
    receiver.state = dict(player_name='Alice', inventory=[dict(name='Saved', count=3)])
    addon.execute('bags[0]=' + bag + '; bags[8]={}')
    activate_addon(addon, receiver)
    _, state = decode_sent(addon)
    assert state['snapshot_complete'] is False
    for _, data in addon.globals().sent.items():
        receiver._handle_datagram(data.encode())
    assert receiver.state['inventory'] == [dict(name='Saved', count=3)]


def test_all_lua_updates_have_reload_identity_and_monotonic_order(addon):
    addon.execute('events["load"]()')
    first = json.loads(addon.globals().sent[1])
    addon.globals().queued = 'SCAN|' + 'a' * 32 + '|' + first['session_id']
    addon.execute('os.clock=function() return 100 end; sent={}; events["prerender"]()')
    response = json.loads(addon.globals().sent[1])
    assert response['challenge'] == 'a' * 32
    addon.execute('sent={}; events["zone change"]()')
    assert json.loads(addon.globals().sent[1])['challenge'] == 'a' * 32
    addon.execute('sent={}; events["load"]()')
    full = json.loads(addon.globals().sent[1])
    addon.execute('sent={}; events["zone change"]()')
    partial = json.loads(addon.globals().sent[1])
    assert full['session_id'] == partial['session_id']
    assert partial['update_seq'] > full['update_seq']
    source = Path(__file__).parents[1] / 'vanadiel_nexus/resources/VanadielNexus.lua'
    addon.execute(source.read_text(encoding='utf-8'))
    addon.execute('sent={}; events["load"]()')
    reload = json.loads(addon.globals().sent[1])
    assert reload['session_id'] != full['session_id']
    assert reload['update_seq'] == 1


def test_scan_targeting_old_load_discovers_new_addon_without_accepting_nonce(addon):
    addon.globals().queued = 'SCAN|' + 'b' * 32 + '|retired-load'
    addon.execute('os.clock=function() return 100 end; sent={}; events["prerender"]()')
    packet = json.loads(addon.globals().sent[1])
    assert packet['challenge'] == ''
    assert packet['state']['snapshot_complete'] is False


def test_inventory_commit_waits_for_next_network_sequence(addon):
    addon.execute('''
        events["incoming chunk"](0x00A, string.char(0,0,10,0))
        events["incoming chunk"](0x01D, string.char(0,0,11,0))
        events["incoming chunk"](0x037, string.char(0,0,11,0))
        sent={}
        events["addon command"]("scan")
    ''')
    assert decode_sent(addon)[1]['snapshot_complete'] is False
    addon.execute('sent={}; events["incoming chunk"](0x037, string.char(0,0,12,0))')
    assert decode_sent(addon)[1]['snapshot_complete'] is True


def test_zone_inventory_waits_until_after_inventory_finished_packet(addon):
    addon.execute('events["incoming chunk"](0x00B); events["incoming chunk"](0x00A); events["addon command"]("scan")')
    assert decode_sent(addon)[1]['snapshot_complete'] is False
    addon.execute('sent={}; events["incoming chunk"](0x01D, string.char(0,0,255,255)); events["addon command"]("scan")')
    assert decode_sent(addon)[1]['snapshot_complete'] is False
    addon.execute('sent={}; events["incoming chunk"](0x037, string.char(0,0,0,0))')
    assert decode_sent(addon)[1]['snapshot_complete'] is True
