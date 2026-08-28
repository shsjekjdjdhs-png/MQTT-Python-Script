@echo off
cd /d "%~dp0"
title Bin_Sensor1 Watchdog

if exist "Bin_Sensor1.stop" del "Bin_Sensor1.stop"

echo Starting Bin_Sensor1 watchdog...

:loop
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p = Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'python.exe' -or $_.Name -eq 'py.exe') -and $_.CommandLine -match 'Collect_Bin_Sensor1\.py' }; if ($p) { exit 0 } else { exit 1 }"
if %ERRORLEVEL%==0 goto :sleep

if exist "Bin_Sensor1.stop" (
    echo %Date% %Time% - Bin_Sensor1 collector intentionally stopped, skipping restart.
    goto :sleep
)

echo %Date% %Time% - Bin_Sensor1 collector not running, restarting...

where py >nul 2>nul
if not errorlevel 1 (
    start "Bin_Sensor1 Collector" py -3 Collect_Bin_Sensor1.py
) else (
    start "Bin_Sensor1 Collector" python Collect_Bin_Sensor1.py
)

:sleep
timeout /t 60 >nul
goto :loop
