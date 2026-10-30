"""Talks to the VanadielNexus Windower addon over localhost UDP, on Qt's event loop (no threads).

    addon --(5017: JSON {"type":"STATE_UPDATE","state":{...}})--> app
    app   --(5018: "SCAN" | "ADDON|load|name" | "CMD|<windower command>")--> addon

The addon only sends on load, job change, zone change and scan, so "connected" means
"heard from the game this session"; the app asks for a scan when it starts.
"""
import json
import secrets
import time

# Hex fragments keep Lua's byte-oriented UTF-8 splitting lossless.
MAX_DATAGRAM = 24000
MAX_SCAN_BYTES = 2 * 1024 * 1024
MAX_CHUNKS = 256
MAX_PENDING = 4
SCAN_TTL = 15.0

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QAbstractSocket, QHostAddress, QUdpSocket

LISTEN_PORT = 5017
SEND_PORT = 5018


class GameBridge(QObject):
    state_received = Signal(dict)
    connection_changed = Signal(bool)

    def __init__(self, parent=None, *, listen_port=LISTEN_PORT):
        super().__init__(parent)
        self.connected = False
        self.state = {}
        self.listening = False
        self._sock = QUdpSocket(self)
        if self._sock.bind(QHostAddress(QHostAddress.LocalHost), listen_port):
            # A complete scan arrives as a burst while the GUI may be busy.
            # Windows' default UDP buffer drops even ordinary full-bag scans.
            self._sock.setSocketOption(QAbstractSocket.SocketOption.ReceiveBufferSizeSocketOption,
                                       MAX_SCAN_BYTES * 4)
            self.listening = True
            self._sock.readyRead.connect(self._read)

    def _read(self) -> None:
        while self._sock.hasPendingDatagrams():
            datagram = self._sock.receiveDatagram()
            if not datagram.senderAddress().isLoopback():
                continue
            self._handle_datagram(bytes(datagram.data()))

    def _handle_datagram(self, data: bytes) -> None:
        if len(data) > MAX_DATAGRAM:
            return
        try:
            self._handle_payload(json.loads(data.decode("utf-8")))
        except (ValueError, UnicodeError, RecursionError):
            return

    def _accept_order(self, packet: dict) -> bool:
        """Accept only sessions that answered a fresh, targeted bridge challenge.

        Legacy messages cannot prove freshness and never publish inventory/state.
        Unknown identities do not retire the active session merely by arriving.
        """
        session, sequence = packet.get("session_id"), packet.get("update_seq")
        if (not isinstance(session, str) or not 1 <= len(session) <= 128
                or '|' in session
                or type(sequence) is not int or not 1 <= sequence <= 9007199254740991):
            return False
        active = getattr(self, "_session_id", None)
        retired = getattr(self, "_retired_sessions", set())
        if session != active:
            if session in retired or len(retired) >= 64:
                return False
            now = time.monotonic()
            challenges = getattr(self, "_challenges", {})
            self._challenges = challenges
            for key in list(challenges):
                if now - challenges[key][1] > SCAN_TTL:
                    del challenges[key]
            candidate = challenges.get(session)
            if candidate is None:
                if len(challenges) >= MAX_PENDING:
                    return False
                nonce = secrets.token_hex(16)
                challenges[session] = (nonce, now)
                self.send(f"SCAN|{nonce}|{session}")
                return False
            if packet.get("challenge") != candidate[0]:
                return False
            if active is not None:
                retired.add(active)
            self._retired_sessions = retired
            self._session_id = session
            self._session_challenge = candidate[0]
            challenges.clear()
            self._highest_update_seq = 0
            self._published_update_seq = 0
            getattr(self, "_pending", {}).clear()
        if packet.get("challenge") != self._session_challenge:
            return False
        if (sequence < self._highest_update_seq
                or sequence <= self._published_update_seq):
            return False
        self._highest_update_seq = sequence
        return True

    def _handle_payload(self, payload: dict) -> None:
        if not isinstance(payload, dict):
            return
        if payload.get("type") == "SNAPSHOT_CHUNK":
            self._chunk(payload)
        elif payload.get("type") == "STATE_UPDATE":
            state = payload.get("state")
            if isinstance(state, dict) and self._accept_order(payload):
                if self._publish(state) and payload.get("session_id") is not None:
                    self._published_update_seq = payload["update_seq"]

    def _chunk(self, packet: dict) -> None:
        now = time.monotonic()
        pending = getattr(self, "_pending", {})
        self._pending = pending
        for key in list(pending):
            if now - pending[key]["started"] > SCAN_TTL:
                del pending[key]
        scan, stamp = packet.get("scan_id"), packet.get("scan_time")
        index, total, data = packet.get("index"), packet.get("total"), packet.get("data")
        if (not isinstance(scan, str) or not 1 <= len(scan) <= 96
                or type(stamp) not in (int, float) or not 0 < stamp < float('inf')
                or type(index) is not int or type(total) is not int
                or not 1 <= total <= MAX_CHUNKS or not 0 <= index < total
                or not isinstance(data, str) or len(data) > 20000):
            return
        if (packet.get("session_id") is None
                and stamp <= getattr(self, "_last_scan_time", 0)):
            return
        try:
            fragment = bytes.fromhex(data)
        except ValueError:
            return
        if not self._accept_order(packet):
            return
        scan = (packet.get("session_id"), packet.get("update_seq"), scan)
        if scan not in pending:
            if len(pending) >= MAX_PENDING:
                del pending[min(pending, key=lambda k: pending[k]["started"])]
            pending[scan] = dict(started=now, stamp=stamp, total=total, parts={}, size=0,
                                 revision=getattr(self, "_update_revision", 0))
        entry = pending[scan]
        if entry["stamp"] != stamp or entry["total"] != total:
            del pending[scan]
            return
        previous = entry["parts"].get(index)
        if previous is not None:
            if previous != fragment:
                del pending[scan]
            return
        entry["parts"][index] = fragment
        entry["size"] += len(fragment)
        if entry["size"] > MAX_SCAN_BYTES:
            del pending[scan]
            return
        if len(entry["parts"]) != total:
            return
        del pending[scan]
        try:
            message = json.loads(b''.join(entry["parts"][i] for i in range(total)).decode('utf-8'))
        except (ValueError, UnicodeError, RecursionError):
            return
        if not isinstance(message, dict) or message.get("type") != "STATE_UPDATE":
            return
        state = message.get("state")
        if not isinstance(state, dict) or state.get("snapshot_complete") is not True:
            return
        if (message.get("session_id"), message.get("update_seq")) != scan[:2]:
            return
        if not self._accept_order(message):
            return
        if entry["revision"] != getattr(self, "_update_revision", 0):
            return
        if self._publish(state):
            if message.get("session_id") is not None:
                self._published_update_seq = message["update_seq"]
            else:
                self._last_scan_time = stamp

    def _publish(self, incoming: dict) -> bool:
        state = dict(incoming)
        name = state.get("player_name")
        if not isinstance(name, str) or not name.strip():
            return False
        complete = state.get("snapshot_complete") is True
        # Older addons have no marker: only nonempty inventories prove a scan.
        if "snapshot_complete" not in state:
            complete = bool(state.get("inventory"))
        if complete and (not isinstance(state.get("inventory"), list)
                         or any(not isinstance(row, dict) or not isinstance(row.get("name"), str)
                                or type(row.get("count")) is not int or row["count"] <= 0
                                or (row.get("character") is not None and (
                                    not isinstance(row["character"], str)
                                    or row["character"].casefold() != name.casefold()))
                                for row in state["inventory"])):
            return False
        state["snapshot_complete"] = complete
        if not complete:
            for key in ("inventory", "equipped", "materials"):
                state.pop(key, None)
                if self.state.get("player_name", "").casefold() == name.casefold() and key in self.state:
                    state[key] = self.state[key]
        self._update_revision = getattr(self, "_update_revision", 0) + 1
        self.state = state
        if not self.connected:
            self.connected = True
            self.connection_changed.emit(True)
        self.state_received.emit(state)
        return True

    def send(self, message: str) -> None:
        self._sock.writeDatagram(message.encode("utf-8"), QHostAddress(QHostAddress.LocalHost), SEND_PORT)

    def request_scan(self) -> None:
        session = getattr(self, "_session_id", None)
        if session:
            self.send(f"SCAN|{self._session_challenge}|{session}")
        else:
            self.send("SCAN")

    def addon(self, action: str, name: str) -> None:
        """action: load | unload | reload"""
        self.send(f"ADDON|{action}|{name}")

    def plugin(self, action: str, name: str) -> None:
        """action: load | unload"""
        self.send(f"CMD|{action} {name}")
