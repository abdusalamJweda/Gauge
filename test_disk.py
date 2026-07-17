import ctypes
import ctypes.wintypes as wintypes
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))
result_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "disk_result.txt")
results = []

kernel32 = ctypes.windll.kernel32
GENERIC_READ = 0x80000000
FILE_SHARE_RW = 1 | 2 | 4
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = -1

results.append(f"Admin: {bool(ctypes.windll.shell32.IsUserAnAdmin())}")

for i in range(2):
    drive_path = f"\\\\.\\PhysicalDrive{i}"
    handle = kernel32.CreateFileW(drive_path, GENERIC_READ, FILE_SHARE_RW, None, OPEN_EXISTING, 0, None)
    if handle == INVALID_HANDLE_VALUE:
        results.append(f"{drive_path}: Open fail err={ctypes.get_last_error()}")
        continue
    results.append(f"{drive_path}: Open OK h={handle}")
    kernel32.CloseHandle(handle)
    results.append(f"  Closed OK")

    handle2 = kernel32.CreateFileW(drive_path, GENERIC_READ, FILE_SHARE_RW, None, OPEN_EXISTING, 0, None)
    if handle2 == INVALID_HANDLE_VALUE:
        results.append(f"  Reopen FAIL err={ctypes.get_last_error()}")
        continue
    results.append(f"  Reopen OK h={handle2}")

    IOCTL_STORAGE_QUERY_PROPERTY = 0x002D1400
    class Q(ctypes.Structure):
        _fields_ = [("PropertyId", wintypes.DWORD), ("QueryType", wintypes.DWORD)]
    q = Q()
    q.PropertyId = 0
    q.QueryType = 0
    out = ctypes.create_string_buffer(512)
    ret = wintypes.DWORD(0)
    ok = kernel32.DeviceIoControl(handle2, IOCTL_STORAGE_QUERY_PROPERTY, ctypes.byref(q), ctypes.sizeof(q), out, 512, ctypes.byref(ret), None)
    err = ctypes.get_last_error()
    results.append(f"  DeviceIoControl: {'OK' if ok else 'FAIL'} err={err} bytes={ret.value}")
    kernel32.CloseHandle(handle2)

with open(result_path, "w") as f:
    f.write("\n".join(results))
