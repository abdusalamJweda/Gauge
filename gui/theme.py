from PySide6.QtGui import QColor, QFont


ACCENT = "#60a5fa"
ACCENT_DIM = "#3b82f6"
BG_DARK = "#0f172a"
BG_CARD = "#1e293b"
BG_CARD_HOVER = "#253349"
TEXT_PRIMARY = "#f1f5f9"
TEXT_SECONDARY = "#94a3b8"
TEXT_MUTED = "#64748b"
GREEN = "#22c55e"
YELLOW = "#f59e0b"
RED = "#ef4444"
PURPLE = "#a78bfa"
GRAPH_BG = "#0d1117"
GRAPH_FILL = "#1a1a2e"
ROW_BG = "#161622"
BORDER = "#2d3a4f"
OV_BG = "#0f172a"


def header_font(size=20, bold=True):
    return QFont("Segoe UI", size, QFont.Weight.Bold if bold else QFont.Weight.Normal)


def label_font(family="Segoe UI", size=11, bold=False):
    return QFont(family, size, QFont.Weight.Bold if bold else QFont.Weight.Normal)


def mono_font(size=11):
    return QFont("Consolas", size)


def temp_color(temp, threshold):
    if temp is None:
        return TEXT_MUTED
    if temp >= threshold:
        return RED
    if temp >= threshold - 15:
        return YELLOW
    return GREEN


def progress_color(pct, temp=None, threshold=85):
    if temp is not None:
        return temp_color(temp, threshold)
    if pct > 85:
        return RED
    if pct > 65:
        return YELLOW
    return GREEN


DARK_STYLESHEET = """
QMainWindow, QDialog {
    background-color: #0f172a;
}
QWidget {
    color: #f1f5f9;
}
QScrollArea {
    border: none;
    background-color: transparent;
}
QScrollBar:vertical {
    background: #0f172a;
    width: 8px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #334155;
    min-height: 30px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #475569;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}
QPushButton {
    background-color: #334155;
    color: #94a3b8;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-family: "Segoe UI";
    font-size: 12px;
}
QPushButton:hover {
    background-color: #475569;
}
QPushButton:pressed {
    background-color: #1e293b;
}
QProgressBar {
    border: none;
    border-radius: 3px;
    background-color: #1a2332;
    height: 6px;
    text-align: center;
}
QProgressBar::chunk {
    border-radius: 3px;
}
QTabWidget::pane {
    border: 1px solid #2d3a4f;
    border-radius: 6px;
    background-color: #1a1a2e;
}
QTabBar::tab {
    background-color: #1e293b;
    color: #94a3b8;
    padding: 8px 16px;
    border: 1px solid #2d3a4f;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
    font-family: "Segoe UI";
    font-size: 11px;
}
QTabBar::tab:selected {
    background-color: #1a1a2e;
    color: #60a5fa;
}
QTabBar::tab:hover:!selected {
    background-color: #253349;
}
QRadioButton {
    color: #94a3b8;
    spacing: 8px;
}
QRadioButton::indicator {
    width: 14px;
    height: 14px;
    border-radius: 7px;
    border: 2px solid #334155;
    background-color: transparent;
}
QRadioButton::indicator:checked {
    border-color: #60a5fa;
    background-color: #60a5fa;
}
QLineEdit {
    background-color: #1a2332;
    border: 1px solid #2d3a4f;
    border-radius: 4px;
    padding: 6px 10px;
    color: #f1f5f9;
    font-family: "Consolas";
    font-size: 12px;
}
QLineEdit:focus {
    border-color: #60a5fa;
}
QSlider::groove:horizontal {
    border: none;
    height: 4px;
    background: #1a2332;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #60a5fa;
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}
QSlider::handle:horizontal:hover {
    background: #3b82f6;
}
QLabel {
    background-color: transparent;
}
"""
