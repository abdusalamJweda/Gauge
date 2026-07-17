@echo off
echo Running disk temperature test as Administrator...
echo.
powershell -Command "Start-Process python -ArgumentList '\"'%~dp0test_disk.py'\"' -Verb RunAs -Wait"
echo.
if exist "%~dp0disk_result.txt" (
    type "%~dp0disk_result.txt"
) else (
    echo No result file - UAC may have been declined
)
echo.
pause
