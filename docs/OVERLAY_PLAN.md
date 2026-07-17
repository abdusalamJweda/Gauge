# Overlay Feature Plan

## Overview
Add a lightweight, always-on-top hardware overlay showing FPS, CPU usage, GPU usage, and RAM usage. Toggle from the main window with a settings icon next to it.

---

## Overlay Design

### Layout
Horizontal bar, single line, semi-transparent dark background.

```
  CPU 45%   GPU 72%   RAM 61%   FPS --
```

- **Width:** auto-sized to content
- **Height:** ~36px (single line, compact font)
- **Position:** top-right by default (configurable)
- **Opacity:** 85% by default (configurable 30-100%)
- **Always on top:** yes
- **Draggable:** click and drag anywhere on the overlay

### Styling
- Background: `#1a1a2e` at configured alpha
- Text: Consolas monospace, size 12 (configurable 10-16)
- Color coding per metric:
  - CPU: green at rest, yellow >65%, red >85%
  - GPU: green at rest, yellow >75%, red >90%
  - RAM: green at rest, yellow >70%, red >90%
  - FPS: green if >60, yellow if >30, red if <30, gray if unavailable

### FPS Handling
FPS is not available via standard hardware sensors. Default shows "--" in gray.
Future-proofed with an `fps` field in `SensorSnapshot` for PresentMon or other sources.

---

## Main Window Changes

### Button Bar
New controls added next to Settings button:

```
[ Start Log ] [ Settings ] [ Overlay ] [ gear ]
```

- **Overlay button:** Toggle on/off. Purple `#7c3aed` when active, `#555` when inactive.
- **Gear button:** 28x28, opens `OverlaySettingsDialog`.

---

## Overlay Settings Dialog

Small popup (300x400) with:

| Setting | Control | Default |
|---|---|---|
| Opacity | Slider 30-100% | 85% |
| Position | Dropdown (4 corners) | top-right |
| Show CPU | Switch | On |
| Show GPU | Switch | On |
| Show RAM | Switch | On |
| Show FPS | Switch | On |
| Background color | Radio buttons (4 themes) | Dark Navy |
| Font size | Slider 10-16 | 12 |

---

## Config Addition

```json
"overlay": {
  "enabled": false,
  "opacity": 0.85,
  "position": "top-right",
  "show_cpu": true,
  "show_gpu": true,
  "show_ram": true,
  "show_fps": true,
  "bg_color": "#1a1a2e",
  "font_size": 12
}
```

---

## Files

| File | Action |
|---|---|
| `gui/overlay.py` | Created |
| `gui/overlay_settings.py` | Created |
| `gui/app.py` | Modified |
| `core/sensors.py` | Modified |
| `docs/OVERLAY_PLAN.md` | This file |
