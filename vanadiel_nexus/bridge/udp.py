"""Talks to the VanadielNexus Windower addon over localhost UDP, on Qt's event loop (no threads).

    addon --(5017: JSON {"type":"STATE_UPDATE","state":{...}})--> app
    app   --(5018: "SCAN" | "ADDON|load|name" | "CMD|<windower command>")--> addon

The addon only sends on load, job change, zone change and scan, so "connected" means
"heard from the game this session"; the app asks for a scan when it starts.
"""
import json

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QHostAddress, QUdpSocket

LISTEN_PORT = 5017
SEND_PORT = 5018


class GameBridge(QObject):
    state_received = Signal(dict)
    connection_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.connected = False
        self.state = {}
        self.listening = False
        self._sock = QUdpSocket(self)
        if self._sock.bind(QHostAddress(QHostAddress.LocalHost), LISTEN_PORT):
            self.listening = True
            self._sock.readyRead.connect(self._read)

    def _read(self) -> None:
        while self._sock.hasPendingDatagrams():
            datagram = self._sock.receiveDatagram()
            try:
                payload = json.loads(bytes(datagram.data()).decode("utf-8", errors="ignore"))
            except ValueError:
                continue
            if isinstance(payload, dict) and payload.get("type") == "STATE_UPDATE":
                state = payload.get("state") or {}
                # Zone-change updates carry no bags: keep the last inventory we saw
                for key in ("inventory", "equipped", "materials"):
                    if not state.get(key) and self.state.get(key):
                        state[key] = self.state[key]
                self.state = state
                if not self.connected:
                    self.connected = True
                    self.connection_changed.emit(True)
                self.state_received.emit(state)

    def send(self, message: str) -> None:
        self._sock.writeDatagram(message.encode("utf-8"), QHostAddress(QHostAddress.LocalHost), SEND_PORT)

    def request_scan(self) -> None:
        self.send("SCAN")

    def addon(self, action: str, name: str) -> None:
        """action: load | unload | reload"""
        self.send(f"ADDON|{action}|{name}")

    def plugin(self, action: str, name: str) -> None:
        """action: load | unload"""
        self.send(f"CMD|{action} {name}")
