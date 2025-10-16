@echo off
chcp 65001 >nul
echo ================================================
echo   SmartSupport - AI Technical Support System
echo ================================================
echo.

cd /d "%~dp0"

REM Check Python installation
echo [1/3] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found with 'python' command
    echo Trying 'py' command...
    py --version >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Python is not installed or not in PATH
        echo.
        echo Please install Python from https://www.python.org/
        echo Make sure to check "Add Python to PATH" during installation
        pause
        exit /b 1
    ) else (
        set PYTHON_CMD=py
        echo Found Python: py
    )
) else (
    set PYTHON_CMD=python
    echo Found Python: python
)

echo.
echo [2/3] Installing dependencies...
echo This may take 1-2 minutes on first run...
%PYTHON_CMD% -m pip install -r requirements.txt
if errorlevel 1 (
    echo WARNING: Some packages may not be installed
    echo Continuing anyway...
)
echo Dependencies installed!

echo.
echo [3/3] Starting web server...
echo ================================================
echo   Open in browser: http://localhost:5000
echo ================================================
echo.

%PYTHON_CMD% app.py

pause

