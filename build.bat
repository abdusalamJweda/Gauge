@echo off
cd /d "%~dp0"
echo Building Gauge Hardware Monitor...
echo.

pyinstaller ^
    --name "Gauge" ^
    --onefile ^
    --windowed ^
    --icon "assets\gauge.ico" ^
    --add-data "assets\gauge.ico;assets" ^
    --add-data "assets\gauge.png;assets" ^
    --add-data "assets\LibreHardwareMonitorLib.dll;assets" ^
    --add-data "config.json;." ^
    --hidden-import pystray ^
    --hidden-import PIL ^
    --hidden-import ctypes ^
    --noconfirm ^
    --clean ^
    main.py

echo.
if %ERRORLEVEL% EQU 0 (
    echo Build successful! Output: dist\Gauge.exe
) else (
    echo Build failed.
)
pause
