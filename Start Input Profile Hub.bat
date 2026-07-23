@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "LOG_DIR=data\mouse_profile_hub\logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "BOOT_LOG=%LOG_DIR%\launcher.log"

echo.>>"%BOOT_LOG%"
echo [%date% %time%] Starting Personal Input Profile Hub>>"%BOOT_LOG%"

where py >nul 2>&1
if errorlevel 1 (
    where python >nul 2>&1
    if errorlevel 1 (
        echo [Input Hub] Python 3 is not installed or not available in PATH.
        echo Install Python 3.11 or newer and enable "Add Python to PATH".
        echo Python not found>>"%BOOT_LOG%"
        pause
        exit /b 1
    )
)

if not exist ".venv\Scripts\python.exe" (
    echo [Input Hub] Creating virtual environment...
    py -3 -m venv .venv >>"%BOOT_LOG%" 2>&1
    if errorlevel 1 python -m venv .venv >>"%BOOT_LOG%" 2>&1
)

if not exist ".venv\Scripts\python.exe" (
    echo [Input Hub] Virtual environment could not be created.
    echo See %BOOT_LOG%
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -c "import tkinter; import tools.mouse_profile_hub.runner" >>"%BOOT_LOG%" 2>&1
if errorlevel 1 (
    echo [Input Hub] Startup check failed.
    echo Your Python installation may be missing Tkinter, or a project file has an error.
    echo See %BOOT_LOG%
    pause
    exit /b 1
)

echo [Input Hub] Starting...
".venv\Scripts\python.exe" -m tools.mouse_profile_hub.runner >>"%BOOT_LOG%" 2>&1
set "EXIT_CODE=%errorlevel%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo [Input Hub] The application stopped with error code %EXIT_CODE%.
    echo See %BOOT_LOG%
    pause
)

endlocal & exit /b %EXIT_CODE%
