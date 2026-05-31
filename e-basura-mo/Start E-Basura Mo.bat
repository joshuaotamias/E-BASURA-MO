@echo off
title E-Basura Mo
cd /d "%~dp0"

set "ARGS="
if /I "%~1"=="kiosk" set "ARGS=--kiosk"
if /I "%~1"=="--kiosk" set "ARGS=--kiosk"

if defined ARGS (
    echo Starting E-Basura Mo kiosk...
) else (
    echo Starting E-Basura Mo...
)

REM Windows Python launcher (recommended)
where py >nul 2>&1
if %ERRORLEVEL%==0 (
    py -3 "%~dp0main.py" %ARGS%
    if errorlevel 1 goto failed
    exit /b 0
)

where pythonw >nul 2>&1
if %ERRORLEVEL%==0 (
    pythonw "%~dp0main.py" %ARGS%
    if errorlevel 1 goto failed
    exit /b 0
)

where python >nul 2>&1
if %ERRORLEVEL%==0 (
    python "%~dp0main.py" %ARGS%
    if errorlevel 1 goto failed
    exit /b 0
)

echo.
echo  Python was not found.
echo  Install Python 3.10+ from https://www.python.org/downloads/
echo  Check "Add python.exe to PATH" during install.
echo.
pause
exit /b 1

:failed
echo.
echo  E-Basura Mo stopped because of an error.
echo  Try opening Command Prompt in this folder and run:  py -3 main.py
echo.
pause
exit /b 1
