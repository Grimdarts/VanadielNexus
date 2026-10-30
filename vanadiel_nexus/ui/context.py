"""Shared app state handed to every page: database, settings, game bridge, Windower folder."""
import os

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtGui import QDesktopServices

from ..bridge.udp import GameBridge
from ..core import paths, windower
from ..core.database import Database
from ..core.jsonfile import read_json, write_json
from ..core.settings import Settings


class AppContext(QObject):
    db_changed = Signal()
    windower_changed = Signal(str)
    job_changed = Signal(str)
    inventory_changed = Signal()

    def __init__(self, version: str):
        super().__init__()
        self.version = version
        self.data_dir = paths.data_dir()
        self.settings = Settings(self.data_dir)
        self.db = Database(self.data_dir)
        self.bridge = GameBridge(self)
        self.windower_dir = windower.find_windower_dir(self.settings.get("windower_dir"), paths.app_dir())
        self.job = self.settings.get("job_filter") or ""
        self._snapshot_path = os.path.join(self.data_dir, "inventory_snapshot.json")
        self.inventory_snapshot = read_json(self._snapshot_path) or {}
        if not self.inventory_snapshot:
            self._seed_inventory_from_addon_files()
        self.bridge.state_received.connect(self._on_state)

    def _seed_inventory_from_addon_files(self) -> None:
        """Older addon versions saved addons/VanadielNexus/data/inventory_<name>.json; reuse them once."""
        folder = os.path.join(self.windower_dir, "addons", windower.ADDON_NAME, "data") if self.windower_dir else ""
        if not os.path.isdir(folder):
            return
        for fn in os.listdir(folder):
            if fn.startswith("inventory_") and fn.endswith(".json"):
                items = read_json(os.path.join(folder, fn))
                if isinstance(items, list) and items:
                    self.inventory_snapshot[fn[len("inventory_"):-len(".json")]] = items
        if self.inventory_snapshot:
            write_json(self._snapshot_path, self.inventory_snapshot)

    # --- persistence ------------------------------------------------------
    def save_db(self) -> None:
        self.db.save()
        self.db_changed.emit()

    def set_windower_dir(self, path: str) -> None:
        self.windower_dir = path
        self.settings.set("windower_dir", path)
        self.windower_changed.emit(path)

    def set_job(self, job: str) -> None:
        if job != self.job:
            self.job = job
            self.settings.set("job_filter", job)
            self.job_changed.emit(job)

    # --- game state -------------------------------------------------------
    def _on_state(self, state: dict) -> None:
        if state.get("main_job"):
            self.set_job(state["main_job"])
        if state.get("inventory"):
            name = state.get("player_name") or "Unknown"
            self.inventory_snapshot[name] = state["inventory"]
            write_json(self._snapshot_path, self.inventory_snapshot)
            self.inventory_changed.emit()

    def all_inventory(self) -> list:
        rows = []
        for char, items in self.inventory_snapshot.items():
            for it in items:
                rows.append({**it, "character": it.get("character") or char})
        return rows

    # --- helpers ----------------------------------------------------------
    @staticmethod
    def open_url(url: str) -> None:
        if url:
            QDesktopServices.openUrl(QUrl(url))

    @staticmethod
    def open_path(path: str) -> None:
        if path and os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
