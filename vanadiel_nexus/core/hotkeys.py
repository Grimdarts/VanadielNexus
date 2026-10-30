"""Hotkeys: scan FFXI / Windower / GearSwap / addon binds and flag conflicts that can actually happen in game."""
import os
import re


def normalize_hotkey_string(raw_key: str) -> str:
    """
    Converts Windower keybind strings (e.g. '^f10', '!f10', '@f9', '~f11',
    '%f8', 'Ctrl-F10', 'Alt+F1') into a canonical uppercase format such as:
    'CTRL+F10', 'ALT+F10', 'WIN+F9', 'SHIFT+F11', 'F8', 'F11', 'F12'.
    """
    k = (raw_key or "").strip()
    if not k:
        return ""
    # Strip Windower game-only / chat prefixes (% or $) for conflict comparison
    k_clean = k.lstrip("%$")

    mods = []
    # Check symbolic prefixes (^ = Ctrl, ! = Alt, @ = Win, ~ = Shift)
    while k_clean and k_clean[0] in "^!@~":
        ch = k_clean[0]
        if ch == "^" and "CTRL" not in mods:
            mods.append("CTRL")
        elif ch == "!" and "ALT" not in mods:
            mods.append("ALT")
        elif ch == "@" and "WIN" not in mods:
            mods.append("WIN")
        elif ch == "~" and "SHIFT" not in mods:
            mods.append("SHIFT")
        k_clean = k_clean[1:]

    # Also handle explicit word prefixes like Ctrl-F10 or Alt+F10
    parts = re.split(r"[-+]", k_clean)
    base_key = parts[-1].upper() if parts else k_clean.upper()
    for p in parts[:-1]:
        pu = p.strip().upper()
        if pu in ("CTRL", "CONTROL") and "CTRL" not in mods:
            mods.append("CTRL")
        elif pu == "ALT" and "ALT" not in mods:
            mods.append("ALT")
        elif pu in ("SHIFT", "SHFT") and "SHIFT" not in mods:
            mods.append("SHIFT")
        elif pu in ("WIN", "WINDOWS", "SUPER") and "WIN" not in mods:
            mods.append("WIN")

    alias_map = {
        "SYSRQ": "PRINTSCREEN",
        "PRINT": "PRINTSCREEN",
        "PRTSC": "PRINTSCREEN",
        "INS": "INSERT",
        "DEL": "DELETE",
        "ESC": "ESCAPE",
    }
    base_key = alias_map.get(base_key, base_key)

    ordered_mods = [m for m in ("CTRL", "ALT", "SHIFT", "WIN") if m in mods]
    if ordered_mods:
        return "+".join(ordered_mods + [base_key])
    return base_key


def to_windower_bind_key(norm_key: str) -> str:
    """Converts canonical 'CTRL+F10' back to Windower bind syntax '^f10'."""
    parts = [p.strip().upper() for p in norm_key.split("+") if p.strip()]
    if not parts:
        return ""
    base = parts[-1].lower()
    prefix = ""
    if "CTRL" in parts[:-1]:
        prefix += "^"
    if "ALT" in parts[:-1]:
        prefix += "!"
    if "WIN" in parts[:-1]:
        prefix += "@"
    if "SHIFT" in parts[:-1]:
        prefix += "~"
    return prefix + base


def scan_all_hotkeys_and_conflicts(windower_dir: str) -> list:
    """
    Scans and aggregates hotkeys across all 4 FFXI / Windower layers:
    1. FFXI Base Game Default Hotkeys
    2. Windower scripts/init.txt
    3. GearSwap Lua files (Mote-Include & job .lua files)
    4. Windower Addons & Plugins (settings.xml, binder.xml, etc.)
    """
    entries = []
    init_path = os.path.join(windower_dir, "scripts", "init.txt")
    settings_path = os.path.join(windower_dir, "settings.xml")
    gs_data_dir = os.path.join(windower_dir, "addons", "GearSwap", "data")
    gs_libs_dir = os.path.join(windower_dir, "addons", "GearSwap", "libs")

    # 1. FFXI Base Game Hotkeys (focusing on F1-F12 & common Ctrl/Alt binds)
    base_game_binds = [
        ("F1", "Target Party Member 1 (Self)", "FFXI Base Game", "In-Game Menu -> Config -> Misc. 2 / Keyboard", "Built-in client key. Overridden if bound without '%' in Windower."),
        ("F2", "Target Party Member 2", "FFXI Base Game", "In-Game Menu -> Config -> Misc. 2 / Keyboard", "Built-in client party target key."),
        ("F3", "Target Party Member 3", "FFXI Base Game", "In-Game Menu -> Config -> Misc. 2 / Keyboard", "Built-in client party target key."),
        ("F4", "Target Party Member 4", "FFXI Base Game", "In-Game Menu -> Config -> Misc. 2 / Keyboard", "Built-in client party target key."),
        ("F5", "Target Party Member 5", "FFXI Base Game", "In-Game Menu -> Config -> Misc. 2 / Keyboard", "Built-in client party target key."),
        ("F6", "Target Party Member 6", "FFXI Base Game", "In-Game Menu -> Config -> Misc. 2 / Keyboard", "Built-in client party target key."),
        ("F7", "Target Self", "FFXI Base Game", "In-Game Menu -> Config -> Misc. 2 / Keyboard", "Built-in client self-target key."),
        ("F8", "Target Nearest NPC / Monster", "FFXI Base Game", "In-Game Menu -> Config -> Misc. 2 / Keyboard", "If your GearSwap Lua binds F8, Windower intercepts F8 before FFXI's Target Nearest NPC unless unbound or rebound."),
        ("F9", "Target Nearest PC (Player)", "FFXI Base Game", "In-Game Menu -> Config -> Misc. 2 / Keyboard", "Standard Mote GearSwap binds F9 to cycle OffenseMode, overriding FFXI's Target Nearest PC."),
        ("F10", "Target Alliance / Window Shortcut", "FFXI Base Game", "In-Game Menu -> Config -> Misc. 2 / Keyboard", "Used by GearSwap (PhysicalDefenseMode / Custom Job Binds). Removed from Vana'diel Nexus!"),
        ("CTRL+1..0", "Macro Palette Bar (Ctrl Row)", "FFXI Base Game", "In-Game Macro Bar (DelayMeNot plugin active)", "Opens & triggers Ctrl Macro slots 1 through 0."),
        ("ALT+1..0", "Macro Palette Bar (Alt Row)", "FFXI Base Game", "In-Game Macro Bar (DelayMeNot plugin active)", "Opens & triggers Alt Macro slots 1 through 0."),
    ]
    for k, act, sys_type, cfg_loc, fix_guide in base_game_binds:
        entries.append({
            "raw_key": k,
            "norm_key": normalize_hotkey_string(k),
            "system": sys_type,
            "source_file": cfg_loc,
            "line_num": 0,
            "action": act,
            "how_to_fix": fix_guide,
            "editable_file": False
        })

    # 2. Windower scripts/init.txt (only what the player's file actually binds)
    if os.path.isfile(init_path):
        try:
            with open(init_path, "r", encoding="utf-8", errors="ignore") as f:
                for idx, line in enumerate(f, start=1):
                    s = line.strip()
                    if not s or s.startswith("//") or s.startswith(";"):
                        continue
                    m = re.match(r"^bind\s+(\S+)\s+(.+)$", s, re.IGNORECASE)
                    if m:
                        rk, cmd = m.group(1), m.group(2).strip()
                        nk = normalize_hotkey_string(rk)
                        entries.append({
                            "raw_key": rk,
                            "norm_key": nk,
                            "system": "Windower init.txt",
                            "source_file": init_path,
                            "line_num": idx,
                            "action": cmd,
                            "how_to_fix": (
                                f"Edit {init_path} (Line {idx}) to change or comment out 'bind {rk} {cmd}', "
                                f"then type '//unbind {rk}' in the Windower console."
                            ),
                            "editable_file": True
                        })
        except Exception:
            pass

    # 3. GearSwap Lua hotkeys (GearSwap/data and libs)
    lua_search_paths = []
    if os.path.isdir(gs_data_dir):
        for root_d, _dirs, files in os.walk(gs_data_dir):
            for fn in files:
                if fn.lower().endswith(".lua"):
                    lua_search_paths.append(os.path.join(root_d, fn))
    if os.path.isdir(gs_libs_dir):
        for fn in os.listdir(gs_libs_dir):
            if fn.lower().endswith(".lua"):
                lua_search_paths.append(os.path.join(gs_libs_dir, fn))

    bind_regex = re.compile(r"bind\s+([~!@^%$a-zA-Z0-9_-]+)\s+([^'\"\r\n]+)", re.IGNORECASE)
    for lpath in lua_search_paths:
        lua_scope = classify_gearswap_lua(lpath, gs_data_dir)
        try:
            with open(lpath, "r", encoding="utf-8", errors="ignore") as f:
                for idx, line in enumerate(f, start=1):
                    s = line.strip()
                    if s.startswith("--"):
                        continue
                    for m in bind_regex.finditer(s):
                        rk = m.group(1).strip()
                        cmd = m.group(2).strip()
                        nk = normalize_hotkey_string(rk)
                        entries.append({
                            "raw_key": rk,
                            "norm_key": nk,
                            "system": f"GearSwap Lua ({os.path.basename(lpath)})",
                            "source_file": lpath,
                            "line_num": idx,
                            "action": cmd,
                            "how_to_fix": (
                                f"Defined in {lpath} (Line {idx}). Edit 'send_command(\"bind {rk} ...\")' in that .lua file, "
                                f"then run '//gs r' in game."
                            ),
                            "editable_file": True,
                            "job": lua_scope["job"],
                            "inactive": lua_scope["scope"] == "inactive",
                            "gearswap": True,
                        })
        except Exception:
            pass

    # 4. Windower console key, read from settings.xml
    console_key, console_line = "Insert", 0
    if os.path.isfile(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8", errors="ignore") as f:
                for idx, line in enumerate(f, start=1):
                    m = re.search(r"<consolekey>\s*([^<]+?)\s*</consolekey>", line, re.IGNORECASE)
                    if m:
                        console_key, console_line = m.group(1), idx
                        break
        except OSError:
            pass
    entries.append({
        "raw_key": console_key,
        "norm_key": normalize_hotkey_string(console_key),
        "system": "Windower Core (settings.xml)",
        "source_file": settings_path,
        "line_num": console_line,
        "action": f"Toggle Windower console (<consolekey>{console_key}</consolekey>)",
        "how_to_fix": f"Configured in {settings_path} under <consolekey>. Close FFXI before editing settings.xml.",
        "editable_file": os.path.isfile(settings_path)
    })

    compute_hotkey_conflicts(entries)

    # Sort so conflicts appear at the top, files GearSwap never loads at the bottom, then F1-F12 order
    def _sort_key(item):
        c_rank = 0 if item["conflict"] else (2 if item.get("inactive") else 1)
        return (c_rank, item["norm_key"], item["system"])

    entries.sort(key=_sort_key)
    return entries


_JOB_TOKEN_RE = re.compile(
    r"(?:^|[_\-\s])(WAR|MNK|WHM|BLM|RDM|THF|PLD|DRK|BST|BRD|RNG|SAM|NIN|DRG|SMN|BLU|COR|PUP|DNC|SCH|GEO|RUN)"
    r"\d*(?=[_\-\s.]|$)",
    re.IGNORECASE,
)


def classify_gearswap_lua(lua_path: str, gs_data_dir: str) -> dict:
    """
    Works out when GearSwap would actually load a .lua file:
      - job:   only while that job is active (e.g. Name_BLU.lua, Name-SMN-sets.lua, BLU.lua)
      - shared: loaded alongside every job (user-globals.lua, libs/Mote-*.lua, include libs)
      - inactive: in a subfolder GearSwap never searches (backups, exports, "Other LUAs", ...)
    GearSwap only looks in data/, data/<character>/ and data/common/.
    """
    try:
        rel = os.path.relpath(lua_path, gs_data_dir)
    except ValueError:
        rel = os.path.basename(lua_path)
    parts = rel.replace("\\", "/").split("/")
    fname = parts[-1]
    if rel.startswith("..") or len(parts) == 1:
        loadable = True  # data/ root or libs/
    elif len(parts) == 2:
        folder = parts[0]
        folder_dir = os.path.join(gs_data_dir, folder)
        try:
            siblings = [f for f in os.listdir(folder_dir) if f.lower().endswith(".lua")]
        except OSError:
            siblings = [fname]
        try:
            root_files = [f for f in os.listdir(gs_data_dir) if f.lower().endswith(".lua")]
        except OSError:
            root_files = []
        # A character folder is named after a character: its files (or the root's) start with "<Name>_"/"<Name>-"
        name_re = re.compile(rf"^{re.escape(folder)}[_\-]", re.IGNORECASE)
        loadable = folder.lower() == "common" or any(name_re.match(s) for s in siblings + root_files)
    else:
        loadable = False

    if not loadable:
        return {"scope": "inactive", "job": ""}
    jobs = _JOB_TOKEN_RE.findall(os.path.splitext(fname)[0])
    if jobs:
        return {"scope": "job", "job": jobs[-1].upper()}
    return {"scope": "shared", "job": ""}


def _can_load_together(a: dict, b: dict) -> bool:
    if a.get("inactive") or b.get("inactive"):
        return False
    # Two different job files are never loaded at the same time
    if a.get("job") and b.get("job") and a["job"] != b["job"]:
        return False
    # A job file rebinding a shared GearSwap default (e.g. Mote-Globals F9) is a deliberate override
    if a.get("gearswap") and b.get("gearswap") and bool(a.get("job")) != bool(b.get("job")):
        return False
    return True


def compute_hotkey_conflicts(entries: list):
    """Flags a bind only when another system binds the same key AND both can be active at once."""
    by_norm = {}
    for e in entries:
        by_norm.setdefault(e["norm_key"], []).append(e)

    for e in entries:
        rivals = [
            g for g in by_norm.get(e["norm_key"], [])
            if g is not e and g["system"] != e["system"] and _can_load_together(e, g)
        ]
        if rivals:
            e["conflict"] = True
            e["conflict_count"] = len(rivals) + 1
            e["status_label"] = f"⚠️ CONFLICT ({len(rivals) + 1} systems)"
            e["conflict_summary"] = "  ||  ".join(f"{g['system']} -> '{g['action']}'" for g in rivals)
        else:
            e["conflict"] = False
            e["conflict_count"] = 1
            e["status_label"] = "💤 Not Loaded (subfolder)" if e.get("inactive") else "✅ OK (No Conflict)"
            e["conflict_summary"] = "None"

def _edit_bind_line(entry: dict, transform) -> bool:
    """Applies transform(line) -> new line to the entry's source line, after a timestamped backup."""
    from .windower import backup_file

    path, line_num = entry.get("source_file", ""), int(entry.get("line_num") or 0)
    if not entry.get("editable_file") or not os.path.isfile(path) or line_num < 1:
        return False
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    if line_num > len(lines):
        return False
    new_line = transform(lines[line_num - 1])
    if new_line == lines[line_num - 1]:
        return False
    backup_file(path)
    lines[line_num - 1] = new_line
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.writelines(lines)
    return True


def disable_bind(entry: dict) -> bool:
    """Comments out the line that creates this bind ('--' in .lua, '//' in Windower scripts)."""
    marker = "-- " if entry.get("source_file", "").lower().endswith(".lua") else "// "
    return _edit_bind_line(entry, lambda line: marker + "[disabled by Vana'diel Nexus] " + line)


def rebind(entry: dict, new_key: str) -> bool:
    """Moves the bind to new_key (any format normalize_hotkey_string accepts) in its source file."""
    wkey = to_windower_bind_key(normalize_hotkey_string(new_key))
    pattern = re.compile(r"(bind\s+)" + re.escape(entry.get("raw_key", "")) + r"(?=\s)", re.IGNORECASE)
    return _edit_bind_line(entry, lambda line: pattern.sub(lambda m: m.group(1) + wkey, line, count=1))
