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
    QAbstractItemView, QComboBox, QFrame, QHBoxLayout, QHeaderView, QLabel, QPlainTextEdit, QScrollArea, QSplitter,
    QStackedWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from ...core import gearswap_files, gearswap_reader, item_res, set_manager
from ...core.jobs import ALL_FFXI_JOBS
from .. import theme, widgets
from ..equip_grid import SLOT_LABELS, CellData, EquipGrid, describe
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
        self._shown_once = False
        self._filter_installed = False
        self.pinned = False
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
        self.toolbar.add(self.character_combo, self.job_combo, self.sub_combo, self.reload_btn)
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
        self.tree.setColumnCount(2)
        self.tree.setHeaderHidden(True)
        self.tree.setTextElideMode(Qt.ElideMiddle)
        self.tree.setIndentation(14)
        self.tree.setStyleSheet(  # the selected row reads as selected even when the tree has no focus
            f'QTreeWidget::item:selected, QTreeWidget::branch:selected {{ background: rgba(34, 211, 238, 0.12); '
            f'color: {theme.ACCENT}; }}')
        self.tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tree.setAccessibleName('Sets')
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
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
        for widget in (self.panel_slot, self.panel_name, self.panel_info, self.panel_note, self.panel_placeholder):
            pl.addWidget(widget)
        pl.addStretch(1)

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
        ctx.windower_changed.connect(self._windower_changed)
        ctx.bridge.state_received.connect(self._game_state)
        self._clear_panel()
        self._apply_label_styles()

    # --- helpers ------------------------------------------------------------
    def _scale(self) -> float:
        try:
            return float(self.ctx.settings.get('text_scale') or 1.0)
        except (TypeError, ValueError):
            return 1.0

    def _apply_label_styles(self) -> None:
        scale = self._scale()
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
        if not self._filter_installed and self.window() is not self:
            self.window().installEventFilter(self)
            self._filter_installed = True
        scale = self._scale()
        if abs(scale - self.grid.scale) > 0.001:
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
                self.request()
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
        if self._shown_once and not self.pinned and name and job:
            if (name, job, sub) != self._context():
                if self.character_combo.findText(name) < 0:
                    self.character_combo.addItem(name)
                self.character_combo.setCurrentText(name)
                if self._fill_jobs(prefer=job, prefer_sub=sub):
                    self.request()
        self._update_follow()

    def _follow_game(self) -> None:
        self.pinned = False
        self._game_state(self.ctx.bridge.state or {})

    def _update_follow(self) -> None:
        name, job, sub = self._live()
        differs = bool(name and job) and (name, job, sub) != self._context()
        show = self.pinned and differs
        self.follow_label.setText(f'Game is on {job}/{sub} ·' if sub else f'Game is on {job} ·')
        self.follow_label.setVisible(show)
        self.follow_btn.setVisible(show)

    # --- reading ----------------------------------------------------------
    def request(self, force: bool = False) -> None:
        """Read the picked job. One read at a time; requests made meanwhile collapse to the latest (eng D15)."""
        character, job, sub = self._context()
        if not character or not job:
            return
        self._generation += 1
        self._latest = self._generation
        key = (self._windower(), character, job, sub)
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
        if view is None:
            self.grid.set_cells({})
            self._set_verdict('', theme.TEXT)
            self.path_label.clear()
            self.set_caption.clear()
            return
        set_read = view.set_read
        cells = {slot: cell_for(slot, status) for slot, status in view.statuses.items()}
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
        self._show_slot(slot)
        if not self._wide:
            self._open_panel()

    def _clear_panel(self) -> None:
        self.current_slot = ''
        for widget in (self.panel_slot, self.panel_name, self.panel_info, self.panel_note):
            widget.clear()
            widget.hide()
        self.panel_placeholder.show()
        if self._wide is False and self.panel.isVisible():
            self.panel.hide()

    def _show_slot(self, slot: str) -> None:
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
