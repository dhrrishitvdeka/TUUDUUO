@echo off
title TUUDUUO
cd /d "%~dp0"

echo TUUDUUO - starting local server...
echo.

where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not found in your system PATH!
    echo Please install Python 3 or add it to PATH.
    pause
    exit /b 1
)

start "" python app.py
exit
