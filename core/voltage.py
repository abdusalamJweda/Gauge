import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class VoltageSensor:
    def __init__(self):
        self._last_stats: List[Dict] = []

    def get_stats(self) -> List[Dict]:
        from core.cpu import _init_lhm, is_admin

        if not is_admin() or not _init_lhm():
            return self._last_stats

        try:
            from LibreHardwareMonitor.Hardware import SensorType
            from core.cpu import _lhm_computer

            voltages = []
            for hardware in _lhm_computer.Hardware:
                hardware.Update()
                for sub in hardware.SubHardware:
                    sub.Update()
                for sensor in hardware.Sensors:
                    if sensor.SensorType == SensorType.Voltage:
                        val = sensor.Value
                        if val is not None and val >= 0:
                            name = sensor.Name or "Voltage"
                            hw_name = hardware.Name or ""
                            voltages.append({
                                "name": name,
                                "label": f"{hw_name} - {name}" if hw_name else name,
                                "volts": round(float(val), 3),
                            })

            self._last_stats = voltages
            return voltages
        except Exception as e:
            logger.debug(f"Voltage sensor query failed: {e}")
            return self._last_stats
