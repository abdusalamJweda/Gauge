<p align="center">
  <img src="assets/gauge.png" alt="Gauge Logo" width="120">
</p>

<h1 align="center">Gauge — Hardware Monitor</h1>

<p align="center">
  A lightweight, real-time hardware monitoring tool for Windows.
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#download--install">Download</a> •
  <a href="#build-from-source">Build from Source</a> •
  <a href="#configuration">Configuration</a> •
  <a href="#project-structure">Structure</a>
</p>

---

A lightweight, real-time hardware monitoring tool for Windows built in Python. Monitors CPU, GPU, RAM, disk, fans, voltages, and network with a dark-mode GUI, transparent overlay, CSV logging, and temperature alerts.

---

## Features

- **Real-time monitoring** — CPU usage/temp/frequency, GPU usage/temp/VRAM/clock, RAM, disk, fans, voltages, network speed
- **Transparent overlay (OSD)** — draggable, always-on-top HUD showing key metrics with color-coded thresholds
- **Dark-mode GUI** — PySide6/Qt interface with live graphs, per-core CPU usage, top processes, and storage details
- **CSV logging** — background logging to daily CSV files with automatic 30-day rotation
- **Temperature alerts** — desktop notifications when CPU/GPU temps exceed configurable thresholds, with cooldown
- **System tray** — minimize to tray with right-click menu (Show / Quit)
- **Min/max/avg tracking** — session statistics for all key metrics
- **Configurable** — all settings in `config.json` (polling interval, thresholds, overlay position/opacity, etc.)

---

## Screenshots

> _Screenshots coming soon._

---

## Download & Install

### Option A: Download the .exe (Recommended)

1. Go to the [Releases](https://github.com/abdusalamJweda/Gauge/releases) page.
2. Download the latest `Gauge.exe` from the most recent release.
3. Place `Gauge.exe` in any folder you want (e.g. `C:\Tools\Gauge`).
4. Double-click `Gauge.exe` to launch.
5. If Windows SmartScreen pops up, click **More info** > **Run anyway**.
6. Accept the UAC prompt (admin privileges are required for CPU temperature readings).
7. The app opens with the dark-mode dashboard. The transparent overlay is enabled by default.

> The `.exe` is fully self-contained — no Python installation required.

### Option B: Run from Source

> Requires [Python 3.9+](https://www.python.org/downloads/) installed.

1. **Clone the repository**
   ```bash
   git clone https://github.com/abdusalamJweda/Gauge.git
   cd Gauge
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the app**
   ```bash
   python main_qt.py
   ```

4. Accept the UAC prompt when prompted.

---

## Build from Source

If you want to build the `.exe` yourself:

1. Install [PyInstaller](https://pyinstaller.org/):
   ```bash
   pip install pyinstaller
   ```

2. Run the build script:
   ```bash
   build.bat
   ```

3. The compiled `Gauge.exe` will be in the `dist/` folder.

---

## Configuration

All settings live in `config.json`. Key options:

```jsonc
{
  "polling_interval_seconds": 1,      // Sensor poll rate
  "temperature_unit": "C",            // "C" or "F"
  "alerts": {
    "cpu_temp_threshold_c": 85,       // CPU alert threshold
    "gpu_temp_threshold_c": 83,       // GPU alert threshold
    "cooldown_seconds": 300           // Min time between alerts
  },
  "logging": {
    "enabled": false,                 // Enable CSV logging
    "log_dir": "logs",
    "retention_days": 30              // Auto-delete old logs
  },
  "overlay": {
    "enabled": true,
    "opacity": 0.41,
    "position": "top-right",          // top-right, top-left, bottom-right, bottom-left
    "bg_color": "#1e1e2e",
    "font_size": 10,
    "show_cpu": true,
    "show_gpu": true,
    "show_ram": true,
    "show_fps": true,
    "show_net": true
  },
  "graphs": {
    "enabled": true,
    "max_points": 60
  }
}
```

---

## Project Structure

```
Gauge/
├── main_qt.py            # Qt entry point
├── config.json           # User configuration
├── requirements.txt
├── build.bat             # PyInstaller build script
├── Gauge.spec            # PyInstaller spec file
├── core/
│   ├── sensors.py        # SensorAggregator — orchestrates all polling
│   ├── cpu.py            # CPU sensor (psutil + LHM for temps)
│   ├── gpu.py            # GPU sensor (pynvml)
│   ├── ram.py            # RAM sensor
│   ├── disk.py           # Disk usage sensor
│   ├── fan.py            # Fan speed sensor (LHM/WMI)
│   ├── voltage.py        # Voltage sensor (LHM/WMI)
│   ├── network.py        # Network speed sensor
│   ├── storage.py        # Storage drive details (LHM/WMI)
│   ├── processes.py      # Top processes by CPU/memory
│   ├── alerts.py         # Temperature threshold alerts
│   └── logger.py         # Background CSV logger
├── gui/
│   ├── main_window.py    # Qt main window
│   ├── overlay.py        # Transparent OSD overlay
│   ├── overlay_settings.py
│   ├── settings.py       # Settings dialog
│   ├── advanced.py       # Advanced details tab
│   ├── graphs.py         # Live metric graphs
│   ├── app.py            # CustomTkinter app (legacy, unused)
│   └── theme.py          # Color constants
├── assets/
│   ├── gauge.ico         # App icon
│   ├── gauge.png         # App icon (PNG)
│   └── LibreHardwareMonitorLib.dll
└── docs/
    ├── PROJECT_PLAN.md
    ├── OVERLAY_PLAN.md
    └── pyside6-rewrite-plan.md
```

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `psutil` | CPU, RAM, disk, network stats |
| `py-cpuinfo` | CPU model name |
| `GPUtil` | GPU info fallback |
| `pynvml` | NVIDIA GPU monitoring (temp, VRAM, clock, fan, power) |
| `wmi` | LibreHardwareMonitor WMI queries for CPU/disk temps |
| `keyboard` | Global hotkey support |
| `PySide6` | Qt GUI framework |
| `qdarkstyle` | Dark theme stylesheet |

---

## Requirements

- **OS:** Windows 10 or Windows 11
- **Python:** 3.9+ (only if running from source)
- **Privileges:** Admin (auto-elevated on launch)

---

## CPU Temperature

CPU temperature requires **admin privileges** and the bundled **LibreHardwareMonitorLib.dll**. The app auto-elevates on launch. If you deny the UAC prompt, temperature will show as `N/A`.

---

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

Not specified. For personal use.
