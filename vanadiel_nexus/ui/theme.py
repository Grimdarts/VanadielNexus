"""DESIGN.md as code: color tokens, one Qt stylesheet, and the dark Windows title bar."""
import ctypes
import sys

from PySide6.QtGui import QColor, QFont, QPalette

BG = "#0B1020"
SURFACE = "#121A2E"
SURFACE_2 = "#18223A"
BORDER = "#26324D"
TEXT = "#E6EAF2"
MUTED = "#9AA6BF"
FAINT = "#7D89A6"
ACCENT = "#22D3EE"
ACCENT_STRONG = "#0EA5C6"
GOLD = "#E0B04A"
SUCCESS = "#34D399"
WARNING = "#F59E0B"
DANGER = "#F87171"

UI_FONT = "Segoe UI Variable Text"
TITLE_FONTS = "Cinzel, Cambria, Georgia, serif"


def stylesheet(scale: float = 1.0) -> str:
    def px(v):
        return f"{round(v * scale)}px"

    return f"""
* {{ font-family: "{UI_FONT}", "Segoe UI"; font-size: {px(14)}; color: {TEXT}; }}
QMainWindow, QDialog, #Content {{ background: {BG}; }}
QToolTip {{ background: {SURFACE_2}; color: {TEXT}; border: 1px solid {BORDER}; padding: 4px 8px; }}

/* Sidebar */
#Sidebar {{ background: {SURFACE}; border-right: 1px solid {BORDER}; }}
#Brand {{ font-family: {TITLE_FONTS}; font-size: {px(17)}; font-weight: 600; color: {GOLD}; padding: 6px 12px 16px 12px; }}
#NavButton {{ text-align: left; padding: {px(9)} {px(12)}; border: none; border-left: 3px solid transparent;
              border-radius: 6px; color: {MUTED}; background: transparent; }}
#NavButton:hover {{ background: {SURFACE_2}; color: {TEXT}; }}
#NavButton:checked {{ color: {ACCENT}; background: rgba(34, 211, 238, 0.08); border-left: 3px solid {ACCENT}; }}
#NavSeparator {{ background: {BORDER}; max-height: 1px; margin: 10px 6px; }}

/* Top bar */
#TopBar {{ background: {BG}; border-bottom: 1px solid {BORDER}; }}
#PageTitle {{ font-family: {TITLE_FONTS}; font-size: {px(21)}; font-weight: 600; }}
#SectionTitle {{ font-size: {px(16)}; font-weight: 600; }}
#Caption, QLabel[muted="true"] {{ color: {MUTED}; font-size: {px(12)}; }}

/* Buttons */
QPushButton {{ background: {SURFACE_2}; border: 1px solid {BORDER}; border-radius: 6px; padding: {px(6)} {px(14)}; }}
QPushButton:hover {{ background: #1E2A46; border-color: #3A4A70; }}
QPushButton:pressed {{ background: {SURFACE}; }}
QPushButton:disabled {{ color: {FAINT}; border-color: {SURFACE_2}; }}
QPushButton[kind="primary"] {{ background: {ACCENT}; color: {BG}; border-color: {ACCENT}; font-weight: 600; }}
QPushButton[kind="primary"]:hover {{ background: {ACCENT_STRONG}; border-color: {ACCENT_STRONG}; }}
QPushButton[kind="primary"]:disabled {{ background: {SURFACE_2}; color: {FAINT}; border-color: {BORDER}; }}
QPushButton[kind="ghost"] {{ background: transparent; border-color: transparent; color: {MUTED}; }}
QPushButton[kind="ghost"]:hover {{ background: {SURFACE_2}; color: {TEXT}; }}
QPushButton[kind="danger"] {{ color: {DANGER}; }}
QPushButton[kind="danger-fill"] {{ background: {DANGER}; color: {BG}; border-color: {DANGER}; font-weight: 600; }}

/* Status pills */
QPushButton[pill="true"], QLabel[pill="true"] {{ border-radius: 11px; padding: 2px 10px; font-size: {px(12)};
    font-weight: 500; border: 1px solid {BORDER}; background: {SURFACE}; color: {MUTED}; }}
*[tone="warning"] {{ color: {WARNING}; border-color: rgba(245, 158, 11, 0.35); background: rgba(245, 158, 11, 0.08); }}
*[tone="success"] {{ color: {SUCCESS}; border-color: rgba(52, 211, 153, 0.3); background: rgba(52, 211, 153, 0.07); }}
*[tone="gold"] {{ color: {GOLD}; border-color: rgba(224, 176, 74, 0.35); background: rgba(224, 176, 74, 0.08); }}
*[tone="accent"] {{ color: {ACCENT}; border-color: rgba(34, 211, 238, 0.35); background: rgba(34, 211, 238, 0.08); }}

/* Inputs */
QLineEdit, QComboBox, QSpinBox, QPlainTextEdit, QTextEdit {{ background: {SURFACE_2}; border: 1px solid {BORDER};
    border-radius: 6px; padding: {px(5)} {px(10)}; selection-background-color: {ACCENT_STRONG}; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QPlainTextEdit:focus, QTextEdit:focus {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{ background: {SURFACE_2}; border: 1px solid {BORDER}; selection-background-color: #1E2A46;
    selection-color: {ACCENT}; outline: none; }}
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px; border: 1px solid {BORDER}; background: {SURFACE_2}; }}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}
QSlider::groove:horizontal {{ height: 4px; background: {SURFACE_2}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {ACCENT}; width: 14px; margin: -6px 0; border-radius: 7px; }}

/* Tables */
QTableView, QTreeView {{ background: {SURFACE}; alternate-background-color: #151E34; border: 1px solid {BORDER};
    border-radius: 10px; gridline-color: transparent; selection-background-color: rgba(34, 211, 238, 0.12);
    selection-color: {TEXT}; outline: none; }}
QTableView::item, QTreeView::item {{ padding: 0 {px(10)}; border: none; }}
QTableView::item:hover, QTreeView::item:hover {{ background: {SURFACE_2}; }}
QHeaderView::section {{ background: {SURFACE}; color: {MUTED}; font-size: {px(12)}; font-weight: 600; border: none;
    border-bottom: 1px solid {BORDER}; padding: {px(8)} {px(10)}; }}
QTableCornerButton::section {{ background: {SURFACE}; border: none; }}

/* Segmented control (QTabBar) */
QTabBar::tab {{ background: transparent; color: {MUTED}; padding: {px(7)} {px(16)}; border: 1px solid {BORDER};
    margin-right: -1px; }}
QTabBar::tab:first {{ border-top-left-radius: 6px; border-bottom-left-radius: 6px; }}
QTabBar::tab:last {{ border-top-right-radius: 6px; border-bottom-right-radius: 6px; }}
QTabBar::tab:selected {{ background: rgba(34, 211, 238, 0.10); color: {ACCENT}; border-color: rgba(34, 211, 238, 0.45); }}
QTabBar::tab:hover:!selected {{ color: {TEXT}; }}

/* Cards, panels, progress */
#Card, #Panel {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 10px; }}
#CardValue {{ font-size: {px(22)}; font-weight: 600; }}
QProgressBar {{ background: {SURFACE_2}; border: none; border-radius: 3px; max-height: 6px; text-align: right; }}
QProgressBar::chunk {{ background: {GOLD}; border-radius: 3px; }}

/* Scrollbars */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 4px; min-height: 30px; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {BORDER}; border-radius: 4px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ background: none; border: none; }}
QMenu {{ background: {SURFACE_2}; border: 1px solid {BORDER}; padding: 4px; }}
QMenu::item {{ padding: 6px 18px; border-radius: 4px; }}
QMenu::item:selected {{ background: #1E2A46; color: {ACCENT}; }}
QMessageBox QLabel {{ min-width: 320px; }}
"""


def palette() -> QPalette:
    pal = QPalette()
    for role, color in (
        (QPalette.Window, BG), (QPalette.Base, SURFACE), (QPalette.AlternateBase, "#151E34"),
        (QPalette.Text, TEXT), (QPalette.WindowText, TEXT), (QPalette.Button, SURFACE_2),
        (QPalette.ButtonText, TEXT), (QPalette.Highlight, ACCENT_STRONG), (QPalette.HighlightedText, BG),
        (QPalette.ToolTipBase, SURFACE_2), (QPalette.ToolTipText, TEXT), (QPalette.PlaceholderText, FAINT),
        (QPalette.Link, ACCENT),
    ):
        pal.setColor(role, QColor(color))
    return pal


def apply(app, scale: float = 1.0) -> None:
    app.setStyle("Fusion")
    app.setPalette(palette())
    app.setFont(QFont(UI_FONT, 10))
    app.setStyleSheet(stylesheet(scale))


def dark_title_bar(widget) -> None:
    """Windows 10/11: ask DWM for a dark title bar, and on Windows 11 tint it to the app background."""
    if sys.platform != "win32":
        return
    try:
        hwnd = int(widget.winId())
        dwm = ctypes.windll.dwmapi
        on = ctypes.c_int(1)
        dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(on), ctypes.sizeof(on))   # DWMWA_USE_IMMERSIVE_DARK_MODE
        caption = ctypes.c_int(0x0020100B)  # COLORREF is 0x00BBGGRR, so this is BG #0B1020
        dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(caption), ctypes.sizeof(caption))  # DWMWA_CAPTION_COLOR
    except (AttributeError, OSError):
        pass
