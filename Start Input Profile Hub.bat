@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [Input Hub] Creating virtual environment...
    py -3 -m venv .venv 2>nul
    if errorlevel 1 python -m venv .venv
)

if not exist ".venv\Scripts\python.exe" (
    echo [Input Hub] Python virtual environment could not be created.
    echo Install Python 3 and try again.
    pause
    exit /b 1
)

echo [Input Hub] Starting Personal Input Profile Hub...
".venv\Scripts\python.exe" -m tools.mouse_profile_hub.main

if errorlevel 1 (
    echo.
    echo [Input Hub] The application stopped with an error.
    pause
)

endlocal
