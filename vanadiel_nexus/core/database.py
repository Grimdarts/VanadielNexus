"""The player's tracker database (data/ffxi_database.json).

Layout (unchanged from v1, plus a schema_version field):
    checkpoints   list of progress goals   {id, job, category, title, current, target, unit, note, wikiUrl, pinned}
    jse_by_job    {JOB: [ {id, set, slot, name, tier, location, mats, ready} ]}
    rema_weapons  list  {id, name, type, job, stage, progressPct, detail, rp}
    wishlist      list  {id, job, name, slot, sourceType, zone, obtainHow, costOrPop, detectedFrom, wikiUrl, pinned}
    catalog_db    {item name: {slot, sourceType, zone, obtainHow, costOrPop, wikiUrl}}
"""
import json
import os
import re
import shutil
import uuid

from .jsonfile import read_json, write_json
from .paths import resource_path

SCHEMA_VERSION = 2
_JOB_RE = re.compile(r"\b(WAR|MNK|WHM|BLM|RDM|THF|PLD|DRK|BST|BRD|RNG|SAM|NIN|DRG|SMN|BLU|COR|PUP|DNC|SCH|GEO|RUN)\b")


def default_database() -> dict:
    with open(resource_path("default_database.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def migrate(db: dict, defaults: dict) -> bool:
    """Brings an older database up to SCHEMA_VERSION in place. Returns True if anything changed."""
    changed = False
    for key in ("checkpoints", "rema_weapons", "wishlist"):
        if not isinstance(db.get(key), list):
            db[key] = []
            changed = True
    for key in ("jse_by_job", "catalog_db"):
        if not isinstance(db.get(key), dict):
            db[key] = {}
            changed = True

    # Jobs added to the defaults after a database was created
    for job, rows in defaults.get("jse_by_job", {}).items():
        if job not in db["jse_by_job"]:
            db["jse_by_job"][job] = rows
            changed = True
    for cp in db["checkpoints"]:
        if "job" not in cp:
            m = re.search(r"\(([A-Z]{3})\)", cp.get("category", ""))
            cp["job"] = m.group(1) if m else "All"
            changed = True
    for wl in db["wishlist"]:
        if "job" not in wl:
            m = _JOB_RE.search(wl.get("slot", ""))
            wl["job"] = m.group(1) if m else "All"
            changed = True

    if db.get("schema_version") != SCHEMA_VERSION:
        db["schema_version"] = SCHEMA_VERSION
        changed = True
    return changed


class Database:
    def __init__(self, data_dir: str):
        self.path = os.path.join(data_dir, "ffxi_database.json")
        self.recovered_from_backup = False
        self.data = self._load()

    def _load(self) -> dict:
        defaults = default_database()
        if not os.path.exists(self.path) and not os.path.exists(self.path + ".bak"):
            db = defaults
            migrate(db, defaults)
            write_json(self.path, db)
            return db

        db = read_json(self.path)
        if db is None or not isinstance(db, dict):
            # Never fall back to demo data over a player's file: keep the broken file for recovery
            if os.path.exists(self.path):
                shutil.copy2(self.path, self.path + ".unreadable")
            db = defaults
            self.recovered_from_backup = True
        else:
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    json.load(f)
            except (OSError, ValueError):
                self.recovered_from_backup = True

        if db.get("schema_version") is None and os.path.exists(self.path):
            v1_copy = os.path.join(os.path.dirname(self.path), "ffxi_database.v1-backup.json")
            if not os.path.exists(v1_copy):
                shutil.copy2(self.path, v1_copy)
        if migrate(db, defaults) or self.recovered_from_backup:
            write_json(self.path, db)
        return db

    def save(self) -> None:
        write_json(self.path, self.data)

    # Convenience accessors used by the pages
    def jobs_with_jse(self) -> list:
        return sorted(self.data["jse_by_job"].keys())
