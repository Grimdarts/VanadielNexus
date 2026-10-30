"""The upgrade guide shown beside Gear and Wishlist tables: next step, where to go, and a materials
checklist counted live from your inventory."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QProgressBar, QScrollArea, QVBoxLayout, QWidget

from ..core import materials
from ..core.wiki import build_wiki_urls
from . import theme, widgets


class GuidePanel(QFrame):
    def __init__(self, ctx, on_edit=None):
        super().__init__()
        self.ctx = ctx
        self.on_edit = on_edit
        self.row = None
        self.setObjectName("Panel")
        self.setMinimumWidth(280)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 14, 16, 14)
        outer.setSpacing(10)

        self.title = widgets.label("Upgrade guide", "SectionTitle", wrap=True)
        self.subtitle = widgets.label("Select an item to see what it needs.", "Caption", wrap=True)
        outer.addWidget(self.title)
        outer.addWidget(self.subtitle)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setTextVisible(False)
        self.bar_label = widgets.label("", "Caption")
        outer.addWidget(self.bar)
        outer.addWidget(self.bar_label)

        self.body = QWidget()
        self.body_lay = QVBoxLayout(self.body)
        self.body_lay.setContentsMargins(0, 0, 0, 0)
        self.body_lay.setSpacing(8)
        scroll = QScrollArea()
        scroll.setWidget(self.body)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        self.body.setStyleSheet("background: transparent;")
        outer.addWidget(scroll, 1)

        self.edit_btn = widgets.button("Edit materials", on_click=lambda: self.on_edit and self.on_edit())
        self.wiki_btn = widgets.button("BG-Wiki ↗", "ghost", self._open_wiki)
        outer.addLayout(widgets.hbox(self.edit_btn, None, self.wiki_btn))
        ctx.inventory_changed.connect(lambda: self.show_row(self.row))
        self.show_row(None)

    def _clear(self) -> None:
        while self.body_lay.count():
            item = self.body_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _section(self, title: str, text: str) -> None:
        if not text:
            return
        self.body_lay.addWidget(widgets.label(title, "Caption"))
        lab = widgets.label(text, wrap=True)
        lab.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.body_lay.addWidget(lab)

    def show_row(self, row) -> None:
        self.row = row
        self._clear()
        has = row is not None
        for w in (self.bar, self.bar_label, self.edit_btn, self.wiki_btn):
            w.setVisible(has)
        if not has:
            self.title.setText("Upgrade guide")
            self.subtitle.setText("Select an item to see its next step and the materials it still needs.")
            self.body_lay.addStretch(1)
            return

        name = row.get("name") or row.get("title", "")
        self.title.setText(name)
        bits = [row.get("job"), row.get("set") or row.get("type") or row.get("category"),
                row.get("tier") or row.get("stage"), row.get("slot")]
        self.subtitle.setText(" · ".join(str(b) for b in bits if b))

        self._section("Next step", row.get("mats") or row.get("detail") or row.get("note") or "")
        self._section("Where", " · ".join(x for x in (row.get("sourceType"), row.get("zone")) if x))
        self._section("How to get it", row.get("obtainHow", ""))
        self._section("Cost / pop item", row.get("costOrPop", ""))

        counted = materials.with_counts(row.get("materials"), materials.inventory_totals(self.ctx.all_inventory()))
        if counted:
            self.body_lay.addWidget(widgets.label("Materials (counted from your bags)", "Caption"))
            for m in counted:
                line = QHBoxLayout()
                mark = widgets.label("✓" if m["done"] else "•")
                mark.setStyleSheet(f"color: {theme.SUCCESS if m['done'] else theme.FAINT}; font-weight: 600;")
                mark.setFixedWidth(14)
                name_l = widgets.label(m["name"], wrap=True)
                count = widgets.label(f"{min(m['have'], 9_999_999):,} / {m['need']:,}")
                count.setStyleSheet(f"color: {theme.SUCCESS if m['done'] else theme.TEXT};")
                line.addWidget(mark)
                line.addWidget(name_l, 1)
                line.addWidget(count)
                holder = QWidget()
                holder.setLayout(line)
                line.setContentsMargins(0, 0, 0, 0)
                self.body_lay.addWidget(holder)
            pct = materials.progress(counted)
            self.bar.setValue(int(pct))
            done = sum(1 for m in counted if m["done"])
            self.bar_label.setText(f"{pct:.0f}% of materials in your bags · {done} of {len(counted)} ready")
            self.edit_btn.setText("Edit materials")
        else:
            pct = self._row_pct(row)
            self.bar.setValue(int(pct))
            self.bar.setVisible(pct > 0)
            self.bar_label.setText("No materials listed yet. Add them and the app counts them from your bags.")
            self.edit_btn.setText("Add materials")
        self.body_lay.addStretch(1)

    @staticmethod
    def _row_pct(row) -> float:
        if row.get("target"):
            return 100.0 * (row.get("current") or 0) / row["target"]
        try:
            return float(row.get("progressPct") or 0)
        except (TypeError, ValueError):
            return 0.0

    def _open_wiki(self) -> None:
        if self.row:
            name = self.row.get("name") or self.row.get("title", "")
            self.ctx.open_url(self.row.get("wikiUrl") or build_wiki_urls(name)["bgwiki"])
