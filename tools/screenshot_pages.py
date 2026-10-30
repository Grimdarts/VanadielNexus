"""Renders every page of the app to PNGs using a throwaway copy of the data folder.

    py tools/screenshot_pages.py <output folder> [width] [height]
"""
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def main():
    out = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "screens")
    width = int(sys.argv[2]) if len(sys.argv) > 2 else 1280
    height = int(sys.argv[3]) if len(sys.argv) > 3 else 800
    os.makedirs(out, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="vn-shot-")
    src = os.path.join(ROOT, "data")
    for fn in ("ffxi_database.json", "inventory_snapshot.json"):
        if os.path.exists(os.path.join(src, fn)):
            shutil.copy2(os.path.join(src, fn), tmp)
    with open(os.path.join(tmp, "settings.json"), "w") as f:
        f.write('{"setup_dismissed": true, "job_filter": "%s"}' % os.environ.get("VN_JOB", ""))
    os.environ["VN_DATA_DIR"] = tmp

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from vanadiel_nexus import __version__
    from vanadiel_nexus.ui import theme
    from vanadiel_nexus.ui.context import AppContext
    from vanadiel_nexus.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    from PySide6.QtGui import QFontDatabase
    from vanadiel_nexus.core import paths
    QFontDatabase.addApplicationFont(paths.resource_path('fonts', 'Cinzel.ttf'))
    ctx = AppContext(__version__)
    theme.apply(app)
    win = MainWindow(ctx)
    win.resize(width, height)
    win.show()
    keys = [p.key for p in win.pages]

    def shoot(i=0):
        if i == len(keys):
            app.quit()
            return
        win.show_page(keys[i])
        QTimer.singleShot(1500 if keys[i] == "hotkeys" else 400,
                          lambda: (win.grab().save(os.path.join(out, f"{i + 1}-{keys[i]}.png")), shoot(i + 1)))

    QTimer.singleShot(500, shoot)
    app.exec()
    shutil.rmtree(tmp, ignore_errors=True)
    print(out)


if __name__ == "__main__":
    main()
