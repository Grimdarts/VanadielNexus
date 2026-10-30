"""Read and safely save Windower addon settings files (addons/<name>/data/*.xml).

Windower's config library writes files like:
    <?xml version="1.1" ?>
    <settings>
        <global> ...nested keys... </global>
        <Charactername> ...per-character overrides... </Charactername>
    </settings>

Python's XML parser only accepts version 1.0 declarations, so the declaration is set aside on load and
written back unchanged on save. Windower also writes list entries as numeric tags (<1>consolas</1>),
which strict XML forbids; those are renamed on load and restored on save. Comments and element order
are preserved; every save keeps a .bak.
"""
import os
import re
import xml.etree.ElementTree as ET

from .windower import backup_file

_DECL_RE = re.compile(r"^\s*<\?xml[^>]*\?>\s*", re.IGNORECASE)
_NUMERIC_TAG_RE = re.compile(r"<(/?)(\d[\w.-]*)(\s*/?)>")
_NUMERIC_PREFIX = "n__"
_RESTORE_RE = re.compile(r"<(/?)" + _NUMERIC_PREFIX + r"(\d[\w.-]*)(\s*/?)>")


def display_tag(tag: str) -> str:
    return tag[len(_NUMERIC_PREFIX):] if tag.startswith(_NUMERIC_PREFIX) else tag


class SettingsFile:
    def __init__(self, path: str):
        self.path = path
        with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
            text = f.read()
        # Windower writes ' and " as entities; keep doing that so files stay byte-for-byte familiar
        self._escape = [(c, e) for c, e in (("'", "&apos;"), ('"', "&quot;")) if e in text]
        m = _DECL_RE.match(text)
        self.declaration = m.group(0).strip() if m else ""
        body = text[m.end():] if m else text
        body = _NUMERIC_TAG_RE.sub(lambda mm: f"<{mm.group(1)}{_NUMERIC_PREFIX}{mm.group(2)}{mm.group(3)}>", body)
        parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
        self.root = ET.fromstring(body, parser=parser)

    def sections(self) -> list:
        """Top-level sections: 'global' first, then character names (or whatever the addon uses)."""
        names = [c.tag for c in self.root if isinstance(c.tag, str)]
        return sorted(names, key=lambda n: (n.lower() != "global", n.lower()))

    def save(self) -> str:
        """Writes the file after a timestamped backup. Returns the backup path."""
        backup = backup_file(self.path)
        ET.indent(self.root, space="    ")
        body = ET.tostring(self.root, encoding="unicode")
        body = _RESTORE_RE.sub(lambda mm: f"<{mm.group(1)}{mm.group(2)}{mm.group(3)}>", body)
        for char, entity in self._escape:
            body = body.replace(char, entity)
        with open(self.path, "w", encoding="utf-8", newline="\n") as f:
            if self.declaration:
                f.write(self.declaration + "\n")
            f.write(body + "\n")
        return backup


def is_leaf(el) -> bool:
    return not any(isinstance(c.tag, str) for c in el)


def value_kind(text: str) -> str:
    """'bool', 'int', 'float' or 'text', so the editor can show the right control."""
    t = (text or "").strip()
    if t.lower() in ("true", "false"):
        return "bool"
    if re.fullmatch(r"-?\d+", t):
        return "int"
    if re.fullmatch(r"-?\d+\.\d+", t):
        return "float"
    return "text"


def is_color_group(el) -> bool:
    """Windower colors are groups with red/green/blue (and usually alpha) children."""
    tags = {c.tag.lower() for c in el if isinstance(c.tag, str)}
    return {"red", "green", "blue"} <= tags and tags <= {"red", "green", "blue", "alpha"}


def settings_files(addon_folder: str) -> list:
    """All XML settings files an addon keeps in data/, settings.xml first."""
    data = os.path.join(addon_folder, "data")
    try:
        names = [f for f in os.listdir(data) if f.lower().endswith(".xml")]
    except OSError:
        return []
    names.sort(key=lambda n: (n.lower() != "settings.xml", n.lower()))
    return [os.path.join(data, n) for n in names]
