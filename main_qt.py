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

    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QIcon
    import qdarkstyle

    from core.sensors import SensorAggregator, load_config, save_config, set_app_dir, get_assets_dir
    from core.logger import CsvLogger
    from core.alerts import AlertManager
    from gui.main_window import MainWindow

    set_app_dir(_app_dir)

    config = load_config()
    logger.info("Config loaded. Starting Gauge (Qt)...")

    aggregator = SensorAggregator(config)
    csv_logger = CsvLogger(config)
    alert_manager = AlertManager(config)

    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet())

    icon_file = os.path.join(get_assets_dir(), "gauge.ico")
    if os.path.exists(icon_file):
        app.setWindowIcon(QIcon(icon_file))

    try:
        win = MainWindow(aggregator, config, csv_logger, alert_manager, save_config)
        logger.info("MainWindow created successfully")
    except Exception as e:
        logger.critical(f"MainWindow creation failed: {e}", exc_info=True)
        return

    win.show()
    logger.info("Starting Qt mainloop...")

    ret = app.exec()

    aggregator.stop()
    csv_logger.stop()
    sys.exit(ret)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        raise
