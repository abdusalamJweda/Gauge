import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class FanSensor:
    def __init__(self):
        self._last_stats: List[Dict] = []

    def get_stats(self) -> List[Dict]:
        from core.cpu import _init_lhm, is_admin

        if not is_admin() or not _init_lhm():
            return self._last_stats

        try:
            from LibreHardwareMonitor.Hardware import SensorType
            from core.cpu import _lhm_computer

            fans = []
            for hardware in _lhm_computer.Hardware:
                hardware.Update()
                for sub in hardware.SubHardware:
                    sub.Update()
                for sensor in hardware.Sensors:
                    if sensor.SensorType == SensorType.Fan:
                        val = sensor.Value
                        if val is not None and val >= 0:
                            name = sensor.Name or "Fan"
                            hw_name = hardware.Name or ""
                            fans.append({
                                "name": name,
                                "label": f"{hw_name} - {name}" if hw_name else name,
                                "rpm": float(val),
                            })

            fans.sort(key=lambda f: f["rpm"], reverse=True)
            self._last_stats = fans
            return fans
        except Exception as e:
            logger.debug(f"Fan sensor query failed: {e}")
            return self._last_stats
