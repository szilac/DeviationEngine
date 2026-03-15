@echo off
cd /d "%~dp0"

where py >nul 2>&1
if %errorlevel% equ 0 (
    py -3 start.py
    goto :end
)

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found. Install from https://python.org
    pause
    exit /b 1
)

python start.py

:end
if %errorlevel% neq 0 (
    echo.
    echo Something went wrong. See the error above.
    pause
)
