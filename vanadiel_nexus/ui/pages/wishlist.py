"""Wishlist: gear you want, where it drops and what it costs. Catalog names autocomplete and prefill."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QInputDialog, QMenu

from ...core.database import new_id
from ...core.jobs import ALL_FFXI_JOBS
from ...core.wiki import build_wiki_urls, parse_wiki_url_or_name
from .. import theme, widgets
from ..forms import Field, FormDialog
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
        self.toolbar = widgets.SearchToolbar("Search wishlist…")
        self.toolbar.add(self.job_combo,
                         widgets.button("Import from wiki link", on_click=self._import_link),
                         widgets.button("Add item", "primary", self._add))

        self.table = DataTable([
            Column("Item", "name", 220, tone=lambda r: theme.ACCENT if r.get("pinned") else None),
            Column("Job", "job", 60), Column("Slot", "slot", 140), Column("Source", "sourceType", 160),
            Column("Zone", "zone", 160), Column("How to get it", "obtainHow", stretch=True),
        ], name="wishlist")
        self.toolbar.text_changed.connect(self.table.proxy.set_needle)
        self.table.row_activated.connect(lambda _r: self._edit())
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        self.table.selectionModel().selectionChanged.connect(self._show_detail)

        self.detail = widgets.label("", wrap=True)
        self.detail.setObjectName("Caption")
        self.detail.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.count = widgets.label("", "Caption")

        self.layout_.addWidget(self.toolbar)
        self.layout_.addWidget(self.table, 1)
        self.layout_.addWidget(self.detail)
        self.layout_.addLayout(widgets.hbox(
            self.count, None,
            widgets.button("Edit", on_click=self._edit),
            widgets.button("Open BG-Wiki ↗", "ghost", self._open_wiki),
            widgets.button("Got it!", on_click=self._obtained, tooltip="Remove from the wishlist because you have it"),
            widgets.button("Remove", "danger", self._remove),
        ))
        ctx.db_changed.connect(self.refresh)
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
        rows.sort(key=lambda w: (not w.get("pinned"), str(w.get("name", "")).lower()))
        self.table.set_rows(rows)
        self.count.setText(f"{len(rows)} wanted")
        self._show_detail()

    def _show_detail(self, *_args) -> None:
        row = self.table.selected_row()
        if not row:
            self.detail.setText("Select an item to see how to get it.")
            return
        bits = [row.get("obtainHow"), f"Cost: {row['costOrPop']}" if row.get("costOrPop") else ""]
        self.detail.setText(f"{row.get('name', '')}: " + "  ".join(b for b in bits if b))

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
        menu.addAction("Open BG-Wiki ↗", self._open_wiki)
        menu.addAction("Got it!", self._obtained)
        menu.addSeparator()
        menu.addAction("Remove", self._remove)
        menu.exec(self.table.viewport().mapToGlobal(pos))
