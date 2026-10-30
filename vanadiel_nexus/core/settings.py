"""App settings (data/settings.json): Windower folder, window placement, text size, last page."""
import os

from .jsonfile import read_json, write_json

DEFAULTS = {
    "windower_dir": "",
    "window_geometry": "",   # Qt saveGeometry() as hex
    "text_scale": 1.0,       # 0.9 - 1.3
    "last_page": "gear",
    "job_filter": "",
    "setup_dismissed": False,
}


class Settings:
    def __init__(self, data_dir: str):
        self.path = os.path.join(data_dir, "settings.json")
        stored = read_json(self.path)
        self._values = dict(DEFAULTS)
        if isinstance(stored, dict):
            self._values.update(stored)

    def get(self, key: str):
        return self._values.get(key, DEFAULTS.get(key))

    def set(self, key: str, value) -> None:
        if self._values.get(key) == value:
            return
        self._values[key] = value
        write_json(self.path, self._values)
