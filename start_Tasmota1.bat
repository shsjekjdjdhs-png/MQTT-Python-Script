@echo off
cd /d "%~dp0"
title Tasmota1 Watchdog

if exist "Tasmota1.stop" del "Tasmota1.stop"

echo Starting Tasmota1 watchdog...

:loop
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p = Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'python.exe' -or $_.Name -eq 'py.exe') -and $_.CommandLine -match 'Collect_Tasmota1\.py' }; if ($p) { exit 0 } else { exit 1 }"
if %ERRORLEVEL%==0 goto :sleep

if exist "Tasmota1.stop" (
    echo %Date% %Time% - Tasmota1 collector intentionally stopped, skipping restart.
    goto :sleep
)

echo %Date% %Time% - Tasmota1 collector not running, restarting...

where py >nul 2>nul
if not errorlevel 1 (
    start "Tasmota1 Collector" py -3 Collect_Tasmota1.py
) else (
    start "Tasmota1 Collector" python Collect_Tasmota1.py
)

:sleep
timeout /t 60 >nul
goto :loop
