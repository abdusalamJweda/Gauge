from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QFrame, QScrollArea, QProgressBar, QWidget
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from core.network import NetworkSensor
from gui.theme import (
    BG_DARK, BG_CARD, ACCENT, GREEN, YELLOW, RED, TEXT_PRIMARY,
    TEXT_SECONDARY, TEXT_MUTED, ROW_BG, BORDER, label_font, mono_font, temp_color
)


def _icon_path():
    import os
    from core.sensors import get_assets_dir
    p = os.path.join(get_assets_dir(), "gauge.ico")
    return p if os.path.exists(p) else None


class AdvancedWindow(QDialog):
    def __init__(self, aggregator, config, parent=None):
        super().__init__(parent)
        self.aggregator = aggregator
        self.config = config
        self.setWindowTitle("Gauge \u2014 Advanced")
        self.setMinimumSize(900, 680)
        self.resize(900, 680)
        self.setStyleSheet(f"background-color: {BG_DARK};")

        icon = _icon_path()
        if icon:
            try:
                from PySide6.QtGui import QIcon
                self.setWindowIcon(QIcon(icon))
            except Exception:
                pass

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        self._build_overview()
        self._build_cpu_detail()
        self._build_gpu_detail()
        self._build_motherboard()
        self._build_network()
        self._build_storage()
        self._build_processes()
        self._build_benchmark()

        self._update_loop()

    def _make_tab(self, name):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        vl = QVBoxLayout(content)
        vl.setContentsMargins(10, 10, 10, 10)
        vl.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(content)
        self._tabs.addTab(scroll, name)
        return content

    def _section_title(self, parent, text):
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {ACCENT};")
        parent.layout().addWidget(lbl)

    def _make_row(self, parent, label, font_size=12):
        frame = QFrame()
        frame.setStyleSheet(f"QFrame {{ background-color: {ROW_BG}; border-radius: 4px; }}")
        hl = QHBoxLayout(frame)
        hl.setContentsMargins(8, 4, 8, 4)
        lbl = QLabel(label)
        lbl.setFixedWidth(180)
        lbl.setFont(QFont("Segoe UI", font_size))
        lbl.setStyleSheet(f"color: #888;")
        hl.addWidget(lbl)
        val = QLabel("--")
        val.setFont(QFont("Segoe UI", font_size))
        val.setStyleSheet(f"color: #eee;")
        hl.addWidget(val, 1)
        parent.layout().addWidget(frame)
        return val

    def _build_overview(self):
        tab = self._make_tab("Overview")
        self._section_title(tab, "Session Min / Max / Avg")

        self._overview_rows = {}
        for key, label in [
            ("cpu_usage", "CPU Usage (%)"), ("cpu_temp", "CPU Temp (C)"),
            ("gpu_usage", "GPU Usage (%)"), ("gpu_temp", "GPU Temp (C)"),
            ("gpu_vram", "GPU VRAM (%)"), ("ram_percent", "RAM Usage (%)"),
        ]:
            frame = QFrame()
            frame.setStyleSheet(f"QFrame {{ background-color: {ROW_BG}; border-radius: 4px; }}")
            hl = QHBoxLayout(frame)
            hl.setContentsMargins(6, 3, 6, 3)
            lbl = QLabel(label)
            lbl.setFixedWidth(140)
            lbl.setFont(QFont("Segoe UI", 11))
            lbl.setStyleSheet("color: #888;")
            hl.addWidget(lbl)
            min_lbl = QLabel("--")
            min_lbl.setFixedWidth(70)
            min_lbl.setFont(QFont("Consolas", 11))
            min_lbl.setStyleSheet(f"color: {RED};")
            hl.addWidget(min_lbl)
            avg_lbl = QLabel("--")
            avg_lbl.setFixedWidth(70)
            avg_lbl.setFont(QFont("Consolas", 11))
            avg_lbl.setStyleSheet(f"color: {YELLOW};")
            hl.addWidget(avg_lbl)
            max_lbl = QLabel("--")
            max_lbl.setFixedWidth(70)
            max_lbl.setFont(QFont("Consolas", 11))
            max_lbl.setStyleSheet(f"color: {GREEN};")
            hl.addWidget(max_lbl)
            tab.layout().addWidget(frame)
            self._overview_rows[key] = (min_lbl, avg_lbl, max_lbl)

        btn = QPushButton("Reset Min/Max")
        btn.setFixedWidth(120)
        btn.setStyleSheet(f"background-color: #555; color: {TEXT_SECONDARY};")
        btn.clicked.connect(self.aggregator.reset_min_max)
        tab.layout().addWidget(btn)
        tab.layout().addStretch()

    def _build_cpu_detail(self):
        tab = self._make_tab("CPU Detail")
        self._section_title(tab, "Per-Core Usage")
        self._core_bars = []
        for i in range(32):
            frame = QFrame()
            frame.setStyleSheet(f"QFrame {{ background-color: {ROW_BG}; border-radius: 3px; }}")
            hl = QHBoxLayout(frame)
            hl.setContentsMargins(6, 2, 6, 2)
            lbl = QLabel(f"Core {i}")
            lbl.setFixedWidth(60)
            lbl.setFont(QFont("Segoe UI", 10))
            lbl.setStyleSheet("color: #888;")
            hl.addWidget(lbl)
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(0)
            bar.setFixedHeight(10)
            bar.setTextVisible(False)
            bar.setStyleSheet(f"QProgressBar {{ border: none; background: {ROW_BG}; border-radius: 2px; }} QProgressBar::chunk {{ border-radius: 2px; background: {GREEN}; }}")
            hl.addWidget(bar, 1)
            val_lbl = QLabel("--")
            val_lbl.setFixedWidth(50)
            val_lbl.setFont(QFont("Consolas", 10))
            val_lbl.setStyleSheet("color: #aaa;")
            hl.addWidget(val_lbl)
            tab.layout().addWidget(frame)
            self._core_bars.append((frame, bar, val_lbl))

        self._section_title(tab, "CPU Info")
        self._cpu_freq_lbl = self._make_row(tab, "Frequency")
        self._cpu_cores_lbl = self._make_row(tab, "Logical Cores")
        self._cpu_phys_lbl = self._make_row(tab, "Physical Cores")
        tab.layout().addStretch()

    def _build_gpu_detail(self):
        tab = self._make_tab("GPU Detail")
        self._section_title(tab, "GPU Information")
        self._gpu_name_lbl = self._make_row(tab, "GPU Name")
        self._gpu_vendor_lbl = self._make_row(tab, "Vendor")
        self._gpu_usage_lbl = self._make_row(tab, "Usage (%)")
        self._gpu_temp_lbl = self._make_row(tab, "Temperature (C)")
        self._gpu_vram_used_lbl = self._make_row(tab, "VRAM Used")
        self._gpu_vram_total_lbl = self._make_row(tab, "VRAM Total")
        self._gpu_clock_lbl = self._make_row(tab, "Core Clock (MHz)")
        self._gpu_fan_lbl = self._make_row(tab, "Fan Speed (%)")
        self._gpu_power_lbl = self._make_row(tab, "Power Draw (W)")
        tab.layout().addStretch()

    def _build_motherboard(self):
        tab = self._make_tab("Motherboard")
        self._section_title(tab, "Fan Speeds (RPM)")
        self._fan_rows_frame = tab
        self._section_title(tab, "Voltage Rails")
        self._voltage_rows_frame = tab
        tab.layout().addStretch()

    def _build_network(self):
        tab = self._make_tab("Network")
        self._section_title(tab, "Network Activity")
        self._net_upload_lbl = self._make_row(tab, "Upload Speed")
        self._net_download_lbl = self._make_row(tab, "Download Speed")
        self._net_total_sent_lbl = self._make_row(tab, "Total Sent")
        self._net_total_recv_lbl = self._make_row(tab, "Total Received")
        self._net_pkts_sent_lbl = self._make_row(tab, "Packets Sent")
        self._net_pkts_recv_lbl = self._make_row(tab, "Packets Received")
        tab.layout().addStretch()

    def _build_storage(self):
        tab = self._make_tab("Storage")
        self._section_title(tab, "Drive Health (S.M.A.R.T.)")
        self._storage_rows_frame = tab
        tab.layout().addStretch()

    def _build_processes(self):
        tab = self._make_tab("Processes")
        self._section_title(tab, "Top Processes by CPU")

        hdr = QFrame()
        hdr.setStyleSheet(f"QFrame {{ background-color: {ROW_BG}; border-radius: 4px; }}")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(6, 4, 6, 4)
        for txt, w in [("PID", 60), ("Name", 200), ("CPU %", 80), ("RAM %", 80)]:
            l = QLabel(txt)
            l.setFixedWidth(w)
            l.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            l.setStyleSheet(f"color: {ACCENT};")
            hl.addWidget(l)
        tab.layout().addWidget(hdr)

        self._proc_rows = []
        for i in range(10):
            frame = QFrame()
            frame.setStyleSheet(f"QFrame {{ background-color: {ROW_BG}; border-radius: 3px; }}")
            pl = QHBoxLayout(frame)
            pl.setContentsMargins(6, 2, 6, 2)
            pid = QLabel("--"); pid.setFixedWidth(60); pid.setFont(QFont("Consolas", 10)); pid.setStyleSheet("color: #aaa;")
            name = QLabel("--"); name.setFixedWidth(200); name.setFont(QFont("Segoe UI", 10)); name.setStyleSheet("color: #eee;")
            cpu = QLabel("--"); cpu.setFixedWidth(80); cpu.setFont(QFont("Consolas", 10)); cpu.setStyleSheet(f"color: {GREEN};")
            mem = QLabel("--"); mem.setFixedWidth(80); mem.setFont(QFont("Consolas", 10)); mem.setStyleSheet(f"color: {YELLOW};")
            for w in [pid, name, cpu, mem]:
                pl.addWidget(w)
            tab.layout().addWidget(frame)
            self._proc_rows.append((pid, name, cpu, mem))
        tab.layout().addStretch()

    def _build_benchmark(self):
        tab = self._make_tab("Benchmark")
        self._section_title(tab, "Quick Benchmark")

        info = QLabel("Click Start to begin recording min/max/avg.\nClick Stop to see results.")
        info.setFont(QFont("Segoe UI", 11))
        info.setStyleSheet(f"color: #888;")
        tab.layout().addWidget(info)

        btn_frame = QHBoxLayout()
        self._bench_start_btn = QPushButton("Start Benchmark")
        self._bench_start_btn.setFixedWidth(140)
        self._bench_start_btn.setStyleSheet(f"background-color: {GREEN}; color: white;")
        self._bench_start_btn.clicked.connect(self._start_benchmark)
        self._bench_stop_btn = QPushButton("Stop")
        self._bench_stop_btn.setFixedWidth(100)
        self._bench_stop_btn.setStyleSheet(f"background-color: {RED}; color: white;")
        self._bench_stop_btn.setEnabled(False)
        self._bench_stop_btn.clicked.connect(self._stop_benchmark)
        btn_frame.addWidget(self._bench_start_btn)
        btn_frame.addWidget(self._bench_stop_btn)
        btn_frame.addStretch()
        tab.layout().addLayout(btn_frame)

        self._bench_status = QLabel("")
        self._bench_status.setFont(QFont("Segoe UI", 11))
        self._bench_status.setStyleSheet(f"color: #888;")
        tab.layout().addWidget(self._bench_status)
        self._bench_results_frame = tab
        self._bench_start_time = None
        tab.layout().addStretch()

    def _start_benchmark(self):
        import time
        self.aggregator.reset_min_max()
        self._bench_start_time = time.time()
        self._bench_start_btn.setEnabled(False)
        self._bench_stop_btn.setEnabled(True)
        self._bench_status.setText("Benchmarking... (collecting data)")
        self._bench_status.setStyleSheet(f"color: {GREEN};")

    def _stop_benchmark(self):
        import time
        elapsed = time.time() - self._bench_start_time if self._bench_start_time else 0
        self._bench_start_btn.setEnabled(True)
        self._bench_stop_btn.setEnabled(False)
        self._bench_status.setText(f"Benchmark complete \u2014 {elapsed:.1f}s")
        self._bench_status.setStyleSheet(f"color: {ACCENT};")

        mm = self.aggregator.min_max
        for key, label in [
            ("cpu_usage", "CPU Usage (%)"), ("cpu_temp", "CPU Temp (C)"),
            ("gpu_usage", "GPU Usage (%)"), ("gpu_temp", "GPU Temp (C)"),
            ("ram_percent", "RAM Usage (%)"),
        ]:
            if key not in mm:
                continue
            data = mm[key]
            frame = QFrame()
            frame.setStyleSheet(f"QFrame {{ background-color: {ROW_BG}; border-radius: 4px; }}")
            hl = QHBoxLayout(frame)
            hl.setContentsMargins(6, 3, 6, 3)
            lbl = QLabel(label); lbl.setFixedWidth(120); lbl.setFont(QFont("Segoe UI", 11)); lbl.setStyleSheet("color: #888;")
            minl = QLabel(f"Min: {data['min']:.1f}"); minl.setFixedWidth(80); minl.setFont(QFont("Consolas", 11)); minl.setStyleSheet(f"color: {RED};")
            avgl = QLabel(f"Avg: {data['avg']:.1f}"); avgl.setFixedWidth(80); avgl.setFont(QFont("Consolas", 11)); avgl.setStyleSheet(f"color: {YELLOW};")
            maxl = QLabel(f"Max: {data['max']:.1f}"); maxl.setFixedWidth(80); maxl.setFont(QFont("Consolas", 11)); maxl.setStyleSheet(f"color: {GREEN};")
            for w in [lbl, minl, avgl, maxl]:
                hl.addWidget(w)
            self._bench_results_frame.layout().addWidget(frame)
        self._bench_start_time = None

    def _update_loop(self):
        if not self.isVisible():
            QTimer.singleShot(1000, self._update_loop)
            return
        snap = self.aggregator.snapshot
        if snap.timestamp > 0:
            self._update_overview(snap)
            self._update_cpu_detail(snap)
            self._update_gpu_detail(snap)
            self._update_motherboard(snap)
            self._update_network(snap)
            self._update_storage(snap)
            self._update_processes(snap)
        QTimer.singleShot(1000, self._update_loop)

    def _update_overview(self, snap):
        mm = self.aggregator.min_max
        mapping = {
            "cpu_usage": ("cpu_usage", "%"), "cpu_temp": ("cpu_temp", "C"),
            "gpu_usage": ("gpu_usage", "%"), "gpu_temp": ("gpu_temp", "C"),
            "gpu_vram": ("gpu_vram_percent", "%"), "ram_percent": ("ram_percent", "%"),
        }
        for key, (mm_key, unit) in mapping.items():
            if mm_key in mm:
                d = mm[mm_key]
                row = self._overview_rows.get(key)
                if row:
                    row[0].setText(f"{d['min']:.1f}{unit}")
                    row[1].setText(f"{d['avg']:.1f}{unit}")
                    row[2].setText(f"{d['max']:.1f}{unit}")

    def _update_cpu_detail(self, snap):
        per_core = snap.cpu_per_core_usage or []
        for i, (frame, bar, val_lbl) in enumerate(self._core_bars):
            if i < len(per_core):
                frame.show()
                usage = per_core[i]
                bar.setValue(int(usage))
                val_lbl.setText(f"{usage:.0f}%")
                if usage > 85:
                    bar.setStyleSheet(f"QProgressBar::chunk {{ background: {RED}; border-radius: 2px; }}")
                elif usage > 65:
                    bar.setStyleSheet(f"QProgressBar::chunk {{ background: {YELLOW}; border-radius: 2px; }}")
                else:
                    bar.setStyleSheet(f"QProgressBar::chunk {{ background: {GREEN}; border-radius: 2px; }}")
            else:
                frame.hide()
        if snap.cpu_freq:
            self._cpu_freq_lbl.setText(f"{snap.cpu_freq:.0f} MHz")
        self._cpu_cores_lbl.setText(str(snap.cpu_cores))

    def _update_gpu_detail(self, snap):
        self._gpu_name_lbl.setText(snap.gpu_name or "N/A")
        self._gpu_vendor_lbl.setText(snap.gpu_vendor or "N/A")
        self._gpu_usage_lbl.setText(f"{snap.gpu_usage:.1f}%" if snap.gpu_usage is not None else "N/A")
        self._gpu_temp_lbl.setText(f"{snap.gpu_temp:.1f}C" if snap.gpu_temp is not None else "N/A")
        self._gpu_vram_used_lbl.setText(f"{snap.gpu_vram_used:.0f} MB" if snap.gpu_vram_used is not None else "N/A")
        self._gpu_vram_total_lbl.setText(f"{snap.gpu_vram_total:.0f} MB" if snap.gpu_vram_total is not None else "N/A")
        self._gpu_clock_lbl.setText(f"{snap.gpu_clock_mhz:.0f}" if snap.gpu_clock_mhz is not None else "N/A")
        self._gpu_fan_lbl.setText(f"{snap.gpu_fan_percent:.0f}%" if snap.gpu_fan_percent is not None else "N/A")
        self._gpu_power_lbl.setText(f"{snap.gpu_power_w:.1f}" if snap.gpu_power_w is not None else "N/A")

    def _update_motherboard(self, snap):
        for w in self._fan_rows_frame.findChildren(QFrame):
            if hasattr(w, "_is_fan_row"):
                w.deleteLater()
        fans = snap.fans or []
        if not fans:
            lbl = QLabel("No fan sensors detected (requires admin)")
            lbl._is_fan_row = True
            lbl.setStyleSheet(f"color: #666; font-size: 10px;")
            self._fan_rows_frame.layout().addWidget(lbl)
        else:
            for f in fans:
                frame = QFrame()
                frame._is_fan_row = True
                frame.setStyleSheet(f"QFrame {{ background-color: {ROW_BG}; border-radius: 3px; }}")
                hl = QHBoxLayout(frame)
                hl.setContentsMargins(6, 2, 6, 2)
                n = QLabel(f["label"]); n.setStyleSheet("color: #aaa;"); n.setFont(QFont("Segoe UI", 10)); hl.addWidget(n)
                r = QLabel(f"{f['rpm']:.0f} RPM"); r.setStyleSheet(f"color: {GREEN};"); r.setFont(QFont("Segoe UI", 10)); hl.addWidget(r)
                self._fan_rows_frame.layout().addWidget(frame)

        for w in self._voltage_rows_frame.findChildren(QFrame):
            if hasattr(w, "_is_voltage_row"):
                w.deleteLater()
        voltages = snap.voltages or []
        if not voltages:
            lbl = QLabel("No voltage sensors detected (requires admin)")
            lbl._is_voltage_row = True
            lbl.setStyleSheet(f"color: #666; font-size: 10px;")
            self._voltage_rows_frame.layout().addWidget(lbl)
        else:
            for v in voltages:
                frame = QFrame()
                frame._is_voltage_row = True
                frame.setStyleSheet(f"QFrame {{ background-color: {ROW_BG}; border-radius: 3px; }}")
                hl = QHBoxLayout(frame)
                hl.setContentsMargins(6, 2, 6, 2)
                n = QLabel(v["label"]); n.setStyleSheet("color: #aaa;"); n.setFont(QFont("Segoe UI", 10)); hl.addWidget(n)
                r = QLabel(f"{v['volts']:.3f} V"); r.setStyleSheet(f"color: {ACCENT};"); r.setFont(QFont("Segoe UI", 10)); hl.addWidget(r)
                self._voltage_rows_frame.layout().addWidget(frame)

    def _update_network(self, snap):
        net = snap.network or {}
        up = net.get("upload_speed_bps", 0)
        down = net.get("download_speed_bps", 0)
        self._net_upload_lbl.setText(NetworkSensor.format_speed(up))
        self._net_download_lbl.setText(NetworkSensor.format_speed(down))
        self._net_total_sent_lbl.setText(f"{net.get('total_sent_gb', 0):.2f} GB")
        self._net_total_recv_lbl.setText(f"{net.get('total_recv_gb', 0):.2f} GB")
        self._net_pkts_sent_lbl.setText(str(net.get("packets_sent", 0)))
        self._net_pkts_recv_lbl.setText(str(net.get("packets_recv", 0)))

    def _update_storage(self, snap):
        for w in self._storage_rows_frame.findChildren(QFrame):
            if hasattr(w, "_is_storage_row"):
                w.deleteLater()
        drives = snap.storage_drives or []
        if not drives:
            lbl = QLabel("No S.M.A.R.T. data (requires admin + LHM)")
            lbl._is_storage_row = True
            lbl.setStyleSheet(f"color: #666; font-size: 10px;")
            self._storage_rows_frame.layout().addWidget(lbl)
        else:
            for d in drives:
                frame = QFrame()
                frame._is_storage_row = True
                frame.setStyleSheet(f"QFrame {{ background-color: {ROW_BG}; border-radius: 4px; }}")
                vl = QVBoxLayout(frame)
                vl.setContentsMargins(8, 4, 8, 4)
                name = QLabel(d["name"]); name.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold)); name.setStyleSheet("color: #eee;")
                vl.addWidget(name)
                hl = QHBoxLayout()
                health = d.get("health_percent")
                temp = d.get("temp_celsius")
                h_color = GREEN if health and health > 80 else YELLOW if health and health > 50 else RED
                h = QLabel(f"Health: {health:.0f}%" if health else "Health: N/A")
                h.setStyleSheet(f"color: {h_color};"); h.setFont(QFont("Segoe UI", 10)); hl.addWidget(h)
                t = QLabel(f"Temp: {temp:.0f}C" if temp else "Temp: N/A")
                t.setStyleSheet("color: #aaa;"); t.setFont(QFont("Segoe UI", 10)); hl.addWidget(t)
                vl.addLayout(hl)
                self._storage_rows_frame.layout().addWidget(frame)

    def _update_processes(self, snap):
        procs = snap.top_processes or []
        for i, (pid_lbl, name_lbl, cpu_lbl, mem_lbl) in enumerate(self._proc_rows):
            if i < len(procs):
                p = procs[i]
                pid_lbl.setText(str(p["pid"]))
                name_lbl.setText(p["name"][:25])
                cpu_lbl.setText(f"{p['cpu_percent']:.1f}%")
                mem_lbl.setText(f"{p['memory_percent']:.1f}%")
            else:
                pid_lbl.setText("--")
                name_lbl.setText("")
                cpu_lbl.setText("--")
                mem_lbl.setText("--")
