@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title ROVENTO Repair WebApp

set "APP_HOST=0.0.0.0"
set "APP_PORT=5058"
set "OPEN_BROWSER=1"

rem Installed or built EXE in the same folder
if exist "%~dp0ROVENTO-Repair-WebApp.exe" (
    start "" "%~dp0ROVENTO-Repair-WebApp.exe"
    exit /b 0
)

rem EXE created by PyInstaller from the project root
if exist "%~dp0dist\ROVENTO-Repair-WebApp\ROVENTO-Repair-WebApp.exe" (
    start "" "%~dp0dist\ROVENTO-Repair-WebApp\ROVENTO-Repair-WebApp.exe"
    exit /b 0
)

rem Source mode when EXE has not been built yet
if exist "%~dp001_RUN_SOURCE.cmd" (
    call "%~dp001_RUN_SOURCE.cmd"
    exit /b %errorlevel%
)

echo.
echo ERROR: ROVENTO Repair WebApp files were not found.
echo.
echo Expected one of these files:
echo   ROVENTO-Repair-WebApp.exe
echo   dist\ROVENTO-Repair-WebApp\ROVENTO-Repair-WebApp.exe
echo   01_RUN_SOURCE.cmd
echo.
pause
exit /b 1
