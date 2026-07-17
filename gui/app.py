import customtkinter as ctk
import threading
from typing import Optional
from core.sensors import SensorSnapshot
from gui.overlay import OverlayWindow
from gui.overlay_settings import OverlaySettingsDialog


class ComponentCard(ctk.CTkFrame):
    def __init__(self, master, title: str, lines: int = 2, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(1, weight=1)

        self.title_label = ctk.CTkLabel(
            self, text=title, font=ctk.CTkFont(size=14, weight="bold"),
            width=70, anchor="nw"
        )
        self.title_label.grid(row=0, column=0, rowspan=lines, padx=(10, 5), pady=8, sticky="nw")

        self._detail_labels = []
        for i in range(lines):
            lbl = ctk.CTkLabel(
                self, text="--", font=ctk.CTkFont(size=11),
                anchor="w", text_color="#ccc"
            )
            lbl.grid(row=i, column=1, padx=5, pady=(6 if i == 0 else 0, 0), sticky="w")
            self._detail_labels.append(lbl)

        bar_row = lines
        self.progress = ctk.CTkProgressBar(self, width=200, height=12)
        self.progress.grid(row=bar_row, column=0, columnspan=2, padx=10, pady=(4, 8), sticky="ew")
        self.progress.set(0)

    def update_values(self, details: list, progress: float, color: str = "#22c55e"):
        for i, text in enumerate(details):
            if i < len(self._detail_labels):
                self._detail_labels[i].configure(text=text)
        self.progress.set(max(0, min(1, progress)))
        if progress > 0.85:
            self.progress.configure(progress_color="#ef4444")
        elif progress > 0.65:
            self.progress.configure(progress_color="#f59e0b")
        else:
            self.progress.configure(progress_color=color)


class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, master, config: dict, on_save=None):
        super().__init__(master)
        self.title("Settings")
        self.geometry("400x520")
        self.resizable(False, False)
        self.config = config
        self.on_save = on_save
        self.grab_set()

        ctk.CTkLabel(self, text="Settings", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(15, 10))

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(frame, text="Polling Interval (seconds):").pack(anchor="w")
        self.interval_slider = ctk.CTkSlider(
            frame, from_=1, to=5, number_of_steps=4,
            command=lambda v: self.interval_label.configure(text=f"{v:.0f}s")
        )
        self.interval_slider.set(config.get("polling_interval_seconds", 1))
        self.interval_slider.pack(fill="x", pady=(0, 5))
        self.interval_label = ctk.CTkLabel(frame, text=f"{config.get('polling_interval_seconds', 1)}s")
        self.interval_label.pack(anchor="w")

        ctk.CTkLabel(frame, text="Temperature Unit:").pack(anchor="w", pady=(10, 0))
        self.unit_var = ctk.StringVar(value=config.get("temperature_unit", "C"))
        unit_frame = ctk.CTkFrame(frame, fg_color="transparent")
        unit_frame.pack(fill="x", pady=5)
        ctk.CTkRadioButton(unit_frame, text="Celsius", variable=self.unit_var, value="C").pack(side="left", padx=10)
        ctk.CTkRadioButton(unit_frame, text="Fahrenheit", variable=self.unit_var, value="F").pack(side="left", padx=10)

        ctk.CTkLabel(frame, text="CPU Alert Threshold (C):").pack(anchor="w", pady=(10, 0))
        self.cpu_thresh_entry = ctk.CTkEntry(frame, placeholder_text="85")
        self.cpu_thresh_entry.insert(0, str(config.get("alerts", {}).get("cpu_temp_threshold_c", 85)))
        self.cpu_thresh_entry.pack(fill="x", pady=5)

        ctk.CTkLabel(frame, text="GPU Alert Threshold (C):").pack(anchor="w", pady=(10, 0))
        self.gpu_thresh_entry = ctk.CTkEntry(frame, placeholder_text="83")
        self.gpu_thresh_entry.insert(0, str(config.get("alerts", {}).get("gpu_temp_threshold_c", 83)))
        self.gpu_thresh_entry.pack(fill="x", pady=5)

        ctk.CTkLabel(frame, text="Alert Cooldown (seconds):").pack(anchor="w", pady=(10, 0))
        self.cooldown_entry = ctk.CTkEntry(frame, placeholder_text="300")
        self.cooldown_entry.insert(0, str(config.get("alerts", {}).get("cooldown_seconds", 300)))
        self.cooldown_entry.pack(fill="x", pady=5)

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(15, 0))
        ctk.CTkButton(btn_frame, text="Save", command=self._save).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy, fg_color="#555").pack(side="left", padx=5)

    def _save(self):
        try:
            self.config["polling_interval_seconds"] = int(float(self.interval_slider.get()))
            self.config["temperature_unit"] = self.unit_var.get()
            if "alerts" not in self.config:
                self.config["alerts"] = {}
            self.config["alerts"]["cpu_temp_threshold_c"] = int(self.cpu_thresh_entry.get())
            self.config["alerts"]["gpu_temp_threshold_c"] = int(self.gpu_thresh_entry.get())
            self.config["alerts"]["cooldown_seconds"] = int(self.cooldown_entry.get())
            if self.on_save:
                self.on_save(self.config)
            self.destroy()
        except ValueError:
            pass


class MainWindow(ctk.CTk):
    def __init__(self, aggregator, config, csv_logger, alert_manager, save_config_fn):
        super().__init__()
        self.aggregator = aggregator
        self.config = config
        self.csv_logger = csv_logger
        self.alert_manager = alert_manager
        self.save_config_fn = save_config_fn

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.title("Gauge")
        self.geometry("600x620")
        self.minsize(540, 520)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._tray_icon = None
        self.overlay = OverlayWindow(self, self.config)
        self._overlay_visible = self.config.get("overlay", {}).get("enabled", False)
        self._build_ui()
        self._start_update_loop()
        if self._overlay_visible:
            self.after(200, self.overlay.show_overlay)
            self._update_overlay_btn()

    def _build_ui(self):
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.cpu_card = ComponentCard(main_frame, "CPU", lines=3)
        self.cpu_card.pack(fill="x", pady=3)

        self.gpu_card = ComponentCard(main_frame, "GPU", lines=3)
        self.gpu_card.pack(fill="x", pady=3)

        self.ram_card = ComponentCard(main_frame, "RAM", lines=3)
        self.ram_card.pack(fill="x", pady=3)

        self.disk_card = ComponentCard(main_frame, "DISK", lines=3)
        self.disk_card.pack(fill="x", pady=3)

        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(10, 0))

        self.log_btn = ctk.CTkButton(
            btn_frame, text="Start Log", width=120,
            command=self._toggle_logging, fg_color="#2563eb"
        )
        self.log_btn.pack(side="left", padx=5)

        self.settings_btn = ctk.CTkButton(
            btn_frame, text="Settings", width=120,
            command=self._open_settings, fg_color="#555"
        )
        self.settings_btn.pack(side="left", padx=5)

        self.overlay_btn = ctk.CTkButton(
            btn_frame, text="Overlay", width=80,
            command=self._toggle_overlay, fg_color="#555"
        )
        self.overlay_btn.pack(side="left", padx=(10, 2))

        self.overlay_settings_btn = ctk.CTkButton(
            btn_frame, text="\u2699", width=28, height=28,
            command=self._open_overlay_settings, fg_color="#444",
            font=ctk.CTkFont(size=16)
        )
        self.overlay_settings_btn.pack(side="left", padx=0)

        self.status_label = ctk.CTkLabel(
            btn_frame, text="Ready", font=ctk.CTkFont(size=11),
            text_color="#888"
        )
        self.status_label.pack(side="right", padx=5)

    def _fmt_temp(self, celsius: Optional[float]) -> str:
        if celsius is None:
            return "N/A"
        unit = self.config.get("temperature_unit", "C")
        if unit == "F":
            return f"{celsius * 9/5 + 32:.0f}F"
        return f"{celsius:.0f}C"

    def _fmt_size(self, gb: float) -> str:
        if gb >= 1024:
            return f"{gb / 1024:.1f} TB"
        return f"{gb:.1f} GB"

    def _temp_color(self, temp: Optional[float], threshold: float) -> str:
        if temp is None:
            return "#888"
        if temp >= threshold:
            return "#ef4444"
        if temp >= threshold - 15:
            return "#f59e0b"
        return "#22c55e"

    def _update_display(self, snap: SensorSnapshot):
        if snap.cpu_usage is not None:
            line1 = f"Usage: {snap.cpu_usage:.0f}%   |   Temp: {self._fmt_temp(snap.cpu_temp)}"
            line2 = f"Frequency: {snap.cpu_freq:.0f} MHz   |   Cores: {snap.cpu_cores} threads" if snap.cpu_freq else f"Cores: {snap.cpu_cores} threads"
            line3 = snap.cpu_model or "CPU"
            self.cpu_card.update_values(
                [line1, line2, line3],
                snap.cpu_usage / 100,
                color=self._temp_color(snap.cpu_temp, self.alert_manager.cpu_threshold)
            )
        else:
            self.cpu_card.update_values(["No data available", "", ""], 0)

        if snap.gpu_name:
            line1 = f"Usage: {snap.gpu_usage or 0:.0f}%   |   Temp: {self._fmt_temp(snap.gpu_temp)}"
            vram_pct = snap.gpu_vram_percent or 0
            line2 = f"VRAM: {snap.gpu_vram_used or 0:.0f} / {snap.gpu_vram_total or 0:.0f} MB  ({vram_pct:.0f}%)"
            line3 = snap.gpu_name
            self.gpu_card.update_values(
                [line1, line2, line3],
                (snap.gpu_usage or 0) / 100,
                color=self._temp_color(snap.gpu_temp, self.alert_manager.gpu_threshold)
            )
        else:
            self.gpu_card.update_values(["No NVIDIA GPU detected", "", ""], 0)

        line1 = f"Used: {self._fmt_size(snap.ram_used)} / {self._fmt_size(snap.ram_total)}   ({snap.ram_percent:.0f}%)"
        line2 = f"Available: {self._fmt_size(snap.ram_available)}   |   Free: {self._fmt_size(snap.ram_total - snap.ram_used)}"
        ram_info_parts = []
        if snap.ram_ddr_type:
            ram_info_parts.append(snap.ram_ddr_type)
        if snap.ram_speed_mhz:
            ram_info_parts.append(f"{snap.ram_speed_mhz} MHz")
        if snap.ram_modules:
            ram_info_parts.append(f"{snap.ram_modules} sticks")
        if snap.ram_manufacturer:
            ram_info_parts.append(snap.ram_manufacturer.strip())
        line3 = " | ".join(ram_info_parts) if ram_info_parts else "RAM"
        self.ram_card.update_values(
            [line1, line2, line3],
            snap.ram_percent / 100,
            color="#22c55e"
        )

        if snap.disks:
            d = snap.disks[0]
            line1 = f"{d['device']}  |  {self._fmt_size(d['used_gb'])} / {self._fmt_size(d['total_gb'])}  ({d['percent']:.0f}%)"
            line2 = f"Free: {self._fmt_size(d['free_gb'])}  |  {d['fstype']}"
            temp_str = self._fmt_temp(d.get("temp_celsius")) if d.get("temp_celsius") is not None else "N/A"
            line3 = f"Temp: {temp_str}"
            self.disk_card.update_values(
                [line1, line2, line3],
                d["percent"] / 100,
                color=self._temp_color(d.get("temp_celsius"), 70)
            )
        else:
            self.disk_card.update_values(["No disks detected", "", ""], 0)

    def _on_snapshot(self, snap: SensorSnapshot):
        self.after(0, self._update_display, snap)
        if self._overlay_visible:
            self.after(0, self.overlay.update_values, snap)

        alerts = self.alert_manager.check(snap)
        for alert in alerts:
            self.after(0, self._show_alert, alert)

    def _show_alert(self, alert: dict):
        from core.alerts import send_notification
        send_notification("Hardware Alert", alert["message"])
        self.status_label.configure(text=f"Alert: {alert['message'][:40]}...", text_color="#ef4444")
        self.after(8000, lambda: self.status_label.configure(text="Monitoring", text_color="#888"))

    def _start_update_loop(self):
        self.aggregator.register_callback(self._on_snapshot)
        self.aggregator.start()

    def _toggle_logging(self):
        if self.csv_logger._running:
            self.csv_logger.stop()
            self.log_btn.configure(text="Start Log", fg_color="#2563eb")
            self.status_label.configure(text="Logging stopped", text_color="#888")
        else:
            self.csv_logger.set_aggregator(self.aggregator)
            self.csv_logger.start()
            self.log_btn.configure(text="Stop Log", fg_color="#dc2626")
            self.status_label.configure(text="Logging...", text_color="#22c55e")

    def _open_settings(self):
        SettingsDialog(self, self.config, on_save=self._on_settings_save)

    def _on_settings_save(self, new_config):
        self.config.update(new_config)
        self.save_config_fn(self.config)
        self.aggregator.update_interval(new_config["polling_interval_seconds"])
        self.alert_manager.cpu_threshold = new_config.get("alerts", {}).get("cpu_temp_threshold_c", 85)
        self.alert_manager.gpu_threshold = new_config.get("alerts", {}).get("gpu_temp_threshold_c", 83)
        self.alert_manager.cooldown = new_config.get("alerts", {}).get("cooldown_seconds", 300)
        self.status_label.configure(text="Settings saved", text_color="#22c55e")
        self.after(3000, lambda: self.status_label.configure(text="Monitoring", text_color="#888"))

    def set_tray_icon(self, icon):
        self._tray_icon = icon

    def _toggle_overlay(self):
        self._overlay_visible = not self._overlay_visible
        self.config.setdefault("overlay", {})["enabled"] = self._overlay_visible
        self.save_config_fn(self.config)
        if self._overlay_visible:
            self.overlay.apply_config(self.config.get("overlay", {}))
            self.overlay.show_overlay()
        else:
            self.overlay.hide_overlay()
        self._update_overlay_btn()

    def _update_overlay_btn(self):
        if self._overlay_visible:
            self.overlay_btn.configure(text="Overlay", fg_color="#7c3aed")
        else:
            self.overlay_btn.configure(text="Overlay", fg_color="#555")

    def _open_overlay_settings(self):
        OverlaySettingsDialog(
            self,
            self.config.get("overlay", {}),
            on_save=self._on_overlay_settings_save,
        )

    def _on_overlay_settings_save(self, new_overlay_cfg):
        self.config["overlay"] = new_overlay_cfg
        self.save_config_fn(self.config)
        self.overlay.apply_config(new_overlay_cfg)
        self.status_label.configure(text="Overlay settings saved", text_color="#22c55e")
        self.after(3000, lambda: self.status_label.configure(text="Monitoring", text_color="#888"))

    def _on_close(self):
        if self._tray_icon:
            self._tray_icon.stop()
        self.overlay.destroy()
        self.aggregator.stop()
        self.csv_logger.stop()
        self.destroy()
