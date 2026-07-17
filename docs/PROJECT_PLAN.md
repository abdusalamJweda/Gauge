# Hardware Monitor — Project Plan

A fully featured, professional hardware monitoring application for Windows, built in Python.

---

## Tech Stack

| Layer | Tool | Why |
|---|---|---|
| Backend | `psutil`, `GPUtil`, `wmi` + LibreHardwareMonitor | CPU/RAM/Disk/GPU + accurate CPU temps on Windows |
| GUI | **CustomTkinter** | Modern dark theme out-of-the-box, lightweight, MIT license |
| System Tray | `pystray` | Lightweight tray icon integration for CustomTkinter |
| Alerts | `plyer` (desktop notifications) | Non-intrusive toast notifications |
| Packaging | **Nuitka** | Compiles to C, smaller binary, fewer AV false positives |
| Logging | CSV + threading | Simple background CSV logger, one file per day |
| Config | `json` | User-editable settings file |

---

## Design Decisions (Locked)

| Decision | Choice | Rationale |
|---|---|---|
| GUI framework | CustomTkinter | Lightweight, dark mode built-in, MIT license |
| Admin privileges | Warn only, no auto-relaunch | Show warning if not admin; disable CPU temp, don't force UAC |
| GPU support | NVIDIA only (via GPUtil) | AMD/Intel can be added later in Phase 3 |
| Live graphs | No — text + progress bars only | Keeps UI simple and fast |
| Packaging | Nuitka | Better binary quality, fewer false positives |
| Installer | Bare `.exe` only | No Inno Setup/NSIS; user runs the .exe directly |
| Logging format | CSV | Universal, opens in Excel, one file per day |
| Alert mechanism | Desktop toast notification (plyer) | Non-intrusive, standard Windows look |
| Temperature unit | Celsius default with toggle to Fahrenheit | Toggle in settings |

---

## Phase 1 — Architecture & Core Logic

**Goal:** Clean, OOP-based backend that gathers all sensor data reliably.

### Tasks

1. **Project scaffolding**
   - Create folder structure:
     ```
     monitor_tool/
     ├── main.py              # Entry point
     ├── core/
     │   ├── __init__.py
     │   ├── cpu.py           # CPU sensor class
     │   ├── gpu.py           # GPU sensor class
     │   ├── ram.py           # RAM sensor class
     │   ├── disk.py          # Disk sensor class
     │   └── sensors.py       # Aggregator / facade
     ├── gui/
     │   └── ...
     ├── assets/
     │   └── icon.ico
     ├── config.json
     └── docs/
     ```
   - Create `requirements.txt` with pinned versions.

2. **Sensor classes (one per component)**
   - Each class exposes a `get_stats() -> dict` method returning normalized keys:
     - **CPU:** `usage_percent`, `temp_celsius`, `freq_mhz`, `core_count`
     - **GPU:** `name`, `usage_percent`, `temp_celsius`, `vram_used_mb`, `vram_total_mb`
     - **RAM:** `total_gb`, `used_gb`, `percent`, `available_gb`
     - **Disk:** list of `{device, total_gb, used_gb, percent}`
   - Handle errors gracefully — return `None` or defaults on failure.

3. **LibreHardwareMonitor integration**
   - Bundle the LHM DLL and query via `wmi` for CPU temperature.
   - **Detect admin privileges** at startup.
   - If **not admin**: log a warning, set CPU temp to `None`, continue running.
   - Do **not** auto-elevate or restart as admin.

4. **SensorAggregator class**
   - Calls each sensor class on a configurable interval (default 1 s).
   - Stores latest snapshot in a `dataclass` or `TypedDict`.
   - Thread-safe — aggregator runs in a background `threading.Thread`.

### Recommended Libraries
- `psutil>=5.9`
- `GPUtil>=1.4`
- `wmi` (the `WMI` package on PyPI)
- LibreHardwareMonitorLib (bundled DLL)

### Pitfalls
| Pitfall | Mitigation |
|---|---|
| LHM needs admin | Detect early, warn once, disable CPU temp if missing |
| `wmi` queries can hang | Run in a thread with timeout; cache last-known value |
| GPU not NVIDIA | Gracefully return empty defaults from GPU sensor class |
| High CPU from polling | Use 1 s+ interval; avoid tight loops |

### Milestone 1
> Run `python main.py` in terminal and see a live-updating dict of CPU/GPU/RAM/Disk stats printed every second.

---

## Phase 2 — GUI Development

**Goal:** Modern dark-mode interface showing all stats in real time.

### Tasks

1. **Set up CustomTkinter**
   - `pip install customtkinter`
   - Appearance: `customtkinter.set_appearance_mode("dark")`
   - Color theme: `"dark-blue"`

2. **Main window layout**
   ```
   +----------------------------------------------+
   |  Hardware Monitor                      - [] X |
   +----------------------------------------------+
   |  [CPU]  Usage: 45%  Temp: 62C                |
   |         ████████████░░░░░  45%               |
   |  [GPU]  Usage: 78%  Temp: 71C                |
   |         ████████████████████░  78%           |
   |  [RAM]  12.4 / 32.0 GB (39%)                |
   |         ████████░░░░░░░░░░  39%              |
   |  [DISK] C: 245 / 512 GB (48%)               |
   |         ██████████░░░░░░░░  48%              |
   +----------------------------------------------+
   |  [> Start Log]   [Settings]                  |
   +----------------------------------------------+
   ```
   - Use `CTkFrame` cards per component.
   - `CTkProgressBar` for usage percentages.
   - Labels update every 1 s via `after()` callback (NOT infinite loop).
   - If CPU temp unavailable (no admin), show `N/A` instead of a value.

3. **Settings panel**
   - Polling interval slider (1 s to 5 s).
   - Temperature unit toggle (C / F).
   - Alert threshold inputs for CPU and GPU temperature.

4. **DPI awareness**
   - Add `ctypes.windll.shcore.SetProcessDpiAwareness(1)` at startup for proper scaling.

### Recommended Libraries
- `customtkinter>=5.2`

### Pitfalls
| Pitfall | Mitigation |
|---|---|
| UI freezes during WMI query | All sensor reads happen in background thread; GUI reads latest snapshot only |
| `after()` scheduling drift | Re-schedule at fixed intervals, do not nest `after()` calls |
| DPI scaling on Windows | Set DPI awareness before window creation |

### Milestone 2
> Dark-mode window opens, shows live CPU/GPU/RAM/Disk stats with progress bars, updates every second without freezing.

---

## Phase 3 — Advanced Features

**Goal:** Logging, system tray, and alerts turn this from a toy into a tool.

### Tasks

1. **Background CSV logging**
   - New `Logger` class writes a row every N seconds to `logs/hardware_YYYY-MM-DD.csv`.
   - Runs in its own thread; controlled by Start/Stop button in UI.
   - Columns: `timestamp, cpu_usage, cpu_temp, gpu_usage, gpu_temp, ram_percent, disk_c_usage, ...`
   - Auto-rotate: delete CSV files older than 30 days.

2. **System tray integration**
   - `pip install pystray Pillow`
   - Minimize-to-tray: hide window, show tray icon with context menu (Show / Quit).
   - Tray icon tooltip shows CPU temperature.
   - Use a high-contrast `.ico` that is visible in both light and dark Windows themes.

3. **High-temperature alerts**
   - Configurable thresholds in `config.json` (default: CPU > 85C, GPU > 83C).
   - When exceeded: desktop toast notification via `plyer`.
   - **Cooldown timer:** alert once per 5 minutes, not every polling cycle.
   - Track last-alert timestamp per sensor to avoid spam.

4. **App logging**
   - Use Python `logging` module to write `app.log` for crash diagnostics.
   - Log rotation: max 5 MB, keep last 3 backups.

### Recommended Libraries
- `pystray>=0.19`
- `Pillow>=10.0` (required by pystray)
- `plyer>=2.1`

### Pitfalls
| Pitfall | Mitigation |
|---|---|
| Tray icon invisible on Windows dark mode | Ship a high-contrast icon file |
| Notification spam from polling | Cooldown timer per sensor (5 min default) |
| CSV files grow huge | Auto-delete logs older than 30 days |
| WMI crash in tray mode | Catch exceptions, show "sensor error" in tooltip, do not crash |
| `plyer` notification not showing | Check Windows notification permissions; log failure silently |

### Milestone 3
> App runs in system tray, logs data to CSV, and fires a desktop notification when CPU temp exceeds threshold.

---

## Phase 4 — Packaging & Distribution

**Goal:** Standalone `.exe` that anyone can run without Python installed.

### Tasks

1. **Set up Nuitka**
   - Install: `pip install nuitka`
   - Initial build command:
     ```
     python -m nuitka --onefile --windows-console-mode=disable --enable-plugin=tk-inter main.py
     ```
   - Add `--windows-icon-from-ico=assets/icon.ico` for custom icon.

2. **Bundle dependencies**
   - Include `config.json` via `--include-data-files`.
   - Include LibreHardwareMonitor DLL.
   - Include tray icon `.ico` and `.png`.

3. **Icon and metadata**
   - Create a custom `.ico` for the `.exe` (32x32, 48x48, 256x256).
   - Set version info in Nuitka config: `--windows-file-version`, `--windows-product-name`.

4. **Test on clean machine**
   - Run on a Windows machine **without Python installed**.
   - Verify: no DLL missing errors, tray icon works, logging works, warning shows for non-admin.

5. **Anti-virus testing**
   - Upload to VirusTotal to check for false positives.
   - If flagged, use Nuitka exclusions to strip unnecessary modules.

### Recommended Tools
- `nuitka>=1.8`

### Pitfalls
| Pitfall | Mitigation |
|---|---|
| Windows Defender flags `.exe` | Test on VirusTotal; use Nuitka (fewer false positives than PyInstaller) |
| Missing DLL errors at runtime | Test on a fresh Windows VM; bundle all required DLLs |
| Large file size | Use UPX compression with Nuitka |
| LHM DLL not found at runtime | Bundle in same directory; use `os.path.dirname(sys.executable)` path |

### Milestone 4
> Double-click `hardware_monitor.exe` on a clean Windows machine — app opens, monitors hardware, logs to CSV, shows tray icon.

---

## Development Timeline

| Phase | Time Estimate | Dependencies |
|---|---|---|
| Phase 1 — Core Logic | 3-5 days | None |
| Phase 2 — GUI | 4-6 days | Phase 1 |
| Phase 3 — Advanced | 3-5 days | Phase 2 |
| Phase 4 — Packaging | 2-3 days | Phases 1-3 |
| **Total** | **~12-19 days** | |

---

## `requirements.txt` (Reference)

```
psutil>=5.9.0
GPUtil>=1.4.0
WMI>=1.5.1
customtkinter>=5.2.0
pystray>=0.19.0
Pillow>=10.0.0
plyer>=2.1.0
nuitka>=1.8.0
```

---

## `config.json` (Default)

```json
{
  "polling_interval_seconds": 1,
  "temperature_unit": "C",
  "alerts": {
    "cpu_temp_threshold_c": 85,
    "gpu_temp_threshold_c": 83,
    "cooldown_seconds": 300
  },
  "logging": {
    "enabled": false,
    "log_dir": "logs",
    "retention_days": 30
  },
  "gui": {
    "theme": "dark",
    "show_cpu": true,
    "show_gpu": true,
    "show_ram": true,
    "show_disk": true
  }
}
```
