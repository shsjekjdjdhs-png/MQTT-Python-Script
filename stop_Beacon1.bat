@echo off
cd /d "%~dp0"

echo. > "Beacon1.stop"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$p = Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -or $_.Name -eq 'py.exe' } | Where-Object { $_.CommandLine -match 'Collect_Beacon1\\.py' }; if ($p) { $p | ForEach-Object { Write-Host ('Stopping PID ' + $_.ProcessId); Stop-Process -Id $_.ProcessId -Force } } else { Write-Host 'No Beacon1 collector running.' }"

pause
