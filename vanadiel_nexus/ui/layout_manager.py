"""Applies overlay layouts: on Save, when the job changes, and from in-game layout mode (//vn layout).

Moving an addon's window means: unload it, write its settings, load it again. A plain reload isn't
enough because some addons save their old position while unloading. Without the game connected the
files are just written, and the addons pick them up the next time they load.
"""
from PySide6.QtCore import QObject, QTimer, Signal

from ..core import overlays, windower

UNLOAD_SETTLE_MS = 1200
DEFAULT_UI = (1920, 1080)
NEVER_TOGGLED = {"gearswap"}  # hiding GearSwap would stop gear swaps, not just a window


class LayoutManager(QObject):
    changed = Signal()
    message = Signal(str)

    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.store = overlays.LayoutStore(ctx.data_dir)
        self._overlays = None
        self._seen = None          # (character, job) the game last reported
        self._applied_shown = {}   # character -> shown map the game is in now
        ctx.bridge.state_received.connect(self._on_state)
        ctx.bridge.layout_message.connect(self._on_layout_message)
        ctx.windower_changed.connect(lambda _p: self.refresh())

    # --- facts ------------------------------------------------------------------------------
    def overlays(self) -> list:
        if self._overlays is None:
            self._overlays = overlays.find_overlays(self.ctx.windower_dir, self.character()) \
                if self.ctx.windower_dir else []
        return self._overlays

    def refresh(self) -> None:
        self._overlays = None
        self.changed.emit()

    def character(self) -> str:
        name = self.ctx.bridge.state.get("player_name")
        if name:
            return name
        saved = self.ctx.settings.get("layout_character")
        if saved:
            return saved
        live = [k for k in self.ctx.inventory_snapshot if not k.startswith("Imported: ")]
        return live[0] if live else ""

    def game_job(self) -> str:
        """The job in game now, or the last one seen (what the addon files were set up for)."""
        if self.ctx.bridge.connected and self.ctx.bridge.state.get("main_job"):
            return self.ctx.bridge.state["main_job"]
        return self.ctx.settings.get("layout_last_job") or ""

    def screen_size(self) -> tuple:
        s = self.ctx.bridge.state
        if s.get("ui_x_res") and s.get("ui_y_res"):
            return int(s["ui_x_res"]), int(s["ui_y_res"])
        saved = self.ctx.settings.get("game_ui_size")
        return tuple(saved) if isinstance(saved, list) and len(saved) == 2 else DEFAULT_UI

    def screen(self) -> overlays.Screen:
        w, h = self.screen_size()
        return overlays.Screen(self.overlays(), self.character(), w, h)

    def toggleable(self, addon: str) -> bool:
        return addon.lower() not in NEVER_TOGGLED

    def current_positions(self) -> dict:
        return overlays.read_all(self.overlays(), self.character())

    # --- layouts ----------------------------------------------------------------------------
    def ensure_default(self, char: str) -> None:
        """First use: Default is what's on screen now, shown = what starts with the game."""
        if not char or self.store.has(char, overlays.DEFAULT):
            return
        startup = windower.autoloads(self.ctx.windower_dir)["addons"] if self.ctx.windower_dir else set()
        shown = {ov.addon: ov.addon.lower() in startup for ov in self.overlays() if self.toggleable(ov.addon)}
        self.store.put(char, overlays.DEFAULT, {"positions": self.current_positions(), "shown": shown})

    def layout_for(self, job: str) -> dict:
        char = self.character()
        self.ensure_default(char)
        layout = self.store.get(char, job or overlays.DEFAULT)
        # Windows the layout has never seen (a new addon) stay where they are.
        for oid, pos in self.current_positions().items():
            layout["positions"].setdefault(oid, pos)
        return layout

    def save_layout(self, job: str, layout: dict) -> None:
        """Save a job's layout; if that's the layout the game is using now, move the windows."""
        char = self.character()
        before = self._applied_shown.get(char) or self.layout_for(self.game_job())["shown"]
        self.store.put(char, job or overlays.DEFAULT, layout)
        self.changed.emit()
        active = self.game_job()
        if not active or job == active or (job == overlays.DEFAULT and not self.store.has(char, active)):
            self.apply(self.layout_for(active), before, backup=True)

    # --- applying ---------------------------------------------------------------------------
    def apply(self, layout: dict, before_shown: dict, backup: bool = False) -> dict:
        char = self.character()
        plan = overlays.plan_switch(self.current_positions(), layout["positions"],
                                    before_shown, layout["shown"], self.overlays())
        self._applied_shown[char] = dict(layout["shown"])
        if not (plan["write"] or plan["load"] or plan["unload"]):
            return plan
        commands = {ov.addon: ov.reload for ov in self.overlays() if ov.reload}
        # Addons layouts never show or hide (GearSwap) have no 'shown' entry, so plan_switch can't tell
        # they're loaded. They always are; one with its own reload command still needs it after a move.
        addon_of = {ov.id: ov.addon for ov in self.overlays()}
        for addon in sorted({addon_of[oid] for oid in plan["write"]}):
            if addon in commands and not self.toggleable(addon) and addon not in plan["reload"]:
                plan["reload"].append(addon)
        bridge = self.ctx.bridge
        if not bridge.connected:
            overlays.write_positions(self.overlays(), char, plan["write"], backup=backup)
            self.message.emit("Layout saved. Addons pick it up the next time they load.")
            return plan
        cycle = [a for a in plan["reload"] if a not in commands]
        for addon in plan["unload"] + cycle:
            bridge.addon("unload", addon)

        def finish():
            overlays.write_positions(self.overlays(), char, plan["write"], backup=backup)
            for addon in plan["load"] + cycle:
                bridge.addon("load", addon)
            for addon in plan["reload"]:
                if addon in commands:
                    bridge.send(f"CMD|{commands[addon]}")
            moved = len(plan["write"])
            self.message.emit(f"Layout applied: {moved} window{'s' if moved != 1 else ''} moved.")
        if plan["unload"] or cycle:
            QTimer.singleShot(UNLOAD_SETTLE_MS, finish)
        else:
            finish()
        return plan

    def _on_state(self, state: dict) -> None:
        char, job = state.get("player_name", ""), state.get("main_job", "")
        if state.get("ui_x_res") and state.get("ui_y_res"):
            self.ctx.settings.set("game_ui_size", [int(state["ui_x_res"]), int(state["ui_y_res"])])
        if not char or not job:
            return
        self.ctx.settings.set("layout_character", char)
        self.ctx.settings.set("layout_last_job", job)
        previous, self._seen = self._seen, (char, job)
        if previous is None or previous == (char, job):
            return  # first word from the game: leave windows where they are
        if previous[0] != char:
            self.refresh()
            return
        if self.ctx.settings.get("layout_switch_with_job") is False:
            return
        before = self._applied_shown.get(char) or self.layout_for(previous[1])["shown"]
        self.apply(self.layout_for(job), before)
        self.changed.emit()

    # --- in-game layout mode ----------------------------------------------------------------
    def _on_layout_message(self, payload: dict) -> None:
        if payload.get("type") == "LAYOUT_REQUEST":
            self.send_frames()
        elif payload.get("type") == "LAYOUT_RESULT" and isinstance(payload.get("positions"), dict):
            self.take_screen_positions(payload["positions"])

    def send_frames(self) -> None:
        job = self.game_job()
        layout = self.layout_for(job)
        scr = self.screen()
        frames = []
        for ov in self.overlays():
            raw = layout["positions"].get(ov.id)
            if raw is None or layout["shown"].get(ov.addon) is False:
                continue
            x, y = scr.to_screen(ov.id, raw, layout["positions"])
            w, h = scr.sizes[ov.id]
            frames.append((ov.id, x, y, w, h, ov.label))
        self.ctx.bridge.show_layout(frames)

    def take_screen_positions(self, screen_positions: dict) -> None:
        job = self.game_job()
        layout = self.layout_for(job)
        scr = self.screen()
        positions = dict(layout["positions"])
        # Leaders first, so windows that follow another (pet bar under xivbar) convert against its new spot.
        order = sorted(screen_positions, key=lambda oid: bool(getattr(scr.by_id.get(oid), "follows", "")))
        for oid in order:
            xy = screen_positions[oid]
            if oid in scr.by_id and isinstance(xy, list) and len(xy) == 2 \
                    and all(isinstance(v, (int, float)) for v in xy):
                positions[oid] = scr.from_screen(oid, xy, positions)
        layout["positions"] = positions
        self.save_layout(job or overlays.DEFAULT, layout)
