"""Coalesced, generation-safe off-hover preparation for later cards/analyzer.

This adapter adds no polling and never touches a widget from a worker thread.
Consumers explicitly request/refresh and connect ready/failed/loading_changed.
"""
from pathlib import Path
from threading import Event

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from ..core.equipment_effects import prepare_source, source_signature


class _Signals(QObject):
    finished = Signal(int, object, object)


class _Prepare(QRunnable):
    def __init__(self, request_id, root, cancel, loader):
        super().__init__()
        self.request_id, self.root, self.cancel, self.loader = request_id, root, cancel, loader
        self.signals = _Signals()

    def run(self):
        result, error = None, None
        try:
            result = self.loader(self.root, self.cancel.is_set)
        except Exception as failure:
            error = str(failure)
        self.signals.finished.emit(self.request_id, result, error)


class EquipmentPreparation(QObject):
    ready = Signal(object)
    failed = Signal(str)
    loading_changed = Signal(bool)

    def __init__(self, parent=None, *, loader=prepare_source, pool=None):
        super().__init__(parent)
        self.loader = loader
        self.pool = pool or QThreadPool.globalInstance()
        self.generation = 0
        self.snapshot = None
        self.loading = False
        self._root = None
        self._cancel = None
        self._closed = False
        self._jobs = {}
        self._pending = None
        # Deleting the consumer cancels work without waiting on the GUI thread.
        # Events contain no references back to a widget or this adapter.
        events = []
        self._events = events
        self.destroyed.connect(lambda: [event.set() for event in events])

    def request(self, root, *, force=False):
        if self._closed:
            return
        root = str(Path(root).resolve())
        if self.loading and self._root == root and not force:
            return  # coalesce same-source requests until completion
        if self.snapshot is not None and self._root == root and not force:
            try:
                current = source_signature(root) == self.snapshot.signature
            except OSError:
                current = False
            if current:
                self.ready.emit(self.snapshot)
                return
        requested_generation = self.generation + 1
        self.cancel()
        if self._closed or self.generation != requested_generation:
            return  # a loading-state listener requested a newer generation
        self._root, self.snapshot = root, None
        self._cancel = Event()
        self._events.append(self._cancel)
        worker = _Prepare(self.generation, root, self._cancel, self.loader)
        worker.signals.finished.connect(self._finished)
        self.loading = True
        self.loading_changed.emit(True)
        if self._closed or self.generation != worker.request_id:
            worker.cancel.set()
            if worker.cancel in self._events:
                self._events.remove(worker.cancel)
            return
        if self._jobs:
            self._pending = worker  # only the newest request survives
        else:
            self._start(worker)

    def _start(self, worker):
        self._jobs[worker.request_id] = worker
        self.pool.start(worker)

    def cancel(self):
        self.generation += 1
        if self._cancel is not None:
            self._cancel.set()
        if self._pending is not None:
            if self._pending.cancel in self._events:
                self._events.remove(self._pending.cancel)
            self._pending = None
        if self.loading:
            self.loading = False
            self.loading_changed.emit(False)

    def close(self):
        self._closed = True
        self.cancel()
        self.snapshot = None

    @Slot(int, object, object)
    def _finished(self, generation, snapshot, error):
        worker = self._jobs.pop(generation, None)
        if worker is not None and worker.cancel in self._events:
            self._events.remove(worker.cancel)
        if self._closed or generation != self.generation:
            if not self._closed and self._pending is not None:
                next_worker, self._pending = self._pending, None
                self._start(next_worker)
            return
        self.loading = False
        self.loading_changed.emit(False)
        if self._closed or generation != self.generation:
            return  # external signal handlers may change selection/root
        if error is None:
            try:
                if snapshot.root != self._root or source_signature(self._root) != snapshot.signature:
                    error = 'Equipment source changed before publication; refresh to retry'
            except (OSError, AttributeError) as failure:
                error = str(failure)
        if error is not None:
            self.snapshot = None
            self.failed.emit(error)
        else:
            self.snapshot = snapshot
            self.ready.emit(snapshot)
