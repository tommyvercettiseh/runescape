@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [Stress Lab] Creating virtual environment...
    py -3 -m venv .venv 2>nul
    if errorlevel 1 python -m venv .venv
)

if not exist ".venv\Scripts\python.exe" (
    echo [Stress Lab] Python virtual environment could not be created.
    echo Install Python 3.11 or newer and try again.
    pause
    exit /b 1
)

if not exist "data\mouse_profile_hub\logs" mkdir "data\mouse_profile_hub\logs"
set "LOG=data\mouse_profile_hub\logs\stress_lab_launcher.log"

echo [%date% %time%] Starting Profile Stress Lab>>"%LOG%"
".venv\Scripts\python.exe" -c "import tkinter; import tools.mouse_profile_hub.stress_lab" >>"%LOG%" 2>&1
if errorlevel 1 (
    echo [Stress Lab] Preflight failed. See %LOG%
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m tools.mouse_profile_hub.stress_lab >>"%LOG%" 2>&1
if errorlevel 1 (
    echo [Stress Lab] Application stopped with an error. See %LOG%
    pause
)

endlocal
