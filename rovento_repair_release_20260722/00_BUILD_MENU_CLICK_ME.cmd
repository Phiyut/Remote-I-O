@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title ROVENTO Repair WebApp - Build Menu
:menu
cls
echo ============================================================
echo ROVENTO REPAIR WEBAPP - BUILD MENU
echo ============================================================
echo 1. Run Source
echo 2. Build EXE
echo 3. Build Installer
echo 4. Build EXE + Installer
echo 5. Open Output Folder
echo 0. Exit
echo.
set "choice="
set /p "choice=Select: "
if "%choice%"=="1" call "01_RUN_SOURCE.cmd" & goto menu
if "%choice%"=="2" call "02_BUILD_EXE.cmd" & goto menu
if "%choice%"=="3" call "03_BUILD_INSTALLER.cmd" & goto menu
if "%choice%"=="4" call "04_BUILD_ALL.cmd" & goto menu
if "%choice%"=="5" if exist installer_output (start "" installer_output) else if exist dist (start "" dist) else (echo No output yet.&pause) & goto menu
if "%choice%"=="0" exit /b 0
goto menu
