@echo off
setlocal EnableExtensions

cd /d "%~dp0"

set "PYTHON_CMD="

where py >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=py"

if not defined PYTHON_CMD (
    where python >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    echo [Error] Python was not found on this computer.
    echo.
    echo Please install Python 3.10 or newer first.
    echo Download: https://www.python.org/downloads/windows/
    start "" "https://www.python.org/downloads/windows/"
    pause
    exit /b 1
)

%PYTHON_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 (
    echo [Error] Python version is too old.
    echo Please install Python 3.10 or newer.
    start "" "https://www.python.org/downloads/windows/"
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [First run] Creating virtual environment...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo Failed to create the virtual environment.
        pause
        exit /b 1
    )
)

echo [Startup] Installing or checking dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)

start "" "http://127.0.0.1:8017"
echo [Startup] Launching WebUI. Closing this window will stop the server.
".venv\Scripts\python.exe" -m uvicorn app:app --reload --host 127.0.0.1 --port 8017 --no-access-log

pause
