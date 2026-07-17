import logging
from typing import Optional

logger = logging.getLogger(__name__)

_nvml_ok = False

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

    def get_stats(self) -> dict:
        if not self._available:
            return {
                "name": None,
                "usage_percent": None,
                "temp_celsius": None,
                "vram_used_mb": None,
                "vram_total_mb": None,
                "vram_percent": None,
            }

        try:
            util = pynvml.nvmlDeviceGetUtilizationRates(_handle)
            temp = pynvml.nvmlDeviceGetTemperature(_handle, pynvml.NVML_TEMPERATURE_GPU)
            mem = pynvml.nvmlDeviceGetMemoryInfo(_handle)

            vram_used = mem.used // (1024 * 1024)
            vram_total = mem.total // (1024 * 1024)

            stats = {
                "name": _name,
                "usage_percent": float(util.gpu),
                "temp_celsius": float(temp),
                "vram_used_mb": float(vram_used),
                "vram_total_mb": float(vram_total),
                "vram_percent": round((vram_used / vram_total) * 100, 1) if vram_total > 0 else 0.0,
            }
            self._last_stats = stats
            return stats
        except Exception as e:
            logger.debug(f"GPU query failed: {e}")
            return self._last_stats or {
                "name": None,
                "usage_percent": None,
                "temp_celsius": None,
                "vram_used_mb": None,
                "vram_total_mb": None,
                "vram_percent": None,
            }
