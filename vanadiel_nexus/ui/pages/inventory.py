"""Inventory: every item across bags and characters, with stacks rolled up and scattered items flagged."""
import csv
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QFileDialog, QMenu, QStackedWidget

from ...core.database import new_id
from ...core.inventory import ITEM_CATEGORIES, consolidate_inventory_items
from ...core.jsonfile import write_json
from ...core.wiki import build_wiki_urls
from .. import theme, widgets
from ..widgets import Column, DataTable
from .base import Page


def parse_inventory_csv(path: str) -> list:
    """Accepts 'Character,Bag,Item,Count[,Augments]' or 'Item,Count,Character,Bag[,Augments]' rows."""
    rows = []
    with open(path, "r", encoding="utf-8", errors="ignore", newline="") as f:
        for parts in csv.reader(f):
            parts = [p.strip() for p in parts]
            if len(parts) < 2 or not parts[0] or parts[0].lower() in ("name", "item", "character"):
                continue
            if parts[1].isdigit():
                rows.append({"name": parts[0], "count": int(parts[1]),
                             "character": parts[2] if len(parts) > 2 else "Imported",
                             "bag": parts[3] if len(parts) > 3 else "Imported",
                             "augments": parts[4] if len(parts) > 4 else ""})
            elif len(parts) >= 4 and parts[3].isdigit():
                rows.append({"character": parts[0], "bag": parts[1], "name": parts[2], "count": int(parts[3]),
                             "augments": parts[4] if len(parts) > 4 else ""})
    return rows


class InventoryPage(Page):
    title = "Inventory"
    key = "inventory"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.category = QComboBox()
        self.category.addItems(["All categories"] + [c if isinstance(c, str) else c[0] for c in ITEM_CATEGORIES])
        self.category.setMaximumWidth(280)
        self.character = QComboBox()
        self.character.setMaximumWidth(200)
        self.scattered = QCheckBox("Split across bags")
        self.toolbar = widgets.SearchToolbar("Search items, augments or bags…")
        self.toolbar.add(self.category, self.character, self.scattered,
                         widgets.button("Import CSV", "ghost", self._import_csv),
                         widgets.button("Refresh from game", "primary", self._refresh_from_game))

        self.table = DataTable([
            Column("Item", "name", 230, tone=lambda r: theme.WARNING if r.get("scattered") else None),
            Column("Count", "total_count", 80, Qt.AlignRight),
            Column("Category", "category", 200),
            Column("Where", "locations_str", 320),
            Column("Augments", "augments", stretch=True),
        ], sort_column=0, name="inventory")
        self.toolbar.text_changed.connect(self.table.proxy.set_needle)
        for w in (self.category, self.character):
            w.currentTextChanged.connect(self._apply_filters)
        self.scattered.toggled.connect(self._apply_filters)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)

        self.empty = widgets.EmptyState(
            "No inventory yet",
            "Log in with the Nexus addon loaded and click Refresh from game, or import a CSV export.",
            widgets.button("Refresh from game", "primary", self._refresh_from_game))
        self.stack = QStackedWidget()
        self.stack.addWidget(self.table)
        self.stack.addWidget(self.empty)
        self.count = widgets.label("", "Caption")

        self.layout_.addWidget(self.toolbar)
        self.layout_.addWidget(self.stack, 1)
        self.layout_.addLayout(widgets.hbox(self.count, None,
                                            widgets.button("Add to wishlist", on_click=self._to_wishlist),
                                            widgets.button("Open BG-Wiki ↗", "ghost", self._open_wiki)))
        ctx.inventory_changed.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        raw = self.ctx.all_inventory()
        chars = sorted({r.get("character", "") for r in raw if r.get("character")})
        current = self.character.currentText()
        self.character.blockSignals(True)
        self.character.clear()
        self.character.addItems(["All characters"] + chars)
        self.character.setCurrentText(current if current in chars else "All characters")
        self.character.blockSignals(False)
        self._raw = raw
        self._apply_filters()

    def _apply_filters(self, *_args) -> None:
        char = self.character.currentText()
        raw = self._raw if char in ("", "All characters") else [r for r in self._raw if r.get("character") == char]
        rows = consolidate_inventory_items(raw)
        cat, only_split = self.category.currentText(), self.scattered.isChecked()
        self.table.proxy.set_predicate(lambda r: (cat == "All categories" or r.get("category") == cat)
                                       and (not only_split or r.get("scattered")))
        self.table.set_rows(rows)
        self.stack.setCurrentIndex(0 if self._raw else 1)
        split = sum(1 for r in rows if r.get("scattered"))
        self.count.setText(f"{self.table.visible_count():,} items shown · {split} split across bags")

    def _refresh_from_game(self) -> None:
        if not self.ctx.bridge.connected:
            self.status("Asking the game for your bags. If nothing happens, check the Nexus addon is loaded.")
        self.ctx.bridge.request_scan()

    def _import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import inventory CSV", "", "CSV or text (*.csv *.txt)")
        if not path:
            return
        rows = parse_inventory_csv(path)
        if not rows:
            self.info("Nothing imported", "That file didn't have rows like Character, Bag, Item, Count.")
            return
        key = f"Imported: {os.path.basename(path)}"
        self.ctx.inventory_snapshot[key] = rows
        write_json(self.ctx._snapshot_path, self.ctx.inventory_snapshot)
        self.ctx.inventory_changed.emit()
        self.status(f"Imported {len(rows):,} rows from {os.path.basename(path)}.")

    def _to_wishlist(self) -> None:
        row = self.table.selected_row()
        if row is None:
            return
        self.ctx.db.data["wishlist"].append({"id": new_id("wl"), "name": row["name"], "job": self.ctx.job or "All",
                                             "slot": "", "detectedFrom": "Inventory",
                                             **self.ctx.db.data["catalog_db"].get(row["name"], {})})
        self.ctx.save_db()
        self.status(f"Added {row['name']} to your wishlist.")

    def _open_wiki(self) -> None:
        row = self.table.selected_row()
        if row is not None:
            self.ctx.open_url(build_wiki_urls(row["name"])["bgwiki"])

    def _context_menu(self, pos) -> None:
        if self.table.selected_row() is None:
            return
        menu = QMenu(self)
        menu.addAction("Add to wishlist", self._to_wishlist)
        menu.addAction("Open BG-Wiki ↗", self._open_wiki)
        menu.exec(self.table.viewport().mapToGlobal(pos))
