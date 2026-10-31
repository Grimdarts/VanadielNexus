"""Entry point: python -m vanadiel_nexus (and the frozen exe)."""
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication

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
    data=Path(os.environ['VN_DATA_DIR']).resolve()
    if not data.is_relative_to(root):
        raise ValueError('Startup check requires isolated data beside its result')
    game=root/'test-windower'
    (game/'addons').mkdir(parents=True,exist_ok=True)
    data.mkdir(parents=True,exist_ok=True)
    (data/'settings.json').write_text(json.dumps({'windower_dir':str(game),'setup_dismissed':True}),encoding='utf-8')
    updater.check=lambda _version: None
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
    Path(output).write_text(json.dumps({'ok':True,'version':__version__,
        'pyside':qt_binding_version,'pages':pages}),encoding='utf-8')
    return 0


def _already_running() -> bool:
    """If another copy is open, ask it to come to the front and return True."""
    sock = QLocalSocket()
    sock.connectToServer(INSTANCE_KEY)
    if sock.waitForConnected(300):
        sock.write(b"show")
        sock.waitForBytesWritten(300)
        return True
    return False


def main() -> int:
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
    sys.exit(main())
