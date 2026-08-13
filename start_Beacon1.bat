@echo off
cd /d "%~dp0"

echo Starting Beacon1 collector...
where py >nul 2>nul
if not errorlevel 1 (
    start "Beacon1 Collector" /B py -3 Collect_Beacon1.py
) else (
    start "Beacon1 Collector" /B python Collect_Beacon1.py
)
echo Beacon1 collector started.
