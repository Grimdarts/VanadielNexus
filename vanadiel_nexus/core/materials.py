"""Upgrade materials: what an item still needs, counted against everything in your bags.

A tracked item (JSE piece, weapon, goal or wishlist entry) may carry
    "materials": [{"name": "Pluton", "need": 1500}, ...]
which the player types one per line, e.g. "Pluton x1500", "1500 Pluton" or "Pluton: 1500".
"""
import re

_LINE_PATTERNS = (
    re.compile(r"^(?P<name>.+?)\s*[x×:]\s*(?P<need>[\d,]+)\s*$", re.IGNORECASE),  # Pluton x1500 / Pluton: 1500
    re.compile(r"^(?P<need>[\d,]+)\s*[x×]?\s+(?P<name>.+?)\s*$", re.IGNORECASE),  # 1500 Pluton / 3x Voidhead
)


def parse_materials(text: str) -> list:
    """One material per line. A line without a number counts as needing 1."""
    result = []
    for raw in (text or "").splitlines():
        line = raw.strip(" \t-•*")
        if not line:
            continue
        for pat in _LINE_PATTERNS:
            m = pat.match(line)
            if m:
                result.append({"name": m.group("name").strip(), "need": int(m.group("need").replace(",", ""))})
                break
        else:
            result.append({"name": line, "need": 1})
    return result


def format_materials(materials: list) -> str:
    return "\n".join(f"{m['name']} x{m['need']}" for m in materials or [])


def inventory_totals(inventory_rows: list) -> dict:
    """{lowercase item name: total count across every character and bag}."""
    totals = {}
    for it in inventory_rows or []:
        key = str(it.get("name", "")).strip().lower()
        if key:
            totals[key] = totals.get(key, 0) + int(it.get("count") or 0)
    return totals


def with_counts(materials: list, totals: dict) -> list:
    """Adds 'have' (capped display stays honest: the real count) and 'done' to each material."""
    rows = []
    for m in materials or []:
        have = totals.get(str(m.get("name", "")).strip().lower(), 0)
        need = int(m.get("need") or 0)
        rows.append({**m, "have": have, "done": have >= need})
    return rows


def progress(counted: list) -> float:
    """Percent of all required units you already hold (each material capped at its need)."""
    need = sum(int(m["need"]) for m in counted)
    if not need:
        return 0.0
    return 100.0 * sum(min(int(m["have"]), int(m["need"])) for m in counted) / need


def goal_current_from_inventory(goal: dict, totals: dict):
    """Goals that count an item (unit = item name, autoCount on) take 'current' from your bags."""
    if not goal.get("autoCount"):
        return None
    return totals.get(str(goal.get("unit", "")).strip().lower(), 0)
