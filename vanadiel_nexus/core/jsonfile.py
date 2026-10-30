"""Crash-safe JSON files: write to a temp file, keep the previous copy as .bak, then swap in."""
import json
import os
import shutil


def read_json(path: str, *, validator=None):
    """Read primary or backup; optionally reject parsed values with validator."""
    for candidate in (path, path + ".bak"):
        try:
            with open(candidate, "r", encoding="utf-8") as f:
                data = json.load(f)
            if validator is None or validator(data):
                return data
        except (OSError, ValueError):
            continue
    return None


def write_json(path: str, data) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    if os.path.exists(path):
        shutil.copy2(path, path + ".bak")
    os.replace(tmp_path, path)
