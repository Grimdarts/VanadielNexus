"""Short descriptions for addons and plugins.

Order of preference: our own short description for well-known addons, then the addon's
_addon.description, then the first descriptive sentence of its README. Nothing is invented for
addons we don't recognise: an empty string means "no description available".
"""
import json
import os
import re

from .paths import resource_path

_SKIP_START = re.compile(r"^(\d+[.)]|commands?\b|author\b|usage\b|version\b|change\b|help\b|[-*!\[<=|`])",
                         re.IGNORECASE)
_KNOWN = None


def _known() -> dict:
    global _KNOWN
    if _KNOWN is None:
        try:
            with open(resource_path("addon_descriptions.json"), "r", encoding="utf-8") as f:
                _KNOWN = json.load(f)
        except (OSError, ValueError):
            _KNOWN = {}
    return _KNOWN


def _from_lua(folder: str, name: str) -> str:
    main = os.path.join(folder, f"{name}.lua")
    try:
        with open(main, "r", encoding="utf-8", errors="ignore") as f:
            head = f.read(8000)
    except OSError:
        return ""
    m = re.search(r"_addon\.description\s*=\s*(['\"])(.+?)\1", head)
    return m.group(2).strip() if m else ""


def _from_readme(folder: str, name: str) -> str:
    try:
        readme = next((f for f in os.listdir(folder) if f.lower().startswith("readme")), None)
    except OSError:
        return ""
    if not readme:
        return ""
    try:
        with open(os.path.join(folder, readme), "r", encoding="utf-8", errors="ignore") as f:
            for raw in f:
                line = raw.strip().lstrip("#").strip()
                if len(line) < 25 or _SKIP_START.match(line) or line.lower().startswith(name.lower()):
                    continue
                sentence = re.split(r"(?<=[.!])\s", line, maxsplit=1)[0]
                return sentence if len(sentence) <= 140 else sentence[:137].rstrip() + "…"
    except OSError:
        pass
    return ""


def describe(name: str, kind: str = "addons", folder: str = "") -> str:
    key = name.lower() if kind == "addons" else f"plugin:{name.lower()}"
    known = _known().get(key)
    if known:
        return known
    if kind != "addons" or not folder:
        return ""
    return _from_lua(folder, name) or _from_readme(folder, name)
