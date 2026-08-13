@echo off
cd /d "%~dp0"

echo Starting Bin_Sensor1 collector...
where py >nul 2>nul
if not errorlevel 1 (
    start "Bin_Sensor1 Collector" /B py -3 Collect_Bin_Sensor1.py
) else (
    start "Bin_Sensor1 Collector" /B python Collect_Bin_Sensor1.py
)
echo Bin_Sensor1 collector started.
