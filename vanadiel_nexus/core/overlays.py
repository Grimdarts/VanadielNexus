"""Overlay layout: where each addon's on-screen window sits, and per-job layouts of them.

Positions are kept as the raw values each addon stores (a right-aligned text keeps its negative x,
xivbar keeps its offset from the bottom center), so layouts don't depend on the screen size.
Converting to and from the screen picture happens in to_screen() / from_screen().

    layouts.json: {character: {job | "Default": {"positions": {overlay id: [x, y]},
                                                  "shown": {addon: bool}}}}
"""
import json
import os
import re
import xml.etree.ElementTree as ET

from .addon_settings import SettingsFile
from .jsonfile import read_json, write_json
from .paths import resource_path

DEFAULT = "Default"
DEFAULT_SIZE = (200, 60)
_LUA_ENTRY_RE = re.compile(r"""\[\s*['"](\w+)['"]\s*\]\s*=\s*\{\s*x\s*=\s*(-?[\d.]+)\s*,\s*y\s*=\s*(-?[\d.]+)\s*\}""")
_LUA_XY_RE = re.compile(r"x\s*=\s*(-?[\d.]+)\s*,\s*y\s*=\s*(-?[\d.]+)")


class Overlay:
    """One movable window. addon_dir is addons/<addon>; files are relative to it."""

    def __init__(self, spec: dict, addon_dir: str, discovered: bool = False):
        self.id = spec["id"]
        self.addon = spec["addon"]
        self.label = spec.get("label", self.id)
        self.size = tuple(spec.get("size", DEFAULT_SIZE))
        self.anchor = spec.get("anchor", "auto")
        self.base_y = spec.get("base_y", 0)
        self.follows = spec.get("follows", "")
        self.follow_dy = spec.get("follow_dy", 0)
        self.preview = spec.get("preview", "")
        self.reload = spec.get("reload", "")
        self.size_from = spec.get("size_from", "")
        self.width_from = spec.get("width_from", "")
        self.addon_dir = addon_dir
        self.discovered = discovered
        self.store = _pick_store(spec["store"], addon_dir)

    def file(self, char: str, store=None) -> str:
        store = store or self.store
        default = "data/settings.xml" if store["kind"] == "xml" else ""
        return os.path.join(self.addon_dir, store.get("file", default).replace("{char}", char))

    def __repr__(self):
        return f"Overlay({self.id})"


def _pick_store(store: dict, addon_dir: str) -> dict:
    """Use the addon's own position file only when its code knows about it (patched Parse)."""
    marker = store.get("when_source_has")
    if marker and not _source_mentions(addon_dir, marker):
        return store["fallback"]
    return store


def _source_mentions(addon_dir: str, marker: str) -> bool:
    try:
        names = [n for n in os.listdir(addon_dir) if n.lower().endswith(".lua")]
    except OSError:
        return False
    for n in names:
        try:
            with open(os.path.join(addon_dir, n), encoding="utf-8", errors="ignore") as f:
                if marker in f.read():
                    return True
        except OSError:
            pass
    return False


def load_registry() -> dict:
    with open(resource_path("overlays.json"), encoding="utf-8") as f:
        return json.load(f)


def find_overlays(windower_dir: str, char: str = "") -> list:
    """Every movable window of every installed addon: known ones first, then any addon whose
    settings.xml has a <pos> with x and y (shown as a plain box)."""
    registry = load_registry()
    addons_root = os.path.join(windower_dir, "addons")
    try:
        installed = {n.lower(): n for n in os.listdir(addons_root) if os.path.isdir(os.path.join(addons_root, n))}
    except OSError:
        return []
    found, known_addons = [], set()
    for spec in registry["overlays"]:
        folder = installed.get(spec["addon"].lower())
        known_addons.add(spec["addon"].lower())
        if not folder:
            continue
        ov = Overlay(spec, os.path.join(addons_root, folder))
        if spec.get("optional") and not os.path.isfile(ov.file(char or "?")):
            continue
        found.append(ov)
    skip = known_addons | {n.lower() for n in registry["never_movable"]} | {"libs"}
    for key, folder in sorted(installed.items()):
        if key in skip:
            continue
        for path in _discover_pos_paths(os.path.join(addons_root, folder, "data", "settings.xml")):
            suffix = path.rsplit("/pos", 1)[0].replace("/", ".")
            spec = {"id": folder + (f".{suffix}" if suffix and suffix != "pos" else ""), "addon": folder,
                    "label": folder + (f": {suffix}" if suffix and suffix != "pos" else ""),
                    "store": {"kind": "xml", "path": path}}
            found.append(Overlay(spec, os.path.join(addons_root, folder), discovered=True))
    return found


def _discover_pos_paths(path: str) -> list:
    try:
        sf = SettingsFile(path)
    except (OSError, ET.ParseError):
        return []
    glob = sf.root.find("global")
    if glob is None:
        return []
    paths = []

    def walk(el, prefix):
        for child in el:
            if not isinstance(child.tag, str):
                continue
            p = f"{prefix}/{child.tag}" if prefix else child.tag
            if child.tag.lower() == "pos" and child.find("x") is not None and child.find("y") is not None:
                paths.append(p)
            else:
                walk(child, p)
    walk(glob, "")
    return paths


# --- reading ---------------------------------------------------------------------------------
def _number(text):
    try:
        v = float(str(text).strip())
    except (TypeError, ValueError):
        return None
    return int(v) if v.is_integer() else v


def _find(el, path: str):
    if el is None:
        return None
    return el if not path else el.find(path)


def _xml_sections(sf, char: str, store: dict) -> list:
    """Sections to read from, most specific first."""
    sections = []
    if store.get("section") != "global" and char:
        sections.append(sf.root.find(char.lower()))
    sections.append(sf.root.find("global"))
    return [s for s in sections if s is not None]


def _read_store(ov: Overlay, store: dict, char: str):
    path = ov.file(char, store)
    if store["kind"] == "xml":
        try:
            sf = SettingsFile(path)
        except (OSError, ET.ParseError):
            return None
        xk, yk = store.get("x", "x"), store.get("y", "y")
        for section in _xml_sections(sf, char, store):
            node = _find(section, store["path"])
            if node is not None:
                x, y = _number(node.findtext(xk)), _number(node.findtext(yk))
                if x is not None and y is not None:
                    return [x, y]
        return None
    text = _read_text(path)
    if text is None:
        return None
    if store["kind"] == "lua_table":
        for key, x, y in _LUA_ENTRY_RE.findall(text):
            if key == store["key"]:
                return [_number(x), _number(y)]
        return None
    m = _LUA_XY_RE.search(text)
    return [_number(m.group(1)), _number(m.group(2))] if m else None


def read_position(ov: Overlay, char: str):
    """[x, y] as the addon stores it now, or None if it has never been saved."""
    pos = _read_store(ov, ov.store, char)
    if pos is None and ov.store.get("fallback"):
        pos = _read_store(ov, ov.store["fallback"], char)
    return pos


def read_all(overlays: list, char: str) -> dict:
    out = {}
    for ov in overlays:
        pos = read_position(ov, char)
        if pos is not None:
            out[ov.id] = pos
    return out


def size_of(ov: Overlay, char: str) -> tuple:
    """Estimated size; a few addons store theirs (ConsoleBG extents, EnemyHUD width)."""
    w, h = ov.size
    if ov.store["kind"] == "xml" and (ov.size_from or ov.width_from):
        try:
            sf = SettingsFile(ov.file(char))
        except (OSError, ET.ParseError):
            return w, h
        for section in _xml_sections(sf, char, ov.store):
            if ov.size_from:
                node = section.find(ov.size_from)
                if node is not None and _number(node.findtext("x")) and _number(node.findtext("y")):
                    return _number(node.findtext("x")), _number(node.findtext("y"))
            if ov.width_from and _number(section.findtext(ov.width_from)):
                return _number(section.findtext(ov.width_from)), h
    return w, h


def _read_text(path: str):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return None


# --- writing ---------------------------------------------------------------------------------
def write_positions(overlays: list, char: str, positions: dict, backup: bool = True) -> list:
    """Write each overlay's [x, y]; returns the files changed. Positions equal to what's stored are skipped."""
    by_id = {ov.id: ov for ov in overlays}
    changed = []
    grouped = {}
    for oid, pos in positions.items():
        ov = by_id.get(oid)
        pos = [_number(round(float(v), 1)) for v in pos] if pos is not None else None
        if ov is None or pos is None or read_position(ov, char) == pos:
            continue
        grouped.setdefault(ov.file(char), []).append((ov, pos))
    for path, items in grouped.items():
        kind = items[0][0].store["kind"]
        if kind == "xml":
            _write_xml(path, char, items, backup)
        elif kind == "lua_table":
            _write_lua_table(path, items, overlays, char)
        else:
            _write_lua_xy(path, items[-1][1])
        changed.append(path)
    return changed


def _write_xml(path: str, char: str, items: list, backup: bool) -> None:
    sf = SettingsFile(path)
    for ov, (x, y) in items:
        store = ov.store
        section_name = "global" if store.get("section") == "global" or not char else char.lower()
        section = sf.root.find(section_name)
        if section is None:
            section = ET.SubElement(sf.root, section_name)
        node = section
        for part in [p for p in store["path"].split("/") if p]:
            child = node.find(part)
            node = child if child is not None else ET.SubElement(node, part)
        for key, value in ((store.get("x", "x"), x), (store.get("y", "y"), y)):
            leaf = node.find(key)
            if leaf is None:
                leaf = ET.SubElement(node, key)
            leaf.text = str(value)
    sf.save(backup=backup)


def _write_lua_table(path: str, items: list, overlays: list, char: str) -> None:
    entries = {}
    text = _read_text(path)
    if text:
        entries = {k: [_number(x), _number(y)] for k, x, y in _LUA_ENTRY_RE.findall(text)}
    else:
        # A new file starts from every window's current spot, so the others don't jump to defaults.
        addon = items[0][0].addon
        for ov in overlays:
            if ov.addon == addon and ov.store["kind"] == "lua_table":
                pos = read_position(ov, char)
                if pos is not None:
                    entries[ov.store["key"]] = pos
    for ov, pos in items:
        entries[ov.store["key"]] = pos
    lines = [f"    ['{k}'] = {{x = {v[0]}, y = {v[1]}}}," for k, v in entries.items()]
    _write_text(path, "return {\n" + "\n".join(lines) + "\n}\n")


def _write_lua_xy(path: str, pos: list) -> None:
    # The SMN HUD saves whole pixels (%d) and compares against what it loaded.
    _write_text(path, f"return {{x={int(round(pos[0]))}, y={int(round(pos[1]))}}}\n")


def _write_text(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


# --- screen picture ----------------------------------------------------------------------------
def _flags(ov: Overlay, char: str) -> dict:
    """texts-library flags beside the position (right/bottom alignment)."""
    if ov.store["kind"] != "xml" or ov.anchor != "auto":
        return {}
    try:
        sf = SettingsFile(ov.file(char))
    except (OSError, ET.ParseError):
        return {}
    parent = "/".join(ov.store["path"].split("/")[:-1])
    for section in sf.root.findall("global"):
        flags = _find(section, f"{parent}/flags" if parent else "flags")
        if flags is not None:
            return {c.tag.lower(): (c.text or "").strip().lower() == "true" for c in flags}
    return {}


class Screen:
    """Converts between stored positions and top-left screen pixels for one character."""

    def __init__(self, overlays: list, char: str, width: int, height: int):
        self.width, self.height = width, height
        self.by_id = {ov.id: ov for ov in overlays}
        self.sizes = {ov.id: size_of(ov, char) for ov in overlays}
        self.flags = {ov.id: _flags(ov, char) for ov in overlays}

    def to_screen(self, oid: str, raw, positions: dict) -> tuple:
        ov, (w, h) = self.by_id[oid], self.sizes[oid]
        x, y = raw
        if ov.anchor == "bottom-center":
            return self.width / 2 - w / 2 + x, self.height + ov.base_y + y
        if ov.anchor == "follow":
            leader = self.by_id.get(ov.follows)
            lraw = positions.get(ov.follows)
            if leader is None or lraw is None:
                return self.width / 2 - w / 2 + x, self.height / 2 + y
            lx, ly = self.to_screen(ov.follows, lraw, positions)
            lw = self.sizes[ov.follows][0]
            return lx + lw / 2 - w / 2 + x, ly + ov.follow_dy + y
        flags = self.flags[oid]
        sx = self.width + x - w if flags.get("right") else x
        sy = self.height + y - h if flags.get("bottom") else y
        return sx, sy

    def from_screen(self, oid: str, screen, positions: dict) -> list:
        """Inverse of to_screen: what to store so the window's top-left lands on screen."""
        zero = self.to_screen(oid, (0, 0), positions)
        return [round(screen[0] - zero[0]), round(screen[1] - zero[1])]


# --- per-job layouts --------------------------------------------------------------------------
class LayoutStore:
    """data/layouts.json. Player data: updates never touch it."""

    def __init__(self, data_dir: str):
        self.path = os.path.join(data_dir, "layouts.json")
        data = read_json(self.path)
        self.data = data if isinstance(data, dict) else {}

    def save(self) -> None:
        write_json(self.path, self.data)

    def jobs(self, char: str) -> list:
        return [j for j in self.data.get(char, {}) if j != DEFAULT]

    def has(self, char: str, job: str) -> bool:
        return job in self.data.get(char, {})

    def get(self, char: str, job: str) -> dict:
        """The layout a job uses: its own, else Default. Missing entries fall back to Default."""
        layouts = self.data.get(char, {})
        default = layouts.get(DEFAULT, {})
        own = layouts.get(job, {}) if job != DEFAULT else {}
        return {
            "positions": {**default.get("positions", {}), **own.get("positions", {})},
            "shown": {**default.get("shown", {}), **own.get("shown", {})},
        }

    def put(self, char: str, job: str, layout: dict) -> None:
        self.data.setdefault(char, {})[job or DEFAULT] = {
            "positions": {k: list(v) for k, v in layout.get("positions", {}).items()},
            "shown": dict(layout.get("shown", {})),
        }
        self.save()

    def remove(self, char: str, job: str) -> None:
        if job != DEFAULT and job in self.data.get(char, {}):
            del self.data[char][job]
            self.save()


def plan_switch(current: dict, target: dict, before_shown: dict, after_shown: dict, overlays: list) -> dict:
    """What a layout change needs: {'write': {id: pos}, 'reload': addons that move and stay shown,
    'load': newly shown, 'unload': newly hidden}. Addons whose shown state isn't recorded on both
    sides are left loaded or unloaded as they are."""
    addon_of = {ov.id: ov.addon for ov in overlays}
    write = {oid: list(pos) for oid, pos in target.items()
             if oid in addon_of and current.get(oid) != list(pos)}
    moved = {addon_of[oid] for oid in write}
    load = {a for a, on in after_shown.items() if on is True and before_shown.get(a) is False}
    unload = {a for a, on in after_shown.items() if on is False and before_shown.get(a) is True}
    reload = {a for a in moved if after_shown.get(a) is True and a not in load}
    return {"write": write, "reload": sorted(reload), "load": sorted(load), "unload": sorted(unload)}
