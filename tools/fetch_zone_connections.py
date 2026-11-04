#!/usr/bin/env python3
"""Fetch every zone's "Connected Zone" table from BG-Wiki into tools/world_map/zone_connections.json.

    py -3 tools/fetch_zone_connections.py [--refresh]

The world map's walking connections come from this file instead of being typed by hand, so they can be
re-checked against the wiki at any time. Raw page text is cached in the system temp folder; --refresh
ignores the cache. Requests are spaced out so the wiki isn't hammered.
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import seed_world_map as seed  # noqa: E402  (zone list + exclusions live there)

API = "https://www.bg-wiki.com/api.php"
USER_AGENT = "VanadielNexus-map-seed/1.0 (github.com/Grimdarts/VanadielNexus)"
CACHE_DIR = os.path.join(tempfile.gettempdir(), "vanadielnexus-bgwiki-cache")
OUT_PATH = os.path.join(ROOT, "tools", "world_map", "zone_connections.json")
DELAY_SECONDS = 0.6

# Windower name -> BG-Wiki page title, where they differ.
PAGE_OVERRIDES: dict[str, str] = {
    "Riverne - Site #A01": "Riverne - Site A01",
    "Riverne - Site #B01": "Riverne - Site B01",
}


def wiki_title(windower_name: str) -> str:
    if windower_name in PAGE_OVERRIDES:
        return PAGE_OVERRIDES[windower_name]
    # Windower writes past-era zones as "Batallia Downs [S]"; BG-Wiki uses "Batallia Downs (S)".
    name = re.sub(r"\s*\[S\]$", " (S)", windower_name)
    return name


def fetch_wikitext(title: str, refresh: bool) -> tuple[str, str] | None:
    """Returns (resolved_title, wikitext), or None if the page doesn't exist."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache = os.path.join(CACHE_DIR, re.sub(r"[^\w.-]+", "_", title) + ".json")
    if not refresh and os.path.exists(cache):
        with open(cache, encoding="utf-8") as f:
            cached = json.load(f)
        return (cached["title"], cached["wikitext"]) if cached.get("wikitext") is not None else None
    query = urllib.parse.urlencode({
        "action": "parse", "page": title, "prop": "wikitext",
        "redirects": "1", "format": "json", "formatversion": "2",
    })
    req = urllib.request.Request(f"{API}?{query}", headers={"User-Agent": USER_AGENT})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.load(resp)
            break
        except OSError:
            if attempt == 3:
                raise
            time.sleep(2 ** (attempt + 1))
    time.sleep(DELAY_SECONDS)
    parse = payload.get("parse")
    result = {"title": parse["title"], "wikitext": parse["wikitext"]} if parse else {"title": title, "wikitext": None}
    with open(cache, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)
    return (result["title"], result["wikitext"]) if parse else None


# Two template generations are in use on BG-Wiki:
#   {{Zone Geography Row   |Geography.Zone=… |Geography.Entrance_Position=(here) |Geography.Exit_Position=(there)}}
#   {{Zone Geography Row 2 |Connected Zone=… |Current Zone Exit Position=(here) |Exit or Entrance Only=…
#                          |Connected Zone Entrance Position=(there)}}
ROW_RE = re.compile(r"\{\{\s*Zone Geography Row( 2)?\s*\n(.*?)\}\}", re.S)
TRAVEL_RE = re.compile(r"\{\{\s*Zone Quick Travel Row\s*\n(.*?)\}\}", re.S)
PARAM_RE = re.compile(r"\|\s*([^=|\n]+?)\s*=([^\n]*)")
DESC_RE = re.compile(r"\|\s*Description\.(Region|Continent|Zone_Type|Timeline|Requires)\s*=\s*([^\n|]*)")
LINK_RE = re.compile(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]")


def clean(value: str) -> str:
    value = LINK_RE.sub(r"\1", value)
    value = re.sub(r"<br\s*/?>", " ", value)
    value = re.sub(r"<[^>]+>", "", value)
    value = re.sub(r"\{\{[^{}]*\}\}", "", value)
    return " ".join(value.split())


def _params(body: str) -> dict[str, str]:
    return {k.strip(): clean(v) for k, v in PARAM_RE.findall(body)}


def parse_page(wikitext: str) -> dict:
    rows = []
    for m in ROW_RE.finditer(wikitext):
        p = _params(m.group(2))
        if m.group(1):  # "Row 2"
            row = {"zone": p.get("Connected Zone", ""), "here": p.get("Current Zone Exit Position", ""),
                   "there": p.get("Connected Zone Entrance Position", ""), "only": p.get("Exit or Entrance Only", "")}
        else:
            row = {"zone": p.get("Geography.Zone", ""), "here": p.get("Geography.Entrance_Position", ""),
                   "there": p.get("Geography.Exit_Position", ""),
                   "only": p.get("Geography.Exit_or_Entrance_Only", "") or p.get("Geography.Notes", "")}
            extra = {k: v for k, v in p.items() if k.startswith("Geography.") and v and k not in (
                "Geography.Zone", "Geography.Entrance_Position", "Geography.Exit_Position",
                "Geography.Entrance_Map", "Geography.Exit_Map")}
            if extra:
                row["extra"] = extra
        if row["zone"]:
            rows.append(row)
    travel = []
    for m in TRAVEL_RE.finditer(wikitext):
        p = _params(m.group(1))
        if p.get("Travel Option"):
            travel.append({"option": p["Travel Option"], "position": p.get("Zone Position", "")})
    desc = {k: clean(v) for k, v in DESC_RE.findall(wikitext)}
    return {"connections": rows, "quick_travel": travel, "description": desc}


ZONE_LINK_RE = re.compile(r"^\*\s*\[\[([^\]|]+)(?:\|[^\]]*)?\]\]", re.M)


def parse_survival_guides(wikitext: str) -> list[str]:
    section = wikitext[wikitext.find("== Survival Guide Locations"):]
    return [m.group(1).strip() for m in ZONE_LINK_RE.finditer(section)]


def parse_home_points(wikitext: str) -> dict[str, list[int]]:
    section = wikitext[wikitext.find("== Home Point Locations"):]
    found: dict[str, list[int]] = {}
    current = None
    for line in section.splitlines():
        m = re.match(r"^\*\s*\[\[([^\]|]+)(?:\|[^\]]*)?\]\]", line)
        if m and not line.startswith("**"):
            current = m.group(1).strip()
            found.setdefault(current, [])
            continue
        m = re.match(r"^\*\*\s*Home Point #(\d+)", line)
        if m and current:
            found[current].append(int(m.group(1)))
    return {k: v for k, v in found.items() if v}


def main() -> int:
    refresh = "--refresh" in sys.argv
    survival_guides = parse_survival_guides(fetch_wikitext("Survival Guide", refresh)[1])
    home_points = parse_home_points(fetch_wikitext("Home Point", refresh)[1])
    zones = seed.parse_windower_zones(seed.WINDOWER_ZONES_PATH)
    out: dict[str, dict] = {}
    missing: list[str] = []
    for zid in sorted(zones):
        if zid in seed.EXCLUDED_ZONE_IDS:
            continue
        name = zones[zid]["en"]
        title = wiki_title(name)
        got = fetch_wikitext(title, refresh)
        if got is None:
            missing.append(f"{zid} {name} (tried '{title}')")
            continue
        resolved, text = got
        parsed = parse_page(text)
        out[str(zid)] = {"name": name, "wiki_title": resolved, **parsed}
        print(f"{zid:>4} {name:<34} {len(parsed['connections'])} connections", flush=True)
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump({"source": "BG-Wiki zone pages, 'Survival Guide' and 'Home Point'",
                   "fetched": date.today().isoformat(), "survival_guides": survival_guides,
                   "home_points": home_points, "zones": out, "missing_pages": missing},
                  f, indent=1, ensure_ascii=False)
    print(f"\n{len(out)} zones written to {OUT_PATH}; {len(missing)} pages not found:")
    for m in missing:
        print("  ", m)
    return 0


if __name__ == "__main__":
    sys.exit(main())
