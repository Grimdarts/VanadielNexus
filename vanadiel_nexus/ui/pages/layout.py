"""Layout: arrange every addon window on a picture of the game screen, one layout per job.

    ┌ Job [SMN ▾] [Copy from ▾] ☑ Switch with my job ............ [Show in game] [Save] ┐
    │ ┌────────── game screen (drag boxes) ──────────┐  Overlays (☑ shown on this job)  │
    │ │  ┌Parse┐            ┌EnemyHUD┐               │  X [   ] Y [   ]                 │
    │ └──────────────────────────────────────────────┘                                 │
"""
from PySide6.QtCore import QRectF, Qt, Signal, QObject
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QGraphicsItem, QGraphicsRectItem, QGraphicsScene, QGraphicsSimpleTextItem,
    QGraphicsView, QListWidget, QListWidgetItem, QMessageBox, QSpinBox, QSplitter, QVBoxLayout, QWidget,
)

from ...core import overlays
from ...core.jobs import ALL_FFXI_JOBS
from .. import theme, widgets
from .base import Page

JOBS = [j for j in ALL_FFXI_JOBS if j != "All"]
SNAP = 8


class _Relay(QObject):
    moved = Signal(str)


class OverlayBox(QGraphicsRectItem):
    """A draggable stand-in for one addon window; its scene position is the window's top-left."""

    def __init__(self, oid: str, label: str, w: float, h: float, relay: _Relay):
        super().__init__(0, 0, w, h)
        self.oid, self.relay = oid, relay
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable
                      | QGraphicsItem.ItemSendsGeometryChanges)
        self.text = QGraphicsSimpleTextItem(label, self)
        self.text.setBrush(QBrush(QColor(theme.TEXT)))
        font = QFont(theme.UI_FONT)
        font.setPixelSize(12)
        self.text.setFont(font)
        self.text.setPos(4, 2)
        # The screen picture is scaled down to fit; keep the names readable at any zoom.
        self.text.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.shown = True
        self.restyle()

    def restyle(self) -> None:
        color = QColor(theme.ACCENT if self.isSelected() else theme.MUTED)
        fill = QColor(theme.ACCENT)
        fill.setAlpha(60 if self.isSelected() else 34)
        if not self.shown:
            color, fill = QColor(theme.FAINT), QColor(0, 0, 0, 0)
        pen = QPen(color, 2 if self.isSelected() else 1)
        pen.setCosmetic(True)
        pen.setStyle(Qt.SolidLine if self.shown else Qt.DashLine)
        self.setPen(pen)
        self.setBrush(QBrush(fill))
        self.text.setBrush(QBrush(QColor(theme.TEXT if self.shown else theme.FAINT)))

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedHasChanged:
            self.restyle()
        elif change == QGraphicsItem.ItemPositionHasChanged:
            self.relay.moved.emit(self.oid)
        return super().itemChange(change, value)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.scene().snap(self)


class ScreenScene(QGraphicsScene):
    def __init__(self):
        super().__init__()
        self.boxes = {}
        self.background = None
        self.screen_rect = None

    def set_screen(self, w: int, h: int, pixmap_path: str = "") -> None:
        for item in list(self.items()):
            if not isinstance(item, (OverlayBox, QGraphicsSimpleTextItem)):
                self.removeItem(item)
        self.setSceneRect(QRectF(0, 0, w, h))
        pix = QPixmap(pixmap_path) if pixmap_path else QPixmap()
        if not pix.isNull():
            self.background = self.addPixmap(pix.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation))
            self.background.setOpacity(0.55)
        else:
            self.background = None
        frame = QPen(QColor(theme.BORDER), 2)
        frame.setCosmetic(True)
        self.screen_rect = self.addRect(0, 0, w, h, frame, QBrush(QColor("#0E1528") if pix.isNull() else Qt.NoBrush))
        for z, item in enumerate((self.background, self.screen_rect)):
            if item is not None:
                item.setZValue(-10 + z)
        center = QPen(QColor(theme.BORDER), 1, Qt.DotLine)
        center.setCosmetic(True)
        self.addLine(w / 2, 0, w / 2, h, center).setZValue(-5)
        self.addLine(0, h / 2, w, h / 2, center).setZValue(-5)

    def snap(self, box: OverlayBox) -> None:
        """Pull a dropped box onto a nearby screen edge, the center lines or another box's edge."""
        r = box.sceneBoundingRect()
        w, h = self.sceneRect().width(), self.sceneRect().height()
        xs, ys = [0, w, w / 2], [0, h, h / 2]
        for other in self.boxes.values():
            if other is not box:
                o = other.sceneBoundingRect()
                xs += [o.left(), o.right()]
                ys += [o.top(), o.bottom()]
        dx = min(((t - e) for t in xs for e in (r.left(), r.right(), r.center().x())), key=abs, default=0)
        dy = min(((t - e) for t in ys for e in (r.top(), r.bottom(), r.center().y())), key=abs, default=0)
        box.moveBy(dx if abs(dx) <= SNAP else 0, dy if abs(dy) <= SNAP else 0)


class ScreenView(QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setBackgroundBrush(QBrush(QColor(theme.BG)))
        self.setFrameShape(QGraphicsView.NoFrame)
        self.setMinimumSize(420, 260)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)

    def keyPressEvent(self, event):
        step = 10 if event.modifiers() & Qt.ShiftModifier else 1
        delta = {Qt.Key_Left: (-step, 0), Qt.Key_Right: (step, 0), Qt.Key_Up: (0, -step), Qt.Key_Down: (0, step)}
        if event.key() in delta and self.scene().selectedItems():
            for item in self.scene().selectedItems():
                item.moveBy(*delta[event.key()])
            return
        super().keyPressEvent(event)


class LayoutPage(Page):
    title = "Layout"
    key = "layout"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.mgr = ctx.layouts
        self.job = ""
        self.layout = {"positions": {}, "shown": {}}
        self.dirty = False
        self._syncing = False

        self.job_combo = QComboBox()
        self.job_combo.addItems([overlays.DEFAULT] + JOBS)
        self.job_combo.currentTextChanged.connect(self._job_picked)
        self.copy_combo = QComboBox()
        self.copy_combo.setToolTip("Start this job's layout from another one")
        self.copy_combo.activated.connect(self._copy_from)
        self.switch = QCheckBox("Switch with my job")
        self.switch.setToolTip("When you change job in game, your windows move to that job's layout.")
        self.switch.setChecked(ctx.settings.get("layout_switch_with_job") is not False)
        self.switch.toggled.connect(lambda on: ctx.settings.set("layout_switch_with_job", on))
        self.uses_default = widgets.label("", "Caption")
        self.save_btn = widgets.button("Save", "primary", self.save)
        self.game_btn = widgets.button("Arrange in game", on_click=self.arrange_in_game,
                                       tooltip="Shows every window as a frame in FFXI to drag there (same as //vn layout)")
        self.layout_.addLayout(widgets.hbox(
            widgets.label("Job", "Caption"), self.job_combo, self.copy_combo, self.switch, self.uses_default,
            None, self.game_btn, self.save_btn))

        self.relay = _Relay()
        self.relay.moved.connect(self._box_moved)
        self.scene = ScreenScene()
        self.scene.selectionChanged.connect(self._selection_changed)
        self.view = ScreenView(self.scene)

        side = QWidget()
        sv = QVBoxLayout(side)
        sv.setContentsMargins(0, 0, 0, 0)
        sv.addWidget(widgets.label("Windows · tick = shown on this job", "Caption"))
        self.list = QListWidget()
        self.list.itemChanged.connect(self._shown_toggled)
        self.list.currentItemChanged.connect(self._list_selected)
        sv.addWidget(self.list, 1)
        self.x_spin, self.y_spin = QSpinBox(), QSpinBox()
        for s in (self.x_spin, self.y_spin):
            s.setRange(-8000, 8000)
            s.valueChanged.connect(self._spin_changed)
        sv.addLayout(widgets.hbox(widgets.label("X"), self.x_spin, widgets.label("Y"), self.y_spin))
        self.size_note = widgets.label("", "Caption", wrap=True)
        sv.addWidget(self.size_note)
        sv.addLayout(widgets.hbox(
            widgets.button("Capture current", on_click=self.capture,
                           tooltip="Use where your windows are right now (e.g. after dragging them in game)"),
            widgets.button("Background…", on_click=self.pick_background,
                           tooltip="Show one of your FFXI screenshots behind the boxes"), None))
        self.reset_btn = widgets.button("Use Default for this job", "ghost", self.use_default)
        sv.addWidget(self.reset_btn)

        split = QSplitter(Qt.Horizontal)
        split.addWidget(self.view)
        split.addWidget(side)
        split.setStretchFactor(0, 1)
        split.setSizes([760, 300])
        self.layout_.addWidget(split, 1)
        self.hint = widgets.label("Drag a box, or select it and use the arrow keys (Shift = 10 px). "
                                  "Boxes are close estimates of each window's size.", "Caption", wrap=True)
        self.layout_.addWidget(self.hint)

        self.mgr.changed.connect(self._external_change)
        self.mgr.message.connect(self.status)

    # --- loading ----------------------------------------------------------------------------
    def on_shown(self) -> None:
        if not self.dirty:
            want = self.mgr.game_job() or overlays.DEFAULT
            if self.job_combo.currentText() != want:
                self.job_combo.setCurrentText(want)  # loads via _job_picked
                return
            self.load(self.job_combo.currentText())

    def _external_change(self) -> None:
        if not self.dirty and self.isVisible():
            self.load(self.job_combo.currentText())

    def _job_picked(self, job: str) -> None:
        if job == self.job:
            return
        if self.dirty and not self._discard_ok():
            self.job_combo.blockSignals(True)
            self.job_combo.setCurrentText(self.job)
            self.job_combo.blockSignals(False)
            return
        self.load(job)

    def _discard_ok(self) -> bool:
        answer = QMessageBox.question(self, "Unsaved layout", f"Save your changes to the {self.job} layout first?",
                                      QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        if answer == QMessageBox.Save:
            self.save()
            return True
        return answer == QMessageBox.Discard

    def load(self, job: str) -> None:
        self.job = job
        char = self.mgr.character()
        self.layout = self.mgr.layout_for(job) if char else {"positions": {}, "shown": {}}
        own = job == overlays.DEFAULT or self.mgr.store.has(char, job)
        self.uses_default.setText("" if own else "Uses Default until you save")
        if not self.ctx.windower_dir or not char:
            self.uses_default.setText("Log in once with the Nexus addon loaded to set up layouts.")
        self.reset_btn.setVisible(job != overlays.DEFAULT and self.mgr.store.has(char, job))
        self.copy_combo.blockSignals(True)
        self.copy_combo.clear()
        self.copy_combo.addItem("Copy from…")
        self.copy_combo.addItems([j for j in [overlays.DEFAULT] + self.mgr.store.jobs(char) if j != job])
        self.copy_combo.blockSignals(False)
        self._build()
        self.dirty = False

    def _build(self) -> None:
        self._syncing = True
        self.scr = self.mgr.screen()
        w, h = self.scr.width, self.scr.height
        self.scene.clear()
        self.scene.boxes = {}
        self.scene.set_screen(w, h, self.ctx.settings.get("layout_background") or "")
        self.list.clear()
        positions = self.layout["positions"]
        for ov in self.mgr.overlays():
            raw = positions.get(ov.id)
            if raw is None:
                continue
            bw, bh = self.scr.sizes[ov.id]
            box = OverlayBox(ov.id, ov.label, bw, bh, self.relay)
            box.shown = self.layout["shown"].get(ov.addon, True)
            box.restyle()
            box.setPos(*self.scr.to_screen(ov.id, raw, positions))
            self.scene.addItem(box)
            self.scene.boxes[ov.id] = box
            item = QListWidgetItem(ov.label + ("  (found automatically)" if ov.discovered else ""))
            item.setData(Qt.UserRole, ov.id)
            if self.mgr.toggleable(ov.addon):
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked if box.shown else Qt.Unchecked)
            self.list.addItem(item)
        self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        if not self.scene.boxes:
            self.size_note.setText("No addon windows found. Check your Windower folder in Settings.")
        self._syncing = False

    # --- editing ----------------------------------------------------------------------------
    def _overlay(self, oid: str):
        return self.scr.by_id.get(oid)

    def _box_moved(self, oid: str) -> None:
        if self._syncing:
            return
        box = self.scene.boxes[oid]
        positions = self.layout["positions"]
        positions[oid] = self.scr.from_screen(oid, (box.pos().x(), box.pos().y()), positions)
        self._syncing = True
        for other_id, other in self.scene.boxes.items():  # e.g. the pet bar rides along under xivbar
            ov = self._overlay(other_id)
            if ov and ov.follows == oid and other_id in positions:
                other.setPos(*self.scr.to_screen(other_id, positions[other_id], positions))
        self._syncing = False
        self.dirty = True
        if self.scene.selectedItems() and self.scene.selectedItems()[0] is box:
            self._show_spins(oid)

    def _selection_changed(self) -> None:
        sel = self.scene.selectedItems()
        if not sel:
            return
        oid = sel[0].oid
        for i in range(self.list.count()):
            if self.list.item(i).data(Qt.UserRole) == oid:
                self.list.blockSignals(True)
                self.list.setCurrentRow(i)
                self.list.blockSignals(False)
        self._show_spins(oid)

    def _list_selected(self, item, _prev=None) -> None:
        if item is None:
            return
        oid = item.data(Qt.UserRole)
        box = self.scene.boxes.get(oid)
        if box:
            self.scene.clearSelection()
            box.setSelected(True)
            self.view.setFocus()

    def _show_spins(self, oid: str) -> None:
        raw = self.layout["positions"].get(oid, [0, 0])
        self._syncing = True
        self.x_spin.setValue(int(raw[0]))
        self.y_spin.setValue(int(raw[1]))
        self._syncing = False
        ov = self._overlay(oid)
        anchor = {"bottom-center": "offset from the bottom center of the screen",
                  "follow": f"offset from {ov.follows}" if ov else ""}.get(ov.anchor if ov else "", "")
        if ov and self.scr.flags.get(oid, {}).get("right"):
            anchor = "measured from the right edge"
        self.size_note.setText(f"{ov.label}: X and Y as {ov.addon} stores them"
                               + (f" ({anchor})" if anchor else "") + "." if ov else "")

    def _spin_changed(self) -> None:
        if self._syncing:
            return
        sel = self.scene.selectedItems()
        if not sel:
            return
        oid = sel[0].oid
        positions = self.layout["positions"]
        positions[oid] = [self.x_spin.value(), self.y_spin.value()]
        self._syncing = True
        sel[0].setPos(*self.scr.to_screen(oid, positions[oid], positions))
        self._syncing = False
        self._box_moved(oid)

    def _shown_toggled(self, item) -> None:
        if self._syncing:
            return
        ov = self._overlay(item.data(Qt.UserRole))
        on = item.checkState() == Qt.Checked
        self.layout["shown"][ov.addon] = on
        self._syncing = True
        for i in range(self.list.count()):  # every window of the same addon follows
            other = self.list.item(i)
            other_ov = self._overlay(other.data(Qt.UserRole))
            if other_ov and other_ov.addon == ov.addon:
                other.setCheckState(Qt.Checked if on else Qt.Unchecked)
                box = self.scene.boxes.get(other_ov.id)
                if box:
                    box.shown = on
                    box.restyle()
        self._syncing = False
        self.dirty = True

    def _copy_from(self, index: int) -> None:
        if index <= 0:
            return
        source = self.copy_combo.itemText(index)
        self.layout = self.mgr.layout_for(source)
        self._build()
        self.dirty = True
        self.copy_combo.setCurrentIndex(0)
        self.status(f"Copied the {source} layout. Save to keep it for {self.job}.")

    def capture(self) -> None:
        current = self.mgr.current_positions()
        self.layout["positions"].update(current)
        self._build()
        self.dirty = True
        self.status("Took the windows' current spots. Save to keep them.")

    def pick_background(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Pick an FFXI screenshot", "",
                                              "Images (*.png *.jpg *.jpeg *.bmp)")
        self.ctx.settings.set("layout_background", path or "")
        self._build()

    def use_default(self) -> None:
        if self.confirm("Use Default", f"Remove the {self.job} layout? {self.job} goes back to using Default.",
                        "Remove"):
            self.mgr.store.remove(self.mgr.character(), self.job)
            self.load(self.job)

    def save(self) -> None:
        if not self.mgr.character():
            self.info("No character yet", "Log in with the Nexus addon loaded once, so the app knows whose layout this is.")
            return
        self.dirty = False
        self.mgr.save_layout(self.job, self.layout)
        self.load(self.job)
        self.status(f"Saved the {self.job} layout.")

    def arrange_in_game(self) -> None:
        if not self.ctx.bridge.connected:
            self.info("Game not connected", "Log in with the Nexus addon loaded, then try again.")
            return
        if self.dirty:
            self.save()
        self.mgr.send_frames()
        self.status("Frames are up in FFXI. Drag them, then click Save layout there.")
