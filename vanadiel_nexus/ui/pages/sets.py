"""Sets: every GearSwap set in the character's job file, drawn as the in-game 4×4 equipment grid.

    ┌ [Search sets or items…] [Character ▾] [Job ▾] [Sub ▾] [⟳ Reload files] ─────────────────────────┐
    │ Lua read 2 min ago · Inventory from 1 Nov 14:20              Game is on SMN/WHM · Follow game    │
    ├ From your Lua (read-only) ┬ ⚠ 2 need attention ──────────────────┬ Head ────────────────────────┤
    │ Weapon skill (12)         │ SavageBlade.Attack                   │ Hashishin Kavuk +2 · owned   │
    │   SavageBlade.Attack  ⚠2  │ Weapon skill · BLU.lua · 15/16 set   │ (slides over the grid when   │
    │   ↪ savage                │ [4×4 EquipGrid]                      │  the window is narrow)       │
    │ Idle (4) …                │ Needs attention · 2                  │                              │
    └───────────────────────────┴──────────────────────────────────────┴──────────────────────────────┘

The page only reads: the job file runs in a sandboxed child process (core/gearswap_reader), one read at a time,
latest request wins. Nothing here writes to disk except the sets_character and sets_tree_width settings.
Spec: docs/SET-MANAGER-DESIGN-REVIEW.md (layout, states, keyboard) and SET-MANAGER-ENG-REVIEW.md.
"""
import os
import time

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPoint, QPropertyAnimation, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtGui import QColor, QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QComboBox, QFrame, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMenu, QPlainTextEdit, QScrollArea, QSplitter,
    QStackedWidget, QTabWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from ...core import gearswap_files, gearswap_reader, item_res, set_manager
from ...core.jobs import ALL_FFXI_JOBS
from .. import theme, widgets
from ..equip_grid import SLOT_LABELS, CellData, EquipGrid, describe
from ..item_links import add_open_actions
from ..equipment_analyzer import EquipmentAnalyzer
from .base import Page

JOBS = [job for job in ALL_FFXI_JOBS if job != 'All']
PANEL_WIDTH = 330
TREE_MIN = 200
PATH_ROLE = Qt.UserRole
ALIAS_ROLE = Qt.UserRole + 1


def short_path(path: str) -> str:
    """'sets.SavageBlade.Attack' → 'SavageBlade.Attack'."""
    return path[5:] if path.startswith('sets.') else path[4:] if path.startswith('sets[') else path


def relative_time(then: float, now: float = None) -> str:
    seconds = max(0, (now or time.time()) - then)
    if seconds < 60:
        return 'just now'
    if seconds < 3600:
        return f'{int(seconds // 60)} min ago'
    if seconds < 86400:
        return f'{int(seconds // 3600)} h ago'
    return time.strftime('%d %b %H:%M', time.localtime(then))


def attention_sentence(slot: str, status, character: str) -> str:
    label = SLOT_LABELS[slot]
    name = status.piece.name if status.piece else ''
    if status.kind == 'unreachable':
        where = 'on a storage slip' if status.detail == 'on a slip' else f'in {status.bag}'
        return f"{label}: {name} is {where}. GearSwap can't equip it from there."
    if status.kind == 'other_character':
        return f"{label}: {name} is {status.detail[0].lower() + status.detail[1:]}, not {character}."
    if status.kind == 'unknown':
        if status.detail == 'Wrong slot':
            return f"{label}: {name} can't go in this slot."
        return f'{label}: "{name}" isn\'t in the game data. Check the spelling.'
    detail = status.detail if status.detail != 'Not owned' else 'not owned'
    return f'{label}: {name}: {detail}.'


def cell_for(slot: str, status) -> CellData:
    piece = status.piece
    name = piece.name if piece else ''
    kind = status.kind
    caption = ''
    if kind == 'owned':
        caption = f'from {short_path(piece.inherited_from)}' if piece and piece.inherited_from else status.bag
    elif kind == 'unreachable':
        caption = f'⚠ {status.detail}'
    elif kind == 'missing':
        caption = '✕ Not owned' if status.detail == 'Not owned' else status.detail
    elif kind in ('other_character', 'unknown', 'no_snapshot'):
        caption = status.detail
    tooltip = ''
    if piece and name:
        lines = [name] + list(piece.augments)
        if piece.bag:
            lines.append(f'Must be in {piece.bag}')
        tooltip = '\n'.join(lines)
    cell = CellData(slot, name, kind, caption, tooltip, note=status.note)
    cell.accessible_name = describe(cell)
    return cell


class _ReadSignals(QObject):
    done = Signal(int, object)


class _ReadTask(QRunnable):
    def __init__(self, generation: int, args: dict):
        super().__init__()
        self.generation = generation
        self.args = args
        self.signals = _ReadSignals()

    def run(self):
        try:
            result = gearswap_reader.read_job(**self.args)
        except Exception as error:  # never leave the page waiting
            result = gearswap_reader.JobRead(self.args['character'], self.args['job'], self.args['sub_job'], '',
                                             False, {}, error=f'{type(error).__name__}: {error}')
        self.signals.done.emit(self.generation, result)


class _ClickLabel(QLabel):
    clicked = Signal()

    def __init__(self, text=''):
        super().__init__(text)
        self.setWordWrap(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setTextFormat(Qt.PlainText)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class _Message(QWidget):
    """A centred message for the whole page or for a read error, with an optional button and details."""

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.addStretch(1)
        self.title = widgets.label('', 'SectionTitle', wrap=True)
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setTextFormat(Qt.PlainText)
        self.detail = widgets.label('', 'Caption', wrap=True)
        self.detail.setAlignment(Qt.AlignCenter)
        self.detail.setTextFormat(Qt.PlainText)
        self.action = widgets.button('', on_click=lambda: self._on_action and self._on_action())
        self._on_action = None
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setMaximumWidth(640)
        lay.addWidget(self.title)
        lay.addWidget(self.detail)
        lay.addLayout(widgets.hbox(None, self.action, None))
        lay.addLayout(widgets.hbox(None, self.details, None))
        lay.addStretch(2)

    def show_message(self, title: str, detail: str = '', action: str = '', on_action=None, details: str = ''):
        self.title.setText(title)
        self.detail.setText(detail)
        self.detail.setVisible(bool(detail))
        self._on_action = on_action
        self.action.setText(action)
        self.action.setVisible(bool(action))
        self.details.setPlainText(details)
        self.details.setVisible(bool(details))
        lines = min(8, max(1, details.count('\n') + 1))
        self.details.setFixedHeight(self.details.fontMetrics().lineSpacing() * lines + 16)


class SetsPage(Page):
    title = 'Sets'
    key = 'sets'

    def __init__(self, ctx):
        super().__init__(ctx)
        # Construction does no I/O: the combos fill and the first read starts in on_shown (eng D13).
        self._generation = 0
        self._latest = 0
        self._busy = False
        self._pending = None
        self._focus_choice = None
        self._shown_once = False
        self._filter_installed = False
        self.pinned = False
        self._followed = None  # the last game (character, job, sub) this page tried to follow
        self.read = None
        self.views = []
        self.view_by_path = {}
        self.current_path = ''
        self.current_slot = ''
        self._read_key = None
        self._previous_cells = {}
        self._snapshot_state = 'absent'
        self._items = {}
        self.read_count = 0

        # Toolbar
        self.toolbar = widgets.SearchToolbar('Search sets or items…')
        self.toolbar.search.setAccessibleName('Search sets or items')
        self.character_combo = QComboBox()
        self.character_combo.setAccessibleName('Character')
        self.job_combo = QComboBox()
        self.job_combo.setAccessibleName('Job')
        self.sub_combo = QComboBox()
        self.sub_combo.setAccessibleName('Sub job')
        self.sub_combo.addItems(['None'] + JOBS)
        self.reload_btn = widgets.button('⟳ Reload files', 'ghost', lambda: self.request(force=True),
                                         'Read the Lua files again (F5)')
        self.selector_labels = {}
        for text, combo in (('Character', self.character_combo), ('Main job', self.job_combo), ('Sub job', self.sub_combo)):
            field = QWidget()
            lay = QVBoxLayout(field)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(4)
            caption = widgets.label(text, 'Caption')
            caption.setBuddy(combo)
            combo.setAccessibleName(text)
            lay.addWidget(caption)
            lay.addWidget(combo)
            self.selector_labels[text] = caption
            self.toolbar.add(field)
        self.toolbar.add(self.reload_btn)
        self.character_combo.activated.connect(self._character_picked)
        self.job_combo.activated.connect(lambda _i: self._manual_pick())
        self.sub_combo.activated.connect(lambda _i: self._manual_pick())
        self.toolbar.text_changed.connect(self._filter_tree)

        self.freshness = widgets.label('', 'Caption')
        self.follow_label = widgets.label('', 'Caption')
        self.follow_btn = widgets.button('Follow game', 'ghost', self._follow_game)
        self.follow_label.hide()
        self.follow_btn.hide()

        # Body: a message, or the workspace
        self.body = QStackedWidget()
        self.message = _Message()
        self.workspace = QWidget()
        self.body.addWidget(self.message)
        self.body.addWidget(self.workspace)

        # Tree column
        tree_col = QWidget()
        tree_col.setMinimumWidth(TREE_MIN)
        tl = QVBoxLayout(tree_col)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(6)
        tl.addWidget(widgets.label('From your Lua (read-only)', 'Caption'))
        self.shared_note = widgets.label('', 'Caption', wrap=True)
        self.shared_note.hide()
        tl.addWidget(self.shared_note)
        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderHidden(True)
        self.tree.setTextElideMode(Qt.ElideMiddle)
        self.tree.setIndentation(14)
        self.tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tree.setAccessibleName('Sets')
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tree.currentItemChanged.connect(self._tree_selected)
        tl.addWidget(self.tree, 1)
        self.no_match = QWidget()
        nm = QVBoxLayout(self.no_match)
        nm.setContentsMargins(0, 8, 0, 0)
        self.no_match_label = widgets.label('', 'Caption', wrap=True)
        self.no_match_label.setTextFormat(Qt.PlainText)
        nm.addWidget(self.no_match_label)
        nm.addLayout(widgets.hbox(widgets.button('Clear', 'ghost', lambda: self.toolbar.search.clear()), None))
        nm.addStretch(1)
        self.no_match.hide()
        tl.addWidget(self.no_match, 1)

        # Centre column (scrolls, so 600 px of height works)
        centre = QWidget()
        cl = QVBoxLayout(centre)
        cl.setContentsMargins(4, 0, 4, 0)
        cl.setSpacing(6)
        self.reading = widgets.label('', 'Caption')
        self.reading.setStyleSheet(f'color: {theme.ACCENT};')
        self.reading.hide()
        self.verdict = QLabel()
        self.verdict.setAccessibleName('Verdict')
        self.path_label = QLabel()
        self.path_label.setTextFormat(Qt.PlainText)
        self.path_label.setWordWrap(True)
        self.set_caption = widgets.label('', 'Caption', wrap=True)
        self.strip = QFrame()
        sl = QHBoxLayout(self.strip)
        sl.setContentsMargins(10, 6, 6, 6)
        self.strip_label = widgets.label('', wrap=True)
        self.strip_label.setTextFormat(Qt.PlainText)
        self.strip_details_btn = widgets.button('Details', 'ghost', self._toggle_details)
        self.strip_retry_btn = widgets.button('Retry', 'ghost', lambda: self.request(force=True))
        sl.addWidget(self.strip_label, 1)
        sl.addWidget(self.strip_details_btn)
        sl.addWidget(self.strip_retry_btn)
        self.strip.hide()
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.hide()
        self.grid = EquipGrid(self._scale())
        self.grid.cell_clicked.connect(self._cell_clicked)
        self.grid.cell_context_requested.connect(self._grid_context_menu)
        self.attention_title = QLabel()
        self.attention_rows = []
        self.more_label = widgets.label('', 'Caption')
        for widget in (self.reading, self.verdict, self.path_label, self.set_caption, self.strip, self.details):
            cl.addWidget(widget)
        cl.addSpacing(4)
        cl.addWidget(self.grid)
        cl.addSpacing(8)
        cl.addWidget(self.attention_title)
        for _ in range(4):
            row = _ClickLabel()
            row.clicked.connect(lambda r=row: self._attention_clicked(r))
            row.hide()
            self.attention_rows.append(row)
            cl.addWidget(row)
        cl.addWidget(self.more_label)
        self._analyzer = None
        self.equipment_tabs = None
        self._centre_layout = cl
        cl.addStretch(1)
        self.centre_scroll = QScrollArea()
        self.centre_scroll.setWidgetResizable(True)
        self.centre_scroll.setFrameShape(QFrame.NoFrame)
        self.centre_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # everything wraps; the grid fits
        self.centre_scroll.setWidget(centre)
        centre.setStyleSheet(f'background: {theme.BG};')

        # Detail panel: docked when there's room, else it slides over the centre (design D3)
        self.panel = QFrame()
        self.panel.setObjectName('SetsPanel')
        self.panel.setStyleSheet(f'#SetsPanel {{ background: {theme.BG}; border-left: 1px solid {theme.BORDER}; }}')
        self.panel.setMinimumWidth(PANEL_WIDTH)
        self.panel.setMaximumWidth(PANEL_WIDTH + 80)
        pl = QVBoxLayout(self.panel)
        pl.setContentsMargins(16, 4, 12, 8)
        pl.setSpacing(6)
        self.back_btn = widgets.button('← Back', 'ghost', self._close_panel)
        self.back_btn.hide()
        self.panel_slot = widgets.label('', 'SectionTitle')
        self.panel_name = widgets.label('', wrap=True)
        self.panel_name.setTextFormat(Qt.PlainText)
        self.panel_info = widgets.label('', 'Caption', wrap=True)
        self.panel_info.setTextFormat(Qt.PlainText)
        self.panel_info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.panel_note = widgets.label('', wrap=True)
        self.panel_note.setStyleSheet(f'color: {theme.WARNING}; font-size: {round(12 * self._scale())}px;')
        self.panel_placeholder = widgets.label('Click a slot to see what you own for it.', 'Caption', wrap=True)
        pl.addWidget(self.back_btn, 0, Qt.AlignLeft)
        panel_content = QWidget()
        content_layout = QVBoxLayout(panel_content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        for widget in (self.panel_slot, self.panel_name, self.panel_info, self.panel_note, self.panel_placeholder):
            content_layout.addWidget(widget)
        self.item_links_btn = widgets.button('Current item links ↗')
        self.item_links_btn.setAccessibleName('Wiki links for current item')
        self.item_links_btn.setMenu(QMenu(self.item_links_btn))
        self.open_file_btn = widgets.button('Open job file', on_click=self._open_file)
        content_layout.addWidget(self.item_links_btn, 0, Qt.AlignLeft)
        content_layout.addWidget(self.open_file_btn, 0, Qt.AlignLeft)
        self.source_help = widgets.label('', wrap=True)
        self.source_help.setTextFormat(Qt.PlainText)
        self.source_help.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.source_help.setAccessibleName('Find this slot in your Lua')
        content_layout.addWidget(self.source_help)
        self.replacements = QWidget()
        rl = QVBoxLayout(self.replacements)
        rl.setContentsMargins(0, 8, 0, 0)
        rl.addWidget(widgets.label('Owned replacements', 'SectionTitle'))
        self.replacement_filter = QLineEdit()
        self.replacement_filter.setPlaceholderText('Filter replacements…')
        self.replacement_filter.setAccessibleName('Filter owned replacements')
        self.replacement_filter.textChanged.connect(self._filter_replacements)
        rl.addWidget(self.replacement_filter)
        self.replacement_list = QTreeWidget()
        self.replacement_list.setFrameShape(QFrame.NoFrame)
        self.replacement_list.setColumnCount(2)
        self.replacement_list.setHeaderLabels(['Item', 'Location'])
        self.replacement_list.setHeaderHidden(False)
        self.replacement_list.header().setStretchLastSection(False)
        self.replacement_list.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.replacement_list.header().setSectionResizeMode(1, QHeaderView.Fixed)
        self.replacement_list.setColumnWidth(1, round(100 * self._scale()))
        self.replacement_list.setTextElideMode(Qt.ElideMiddle)
        self.replacement_list.setIndentation(12)
        self.replacement_list.setAccessibleName('Owned replacements')
        self.replacement_list.setMinimumHeight(160)
        self.replacement_list.setMaximumHeight(260)
        self.replacement_list.currentItemChanged.connect(self._replacement_selected)
        rl.addWidget(self.replacement_list)
        self.replacement_details = widgets.label('', 'Caption', wrap=True)
        self.replacement_details.setTextFormat(Qt.PlainText)
        self.replacement_name = widgets.label('', wrap=True)
        self.replacement_name.setTextFormat(Qt.PlainText)
        self.replacement_name.setStyleSheet('font-weight: 600;')
        rl.addWidget(self.replacement_name)
        rl.addWidget(self.replacement_details)
        self.replacement_links_btn = widgets.button('Replacement links ↗')
        self.replacement_links_btn.setAccessibleName('Wiki links for selected replacement')
        self.replacement_links_btn.setMenu(QMenu(self.replacement_links_btn))
        rl.addWidget(self.replacement_links_btn, 0, Qt.AlignLeft)
        self.copy_area = QWidget()
        ca = QVBoxLayout(self.copy_area)
        ca.setContentsMargins(0, 4, 0, 0)
        self.copy_scope = widgets.label('', wrap=True)
        self.copy_scope.setTextFormat(Qt.PlainText)
        self.affected_btn = widgets.button('', 'ghost', self._toggle_affected)
        self.affected_sets = widgets.label('', 'Caption', wrap=True)
        self.affected_sets.setTextFormat(Qt.PlainText)
        self.copy_location = widgets.label('', 'Caption', wrap=True)
        self.copy_location.setTextFormat(Qt.PlainText)
        self.copy_warning = widgets.label('', wrap=True)
        self.copy_warning.setTextFormat(Qt.PlainText)
        self.copy_warning.setStyleSheet(f'color: {theme.WARNING};')
        self.copy_warning.setAccessibleName('Copy availability warning')
        self.snippet = QPlainTextEdit()
        self.snippet.setReadOnly(True)
        self.snippet.setAccessibleName('Copy-paste Lua snippet')
        self.snippet.setFont(QFont('Consolas', 10))
        self.snippet.setFixedHeight(100)
        self.copy_btn = widgets.button('Copy slot line', 'primary', self._copy_fix)
        self.copy_all_btn = widgets.button('', on_click=lambda: self._copy_fix(all_targets=True))
        self.copy_note = widgets.label('This set is in your own Lua, so the app won’t change it. '
                                       'Paste this in place of the current slot line.', 'Caption', wrap=True)
        for widget in (self.copy_scope, self.affected_btn, self.affected_sets, self.copy_location, self.copy_warning, self.snippet,
                       self.copy_btn, self.copy_all_btn, self.copy_note):
            ca.addWidget(widget)
        rl.addWidget(self.copy_area)
        content_layout.addWidget(self.replacements)
        content_layout.addStretch(1)
        panel_scroll = QScrollArea()
        panel_scroll.setWidgetResizable(True)
        panel_scroll.setFrameShape(QFrame.NoFrame)
        panel_scroll.setWidget(panel_content)
        pl.addWidget(panel_scroll, 1)
        self._copy_plan = None
        self._copy_target = None

        self.split = QSplitter(Qt.Horizontal)
        self.split.setChildrenCollapsible(False)
        self.split.addWidget(tree_col)
        self.split.addWidget(self.centre_scroll)
        self.split.setStretchFactor(1, 1)
        self.split.splitterMoved.connect(lambda *_a: self.ctx.settings.set('sets_tree_width', self.split.sizes()[0]))
        wl = QHBoxLayout(self.workspace)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.addWidget(self.split)
        self._wide = None
        self._panel_anim = None
        self.workspace.installEventFilter(self)

        self.layout_.addWidget(self.toolbar)
        self.layout_.addLayout(widgets.hbox(self.freshness, None, self.follow_label, self.follow_btn))
        self.layout_.addWidget(self.body, 1)

        for a, b in ((self.toolbar.search, self.character_combo), (self.character_combo, self.job_combo),
                     (self.job_combo, self.sub_combo), (self.sub_combo, self.reload_btn),
                     (self.reload_btn, self.tree), (self.tree, self.grid)):
            QWidget.setTabOrder(a, b)
        for keys, action in ((QKeySequence.Find, lambda: self.toolbar.search.setFocus(Qt.ShortcutFocusReason)),
                             (QKeySequence(Qt.Key_F5), lambda: self.request(force=True)),
                             (QKeySequence(Qt.Key_Escape), self._close_panel)):
            shortcut = QShortcut(keys, self)
            shortcut.setContext(Qt.WidgetWithChildrenShortcut)
            shortcut.activated.connect(action)

        ctx.inventory_changed.connect(self._inventory_changed)
        self.item_details_shortcut = QShortcut(QKeySequence('Alt+I'), self,
                                             activated=lambda: self.analyzer.show_item(self.grid.focused_slot(), self.grid))
        ctx.windower_changed.connect(self._windower_changed)
        ctx.bridge.state_received.connect(self._game_state)
        self._clear_panel()
        self._labels_styled = False

    # --- helpers ------------------------------------------------------------
    @property
    def analyzer(self):
        # Construction stays cheap for startup/sidebar enumeration. Materialize
        # this consumer at first actual Sets use, before requesting its source.
        if self._analyzer is None:
            self._analyzer = EquipmentAnalyzer(self.ctx, self)
            self._analyzer.attach_grid(self.grid)
            index = self._centre_layout.indexOf(self.attention_title)
            attention_page = QWidget()
            layout = QVBoxLayout(attention_page)
            layout.setContentsMargins(0, 8, 0, 0)
            for widget in (self.attention_title, *self.attention_rows, self.more_label):
                self._centre_layout.removeWidget(widget)
                layout.addWidget(widget)
            self.equipment_tabs = QTabWidget()
            self.equipment_tabs.addTab(attention_page, 'Attention & copy fixes')
            self.equipment_tabs.addTab(self._analyzer, 'Equipment analysis')
            self._centre_layout.insertWidget(index, self.equipment_tabs)
        return self._analyzer

    def _scale(self) -> float:
        try:
            return float(self.ctx.settings.get('text_scale') or 1.0)
        except (TypeError, ValueError):
            return 1.0

    def _apply_label_styles(self) -> None:
        self._labels_styled = True
        scale = self._scale()
        # Keep focus visible even for ghost buttons and trees whose native outline
        # is suppressed by the app theme. Scope this pass to Sets.
        self.setStyleSheet(
            f'QPushButton:focus {{ border: 2px solid {theme.ACCENT}; }}'
            f'QTreeWidget:focus {{ border: 2px solid {theme.ACCENT}; }}'
            f'QMenu::item {{ border: 1px solid transparent; }}'
            f'QMenu::item:selected {{ border: 1px solid {theme.ACCENT}; background: {theme.SURFACE}; '
            f'color: {theme.ACCENT}; }}')
        for tree in (self.tree, self.replacement_list):
            tree.setStyleSheet(
                f'QTreeWidget::item:selected, QTreeWidget::branch:selected {{ '
                f'background: rgba(34, 211, 238, 0.12); color: {theme.ACCENT}; }}')
        for label in (self.panel_info, self.panel_placeholder, self.replacement_details, self.source_help,
                      self.affected_sets, self.copy_location, self.copy_note):
            label.setStyleSheet(f'color: {theme.TEXT}; font-size: {round(14 * scale)}px;')
        self.panel_note.setStyleSheet(f'color: {theme.WARNING}; font-size: {round(14 * scale)}px;')
        self.replacement_list.setColumnWidth(1, round(100 * scale))
        self.snippet.setStyleSheet(
            f'QPlainTextEdit {{ background: {theme.SURFACE_2}; border: 1px solid {theme.BORDER}; border-radius: 6px; '
            f'font-family: Consolas; font-size: {round(14 * scale)}px; }}'
            f'QPlainTextEdit:focus {{ border-color: {theme.ACCENT}; }}')
        self.path_label.setStyleSheet(f'font-size: {round(14 * scale)}px;')
        self.attention_title.setStyleSheet(f'font-size: {round(14 * scale)}px; font-weight: 600;')
        for row in self.attention_rows:
            row.setStyleSheet(f'color: {theme.TEXT}; font-size: {round(13 * scale)}px;')

    def _set_verdict(self, text: str, colour: str) -> None:
        self.verdict.setText(text)
        self.verdict.setStyleSheet(f'font-size: {round(16 * self._scale())}px; font-weight: 600; color: {colour};')

    def _windower(self) -> str:
        return self.ctx.windower_dir or ''

    def _live(self) -> tuple:
        state = self.ctx.bridge.state or {}
        return state.get('player_name', ''), state.get('main_job', ''), state.get('sub_job', '')

    def _context(self) -> tuple:
        job = self.job_combo.currentData() or ''
        sub = self.sub_combo.currentText()
        return self.character_combo.currentText(), job, '' if sub == 'None' else sub

    # --- showing the page -------------------------------------------------
    def on_shown(self) -> None:
        self.analyzer.activate()
        if not self._filter_installed and self.window() is not self:
            self.window().installEventFilter(self)
            self._filter_installed = True
        scale = self._scale()
        if not self._labels_styled or abs(scale - self.grid.scale) > 0.001:
            self.grid.set_scale(scale)
            self._apply_label_styles()
        if not self._shown_once:
            self._shown_once = True
            if self._fill_contexts():
                self.request()
        elif self.read is not None:
            self.request()  # files may have changed; a cache hit costs a few stats

    def eventFilter(self, obj, event):
        if obj is self.workspace and event.type() == QEvent.Resize:
            self._layout_mode()
        elif obj is self.window() and event.type() == QEvent.ActivationChange:
            # Back from pasting in an editor: re-read quietly; unchanged files are a cache hit (design D11).
            if self.window().isActiveWindow() and self.isVisible() and self.read is not None:
                self.request(preserve_replacement=True)
        return False

    def _fill_contexts(self) -> bool:
        """Fill the character and job pickers; show a message and return False when nothing can be read."""
        windower_dir = self._windower()
        if not windower_dir or not os.path.isdir(windower_dir):
            choose = getattr(self.window(), 'choose_windower', None)
            self.message.show_message('Choose your Windower folder in Settings',
                                      'The Sets page reads your GearSwap files from it.',
                                      'Choose folder…' if choose else '', choose)
            self.body.setCurrentWidget(self.message)
            return False
        if not os.path.isdir(gearswap_files.gearswap_dir(windower_dir)):
            self.message.show_message("GearSwap isn't installed.",
                                      "Install GearSwap in Windower's addon list to see your sets here.")
            self.body.setCurrentWidget(self.message)
            return False
        names = {key for key in self.ctx.inventory_snapshot if not key.startswith('Imported: ')}
        live = self._live()
        if live[0]:
            names.add(live[0])
        with_files = gearswap_files.characters_with_files(windower_dir)
        names = sorted(names | with_files, key=str.casefold)
        self.character_combo.blockSignals(True)
        self.character_combo.clear()
        self.character_combo.addItems(names)
        for preferred in (live[0], self.ctx.settings.get('sets_character') or '',
                          next((n for n in names if n in with_files), '')):
            if preferred in names:
                self.character_combo.setCurrentText(preferred)
                break
        self.character_combo.blockSignals(False)
        if not names:
            self.message.show_message('No GearSwap files yet', 'Log in with the Nexus addon running, or add a job '
                                      'file under addons/GearSwap/data.')
            self.body.setCurrentWidget(self.message)
            return False
        return self._fill_jobs()

    def _fill_jobs(self, prefer: str = '', prefer_sub: str = None) -> bool:
        windower_dir = self._windower()
        character = self.character_combo.currentText()
        live = self._live()
        current = self.job_combo.currentData() or ''
        self.job_combo.blockSignals(True)
        self.job_combo.clear()
        first = ''
        for job in JOBS:
            found = gearswap_files.find_job_file(windower_dir, character, job).path
            self.job_combo.addItem(job if found else f'{job} (no file)', job)
            item = self.job_combo.model().item(self.job_combo.count() - 1)
            item.setEnabled(bool(found))
            if found and not first:
                first = job
        same_player = live[0] and live[0].casefold() == character.casefold()
        wanted = [prefer, live[1] if same_player else '', current, first]
        for job in wanted:
            index = self.job_combo.findData(job) if job else -1
            if index >= 0 and self.job_combo.model().item(index).isEnabled():
                self.job_combo.setCurrentIndex(index)
                break
        self.job_combo.blockSignals(False)
        sub = prefer_sub if prefer_sub is not None else (live[2] if same_player and self.job_combo.currentData() == live[1] else None)
        if sub is not None:
            self.sub_combo.setCurrentText(sub if sub in JOBS else 'None')
        if not first:
            dirs = gearswap_files.search_dirs(windower_dir, character)
            self.message.show_message(f'No GearSwap files for {character}', 'GearSwap looks in these folders:',
                                      details='\n'.join(dirs))
            self.body.setCurrentWidget(self.message)
            return False
        return True

    # --- picking ----------------------------------------------------------
    def _character_picked(self, _index) -> None:
        self._clear_panel()
        self.ctx.settings.set('sets_character', self.character_combo.currentText())
        self.pinned = True
        if self._fill_jobs():
            self.request()
        self._update_follow()

    def _manual_pick(self) -> None:
        self.pinned = True
        self.request()
        self._update_follow()

    def _game_state(self, _state: dict) -> None:
        """Follow the game's character and job unless a job was picked by hand (design D12)."""
        name, job, sub = self._live()
        if self._shown_once and not self.pinned and self._copy_target is None and name and job:
            # A game job with no file can't be selected, so the context never matches; follow each game
            # state once instead of re-searching every job file on every update from the game.
            if (name, job, sub) != self._context() and (name, job, sub) != self._followed:
                self._followed = (name, job, sub)
                if self.character_combo.findText(name) < 0:
                    self.character_combo.addItem(name)
                self.character_combo.setCurrentText(name)
                if self._fill_jobs(prefer=job, prefer_sub=sub):
                    self.request()
        self._update_follow()

    def _follow_game(self) -> None:
        self._reset_copy()
        self.pinned = False
        self._followed = None
        self._game_state(self.ctx.bridge.state or {})

    def _update_follow(self) -> None:
        name, job, sub = self._live()
        differs = bool(name and job) and (name, job, sub) != self._context()
        show = self.pinned and differs
        self.follow_label.setText(f'Game is on {job}/{sub} ·' if sub else f'Game is on {job} ·')
        self.follow_label.setVisible(show)
        self.follow_btn.setVisible(show)

    # --- reading ----------------------------------------------------------
    def request(self, force: bool = False, *, preserve_replacement: bool = False) -> None:
        """Read the picked job. One read at a time; requests made meanwhile collapse to the latest (eng D15)."""
        character, job, sub = self._context()
        if not character or not job:
            return
        self.analyzer.invalidate()
        key = (self._windower(), character, job, sub)
        choice = None
        if preserve_replacement and not force and key == self._read_key and self._copy_target is not None:
            entry = self.replacement_list.currentItem()
            view = self.view_by_path.get(self.current_path)
            row = entry.data(0, Qt.UserRole) if entry is not None else None
            if row and view:
                choice = (key, self.current_path, self.current_slot, view.set_read.pieces.get(self.current_slot),
                          row, dict(self.read.files), self.read.path)
        self._focus_choice = choice
        self._reset_copy()
        self.replacements.setEnabled(False)
        self.open_file_btn.setEnabled(False)
        self._generation += 1
        self._latest = self._generation
        args = {'windower_dir': self._windower(), 'character': character, 'job': job, 'sub_job': sub,
                'force': force}
        same = self.read is not None and key == self._read_key
        found = gearswap_files.find_job_file(self._windower(), character, job).path
        reading = f'Reading {os.path.basename(found or "")}…'
        if same:
            self.grid.set_dimmed(True)
            self.reading.setText(reading)
            self.reading.show()
        else:
            self._clear_panel()
            if self.read is None or self.body.currentWidget() is self.message:
                self.message.show_message(reading)
                self.body.setCurrentWidget(self.message)
            else:
                self.grid.set_dimmed(True)
                self.reading.setText(reading)
                self.reading.show()
        if self._busy:
            self._pending = (self._generation, args)
            return
        self._start(self._generation, args)

    def _start(self, generation: int, args: dict) -> None:
        self._busy = True
        self.read_count += 1
        task = _ReadTask(generation, args)
        task.signals.done.connect(self._read_done)
        QThreadPool.globalInstance().start(task)

    def _read_done(self, generation: int, read) -> None:
        self._busy = False
        if generation == self._latest:  # older answers are dropped (a later pick, a Reload)
            self._apply(read)
        if self._pending:
            generation, args = self._pending
            self._pending = None
            self._start(generation, args)

    def _apply(self, read) -> None:
        choice, self._focus_choice = self._focus_choice, None
        self._reset_copy()
        self.reading.hide()
        self.grid.set_dimmed(False)
        key = (self._windower(), read.character, read.job, read.sub_job)
        same_context = key == self._read_key
        self._read_key = key
        self.read = read
        self._update_freshness()
        if read.error == gearswap_reader.NO_FILE:
            self.message.show_message(f"No GearSwap file for {read.character}'s {read.job}",
                                      'GearSwap looks in these folders:',
                                      details='\n'.join(gearswap_files.search_dirs(self._windower(), read.character)))
            self.body.setCurrentWidget(self.message)
            return
        if read.error and not read.partial:
            name = os.path.basename(read.path)
            self.message.show_message(f"Couldn't read {name}: {read.error}", 'Other jobs still work.', 'Retry',
                                      lambda: self.request(force=True), read.error_details or read.error)
            self.body.setCurrentWidget(self.message)
            return
        self.body.setCurrentWidget(self.workspace)
        if not same_context:
            self._previous_cells = {}
            self.current_path = ''
            self.current_slot = ''
        self._recompute(keep=same_context)
        self._update_open_file()
        if choice and same_context:
            old_key, path, slot, old_piece, row, files, job_file = choice
            view = self.view_by_path.get(path)
            if (old_key == key and read.path == job_file and read.files == files and self.current_path == path
                    and self.current_slot == slot and view and view.set_read.pieces.get(slot) == old_piece):
                for i in range(self.replacement_list.topLevelItemCount()):
                    group = self.replacement_list.topLevelItem(i)
                    for j in range(group.childCount()):
                        entry = group.child(j)
                        if entry.data(0, Qt.UserRole) == row:
                            self.replacement_list.setCurrentItem(entry)
                            return

    def _recompute(self, keep: bool = True) -> None:
        """Statuses from the snapshot; no Lua runs here."""
        if self.read is None or self.body.currentWidget() is not self.workspace:
            return
        self.views = set_manager.build_views(self.read, self.ctx.inventory_snapshot, self._windower())
        self.view_by_path = {view.set_read.path: view for view in self.views}
        state = set_manager.snapshot_state(self.ctx.inventory_snapshot, self.read.character)
        self._snapshot_state = state
        self.shared_note.setText(f'Uses {os.path.basename(self.read.path)}, shared with other jobs.')
        self.shared_note.setVisible(self.read.shared_file)
        self._fill_tree()
        path = self.current_path if keep and self.current_path in self.view_by_path else ''
        if not path:  # first set needing attention in tree order, else the first set (design D8)
            order = {purpose: i for i, purpose in enumerate(set_manager.PURPOSE_ORDER)}
            ordered = sorted(self.views, key=lambda v: order.get(v.purpose, len(order)))
            attention = [v for v in ordered if v.attention and not v.set_read.empty_in_file]
            pool = attention or [v for v in ordered if not v.set_read.empty_in_file] or ordered
            path = pool[0].set_read.path if pool else ''
        self._select_path(path)
        self._update_strip()

    def _inventory_changed(self) -> None:
        self._recompute(keep=True)
        self._update_freshness()

    def _windower_changed(self, _path: str) -> None:
        self.analyzer.invalidate('Equipment source changed')
        if self._shown_once:
            self.analyzer.activate()
        self._focus_choice = None
        self._clear_panel()
        self._generation += 1
        self._latest = self._generation
        self._pending = None
        gearswap_reader.clear_cache()
        item_res.clear()
        self.read = None
        self._read_key = None
        if self._shown_once and self._fill_contexts():
            self.request()

    def _update_freshness(self) -> None:
        parts = []
        if self.read is not None and self.read.read_at:
            parts.append(f'Lua read {relative_time(self.read.read_at)}')
        character = self.character_combo.currentText()
        updated = (self.ctx.settings.get('inventory_updated') or {}).get(character)
        if updated:
            parts.append('Inventory from ' + time.strftime('%d %b %H:%M', time.localtime(float(updated))))
        else:
            parts.append('No inventory yet')
        self.freshness.setText(' · '.join(parts))

    def _update_strip(self) -> None:
        """One status strip, in priority order: read incomplete > no snapshot > empty snapshot (design D9)."""
        details = ''
        if self.read is not None and self.read.partial:
            text, colour, tint = 'Read incomplete: some sets may be missing', theme.WARNING, 'rgba(245, 158, 11, 0.08)'
            details = f'{self.read.error}\n\n{self.read.error_details}'.strip()
        elif self._snapshot_state == 'absent':
            text, colour, tint = 'Log in with the Nexus addon running to see what you own', theme.FAINT, theme.SURFACE
        elif self._snapshot_state == 'empty':
            text, colour, tint = f'No items recorded for {self.read.character}.', theme.FAINT, theme.SURFACE
        else:
            self.strip.hide()
            self.details.hide()
            return
        self.strip_label.setText(text)
        self.strip_label.setStyleSheet(f'color: {colour}; background: transparent;')
        self.strip.setStyleSheet(f'background: {tint}; border-radius: 6px;')
        self.strip_details_btn.setVisible(bool(details))
        self.strip_retry_btn.setVisible(bool(details))
        self.details.setPlainText(details)
        lines = min(8, max(2, details.count('\n') + 1))
        self.details.setFixedHeight(self.details.fontMetrics().lineSpacing() * lines + 16)
        if not details:
            self.details.hide()
        self.strip.show()

    def _toggle_details(self) -> None:
        self.details.setVisible(not self.details.isVisible())

    # --- tree -------------------------------------------------------------
    def _fill_tree(self) -> None:
        self.tree.blockSignals(True)
        self.tree.clear()
        self._items = {}
        groups = {}
        for view in self.views:
            groups.setdefault(view.purpose, []).append(view)
        bold = QFont(self.tree.font())
        bold.setWeight(QFont.DemiBold)
        for purpose in set_manager.PURPOSE_ORDER:
            members = groups.get(purpose)
            if not members:
                continue
            group = QTreeWidgetItem([f'{purpose} ({len(members)})'])
            group.setFont(0, bold)
            group.setFlags(Qt.ItemIsEnabled)
            group.setData(0, PATH_ROLE, '')
            self.tree.addTopLevelItem(group)
            for view in members:
                path = view.set_read.path
                text = short_path(path) + (' (empty in file)' if view.set_read.empty_in_file else '')
                item = QTreeWidgetItem([text])
                item.setData(0, PATH_ROLE, path)
                item.setToolTip(0, path)
                item.setData(0, Qt.AccessibleTextRole, path)
                group.addChild(item)
                self._items[path] = item
                if view.attention:
                    item.setText(1, f'⚠ {view.attention}')
                    item.setForeground(1, QColor(theme.WARNING))
                    item.setTextAlignment(1, Qt.AlignRight | Qt.AlignVCenter)
                    item.setToolTip(1, f'{view.attention} slots need attention')
                upgrades = sum(bool(rows) for rows in view.upgrades.values())
                if upgrades:
                    item.setText(2, f'↑ {upgrades}')
                    item.setForeground(2, QColor(theme.GOLD))
                    item.setToolTip(2, f'{upgrades} slots have a higher tier owned')
                for alias in view.set_read.aliases:
                    alias_item = QTreeWidgetItem([f'↪ {short_path(alias)}'])
                    alias_item.setData(0, PATH_ROLE, path)
                    alias_item.setData(0, ALIAS_ROLE, alias)
                    alias_item.setToolTip(0, f'{alias} (same as {path})')
                    alias_item.setData(0, Qt.AccessibleTextRole, f'{alias}, same as {path}')
                    alias_item.setForeground(0, self.palette().placeholderText())
                    group.addChild(alias_item)
            group.setExpanded(True)
        self.tree.blockSignals(False)
        self._filter_tree(self.toolbar.search.text())

    def _filter_tree(self, text: str) -> None:
        needle = (text or '').strip().casefold()
        any_visible = False
        for i in range(self.tree.topLevelItemCount()):
            group = self.tree.topLevelItem(i)
            visible = 0
            for j in range(group.childCount()):
                item = group.child(j)
                path = item.data(0, PATH_ROLE)
                view = self.view_by_path.get(path)
                alias = item.data(0, ALIAS_ROLE) or ''
                haystack = [path, alias] + (view.set_read.aliases if view else []) + [
                    piece.name for piece in (view.set_read.pieces.values() if view else [])]
                match = not needle or any(needle in str(h).casefold() for h in haystack)
                item.setHidden(not match)
                visible += match
            group.setHidden(visible == 0)
            if needle and visible:
                group.setExpanded(True)
            any_visible = any_visible or visible > 0
        empty = bool(needle) and not any_visible
        self.no_match_label.setText(f'No set or item matches "{text.strip()}"')
        self.no_match.setVisible(empty)
        self.tree.setVisible(not empty)

    def _tree_selected(self, item, _previous=None) -> None:
        if item is None:
            return
        path = item.data(0, PATH_ROLE)
        if not path:
            return
        if item.data(0, ALIAS_ROLE):  # an alias row selects its canonical set
            canonical = self._items.get(path)
            if canonical is not None:
                self.tree.setCurrentItem(canonical)
                return
        self._show_set(path)

    def _select_path(self, path: str) -> None:
        item = self._items.get(path) if hasattr(self, '_items') else None
        if item is not None:
            self.tree.blockSignals(True)
            self.tree.setCurrentItem(item)
            self.tree.blockSignals(False)
            self.tree.scrollToItem(item)
        self._show_set(path)

    # --- centre -----------------------------------------------------------
    def _show_set(self, path: str) -> None:
        view = self.view_by_path.get(path)
        changed_set = path != self.current_path
        self.current_path = path
        if self.read is not None and not self._busy and (self._windower(), *self._context()) == self._read_key:
            self.analyzer.set_selection(self.read, path)
        else:
            self.analyzer.invalidate()
        if view is None:
            self.grid.set_cells({})
            self._set_verdict('', theme.TEXT)
            self.path_label.clear()
            self.set_caption.clear()
            return
        set_read = view.set_read
        cells = {slot: cell_for(slot, status) for slot, status in view.statuses.items()}
        for slot, rows in view.upgrades.items():
            if rows:
                cells[slot].badge = '↑'
                cells[slot].accessible_name = describe(cells[slot])
        previous = self._previous_cells.get(path)
        if previous is not None:
            for slot, cell in cells.items():
                old = previous.get(slot)
                cell.changed = old is not None and old != (cell.name, cell.state, cell.caption)
        self._previous_cells[path] = {slot: (c.name, c.state, c.caption) for slot, c in cells.items()}
        self.grid.set_cells(cells)

        if self._snapshot_state == 'absent':
            self._set_verdict('No inventory snapshot', theme.FAINT)
        elif set_read.empty_in_file:
            self._set_verdict('No pieces in the file', theme.FAINT)
        elif view.attention:
            self._set_verdict(f'⚠ {view.attention} need attention', theme.WARNING)
        else:
            self._set_verdict('✓ All pieces owned', theme.GOLD)
        self.verdict.setAccessibleDescription(self.verdict.text())
        aliases = ', '.join(short_path(a) for a in set_read.aliases)
        self.path_label.setText(short_path(set_read.path) + (f' · also called {aliases}' if aliases else ''))
        caption = [view.purpose, os.path.basename(self.read.path), f'{view.filled}/16 set']
        upgrades = sum(bool(rows) for rows in view.upgrades.values())
        if upgrades:
            caption.append(f'{upgrades} upgrade' + ('s' if upgrades != 1 else ''))
        if set_read.empty_in_file:
            caption.append('No pieces in the file. This job may pick gear at runtime.')
        self.set_caption.setText(' · '.join(caption))

        attention = [(slot, status) for slot, status in view.statuses.items() if status.kind in set_manager.ATTENTION]
        self.attention_title.setText(f'Needs attention · {len(attention)}')
        self.attention_title.setVisible(bool(attention))
        for row, entry in zip(self.attention_rows, attention[:4] + [None] * 4):
            if entry is None:
                row.hide()
                continue
            slot, status = entry
            row.slot = slot
            row.setText(attention_sentence(slot, status, self.read.character))
            row.show()
        self.more_label.setText(f'+{len(attention) - 4} more')
        self.more_label.setVisible(len(attention) > 4)

        slot = self.current_slot if not changed_set and self.current_slot else ''
        if slot:
            self.grid.select(slot)
            self._show_slot(slot)
        else:
            self.grid.select('')
            self._clear_panel()

    def _attention_clicked(self, row) -> None:
        slot = getattr(row, 'slot', '')
        if slot:
            self.grid.select(slot)
            self._cell_clicked(slot)

    # --- panel ------------------------------------------------------------
    def _cell_clicked(self, slot: str) -> None:
        self.current_slot = slot
        self.analyzer.selected_slot = slot
        self._show_slot(slot)
        if not self._wide:
            self._open_panel()

    def _item_for_slot(self, slot):
        view = self.view_by_path.get(self.current_path)
        piece = view.set_read.pieces.get(slot) if view else None
        if not piece or piece.empty or not piece.name:
            return None
        game = set_manager.GameData.load(self._windower())
        ids, _problem = set_manager.resolve(piece, game, self.read.job)
        item = game.items[ids[0]] if len(ids) == 1 else None
        return {'name': item.en if item else piece.name, 'item_id': item.id if item else None}

    def _grid_context_menu(self, slot, global_pos):
        if self.read is None or self._busy or (self._windower(), *self._context()) != self._read_key:
            return
        row = self._item_for_slot(slot)
        self.grid.select(slot)
        if slot != self.current_slot:
            self.current_slot = slot
            self._show_slot(slot)
        if row:
            menu = QMenu(self)
            menu.addAction('Item details (Alt+I)', lambda: self.analyzer.show_item(slot, self.grid))
            add_open_actions(menu, self.ctx, row)
            menu.exec(global_pos)
            menu.deleteLater()

    def _clear_panel(self) -> None:
        self._reset_copy()
        self.item_links_btn.hide()
        self.item_links_btn.menu().clear()
        self.replacements.hide()
        self.current_slot = ''
        for widget in (self.panel_slot, self.panel_name, self.panel_info, self.panel_note):
            widget.clear()
            widget.hide()
        self.source_help.clear()
        self.source_help.hide()
        self.panel_placeholder.show()
        if self._wide is False and self.panel.isVisible():
            self.panel.hide()

    def _show_slot(self, slot: str) -> None:
        self._reset_copy()
        view = self.view_by_path.get(self.current_path)
        if view is None:
            return
        status = view.statuses[slot]
        piece = status.piece
        self.panel_placeholder.hide()
        self.panel_slot.setText(SLOT_LABELS[slot])
        self.panel_slot.show()
        if status.kind == 'not_set':
            self.panel_name.setText('Not specified in this set')
        elif status.kind == 'empty':
            self.panel_name.setText('Unequip (set to empty)')
        else:
            word = {'owned': 'owned', 'unreachable': 'stored', 'missing': 'missing', 'other_character': 'other character',
                    'unknown': 'not in game data', 'no_snapshot': 'no snapshot'}[status.kind]
            self.panel_name.setText(f'{piece.name} · {word}')
        self.panel_name.show()
        info = []
        if piece and piece.augments:
            info.append('Augments:')
            info.extend(f'  {aug}' for aug in piece.augments)
        if piece and piece.bag:
            info.append(f'Must be in {piece.bag} (bag="{piece.bag}")')
        if piece and piece.priority is not None:
            info.append(f'Priority {piece.priority}')
        if status.kind == 'owned':
            info.append(f'In {status.bag}')
        elif status.kind == 'unreachable':
            info.append(f'Stored {"on a storage slip" if status.detail == "on a slip" else "in " + status.bag}: '
                        "GearSwap can't equip it from there")
        elif status.detail and status.kind not in ('empty', 'not_set'):
            info.append(f'Status: {status.detail}')
        if piece and piece.inherited_from:
            info.append(f'Comes from {piece.inherited_from} through set_combine.')
            if piece.origin_path and piece.origin_path != piece.inherited_from:
                info.append(f'Defined in {piece.origin_path}. Change it there.')
        if piece and piece.shared_count > 1:
            info.append(f'Defined once and reused in {piece.shared_count} slots.')
        if piece:
            info.append(f'Written as {piece.original_key}= in your Lua.')
        self.panel_info.setText('\n'.join(info))
        self.panel_info.setVisible(bool(info))
        self.panel_note.setText(f'Requirements unverified: {status.note}' if status.note else '')
        self.panel_note.setVisible(bool(status.note))
        self._set_item_links(self.item_links_btn, self._item_for_slot(slot))
        self._fill_replacements(view, slot)

    def _set_item_links(self, button, row):
        button.menu().clear()
        button.setVisible(bool(row and row.get('name')))
        if row and row.get('name'):
            add_open_actions(button.menu(), self.ctx, row)

    def _reset_copy(self):
        self._copy_plan = None
        self._copy_target = None
        self.copy_area.hide()
        self.copy_btn.setEnabled(False)
        self.copy_all_btn.setEnabled(False)
        self._update_open_file()
        self.snippet.clear()
        self.replacement_name.clear()
        self.replacement_name.hide()
        self.copy_warning.clear()
        self.copy_warning.hide()
        self._set_item_links(self.replacement_links_btn, None)

    def _fill_replacements(self, view, slot):
        self.replacements.setVisible(self._snapshot_state != 'absent')
        self.replacements.setEnabled(not self._busy and not self.reading.isVisible())
        self.replacement_filter.blockSignals(True)
        self.replacement_filter.clear()
        self.replacement_filter.blockSignals(False)
        self.replacement_list.clear()
        self.replacement_details.clear()
        if self._snapshot_state == 'absent':
            return
        game = set_manager.GameData.load(self._windower())
        job_id = game.job_ids.get(self.read.job)
        upgrades = view.upgrades.get(slot, [])
        upgrade_ids = {row['item_id'] for row in upgrades}
        groups = {name: [] for name in ('Higher tier owned', 'In your wardrobes', 'Stored', 'On other characters')}
        for character, rows in self.ctx.inventory_snapshot.items():
            if character.startswith('Imported: '):
                continue
            for raw in rows or []:
                item = game.items.get(raw.get('item_id'))
                if not item or not item_res.fits(item, slot) or (job_id is not None and not item_res.wearable(item, job_id)):
                    continue
                row = {**raw, 'name': item.en, 'character': character}
                own = character.casefold() == self.read.character.casefold()
                group = ('On other characters' if not own else 'Higher tier owned' if row['item_id'] in upgrade_ids else
                         'In your wardrobes' if set_manager.reachable(row.get('bag', '')) else 'Stored')
                groups[group].append(row)
        count = sum(len(rows) for rows in groups.values())
        self.replacement_filter.setVisible(count > 8)
        for name, rows in groups.items():
            if not rows:
                continue
            other = name == 'On other characters'
            group = QTreeWidgetItem([f'{name} ({len(rows)})' if other else name])
            group.setFlags(Qt.ItemIsEnabled)
            self.replacement_list.addTopLevelItem(group)
            group.setFirstColumnSpanned(True)
            group.setExpanded(not other)
            if name == 'Higher tier owned':
                group.setForeground(0, QColor(theme.GOLD))
            ordered = sorted(rows, key=lambda r: (-set_manager._tier(r['name'])[1] if name == 'Higher tier owned' else 0,
                                                   not set_manager.reachable(r.get('bag', '')),
                                                   r['name'].casefold(), r.get('bag', '')))
            for row in ordered:
                augs = set_manager.split_augments(row.get('augments', ''))
                caption = row.get('bag', '')
                if other:
                    caption = row['character'] + ' · ' + caption
                entry = QTreeWidgetItem([row['name'] + ('  ↑' if name == 'Higher tier owned' else ''), caption])
                item_font = QFont(self.replacement_list.font())
                item_font.setWeight(QFont.DemiBold)
                entry.setFont(0, item_font)
                location_font = QFont(self.replacement_list.font())
                location_font.setPixelSize(round(12 * self._scale()))
                entry.setFont(1, location_font)
                entry.setForeground(1, QColor(theme.MUTED))
                entry.setData(0, Qt.UserRole, row)
                tooltip = '\n'.join([row['name'], caption, *augs])
                entry.setToolTip(0, tooltip)
                entry.setToolTip(1, tooltip)
                entry.setData(0, Qt.AccessibleTextRole, tooltip)
                group.addChild(entry)
        if not count:
            self.replacement_details.setText(f'No items recorded for {self.read.character}.' if self._snapshot_state == 'empty'
                                             else 'No owned replacements for this slot and job.')

    def _filter_replacements(self, text):
        self._reset_copy()
        self.replacement_list.setCurrentItem(None)
        self.replacement_details.clear()
        for i in range(self.replacement_list.topLevelItemCount()):
            group = self.replacement_list.topLevelItem(i)
            visible = 0
            for j in range(group.childCount()):
                entry = group.child(j)
                match = text.casefold() in entry.toolTip(0).casefold()
                entry.setHidden(not match)
                visible += match
            group.setHidden(not visible)
            if text and visible:
                group.setExpanded(True)

    def _replacement_selected(self, entry, _previous=None):
        self._reset_copy()
        self.replacement_details.clear()
        if entry is None:
            return
        row = entry.data(0, Qt.UserRole)
        if not row:
            return
        self.replacement_name.setText(row['name'])
        self.replacement_name.show()
        self._set_item_links(self.replacement_links_btn, row)
        game = set_manager.GameData.load(self._windower())
        details = [part for part in [row.get('bag', ''), *set_manager.split_augments(row.get('augments', ''))] if part]
        note = set_manager._requirements_note([row['item_id']], game)
        if note:
            details.append('Requirements unverified: ' + note)
        if not set_manager.reachable(row.get('bag', '')):
            details.append(f'Move from {row.get("bag", "storage")} before use')
        own = row['character'].casefold() == self.read.character.casefold()
        if not own:
            details.append(f'On {row["character"]}; this copy is not available here.')
        self.replacement_details.setText('\n'.join(details))
        if not own or self._busy or not self.replacements.isEnabled():
            return
        view = self.view_by_path.get(self.current_path)
        piece = view.set_read.pieces.get(self.current_slot) if view else None
        if piece is None or piece.empty:
            return
        ids, problem = set_manager.resolve(piece, game, self.read.job)
        if problem not in ('', 'unknown') or (not problem and len(ids) != 1):
            self.replacement_details.setText(self.replacement_details.text() + '\nCurrent item is unresolved; no copy fix available.')
            return
        try:
            plan = (set_manager.slot_fix_plan(self.read, view.set_read, piece, row, game) if problem == 'unknown' else
                    set_manager.fix_plan(self.read, ids[0], set_manager.augment_key(piece.augments), row, game))
        except ValueError as error:
            self.replacement_details.setText(self.replacement_details.text() + '\n' + str(error))
            return
        target = next((t for t in plan.targets if self.current_path in t.affected_sets and
                       (t.slot == self.current_slot or t.key == ('table', piece.table_id))), None)
        if target is None:
            return
        if target.blocked_reason:
            self.replacement_details.setText(self.replacement_details.text() + '\n' + target.blocked_reason)
            return
        self._copy_plan, self._copy_target = plan, target
        shared = target.key[0] == 'table'
        override = problem == 'unknown' and bool(piece.inherited_from)
        file = os.path.basename(target.location.file) if target.location.verified else 'your Lua file'
        scope = (f'Add slot override in {short_path(target.path)} · affects {len(target.affected_sets)} sets' if override else
                 f'Replace shared table · affects {len(target.affected_sets)} sets' if shared else
                 f'Fix at root {short_path(target.path)} · fixes {len(target.affected_sets)} sets' if len(target.affected_sets) > 1 else
                 f'Replace 1 slot line in {file}')
        self.copy_scope.setText(scope)
        self.affected_btn.setText(f'Affected sets ({len(target.affected_sets)}) ▸')
        self.affected_btn.setVisible(len(target.affected_sets) > 1)
        self.affected_sets.setText('\n'.join(target.affected_sets))
        self.affected_sets.hide()
        if target.location.verified:
            location = f'{file}, line {target.location.line}'
        else:
            location = f'Location ambiguous · search for {target.path or piece.name}'
            for filename, line in target.location.candidates[:5]:
                location += f'\n{os.path.basename(filename)}:{line}'
        self.copy_location.setText(location)
        self.snippet.setPlainText(target.snippet)
        self.copy_btn.setText('Copy table' if shared else 'Copy slot line')
        self.copy_btn.setEnabled(True)
        self._update_open_file()
        count = len(plan.copyable_targets)
        self.copy_all_btn.setText(f'Copy {count} snippets')
        self.copy_all_btn.setVisible(count > 1)
        self.copy_all_btn.setEnabled(count > 1)
        self.copy_note.setText('This set is in your own Lua, so the app won’t change it. ' +
                               (f'Add this field to {target.path}’s table or set_combine override table. '
                                'Leave the shared root unchanged.' if override else
                                'Replace the whole table after the shared definition’s =.' if shared else
                                'Replace the entire current slot entry, including any multiline item table.'))
        blocked = len(plan.targets) - count
        if blocked:
            self.copy_note.setText(self.copy_note.text() + f' {blocked} other edit location(s) need a reachable copy.')
        rows = [r for character, inventory in self.ctx.inventory_snapshot.items()
                if character.casefold() == self.read.character.casefold() for r in inventory or []]
        single_shortages = set_manager.copy_shortages(self.read, [target], row, rows, game)
        bulk_shortages = set_manager.copy_shortages(self.read, plan.copyable_targets, row, rows, game)
        warnings = []
        if single_shortages:
            warnings.append('Copy warning: ' + '\n'.join(single_shortages))
        extra = [message for message in bulk_shortages if message not in single_shortages]
        if extra:
            warnings.append('Copy all warning: ' + '\n'.join(extra))
        self.copy_warning.setText('\n'.join(warnings))
        self.copy_warning.setVisible(bool(warnings))
        self.copy_area.show()

    def _toggle_affected(self):
        self.affected_sets.setVisible(self.affected_sets.isHidden())

    def _copy_fix(self, all_targets=False):
        if (self._copy_target is None or self._busy or not self.replacements.isEnabled()
                or (self._windower(), *self._context()) != self._read_key):
            return
        QApplication.clipboard().setText(self._copy_plan.text() if all_targets else self._copy_target.snippet)
        targets = self._copy_plan.copyable_targets if all_targets else [self._copy_target]
        files = list(dict.fromkeys(os.path.basename(t.location.file) for t in targets if t.location.verified))
        destination = ', '.join(files) if all(t.location.verified for t in targets) else 'your Lua file (search the locations shown)'
        self.status(f'Copied: paste each snippet at its listed location in {destination}, then //gs reload' if all_targets else
                    f'Copied: paste into {destination}, then //gs reload')

    def _open_file_path(self):
        if self.read is None or (self._windower(), *self._context()) != self._read_key:
            return ''
        path = (self._copy_target.location.file if self._copy_target and self._copy_target.location.verified else
                self.read.path)
        return path if path and os.path.isfile(path) else ''

    def _update_open_file(self):
        path = self._open_file_path()
        source = bool(self._copy_target and self._copy_target.location.verified)
        self.open_file_btn.setText('Open source file' if source else 'Open job file')
        self.open_file_btn.setToolTip(path or 'No readable job file for the current selection')
        self.open_file_btn.setEnabled(bool(path) and not self._busy and not self.reading.isVisible())
        # File associations cannot promise a jump to a line. Keep the search
        # instructions in the inspector so they remain available beside an editor.
        view = self.view_by_path.get(self.current_path)
        piece = view.set_read.pieces.get(self.current_slot) if view else None
        help_text = ''
        if piece is not None:
            target = self._copy_target
            shared = target and target.key[0] == 'table'
            search_path = ((target.path or piece.name) if target else
                           (piece.origin_path or piece.inherited_from or self.current_path))
            help_text = f'In your editor, press Ctrl+F and search for:\n{search_path}'
            if shared:
                help_text += '\nFind the shared item table definition.'
            else:
                help_text += f'\nThen find {piece.original_key}= '
                help_text += f'({piece.name}).' if piece.name else 'in that table.'
            if target and target.location.verified:
                help_text += f'\nSource: {os.path.basename(target.location.file)}, line {target.location.line}.'
            elif target:
                help_text += '\nLocation ambiguous: check the candidate locations below before pasting.'
        self.source_help.setText(help_text)
        self.source_help.setVisible(bool(help_text))

    def _open_file(self):
        path = self._open_file_path()
        if path and not self._busy:
            try:
                self.ctx.edit_file(path)  # never 'open': that can run the Lua (see AppContext.edit_file)
            except OSError as error:
                self.status(f'Couldn’t open file: {error}')

    # --- wide / narrow layout ---------------------------------------------
    def _layout_mode(self) -> None:
        saved = self.ctx.settings.get('sets_tree_width')
        saved = int(saved) if isinstance(saved, (int, float)) and saved >= TREE_MIN else 0
        tree_width = saved or TREE_MIN
        wide = self.workspace.width() >= tree_width + self.grid.width() + PANEL_WIDTH + 48
        if wide != self._wide:
            self._wide = wide
            if wide:
                self.back_btn.hide()
                self.panel.setParent(None)
                self.split.addWidget(self.panel)
                self.split.setStretchFactor(2, 0)
                self.panel.show()
            else:
                self.panel.setParent(self.workspace)
                self.back_btn.show()
                self.panel.hide()
        if not wide:
            self._place_overlay()
        # Until the splitter is dragged (sets_tree_width), the tree takes the room the grid doesn't need.
        room = self.workspace.width() - self.grid.width() - 48 - (PANEL_WIDTH if wide else 0)
        width = saved or max(TREE_MIN, min(320, room))
        rest = max(100, self.workspace.width() - width - (PANEL_WIDTH if wide else 0))
        self.split.blockSignals(True)
        self.split.setSizes([width, rest] + ([PANEL_WIDTH] if wide else []))
        self.split.blockSignals(False)

    def _place_overlay(self) -> None:
        width = min(PANEL_WIDTH + 40, self.workspace.width())
        self.panel.setGeometry(self.workspace.width() - width, 0, width, self.workspace.height())

    def _open_panel(self) -> None:
        self._place_overlay()
        end = self.panel.pos()
        self.panel.move(end + QPoint(self.panel.width(), 0))
        self.panel.show()
        self.panel.raise_()
        self._panel_anim = QPropertyAnimation(self.panel, b'pos', self)
        self._panel_anim.setDuration(160)
        self._panel_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._panel_anim.setStartValue(self.panel.pos())
        self._panel_anim.setEndValue(end)
        self._panel_anim.start()

    def _close_panel(self) -> None:
        if self._wide is False and self.panel.isVisible():
            self.panel.hide()
            self.grid.setFocus(Qt.ShortcutFocusReason)
