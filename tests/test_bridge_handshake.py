"""Session activation must prove a response to a fresh bridge challenge."""
import json
import pytest
from vanadiel_nexus.bridge.udp import GameBridge

@pytest.fixture
def bridge(qapp, monkeypatch):
    b = GameBridge(listen_port=0)
    sent = []
    monkeypatch.setattr(b, 'send', sent.append)
    b.sent = sent
    return b

def partial(session, seq, name, challenge=None):
    return dict(type='STATE_UPDATE', session_id=session, update_seq=seq,
                challenge=challenge, state=dict(player_name=name, snapshot_complete=False))

def activate(b, session, name):
    b._handle_payload(partial(session, 1, name))
    command = b.sent[-1].split('|')
    assert command[0] == 'SCAN' and command[2] == session
    b._handle_payload(partial(session, 2, name, command[1]))
    assert b.state['player_name'] == name
    return command[1]

def test_unseen_delayed_session_cannot_retire_current(bridge):
    nonce = activate(bridge, 'new-load', 'Bob')
    bridge._handle_payload(partial('unseen-old-load', 1, 'Alice'))
    assert bridge.state['player_name'] == 'Bob'
    bridge._handle_payload(partial('new-load', 3, 'Bob', nonce))
    assert bridge.state['player_name'] == 'Bob'
    assert bridge._session_id == 'new-load'

def test_old_challenge_cannot_activate_reloaded_session(bridge):
    nonce = activate(bridge, 'first', 'Alice')
    bridge._handle_payload(partial('reload', 1, 'Bob', nonce))
    assert bridge.state['player_name'] == 'Alice'
    command = bridge.sent[-1].split('|')
    bridge._handle_payload(partial('reload', 2, 'Bob', command[1]))
    assert bridge.state['player_name'] == 'Bob'
    bridge._handle_payload(partial('first', 9, 'Alice', nonce))
    assert bridge.state['player_name'] == 'Bob'

def test_legacy_snapshot_cannot_change_current_or_saved_state(bridge):
    nonce = activate(bridge, 'current', 'Bob')
    legacy = dict(type='STATE_UPDATE', state=dict(player_name='Alice', inventory=[], snapshot_complete=True))
    bridge._handle_payload(legacy)
    raw = json.dumps(legacy).encode().hex()
    bridge._handle_payload(dict(type='SNAPSHOT_CHUNK', scan_id='old', scan_time=1,
                                index=0, total=1, data=raw))
    assert bridge.state['player_name'] == 'Bob'

def test_legacy_first_contact_is_not_authoritative(bridge):
    bridge._handle_payload(dict(type='STATE_UPDATE',state=dict(player_name='Alice',inventory=[dict(name='Ore',count=1)])))
    assert not bridge.state

def test_request_scan_targets_active_session_with_current_challenge(bridge):
    nonce = activate(bridge, 'current', 'Bob')
    bridge.request_scan()
    assert bridge.sent[-1] == f'SCAN|{nonce}|current'
