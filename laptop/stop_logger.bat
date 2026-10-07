@echo off
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\VisaSlotLogger.cmd" >nul 2>nul
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"name='pythonw.exe'\" | Where-Object { $_.CommandLine -like '*run_logger.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
echo Logger stopped and removed from startup. Run setup.bat to turn it back on.
pause
