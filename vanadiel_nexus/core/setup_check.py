"""The Setup checklist shown from the top bar: what a new player still needs to do."""
import os

from . import windower
from .paths import resource_path


def bundled_addon_lua() -> str:
    with open(resource_path("VanadielNexus.lua"), "r", encoding="utf-8") as f:
        return f.read()


def run_checks(windower_dir: str) -> list:
    """Each step: {id, label, detail, ok, fix}. 'fix' names the action the UI offers."""
    found = windower.is_windower_dir(windower_dir)
    steps = [{
        "id": "windower",
        "label": "Windower folder found",
        "detail": windower_dir if found else "Choose the folder that contains windower.exe.",
        "ok": found,
        "fix": "choose_windower",
    }]

    lua_path = windower.addon_lua_path(windower_dir) if found else ""
    installed = found and os.path.isfile(lua_path)
    current = False
    if installed:
        with open(lua_path, "r", encoding="utf-8", errors="ignore") as f:
            current = f.read() == bundled_addon_lua()
    steps.append({
        "id": "addon",
        "label": "Nexus addon installed and up to date",
        "detail": ("Installed." if current else "An older version is installed.") if installed
        else "Lets the app see your character, job and inventory.",
        "ok": current,
        "fix": "install_addon",
    })

    autoload = found and windower.ADDON_NAME.lower() in windower.autoloads(windower_dir)["addons"]
    steps.append({
        "id": "autoload",
        "label": "Addon starts with the game",
        "detail": "Adds 'lua load VanadielNexus' to scripts/init.txt (a backup is kept)." if not autoload
        else "Listed in scripts/init.txt.",
        "ok": autoload,
        "fix": "enable_autoload",
    })
    return steps


def install_addon(windower_dir: str) -> bool:
    return windower.write_if_changed(windower.addon_lua_path(windower_dir), bundled_addon_lua())


def summary(steps: list) -> tuple:
    done = sum(1 for s in steps if s["ok"])
    return done, len(steps)
