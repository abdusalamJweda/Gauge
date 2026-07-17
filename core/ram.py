import psutil
from typing import Optional


class RamSensor:
    def __init__(self):
        self._last_stats: Optional[dict] = None
        self._ddr_type: Optional[str] = None
        self._speed_mhz: Optional[int] = None
        self._modules: Optional[int] = None
        self._manufacturer: Optional[str] = None
        self._detect_hardware()

    def _detect_hardware(self):
        try:
            import wmi
            w = wmi.WMI()
            sticks = w.Win32_PhysicalMemory()
            if sticks:
                stick = sticks[0]
                part = stick.PartNumber or ""
                speed = stick.Speed or 0
                mfr = stick.Manufacturer or ""

                self._speed_mhz = int(speed) if speed else None
                self._modules = len(sticks)
                self._manufacturer = mfr.strip() if mfr else None

                part_upper = part.upper().strip()
                if "DDR5" in part_upper:
                    self._ddr_type = "DDR5"
                elif "DDR4" in part_upper:
                    self._ddr_type = "DDR4"
                elif "DDR3" in part_upper:
                    self._ddr_type = "DDR3"
                elif self._speed_mhz and self._speed_mhz >= 4800:
                    self._ddr_type = "DDR5"
                elif self._speed_mhz and self._speed_mhz >= 2133:
                    self._ddr_type = "DDR4"
                else:
                    self._ddr_type = "DDR"
        except Exception:
            pass

    def get_stats(self) -> dict:
        try:
            mem = psutil.virtual_memory()
            stats = {
                "total_gb": round(mem.total / (1024**3), 2),
                "used_gb": round(mem.used / (1024**3), 2),
                "available_gb": round(mem.available / (1024**3), 2),
                "percent": mem.percent,
                "ddr_type": self._ddr_type,
                "speed_mhz": self._speed_mhz,
                "modules": self._modules,
                "manufacturer": self._manufacturer,
            }
            self._last_stats = stats
            return stats
        except Exception:
            return self._last_stats or {
                "total_gb": 0,
                "used_gb": 0,
                "available_gb": 0,
                "percent": 0,
                "ddr_type": None,
                "speed_mhz": None,
                "modules": None,
                "manufacturer": None,
            }
