import json
import os
import threading
import time
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Callable

from core.cpu import CpuSensor, get_lhm_disk_temps
from core.gpu import GpuSensor
from core.ram import RamSensor
from core.disk import DiskSensor, set_lhm_disk_temps

logger = logging.getLogger(__name__)

CONFIG_FILE = "config.json"

_app_dir = None


def set_app_dir(path: str):
    global _app_dir
    _app_dir = path


def get_config_path() -> str:
    if _app_dir:
        return os.path.join(_app_dir, CONFIG_FILE)
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, CONFIG_FILE)


def load_config() -> dict:
    defaults = {
        "polling_interval_seconds": 1,
        "temperature_unit": "C",
        "alerts": {
            "cpu_temp_threshold_c": 85,
            "gpu_temp_threshold_c": 83,
            "cooldown_seconds": 300,
        },
        "logging": {
            "enabled": False,
            "log_dir": "logs",
            "retention_days": 30,
        },
        "gui": {
            "theme": "dark",
            "show_cpu": True,
            "show_gpu": True,
            "show_ram": True,
            "show_disk": True,
        },
    }
    path = get_config_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            user_cfg = json.load(f)
        for key, val in defaults.items():
            if key not in user_cfg:
                user_cfg[key] = val
            elif isinstance(val, dict):
                for k2, v2 in val.items():
                    if k2 not in user_cfg[key]:
                        user_cfg[key][k2] = v2
        return user_cfg
    except FileNotFoundError:
        save_config(defaults)
        return defaults
    except Exception as e:
        logger.warning(f"Failed to load config: {e}. Using defaults.")
        return defaults


def save_config(cfg: dict):
    path = get_config_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save config: {e}")


@dataclass
class SensorSnapshot:
    timestamp: float = 0.0
    cpu_model: Optional[str] = None
    cpu_usage: Optional[float] = None
    cpu_temp: Optional[float] = None
    cpu_freq: Optional[float] = None
    cpu_cores: int = 0
    gpu_name: Optional[str] = None
    gpu_usage: Optional[float] = None
    gpu_temp: Optional[float] = None
    gpu_vram_used: Optional[float] = None
    gpu_vram_total: Optional[float] = None
    gpu_vram_percent: Optional[float] = None
    ram_total: float = 0.0
    ram_used: float = 0.0
    ram_available: float = 0.0
    ram_percent: float = 0.0
    ram_ddr_type: Optional[str] = None
    ram_speed_mhz: Optional[int] = None
    ram_modules: Optional[int] = None
    ram_manufacturer: Optional[str] = None
    disks: List[dict] = field(default_factory=list)


class SensorAggregator:
    def __init__(self, config: dict):
        self.config = config
        self.cpu = CpuSensor()
        self.gpu = GpuSensor()
        self.ram = RamSensor()
        self.disk = DiskSensor()
        self._snapshot = SensorSnapshot()
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable] = []

    @property
    def snapshot(self) -> SensorSnapshot:
        with self._lock:
            return self._snapshot

    def register_callback(self, cb: Callable):
        self._callbacks.append(cb)

    def unregister_callback(self, cb: Callable):
        self._callbacks = [c for c in self._callbacks if c is not cb]

    def _poll_once(self):
        cpu_stats = self.cpu.get_stats()
        gpu_stats = self.gpu.get_stats()
        ram_stats = self.ram.get_stats()

        lhm_disk_temps = get_lhm_disk_temps()
        set_lhm_disk_temps(lhm_disk_temps)

        disk_stats = self.disk.get_stats()

        snap = SensorSnapshot(
            timestamp=time.time(),
            cpu_model=cpu_stats.get("model_name"),
            cpu_usage=cpu_stats.get("usage_percent"),
            cpu_temp=cpu_stats.get("temp_celsius"),
            cpu_freq=cpu_stats.get("freq_mhz"),
            cpu_cores=cpu_stats.get("core_count", 0),
            gpu_name=gpu_stats.get("name"),
            gpu_usage=gpu_stats.get("usage_percent"),
            gpu_temp=gpu_stats.get("temp_celsius"),
            gpu_vram_used=gpu_stats.get("vram_used_mb"),
            gpu_vram_total=gpu_stats.get("vram_total_mb"),
            gpu_vram_percent=gpu_stats.get("vram_percent"),
            ram_total=ram_stats.get("total_gb", 0),
            ram_used=ram_stats.get("used_gb", 0),
            ram_available=ram_stats.get("available_gb", 0),
            ram_percent=ram_stats.get("percent", 0),
            ram_ddr_type=ram_stats.get("ddr_type"),
            ram_speed_mhz=ram_stats.get("speed_mhz"),
            ram_modules=ram_stats.get("modules"),
            ram_manufacturer=ram_stats.get("manufacturer"),
            disks=disk_stats,
        )

        with self._lock:
            self._snapshot = snap

        for cb in self._callbacks:
            try:
                cb(snap)
            except Exception as e:
                logger.debug(f"Callback error: {e}")

    def _loop(self):
        interval = self.config.get("polling_interval_seconds", 1)
        while self._running:
            try:
                self._poll_once()
            except Exception as e:
                logger.error(f"Poll error: {e}")
            time.sleep(interval)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="sensor-poll")
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None

    def update_interval(self, seconds: float):
        self.config["polling_interval_seconds"] = seconds
