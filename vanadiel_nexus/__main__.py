"""Entry point: python -m vanadiel_nexus (and the frozen exe)."""
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication

from vanadiel_nexus import __version__
from vanadiel_nexus.core import paths

INSTANCE_KEY = "VanadielNexus-single-instance"


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
