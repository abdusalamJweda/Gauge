# Gauge — PySide6 Rewrite Plan

## Why Rewrite?

CustomTkinter resize stuttering is a **known unsolvable limitation** confirmed by the maintainer:

> *"I don't think this is solvable. This library and Python itself have their limits."*
> — TomSchimansky, CustomTkinter issue #2690

Every `widget.configure()` goes through Python → Tcl/Tk bridge → canvas redraw. During resize, hundreds of Configure events fire per second, each re-rendering every widget. No batch rendering, no GPU acceleration, no bypass.

PySide6 (Qt) uses native GPU-accelerated rendering with smooth resize by default.

## Scope

Complete rewrite of all GUI code. Same visual layout, same features, smooth resize.

## What Stays the Same

All `core/` files are framework-independent (return plain dicts):
- `core/cpu.py`, `core/gpu.py`, `core/ram.py`, `core/disk.py`
- `core/fan.py`, `core/voltage.py`, `core/network.py`
- `core/storage.py`, `core/processes.py`
- `core/sensors.py`, `core/alerts.py`, `core/logger.py`
- `config.json`, `assets/*`

## Dependency Changes

| Remove | Add |
|--------|-----|
| customtkinter>=5.2.0 | PySide6>=6.5.0 |
| pystray>=0.19.0 | qdarktheme>=1.3.0 |
| keyboard>=0.13.5 | (QShortcut built-in) |

## Widget Mapping

| CustomTkinter | PySide6 |
|---|---|
| `ctk.CTk()` | `QMainWindow` |
| `ctk.CTkFrame` | `QFrame` |
| `ctk.CTkLabel` | `QLabel` |
| `ctk.CTkButton` | `QPushButton` |
| `ctk.CTkProgressBar` | `QProgressBar` |
| `ctk.CTkSlider` | `QSlider` |
| `ctk.CTkRadioButton` | `QRadioButton` |
| `ctk.CTkEntry` | `QLineEdit` |
| `ctk.CTkScrollableFrame` | `QScrollArea` |
| `ctk.CTkTabview` | `QTabWidget` |
| `ctk.CTkToplevel` | `QDialog` / `QWidget(Qt.Window)` |
| `ctk.CTkFont` | `QFont` |
| `tkinter.Canvas` | `QPainter` on `QWidget` |
| `pystray` tray | `QSystemTrayIcon` |
| `keyboard` hotkeys | `QShortcut` |

## File Structure

```
monitor tool/
├── core/                    # UNCHANGED
├── gui/                     # REWRITTEN
│   ├── __init__.py
│   ├── main_window.py       # QMainWindow with cards + graphs + buttons
│   ├── graphs.py            # QPainter-based LiveGraph
│   ├── advanced.py          # QTabWidget advanced window (8 tabs)
│   ├── overlay.py           # Frameless QWidget overlay
│   ├── settings.py          # QDialog settings
│   └── theme.py             # Dark theme constants + qdarktheme setup
├── assets/                  # UNCHANGED
├── main.py                  # REWRITTEN — QApplication entry
├── config.json              # UNCHANGED
├── requirements.txt         # UPDATED
└── docs/
    └── pyside6-rewrite-plan.md
```

## Implementation Order

1. Theme + main window skeleton
2. Sensor cards (4x QFrame with labels + QProgressBar)
3. Live graphs (QWidget + QPainter line charts)
4. Button row
5. Settings dialog
6. Advanced window (8 tabs)
7. Overlay + system tray
8. Hotkeys (QShortcut)
9. Build with Nuitka

## Thread Safety

Sensor polling runs in QThread, emits Signal to main thread:

```python
class SensorWorker(QThread):
    snapshot_ready = Signal(object)
    def run(self):
        while self._running:
            self.aggregator._poll_once()
            self.snapshot_ready.emit(self.aggregator.snapshot)
            time.sleep(interval)
```

## Dark Theme

Use `qdarktheme.setup_theme()` — one line for polished dark theme.

## Build

Nuitka with `--enable-plugin=pyside6`. Expected size ~120-150MB.
