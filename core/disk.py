import psutil
import ctypes
import ctypes.wintypes as wintypes
import struct
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

_lhm_disk_temps = {}


def set_lhm_disk_temps(temps: dict):
    global _lhm_disk_temps
    _lhm_disk_temps = temps

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 1
FILE_SHARE_WRITE = 2
FILE_SHARE_DELETE = 4
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = -1

IOCTL_SCSI_MINIPORT = 0x0004D008
IOCTL_STORAGE_QUERY_PROPERTY = 0x002D1400


class SRB_IO_CONTROL(ctypes.Structure):
    _fields_ = [
        ("HeaderLength", wintypes.DWORD),
        ("Signature", ctypes.c_char * 8),
        ("Timeout", wintypes.DWORD),
        ("ControlCode", wintypes.DWORD),
        ("ReturnCode", wintypes.DWORD),
        ("Length", wintypes.DWORD),
    ]


STORAGE_PROTOCOL_COMMAND = 0x002221D8
STORAGE_PROTOCOL_NVME = 0x4E564D45
NVME_ADMIN_COMMAND_GET_LOG_PAGE = 0x02
NVME_SMART_LOG_PAGE_ID = 0x02


class STORAGE_PROTOCOL_COMMAND_HEADER(ctypes.Structure):
    _fields_ = [
        ("Version", wintypes.DWORD),
        ("Protocol", wintypes.DWORD),
        ("Flags", wintypes.DWORD),
        ("CommandLength", wintypes.DWORD),
        ("ErrorInfoLength", wintypes.DWORD),
        ("DataToDeviceTransferLength", wintypes.DWORD),
        ("DataFromDeviceTransferLength", wintypes.DWORD),
        ("TimeOutValue", wintypes.DWORD),
        ("Status", wintypes.DWORD),
        ("ReturnedStatus", wintypes.DWORD),
        ("Reserved0", wintypes.DWORD),
        ("CdbLength", ctypes.c_ubyte),
        ("CdbSize", ctypes.c_ubyte),
        ("Reserved1", ctypes.c_ubyte * 2),
        ("Cdb", ctypes.c_ubyte * 16),
    ]


def _open_drive(drive_path: str, read_only: bool = True):
    kernel32 = ctypes.windll.kernel32
    access = GENERIC_READ if read_only else (GENERIC_READ | GENERIC_WRITE)
    sharing = FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE
    handle = kernel32.CreateFileW(
        drive_path, access, sharing, None, OPEN_EXISTING, 0, None,
    )
    if handle == INVALID_HANDLE_VALUE:
        handle = kernel32.CreateFileW(
            drive_path, 0, sharing, None, OPEN_EXISTING, 0, None,
        )
    return handle if handle != INVALID_HANDLE_VALUE else None


def _query_nvme_smart_temp(drive_path: str) -> Optional[float]:
    try:
        handle = _open_drive(drive_path)
        if handle is None:
            return None

        buf_size = 8192
        buf = ctypes.create_string_buffer(buf_size)

        header = STORAGE_PROTOCOL_COMMAND_HEADER.from_buffer(buf)
        header.Version = 1
        header.Protocol = STORAGE_PROTOCOL_NVME
        header.CommandLength = 64
        header.ErrorInfoLength = 0
        header.DataToDeviceTransferLength = 4096
        header.DataFromDeviceTransferLength = 0
        header.TimeOutValue = 10
        header.CdbLength = 0
        header.CdbSize = 0

        nvme_offset = ctypes.sizeof(STORAGE_PROTOCOL_COMMAND_HEADER)
        nvme_buf = (ctypes.c_ubyte * 64).from_buffer(buf, nvme_offset)
        numd = (4096 // 4) - 1
        cmd = struct.pack("<BBBBHBBHII", NVME_ADMIN_COMMAND_GET_LOG_PAGE, 0, 0, 0, 0, 0, 0, 0, NVME_SMART_LOG_PAGE_ID, numd, 0)
        ctypes.memmove(nvme_buf, cmd, len(cmd))

        bytes_returned = wintypes.DWORD(0)
        ok = ctypes.windll.kernel32.DeviceIoControl(
            handle, STORAGE_PROTOCOL_COMMAND, buf, buf_size, buf, buf_size,
            ctypes.byref(bytes_returned), None,
        )
        ctypes.windll.kernel32.CloseHandle(handle)

        if ok and bytes_returned.value >= nvme_offset + 64 + 4096 + 16:
            data_offset = nvme_offset + 64
            temp_raw = struct.unpack_from("<H", buf, data_offset + 1)[0]
            if temp_raw > 0:
                temp_c = (temp_raw - 27315) / 100.0
                if 0 < temp_c < 150:
                    return round(temp_c, 1)
        return None
    except Exception as e:
        logger.debug(f"NVMe SMART query failed for {drive_path}: {e}")
        return None


def _query_srb_miniport_temp(drive_path: str) -> Optional[float]:
    try:
        handle = _open_drive(drive_path)
        if handle is None:
            return None

        header_size = ctypes.sizeof(SRB_IO_CONTROL)
        buf_size = header_size + 16 + 64 + 16 + 16 + 4096
        buf = ctypes.create_string_buffer(buf_size)

        srb = SRB_IO_CONTROL.from_buffer(buf)
        srb.HeaderLength = header_size
        srb.Signature = b"SCSI\\Miniport"
        srb.Timeout = 10
        srb.ControlCode = 0xE  # IOCTL_SCSI_MINIPORT_NVM
        srb.Length = buf_size - header_size

        off = header_size + 16
        numd = (4096 // 4) - 1
        cmd = struct.pack("<BBBBHBBHII", NVME_ADMIN_COMMAND_GET_LOG_PAGE, 0, 0, 0, 0, 0, 0, 0, NVME_SMART_LOG_PAGE_ID, numd, 0)
        ctypes.memmove(ctypes.addressof(buf) + off, cmd, min(len(cmd), 64))

        bytes_returned = wintypes.DWORD(0)
        ok = ctypes.windll.kernel32.DeviceIoControl(
            handle, IOCTL_SCSI_MINIPORT, buf, buf_size, buf, buf_size,
            ctypes.byref(bytes_returned), None,
        )
        ctypes.windll.kernel32.CloseHandle(handle)

        if ok and srb.ReturnCode == 0:
            data_off = header_size + 16 + 64 + 16 + 16
            if bytes_returned.value >= data_off + 512:
                temp_raw = struct.unpack_from("<H", buf, data_off + 1)[0]
                if temp_raw > 0:
                    temp_c = (temp_raw - 27315) / 100.0
                    if 0 < temp_c < 150:
                        return round(temp_c, 1)
        return None
    except Exception as e:
        logger.debug(f"SRB miniport query failed for {drive_path}: {e}")
        return None


def _query_all_drive_temps() -> dict:
    temps = {}
    kernel32 = ctypes.windll.kernel32
    for i in range(16):
        drive_path = f"\\\\.\\PhysicalDrive{i}"
        sharing = FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE
        handle = kernel32.CreateFileW(drive_path, 0, sharing, None, OPEN_EXISTING, 0, None)
        if handle == INVALID_HANDLE_VALUE:
            break
        kernel32.CloseHandle(handle)

        temp = _query_nvme_smart_temp(drive_path)
        if temp is None:
            temp = _query_srb_miniport_temp(drive_path)
        if temp is not None:
            temps[i] = temp
    return temps


def _get_wmi_drive_mapping() -> dict:
    mapping = {}
    try:
        import wmi
        w = wmi.WMI()
        for disk in w.Win32_DiskDrive():
            drive_idx = disk.Index
            for logical in disk.Associators("Win32_DiskDriveToDiskPartition"):
                for logical_disk in logical.Associators("Win32_LogicalDiskToPartition"):
                    if hasattr(logical_disk, "DeviceID") and logical_disk.DeviceID:
                        letter = logical_disk.DeviceID[0].upper()
                        mapping[letter] = drive_idx
    except Exception as e:
        logger.debug(f"WMI drive mapping failed: {e}")
    return mapping


class DiskSensor:
    def __init__(self):
        self._last_stats: Optional[List[dict]] = None
        self._drive_temps: dict = {}
        self._drive_mapping: dict = {}
        self._temp_query_count = 0
        self._mapping_loaded = False

    def _load_mapping(self):
        if not self._mapping_loaded:
            self._drive_mapping = _get_wmi_drive_mapping()
            self._mapping_loaded = True

    @staticmethod
    def _get_drive_model_names() -> dict:
        mapping = {}
        try:
            import wmi
            w = wmi.WMI()
            for disk in w.Win32_DiskDrive():
                mapping[disk.Index] = (disk.Model or "").strip()
        except Exception:
            pass
        return mapping

    @staticmethod
    def _match_lhm_temps() -> dict:
        if not _lhm_disk_temps:
            logger.info("No LHM disk temps available")
            return {}
        model_map = DiskSensor._get_drive_model_names()
        logger.info(f"WMI drive models: {model_map}")
        logger.info(f"LHM disk temps: {_lhm_disk_temps}")
        result = {}
        for drive_idx, model_name in model_map.items():
            for lhm_name, temp in _lhm_disk_temps.items():
                if model_name and model_name.lower() in lhm_name.lower():
                    result[drive_idx] = temp
                    break
                if lhm_name.lower() in model_name.lower():
                    result[drive_idx] = temp
                    break
        if not result and len(_lhm_disk_temps) == len(model_map):
            sorted_lhm = sorted(_lhm_disk_temps.items(), key=lambda x: x[0])
            sorted_drives = sorted(model_map.keys())
            for i, drive_idx in enumerate(sorted_drives):
                if i < len(sorted_lhm):
                    result[drive_idx] = sorted_lhm[i][1]
        logger.info(f"Matched LHM temps: {result}")
        return result

    def get_stats(self) -> List[dict]:
        try:
            self._load_mapping()

            if self._temp_query_count % 30 == 0:
                self._drive_temps = _query_all_drive_temps()
            self._temp_query_count += 1

            lhm_temps = self._match_lhm_temps()

            disks = []
            for part in psutil.disk_partitions(all=False):
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    letter = part.mountpoint[0].upper()
                    drive_num = self._drive_mapping.get(letter)

                    temp = None
                    if drive_num is not None:
                        temp = lhm_temps.get(drive_num)
                        if temp is None:
                            temp = self._drive_temps.get(drive_num)

                    disks.append({
                        "device": part.device,
                        "mountpoint": part.mountpoint,
                        "fstype": part.fstype,
                        "total_gb": round(usage.total / (1024**3), 2),
                        "used_gb": round(usage.used / (1024**3), 2),
                        "free_gb": round(usage.free / (1024**3), 2),
                        "percent": usage.percent,
                        "temp_celsius": temp,
                        "drive_number": drive_num,
                    })
                except PermissionError:
                    continue
                except OSError:
                    continue
            self._last_stats = disks
            return disks
        except Exception:
            return self._last_stats or []
