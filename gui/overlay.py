from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QSystemTrayIcon, QMenu
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QFont, QIcon, QAction

from core.network import NetworkSensor
from gui.theme import BG_DARK, OV_BG, TEXT_MUTED


class OverlayWindow(QWidget):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self._drag_data = {"x": 0, "y": 0}

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

    def _build_ui(self, ov):
        font_size = ov.get("font_size", 12)
        small_font_size = max(8, font_size - 2)

        self._outer = QWidget(self)
        self._outer.setStyleSheet(f"background-color: {ov.get('bg_color', OV_BG)}; border-radius: 6px;")

        layout = QHBoxLayout(self._outer)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        self._metrics = {}
        for key, default_prefix in [("cpu", "CPU"), ("gpu", "GPU"), ("ram", "RAM"), ("fps", "FPS"), ("net", "NET")]:
            container = QWidget()
            container.setStyleSheet("background: transparent;")
            vl = QHBoxLayout(container)
            vl.setContentsMargins(0, 0, 0, 0)
            vl.setSpacing(0)

            prefix = QLabel(f"{default_prefix}:")
            prefix.setFont(QFont("Consolas", small_font_size))
            prefix.setStyleSheet("color: #475569; background: transparent;")
            vl.addWidget(prefix)

            value = QLabel("--")
            value.setFont(QFont("Consolas", font_size))
            value.setStyleSheet("color: #94a3b8; background: transparent;")
            vl.addWidget(value)

            self._metrics[key] = value
            layout.addWidget(container)

            for w in [container, prefix, value]:
                w.mousePressEvent = self._on_press
                w.mouseMoveEvent = self._on_drag

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(self._outer)

    def _apply_opacity(self, ov):
        opacity = ov.get("opacity", 0.85)
        self.setWindowOpacity(max(0.3, min(1.0, opacity)))

    def _position_window(self, ov):
        position = ov.get("position", "top-right")
        self.adjustSize()
        sw = self.screen().availableGeometry().width()
        sh = self.screen().availableGeometry().height()
        w, h = self.width(), self.height()
        margin = 12
        positions = {
            "top-right": (sw - w - margin, margin),
            "top-left": (margin, margin),
            "bottom-right": (sw - w - margin, sh - h - margin),
            "bottom-left": (margin, sh - h - margin),
        }
        x, y = positions.get(position, positions["top-right"])
        self.move(max(0, x), max(0, y))

    def _on_press(self, event):
        self._drag_data["x"] = event.globalPosition().x() - self.x()
        self._drag_data["y"] = event.globalPosition().y() - self.y()

    def _on_drag(self, event):
        x = event.globalPosition().x() - self._drag_data["x"]
        y = event.globalPosition().y() - self._drag_data["y"]
        self.move(int(x), int(y))

    def update_values(self, snap):
        ov = self.config.get("overlay", {})

        if ov.get("show_cpu", True) and snap.cpu_usage is not None:
            c = self._color(snap.cpu_usage, 65, 85)
            self._metrics["cpu"].setText(f"{snap.cpu_usage:.0f}%")
            self._metrics["cpu"].setStyleSheet(f"color: {c}; background: transparent;")
        else:
            self._metrics["cpu"].setText("")

        if ov.get("show_gpu", True) and snap.gpu_usage is not None:
            c = self._color(snap.gpu_usage, 75, 90)
            self._metrics["gpu"].setText(f"{snap.gpu_usage:.0f}%")
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

    @staticmethod
    def _color(value, warn, crit):
        if value >= crit:
            return "#ef4444"
        if value >= warn:
            return "#f59e0b"
        return "#22c55e"

    def apply_config(self, overlay_cfg):
        self.config["overlay"] = overlay_cfg
        bg = overlay_cfg.get("bg_color", OV_BG)
        self._outer.setStyleSheet(f"background-color: {bg}; border-radius: 6px;")
        self._apply_opacity(overlay_cfg)
        self._position_window(overlay_cfg)

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
