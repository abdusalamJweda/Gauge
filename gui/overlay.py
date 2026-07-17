import customtkinter as ctk
from typing import Optional
from core.sensors import SensorSnapshot


class OverlayWindow(ctk.CTkToplevel):
    def __init__(self, master, config: dict):
        super().__init__(master)
        self.config = config
        self._drag_data = {"x": 0, "y": 0}

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        try:
            self.attributes("-toolwindow", True)
        except Exception:
            pass
        self.transient(master)
        self._apply_opacity()
        ov = self.config.get("overlay", {})
        self.configure(fg_color=ov.get("bg_color", "#1a1a2e"))

        self._build_ui()
        self._position_window()
        self.withdraw()

    def _build_ui(self):
        self._frame = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self._frame.pack(fill="both", expand=True, padx=6, pady=4)

        ov = self.config.get("overlay", {})
        font_size = ov.get("font_size", 12)
        font = ctk.CTkFont(family="Consolas", size=font_size)

        self._cpu_label = ctk.CTkLabel(
            self._frame, text="CPU --%", font=font, text_color="#888", anchor="w"
        )
        self._cpu_label.pack(side="left", padx=(0, 10))

        self._gpu_label = ctk.CTkLabel(
            self._frame, text="GPU --%", font=font, text_color="#888", anchor="w"
        )
        self._gpu_label.pack(side="left", padx=(0, 10))

        self._ram_label = ctk.CTkLabel(
            self._frame, text="RAM --%", font=font, text_color="#888", anchor="w"
        )
        self._ram_label.pack(side="left", padx=(0, 10))

        self._fps_label = ctk.CTkLabel(
            self._frame, text="FPS --", font=font, text_color="#888", anchor="w"
        )
        self._fps_label.pack(side="left")

        self._frame.bind("<ButtonPress-1>", self._on_press)
        self._frame.bind("<B1-Motion>", self._on_drag)
        self._cpu_label.bind("<ButtonPress-1>", self._on_press)
        self._cpu_label.bind("<B1-Motion>", self._on_drag)
        self._gpu_label.bind("<ButtonPress-1>", self._on_press)
        self._gpu_label.bind("<B1-Motion>", self._on_drag)
        self._ram_label.bind("<ButtonPress-1>", self._on_press)
        self._ram_label.bind("<B1-Motion>", self._on_drag)
        self._fps_label.bind("<ButtonPress-1>", self._on_press)
        self._fps_label.bind("<B1-Motion>", self._on_drag)

    def _apply_opacity(self):
        ov = self.config.get("overlay", {})
        opacity = ov.get("opacity", 0.85)
        self.attributes("-alpha", max(0.3, min(1.0, opacity)))

    def _position_window(self):
        ov = self.config.get("overlay", {})
        position = ov.get("position", "top-right")
        self.update_idletasks()
        w = self.winfo_reqwidth()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        margin = 12

        positions = {
            "top-right": (sw - w - margin, margin),
            "top-left": (margin, margin),
            "bottom-right": (sw - w - margin, sh - 40 - margin),
            "bottom-left": (margin, sh - 40 - margin),
        }
        x, y = positions.get(position, positions["top-right"])
        self.geometry(f"+{x}+{y}")

    def _on_press(self, event):
        self._drag_data["x"] = event.x_root - self.winfo_x()
        self._drag_data["y"] = event.y_root - self.winfo_y()

    def _on_drag(self, event):
        x = event.x_root - self._drag_data["x"]
        y = event.y_root - self._drag_data["y"]
        self.geometry(f"+{x}+{y}")

    def update_values(self, snap: SensorSnapshot):
        ov = self.config.get("overlay", {})
        if ov.get("show_cpu", True) and snap.cpu_usage is not None:
            color = self._metric_color(snap.cpu_usage, 65, 85)
            self._cpu_label.configure(text=f"CPU {snap.cpu_usage:.0f}%", text_color=color)
        else:
            self._cpu_label.configure(text="CPU --%", text_color="#555")

        if ov.get("show_gpu", True) and snap.gpu_usage is not None:
            color = self._metric_color(snap.gpu_usage, 75, 90)
            self._gpu_label.configure(text=f"GPU {snap.gpu_usage:.0f}%", text_color=color)
        else:
            self._gpu_label.configure(text="GPU --%", text_color="#555")

        if ov.get("show_ram", True):
            color = self._metric_color(snap.ram_percent, 70, 90)
            self._ram_label.configure(text=f"RAM {snap.ram_percent:.0f}%", text_color=color)
        else:
            self._ram_label.configure(text="RAM --%", text_color="#555")

        if ov.get("show_fps", True) and snap.fps is not None:
            if snap.fps >= 60:
                color = "#22c55e"
            elif snap.fps >= 30:
                color = "#f59e0b"
            else:
                color = "#ef4444"
            self._fps_label.configure(text=f"FPS {snap.fps:.0f}", text_color=color)
        else:
            self._fps_label.configure(text="FPS --", text_color="#555")

    @staticmethod
    def _metric_color(value: float, warn: float, crit: float) -> str:
        if value >= crit:
            return "#ef4444"
        if value >= warn:
            return "#f59e0b"
        return "#22c55e"

    def apply_config(self, overlay_cfg: dict):
        self.configure(fg_color=overlay_cfg.get("bg_color", "#1a1a2e"))
        self._apply_opacity()
        self._position_window()

        font_size = overlay_cfg.get("font_size", 12)
        font = ctk.CTkFont(family="Consolas", size=font_size)
        for label in [self._cpu_label, self._gpu_label, self._ram_label, self._fps_label]:
            label.configure(font=font)

    def show_overlay(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def hide_overlay(self):
        self.withdraw()
