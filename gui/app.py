import customtkinter as ctk
import tkinter
import threading
import os
from typing import Optional
from core.sensors import SensorSnapshot, get_assets_dir
from gui.overlay import OverlayWindow
from gui.overlay_settings import OverlaySettingsDialog
from gui.graphs import MiniGraphSet
from gui.advanced import AdvancedWindow


class ScrollableFrame(ctk.CTkFrame):
    """Lightweight scrollable container using plain tkinter Canvas."""
    def __init__(self, master, fg_color="#0f172a", **kwargs):
        super().__init__(master, fg_color=fg_color, **kwargs)
        self._canvas = tkinter.Canvas(self, bg=fg_color, highlightthickness=0, bd=0)
        self._scrollbar = ctk.CTkScrollbar(self, orientation="vertical", command=self._canvas.yview)
        self._inner = ctk.CTkFrame(self._canvas, fg_color="transparent")
        self._inner.bind("<Configure>", lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas_win = self._canvas.create_window((0, 0), window=self._inner, anchor="nw")
        self._canvas.configure(yscrollcommand=self._scrollbar.set)
        self._canvas.pack(side="left", fill="both", expand=True)
        self._scrollbar.pack(side="right", fill="y")
        self._canvas.bind("<Configure>", self._on_canvas_cfg)
        self._canvas.bind("<Enter>", lambda e: self._canvas.bind_all("<MouseWheel>", self._on_wheel))
        self._canvas.bind("<Leave>", lambda e: self._canvas.unbind_all("<MouseWheel>"))

    def _on_canvas_cfg(self, event):
        self._canvas.itemconfig(self._canvas_win, width=event.width)

    def _on_wheel(self, event):
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    @property
    def inner_frame(self):
        return self._inner


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


def _icon_path():
    return os.path.join(get_assets_dir(), "gauge.ico")


class HeaderBar(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_CARD, corner_radius=0, height=56, **kwargs)
        self.pack_propagate(False)

        icon_file = os.path.join(get_assets_dir(), "gauge.png")
        self._logo_img = None
        if os.path.exists(icon_file):
            from PIL import Image, ImageTk
            pil = Image.open(icon_file).resize((32, 32), Image.LANCZOS)
            self._logo_img = ImageTk.PhotoImage(pil)

        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", padx=16, pady=8)

        if self._logo_img:
            ctk.CTkLabel(left, image=self._logo_img, text="").pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            left, text="Gauge",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(side="left")

        ctk.CTkLabel(
            left, text="Hardware Monitor",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=TEXT_MUTED,
        ).pack(side="left", padx=(8, 0), pady=(4, 0))


class ComponentCard(ctk.CTkFrame):
    def __init__(self, master, title: str, icon_text: str, lines: int = 3, **kwargs):
        super().__init__(
            master,
            fg_color=BG_CARD,
            corner_radius=12,
            border_width=1,
            border_color="#2d3a4f",
            **kwargs,
        )
        self.grid_columnconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, rowspan=lines, padx=(14, 6), pady=(12, 0), sticky="nw")

        icon_lbl = ctk.CTkLabel(
            header, text=icon_text,
            font=ctk.CTkFont(size=18),
            text_color=ACCENT,
            width=28,
        )
        icon_lbl.pack(anchor="w")

        title_lbl = ctk.CTkLabel(
            header, text=title,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=TEXT_PRIMARY,
            width=70,
            anchor="w",
        )
        title_lbl.pack(anchor="w", pady=(2, 0))

        self._detail_labels = []
        for i in range(lines):
            lbl = ctk.CTkLabel(
                self, text="--",
                font=ctk.CTkFont(family="Consolas", size=11),
                anchor="w",
                text_color=TEXT_SECONDARY,
            )
            lbl.grid(row=i, column=1, padx=(4, 14), pady=(10 if i == 0 else 2, 0), sticky="w")
            self._detail_labels.append(lbl)

        bar_row = lines
        self.progress = ctk.CTkProgressBar(
            self, width=200, height=6,
            corner_radius=3,
            progress_color=ACCENT,
            fg_color="#1a2332",
        )
        self.progress.grid(row=bar_row, column=0, columnspan=2, padx=14, pady=(6, 12), sticky="ew")
        self.progress.set(0)

    def update_values(self, details: list, progress: float, color: str = GREEN):
        for i, text in enumerate(details):
            if i < len(self._detail_labels):
                self._detail_labels[i].configure(text=text)
        self.progress.set(max(0, min(1, progress)))
        if progress > 0.85:
            self.progress.configure(progress_color=RED)
        elif progress > 0.65:
            self.progress.configure(progress_color=YELLOW)
        else:
            self.progress.configure(progress_color=color)


class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, master, config: dict, on_save=None):
        super().__init__(master)
        self.title("Settings")
        self.geometry("420x560")
        self.resizable(False, False)
        self.configure(fg_color=BG_DARK)
        self.config = config
        self.on_save = on_save
        self.grab_set()

        icon = _icon_path()
        if os.path.exists(icon):
            try:
                self.iconbitmap(icon)
            except Exception:
                pass

        ctk.CTkLabel(
            self, text="Settings",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=TEXT_PRIMARY,
        ).pack(pady=(20, 12))

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        self._section_label(scroll, "General")
        ctk.CTkLabel(scroll, text="Polling Interval (seconds):", text_color=TEXT_SECONDARY).pack(anchor="w", pady=(4, 0))
        self.interval_slider = ctk.CTkSlider(
            scroll, from_=1, to=5, number_of_steps=4,
            progress_color=ACCENT,
            button_color=ACCENT,
            button_hover_color=ACCENT_DIM,
            command=lambda v: self.interval_label.configure(text=f"{v:.0f}s"),
        )
        self.interval_slider.set(config.get("polling_interval_seconds", 1))
        self.interval_slider.pack(fill="x", pady=(2, 2))
        self.interval_label = ctk.CTkLabel(
            scroll, text=f"{config.get('polling_interval_seconds', 1)}s",
            font=ctk.CTkFont(size=11), text_color=TEXT_MUTED,
        )
        self.interval_label.pack(anchor="w")

        ctk.CTkLabel(scroll, text="Temperature Unit:", text_color=TEXT_SECONDARY).pack(anchor="w", pady=(12, 0))
        self.unit_var = ctk.StringVar(value=config.get("temperature_unit", "C"))
        unit_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        unit_frame.pack(fill="x", pady=4)
        ctk.CTkRadioButton(unit_frame, text="Celsius", variable=self.unit_var, value="C",
                           fg_color=ACCENT, hover_color=ACCENT_DIM).pack(side="left", padx=10)
        ctk.CTkRadioButton(unit_frame, text="Fahrenheit", variable=self.unit_var, value="F",
                           fg_color=ACCENT, hover_color=ACCENT_DIM).pack(side="left", padx=10)

        self._section_label(scroll, "Alert Thresholds")
        ctk.CTkLabel(scroll, text="CPU Alert Threshold (C):", text_color=TEXT_SECONDARY).pack(anchor="w", pady=(4, 0))
        self.cpu_thresh_entry = ctk.CTkEntry(
            scroll, placeholder_text="85", fg_color="#1a2332",
            border_color="#2d3a4f", text_color=TEXT_PRIMARY,
        )
        self.cpu_thresh_entry.insert(0, str(config.get("alerts", {}).get("cpu_temp_threshold_c", 85)))
        self.cpu_thresh_entry.pack(fill="x", pady=(2, 6))

        ctk.CTkLabel(scroll, text="GPU Alert Threshold (C):", text_color=TEXT_SECONDARY).pack(anchor="w", pady=(4, 0))
        self.gpu_thresh_entry = ctk.CTkEntry(
            scroll, placeholder_text="83", fg_color="#1a2332",
            border_color="#2d3a4f", text_color=TEXT_PRIMARY,
        )
        self.gpu_thresh_entry.insert(0, str(config.get("alerts", {}).get("gpu_temp_threshold_c", 83)))
        self.gpu_thresh_entry.pack(fill="x", pady=(2, 6))

        ctk.CTkLabel(scroll, text="Alert Cooldown (seconds):", text_color=TEXT_SECONDARY).pack(anchor="w", pady=(4, 0))
        self.cooldown_entry = ctk.CTkEntry(
            scroll, placeholder_text="300", fg_color="#1a2332",
            border_color="#2d3a4f", text_color=TEXT_PRIMARY,
        )
        self.cooldown_entry.insert(0, str(config.get("alerts", {}).get("cooldown_seconds", 300)))
        self.cooldown_entry.pack(fill="x", pady=(2, 6))

        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(16, 0))
        ctk.CTkButton(
            btn_frame, text="Save", width=120, height=36,
            fg_color=ACCENT, hover_color=ACCENT_DIM,
            text_color=BG_DARK, font=ctk.CTkFont(weight="bold"),
            command=self._save,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            btn_frame, text="Cancel", width=120, height=36,
            fg_color="#334155", hover_color="#475569",
            text_color=TEXT_SECONDARY,
            command=self.destroy,
        ).pack(side="left")

    def _section_label(self, parent, text):
        ctk.CTkLabel(
            parent, text=text,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=ACCENT,
        ).pack(anchor="w", pady=(14, 2))

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
        self.geometry("640x900")
        self.minsize(560, 700)
        self.configure(fg_color=BG_DARK)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        icon = _icon_path()
        if os.path.exists(icon):
            try:
                self.iconbitmap(icon)
            except Exception:
                pass

        self._tray_icon = None
        self.overlay = OverlayWindow(self, self.config)
        self._overlay_visible = self.config.get("overlay", {}).get("enabled", False)
        self._advanced_window = None
        self._hotkey_thread = None
        self._is_resizing = False
        self._pending_snap = None
        self._resize_timer = None
        self._build_ui()
        self._start_update_loop()
        self._start_hotkey_listener()
        self.bind("<Configure>", self._on_window_resize)
        if self._overlay_visible:
            self.after(200, self.overlay.show_overlay)
            self._update_overlay_btn()

    def _build_ui(self):
        HeaderBar(self).pack(fill="x")

        main_frame = ScrollableFrame(self)
        main_frame.pack(fill="both", expand=True, padx=12, pady=(8, 12))
        content = main_frame.inner_frame

        self.cpu_card = ComponentCard(content, "CPU", "\u2699\uFE0F", lines=3)
        self.cpu_card.pack(fill="x", pady=4)

        self.gpu_card = ComponentCard(content, "GPU", "\uD83D\uDDA5", lines=3)
        self.gpu_card.pack(fill="x", pady=4)

        self.ram_card = ComponentCard(content, "RAM", "\uD83D\uDCE6", lines=3)
        self.ram_card.pack(fill="x", pady=4)

        self.disk_card = ComponentCard(content, "DISK", "\uD83D\uDCBF", lines=3)
        self.disk_card.pack(fill="x", pady=4)

        graphs_header = ctk.CTkLabel(
            content, text="Performance Graphs",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=ACCENT, anchor="w",
        )
        graphs_header.pack(fill="x", pady=(8, 2), padx=4)

        self.graphs = MiniGraphSet(content)
        self.graphs.pack(fill="x", pady=(0, 4))

        btn_frame = ctk.CTkFrame(content, fg_color=BG_CARD, corner_radius=10)
        btn_frame.pack(fill="x", pady=(10, 0), ipady=6)

        inner = ctk.CTkFrame(btn_frame, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=4)

        self.log_btn = ctk.CTkButton(
            inner, text="Start Log", width=110, height=34,
            fg_color=ACCENT, hover_color=ACCENT_DIM,
            text_color=BG_DARK, font=ctk.CTkFont(size=12, weight="bold"),
            corner_radius=8,
            command=self._toggle_logging,
        )
        self.log_btn.pack(side="left", padx=(0, 6))

        self.settings_btn = ctk.CTkButton(
            inner, text="Settings", width=100, height=34,
            fg_color="#334155", hover_color="#475569",
            text_color=TEXT_SECONDARY, font=ctk.CTkFont(size=12),
            corner_radius=8,
            command=self._open_settings,
        )
        self.settings_btn.pack(side="left", padx=(0, 6))

        self.overlay_btn = ctk.CTkButton(
            inner, text="Overlay", width=90, height=34,
            fg_color="#334155", hover_color="#475569",
            text_color=TEXT_SECONDARY, font=ctk.CTkFont(size=12),
            corner_radius=8,
            command=self._toggle_overlay,
        )
        self.overlay_btn.pack(side="left", padx=(0, 4))

        self.overlay_settings_btn = ctk.CTkButton(
            inner, text="\u2699", width=34, height=34,
            fg_color="#334155", hover_color="#475569",
            text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(size=16),
            corner_radius=8,
            command=self._open_overlay_settings,
        )
        self.overlay_settings_btn.pack(side="left")

        self.advanced_btn = ctk.CTkButton(
            inner, text="Advanced", width=90, height=34,
            fg_color="#334155", hover_color="#475569",
            text_color=TEXT_SECONDARY, font=ctk.CTkFont(size=12),
            corner_radius=8,
            command=self._open_advanced,
        )
        self.advanced_btn.pack(side="left", padx=(8, 0))

        self.status_label = ctk.CTkLabel(
            inner, text="Ready",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=TEXT_MUTED,
        )
        self.status_label.pack(side="right")

    def _fmt_temp(self, celsius: Optional[float]) -> str:
        if celsius is None:
            return "N/A"
        unit = self.config.get("temperature_unit", "C")
        if unit == "F":
            return f"{celsius * 9/5 + 32:.0f}\u00b0F"
        return f"{celsius:.0f}\u00b0C"

    def _fmt_size(self, gb: float) -> str:
        if gb >= 1024:
            return f"{gb / 1024:.1f} TB"
        return f"{gb:.1f} GB"

    def _temp_color(self, temp: Optional[float], threshold: float) -> str:
        if temp is None:
            return TEXT_MUTED
        if temp >= threshold:
            return RED
        if temp >= threshold - 15:
            return YELLOW
        return GREEN

    def _update_display(self, snap: SensorSnapshot):
        if snap.cpu_usage is not None:
            line1 = f"Usage: {snap.cpu_usage:.0f}%   |   Temp: {self._fmt_temp(snap.cpu_temp)}"
            line2 = f"Freq: {snap.cpu_freq:.0f} MHz   |   Cores: {snap.cpu_cores}" if snap.cpu_freq else f"Cores: {snap.cpu_cores}"
            line3 = snap.cpu_model or "CPU"
            self.cpu_card.update_values(
                [line1, line2, line3],
                snap.cpu_usage / 100,
                color=self._temp_color(snap.cpu_temp, self.alert_manager.cpu_threshold),
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
                color=self._temp_color(snap.gpu_temp, self.alert_manager.gpu_threshold),
            )
        else:
            self.gpu_card.update_values(["No NVIDIA GPU detected", "", ""], 0)

        line1 = f"Used: {self._fmt_size(snap.ram_used)} / {self._fmt_size(snap.ram_total)}   ({snap.ram_percent:.0f}%)"
        line2 = f"Available: {self._fmt_size(snap.ram_available)}   |   Free: {self._fmt_size(snap.ram_total - snap.ram_used)}"
        ram_parts = []
        if snap.ram_ddr_type:
            ram_parts.append(snap.ram_ddr_type)
        if snap.ram_speed_mhz:
            ram_parts.append(f"{snap.ram_speed_mhz} MHz")
        if snap.ram_modules:
            ram_parts.append(f"{snap.ram_modules} sticks")
        if snap.ram_manufacturer:
            ram_parts.append(snap.ram_manufacturer.strip())
        line3 = " | ".join(ram_parts) if ram_parts else "RAM"
        self.ram_card.update_values([line1, line2, line3], snap.ram_percent / 100, color=GREEN)

        if snap.disks:
            d = snap.disks[0]
            line1 = f"{d['device']}  |  {self._fmt_size(d['used_gb'])} / {self._fmt_size(d['total_gb'])}  ({d['percent']:.0f}%)"
            line2 = f"Free: {self._fmt_size(d['free_gb'])}  |   {d['fstype']}"
            temp_str = self._fmt_temp(d.get("temp_celsius")) if d.get("temp_celsius") is not None else "N/A"
            line3 = f"Temp: {temp_str}"
            self.disk_card.update_values(
                [line1, line2, line3],
                d["percent"] / 100,
                color=self._temp_color(d.get("temp_celsius"), 70),
            )
        else:
            self.disk_card.update_values(["No disks detected", "", ""], 0)

    def _on_snapshot(self, snap: SensorSnapshot):
        self.after(0, self._apply_snapshot, snap)

        alerts = self.alert_manager.check(snap)
        for alert in alerts:
            self.after(0, self._show_alert, alert)

    def _apply_snapshot(self, snap: SensorSnapshot):
        if self._is_resizing:
            self._pending_snap = snap
            return
        self._update_display(snap)
        self.graphs.update_from_snapshot(snap)
        if self._overlay_visible:
            self.overlay.update_values(snap)

    def _on_window_resize(self, event):
        if event.widget is not self:
            return
        self._is_resizing = True
        if self._resize_timer is not None:
            self.after_cancel(self._resize_timer)
        self._resize_timer = self.after(200, self._on_resize_settle)

    def _on_resize_settle(self):
        self._resize_timer = None
        self._is_resizing = False
        if self._pending_snap is not None:
            snap = self._pending_snap
            self._pending_snap = None
            self._apply_snapshot(snap)

    def _show_alert(self, alert: dict):
        from core.alerts import send_notification
        send_notification("Hardware Alert", alert["message"])
        self.status_label.configure(text=f"Alert: {alert['message'][:40]}...", text_color=RED)
        self.after(8000, lambda: self.status_label.configure(text="Monitoring", text_color=TEXT_MUTED))

    def _start_update_loop(self):
        self.aggregator.register_callback(self._on_snapshot)
        self.aggregator.start()

    def _toggle_logging(self):
        if self.csv_logger._running:
            self.csv_logger.stop()
            self.log_btn.configure(text="Start Log", fg_color=ACCENT, text_color=BG_DARK)
            self.status_label.configure(text="Logging stopped", text_color=TEXT_MUTED)
        else:
            self.csv_logger.set_aggregator(self.aggregator)
            self.csv_logger.start()
            self.log_btn.configure(text="Stop Log", fg_color=RED, text_color="#fff")
            self.status_label.configure(text="Logging...", text_color=GREEN)

    def _open_settings(self):
        SettingsDialog(self, self.config, on_save=self._on_settings_save)

    def _on_settings_save(self, new_config):
        self.config.update(new_config)
        self.save_config_fn(self.config)
        self.aggregator.update_interval(new_config["polling_interval_seconds"])
        self.alert_manager.cpu_threshold = new_config.get("alerts", {}).get("cpu_temp_threshold_c", 85)
        self.alert_manager.gpu_threshold = new_config.get("alerts", {}).get("gpu_temp_threshold_c", 83)
        self.alert_manager.cooldown = new_config.get("alerts", {}).get("cooldown_seconds", 300)
        self.status_label.configure(text="Settings saved", text_color=GREEN)
        self.after(3000, lambda: self.status_label.configure(text="Monitoring", text_color=TEXT_MUTED))

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
            self.overlay_btn.configure(text="Overlay", fg_color=PURPLE, text_color="#fff")
        else:
            self.overlay_btn.configure(text="Overlay", fg_color="#334155", text_color=TEXT_SECONDARY)

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
        self.status_label.configure(text="Overlay settings saved", text_color=GREEN)
        self.after(3000, lambda: self.status_label.configure(text="Monitoring", text_color=TEXT_MUTED))

    def _open_advanced(self):
        if self._advanced_window and self._advanced_window.winfo_exists():
            self._advanced_window.lift()
            self._advanced_window.focus_force()
            return
        self._advanced_window = AdvancedWindow(self, self.aggregator, self.config)

    def _start_hotkey_listener(self):
        try:
            import keyboard
            self._hotkey_thread = threading.Thread(target=self._hotkey_loop, daemon=True)
            self._hotkey_thread.start()
        except ImportError:
            pass

    def _hotkey_loop(self):
        try:
            import keyboard
            keyboard.add_hotkey("ctrl+shift+o", lambda: self.after(0, self._toggle_overlay))
            keyboard.add_hotkey("ctrl+shift+m", lambda: self.after(0, self._toggle_main_visibility))
            keyboard.add_hotkey("ctrl+shift+a", lambda: self.after(0, self._open_advanced))
            keyboard.wait()
        except Exception:
            pass

    def _toggle_main_visibility(self):
        if self.state() == "withdrawn":
            self.deiconify()
            self.lift()
            self.focus_force()
        else:
            self.withdraw()

    def _on_close(self):
        if self._tray_icon:
            self._tray_icon.stop()
        self.overlay.destroy()
        self.aggregator.stop()
        self.csv_logger.stop()
        self.destroy()
