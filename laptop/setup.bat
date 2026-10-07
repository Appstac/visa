@echo off
setlocal
title Visa Slot Logger - setup
cd /d "%~dp0\.."
echo.
echo === Visa Slot Logger setup ===
echo Repo folder: %CD%
echo.

where git >nul 2>nul || (echo [X] Git is not installed. Get it from https://git-scm.com/download/win then run this again. & pause & exit /b 1)

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (where python >nul 2>nul && set "PY=python")
if not defined PY (echo [X] Python is not installed. Get it from https://www.python.org/downloads/ ^(tick "Add python.exe to PATH"^) then run this again. & pause & exit /b 1)

for /f "delims=" %%i in ('%PY% -c "import sys,os;print(os.path.join(os.path.dirname(sys.executable),'pythonw.exe'))"') do set "PYW=%%i"
if not exist "%PYW%" (echo [X] Could not find pythonw.exe & pause & exit /b 1)
echo [OK] Git and Python found.

git config user.name >nul 2>nul || git config user.name "slot-logger"
git config user.email >nul 2>nul || git config user.email "slot-logger@users.noreply.github.com"

echo.
echo Running a first check and pushing to GitHub...
echo If a GitHub sign-in window opens, sign in as Appstac and approve it.
echo.
%PY% laptop\run_logger.py --once
echo.
echo Last log lines:
powershell -NoProfile -Command "Get-Content 'laptop\logger.log' -Tail 4"
echo.

echo Adding the logger to Windows startup...
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
> "%STARTUP%\VisaSlotLogger.cmd" echo @start "" "%PYW%" "%CD%\laptop\run_logger.py"
if not exist "%STARTUP%\VisaSlotLogger.cmd" (echo [X] Could not add to startup. & pause & exit /b 1)
start "" "%PYW%" "%CD%\laptop\run_logger.py"
echo [OK] Logger is running in the background and will start again at every sign-in.

echo.
echo Keeping the laptop awake while plugged in...
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
echo [OK] Sleep and hibernate disabled on AC power.

echo.
echo === Done ===
echo Dashboard: https://visa-slot-tracker.vercel.app
echo Log file:  %CD%\laptop\logger.log
echo.
echo Still to do by hand: Settings ^> System ^> Power ^> Lid close action ^> "Do nothing" (plugged in),
echo and make sure Windows signs in automatically after a restart or update.
echo.
pause
