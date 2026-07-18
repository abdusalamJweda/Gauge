import logging
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

_nvml_ok = False
_handle = None
_name = None

try:
    import pynvml
    pynvml.nvmlInit()
    _gpu_count = pynvml.nvmlDeviceGetCount()
    _nvml_ok = _gpu_count > 0
    if _nvml_ok:
        _handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        _name = pynvml.nvmlDeviceGetName(_handle)
        if isinstance(_name, bytes):
            _name = _name.decode("utf-8")
        logger.info(f"NVIDIA GPU detected: {_name}")
except ImportError:
    logger.debug("nvidia-ml-py not installed. pip install nvidia-ml-py")
except Exception as e:
    logger.debug(f"NVML init failed: {e}")


class GpuSensor:
    def __init__(self):
        self._available = _nvml_ok
        self._last_stats: Optional[dict] = None
        self._lhm_gpus: List[Dict] = []

    def get_stats(self) -> dict:
        if self._available:
            return self._get_nvidia_stats()
        return self._get_lhm_stats()

    def _get_nvidia_stats(self) -> dict:
        try:
            util = pynvml.nvmlDeviceGetUtilizationRates(_handle)
            temp = pynvml.nvmlDeviceGetTemperature(_handle, pynvml.NVML_TEMPERATURE_GPU)
            mem = pynvml.nvmlDeviceGetMemoryInfo(_handle)

            vram_used = mem.used // (1024 * 1024)
            vram_total = mem.total // (1024 * 1024)

            clock = None
            try:
                clock = pynvml.nvmlDeviceGetClockInfo(_handle, pynvml.NVML_CLOCK_GRAPHICS)
            except Exception:
                pass

            fan_speed = None
            try:
                fan_speed = pynvml.nvmlDeviceGetFanSpeed(_handle)
            except Exception:
                pass

            power_draw = None
            try:
                power_draw = pynvml.nvmlDeviceGetPowerUsage(_handle) / 1000.0
            except Exception:
                pass

            stats = {
                "name": _name,
                "usage_percent": float(util.gpu),
                "temp_celsius": float(temp),
                "vram_used_mb": float(vram_used),
                "vram_total_mb": float(vram_total),
                "vram_percent": round((vram_used / vram_total) * 100, 1) if vram_total > 0 else 0.0,
                "clock_mhz": float(clock) if clock is not None else None,
                "fan_speed_percent": float(fan_speed) if fan_speed is not None else None,
                "power_draw_w": round(power_draw, 1) if power_draw is not None else None,
                "vendor": "NVIDIA",
            }
            self._last_stats = stats
            return stats
        except Exception as e:
            logger.debug(f"NVIDIA GPU query failed: {e}")
            return self._last_stats or self._empty_stats()

    def _get_lhm_stats(self) -> dict:
        from core.cpu import _init_lhm, is_admin

        if not is_admin() or not _init_lhm():
            return self._empty_stats()

        try:
            from LibreHardwareMonitor.Hardware import SensorType
            from core.cpu import _lhm_computer

            for hardware in _lhm_computer.Hardware:
                hw_type = str(hardware.HardwareType)
                if "Gpu" not in hw_type:
                    continue
                hardware.Update()
                for sub in hardware.SubHardware:
                    sub.Update()

                usage = None
                temp = None
                vram_used = None
                vram_total = None
                clock = None
                fan = None
                power = None

                for sensor in hardware.Sensors:
                    val = sensor.Value
                    if val is None:
                        continue
                    sname = sensor.Name.lower()
                    stype = str(sensor.SensorType)

                    if "Load" in stype and "gpu" in sname:
                        usage = float(val)
                    elif "Temperature" in stype and "core" in sname:
                        temp = float(val)
                    elif "SmallData" in stype and "memory used" in sname:
                        vram_used = float(val) * 1024
                    elif "SmallData" in stype and "memory total" in sname:
                        vram_total = float(val) * 1024
                    elif "Clock" in stype and "core" in sname:
                        clock = float(val)
                    elif "Fan" in stype:
                        fan = float(val)
                    elif "Power" in stype and "total" in sname:
                        power = float(val)

                name = hardware.Name or "GPU"
                if vram_total and vram_total > 0 and vram_used is None:
                    vram_used = 0

                stats = {
                    "name": name,
                    "usage_percent": round(usage, 1) if usage is not None else None,
                    "temp_celsius": round(temp, 1) if temp is not None else None,
                    "vram_used_mb": round(vram_used, 0) if vram_used is not None else None,
                    "vram_total_mb": round(vram_total, 0) if vram_total is not None else None,
                    "vram_percent": round((vram_used / vram_total) * 100, 1) if vram_used and vram_total and vram_total > 0 else None,
                    "clock_mhz": round(clock, 0) if clock is not None else None,
                    "fan_speed_percent": round(fan, 1) if fan is not None else None,
                    "power_draw_w": round(power, 1) if power is not None else None,
                    "vendor": "AMD/Intel",
                }
                self._last_stats = stats
                return stats

            return self._empty_stats()
        except Exception as e:
            logger.debug(f"LHM GPU query failed: {e}")
            return self._last_stats or self._empty_stats()

    @staticmethod
    def _empty_stats() -> dict:
        return {
            "name": None,
            "usage_percent": None,
            "temp_celsius": None,
            "vram_used_mb": None,
            "vram_total_mb": None,
            "vram_percent": None,
            "clock_mhz": None,
            "fan_speed_percent": None,
            "power_draw_w": None,
            "vendor": None,
        }
