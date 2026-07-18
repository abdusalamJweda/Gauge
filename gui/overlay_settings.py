from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QComboBox, QCheckBox, QWidget, QScrollArea,
    QFrame, QButtonGroup, QRadioButton
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from gui.theme import (
    BG_DARK, BG_CARD, ACCENT, ACCENT_DIM, TEXT_PRIMARY, TEXT_SECONDARY,
    TEXT_MUTED, BORDER
)

BG_COLORS = [
    ("#0f172a", "Deep Navy"),
    ("#1a1a2e", "Dark Navy"),
    ("#0d1117", "GitHub Dark"),
    ("#1e1e2e", "Catppuccin"),
    ("#282a36", "Dracula"),
]


class OverlaySettingsDialog(QDialog):
    saved = Signal(dict)

    def __init__(self, overlay_config, parent=None):
        super().__init__(parent)
        self.overlay_config = dict(overlay_config)
        self.setWindowTitle("Overlay Settings")
        self.setFixedSize(360, 580)
        self.setStyleSheet(f"background-color: {BG_DARK};")

        icon_path = self._icon_path()
        if icon_path:
            try:
                from PySide6.QtGui import QIcon
                self.setWindowIcon(QIcon(icon_path))
            except Exception:
                pass

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 10)

        title = QLabel("Overlay Settings")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {TEXT_PRIMARY};")
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

        self._section(cl, "Appearance")

        cl.addWidget(self._label("Opacity:"))
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(30, 100)
        self.opacity_slider.setValue(int(overlay_config.get("opacity", 0.85) * 100))
        self.opacity_slider.setStyleSheet(self._slider_css())
        self.opacity_slider.valueChanged.connect(
            lambda v: self.opacity_lbl.setText(f"{v}%")
        )
        cl.addWidget(self.opacity_slider)
        self.opacity_lbl = QLabel(f"{self.opacity_slider.value()}%")
        self.opacity_lbl.setFont(QFont("Consolas", 11))
        self.opacity_lbl.setStyleSheet(f"color: {TEXT_MUTED};")
        cl.addWidget(self.opacity_lbl)

        cl.addWidget(self._label("Position:"))
        self.position_combo = QComboBox()
        self.position_combo.addItems(["top-right", "top-left", "bottom-right", "bottom-left"])
        pos = overlay_config.get("position", "top-right")
        idx = self.position_combo.findText(pos)
        if idx >= 0:
            self.position_combo.setCurrentIndex(idx)
        self.position_combo.setStyleSheet(self._combo_css())
        cl.addWidget(self.position_combo)

        cl.addWidget(self._label("Font Size:"))
        self.font_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_slider.setRange(10, 16)
        self.font_slider.setValue(overlay_config.get("font_size", 12))
        self.font_slider.setStyleSheet(self._slider_css())
        self.font_slider.valueChanged.connect(
            lambda v: self.font_lbl.setText(str(v))
        )
        cl.addWidget(self.font_slider)
        self.font_lbl = QLabel(str(self.font_slider.value()))
        self.font_lbl.setFont(QFont("Consolas", 11))
        self.font_lbl.setStyleSheet(f"color: {TEXT_MUTED};")
        cl.addWidget(self.font_lbl)

        cl.addWidget(self._label("Background Color:"))
        self.bg_group = QButtonGroup(self)
        for i, (hex_val, name) in enumerate(BG_COLORS):
            rb = QRadioButton(name)
            rb.setStyleSheet(f"color: {TEXT_SECONDARY};")
            self.bg_group.addButton(rb, i)
            cl.addWidget(rb)
            if hex_val == overlay_config.get("bg_color", "#0f172a"):
                rb.setChecked(True)

        self._section(cl, "Visible Metrics")

        self.cpu_chk = QCheckBox("CPU")
        self.cpu_chk.setChecked(overlay_config.get("show_cpu", True))
        self.cpu_chk.setStyleSheet(self._checkbox_css())
        cl.addWidget(self.cpu_chk)

        self.gpu_chk = QCheckBox("GPU")
        self.gpu_chk.setChecked(overlay_config.get("show_gpu", True))
        self.gpu_chk.setStyleSheet(self._checkbox_css())
        cl.addWidget(self.gpu_chk)

        self.ram_chk = QCheckBox("RAM")
        self.ram_chk.setChecked(overlay_config.get("show_ram", True))
        self.ram_chk.setStyleSheet(self._checkbox_css())
        cl.addWidget(self.ram_chk)

        self.fps_chk = QCheckBox("FPS")
        self.fps_chk.setChecked(overlay_config.get("show_fps", True))
        self.fps_chk.setStyleSheet(self._checkbox_css())
        cl.addWidget(self.fps_chk)

        self.net_chk = QCheckBox("Network Speed")
        self.net_chk.setChecked(overlay_config.get("show_net", True))
        self.net_chk.setStyleSheet(self._checkbox_css())
        cl.addWidget(self.net_chk)

        cl.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        btn_frame = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.setFixedSize(110, 36)
        save_btn.setStyleSheet(f"""
            QPushButton {{ background-color: {ACCENT}; color: {BG_DARK}; font-weight: bold;
                border-radius: 8px; font-family: "Segoe UI"; font-size: 12px; }}
            QPushButton:hover {{ background-color: {ACCENT_DIM}; }}
        """)
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedSize(110, 36)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{ background-color: #334155; color: {TEXT_SECONDARY};
                border-radius: 8px; font-family: "Segoe UI"; font-size: 12px; }}
            QPushButton:hover {{ background-color: #475569; }}
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_frame.addWidget(save_btn)
        btn_frame.addWidget(cancel_btn)
        btn_frame.addStretch()
        layout.addLayout(btn_frame)

    def _section(self, layout, text):
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {ACCENT}; padding-top: 14px;")
        layout.addWidget(lbl)

    def _label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")
        return lbl

    def _save(self):
        self.overlay_config["opacity"] = round(self.opacity_slider.value() / 100.0, 2)
        self.overlay_config["position"] = self.position_combo.currentText()
        self.overlay_config["font_size"] = self.font_slider.value()
        btn = self.bg_group.checkedButton()
        if btn:
            for hex_val, name in BG_COLORS:
                if name == btn.text():
                    self.overlay_config["bg_color"] = hex_val
                    break
        self.overlay_config["show_cpu"] = self.cpu_chk.isChecked()
        self.overlay_config["show_gpu"] = self.gpu_chk.isChecked()
        self.overlay_config["show_ram"] = self.ram_chk.isChecked()
        self.overlay_config["show_fps"] = self.fps_chk.isChecked()
        self.overlay_config["show_net"] = self.net_chk.isChecked()
        self.saved.emit(self.overlay_config)
        self.accept()

    @staticmethod
    def _slider_css():
        return f"""
            QSlider::groove:horizontal {{ border: none; height: 4px; background: #1a2332; border-radius: 2px; }}
            QSlider::handle:horizontal {{ background: {ACCENT}; width: 16px; height: 16px; margin: -6px 0; border-radius: 8px; }}
        """

    @staticmethod
    def _combo_css():
        return f"""
            QComboBox {{ background-color: #1a2332; border: 1px solid #2d3a4f; border-radius: 4px;
                         padding: 6px 10px; color: {TEXT_PRIMARY}; font-family: "Segoe UI"; font-size: 12px; }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox::down-arrow {{ image: none; }}
            QComboBox QAbstractItemView {{ background-color: {BG_CARD}; color: {TEXT_PRIMARY}; selection-background-color: #253349; }}
        """

    @staticmethod
    def _checkbox_css():
        return f"""
            QCheckBox {{ color: {TEXT_SECONDARY}; spacing: 8px; }}
            QCheckBox::indicator {{ width: 18px; height: 18px; border: 2px solid #2d3a4f; border-radius: 4px; background: #1a2332; }}
            QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}
        """

    @staticmethod
    def _icon_path():
        import os
        from core.sensors import get_assets_dir
        p = os.path.join(get_assets_dir(), "gauge.ico")
        return p if os.path.exists(p) else None
