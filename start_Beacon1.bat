@echo off
cd /d "%~dp0"
title Beacon1 Watchdog

if exist "Beacon1.stop" del "Beacon1.stop"

echo Starting Beacon1 watchdog...

:loop
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p = Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'python.exe' -or $_.Name -eq 'py.exe') -and $_.CommandLine -match 'Collect_Beacon1\.py' }; if ($p) { exit 0 } else { exit 1 }"
if %ERRORLEVEL%==0 goto :sleep

if exist "Beacon1.stop" (
    echo %Date% %Time% - Beacon1 collector intentionally stopped, skipping restart.
    goto :sleep
)

echo %Date% %Time% - Beacon1 collector not running, restarting...

where py >nul 2>nul
if not errorlevel 1 (
    start "Beacon1 Collector" py -3 Collect_Beacon1.py
) else (
    start "Beacon1 Collector" python Collect_Beacon1.py
)

:sleep
timeout /t 60 >nul
goto :loop
