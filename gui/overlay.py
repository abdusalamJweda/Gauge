from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QSystemTrayIcon, QMenu
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon, QAction

from core.network import NetworkSensor
from gui.theme import OV_BG


class _MetricWidget(QWidget):
    """Single metric: a label pair (prefix + value) with a separator."""

    def __init__(self, prefix_text, font_size, small_size, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        self._prefix = QLabel(f"{prefix_text}")
        self._prefix.setFont(QFont("Consolas", small_size))
        self._prefix.setStyleSheet("color: #475569; background: transparent;")
        row.addWidget(self._prefix)

        self._value = QLabel("--")
        self._value.setFont(QFont("Consolas", font_size))
        self._value.setStyleSheet("color: #94a3b8; background: transparent;")
        row.addWidget(self._value)

        self.value_label = self._value

    def set_prefix(self, text):
        self._prefix.setText(text)


class OverlayWindow(QWidget):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self._drag_data = {"x": 0, "y": 0}
        self._font_size = config.get("overlay", {}).get("font_size", 12)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        ov = self.config.get("overlay", {})
        self._apply_opacity(ov)
        self._build_ui(ov)
        self._position_window(ov)
        self.hide()

    # ── UI ────────────────────────────────────────────────────────────
    def _build_ui(self, ov):
        font_size = ov.get("font_size", 12)
        small_size = max(8, font_size - 2)
        self._font_size = font_size

        self._outer = QWidget(self)
        self._outer.setObjectName("ov_bg")
        self._outer.setStyleSheet(
            f"QWidget#ov_bg {{ background-color: {ov.get('bg_color', OV_BG)}; "
            f"border-radius: 8px; border: 1px solid rgba(255,255,255,0.06); }}"
        )

        hlay = QHBoxLayout(self._outer)
        hlay.setContentsMargins(14, 8, 14, 8)
        hlay.setSpacing(0)

        self._metrics = {}
        keys = ["cpu", "gpu", "ram", "fps", "net"]
        labels = {"cpu": "CPU", "gpu": "GPU", "ram": "RAM", "fps": "FPS", "net": "NET"}

        self._populate_metrics(hlay, keys, labels, font_size, small_size)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._outer)

    def _populate_metrics(self, layout, keys, labels, font_size, small_size):
        for i, key in enumerate(keys):
            mw = _MetricWidget(labels[key], font_size, small_size)
            self._metrics[key] = mw.value_label
            layout.addWidget(mw)

            for w in [mw, mw._prefix, mw._value]:
                w.mousePressEvent = self._on_press
                w.mouseMoveEvent = self._on_drag

            if i < len(keys) - 1:
                sep = QLabel()
                sep.setFixedWidth(1)
                sep.setContentsMargins(8, 4, 8, 4)
                sep.setStyleSheet("background-color: rgba(255,255,255,0.08);")
                layout.addWidget(sep)

                sep.mousePressEvent = self._on_press
                sep.mouseMoveEvent = self._on_drag

    # ── Opacity ───────────────────────────────────────────────────────
    def _apply_opacity(self, ov):
        opacity = ov.get("opacity", 0.85)
        self.setWindowOpacity(max(0.2, min(1.0, opacity)))

    # ── Positioning ───────────────────────────────────────────────────
    def _screen_geo(self):
        s = self.screen()
        return s.availableGeometry() if s else None

    def _position_window(self, ov):
        self.adjustSize()
        geo = self._screen_geo()
        if geo is None:
            return
        sw, sh = geo.width(), geo.height()
        w, h = self.width(), self.height()
        margin = 14
        position = ov.get("position", "top-right")

        if position == "top-left":
            x, y = geo.x() + margin, geo.y() + margin
        elif position == "bottom-right":
            x, y = geo.x() + sw - w - margin, geo.y() + sh - h - margin
        elif position == "bottom-left":
            x, y = geo.x() + margin, geo.y() + sh - h - margin
        else:  # top-right (default)
            x, y = geo.x() + sw - w - margin, geo.y() + margin

        self.move(x, y)

    def _clamp_to_screen(self):
        geo = self._screen_geo()
        if geo is None:
            return
        margin = 4
        x, y = self.x(), self.y()
        w, h = self.width(), self.height()

        max_x = geo.x() + geo.width() - w - margin
        min_x = geo.x() + margin
        max_y = geo.y() + geo.height() - h - margin
        min_y = geo.y() + margin

        x = max(min_x, min(x, max_x))
        y = max(min_y, min(y, max_y))
        self.move(x, y)

    # ── Drag ──────────────────────────────────────────────────────────
    def _on_press(self, event):
        self._drag_data["x"] = event.globalPosition().x() - self.x()
        self._drag_data["y"] = event.globalPosition().y() - self.y()

    def _on_drag(self, event):
        x = event.globalPosition().x() - self._drag_data["x"]
        y = event.globalPosition().y() - self._drag_data["y"]
        self.move(int(x), int(y))

    # ── Data update ───────────────────────────────────────────────────
    def _fmt_temp(self, temp):
        if temp is None:
            return ""
        return f" {temp:.0f}\u00b0"

    def update_values(self, snap):
        ov = self.config.get("overlay", {})

        if ov.get("show_cpu", True) and snap.cpu_usage is not None:
            c = self._color(snap.cpu_usage, 65, 85)
            temp = self._fmt_temp(snap.cpu_temp)
            self._metrics["cpu"].setText(f"{snap.cpu_usage:.0f}%{temp}")
            self._metrics["cpu"].setStyleSheet(f"color: {c}; background: transparent;")
        else:
            self._metrics["cpu"].setText("")

        if ov.get("show_gpu", True) and snap.gpu_usage is not None:
            c = self._color(snap.gpu_usage, 75, 90)
            temp = self._fmt_temp(snap.gpu_temp)
            self._metrics["gpu"].setText(f"{snap.gpu_usage:.0f}%{temp}")
            self._metrics["gpu"].setStyleSheet(f"color: {c}; background: transparent;")
        else:
            self._metrics["gpu"].setText("")

        if ov.get("show_ram", True):
            c = self._color(snap.ram_percent, 70, 90)
            self._metrics["ram"].setText(f"{snap.ram_percent:.0f}%")
            self._metrics["ram"].setStyleSheet(f"color: {c}; background: transparent;")
        else:
            self._metrics["ram"].setText("")

        if ov.get("show_fps", True) and snap.fps is not None:
            c = "#22c55e" if snap.fps >= 60 else "#f59e0b" if snap.fps >= 30 else "#ef4444"
            self._metrics["fps"].setText(f"{snap.fps:.0f}")
            self._metrics["fps"].setStyleSheet(f"color: {c}; background: transparent;")
        else:
            self._metrics["fps"].setText("")

        if ov.get("show_net", True) and snap.network:
            down = snap.network.get("download_speed_bps", 0)
            up = snap.network.get("upload_speed_bps", 0)
            net_text = f"\u2193{NetworkSensor.format_speed(down)} \u2191{NetworkSensor.format_speed(up)}"
            self._metrics["net"].setText(net_text)
            self._metrics["net"].setStyleSheet("color: #60a5fa; background: transparent;")
        else:
            self._metrics["net"].setText("")

        self.adjustSize()
        self._clamp_to_screen()

    # ── Helpers ───────────────────────────────────────────────────────
    @staticmethod
    def _color(value, warn, crit):
        if value >= crit:
            return "#ef4444"
        if value >= warn:
            return "#f59e0b"
        return "#22c55e"

    # ── Config ────────────────────────────────────────────────────────
    def apply_config(self, overlay_cfg):
        self.config["overlay"] = overlay_cfg
        bg = overlay_cfg.get("bg_color", OV_BG)
        self._outer.setStyleSheet(
            f"QWidget#ov_bg {{ background-color: {bg}; "
            f"border-radius: 8px; border: 1px solid rgba(255,255,255,0.06); }}"
        )
        self._apply_opacity(overlay_cfg)
        new_font = overlay_cfg.get("font_size", 12)
        if new_font != self._font_size:
            self._rebuild_ui(overlay_cfg)
            self.adjustSize()
        self._position_window(overlay_cfg)

    def _rebuild_ui(self, ov):
        layout = self._outer.layout()
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._metrics.clear()
        font_size = ov.get("font_size", 12)
        small_size = max(8, font_size - 2)
        self._font_size = font_size
        keys = ["cpu", "gpu", "ram", "fps", "net"]
        labels = {"cpu": "CPU", "gpu": "GPU", "ram": "RAM", "fps": "FPS", "net": "NET"}
        self._populate_metrics(layout, keys, labels, font_size, small_size)

    def show_overlay(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def hide_overlay(self):
        self.hide()


class TrayIcon:
    def __init__(self, app, on_show, on_quit, icon_path=None):
        self._app = app
        self._on_show = on_show
        self._on_quit = on_quit
        self._tray = QSystemTrayIcon()
        if icon_path:
            self._tray.setIcon(QIcon(icon_path))
        menu = QMenu()
        show_action = QAction("Show Gauge", menu)
        show_action.triggered.connect(on_show)
        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(on_quit)
        menu.addAction(show_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_activated)
        self._tray.show()

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._on_show()

    def stop(self):
        self._tray.hide()
