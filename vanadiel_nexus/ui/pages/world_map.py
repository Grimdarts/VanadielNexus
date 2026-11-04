"""Interactive Vana'diel World Map & Route Finder page."""
from __future__ import annotations

import math
import os

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QKeySequence,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
    QShortcut,
)
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFrame,
    QGraphicsItem,
    QGraphicsObject,
    QGraphicsPathItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...core import world_map
from .. import theme, widgets

NODE_WIDTH = 152.0
NODE_HEIGHT = 32.0
MIN_ZOOM = 0.55    # floor for the mouse wheel at normal sizes; "Whole map" may go lower to fit everything
MAX_ZOOM = 3.00
LABEL_ZOOM = 0.62  # below this, zone names are hidden and region banners do the talking


class RegionBannerItem(QGraphicsRectItem):
    """Draggable header banner for a regional halo cluster."""

    def __init__(self, halo: RegionHaloItem, name: str):
        super().__init__()  # not a child of the halo, so it can sit above lines and nodes
        self.halo = halo
        self.setZValue(40)
        # Box and text both stay a fixed screen size, so the name is readable at every zoom level
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
        self.setBrush(QBrush(QColor(18, 26, 46, 235)))
        self.setPen(QPen(QColor(theme.BORDER), 1.0))
        self.text_item = QGraphicsSimpleTextItem(name, self)
        f = QFont(theme.UI_FONT)
        f.setPixelSize(13)
        f.setBold(True)
        self.text_item.setFont(f)
        self.text_item.setBrush(QBrush(QColor(theme.MUTED)))
        tb = self.text_item.boundingRect()
        self.text_item.setPos(-tb.width() / 2.0, -tb.height() / 2.0)
        self.setRect(-tb.width() / 2.0 - 10.0, -tb.height() / 2.0 - 4.0, tb.width() + 20.0, tb.height() + 8.0)
        self._dragging = False
        self._last_scene_pos = QPointF()

    def mousePressEvent(self, event):
        if self.halo.page.arrange_mode and event.button() == Qt.LeftButton:
            self._dragging = True
            self._last_scene_pos = event.scenePos()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging and self.halo.page.arrange_mode:
            delta = event.scenePos() - self._last_scene_pos
            self._last_scene_pos = event.scenePos()
            self.halo.translate_members(delta.x(), delta.y())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._dragging:
            self._dragging = False
            self.halo.page.persist_current_layout()
            event.accept()
            return
        super().mouseReleaseEvent(event)


class RegionHaloItem(QGraphicsRectItem):
    """Dynamic bounding-box halo wrapping all member ZoneNode items in a region."""

    def __init__(self, region: world_map.RegionCluster, page: WorldMapPage):
        super().__init__()
        self.region = region
        self.page = page
        self.member_nodes: list[NodeItem] = []
        self.setZValue(-20)
        self.setBrush(QBrush(QColor(18, 26, 46, 95)))
        self.setPen(QPen(QColor(theme.BORDER), 1.2, Qt.DashLine))
        self.banner = RegionBannerItem(self, region.name)
        self.update_bounds()

    def update_bounds(self) -> None:
        if not self.member_nodes:
            rect = QRectF(
                self.region.cx - self.region.rx,
                self.region.cy - self.region.ry,
                self.region.rx * 2.0,
                self.region.ry * 2.0,
            )
        else:
            min_x = min(n.pos().x() - NODE_WIDTH / 2.0 for n in self.member_nodes) - 28.0
            max_x = max(n.pos().x() + NODE_WIDTH / 2.0 for n in self.member_nodes) + 28.0
            min_y = min(n.pos().y() - NODE_HEIGHT / 2.0 for n in self.member_nodes) - 34.0
            max_y = max(n.pos().y() + NODE_HEIGHT / 2.0 for n in self.member_nodes) + 24.0
            rect = QRectF(min_x, min_y, max_x - min_x, max_y - min_y)
            self.region.cx = round(rect.center().x(), 1)
            self.region.cy = round(rect.center().y(), 1)
            self.region.rx = round(rect.width() / 2.0, 1)
            self.region.ry = round(rect.height() / 2.0, 1)
        self.setRect(rect)
        self.banner.setPos(rect.center().x(), rect.top() + 12.0)

    def translate_members(self, dx: float, dy: float) -> None:
        for node_item in self.member_nodes:
            node_item.setPos(node_item.pos().x() + dx, node_item.pos().y() + dy)
        self.update_bounds()

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setBrush(self.brush())
        painter.setPen(self.pen())
        painter.drawRoundedRect(self.rect(), 18.0, 18.0)


class EdgeItem(QGraphicsPathItem):
    """Connection line between two ZoneNodes with optional one-way arrowhead."""

    def __init__(self, edge: world_map.ZoneEdge, source_item: NodeItem, target_item: NodeItem):
        super().__init__()
        self.edge = edge
        self.source_item = source_item
        self.target_item = target_item
        self.is_on_route = False
        self.route_forward = True
        self.span_length = 0.0
        self.setZValue(-10)
        self.update_geometry()

    def update_geometry(self) -> None:
        p1 = self.source_item.pos()
        p2 = self.target_item.pos()
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        self.span_length = math.hypot(dx, dy)
        path = QPainterPath()
        path.moveTo(p1)
        path.lineTo(p2)

        # Add directional arrowhead for one-way edges or active route edges
        if not self.edge.bidirectional or self.is_on_route:
            start_pt = p1 if (not self.is_on_route or self.route_forward) else p2
            end_pt = p2 if (not self.is_on_route or self.route_forward) else p1
            adx = end_pt.x() - start_pt.x()
            ady = end_pt.y() - start_pt.y()
            length = math.hypot(adx, ady)
            if length > 40.0:
                ux, uy = adx / length, ady / length
                # Place arrowhead 58% along the segment so it never hides under the node pill
                tip = QPointF(start_pt.x() + adx * 0.58, start_pt.y() + ady * 0.58)
                size = 8.0
                left = QPointF(
                    tip.x() - ux * size - uy * (size * 0.6),
                    tip.y() - uy * size + ux * (size * 0.6),
                )
                right = QPointF(
                    tip.x() - ux * size + uy * (size * 0.6),
                    tip.y() - uy * size - ux * (size * 0.6),
                )
                path.moveTo(tip)
                path.lineTo(left)
                path.lineTo(right)
                path.closeSubpath()

        self.setPath(path)
        self._apply_pen()

    def _apply_pen(self) -> None:
        if self.is_on_route:
            pen = QPen(QColor(theme.GOLD), 3.0, Qt.SolidLine)
            self.setBrush(QBrush(QColor(theme.GOLD)))
            self.setZValue(-5)
        elif self.edge.kind == "transport":
            pen = QPen(QColor(theme.ACCENT_STRONG), 1.8, Qt.DashLine)
            self.setBrush(QBrush(QColor(theme.ACCENT_STRONG)))
            self.setZValue(-10)
        elif self.edge.kind == "gated":
            pen = QPen(QColor(theme.WARNING), 2.0, Qt.DotLine)
            self.setBrush(QBrush(QColor(theme.WARNING)))
            self.setZValue(-10)
        else:
            pen = QPen(QColor("#3B4B72"), 1.8, Qt.SolidLine)
            self.setBrush(QBrush(QColor(theme.MUTED)))
            self.setZValue(-10)
        self.setPen(pen)


class NodeItem(QGraphicsObject):
    """Stylized zone node (stadium pill for hub, rounded rect for field/dungeon, diamond for endgame)."""

    clicked = Signal(int)

    def __init__(self, zone: world_map.ZoneNode, page: WorldMapPage):
        super().__init__()
        self.zone = zone
        self.page = page
        self.incident_edges: list[EdgeItem] = []
        self.parent_halo: RegionHaloItem | None = None
        self.is_selected = False
        self.is_live_zone = False
        self.is_on_route = False
        self._drag_start_pos = QPointF(zone.x, zone.y)

        self.setPos(zone.x, zone.y)
        self.setZValue(10)
        self.setCursor(Qt.PointingHandCursor)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setToolTip(f"{zone.name} (ID {zone.id})")

    def boundingRect(self) -> QRectF:
        return QRectF(-NODE_WIDTH / 2.0 - 4.0, -NODE_HEIGHT / 2.0 - 4.0, NODE_WIDTH + 8.0, NODE_HEIGHT + 8.0)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(-NODE_WIDTH / 2.0, -NODE_HEIGHT / 2.0, NODE_WIDTH, NODE_HEIGHT)

        # Fill & border color
        if self.is_selected:
            fill = QColor("#1E2D4F")
        elif self.zone.kind == "endgame":
            fill = QColor("#1B192E")
        elif self.zone.kind == "hub":
            fill = QColor("#16223B")
        else:
            fill = QColor(theme.SURFACE)

        if self.is_live_zone:
            border_color = QColor(theme.ACCENT)
            border_width = 2.6
        elif self.is_selected or self.is_on_route:
            border_color = QColor(theme.GOLD)
            border_width = 2.5
        elif self.zone.kind == "endgame":
            border_color = QColor(theme.GOLD)
            border_width = 1.6
        elif self.zone.kind == "hub":
            border_color = QColor(theme.MUTED)
            border_width = 1.6
        else:
            border_color = QColor("#3B4B72")
            border_width = 1.4

        pen = QPen(border_color, border_width)
        if self.zone.kind == "dungeon" and not (self.is_selected or self.is_on_route or self.is_live_zone):
            pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        painter.setBrush(QBrush(fill))

        lod = option.levelOfDetailFromTransform(painter.worldTransform()) if option is not None else 1.0
        if lod < LABEL_ZOOM and not (self.is_selected or self.is_live_zone or self.is_on_route):
            # Zoomed out: a quiet marker instead of an unreadable label
            painter.setPen(QPen(border_color, 1.0))
            painter.setBrush(QBrush(border_color if self.zone.kind != "field" else QColor("#3B4B72")))
            painter.drawRoundedRect(QRectF(-NODE_WIDTH / 2.0 + 18, -6.0, NODE_WIDTH - 36, 12.0), 6.0, 6.0)
            return
        if self.zone.kind == "endgame":
            # Subtle elongated octagon/diamond badge
            cut = 10.0
            poly = QPolygonF([
                QPointF(rect.left() + cut, rect.top()),
                QPointF(rect.right() - cut, rect.top()),
                QPointF(rect.right(), rect.center().y()),
                QPointF(rect.right() - cut, rect.bottom()),
                QPointF(rect.left() + cut, rect.bottom()),
                QPointF(rect.left(), rect.center().y()),
            ])
            painter.drawPolygon(poly)
        elif self.zone.kind == "hub":
            painter.drawRoundedRect(rect, NODE_HEIGHT / 2.0, NODE_HEIGHT / 2.0)
        else:
            painter.drawRoundedRect(rect, 6.0, 6.0)

        # Scene-space label, elided inside the box (full name in the tooltip)
        font = QFont(theme.UI_FONT)
        font.setPixelSize(13)
        if self.is_selected or self.is_live_zone or self.zone.kind == "hub":
            font.setBold(True)
        painter.setFont(font)

        prefix = "★ " if self.is_live_zone else ("◆ " if self.zone.kind == "endgame" else "")
        raw_label = f"{prefix}{self.zone.short_name}"
        metrics = QFontMetrics(font)
        elided = metrics.elidedText(raw_label, Qt.ElideRight, int(NODE_WIDTH - 14))

        text_color = QColor(theme.ACCENT) if self.is_live_zone else QColor(theme.TEXT)
        painter.setPen(QPen(text_color))
        painter.drawText(rect.adjusted(6.0, 0.0, -6.0, 0.0), Qt.AlignCenter, elided)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            pos = self.pos()
            self.zone.x = round(pos.x(), 1)
            self.zone.y = round(pos.y(), 1)
            for edge_item in self.incident_edges:
                edge_item.update_geometry()
            if self.parent_halo is not None:
                self.parent_halo.update_bounds()
            self.page.update_warp_arcs()
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = QPointF(self.pos())
            self.clicked.emit(self.zone.id)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if (
            self.page.arrange_mode
            and event.button() == Qt.LeftButton
            and (self.pos() - self._drag_start_pos).manhattanLength() > 0.5
        ):
            self.page.persist_current_layout()


class WorldMapCanvasView(QGraphicsView):
    """Cursor-anchored zoomable/pannable QGraphicsView with 0.55x minimum zoom floor."""

    def __init__(self, scene: QGraphicsScene, parent=None):
        super().__init__(scene, parent)
        self._zoom = 1.0
        self.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setViewportUpdateMode(QGraphicsView.SmartViewportUpdate)
        self.setBackgroundBrush(QBrush(QColor(theme.BG)))
        self.setFrameShape(QFrame.NoFrame)

    def set_zoom(self, zoom: float) -> None:
        clamped = max(self.min_zoom(), min(MAX_ZOOM, zoom))
        factor = clamped / self._zoom
        self._zoom = clamped
        self.scale(factor, factor)

    def min_zoom(self) -> float:
        """Wheel floor: the 0.55x readability floor, or lower if that's what it takes to see the whole map."""
        rect = self.scene().itemsBoundingRect() if self.scene() is not None else QRectF()
        if not rect.isValid() or rect.width() <= 0:
            return MIN_ZOOM
        fit = min((self.viewport().width() - 20) / rect.width(), (self.viewport().height() - 20) / rect.height())
        return max(0.1, min(MIN_ZOOM, fit))

    def fit_rect(self, rect: QRectF) -> None:
        """Zoom out until rect fits the viewport."""
        target = min((self.viewport().width() - 20) / max(1.0, rect.width()),
                     (self.viewport().height() - 20) / max(1.0, rect.height()), 1.0)
        self.set_zoom(target)
        self.centerOn(rect.center())

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta == 0:
            return
        step = 1.15 if delta > 0 else (1.0 / 1.15)
        self.set_zoom(self._zoom * step)


class _RowButton(QLabel):
    """A clickable, word-wrapping row for route steps and neighbours (QPushButton can't wrap text)."""

    def __init__(self, text: str, on_click, tooltip: str = ""):
        super().__init__(text)
        self._on_click = on_click
        self.setWordWrap(True)
        self.setTextFormat(Qt.PlainText)
        self.setToolTip(tooltip)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setStyleSheet(
            f"QLabel {{ background: {theme.SURFACE}; border: 1px solid {theme.BORDER}; border-radius: 6px;"
            f" padding: 6px 10px; color: {theme.TEXT}; }}"
            f"QLabel:hover, QLabel:focus {{ border-color: {theme.ACCENT}; }}"
        )

    def click(self) -> None:
        self._on_click()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect().contains(event.position().toPoint()):
            self._on_click()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self._on_click()
            return
        super().keyPressEvent(event)


class WorldMapPage(QWidget):
    key = "map"
    title = "World Map"

    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self._override_path = os.path.join(self.ctx.data_dir, "world_map_layout.json")
        self.graph: world_map.WorldMapGraph | None = None
        self.node_items: dict[int, NodeItem] = {}
        self.edge_items: list[EdgeItem] = []
        self.halo_items: dict[str, RegionHaloItem] = {}
        self.warp_arc_items: list[QGraphicsPathItem] = []

        self.selected_era = "all"
        self.selected_zone_id: int = world_map.DEFAULT_HUB_ZONE_ID
        self.origin_zone_id: int = world_map.DEFAULT_HUB_ZONE_ID
        self.live_zone_id: int | None = None
        self.active_route: world_map.RouteResult | None = None
        self.arrange_mode = False
        self._scene_built = False

        self._build_ui()
        self.ctx.zone_changed.connect(self._on_live_zone_changed)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)

        # --- 2-Row Top Toolbar ---
        toolbar_frame = QFrame()
        toolbar_frame.setObjectName("Card")
        tb_layout = QVBoxLayout(toolbar_frame)
        tb_layout.setContentsMargins(12, 10, 12, 10)
        tb_layout.setSpacing(8)

        # Row 1: Search + Arrange Layout + Reset Layout + Open in Browser
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search zone (e.g. Sortie, Reisenjima, Sky, 246)…")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMinimumWidth(220)
        self.search_input.textChanged.connect(self._on_search_changed)
        self.search_input.returnPressed.connect(self._on_search_enter)
        row1.addWidget(self.search_input, 1)

        find_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        find_shortcut.activated.connect(lambda: self.search_input.setFocus())
        esc_shortcut = QShortcut(QKeySequence("Esc"), self)
        esc_shortcut.activated.connect(self._clear_search_or_selection)

        self.arrange_btn = widgets.button(
            "Arrange Layout: Off",
            on_click=self.toggle_arrange_mode,
            tooltip="Drag zone nodes or regional banners on the canvas and save layout overrides",
        )
        self.reset_layout_btn = widgets.button(
            "Reset Layout",
            kind="ghost",
            on_click=self.reset_layout,
            tooltip="Restore default shipped node positions",
        )
        self.export_btn = widgets.button(
            "Open in Browser ↗",
            kind="primary",
            on_click=self.open_in_browser,
            tooltip="Export and open a standalone interactive HTML/SVG world map",
        )
        row1.addWidget(self.arrange_btn)
        row1.addWidget(self.reset_layout_btn)
        row1.addWidget(self.export_btn)
        tb_layout.addLayout(row1)

        # Row 2: Responsive FlowLayout with 8 Era/Content filter pills
        pill_container = QWidget()
        self.pill_flow = widgets.FlowLayout(pill_container, spacing=6)
        self.era_group = QButtonGroup(self)
        self.era_group.setExclusive(True)
        self.era_buttons: dict[str, QPushButton] = {}
        for era_key, era_label in world_map.ERA_LABELS.items():
            btn = widgets.pill(era_label.replace("&", "&&"), clickable=True)
            btn.setCheckable(True)
            if era_key == "all":
                btn.setChecked(True)
            btn.clicked.connect(lambda _checked=False, k=era_key: self.set_era_filter(k))
            self.era_group.addButton(btn)
            self.pill_flow.addWidget(btn)
            self.era_buttons[era_key] = btn
        tb_layout.addWidget(pill_container)
        root.addWidget(toolbar_frame)

        # --- Workspace: Canvas (Left) + 340px Detail Panel (Right) ---
        workspace = QHBoxLayout()
        workspace.setSpacing(12)

        canvas_frame = QFrame()
        canvas_frame.setObjectName("Card")
        canvas_lay = QVBoxLayout(canvas_frame)
        canvas_lay.setContentsMargins(2, 2, 2, 2)
        canvas_lay.setSpacing(0)

        self.scene = QGraphicsScene(0, 0, 3600, 2400, self)
        self.view = WorldMapCanvasView(self.scene, self)
        canvas_lay.addWidget(self.view, 1)

        # Bottom canvas utility bar
        canvas_bar = QHBoxLayout()
        canvas_bar.setContentsMargins(10, 6, 10, 6)
        self.live_status_label = widgets.label("Live Zone: Offline (routing from Port Jeuno)", "Caption")
        self.center_me_btn = widgets.button("Center on Origin", kind="ghost", on_click=self.center_on_origin)
        self.whole_map_btn = widgets.button("Whole map", kind="ghost", on_click=self.show_whole_map,
                                            tooltip="Zoom out to see every region")
        self.reset_zoom_btn = widgets.button("Reset Zoom", kind="ghost", on_click=self.reset_zoom)
        canvas_bar.addWidget(self.live_status_label)
        canvas_bar.addStretch(1)
        canvas_bar.addWidget(self.center_me_btn)
        canvas_bar.addWidget(self.whole_map_btn)
        canvas_bar.addWidget(self.reset_zoom_btn)
        canvas_lay.addLayout(canvas_bar)
        workspace.addWidget(canvas_frame, 1)

        # Right-hand Detail Panel (340px fixed width)
        self.detail_panel = QFrame()
        self.detail_panel.setObjectName("Card")
        self.detail_panel.setFixedWidth(340)
        dp_outer = QVBoxLayout(self.detail_panel)
        dp_outer.setContentsMargins(14, 14, 14, 14)
        dp_outer.setSpacing(10)

        self.detail_title = widgets.label("Port Jeuno", "SectionTitle", wrap=True)
        self.detail_meta = widgets.label("", "Caption", wrap=True)
        dp_outer.addWidget(self.detail_title)
        dp_outer.addWidget(self.detail_meta)

        self.badge_container = QWidget()
        self.badge_flow = widgets.FlowLayout(self.badge_container, spacing=6)
        dp_outer.addWidget(self.badge_container)

        self.detail_notes = widgets.label("", "Caption", wrap=True)
        dp_outer.addWidget(self.detail_notes)

        self.wiki_btn = widgets.button("Open on BG-Wiki ↗", on_click=self._open_selected_wiki)
        dp_outer.addWidget(self.wiki_btn)

        sep1 = QFrame()
        sep1.setObjectName("NavSeparator")
        dp_outer.addWidget(sep1)

        # Route Finder controls
        dp_outer.addWidget(widgets.label("How Do I Get Here?", "SectionTitle"))
        from_row = QHBoxLayout()
        from_row.addWidget(widgets.label("From:", "Caption"))
        self.from_combo = QComboBox()
        self.from_combo.currentIndexChanged.connect(self._on_origin_combo_changed)
        from_row.addWidget(self.from_combo, 1)
        dp_outer.addLayout(from_row)

        self.use_hp_chk = QCheckBox("Use Home Points")
        self.use_hp_chk.setChecked(True)
        self.use_hp_chk.toggled.connect(self._recompute_route)
        self.use_sg_chk = QCheckBox("Use Survival Guides")
        self.use_sg_chk.setChecked(True)
        self.use_sg_chk.toggled.connect(self._recompute_route)
        dp_outer.addWidget(self.use_hp_chk)
        dp_outer.addWidget(self.use_sg_chk)

        # Scrollable Route Steps + Connected Zones
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll_body = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_body)
        self.scroll_layout.setContentsMargins(0, 4, 0, 4)
        self.scroll_layout.setSpacing(6)

        self.route_header_label = widgets.label("Fastest Route", "Caption")
        self.scroll_layout.addWidget(self.route_header_label)
        self.route_steps_box = QVBoxLayout()
        self.route_steps_box.setSpacing(4)
        self.scroll_layout.addLayout(self.route_steps_box)

        self.neighbors_header_label = widgets.label("Connected Zones", "Caption")
        self.scroll_layout.addWidget(self.neighbors_header_label)
        self.neighbors_box = QVBoxLayout()
        self.neighbors_box.setSpacing(4)
        self.scroll_layout.addLayout(self.neighbors_box)
        self.scroll_layout.addStretch(1)

        scroll.setWidget(scroll_body)
        dp_outer.addWidget(scroll, 1)

        workspace.addWidget(self.detail_panel)
        root.addLayout(workspace, 1)

    # --- Lifecycle & Scene Construction ---
    def ensure_loaded(self) -> None:
        if self._scene_built and self.graph is not None:
            return
        self.graph = world_map.load_world_map(user_override_path=self._override_path)
        self._populate_from_combo()
        self._rebuild_scene()
        self._scene_built = True
        if self.ctx.zone_name:
            self._on_live_zone_changed(self.ctx.zone_name)
        else:
            self.select_zone(self.selected_zone_id, center=True)

    def on_shown(self) -> None:
        self.ensure_loaded()

    def _populate_from_combo(self) -> None:
        if self.graph is None:
            return
        self.from_combo.blockSignals(True)
        self.from_combo.clear()
        for z in sorted(self.graph.zones.values(), key=lambda item: item.name):
            self.from_combo.addItem(z.name, z.id)
        idx = self.from_combo.findData(self.origin_zone_id)
        if idx >= 0:
            self.from_combo.setCurrentIndex(idx)
        self.from_combo.blockSignals(False)

    def _rebuild_scene(self) -> None:
        if self.graph is None:
            return
        self.scene.clear()
        self.node_items.clear()
        self.edge_items.clear()
        self.halo_items.clear()
        self.warp_arc_items.clear()

        for region in self.graph.regions.values():
            halo = RegionHaloItem(region, self)
            self.scene.addItem(halo)
            self.scene.addItem(halo.banner)
            self.halo_items[region.id] = halo

        for zone in self.graph.zones.values():
            item = NodeItem(zone, self)
            item.clicked.connect(lambda zid: self.select_zone(zid, center=False))
            self.scene.addItem(item)
            self.node_items[zone.id] = item
            halo = self.halo_items.get(zone.region_id)
            if halo is not None:
                halo.member_nodes.append(item)
                item.parent_halo = halo

        for halo in self.halo_items.values():
            halo.update_bounds()

        for edge in self.graph.edges:
            s_item = self.node_items.get(edge.from_id)
            t_item = self.node_items.get(edge.to_id)
            if s_item is None or t_item is None:
                continue
            e_item = EdgeItem(edge, s_item, t_item)
            self.scene.addItem(e_item)
            self.edge_items.append(e_item)
            s_item.incident_edges.append(e_item)
            t_item.incident_edges.append(e_item)

        self._apply_arrange_flags()
        self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-300, -200, 300, 200))

    # --- Selection, Filtering, & Routing ---
    def select_zone(self, zone_id: int, *, center: bool = False) -> None:
        self.ensure_loaded()
        if self.graph is None:
            return
        node = self.graph.resolve_zone(zone_id)
        if node is None:
            return
        self.selected_zone_id = node.id
        for zid, item in self.node_items.items():
            item.is_selected = zid == self.selected_zone_id
            item.update()
        self._recompute_route()
        self._update_detail_panel()
        if center and node.id in self.node_items:
            self.view.centerOn(self.node_items[node.id])

    def set_era_filter(self, era_key: str) -> None:
        self.ensure_loaded()
        self.selected_era = era_key
        if era_key in self.era_buttons and not self.era_buttons[era_key].isChecked():
            self.era_buttons[era_key].setChecked(True)
        self._update_canvas_visibility()

    def _on_search_changed(self, _text: str) -> None:
        self.ensure_loaded()
        self._update_canvas_visibility()

    def _on_search_enter(self) -> None:
        self.ensure_loaded()
        if self.graph is None:
            return
        matches = world_map.search_zones(self.graph, self.search_input.text())
        if matches:
            self.select_zone(matches[0].id, center=True)

    def _clear_search_or_selection(self) -> None:
        if self.search_input.text():
            self.search_input.clear()
        elif self.graph is not None and self.selected_zone_id != self.origin_zone_id:
            self.select_zone(self.origin_zone_id, center=False)

    def _on_origin_combo_changed(self, index: int) -> None:
        if index < 0:
            return
        zid = self.from_combo.itemData(index)
        if isinstance(zid, int):
            self.origin_zone_id = zid
            self._recompute_route()

    def _on_live_zone_changed(self, zone_name: str) -> None:
        self.ensure_loaded()
        if self.graph is None:
            return
        resolved = self.graph.resolve_zone(zone_name)
        if resolved is not None:
            self.live_zone_id = resolved.id
            self.origin_zone_id = resolved.id
            idx = self.from_combo.findData(resolved.id)
            if idx >= 0:
                self.from_combo.blockSignals(True)
                self.from_combo.setCurrentIndex(idx)
                self.from_combo.blockSignals(False)
            self.live_status_label.setText(f"★ Live Zone: {resolved.name}")
        else:
            self.live_zone_id = None
            self.origin_zone_id = world_map.DEFAULT_HUB_ZONE_ID
            idx = self.from_combo.findData(world_map.DEFAULT_HUB_ZONE_ID)
            if idx >= 0:
                self.from_combo.blockSignals(True)
                self.from_combo.setCurrentIndex(idx)
                self.from_combo.blockSignals(False)
            self.live_status_label.setText(f"Live zone ({zone_name}) in Mog House/Instance — routing from Port Jeuno")

        for zid, item in self.node_items.items():
            item.is_live_zone = zid == self.live_zone_id
            item.update()
        self._recompute_route()

    def _recompute_route(self) -> None:
        if self.graph is None:
            return
        use_hp = self.use_hp_chk.isChecked()
        use_sg = self.use_sg_chk.isChecked()
        self.active_route = world_map.find_route(
            self.graph,
            self.origin_zone_id,
            self.selected_zone_id,
            allow_fast_travel=(use_hp or use_sg),
            use_hp=use_hp,
            use_sg=use_sg,
        )
        self._update_route_highlights()
        self._update_route_steps_list()
        self._update_canvas_visibility()

    def _update_route_highlights(self) -> None:
        route_nodes: set[int] = set()
        route_pairs: dict[tuple[int, int], bool] = {}
        if self.active_route and self.active_route.steps:
            route_nodes.add(self.active_route.start_id)
            for s in self.active_route.steps:
                route_nodes.add(s.from_id)
                route_nodes.add(s.to_id)
                if s.kind not in ("homepoint", "survival_guide", "warp_ring"):
                    route_pairs[(s.from_id, s.to_id)] = True

        for zid, n_item in self.node_items.items():
            n_item.is_on_route = zid in route_nodes
            n_item.update()

        for e_item in self.edge_items:
            fwd = (e_item.edge.from_id, e_item.edge.to_id) in route_pairs
            rev = e_item.edge.bidirectional and (e_item.edge.to_id, e_item.edge.from_id) in route_pairs
            e_item.is_on_route = fwd or rev
            e_item.route_forward = True if fwd else False
            e_item.update_geometry()

        self.update_warp_arcs()

    def update_warp_arcs(self) -> None:
        for arc in self.warp_arc_items:
            self.scene.removeItem(arc)
        self.warp_arc_items.clear()
        if not self.active_route:
            return
        for s in self.active_route.steps:
            if s.kind not in ("homepoint", "survival_guide", "warp_ring"):
                continue
            a_item = self.node_items.get(s.from_id)
            b_item = self.node_items.get(s.to_id)
            if a_item is None or b_item is None:
                continue
            p1 = a_item.pos()
            p2 = b_item.pos()
            ctrl = QPointF((p1.x() + p2.x()) / 2.0, (p1.y() + p2.y()) / 2.0 - 70.0)
            path = QPainterPath()
            path.moveTo(p1)
            path.quadTo(ctrl, p2)
            arc_item = QGraphicsPathItem(path)
            pen = QPen(QColor(theme.GOLD), 2.6, Qt.DashLine)
            arc_item.setPen(pen)
            arc_item.setZValue(5)
            self.scene.addItem(arc_item)
            self.warp_arc_items.append(arc_item)

    def _update_canvas_visibility(self) -> None:
        if self.graph is None:
            return
        query = self.search_input.text().strip()
        matched_ids = (
            {z.id for z in world_map.search_zones(self.graph, query)}
            if query
            else set(self.graph.zones.keys())
        )

        # Endgame filter includes endgame nodes AND their immediate parent entry hubs
        endgame_hubs: set[int] = set()
        if self.selected_era == "endgame":
            for e in self.graph.edges:
                if self.graph.zones[e.from_id].kind == "endgame":
                    endgame_hubs.add(e.to_id)
                if self.graph.zones[e.to_id].kind == "endgame":
                    endgame_hubs.add(e.from_id)

        for zid, n_item in self.node_items.items():
            z = n_item.zone
            if self.selected_era == "all":
                era_ok = True
            elif self.selected_era == "endgame":
                era_ok = z.kind == "endgame" or zid in endgame_hubs
            else:
                era_ok = z.era == self.selected_era
            search_ok = zid in matched_ids
            active = (era_ok and search_ok) or n_item.is_on_route or n_item.is_selected
            n_item.setOpacity(1.0 if active else 0.18)

        for e_item in self.edge_items:
            is_endpoint_selected = (
                e_item.edge.from_id == self.selected_zone_id
                or e_item.edge.to_id == self.selected_zone_id
            )
            # Hide cross-continent (>700px) non-local links unless selected or on active route
            if e_item.span_length > 700.0 and not (e_item.is_on_route or is_endpoint_selected):
                e_item.setVisible(False)
                continue
            e_item.setVisible(True)
            a_op = self.node_items[e_item.edge.from_id].opacity()
            b_op = self.node_items[e_item.edge.to_id].opacity()
            e_item.setOpacity(1.0 if (e_item.is_on_route or is_endpoint_selected) else min(a_op, b_op))

    # --- Detail Panel Updates ---
    def _clear_layout(self, lay) -> None:
        while lay.count():
            item = lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()

    @staticmethod
    def _compact_button(full_text: str, on_click, tooltip: str = "") -> QWidget:
        return _RowButton(full_text, on_click, tooltip or full_text)

    def _update_detail_panel(self) -> None:
        if self.graph is None:
            return
        z = self.graph.zones.get(self.selected_zone_id)
        if z is None:
            return
        reg = self.graph.regions.get(z.region_id)
        reg_name = reg.name if reg else z.region_id
        self.detail_title.setText(z.name)
        self.detail_meta.setText(f"{reg_name} · {world_map.ERA_LABELS.get(z.era, z.era)} · ID {z.id}")
        self.detail_notes.setText(z.notes or "Select any connected zone or route step below to pan the map.")

        self._clear_layout(self.badge_flow)
        self.badge_flow.addWidget(widgets.pill(z.kind.capitalize(), tone="gold" if z.kind == "endgame" else ""))
        if z.homepoints:
            self.badge_flow.addWidget(widgets.pill(f"Home Point ×{len(z.homepoints)}", tone="accent"))
        if z.has_survival_guide:
            self.badge_flow.addWidget(widgets.pill("Survival Guide ✓", tone="gold"))
        if z.can_mount:
            self.badge_flow.addWidget(widgets.pill("Mount ✓", tone="success"))
        self.badge_container.updateGeometry()

        # Connected neighbors
        self._clear_layout(self.neighbors_box)
        seen_neighbors: set[tuple[int, str]] = set()
        for nb_id, edge in self.graph.adjacency.get(z.id, []):
            pos = edge.position_in(z.id)
            key = (nb_id, pos)
            if key in seen_neighbors:
                continue
            seen_neighbors.add(key)
            nb = self.graph.zones[nb_id]
            suffix = f" · {pos}" if pos else ""
            req = f" [{edge.requirement}]" if edge.requirement else ""
            full_label = f"→ {nb.short_name}{suffix}{req}"
            btn = self._compact_button(
                full_label,
                on_click=lambda _c=False, target=nb_id: self.select_zone(target, center=True),
                tooltip=f"{nb.name}{suffix}{req}",
            )
            self.neighbors_box.addWidget(btn)

    def _update_route_steps_list(self) -> None:
        self._clear_layout(self.route_steps_box)
        if self.active_route is None:
            self.route_steps_box.addWidget(widgets.label("No route found between selected zones.", "Caption", wrap=True))
            return
        if not self.active_route.steps:
            self.route_steps_box.addWidget(widgets.label("You are already in this zone (0 hops).", "Caption", wrap=True))
            return
        for idx, step in enumerate(self.active_route.steps, start=1):
            req = f" ({step.requirement})" if step.requirement else ""
            full_step = f"{idx}. {step.label}{req}"
            btn = self._compact_button(
                full_step,
                on_click=lambda _c=False, target=step.to_id: self.select_zone(target, center=True),
                tooltip=full_step,
            )
            self.route_steps_box.addWidget(btn)

    # --- Actions: Arrange Mode, Reset, Browser Export, Wiki ---
    def toggle_arrange_mode(self) -> None:
        self.ensure_loaded()
        self.arrange_mode = not self.arrange_mode
        self.arrange_btn.setText("Arrange Layout: On" if self.arrange_mode else "Arrange Layout: Off")
        self._apply_arrange_flags()
        if not self.arrange_mode:
            self.persist_current_layout()

    def _apply_arrange_flags(self) -> None:
        for item in self.node_items.values():
            item.setFlag(QGraphicsItem.ItemIsMovable, self.arrange_mode)

    def persist_current_layout(self) -> None:
        if self.graph is not None:
            world_map.save_layout_overrides(self.graph, self._override_path)

    def reset_layout(self) -> None:
        self.ensure_loaded()
        if self.graph is None:
            return
        world_map.reset_layout_overrides(self.graph, self._override_path)
        for zid, item in self.node_items.items():
            z = self.graph.zones[zid]
            item.setPos(z.x, z.y)
        for halo in self.halo_items.values():
            halo.update_bounds()
        for e_item in self.edge_items:
            e_item.update_geometry()
        self.update_warp_arcs()

    def center_on_origin(self) -> None:
        self.ensure_loaded()
        target_id = self.live_zone_id or self.origin_zone_id
        if target_id in self.node_items:
            self.view.centerOn(self.node_items[target_id])

    def reset_zoom(self) -> None:
        self.view.set_zoom(1.0)

    def show_whole_map(self) -> None:
        self.ensure_loaded()
        rect = self.scene.itemsBoundingRect()
        if rect.isValid():
            self.view.fit_rect(rect)

    def open_in_browser(self) -> str:
        self.ensure_loaded()
        assert self.graph is not None
        out_path = os.path.join(self.ctx.data_dir, "exports", "vanadiel_world_map.html")
        world_map.export_standalone_html(
            self.graph,
            out_path,
            current_zone_id=self.live_zone_id or self.origin_zone_id,
            selected_zone_id=self.selected_zone_id,
            active_route=self.active_route,
        )
        self.ctx.open_path(out_path)
        return out_path

    def _open_selected_wiki(self) -> None:
        if self.graph is None:
            return
        z = self.graph.zones.get(self.selected_zone_id)
        if z is not None:
            self.ctx.open_url(z.bgwiki_url)
