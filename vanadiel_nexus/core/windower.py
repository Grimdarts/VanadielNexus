"""Windower 4 folder: find it, list addons and plugins, and read or edit what scripts/init.txt autoloads."""
import os
import re
import shutil
import time

ADDON_NAME = "VanadielNexus"
_LUA_LOAD_RE = re.compile(r"^\s*lua\s+(?:load|l)\s+(\S+)\s*$", re.IGNORECASE)
_PLUGIN_LOAD_RE = re.compile(r"^\s*load\s+(\S+)\s*$", re.IGNORECASE)


def candidate_dirs(app_dir: str) -> list:
    return [
        os.path.join(os.path.dirname(app_dir), "Windower4"),
        os.path.join(app_dir, "Windower4"),
        r"C:\Windower4",
        r"C:\Program Files (x86)\Windower4",
        r"C:\Program Files\Windower4",
        os.path.join(os.path.expanduser("~"), "Games", "Windower4"),
    ]


def is_windower_dir(path: str) -> bool:
    return bool(path) and (
        os.path.isfile(os.path.join(path, "windower.exe")) or os.path.isdir(os.path.join(path, "addons"))
    )


def find_windower_dir(saved: str, app_dir: str) -> str:
    """Saved choice first, then a Windower4 folder next to the app, then common install spots. '' if none."""
    if is_windower_dir(saved):
        return saved
    for c in candidate_dirs(app_dir):
        if os.path.isfile(os.path.join(c, "windower.exe")):
            return c
    for c in candidate_dirs(app_dir):
        if is_windower_dir(c):
            return c
    return ""


def init_txt_path(windower_dir: str) -> str:
    return os.path.join(windower_dir, "scripts", "init.txt")


def _read_lines(path: str) -> list:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().splitlines()
    except OSError:
        return []


def autoloads(windower_dir: str) -> dict:
    """{'addons': {lowercase name, ...}, 'plugins': {...}} from active (uncommented) init.txt lines."""
    found = {"addons": set(), "plugins": set()}
    for line in _read_lines(init_txt_path(windower_dir)):
        s = line.strip()
        if not s or s.startswith("//"):  # Windower script comments
            continue
        m = _LUA_LOAD_RE.match(s)
        if m:
            found["addons"].add(m.group(1).lower())
            continue
        m = _PLUGIN_LOAD_RE.match(s)
        if m:
            found["plugins"].add(m.group(1).lower().removesuffix(".dll"))
    return found


def backup_file(path: str) -> str:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dst = f"{path}.{stamp}.bak"
    shutil.copy2(path, dst)
    return dst


def set_autoload(windower_dir: str, name: str, kind: str, enabled: bool) -> None:
    """Adds or removes the init.txt line that autoloads an addon ('addons') or plugin ('plugins')."""
    path = init_txt_path(windower_dir)
    lines = _read_lines(path)
    pattern = _LUA_LOAD_RE if kind == "addons" else _PLUGIN_LOAD_RE
    target = name.lower()

    def matches(line: str) -> bool:
        m = pattern.match(line.strip())
        return bool(m) and m.group(1).lower().removesuffix(".dll") == target

    currently = any(matches(line) for line in lines)
    if currently == enabled:
        return
    if os.path.exists(path):
        backup_file(path)
    if enabled:
        lines.append(f"lua load {name}" if kind == "addons" else f"load {name}")
    else:
        lines = [line for line in lines if not matches(line)]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def list_addons(windower_dir: str) -> list:
    """Installed addons: folders in addons/ that contain <name>.lua (libs excluded)."""
    root = os.path.join(windower_dir, "addons")
    loads = autoloads(windower_dir)["addons"]
    result = []
    try:
        names = sorted(os.listdir(root), key=str.lower)
    except OSError:
        return result
    for name in names:
        folder = os.path.join(root, name)
        if name.lower() == "libs" or not os.path.isdir(folder):
            continue
        main = next((f for f in os.listdir(folder) if f.lower() == f"{name.lower()}.lua"), None)
        if not main:
            continue
        result.append({
            "name": name,
            "kind": "addons",
            "folder": folder,
            "autoload": name.lower() in loads,
            "settings_file": _settings_file(folder),
        })
    return result


def _settings_file(folder: str) -> str:
    """The addon's main settings file: data/settings.xml, else the first XML file in data/."""
    data = os.path.join(folder, "data")
    try:
        xmls = sorted((f for f in os.listdir(data) if f.lower().endswith(".xml")),
                      key=lambda n: (n.lower() != "settings.xml", n.lower()))
    except OSError:
        return ""
    return os.path.join(data, xmls[0]) if xmls else ""


def list_plugins(windower_dir: str) -> list:
    root = os.path.join(windower_dir, "plugins")
    loads = autoloads(windower_dir)["plugins"]
    try:
        names = sorted((f[:-4] for f in os.listdir(root) if f.lower().endswith(".dll")), key=str.lower)
    except OSError:
        return []
    return [{"name": n, "kind": "plugins", "folder": root, "autoload": n.lower() in loads, "settings_file": ""}
            for n in names]


def write_if_changed(path: str, content: str) -> bool:
    """Writes content only when it differs. Returns True if the file was written."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            if f.read() == content:
                return False
    except OSError:
        pass
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    return True


def addon_lua_path(windower_dir: str) -> str:
    return os.path.join(windower_dir, "addons", ADDON_NAME, f"{ADDON_NAME}.lua")
