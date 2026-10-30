"""Gear: JSE armor by job, REMA weapons, and progress goals (checkpoints)."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QGridLayout, QMenu, QStackedWidget, QTabBar, QWidget

from ...core.database import new_id
from ...core.jobs import ALL_FFXI_JOBS
from ...core.wiki import build_wiki_urls
from .. import theme, widgets
from ..forms import Field, FormDialog
from ..widgets import Column, DataTable
from .base import Page

JOBS = [j for j in ALL_FFXI_JOBS if j != "All"]
JSE_SETS = ["AF", "Relic", "Empyrean"]


def _pct(row) -> float:
    try:
        return float(row.get("progressPct") or 0)
    except (TypeError, ValueError):
        return 0.0


def _goal_pct(cp) -> float:
    target = cp.get("target") or 0
    return 100.0 * (cp.get("current") or 0) / target if target else 0.0


class GearPage(Page):
    title = "Gear"
    key = "gear"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.tabs = QTabBar()
        self.tabs.setExpanding(False)
        self.tabs.setDrawBase(False)
        for name in ("JSE armor", "Weapons", "Goals"):
            self.tabs.addTab(name)
        self.tabs.currentChanged.connect(self._switch)

        self.job_combo = QComboBox()
        self.job_combo.addItems(["All jobs"] + JOBS)
        self.job_combo.currentTextChanged.connect(self._job_picked)

        self.toolbar = widgets.SearchToolbar("Search gear…")
        self.more = widgets.button("⋯ More", "ghost")
        self.more_menu = QMenu(self)
        self.more.setMenu(self.more_menu)
        self.add_btn = widgets.button("Add", "primary", self._add)
        self.toolbar.add(self.job_combo, self.more, self.add_btn)

        self.cards = QWidget()
        self.cards_grid = QGridLayout(self.cards)
        self.cards_grid.setContentsMargins(0, 0, 0, 0)
        self.cards_grid.setSpacing(12)

        gold = lambda r: theme.GOLD if r.get("ready") or str(r.get("tier", "")).endswith("+3") else None  # noqa: E731
        self.jse = DataTable([
            Column("Job", "job", 60), Column("Set", "set", 90), Column("Slot", "slot", 80),
            Column("Item", "name", 240, tone=gold), Column("Tier", "tier", 60),
            Column("Where", "location", 120), Column("Next step", "mats", stretch=True),
        ])
        self.weapons = DataTable([
            Column("Weapon", "name", 160, tone=lambda r: theme.GOLD if _pct(r) >= 100 else None),
            Column("Type", "type", 100), Column("Job", "job", 60), Column("Stage", "stage", 160),
            Column("Progress", lambda r: int(_pct(r)), 90, Qt.AlignRight),
            Column("Details", "detail", stretch=True),
        ])
        self.goals = DataTable([
            Column("Goal", "title", 280, tone=lambda r: theme.GOLD if _goal_pct(r) >= 100 else None),
            Column("Job", "job", 60), Column("Category", "category", 180),
            Column("Progress", lambda r: f"{r.get('current', 0):,} / {r.get('target', 0):,} {r.get('unit', '')}",
                   200, Qt.AlignRight),
            Column("Note", "note", stretch=True),
        ])
        self.stack = QStackedWidget()
        for t in (self.jse, self.weapons, self.goals):
            self.stack.addWidget(t)
            self.toolbar.text_changed.connect(t.proxy.set_needle)
            t.row_activated.connect(lambda _row: self._edit())
            t.setContextMenuPolicy(Qt.CustomContextMenu)
            t.customContextMenuRequested.connect(self._context_menu)

        self.count = widgets.label("", "Caption")
        self.edit_btn = widgets.button("Edit", on_click=self._edit)
        self.minus_btn = widgets.button("−1", on_click=lambda: self._step_goal(-1), tooltip="Goal progress −1")
        self.plus_btn = widgets.button("+1", on_click=lambda: self._step_goal(1), tooltip="Goal progress +1")
        self.wiki_btn = widgets.button("Open BG-Wiki ↗", "ghost", self._open_wiki)
        self.remove_btn = widgets.button("Remove", "danger", self._remove)

        self.layout_.addLayout(widgets.hbox(self.tabs, None))
        self.layout_.addWidget(self.cards)
        self.layout_.addWidget(self.toolbar)
        self.layout_.addWidget(self.stack, 1)
        self.layout_.addLayout(widgets.hbox(self.count, None, self.minus_btn, self.plus_btn, self.edit_btn,
                                            self.wiki_btn, self.remove_btn))

        ctx.db_changed.connect(self.refresh)
        ctx.job_changed.connect(self._sync_job)
        self._sync_job(ctx.job)
        self._switch(0)

    # --- data -------------------------------------------------------------
    @property
    def db(self):
        return self.ctx.db.data

    def _job(self) -> str:
        j = self.job_combo.currentText()
        return "" if j == "All jobs" else j

    def _sync_job(self, job: str) -> None:
        self.job_combo.blockSignals(True)
        self.job_combo.setCurrentText(job if job in JOBS else "All jobs")
        self.job_combo.blockSignals(False)
        self.refresh()

    def _job_picked(self, text: str) -> None:
        self.ctx.set_job("" if text == "All jobs" else text)
        self.refresh()

    def _jse_rows(self):
        rows = []
        for job, items in self.db["jse_by_job"].items():
            for it in items:
                it.setdefault("job", job)
                rows.append(it)
        return rows

    def refresh(self) -> None:
        job = self._job()
        match = lambda r: not job or r.get("job") in (job, "All", "", None)  # noqa: E731
        self.jse.set_rows([r for r in self._jse_rows() if match(r)])
        self.weapons.set_rows([r for r in self.db["rema_weapons"] if match(r)])
        self.goals.set_rows([r for r in self.db["checkpoints"] if match(r)])
        self._build_cards()
        self._update_footer()

    def _build_cards(self) -> None:
        while self.cards_grid.count():
            self.cards_grid.takeAt(0).widget().deleteLater()
        idx, job = self.tabs.currentIndex(), self._job()
        cards = []
        if idx == 0 and job:
            for s in JSE_SETS:
                items = [r for r in self.jse.model_.rows if str(r.get("set", "")).lower().startswith(s.lower()[:3])]
                if items:
                    done = sum(1 for r in items if str(r.get("tier", "")).endswith("+3"))
                    nxt = next((r["name"] for r in items if not str(r.get("tier", "")).endswith("+3")), "Complete")
                    cards.append(widgets.ProgressCard(f"{job} {s}", f"{done} / {len(items)} at +3",
                                                      100 * done / len(items), f"Next: {nxt}"))
        elif idx == 1:
            for w in sorted(self.weapons.model_.rows, key=_pct)[:3]:
                cards.append(widgets.ProgressCard(f"{w.get('name')} · {w.get('type', '')}", w.get("stage", ""),
                                                  _pct(w), w.get("detail", "")))
        elif idx == 2:
            pinned = [c for c in self.goals.model_.rows if c.get("pinned")] or self.goals.model_.rows
            for c in pinned[:3]:
                cards.append(widgets.ProgressCard(c.get("title", ""), f"{c.get('current', 0):,} / {c.get('target', 0):,}",
                                                  _goal_pct(c), c.get("unit", "")))
        for i, card in enumerate(cards):
            self.cards_grid.addWidget(card, 0, i)
        self.cards.setVisible(bool(cards))

    def _switch(self, idx: int) -> None:
        self.stack.setCurrentIndex(idx)
        self.add_btn.setText(["Add JSE piece", "Add weapon", "Add goal"][idx])
        self.minus_btn.setVisible(idx == 2)
        self.plus_btn.setVisible(idx == 2)
        self.more_menu.clear()
        self.more_menu.addAction("Open FFXIAH ↗", lambda: self._open_wiki("ffxiah"))
        self.more_menu.addAction("Open FFXIclopedia ↗", lambda: self._open_wiki("ffxiclopedia"))
        self._build_cards()
        self._update_footer()

    def _table(self) -> DataTable:
        return self.stack.currentWidget()

    def _update_footer(self) -> None:
        t = self._table()
        self.count.setText(f"{t.visible_count()} shown")

    # --- actions ----------------------------------------------------------
    def _fields(self):
        job = self._job() or "BLU"
        idx = self.tabs.currentIndex()
        if idx == 0:
            return [Field("job", "Job", "choice", JOBS), Field("set", "Set", "combo", JSE_SETS),
                    Field("slot", "Slot", "combo", ["Head", "Body", "Hands", "Legs", "Feet"]),
                    Field("name", "Item", required=True), Field("tier", "Tier", "combo", ["NQ", "+1", "+2", "+3"]),
                    Field("location", "Where it is"), Field("mats", "Next step", "long")], {"job": job}
        if idx == 1:
            return [Field("name", "Weapon", required=True),
                    Field("type", "Type", "combo", ["Relic", "Mythic", "Empyrean", "Aeonic", "Ergon", "Prime"]),
                    Field("job", "Job", "choice", JOBS + ["All"]), Field("stage", "Stage"),
                    Field("progressPct", "Progress %", "int"), Field("detail", "Details", "long"),
                    Field("rp", "Notes")], {"job": job}
        return [Field("title", "Goal", required=True), Field("job", "Job", "choice", JOBS + ["All"]),
                Field("category", "Category"), Field("current", "Current", "int"), Field("target", "Target", "int"),
                Field("unit", "Unit", placeholder="e.g. Alexandrite"), Field("note", "Note", "long"),
                Field("wikiUrl", "Wiki link"), Field("pinned", "Pin to top", "bool")], {"job": job, "target": 1}

    def _collection(self, idx=None):
        return [None, self.db["rema_weapons"], self.db["checkpoints"]][self.tabs.currentIndex() if idx is None else idx]

    def _add(self) -> None:
        fields, defaults = self._fields()
        values = FormDialog.ask(self, self.add_btn.text(), fields, defaults)
        if not values:
            return
        idx = self.tabs.currentIndex()
        if idx == 0:
            values["id"] = new_id("jse")
            self.db["jse_by_job"].setdefault(values["job"], []).append(values)
        else:
            values["id"] = new_id(["", "rema", "cp"][idx])
            self._collection().append(values)
        self.ctx.save_db()
        self.status(f"Added {values.get('name') or values.get('title')}.")

    def _edit(self) -> None:
        row = self._table().selected_row()
        if row is None:
            return
        fields, _ = self._fields()
        values = FormDialog.ask(self, "Edit", fields, row)
        if not values:
            return
        if self.tabs.currentIndex() == 0 and values.get("job") != row.get("job"):
            self.db["jse_by_job"].get(row.get("job"), []).remove(row)
            self.db["jse_by_job"].setdefault(values["job"], []).append(row)
        row.update(values)
        self.ctx.save_db()

    def _remove(self) -> None:
        row = self._table().selected_row()
        if row is None:
            return
        name = row.get("name") or row.get("title") or "this item"
        if not self.confirm("Remove from tracker", f"Remove {name} from your tracker?"):
            return
        if self.tabs.currentIndex() == 0:
            self.db["jse_by_job"].get(row.get("job"), []).remove(row)
        else:
            self._collection().remove(row)
        self.ctx.save_db()
        self.status(f"Removed {name}.")

    def _step_goal(self, delta: int) -> None:
        row = self.goals.selected_row()
        if row is None:
            return
        row["current"] = max(0, int(row.get("current") or 0) + delta)
        self.ctx.save_db()

    def _open_wiki(self, provider: str = "bgwiki") -> None:
        row = self._table().selected_row()
        if row is None:
            return
        name = row.get("name") or row.get("title", "")
        url = row.get("wikiUrl") if provider == "bgwiki" and row.get("wikiUrl") else build_wiki_urls(name).get(provider)
        self.ctx.open_url(url)

    def _context_menu(self, pos) -> None:
        if self._table().selected_row() is None:
            return
        menu = QMenu(self)
        menu.addAction("Edit", self._edit)
        menu.addAction("Open BG-Wiki ↗", self._open_wiki)
        menu.addSeparator()
        menu.addAction("Remove", self._remove)
        menu.exec(self._table().viewport().mapToGlobal(pos))
