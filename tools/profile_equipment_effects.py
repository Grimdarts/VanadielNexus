"""Read-only T5 source/worker probe; no AppContext, player data, bridge or build.

Usage: python tools/profile_equipment_effects.py WINDOWER_ROOT OUTPUT_JSON
Reports standalone preparation baseline; full-page/card/frozen budgets remain T6/T9.
"""
import ctypes
from ctypes import wintypes
import gc
import json
import os
from pathlib import Path
import statistics
import sys
import time
import tracemalloc

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QCoreApplication, QTimer
from vanadiel_nexus.core.equipment_effects import EvaluationCache, SLOTS, prepare_source
from vanadiel_nexus.ui.equipment_preparation import EquipmentPreparation


def rss():
    class Counters(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('faults', wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in ('peak', 'working', 'peak_paged', 'paged',
                                               'peak_nonpaged', 'nonpaged', 'pagefile', 'peak_pagefile')]
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    current = ctypes.windll.kernel32.GetCurrentProcess
    current.restype = wintypes.HANDLE
    call = ctypes.windll.psapi.GetProcessMemoryInfo
    call.argtypes = (wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD)
    if not call(current(), ctypes.byref(counters), counters.cb):
        raise ctypes.WinError()
    return counters.working


def main():
    root, output = sys.argv[1:]
    app = QCoreApplication([])
    adapter = EquipmentPreparation()
    cache = EvaluationCache()
    baseline = rss()
    memory, gaps, state = [baseline], [], {}
    last = time.perf_counter()
    timer = QTimer()
    timer.setInterval(5)
    def sample():
        nonlocal last
        now = time.perf_counter()
        gaps.append(now - last)
        last = now
        memory.append(rss())
    timer.timeout.connect(sample)
    def ready(source):
        state['source'] = source
        state['seconds'] = time.perf_counter() - started
        app.quit()
    adapter.ready.connect(ready)
    adapter.failed.connect(lambda error: (state.update(error=error), app.quit()))
    timer.start()
    started = time.perf_counter()
    adapter.request(root)
    QTimer.singleShot(15000, app.quit)
    app.exec()
    timer.stop()
    adapter.close()
    if 'source' not in state:
        raise RuntimeError(state.get('error', 'Preparation timed out'))
    source = state['source']
    selected = {'head': 25577, 'body': 25793, 'hands': 25831, 'legs': 25882, 'feet': 25949,
                'neck': 26002, 'ring1': 26184, 'ring2': 26184}
    slots = [dict(slot=s, state='selected', item_id=selected[s], requirements={}) if s in selected
             else dict(slot=s, state='empty') for s in SLOTS]
    timings = []
    # Misses: same supported 16-slot fixture, changing an irrelevant explicit
    # scenario marker. Hits: same fixture/scenario and immutable result.
    for n in range(200):
        start = time.perf_counter()
        result = cache.evaluate(slots, source, job='WHM', scenario={'probe': n})
        timings.append((time.perf_counter() - start) * 1000)
    hits = []
    settled = []
    for batch in range(10):
        for _ in range(100):
            start = time.perf_counter()
            cache.evaluate(slots, source, job='WHM', scenario={'probe': 199})
            hits.append((time.perf_counter() - start) * 1000)
        gc.collect()
        settled.append(rss() - baseline)
    # Separate instrumented run; its elapsed time is not the cold latency claim.
    tracemalloc.start()
    measured = prepare_source(root)
    traced_current, traced_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    del measured
    report = {'source_fingerprint': source.fingerprint, 'source_signature': source.signature,
              'items': len(source.items), 'descriptions': len(source.descriptions),
              'preparation_seconds': state['seconds'], 'event_loop_max_gap_ms': max(gaps, default=0) * 1000,
              'event_loop_samples': len(gaps), 'peak_sampled_rss_delta_bytes': max(memory) - baseline,
              'settled_rss_delta_bytes': settled, 'traced_second_run_current_bytes': traced_current,
              'traced_second_run_peak_bytes': traced_peak, 'cache_estimated_retained_bytes': cache.retained_bytes,
              'recalculation_samples': len(timings), 'recalculation_p95_ms': sorted(timings)[189],
              'cache_hit_samples': len(hits), 'cache_hit_p95_ms': sorted(hits)[949],
              'fixture': 'WHM: 5 Inyanga +2 pieces, Loricate +1, 2 Stikini +1; 8 intentional empty slots',
              'known_refresh': result.get('refresh').known, 'complete_refresh': result.get('refresh').complete,
              'limits': 'Standalone QCoreApplication baseline. No card dwell, full-page baseline, frozen size or live coexistence claim.'}
    Path(output).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
