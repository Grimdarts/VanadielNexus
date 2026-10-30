"""Windower 4 folder, configured startup sources, and init.txt-only startup editing."""
import os
import re
import shutil
import time
import xml.etree.ElementTree as ET

ADDON_NAME = "VanadielNexus"


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
    """Configured startup, not live loaded state; names plus relative source paths."""
    found = {"addons": set(), "plugins": set(), "sources": {"addons": {}, "plugins": {}}}

    def record(kind, name, source):
        name = name.strip().lower()
        if kind == "plugins":
            name = name.removesuffix(".dll")
        if name:
            found[kind].add(name)
            sources = found["sources"][kind].setdefault(name, [])
            if source not in sources:
                sources.append(source)

    xml_path = os.path.join(windower_dir, "settings.xml")
    try:
        root = ET.parse(xml_path).getroot()
    except (OSError, ET.ParseError):
        root = []
    for autoload in root:
        if autoload.tag.rsplit("}", 1)[-1] == "autoload":
            for entry in autoload:
                kind = {"addon": "addons", "plugin": "plugins"}.get(entry.tag.rsplit("}", 1)[-1])
                if kind:
                    record(kind, entry.text or "", "settings.xml")
    scripts_root = os.path.realpath(os.path.join(windower_dir, "scripts"))
    pending = [init_txt_path(windower_dir)]
    visited = set()
    while pending:
        path = os.path.realpath(pending.pop())
        try:
            if os.path.commonpath([scripts_root, path]) != scripts_root:
                continue
        except ValueError:  # A different drive is never inside scripts/.
            continue
        key = os.path.normcase(path)
        if key in visited:
            continue
        visited.add(key)
        source = "scripts/" + os.path.relpath(path, scripts_root).replace(os.sep, "/")
        for line in _read_lines(path):
            for _start, _end, tokens in _script_commands(line):
                load = _startup_load(tokens)
                if load:
                    record(*load, source)
                elif len(tokens) == 2 and tokens[0].lower() == "exec":
                    script = tokens[1].replace("\\", os.sep)
                    if not os.path.splitext(script)[1]:
                        script += ".txt"
                    pending.append(os.path.join(scripts_root, script))
    return found


def _script_commands(line: str) -> list:
    """Command spans and tokens; separators/comments inside quotes are literal."""
    commands = []
    start = 0
    quote = None
    i = 0
    while i <= len(line):
        end = i == len(line)
        char = "" if end else line[i]
        if not end and quote:
            if char == quote:
                quote = None
        elif not end and char in ('"', "'"):
            quote = char
        elif end or char == ";" or line[i:i + 2] == "//":
            if not quote:
                text = line[start:i]
                tokens = [next(g for g in match.groups() if g is not None)
                          for match in re.finditer(r'''"([^"]*)"|'([^']*)'|([^\s]+)''', text)]
                if tokens:
                    commands.append((start, i, tokens))
            if end or char != ";":
                break
            start = i + 1
        i += 1
    return commands


def _startup_load(tokens: list):
    lower = [t.lower() for t in tokens]
    if len(lower) == 3 and lower[0] == "lua" and lower[1] in ("load", "l"):
        return "addons", lower[2]
    if len(lower) == 2 and lower[0] == "load":
        return "plugins", lower[1].removesuffix(".dll")
    return None


def backup_file(path: str) -> str:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dst = f"{path}.{stamp}.bak"
    shutil.copy2(path, dst)
    return dst


def set_autoload(windower_dir: str, name: str, kind: str, enabled: bool) -> None:
    """Adds or removes the init.txt line that autoloads an addon ('addons') or plugin ('plugins')."""
    target = name.lower().removesuffix(".dll") if kind == "plugins" else name.lower()
    sources = autoloads(windower_dir)["sources"][kind].get(target, [])
    uncontrolled = [source for source in sources if source != "scripts/init.txt"]
    if not enabled and uncontrolled:
        raise ValueError("Startup is managed by " + ", ".join(uncontrolled) + "; only scripts/init.txt can be edited.")
    if enabled and sources:
        return
    path = init_txt_path(windower_dir)
    lines = _read_lines(path)
    currently = bool(sources)
    if currently == enabled:
        return
    if os.path.exists(path):
        backup_file(path)
    if enabled:
        lines.append(f"lua load {name}" if kind == "addons" else f"load {name}")
    else:
        updated = []
        for line in lines:
            for start, end, tokens in reversed(_script_commands(line)):
                if _startup_load(tokens) == (kind, target):
                    # Remove only this command and its following separator, not neighbours/comments.
                    end += int(line[end:end + 1] == ";")
                    line = line[:start] + line[end:]
            if line.strip():
                updated.append(line)
        lines = updated
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def list_addons(windower_dir: str) -> list:
    """Installed addons: folders in addons/ that contain <name>.lua (libs excluded)."""
    root = os.path.join(windower_dir, "addons")
    startup = autoloads(windower_dir)
    loads = startup["addons"]
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
            "autoload_sources": startup["sources"]["addons"].get(name.lower(), []),
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
    startup = autoloads(windower_dir)
    loads = startup["plugins"]
    try:
        names = sorted((f[:-4] for f in os.listdir(root) if f.lower().endswith(".dll")), key=str.lower)
    except OSError:
        return []
    return [{"name": n, "kind": "plugins", "folder": root, "autoload": n.lower() in loads, "settings_file": "",
             "autoload_sources": startup["sources"]["plugins"].get(n.lower(), [])}
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
