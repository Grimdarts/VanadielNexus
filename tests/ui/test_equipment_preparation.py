import os
from pathlib import Path
from threading import Event

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QCoreApplication, QThread
import pytest

from vanadiel_nexus.core.equipment_effects import prepare_source
from vanadiel_nexus.ui.equipment_preparation import EquipmentPreparation


def source(root):
    folder = root / 'res'
    folder.mkdir(parents=True)
    (folder / 'items.lua').write_text('[1] = {id=1,en="Fictional",slots=16,jobs=8},\n')
    (folder / 'item_descriptions.lua').write_text('[1] = {id=1,en="Unknown effect"},\n')
    return str(root)


def test_same_root_coalesces_and_ready_is_on_gui_thread(qtbot, tmp_path):
    root = source(tmp_path / 'source')
    calls, seen, threads = [], [], []
    def loader(root, cancelled):
        calls.append(root)
        assert QThread.currentThread() != QCoreApplication.instance().thread()
        return prepare_source(root, cancelled)
    adapter = EquipmentPreparation(loader=loader)
    adapter.ready.connect(lambda value: (seen.append(value), threads.append(QThread.currentThread())))
    adapter.request(root)
    adapter.request(root)
    qtbot.waitUntil(lambda: bool(seen))
    assert len(calls) == 1
    assert seen[0].names['fictional'] == (1,)
    with pytest.raises(TypeError):
        seen[0].names['fictional'] = (2,)
    assert threads == [QCoreApplication.instance().thread()]
    adapter.request(root)
    assert len(calls) == 1 and len(seen) == 2
    adapter.close()


def test_rapid_changes_keep_one_active_and_latest_pending(qtbot, tmp_path):
    first, latest = source(tmp_path / 'a'), source(tmp_path / 'b')
    entered, release = Event(), Event()
    calls, seen = [], []
    def loader(root, cancelled):
        calls.append(root)
        if len(calls) == 1:
            entered.set()
            release.wait(3)
            # Deliberately ignore cancellation to prove stale-result rejection.
            return prepare_source(root)
        return prepare_source(root, cancelled)
    adapter = EquipmentPreparation(loader=loader)
    adapter.ready.connect(seen.append)
    adapter.request(first)
    qtbot.waitUntil(entered.is_set)
    for _ in range(30):
        adapter.request(latest, force=True)
    assert len(adapter._jobs) == 1 and adapter._pending is not None
    assert len(adapter._events) <= 2
    release.set()
    qtbot.waitUntil(lambda: bool(seen))
    assert len(calls) == 2
    assert len(seen) == 1 and seen[0].root == str(Path(latest).resolve())
    assert not adapter.loading
    adapter.close()


def test_failure_and_source_change_clear_loading_and_allow_retry(qtbot, tmp_path):
    root = source(tmp_path / 'a')
    seen, errors = [], []
    def loader(root, cancelled):
        value = prepare_source(root, cancelled)
        with (Path(root) / 'res/items.lua').open('a') as stream:
            stream.write('-- changed before GUI publication\n')
        return value
    adapter = EquipmentPreparation(loader=loader)
    adapter.ready.connect(seen.append)
    adapter.failed.connect(errors.append)
    adapter.request(root)
    qtbot.waitUntil(lambda: bool(errors))
    assert not seen and not adapter.loading and adapter.snapshot is None
    assert 'changed' in errors[0]
    adapter.loader = prepare_source
    adapter.request(root)
    qtbot.waitUntil(lambda: bool(seen))
    assert adapter.snapshot is seen[0]
    adapter.request(str(tmp_path / 'missing'))
    qtbot.waitUntil(lambda: len(errors) == 2)
    assert adapter.snapshot is None and not adapter.loading
    adapter.close()


def test_close_cancels_without_late_publication(qtbot, tmp_path):
    root = source(tmp_path / 'a')
    entered, release, finished = Event(), Event(), Event()
    seen = []
    def loader(root, cancelled):
        entered.set()
        release.wait(3)
        finished.set()
        return prepare_source(root)
    adapter = EquipmentPreparation(loader=loader)
    adapter.ready.connect(seen.append)
    adapter.request(root)
    qtbot.waitUntil(entered.is_set)
    adapter.close()
    release.set()
    qtbot.waitUntil(finished.is_set)
    qtbot.waitUntil(lambda: not adapter._jobs)
    assert not seen and not adapter.loading and adapter.snapshot is None
    adapter.request(root)
    assert not adapter._jobs


def test_receiver_destruction_sets_worker_cancel_event(qtbot, tmp_path):
    from PySide6.QtCore import QEvent
    root = source(tmp_path / 'a')
    entered, cancelled, done = Event(), Event(), Event()
    def loader(root, check):
        entered.set()
        while not check() and not done.wait(.005):
            pass
        if check():
            cancelled.set()
        return prepare_source(root)
    adapter = EquipmentPreparation(loader=loader)
    adapter.request(root)
    qtbot.waitUntil(entered.is_set)
    adapter.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    qtbot.waitUntil(cancelled.is_set)
    done.set()


def test_reentrant_loading_listener_cannot_publish_old_source(qtbot, tmp_path):
    first, second = source(tmp_path / 'first'), source(tmp_path / 'second')
    seen, changed = [], []
    adapter = EquipmentPreparation()
    def change(loading):
        if not loading and not changed:
            changed.append(True)
            adapter.request(second)
    adapter.loading_changed.connect(change)
    adapter.ready.connect(seen.append)
    adapter.request(first)
    qtbot.waitUntil(lambda: bool(seen))
    assert len(seen) == 1 and seen[0].root == str(Path(second).resolve())
    adapter.close()


def test_reentrant_start_listener_keeps_only_newest_request(qtbot, tmp_path):
    first, second = source(tmp_path / 'first'), source(tmp_path / 'second')
    seen, changed, calls = [], [], []
    def loader(root, cancelled):
        calls.append(root)
        return prepare_source(root, cancelled)
    adapter = EquipmentPreparation(loader=loader)
    def change(loading):
        if loading and not changed:
            changed.append(True)
            adapter.request(second)
    adapter.loading_changed.connect(change)
    adapter.ready.connect(seen.append)
    adapter.request(first)
    qtbot.waitUntil(lambda: bool(seen))
    assert calls == [str(Path(second).resolve())]
    assert len(seen) == 1 and seen[0].root == calls[0]
    adapter.close()
