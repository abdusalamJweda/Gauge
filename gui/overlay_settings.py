import customtkinter as ctk


BG_COLORS = [
    ("#1a1a2e", "Dark Navy"),
    ("#0d1117", "GitHub Dark"),
    ("#1e1e2e", "Catppuccin"),
    ("#282a36", "Dracula"),
]


class OverlaySettingsDialog(ctk.CTkToplevel):
    def __init__(self, master, overlay_config: dict, on_save=None):
        super().__init__(master)
        self.title("Overlay Settings")
        self.geometry("320x520")
        self.resizable(False, True)
        self.overlay_config = dict(overlay_config)
        self.on_save = on_save
        self.grab_set()

        ctk.CTkLabel(
            self, text="Overlay Settings",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(12, 4))

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        ctk.CTkLabel(scroll, text="Opacity:").pack(anchor="w")
        self.opacity_slider = ctk.CTkSlider(
            scroll, from_=0.3, to=1.0, number_of_steps=14,
            command=lambda v: self.opacity_label.configure(text=f"{v:.0%}")
        )
        self.opacity_slider.set(overlay_config.get("opacity", 0.85))
        self.opacity_slider.pack(fill="x", pady=(0, 2))
        self.opacity_label = ctk.CTkLabel(
            scroll, text=f"{overlay_config.get('opacity', 0.85):.0%}",
            font=ctk.CTkFont(size=11)
        )
        self.opacity_label.pack(anchor="w")

        ctk.CTkLabel(scroll, text="Position:").pack(anchor="w", pady=(8, 0))
        self.position_var = ctk.StringVar(value=overlay_config.get("position", "top-right"))
        ctk.CTkOptionMenu(
            scroll, variable=self.position_var,
            values=["top-right", "top-left", "bottom-right", "bottom-left"],
            width=160
        ).pack(anchor="w", pady=4)

        ctk.CTkLabel(scroll, text="Font Size:").pack(anchor="w", pady=(4, 0))
        self.font_slider = ctk.CTkSlider(
            scroll, from_=10, to=16, number_of_steps=6,
            command=lambda v: self.font_label.configure(text=f"{v:.0f}")
        )
        self.font_slider.set(overlay_config.get("font_size", 12))
        self.font_slider.pack(fill="x", pady=(0, 2))
        self.font_label = ctk.CTkLabel(
            scroll, text=f"{overlay_config.get('font_size', 12)}",
            font=ctk.CTkFont(size=11)
        )
        self.font_label.pack(anchor="w")

        ctk.CTkLabel(scroll, text="Background Color:").pack(anchor="w", pady=(8, 0))
        self.bg_var = ctk.StringVar(value=overlay_config.get("bg_color", "#1a1a2e"))
        for hex_val, name in BG_COLORS:
            ctk.CTkRadioButton(
                scroll, text=name,
                variable=self.bg_var,
                value=hex_val
            ).pack(anchor="w", pady=1)

        ctk.CTkLabel(scroll, text="Visible Metrics:").pack(anchor="w", pady=(10, 0))

        self.cpu_var = ctk.BooleanVar(value=overlay_config.get("show_cpu", True))
        ctk.CTkSwitch(scroll, text="Show CPU", variable=self.cpu_var).pack(anchor="w", pady=2)

        self.gpu_var = ctk.BooleanVar(value=overlay_config.get("show_gpu", True))
        ctk.CTkSwitch(scroll, text="Show GPU", variable=self.gpu_var).pack(anchor="w", pady=2)

        self.ram_var = ctk.BooleanVar(value=overlay_config.get("show_ram", True))
        ctk.CTkSwitch(scroll, text="Show RAM", variable=self.ram_var).pack(anchor="w", pady=2)

        self.fps_var = ctk.BooleanVar(value=overlay_config.get("show_fps", True))
        ctk.CTkSwitch(scroll, text="Show FPS", variable=self.fps_var).pack(anchor="w", pady=2)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkButton(btn_frame, text="Save", width=100, command=self._save).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Cancel", width=100, command=self.destroy, fg_color="#555").pack(side="left", padx=5)

    def _save(self):
        self.overlay_config["opacity"] = round(self.opacity_slider.get(), 2)
        self.overlay_config["position"] = self.position_var.get()
        self.overlay_config["font_size"] = int(self.font_slider.get())
        self.overlay_config["bg_color"] = self.bg_var.get()
        self.overlay_config["show_cpu"] = self.cpu_var.get()
        self.overlay_config["show_gpu"] = self.gpu_var.get()
        self.overlay_config["show_ram"] = self.ram_var.get()
        self.overlay_config["show_fps"] = self.fps_var.get()
        if self.on_save:
            self.on_save(self.overlay_config)
        self.destroy()
