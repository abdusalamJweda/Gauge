import customtkinter as ctk
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
        self._apply_opacity()
        ov = self.config.get("overlay", {})
        self.configure(fg_color=ov.get("bg_color", "#1a1a2e"))

        self._build_ui()
        self._position_window()
        self.withdraw()

    def _build_ui(self):
        ov = self.config.get("overlay", {})
        font_size = ov.get("font_size", 12)
        font = ctk.CTkFont(family="Consolas", size=font_size)
        small_font = ctk.CTkFont(family="Consolas", size=max(8, font_size - 2))

        self._frame = ctk.CTkFrame(
            self, fg_color="transparent", corner_radius=8
        )
        self._frame.pack(fill="both", expand=True, padx=8, pady=6)

        self._metrics = {}
        for key in ["cpu", "gpu", "ram", "fps"]:
            lbl = ctk.CTkLabel(
                self._frame, text="", font=font, text_color="#666", anchor="w"
            )
            lbl.pack(side="left", padx=(0, 8))
            self._metrics[key] = lbl

        for widget in [self._frame] + list(self._metrics.values()):
            widget.bind("<ButtonPress-1>", self._on_press)
            widget.bind("<B1-Motion>", self._on_drag)

    def _apply_opacity(self):
        ov = self.config.get("overlay", {})
        opacity = ov.get("opacity", 0.85)
        self.attributes("-alpha", max(0.3, min(1.0, opacity)))

    def _position_window(self):
        ov = self.config.get("overlay", {})
        position = ov.get("position", "top-right")
        self.update_idletasks()
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        margin = 12

        positions = {
            "top-right": (sw - w - margin, margin),
            "top-left": (margin, margin),
            "bottom-right": (sw - w - margin, sh - h - margin),
            "bottom-left": (margin, sh - h - margin),
        }
        x, y = positions.get(position, positions["top-right"])

        x = max(0, min(x, sw - w - margin))
        y = max(0, min(y, sh - h - margin))

        self.geometry(f"+{x}+{y}")

    def _on_press(self, event):
        self._drag_data["x"] = event.x_root - self.winfo_x()
        self._drag_data["y"] = event.y_root - self.winfo_y()

    def _on_drag(self, event):
        x = event.x_root - self._drag_data["x"]
        y = event.y_root - self._drag_data["y"]
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()
        x = max(0, min(x, sw - w))
        y = max(0, min(y, sh - h))
        self.geometry(f"+{x}+{y}")

    def update_values(self, snap: SensorSnapshot):
        ov = self.config.get("overlay", {})

        if ov.get("show_cpu", True) and snap.cpu_usage is not None:
            c = self._color(snap.cpu_usage, 65, 85)
            self._metrics["cpu"].configure(text=f"CPU {snap.cpu_usage:.0f}%", text_color=c)
        else:
            self._metrics["cpu"].configure(text="", text_color="#555")

        if ov.get("show_gpu", True) and snap.gpu_usage is not None:
            c = self._color(snap.gpu_usage, 75, 90)
            self._metrics["gpu"].configure(text=f"GPU {snap.gpu_usage:.0f}%", text_color=c)
        else:
            self._metrics["gpu"].configure(text="", text_color="#555")

        if ov.get("show_ram", True):
            c = self._color(snap.ram_percent, 70, 90)
            self._metrics["ram"].configure(text=f"RAM {snap.ram_percent:.0f}%", text_color=c)
        else:
            self._metrics["ram"].configure(text="", text_color="#555")

        if ov.get("show_fps", True) and snap.fps is not None:
            if snap.fps >= 60:
                c = "#22c55e"
            elif snap.fps >= 30:
                c = "#f59e0b"
            else:
                c = "#ef4444"
            self._metrics["fps"].configure(text=f"FPS {snap.fps:.0f}", text_color=c)
        else:
            self._metrics["fps"].configure(text="", text_color="#555")

    @staticmethod
    def _color(value: float, warn: float, crit: float) -> str:
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
        for lbl in self._metrics.values():
            lbl.configure(font=font)

    def show_overlay(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def hide_overlay(self):
        self.withdraw()
