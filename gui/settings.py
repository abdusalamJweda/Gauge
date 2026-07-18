from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QRadioButton, QLineEdit, QButtonGroup, QWidget, QScrollArea,
    QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from gui.theme import BG_DARK, ACCENT, ACCENT_DIM, TEXT_SECONDARY, TEXT_MUTED, label_font, mono_font


class SettingsDialog(QDialog):
    saved = Signal(dict)

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Settings")
        self.setFixedSize(420, 520)
        self.setStyleSheet(f"background-color: {BG_DARK};")

        icon_path = self._icon_path()
        if icon_path:
            try:
                from PySide6.QtGui import QIcon
                self.setWindowIcon(QIcon(icon_path))
            except Exception:
                pass

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 10)

        title = QLabel("Settings")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: #f1f5f9;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(0, 10, 0, 10)

        self._section(cl, "General")
        cl.addWidget(self._label("Polling Interval (seconds):"))
        self.interval_slider = QSlider(Qt.Orientation.Horizontal)
        self.interval_slider.setRange(1, 5)
        self.interval_slider.setValue(config.get("polling_interval_seconds", 1))
        self.interval_slider.setStyleSheet(self._slider_css())
        self.interval_slider.valueChanged.connect(
            lambda v: self.interval_lbl.setText(f"{v}s")
        )
        cl.addWidget(self.interval_slider)
        self.interval_lbl = QLabel(f"{self.interval_slider.value()}s")
        self.interval_lbl.setFont(QFont("Consolas", 11))
        self.interval_lbl.setStyleSheet(f"color: {TEXT_MUTED};")
        cl.addWidget(self.interval_lbl)

        cl.addWidget(self._label("Temperature Unit:"))
        unit_frame = QHBoxLayout()
        self.unit_group = QButtonGroup(self)
        self.unit_c = QRadioButton("Celsius")
        self.unit_f = QRadioButton("Fahrenheit")
        self.unit_c.setStyleSheet(f"color: {TEXT_SECONDARY};")
        self.unit_f.setStyleSheet(f"color: {TEXT_SECONDARY};")
        self.unit_group.addButton(self.unit_c, 0)
        self.unit_group.addButton(self.unit_f, 1)
        if config.get("temperature_unit", "C") == "F":
            self.unit_f.setChecked(True)
        else:
            self.unit_c.setChecked(True)
        unit_frame.addWidget(self.unit_c)
        unit_frame.addWidget(self.unit_f)
        unit_frame.addStretch()
        cl.addLayout(unit_frame)

        self._section(cl, "Alert Thresholds")
        cl.addWidget(self._label("CPU Alert Threshold (C):"))
        self.cpu_thresh = QLineEdit(str(config.get("alerts", {}).get("cpu_temp_threshold_c", 85)))
        self.cpu_thresh.setStyleSheet(self._entry_css())
        cl.addWidget(self.cpu_thresh)

        cl.addWidget(self._label("GPU Alert Threshold (C):"))
        self.gpu_thresh = QLineEdit(str(config.get("alerts", {}).get("gpu_temp_threshold_c", 83)))
        self.gpu_thresh.setStyleSheet(self._entry_css())
        cl.addWidget(self.gpu_thresh)

        cl.addWidget(self._label("Alert Cooldown (seconds):"))
        self.cooldown = QLineEdit(str(config.get("alerts", {}).get("cooldown_seconds", 300)))
        self.cooldown.setStyleSheet(self._entry_css())
        cl.addWidget(self.cooldown)

        cl.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        btn_frame = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.setFixedSize(120, 36)
        save_btn.setStyleSheet(f"background-color: {ACCENT}; color: #0f172a; font-weight: bold;")
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedSize(120, 36)
        cancel_btn.setStyleSheet(f"background-color: #334155; color: {TEXT_SECONDARY};")
        cancel_btn.clicked.connect(self.reject)
        btn_frame.addWidget(save_btn)
        btn_frame.addWidget(cancel_btn)
        btn_frame.addStretch()
        layout.addLayout(btn_frame)

    def _save(self):
        try:
            self.config["polling_interval_seconds"] = self.interval_slider.value()
            self.config["temperature_unit"] = "F" if self.unit_f.isChecked() else "C"
            if "alerts" not in self.config:
                self.config["alerts"] = {}
            self.config["alerts"]["cpu_temp_threshold_c"] = int(self.cpu_thresh.text())
            self.config["alerts"]["gpu_temp_threshold_c"] = int(self.gpu_thresh.text())
            self.config["alerts"]["cooldown_seconds"] = int(self.cooldown.text())
            self.saved.emit(self.config)
            self.accept()
        except ValueError:
            pass

    def _section(self, layout, text):
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {ACCENT}; padding-top: 14px;")
        layout.addWidget(lbl)

    def _label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
        return lbl

    @staticmethod
    def _slider_css():
        return f"""
            QSlider::groove:horizontal {{ border: none; height: 4px; background: #1a2332; border-radius: 2px; }}
            QSlider::handle:horizontal {{ background: {ACCENT}; width: 16px; height: 16px; margin: -6px 0; border-radius: 8px; }}
        """

    @staticmethod
    def _entry_css():
        return f"""
            QLineEdit {{ background-color: #1a2332; border: 1px solid #2d3a4f; border-radius: 4px;
                         padding: 6px 10px; color: #f1f5f9; font-family: Consolas; font-size: 12px; }}
            QLineEdit:focus {{ border-color: {ACCENT}; }}
        """

    @staticmethod
    def _icon_path():
        import os
        from core.sensors import get_assets_dir
        p = os.path.join(get_assets_dir(), "gauge.ico")
        return p if os.path.exists(p) else None
