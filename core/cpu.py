import psutil
import ctypes
import os
import sys
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_admin_warning_shown = False
_lhm_computer = None


def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def _get_dll_path() -> str:
    if getattr(sys, "frozen", False):
        try:
            buf = ctypes.create_unicode_buffer(512)
            ctypes.windll.kernel32.GetModuleFileNameW(None, buf, 512)
            base = os.path.dirname(os.path.abspath(buf.value))
        except Exception:
            base = os.path.dirname(os.path.abspath(sys.argv[0]))
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "assets", "LibreHardwareMonitorLib.dll")


def _init_lhm():
    global _lhm_computer
    if _lhm_computer is not None:
        return _lhm_computer is not False

    dll_path = _get_dll_path()
    if not os.path.isfile(dll_path):
        logger.debug(f"LHM DLL not found: {dll_path}")
        _lhm_computer = False
        return False

    try:
        import clr
        clr.AddReference(dll_path)
        from LibreHardwareMonitor.Hardware import Computer, SensorType

        computer = Computer()
        computer.IsCpuEnabled = True
        computer.IsGpuEnabled = False
        computer.IsMotherboardEnabled = False
        computer.IsStorageEnabled = True
        computer.IsMemoryEnabled = False
        computer.IsNetworkEnabled = False
        computer.Open()

        _lhm_computer = computer
        logger.info("LibreHardwareMonitor initialized")
        return True
    except Exception as e:
        logger.debug(f"LHM init failed: {e}")
        _lhm_computer = False
        return False


def _get_lhm_temp() -> Optional[float]:
    if not is_admin():
        global _admin_warning_shown
        if not _admin_warning_shown:
            logger.warning("Not running as admin. CPU temperature unavailable.")
            _admin_warning_shown = True
        return None

    if not _init_lhm():
        return None

    try:
        from LibreHardwareMonitor.Hardware import SensorType

        for hardware in _lhm_computer.Hardware:
            hardware.Update()
            for sub in hardware.SubHardware:
                sub.Update()

        for hardware in _lhm_computer.Hardware:
            for sensor in hardware.Sensors:
                if sensor.SensorType == SensorType.Temperature:
                    val = sensor.Value
                    if val is not None and val > 0:
                        return float(val)
        return None
    except Exception as e:
        logger.debug(f"LHM temp query failed: {e}")
        return None


def _get_psutil_temp() -> Optional[float]:
    try:
        temps = psutil.sensors_temperatures()
        if not temps:
            return None
        for name in ("coretemp", "k10temp", "cpu_thermal", "acpitz"):
            if name in temps and temps[name]:
                readings = [t.current for t in temps[name] if t.current > 0]
                if readings:
                    return sum(readings) / len(readings)
        for name, entries in temps.items():
            readings = [t.current for t in entries if t.current > 0]
            if readings:
                return sum(readings) / len(readings)
        return None
    except (AttributeError, OSError):
        return None


def get_lhm_disk_temps() -> dict:
    if not is_admin():
        return {}
    if not _init_lhm():
        return {}
    try:
        from LibreHardwareMonitor.Hardware import SensorType, HardwareType
        temps = {}
        hw_list = list(_lhm_computer.Hardware)
        logger.info(f"LHM hardware count: {len(hw_list)}")
        for hardware in hw_list:
            hw_type = hardware.HardwareType
            logger.info(f"LHM hw: {hardware.Name} type={hw_type}")
            hardware.Update()
            for sub in hardware.SubHardware:
                sub.Update()
                logger.info(f"  sub: {sub.Name} type={sub.HardwareType}")
            for sensor in hardware.Sensors:
                if sensor.SensorType == SensorType.Temperature:
                    logger.info(f"  sensor: {sensor.Name} = {sensor.Value}")
        for hardware in hw_list:
            if hardware.HardwareType == HardwareType.Storage:
                for sensor in hardware.Sensors:
                    if sensor.SensorType == SensorType.Temperature:
                        val = sensor.Value
                        if val is not None and val > 0:
                            name = hardware.Name or ""
                            temps[name] = float(val)
                            logger.info(f"LHM disk temp: {name} = {val}")
        logger.info(f"LHM disk temps result: {temps}")
        return temps
    except Exception as e:
        logger.debug(f"LHM disk temp query failed: {e}")
        return {}


class CpuSensor:
    def __init__(self):
        self._last_usage: Optional[float] = None
        self._last_temp: Optional[float] = None
        self._last_freq: Optional[float] = None
        self._core_count: int = psutil.cpu_count(logical=True) or 0
        self._physical_cores: int = psutil.cpu_count(logical=False) or 0
        self._model_name: Optional[str] = self._detect_model()

    def _detect_model(self) -> Optional[str]:
        try:
            import wmi
            w = wmi.WMI()
            for cpu in w.Win32_Processor():
                return cpu.Name.strip()
        except Exception:
            pass
        try:
            import platform
            return platform.processor()
        except Exception:
            return None

    def get_stats(self) -> dict:
        try:
            usage = psutil.cpu_percent(interval=0.1)
            self._last_usage = usage
        except Exception:
            usage = self._last_usage

        try:
            freq = psutil.cpu_freq()
            if freq:
                self._last_freq = freq.current
        except Exception:
            pass

        temp = _get_lhm_temp()
        if temp is None:
            temp = _get_psutil_temp()
        self._last_temp = temp

        return {
            "model_name": self._model_name,
            "usage_percent": usage,
            "temp_celsius": round(temp, 1) if temp is not None else None,
            "freq_mhz": round(self._last_freq, 0) if self._last_freq else None,
            "core_count": self._core_count,
            "physical_cores": self._physical_cores,
        }
