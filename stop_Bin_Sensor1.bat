@echo off
cd /d "%~dp0"

echo. > "Bin_Sensor1.stop"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$p = Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -or $_.Name -eq 'py.exe' } | Where-Object { $_.CommandLine -match 'Collect_Bin_Sensor1\\.py' }; if ($p) { $p | ForEach-Object { Write-Host ('Stopping PID ' + $_.ProcessId); Stop-Process -Id $_.ProcessId -Force } } else { Write-Host 'No Bin_Sensor1 collector running.' }"

pause
