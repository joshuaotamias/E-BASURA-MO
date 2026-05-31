@echo off
title Clear E-Basura Mo Database
cd /d "%~dp0"

echo.
echo  WARNING: This deletes ALL records, photos, and saved reports.
echo  Demo login accounts will be created again after reset.
echo.
set /p OK=Type YES to continue: 
if /I not "%OK%"=="YES" (
    echo Cancelled.
    pause
    exit /b 0
)

echo.
where py >nul 2>&1
if %ERRORLEVEL%==0 (
    py -3 -c "from database import Database; Database.clear_all_data(); print('Done. Demo logins: admin/admin123, staff/staff123, captain/captain123')"
    goto done
)
where python >nul 2>&1
if %ERRORLEVEL%==0 (
    python -c "from database import Database; Database.clear_all_data(); print('Done. Demo logins: admin/admin123, staff/staff123, captain/captain123')"
    goto done
)

echo Python not found.
pause
exit /b 1

:done
echo.
pause
