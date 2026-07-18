import logging
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


class StorageSensor:
    def __init__(self):
        self._last_stats: List[Dict] = []

    def get_stats(self) -> List[Dict]:
        from core.cpu import _init_lhm, is_admin

        drives = []

        if is_admin() and _init_lhm():
            try:
                from LibreHardwareMonitor.Hardware import SensorType
                from core.cpu import _lhm_computer

                for hardware in _lhm_computer.Hardware:
                    hw_type_str = str(hardware.HardwareType)
                    if "Storage" not in hw_type_str:
                        continue
                    hardware.Update()
                    for sub in hardware.SubHardware:
                        sub.Update()

                    health_pct = None
                    temp = None
                    for sensor in hardware.Sensors:
                        if sensor.SensorType == SensorType.Health:
                            if sensor.Value is not None:
                                health_pct = round(float(sensor.Value), 1)
                        elif sensor.SensorType == SensorType.Temperature:
                            if sensor.Value is not None and float(sensor.Value) > 0:
                                temp = round(float(sensor.Value), 1)

                    name = hardware.Name or "Drive"
                    drives.append({
                        "name": name,
                        "health_percent": health_pct,
                        "temp_celsius": temp,
                    })
            except Exception as e:
                logger.debug(f"Storage SMART query failed: {e}")

        self._last_stats = drives
        return drives
