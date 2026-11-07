"""Entry point: python -m vanadiel_nexus (and the frozen exe).

Qt is imported inside the functions, not here: the Sets page reads GearSwap files in a spawned child process,
which imports this module again (as __mp_main__) and must only load multiprocessing, gs_worker and lupa.
"""
import multiprocessing
import sys

from vanadiel_nexus import __version__
from vanadiel_nexus.core import paths

INSTANCE_KEY = "VanadielNexus-single-instance"


def startup_check(app, output):
    """Initialize the real frozen UI with temporary data and no game/update requests."""
    import json
    import os
    from pathlib import Path
    from PySide6.QtCore import QThreadPool
    from PySide6 import __version__ as qt_binding_version
    from vanadiel_nexus.core import updater
    from vanadiel_nexus.ui import theme
    from vanadiel_nexus.ui.context import AppContext
    from vanadiel_nexus.ui.main_window import MainWindow

    root=Path(output).resolve().parent
    spawn=spawn_check(root/'spawn-check')
    data=Path(os.environ['VN_DATA_DIR']).resolve()
    if not data.is_relative_to(root):
        raise ValueError('Startup check requires isolated data beside its result')
    game=root/'test-windower'
    (game/'addons').mkdir(parents=True,exist_ok=True)
    data.mkdir(parents=True,exist_ok=True)
    (data/'settings.json').write_text(json.dumps({'windower_dir':str(game),'setup_dismissed':True}),encoding='utf-8')
    updater.check=lambda _version: None
    AppContext._seed_inventory_from_addon_files=lambda self: None
    ctx=AppContext(__version__)
    ctx.bridge.request_scan=lambda: None
    theme.apply(app)
    window=MainWindow(ctx)
    pages=[]
    for page in window.pages:
        window.show_page(page.key)
        app.processEvents()
        pages.append(page.key)
    window.close()
    QThreadPool.globalInstance().waitForDone(5000)
    app.processEvents()
    guides=next(page for page in window.pages if page.key=='guides')
    catalog=guides.catalog
    guide_check={'ok':guides.catalog_error is None,'error':guides.catalog_error,
        'schema':catalog.get('schema_version'),'sets':len(catalog['sets']),
        'revisions':len(catalog.get('revisions',[])),
        'retired':len(catalog.get('_retirements',{}))}
    Path(output).write_text(json.dumps({'ok':True,'version':__version__,
        'pyside':qt_binding_version,'pages':pages,'spawn':spawn,
        'guide_catalog':guide_check}),encoding='utf-8')
    return 0


def spawn_check(folder) -> dict:
    """Read a 3-line GearSwap file through the real spawn path, timed on its own (must finish in 5 s)."""
    import time
    from pathlib import Path
    from vanadiel_nexus.core import gearswap_reader
    data=Path(folder)/'addons'/'GearSwap'/'data'
    data.mkdir(parents=True,exist_ok=True)
    job=data/'Check_BLU.lua'
    job.write_text('function get_sets()\n    sets.Check = {head="Nyame Mail"}\nend\n',encoding='utf-8')
    started=time.monotonic()
    raw=gearswap_reader._spawn({'windower_dir':str(folder),'character':'Check','job':'BLU','job_long':'Blue Mage',
                                'job_id':16,'sub_job':'','job_path':str(job),'appdata':str(Path(folder)/'appdata')},5.0)
    seconds=round(time.monotonic()-started,2)
    pieces=[p for node in raw.get('nodes') or [] for p in node.get('pieces') or []]
    ok=not raw.get('error') and any(p.get('name')=='Nyame Mail' for p in pieces) and seconds<=5
    return {'ok':ok,'seconds':seconds,'error':raw.get('error') or ''}


def _already_running() -> bool:
    """If another copy is open, ask it to come to the front and return True."""
    from PySide6.QtNetwork import QLocalSocket
    sock = QLocalSocket()
    sock.connectToServer(INSTANCE_KEY)
    if sock.waitForConnected(300):
        sock.write(b"show")
        sock.waitForBytesWritten(300)
        return True
    return False


def main() -> int:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFontDatabase
    from PySide6.QtNetwork import QLocalServer
    from PySide6.QtWidgets import QApplication

    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName("Vana'diel Nexus")
    if '--startup-check' in sys.argv:
        return startup_check(app, sys.argv[sys.argv.index('--startup-check')+1])
    if _already_running():
        return 0

    from vanadiel_nexus.ui import theme
    from vanadiel_nexus.ui.context import AppContext
    from vanadiel_nexus.ui.main_window import MainWindow

    font_file = paths.resource_path("fonts", "Cinzel.ttf")  # SIL OFL, see Cinzel-OFL.txt
    QFontDatabase.addApplicationFont(font_file)  # optional: falls back to Cambria if absent

    ctx = AppContext(__version__)
    theme.apply(app, float(ctx.settings.get("text_scale") or 1.0))
    win = MainWindow(ctx)

    server = QLocalServer()
    QLocalServer.removeServer(INSTANCE_KEY)
    server.listen(INSTANCE_KEY)

    def _raise():
        conn = server.nextPendingConnection()
        if conn:
            conn.close()
        win.showNormal()
        win.raise_()
        win.activateWindow()

    server.newConnection.connect(_raise)
    win.show()
    return app.exec()


if __name__ == "__main__":
    multiprocessing.freeze_support()  # first: a frozen child must never reach Qt or the single-instance check
    sys.exit(main())
