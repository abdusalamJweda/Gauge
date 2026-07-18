from PySide6.QtGui import QFont


ACCENT = "#60a5fa"
ACCENT_DIM = "#3b82f6"
BG_DARK = "#0f172a"
BG_CARD = "#1e293b"
TEXT_PRIMARY = "#f1f5f9"
TEXT_SECONDARY = "#94a3b8"
TEXT_MUTED = "#64748b"
GREEN = "#22c55e"
YELLOW = "#f59e0b"
RED = "#ef4444"
PURPLE = "#a78bfa"
GRAPH_BG = "#0d1117"
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

