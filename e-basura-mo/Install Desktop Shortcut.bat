@echo off
cd /d "%~dp0"
echo Adding E-Basura Mo to your Desktop...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_desktop_shortcut.ps1"
echo.
echo Done. Double-click "E-Basura Mo" on your Desktop to start.
pause
