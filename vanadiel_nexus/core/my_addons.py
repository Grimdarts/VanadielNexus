"""My Addons: addons you write yourself, kept in your own folder and installed into Windower on demand.

    Documents/VanadielNexus/MyAddons/<Name>/<Name>.lua   your working copy (edit here)
    Windower4/addons/<Name>/                             installed copy (what the game loads)

Installing copies everything except data/, so settings an addon saved in game are never overwritten.
"""
import filecmp
import os
import re
import shutil

SKIP_DIRS = {"data", ".git", "__pycache__"}

TEMPLATE = """_addon.name = '{name}'
_addon.author = '{author}'
_addon.version = '0.1.0'
_addon.commands = {{'{command}'}}

-- Settings saved per character in data/settings.xml (editable from Vana'diel Nexus)
local config = require('config')
local defaults = {{
    enabled = true,
}}
local settings = config.load(defaults)

windower.register_event('load', function()
    windower.add_to_chat(207, '[{name}] loaded. Type //{command} help')
end)

windower.register_event('addon command', function(cmd, ...)
    cmd = cmd and cmd:lower() or 'help'
    if cmd == 'toggle' then
        settings.enabled = not settings.enabled
        settings:save()
        windower.add_to_chat(207, '[{name}] enabled = ' .. tostring(settings.enabled))
    else
        windower.add_to_chat(207, '[{name}] commands: //{command} toggle')
    end
end)
"""


def default_dir() -> str:
    return os.path.join(os.path.expanduser("~"), "Documents", "VanadielNexus", "MyAddons")


def valid_name(name: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{1,40}", name or ""))


def _files(root: str) -> list:
    """Relative paths of every file that gets installed (data/ and tool folders skipped)."""
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIRS]
        for fn in filenames:
            out.append(os.path.relpath(os.path.join(dirpath, fn), root))
    return sorted(out)


def list_my_addons(my_dir: str, windower_dir: str = "") -> list:
    """[{name, folder, installed, up_to_date}] for each folder holding <name>.lua."""
    result = []
    try:
        names = sorted(os.listdir(my_dir), key=str.lower)
    except OSError:
        return result
    for name in names:
        folder = os.path.join(my_dir, name)
        if not os.path.isfile(os.path.join(folder, f"{name}.lua")):
            continue
        target = os.path.join(windower_dir, "addons", name) if windower_dir else ""
        installed = bool(target) and os.path.isdir(target)
        result.append({"name": name, "folder": folder, "installed": installed,
                       "up_to_date": installed and is_up_to_date(folder, target)})
    return result


def is_up_to_date(src: str, dst: str) -> bool:
    files = _files(src)
    return all(os.path.isfile(os.path.join(dst, f)) and
               filecmp.cmp(os.path.join(src, f), os.path.join(dst, f), shallow=False) for f in files)


def install(src: str, windower_dir: str) -> list:
    """Copies the addon into Windower4/addons/<name>, leaving its data/ folder alone. Returns copied files."""
    name = os.path.basename(os.path.normpath(src))
    dst = os.path.join(windower_dir, "addons", name)
    copied = []
    for rel in _files(src):
        target = os.path.join(dst, rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        if not (os.path.isfile(target) and filecmp.cmp(os.path.join(src, rel), target, shallow=False)):
            shutil.copy2(os.path.join(src, rel), target)
            copied.append(rel)
    return copied


def create(my_dir: str, name: str, author: str = "") -> str:
    """Makes a new addon folder from the starter template. Returns its folder."""
    if not valid_name(name):
        raise ValueError("Use letters, numbers or _ only, starting with a letter.")
    folder = os.path.join(my_dir, name)
    if os.path.exists(folder):
        raise FileExistsError(f"{name} already exists in your My Addons folder.")
    os.makedirs(folder)
    with open(os.path.join(folder, f"{name}.lua"), "w", encoding="utf-8", newline="\n") as f:
        f.write(TEMPLATE.format(name=name, author=author or "You", command=name.lower()))
    return folder
