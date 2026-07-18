import os
import threading
import time
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QProgressBar, QComboBox
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QThread
from PySide6.QtGui import QFont, QIcon

from core.sensors import get_assets_dir
from core.alerts import send_notification
from gui.graphs import MiniGraphSet
from gui.settings import SettingsDialog
from gui.advanced import AdvancedWindow
from gui.overlay import OverlayWindow, TrayIcon
from gui.theme import (
    BG_DARK, BG_CARD, ACCENT, ACCENT_DIM, GREEN, YELLOW, RED,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, PURPLE, BORDER,
    header_font, label_font, mono_font, progress_color, temp_color
)


def _icon_path():
    p = os.path.join(get_assets_dir(), "gauge.ico")
    return p if os.path.exists(p) else None


class HeaderBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)
        self.setStyleSheet(f"background-color: {BG_CARD}; border: none;")
        hl = QHBoxLayout(self)
        hl.setContentsMargins(16, 0, 16, 0)

        icon_file = os.path.join(get_assets_dir(), "gauge.png")
        if os.path.exists(icon_file):
            from PySide6.QtGui import QPixmap
            pixmap = QPixmap(icon_file).scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio,
                                                Qt.TransformationMode.SmoothTransformation)
            icon_lbl = QLabel()
            icon_lbl.setPixmap(pixmap)
            hl.addWidget(icon_lbl)

        title = QLabel("Gauge")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT_PRIMARY};")
        hl.addWidget(title)

        subtitle = QLabel("Hardware Monitor")
        subtitle.setFont(QFont("Segoe UI", 11))
        subtitle.setStyleSheet(f"color: {TEXT_MUTED};")
        hl.addWidget(subtitle)
        hl.addStretch()


class ComponentCard(QFrame):
    def __init__(self, title, icon_text, lines=3, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 12px;
            }}
        """)
        self._lines = lines

        hl = QHBoxLayout(self)
        hl.setContentsMargins(14, 12, 14, 12)
        hl.setSpacing(10)

        left = QVBoxLayout()
        left.setSpacing(2)
        icon_lbl = QLabel(icon_text)
        icon_lbl.setFont(QFont("Segoe UI", 18))
        icon_lbl.setStyleSheet(f"color: {ACCENT};")
        left.addWidget(icon_lbl)
        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {TEXT_PRIMARY};")
        left.addWidget(title_lbl)
        hl.addLayout(left)

        right = QVBoxLayout()
        right.setSpacing(2)
        self._detail_labels = []
        for i in range(lines):
            lbl = QLabel("--")
            lbl.setFont(QFont("Consolas", 11))
            lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
            right.addWidget(lbl)
            self._detail_labels.append(lbl)
        hl.addLayout(right, 1)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setValue(0)
        self.progress.setFixedHeight(6)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(f"""
            QProgressBar {{ border: none; border-radius: 3px; background-color: #1a2332; }}
            QProgressBar::chunk {{ border-radius: 3px; background-color: {ACCENT}; }}
        """)
        right.addWidget(self.progress)

    def update_values(self, details, progress, color=GREEN):
        for i, text in enumerate(details):
            if i < len(self._detail_labels):
                self._detail_labels[i].setText(text)
        self.progress.setValue(int(max(0, min(1, progress)) * 1000))
        c = progress_color(progress * 100, threshold=85) if color == GREEN else color
        if progress > 0.85:
            c = RED
        elif progress > 0.65:
            c = YELLOW
        else:
            c = color
        self.progress.setStyleSheet(f"""
            QProgressBar {{ border: none; border-radius: 3px; background-color: #1a2332; }}
            QProgressBar::chunk {{ border-radius: 3px; background-color: {c}; }}
        """)


class DiskCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 12px;
            }}
        """)
        self._disks = []
        self._selected_index = 0

        hl = QHBoxLayout(self)
        hl.setContentsMargins(14, 12, 14, 12)
        hl.setSpacing(10)

        left = QVBoxLayout()
        left.setSpacing(2)
        icon_lbl = QLabel("\U0001f4bf")
        icon_lbl.setFont(QFont("Segoe UI", 18))
        icon_lbl.setStyleSheet(f"color: {ACCENT};")
        left.addWidget(icon_lbl)
        title_lbl = QLabel("DISK")
        title_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {TEXT_PRIMARY};")
        left.addWidget(title_lbl)
        hl.addLayout(left)

        right = QVBoxLayout()
        right.setSpacing(2)

        self.part_combo = QComboBox()
        self.part_combo.setFixedHeight(28)
        self.part_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: #1a2332; border: 1px solid {BORDER}; border-radius: 4px;
                padding: 2px 8px; color: {TEXT_PRIMARY}; font-family: "Consolas"; font-size: 11px;
            }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox::down-arrow {{ image: none; border-left: 4px solid transparent; border-right: 4px solid transparent;
                                     border-top: 6px solid {TEXT_SECONDARY}; margin-right: 6px; }}
            QComboBox QAbstractItemView {{ background-color: {BG_CARD}; color: {TEXT_PRIMARY}; selection-background-color: #253349; border: 1px solid {BORDER}; }}
        """)
        self.part_combo.currentIndexChanged.connect(self._on_partition_changed)
        right.addWidget(self.part_combo)

        self._detail_labels = []
        for _ in range(2):
            lbl = QLabel("--")
            lbl.setFont(QFont("Consolas", 11))
            lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
            right.addWidget(lbl)
            self._detail_labels.append(lbl)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setValue(0)
        self.progress.setFixedHeight(6)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(f"""
            QProgressBar {{ border: none; border-radius: 3px; background-color: #1a2332; }}
            QProgressBar::chunk {{ border-radius: 3px; background-color: {ACCENT}; }}
        """)
        right.addWidget(self.progress)
        hl.addLayout(right, 1)

    def _on_partition_changed(self, index):
        self._selected_index = index
        if 0 <= index < len(self._disks):
            d = self._disks[index]
            self._refresh_display(d)

    def _refresh_display(self, d):
        fmt = self._fmt_size
        l1 = f"{d['device']}  |  {fmt(d['used_gb'])} / {fmt(d['total_gb'])}  ({d['percent']:.0f}%)"
        l2 = f"Free: {fmt(d['free_gb'])}  |   {d['fstype']}"
        self._detail_labels[0].setText(l1)
        self._detail_labels[1].setText(l2)
        pct = d["percent"] / 100
        self.progress.setValue(int(max(0, min(1, pct)) * 1000))
        c = temp_color(d.get("temp_celsius"), 70)
        self.progress.setStyleSheet(f"""
            QProgressBar {{ border: none; border-radius: 3px; background-color: #1a2332; }}
            QProgressBar::chunk {{ border-radius: 3px; background-color: {c}; }}
        """)

    def update_disks(self, disks):
        prev_text = self.part_combo.currentText() if self.part_combo.count() > 0 else ""
        self._disks = disks

        self.part_combo.blockSignals(True)
        self.part_combo.clear()
        for d in disks:
            self.part_combo.addItem(f"{d['device']}  ({d['fstype']})")
        self.part_combo.blockSignals(False)

        if disks:
            restore_idx = 0
            if prev_text:
                for i, d in enumerate(disks):
                    label = f"{d['device']}  ({d['fstype']})"
                    if label == prev_text:
                        restore_idx = i
                        break
            self.part_combo.setCurrentIndex(restore_idx)
            self._selected_index = restore_idx
            self._refresh_display(disks[restore_idx])
        else:
            for lbl in self._detail_labels:
                lbl.setText("--")
            self.progress.setValue(0)

    @staticmethod
    def _fmt_size(gb):
        if gb >= 1024:
            return f"{gb / 1024:.1f} TB"
        return f"{gb:.1f} GB"


class MainWindow(QMainWindow):
    def __init__(self, aggregator, config, csv_logger, alert_manager, save_config_fn):
        super().__init__()
        self.aggregator = aggregator
        self.config = config
        self.csv_logger = csv_logger
        self.alert_manager = alert_manager
        self.save_config_fn = save_config_fn

        self.setWindowTitle("Gauge")
        self.resize(640, 900)
        self.setMinimumSize(560, 700)
        self.setStyleSheet(f"background-color: {BG_DARK};")

        icon = _icon_path()
        if icon:
            self.setWindowIcon(QIcon(icon))

        self._overlay_visible = self.config.get("overlay", {}).get("enabled", False)
        self._advanced_window = None
        self._pending_snap = None
        self._is_resizing = False
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(200)
        self._resize_timer.timeout.connect(self._on_resize_settle)

        self._build_ui()
        self._setup_hotkeys()
        self._start_update_loop()

        self._overlay = OverlayWindow(self.config, self)
        if self._overlay_visible:
            QTimer.singleShot(200, self._overlay.show_overlay)

        self._tray = TrayIcon(None, self._show_from_tray, self._on_close, icon)

    def _build_ui(self):
        central = QWidget()
        central.setStyleSheet("background: transparent;")
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        main_layout.addWidget(HeaderBar())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(12, 8, 12, 12)
        cl.setSpacing(4)

        self.cpu_card = ComponentCard("CPU", "\u2699\ufe0f", lines=3)
        cl.addWidget(self.cpu_card)
        self.gpu_card = ComponentCard("GPU", "\U0001f5a5", lines=3)
        cl.addWidget(self.gpu_card)
        self.ram_card = ComponentCard("RAM", "\U0001f4e6", lines=3)
        cl.addWidget(self.ram_card)
        self.disk_card = DiskCard()
        cl.addWidget(self.disk_card)

        graphs_header = QLabel("Performance Graphs")
        graphs_header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        graphs_header.setStyleSheet(f"color: {ACCENT}; padding-top: 8px;")
        cl.addWidget(graphs_header)

        self.graphs = MiniGraphSet()
        cl.addWidget(self.graphs)

        btn_frame = QFrame()
        btn_frame.setStyleSheet(f"QFrame {{ background-color: {BG_CARD}; border-radius: 10px; }}")
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(10, 6, 10, 6)

        self.log_btn = self._make_btn("Start Log", ACCENT, "#0f172a", bold=True)
        self.log_btn.clicked.connect(self._toggle_logging)
        btn_layout.addWidget(self.log_btn)

        settings_btn = self._make_btn("Settings")
        settings_btn.clicked.connect(self._open_settings)
        btn_layout.addWidget(settings_btn)

        self.overlay_btn = self._make_btn("Overlay")
        self.overlay_btn.clicked.connect(self._toggle_overlay)
        btn_layout.addWidget(self.overlay_btn)

        overlay_settings_btn = self._make_btn("\u2699", width=34)
        overlay_settings_btn.clicked.connect(self._open_overlay_settings)
        btn_layout.addWidget(overlay_settings_btn)

        advanced_btn = self._make_btn("Advanced")
        advanced_btn.clicked.connect(self._open_advanced)
        btn_layout.addWidget(advanced_btn)

        self.status_label = QLabel("Ready")
        self.status_label.setFont(QFont("Consolas", 11))
        self.status_label.setStyleSheet(f"color: {TEXT_MUTED};")
        btn_layout.addWidget(self.status_label)
        btn_layout.addStretch()

        cl.addWidget(btn_frame)
        cl.addStretch()

        scroll.setWidget(content)
        main_layout.addWidget(scroll, 1)

        self._update_overlay_btn()

    def _make_btn(self, text, bg="#334155", fg=TEXT_SECONDARY, bold=False, width=None):
        btn = QPushButton(text)
        if width:
            btn.setFixedWidth(width)
        btn.setFixedHeight(34)
        weight = "bold" if bold else "normal"
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg}; color: {fg};
                border: none; border-radius: 8px;
                font-family: "Segoe UI"; font-size: 12px; font-weight: {weight};
                padding: 8px 16px;
            }}
            QPushButton:hover {{ background-color: #475569; }}
        """)
        return btn

    def _fmt_temp(self, celsius):
        if celsius is None:
            return "N/A"
        unit = self.config.get("temperature_unit", "C")
        if unit == "F":
            return f"{celsius * 9/5 + 32:.0f}\u00b0F"
        return f"{celsius:.0f}\u00b0C"

    def _fmt_size(self, gb):
        if gb >= 1024:
            return f"{gb / 1024:.1f} TB"
        return f"{gb:.1f} GB"

    def _update_display(self, snap):
        if snap.cpu_usage is not None:
            l1 = f"Usage: {snap.cpu_usage:.0f}%   |   Temp: {self._fmt_temp(snap.cpu_temp)}"
            l2 = f"Freq: {snap.cpu_freq:.0f} MHz   |   Cores: {snap.cpu_cores}" if snap.cpu_freq else f"Cores: {snap.cpu_cores}"
            l3 = snap.cpu_model or "CPU"
            self.cpu_card.update_values([l1, l2, l3], snap.cpu_usage / 100,
                                         color=temp_color(snap.cpu_temp, self.alert_manager.cpu_threshold))
        else:
            self.cpu_card.update_values(["No data available", "", ""], 0)

        if snap.gpu_name:
            l1 = f"Usage: {snap.gpu_usage or 0:.0f}%   |   Temp: {self._fmt_temp(snap.gpu_temp)}"
            vram_pct = snap.gpu_vram_percent or 0
            l2 = f"VRAM: {snap.gpu_vram_used or 0:.0f} / {snap.gpu_vram_total or 0:.0f} MB  ({vram_pct:.0f}%)"
            l3 = snap.gpu_name
            self.gpu_card.update_values([l1, l2, l3], (snap.gpu_usage or 0) / 100,
                                         color=temp_color(snap.gpu_temp, self.alert_manager.gpu_threshold))
        else:
            self.gpu_card.update_values(["No GPU detected", "", ""], 0)

        l1 = f"Used: {self._fmt_size(snap.ram_used)} / {self._fmt_size(snap.ram_total)}   ({snap.ram_percent:.0f}%)"
        l2 = f"Available: {self._fmt_size(snap.ram_available)}   |   Free: {self._fmt_size(snap.ram_total - snap.ram_used)}"
        ram_parts = []
        if snap.ram_ddr_type:
            ram_parts.append(snap.ram_ddr_type)
        if snap.ram_speed_mhz:
            ram_parts.append(f"{snap.ram_speed_mhz} MHz")
        if snap.ram_modules:
            ram_parts.append(f"{snap.ram_modules} sticks")
        if snap.ram_manufacturer:
            ram_parts.append(snap.ram_manufacturer.strip())
        l3 = " | ".join(ram_parts) if ram_parts else "RAM"
        self.ram_card.update_values([l1, l2, l3], snap.ram_percent / 100, color=GREEN)

        self.disk_card.update_disks(snap.disks or [])

    def _on_snapshot(self, snap):
        if self._is_resizing:
            self._pending_snap = snap
            return
        self._apply_snapshot(snap)

    def _apply_snapshot(self, snap):
        self._update_display(snap)
        self.graphs.update_from_snapshot(snap)
        if self._overlay_visible:
            self._overlay.update_values(snap)

    def _show_alert(self, alert):
        send_notification("Hardware Alert", alert["message"])
        self.status_label.setText(f"Alert: {alert['message'][:40]}...")
        self.status_label.setStyleSheet(f"color: {RED};")
        QTimer.singleShot(8000, lambda: (
            self.status_label.setText("Monitoring"),
            self.status_label.setStyleSheet(f"color: {TEXT_MUTED};"),
        ))

    def _start_update_loop(self):
        self._worker = SensorPollWorker(self.aggregator, self.config, self.alert_manager)
        self._worker_thread = QThread(self)
        self._worker.moveToThread(self._worker_thread)
        self._worker_thread.started.connect(self._worker.run)
        self._worker.snapshot_ready.connect(self._on_snapshot)
        self._worker.alert_ready.connect(self._show_alert)
        self._worker_thread.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._is_resizing = True
        self._resize_timer.start()

    def _on_resize_settle(self):
        self._is_resizing = False
        if self._pending_snap is not None:
            snap = self._pending_snap
            self._pending_snap = None
            self._apply_snapshot(snap)

    def _setup_hotkeys(self):
        try:
            import keyboard
            def run_in_thread(fn):
                def wrapper():
                    threading.Thread(target=fn, daemon=True).start()
                return wrapper
            keyboard.add_hotkey("ctrl+shift+o", run_in_thread(lambda: self._toggle_overlay()))
            keyboard.add_hotkey("ctrl+shift+m", run_in_thread(lambda: self._toggle_main_visibility()))
            keyboard.add_hotkey("ctrl+shift+a", run_in_thread(lambda: self._open_advanced()))
        except ImportError:
            pass

    def _toggle_logging(self):
        if self.csv_logger._running:
            self.csv_logger.stop()
            self.log_btn.setText("Start Log")
            self.log_btn.setStyleSheet(f"""
                QPushButton {{ background-color: {ACCENT}; color: #0f172a; border-radius: 8px;
                    font-family: "Segoe UI"; font-size: 12px; font-weight: bold; padding: 8px 16px; }}
                QPushButton:hover {{ background-color: {ACCENT_DIM}; }}
            """)
            self.status_label.setText("Logging stopped")
            self.status_label.setStyleSheet(f"color: {TEXT_MUTED};")
        else:
            self.csv_logger.set_aggregator(self.aggregator)
            self.csv_logger.start()
            self.log_btn.setText("Stop Log")
            self.log_btn.setStyleSheet(f"""
                QPushButton {{ background-color: {RED}; color: white; border-radius: 8px;
                    font-family: "Segoe UI"; font-size: 12px; font-weight: bold; padding: 8px 16px; }}
                QPushButton:hover {{ background-color: #dc2626; }}
            """)
            self.status_label.setText("Logging...")
            self.status_label.setStyleSheet(f"color: {GREEN};")

    def _open_settings(self):
        dlg = SettingsDialog(self.config.copy(), self)
        dlg.saved.connect(self._on_settings_save)
        dlg.exec()

    def _on_settings_save(self, new_config):
        self.config.update(new_config)
        self.save_config_fn(self.config)
        self.aggregator.update_interval(new_config["polling_interval_seconds"])
        self.alert_manager.cpu_threshold = new_config.get("alerts", {}).get("cpu_temp_threshold_c", 85)
        self.alert_manager.gpu_threshold = new_config.get("alerts", {}).get("gpu_temp_threshold_c", 83)
        self.alert_manager.cooldown = new_config.get("alerts", {}).get("cooldown_seconds", 300)
        self.status_label.setText("Settings saved")
        self.status_label.setStyleSheet(f"color: {GREEN};")
        QTimer.singleShot(3000, lambda: (
            self.status_label.setText("Monitoring"),
            self.status_label.setStyleSheet(f"color: {TEXT_MUTED};"),
        ))

    def _toggle_overlay(self):
        self._overlay_visible = not self._overlay_visible
        self.config.setdefault("overlay", {})["enabled"] = self._overlay_visible
        self.save_config_fn(self.config)
        if self._overlay_visible:
            self._overlay.apply_config(self.config.get("overlay", {}))
            self._overlay.show_overlay()
        else:
            self._overlay.hide_overlay()
        self._update_overlay_btn()

    def _update_overlay_btn(self):
        if self._overlay_visible:
            self.overlay_btn.setText("Overlay")
            self.overlay_btn.setStyleSheet(f"""
                QPushButton {{ background-color: {PURPLE}; color: white; border-radius: 8px;
                    font-family: "Segoe UI"; font-size: 12px; padding: 8px 16px; }}
                QPushButton:hover {{ background-color: #8b5cf6; }}
            """)
        else:
            self.overlay_btn.setText("Overlay")
            self.overlay_btn.setStyleSheet(f"""
                QPushButton {{ background-color: #334155; color: {TEXT_SECONDARY}; border-radius: 8px;
                    font-family: "Segoe UI"; font-size: 12px; padding: 8px 16px; }}
                QPushButton:hover {{ background-color: #475569; }}
            """)

    def _open_overlay_settings(self):
        from gui.overlay_settings import OverlaySettingsDialog
        dlg = OverlaySettingsDialog(self.config.get("overlay", {}), self)
        dlg.saved.connect(self._on_overlay_settings_save)
        dlg.exec()

    def _on_overlay_settings_save(self, new_cfg):
        self.config["overlay"] = new_cfg
        self.save_config_fn(self.config)
        self._overlay.apply_config(new_cfg)
        self.status_label.setText("Overlay settings saved")
        self.status_label.setStyleSheet(f"color: {GREEN};")
        QTimer.singleShot(3000, lambda: (
            self.status_label.setText("Monitoring"),
            self.status_label.setStyleSheet(f"color: {TEXT_MUTED};"),
        ))

    def _open_advanced(self):
        if self._advanced_window and self._advanced_window.isVisible():
            self._advanced_window.raise_()
            self._advanced_window.activateWindow()
            return
        self._advanced_window = AdvancedWindow(self.aggregator, self.config, self)
        self._advanced_window.show()

    def _toggle_main_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

    def _show_from_tray(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def _on_close(self):
        self._tray.stop()
        self._overlay.close()
        self.aggregator.stop()
        self.csv_logger.stop()
        self.close()


class SensorPollWorker(QObject):
    snapshot_ready = Signal(object)
    alert_ready = Signal(object)

    def __init__(self, aggregator, config, alert_manager):
        super().__init__()
        self.aggregator = aggregator
        self.config = config
        self.alert_manager = alert_manager
        self._running = True

    def run(self):
        self.aggregator.register_callback(self._on_poll_done)
        while self._running:
            try:
                self.aggregator._poll_once()
            except Exception:
                pass
            time.sleep(self.config.get("polling_interval_seconds", 1))
        self.aggregator.unregister_callback(self._on_poll_done)

    def _on_poll_done(self, snap):
        self.snapshot_ready.emit(snap)
        try:
            alerts = self.alert_manager.check(snap)
            for a in alerts:
                self.alert_ready.emit(a)
        except Exception:
            pass

    def stop(self):
        self._running = False
