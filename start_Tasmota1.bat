@echo off
cd /d "%~dp0"

echo Starting Tasmota1 collector...
where py >nul 2>nul
if not errorlevel 1 (
    start "Tasmota1 Collector" /B py -3 Collect_Tasmota1.py
) else (
    start "Tasmota1 Collector" /B python Collect_Tasmota1.py
)
echo Tasmota1 collector started.
