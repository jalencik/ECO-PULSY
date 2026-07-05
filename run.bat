@echo off
title EcoPulse - setup and run
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found on this computer.
    echo Install it from https://www.python.org/downloads/
    echo IMPORTANT: tick "Add python.exe to PATH" during installation,
    echo then double-click this file again.
    pause
    exit /b 1
)

if not exist venv\Scripts\activate.bat (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat
echo Installing dependencies (first run can take a minute)...
pip install -q -r requirements.txt

echo.
echo Starting EcoPulse at http://127.0.0.1:5000
echo Keep this window open while you use the app. Press Ctrl+C to stop.
echo.
start "" http://127.0.0.1:5000
python -m flask --app app run
pause
