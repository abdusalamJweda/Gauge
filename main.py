import sys
import os
import logging
import ctypes

def _is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def _get_exe_path() -> str:
    try:
        buf = ctypes.create_unicode_buffer(512)
        ctypes.windll.kernel32.GetModuleFileNameW(None, buf, 512)
        return os.path.abspath(buf.value)
    except Exception:
        return os.path.abspath(sys.argv[0])

def _elevate():
    try:
        exe = _get_exe_path()
        params = " ".join(f'"{a}"' for a in sys.argv[1:])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
        sys.exit(0)
    except Exception:
        sys.exit(1)

if not _is_admin():
    _elevate()

def _get_app_dir() -> str:
    """Get the directory where the .exe or script actually lives."""
    argv0 = os.path.abspath(sys.argv[0])
    if argv0.lower().endswith(".py"):
        return os.path.dirname(argv0)
    try:
        buf = ctypes.create_unicode_buffer(512)
        ctypes.windll.kernel32.GetModuleFileNameW(None, buf, 512)
        exe_path = os.path.abspath(buf.value)
        if "python" not in exe_path.lower():
            return os.path.dirname(exe_path)
    except Exception:
        pass
    return os.path.dirname(argv0)

_app_dir = _get_app_dir()
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)

_log_path = os.path.join(_app_dir, "crash.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(_log_path, encoding="utf-8"),
    ],
)

logger = logging.getLogger("hwmonitor")

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass


def main():
    logger.info(f"App dir: {_app_dir}")
    logger.info(f"Python: {sys.version}")
    logger.info(f"Frozen: {getattr(sys, 'frozen', False)}")

    from core.sensors import SensorAggregator, load_config, save_config, set_app_dir
    from core.logger import CsvLogger
    from core.alerts import AlertManager
    from gui.app import MainWindow

    set_app_dir(_app_dir)

    config = load_config()
    logger.info("Config loaded. Starting Gauge...")

    aggregator = SensorAggregator(config)
    csv_logger = CsvLogger(config)
    alert_manager = AlertManager(config)

    def start_gui():
        logger.info("Creating MainWindow...")
        try:
            app = MainWindow(aggregator, config, csv_logger, alert_manager, save_config)
            logger.info("MainWindow created successfully")
        except Exception as e:
            logger.critical(f"MainWindow creation failed: {e}", exc_info=True)
            return

        try:
            import pystray
            from PIL import Image, ImageDraw

            def create_tray_icon():
                from core.sensors import get_assets_dir
                assets = get_assets_dir()
                ico_path = os.path.join(assets, "gauge.ico")
                png_path = os.path.join(assets, "gauge.png")
                if os.path.exists(ico_path):
                    return Image.open(ico_path).resize((64, 64), Image.LANCZOS)
                if os.path.exists(png_path):
                    return Image.open(png_path).resize((64, 64), Image.LANCZOS)
                img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
                draw = ImageDraw.Draw(img)
                draw.rounded_rectangle([8, 8, 56, 56], radius=10, fill="#0f172a", outline="#60a5fa", width=2)
                return img

            def on_show(icon, item):
                app.after(0, _show_window)

            def on_quit(icon, item):
                app.after(0, app._on_close)

            def _show_window():
                app.deiconify()
                app.lift()
                app.focus_force()
                if app._overlay_visible:
                    app.after(50, app.overlay.lift)

            tray_icon = pystray.Icon(
                "Gauge",
                create_tray_icon(),
                "Gauge",
                menu=pystray.Menu(
                    pystray.MenuItem("Show", on_show, default=True),
                    pystray.MenuItem("Quit", on_quit),
                ),
            )

            def on_close_to_tray():
                app.withdraw()
                if app._overlay_visible:
                    app.after(50, app.overlay.lift)

            app.protocol("WM_DELETE_WINDOW", on_close_to_tray)
            app.set_tray_icon(tray_icon)

            import threading
            tray_thread = threading.Thread(target=tray_icon.run, daemon=True)
            tray_thread.start()
            logger.info("System tray icon active")

        except ImportError:
            logger.info("pystray not installed. Tray icon disabled.")
        except Exception as e:
            logger.warning(f"Tray icon failed: {e}", exc_info=True)

        logger.info("Starting mainloop...")
        app.mainloop()

    start_gui()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        raise
