"""Wishlist: gear you want, where it drops and what it costs. Catalog names autocomplete and prefill."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QInputDialog, QMenu, QSplitter

from ...core import materials
from ...core.database import new_id
from ...core.jobs import ALL_FFXI_JOBS
from ...core.wiki import build_wiki_urls, parse_wiki_url_or_name
from .. import theme, widgets
from ..forms import Field, FormDialog
from ..guide_panel import GuidePanel
from ..widgets import Column, DataTable
from .base import Page

JOBS = [j for j in ALL_FFXI_JOBS if j != "All"]

FIELDS = [
    Field("name", "Item", required=True, placeholder="Start typing to search the catalog"),
    Field("job", "Job", "choice", JOBS + ["All"]),
    Field("slot", "Slot"),
    Field("sourceType", "Source", placeholder="e.g. Omen, Sortie, Odyssey"),
    Field("zone", "Zone"),
    Field("obtainHow", "How to get it", "long"),
    Field("costOrPop", "Cost / pop item"),
    Field("materials", "Materials / pop items", "materials"),
    Field("wikiUrl", "Wiki link"),
    Field("pinned", "Pin to top", "bool"),
]


class WishlistPage(Page):
    title = "Wishlist"
    key = "wishlist"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.job_combo = QComboBox()
        self.job_combo.addItems(["All jobs"] + JOBS)
        self.job_combo.currentTextChanged.connect(lambda t: (ctx.set_job("" if t == "All jobs" else t), self.refresh()))
        self.source_combo = QComboBox()
        self.source_combo.setMaximumWidth(220)
        self.source_combo.currentTextChanged.connect(lambda _t: self._apply_source())
        self.toolbar = widgets.SearchToolbar("Search wishlist…")
        self.toolbar.add(self.job_combo, self.source_combo,
                         widgets.button("Import from wiki link", on_click=self._import_link),
                         widgets.button("Add item", "primary", self._add))

        self.owned = {}
        self.table = DataTable([
            Column("Item", "name", 220, tone=lambda r: theme.ACCENT if r.get("pinned") else None),
            Column("Have", lambda r: "In your bags" if self.owned.get(str(r.get("name", "")).lower()) else "", 110,
                   tone=lambda _r: theme.SUCCESS),
            Column("Job", "job", 60), Column("Slot", "slot", 140), Column("Source", "sourceType", 160),
            Column("Zone", "zone", 160), Column("How to get it", "obtainHow", stretch=True),
        ], name="wishlist")
        self.toolbar.text_changed.connect(self.table.proxy.set_needle)
        self.table.row_activated.connect(lambda _r: self._edit())
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        self.table.selectionModel().selectionChanged.connect(self._show_detail)

        self.guide = GuidePanel(ctx, on_edit=self._edit_materials)
        split = QSplitter(Qt.Horizontal)
        split.addWidget(self.table)
        split.addWidget(self.guide)
        split.setStretchFactor(0, 1)
        split.setSizes([900, 320])
        split.setChildrenCollapsible(False)
        self.count = widgets.label("", "Caption")

        self.layout_.addWidget(self.toolbar)
        self.layout_.addWidget(split, 1)
        self.layout_.addLayout(widgets.hbox(
            self.count, None,
            widgets.button("Edit", on_click=self._edit),
            widgets.button("Track as goal", on_click=self._track_as_goal,
                           tooltip="Add to Gear → Goals so its materials show up with your other progress"),
            widgets.button("Open BG-Wiki ↗", "ghost", self._open_wiki),
            widgets.button("Got it!", on_click=self._obtained, tooltip="Remove from the wishlist because you have it"),
            widgets.button("Remove", "danger", self._remove),
        ))
        ctx.db_changed.connect(self.refresh)
        ctx.inventory_changed.connect(self.refresh)
        ctx.job_changed.connect(self._sync_job)
        self._sync_job(ctx.job)

    @property
    def items(self):
        return self.ctx.db.data["wishlist"]

    def _sync_job(self, job: str) -> None:
        self.job_combo.blockSignals(True)
        self.job_combo.setCurrentText(job if job in JOBS else "All jobs")
        self.job_combo.blockSignals(False)
        self.refresh()

    def refresh(self) -> None:
        job = "" if self.job_combo.currentText() == "All jobs" else self.job_combo.currentText()
        rows = [w for w in self.items if not job or w.get("job") in (job, "All", "", None)]
        self.owned = materials.inventory_totals(self.ctx.all_inventory())
        rows.sort(key=lambda w: (not w.get("pinned"), str(w.get("name", "")).lower()))
        sources = sorted({w.get("sourceType", "") for w in rows if w.get("sourceType")}, key=str.lower)
        current = self.source_combo.currentText()
        self.source_combo.blockSignals(True)
        self.source_combo.clear()
        self.source_combo.addItems(["All sources"] + sources)
        self.source_combo.setCurrentText(current if current in sources else "All sources")
        self.source_combo.blockSignals(False)
        self.table.set_rows(rows)
        self._apply_source()

    def _apply_source(self) -> None:
        src = self.source_combo.currentText()
        self.table.proxy.set_predicate(None if src in ("", "All sources") else (lambda w: w.get("sourceType") == src))
        have = sum(1 for r in self.table.model_.rows if self.owned.get(str(r.get("name", "")).lower()))
        self.count.setText(f"{self.table.visible_count()} wanted" +
                           (f" · {have} already in your bags (click Got it! to clear them)" if have else ""))
        self._show_detail()

    def _show_detail(self, *_args) -> None:
        self.guide.show_row(self.table.selected_row())

    def _edit_materials(self) -> None:
        row = self.table.selected_row()
        if row is None:
            return
        values = FormDialog.ask(self, f"Materials for {row.get('name')}",
                                [Field("materials", "Materials / pop items", "materials")], row)
        if values is not None:
            row["materials"] = values["materials"]
            self.ctx.save_db()

    def _track_as_goal(self) -> None:
        row = self.table.selected_row()
        if row is None:
            return
        goals = self.ctx.db.data["checkpoints"]
        if any(g.get("fromWishlist") == row.get("id") for g in goals):
            self.status(f"{row.get('name')} is already on your Goals.")
            return
        goals.append({"id": new_id("cp"), "job": row.get("job") or "All", "category": row.get("sourceType", ""),
                      "title": row.get("name", ""), "current": 0, "target": 1, "unit": "obtained",
                      "note": row.get("obtainHow", ""), "wikiUrl": row.get("wikiUrl", ""),
                      "materials": row.get("materials", []), "fromWishlist": row.get("id"), "pinned": True})
        self.ctx.save_db()
        self.status(f"{row.get('name')} added to Gear → Goals.")

    def _catalog_prefill(self, name: str) -> dict:
        return dict(self.ctx.db.data["catalog_db"].get(name, {}))

    def _add(self, prefill=None) -> None:
        values = FormDialog.ask(self, "Add to wishlist", FIELDS,
                                {"job": self.ctx.job or "All", **(prefill or {})},
                                completions=list(self.ctx.db.data["catalog_db"].keys()),
                                on_complete=self._catalog_prefill)
        if values:
            values["id"] = new_id("wl")
            self.items.append(values)
            self.ctx.save_db()
            self.status(f"Added {values['name']} to your wishlist.")

    def _import_link(self) -> None:
        text, ok = QInputDialog.getText(self, "Import from wiki link",
                                        "Paste a BG-Wiki, FFXIAH or FFXIclopedia link (or an item name):")
        if not ok or not text.strip():
            return
        parsed = parse_wiki_url_or_name(text.strip())
        name = " ".join(w if w.isupper() else w.capitalize() for w in parsed.get("name", "").split())
        if not name:
            self.info("Couldn't read that link", "Paste a link to an item page, or type the item's name.")
            return
        self._add({"name": name, "wikiUrl": parsed.get("wikiUrl", ""), **self._catalog_prefill(name)})

    def _edit(self) -> None:
        row = self.table.selected_row()
        if row is None:
            return
        values = FormDialog.ask(self, "Edit wishlist item", FIELDS, row)
        if values:
            row.update(values)
            self.ctx.save_db()

    def _remove_row(self, row, message: str) -> None:
        self.items.remove(row)
        self.ctx.save_db()
        self.status(message)

    def _obtained(self) -> None:
        row = self.table.selected_row()
        if row is not None:
            self._remove_row(row, f"Nice! {row.get('name')} marked as obtained.")

    def _remove(self) -> None:
        row = self.table.selected_row()
        if row is not None and self.confirm("Remove from wishlist", f"Remove {row.get('name')} from your wishlist?"):
            self._remove_row(row, f"Removed {row.get('name')}.")

    def _open_wiki(self) -> None:
        row = self.table.selected_row()
        if row is not None:
            self.ctx.open_url(row.get("wikiUrl") or build_wiki_urls(row.get("name", ""))["bgwiki"])

    def _context_menu(self, pos) -> None:
        if self.table.selected_row() is None:
            return
        menu = QMenu(self)
        menu.addAction("Edit", self._edit)
        menu.addAction("Edit materials", self._edit_materials)
        menu.addAction("Track as goal", self._track_as_goal)
        menu.addAction("Open BG-Wiki ↗", self._open_wiki)
        menu.addAction("Got it!", self._obtained)
        menu.addSeparator()
        menu.addAction("Remove", self._remove)
        menu.exec(self.table.viewport().mapToGlobal(pos))
