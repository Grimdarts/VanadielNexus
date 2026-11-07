"""Read-only source Sets-page probe with fictional snapshots; no AppContext/Lua.

Usage: python tools/profile_equipment_ui.py WINDOWER_ROOT OUTPUT_DIRECTORY
Offscreen measurements exclude the installed executable, game and whole app shell.
"""
import gc
import json
import os
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from profile_equipment_effects import rss
from vanadiel_nexus.core.equipment_matching import SLOTS
from vanadiel_nexus.core.gearswap_reader import Piece, SetRead, JobRead
from vanadiel_nexus.ui import theme
from vanadiel_nexus.ui.pages.sets import SetsPage


class Settings:
    def __init__(self):
        self.values = {'text_scale': 1.0}

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value


class Bridge(QObject):
    state_received = Signal(dict)
    state = {}


class Context(QObject):
    inventory_changed = Signal()
    windower_changed = Signal(str)

    def __init__(self, root):
        super().__init__()
        self.windower_dir = root
        self.settings = Settings()
        self.bridge = Bridge(self)
        self.inventory_snapshot = {}


def main():
    root, destination = sys.argv[1:]
    output = Path(destination)
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    for font in ('segoeui.ttf', 'seguisb.ttf'):
        QFontDatabase.addApplicationFont('C:/Windows/Fonts/' + font)
    theme.apply(app)
    ctx = Context(root)
    page = SetsPage(ctx)
    page.resize(1024, 768)
    page.show()
    selected = {'head': (25577, 'Inyanga Tiara +2'), 'body': (25793, 'Inyanga Jubbah +2'),
                'hands': (25831, 'Inyanga Dastanas +2'), 'legs': (25882, 'Inyanga Shalwar +2'),
                'feet': (25949, 'Inyanga Crackows +2'), 'neck': (26002, 'Loricate Torque +1'),
                'ring1': (26184, 'Stikini Ring +1'), 'ring2': (26184, 'Stikini Ring +1')}
    pieces = {s: Piece(s, s, selected[s][1]) if s in selected else Piece(s, s, empty=True) for s in SLOTS}
    first = SetRead('sets.Idle.ExampleA', ['Idle', 'ExampleA'], pieces)
    second = SetRead('sets.Idle.ExampleB', ['Idle', 'ExampleB'], {s: p for s, p in pieces.items() if s != 'feet'})
    ctx.inventory_snapshot = {'Example': [{'item_id': i, 'name': name, 'bag': 'Wardrobe 2', 'count': 1}
                                          for i, name in selected.values()]}
    ctx.settings.set('inventory_updated', {'Example': time.time() - 720})
    read = JobRead('Example', 'WHM', '', 'fictional.lua', False, {}, sets=[first, second])
    page.character_combo.addItem('Example')
    page.job_combo.clear()
    page.job_combo.addItem('WHM', 'WHM')
    page._apply(read)
    page._apply_label_styles()  # normal first-use styling without starting a Lua reader
    page.equipment_tabs.setCurrentIndex(1)
    app.processEvents()
    baseline = rss()
    memory, gaps, state = [baseline], [], {}
    last = time.perf_counter()
    timer = QTimer(interval=5)
    def sample():
        nonlocal last
        now = time.perf_counter()
        gaps.append((now - last) * 1000)
        last = now
        memory.append(rss())
    timer.timeout.connect(sample)
    service = page.analyzer.service
    def changed():
        if service.source:
            state['preparation_seconds'] = time.perf_counter() - started
            QTimer.singleShot(20, app.quit)
        elif service.error:
            state['error'] = service.error
            app.quit()
    service.changed.connect(changed)
    timer.start()
    started = time.perf_counter()
    page.analyzer.activate()
    QTimer.singleShot(10000, app.quit)
    app.exec()
    timer.stop()
    service.changed.disconnect(changed)
    if not service.source:
        raise RuntimeError(state.get('error', 'Preparation timed out'))
    page.analyzer.baseline.setCurrentIndex(page.analyzer.baseline.findData(second.path))
    recalculations, cards, settled = [], [], []
    for batch in range(10):
        for n in range(20):
            service.cache.clear()  # measure the real presentation path on misses
            start = time.perf_counter()
            page.analyzer.set_selection(read, first.path if n % 2 else second.path)
            app.processEvents()
            recalculations.append((time.perf_counter() - start) * 1000)
            start = time.perf_counter()
            page.analyzer.show_item('ring1', page.grid)
            app.processEvents()
            cards.append((time.perf_counter() - start) * 1000)
            page.analyzer.card.invalidate()
        gc.collect()
        settled.append(rss() - baseline)
    page._show_set(first.path)
    screenshots = []
    for width, height, scale in ((900, 600, 1.0), (1024, 768, 1.0), (900, 600, 1.3)):
        ctx.settings.set('text_scale', scale)
        theme.apply(app, scale)
        page.grid.set_scale(scale)
        page._apply_label_styles()
        page.resize(width, height)
        app.processEvents()
        page._layout_mode()
        app.processEvents()
        for _ in range(3):
            app.processEvents()
            page.centre_scroll.verticalScrollBar().setValue(page.centre_scroll.verticalScrollBar().maximum())
        path = output / f't6-analysis-{width}-{height}-{scale}.png'
        page.grab().save(str(path))
        screenshots.append(str(path))
        page.analyzer.show_item('ring1', page.grid)
        app.processEvents()
        path = output / f't6-card-{width}-{height}-{scale}.png'
        page.analyzer.card.grab().save(str(path))
        screenshots.append(str(path))
        page.analyzer.card.invalidate()
    result = page.analyzer.result
    report = dict(state, source_fingerprint=service.source.fingerprint,
                  source_signature=service.source.signature, items=len(service.source.items),
                  descriptions=len(service.source.descriptions), baseline_rss_bytes=baseline,
                  peak_sampled_preparation_delta_bytes=max(memory) - baseline,
                  event_loop_max_gap_ms=max(gaps), event_loop_samples=len(gaps),
                  recalc_samples=len(recalculations), recalc_p95_ms=sorted(recalculations)[189],
                  card_samples=len(cards), card_p95_ms=sorted(cards)[189],
                  settled_rss_delta_bytes=settled, known_refresh=result.get('refresh').known,
                  complete_refresh=result.get('refresh').complete, screenshots=screenshots,
                  fixture='Fictional WHM: 5 Inyanga +2, Loricate +1, two Stikini +1, 8 explicit empty slots; '
                          'comparison omits feet. Two distinct saved rings, same bag; identity ambiguous.',
                  limits='Actual source SetsPage and ItemCard offscreen; one small supported fixture. '
                         'No full-app/frozen-size/game-coexistence or live-input acceptance. '
                         'Timings exclude hover dwell; include processEvents and widget publication. '
                         'RSS baseline already includes the page and existing item_res caches.')
    (output / 'equipment-ui-profile.json').write_text(json.dumps(report, indent=2) + '\n')
    service.close()
    page.close()
    print(json.dumps({k: v for k, v in report.items() if k not in ('source_signature', 'screenshots')}, indent=2))


if __name__ == '__main__':
    main()
