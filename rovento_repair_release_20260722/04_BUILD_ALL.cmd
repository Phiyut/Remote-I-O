@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title ROVENTO Repair WebApp - Build All
set "BUILD_NO_PAUSE=1"
call "02_BUILD_EXE.cmd"
if errorlevel 1 goto :fail
call "03_BUILD_INSTALLER.cmd"
if errorlevel 1 goto :fail
echo.
echo ============================================================
echo BUILD ALL COMPLETED
echo EXE: %CD%\dist\ROVENTO-Repair-WebApp\ROVENTO-Repair-WebApp.exe
echo SETUP: %CD%\installer_output\ROVENTO_Repair_WebApp_Setup.exe
echo ============================================================
pause
exit /b 0
:fail
echo.
echo BUILD ALL FAILED
pause
exit /b 1
