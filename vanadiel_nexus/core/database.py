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


def strip_display_keys(value):
    """Keys starting with '_' are computed for display (e.g. '_mat_pct') and never saved."""
    if isinstance(value, dict):
        return {k: strip_display_keys(v) for k, v in value.items() if not str(k).startswith("_")}
    if isinstance(value, list):
        return [strip_display_keys(v) for v in value]
    return value


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


def _is_database_shape(data) -> bool:
    """Reject unsafe containers before migration; missing legacy fields are OK."""
    if not isinstance(data, dict):
        return False
    for key in ("checkpoints", "rema_weapons", "wishlist"):
        if key in data and (
            not isinstance(data[key], list)
            or not all(isinstance(row, dict) for row in data[key])
        ):
            return False
    for key in ("jse_by_job", "catalog_db"):
        if key in data and not isinstance(data[key], dict):
            return False
    for key, field in (("checkpoints", "category"), ("wishlist", "slot")):
        if any(
            "job" not in row and not isinstance(row.get(field, ""), str)
            for row in data.get(key, [])
        ):
            return False
    return all(
        isinstance(rows, list) and all(isinstance(row, dict) for row in rows)
        for rows in data.get("jse_by_job", {}).values()
    )


class Database:
    def __init__(self, data_dir: str):
        self.path = os.path.join(data_dir, "ffxi_database.json")
        self.recovered_from_backup = False
        self.recovery_source = None
        self.unreadable_path = None
        self.data = self._load()

    def _load(self) -> dict:
        defaults = default_database()
        if not os.path.exists(self.path) and not os.path.exists(self.path + ".bak"):
            db = defaults
            migrate(db, defaults)
            write_json(self.path, db)
            return db

        needs_recovery = False
        db = read_json(self.path, validator=_is_database_shape)
        if db is None or not isinstance(db, dict):
            # Preserve the rejected primary before writing defaults.
            db = defaults
            needs_recovery = True
            self.recovery_source = "defaults"
        else:
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.recovered_from_backup = not _is_database_shape(json.load(f))
            except (OSError, ValueError):
                self.recovered_from_backup = True

        needs_recovery = needs_recovery or self.recovered_from_backup
        if self.recovered_from_backup:
            self.recovery_source = "backup"
        if needs_recovery and os.path.exists(self.path):
            unreadable = self.path + ".unreadable"
            suffix = 1
            while os.path.exists(unreadable):
                unreadable = self.path + f".unreadable.{suffix}"
                suffix += 1
            os.rename(self.path, unreadable)
            self.unreadable_path = unreadable

        if db.get("schema_version") is None and os.path.exists(self.path):
            v1_copy = os.path.join(os.path.dirname(self.path), "ffxi_database.v1-backup.json")
            if not os.path.exists(v1_copy):
                shutil.copy2(self.path, v1_copy)
        if migrate(db, defaults) or needs_recovery:
            write_json(self.path, db)
        return db

    def save(self) -> None:
        write_json(self.path, strip_display_keys(self.data))

    # Convenience accessors used by the pages
    def jobs_with_jse(self) -> list:
        return sorted(self.data["jse_by_job"].keys())
