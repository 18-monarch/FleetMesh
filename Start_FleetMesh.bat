@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if %errorlevel%==0 (
    py -3 start.py --open
) else (
    where python >nul 2>&1
    if errorlevel 1 (
        echo Python was not found. Install Python 3.10 or newer and enable Add Python to PATH.
        pause
        exit /b 1
    )
    python start.py --open
)
if errorlevel 1 pause
endlocal
