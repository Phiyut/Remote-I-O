@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title ROVENTO Repair WebApp - Build Installer

if not exist "dist\ROVENTO-Repair-WebApp\ROVENTO-Repair-WebApp.exe" (
  echo ERROR: Build EXE first.
  if not defined BUILD_NO_PAUSE pause
  exit /b 1
)
set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC (
  where winget >nul 2>&1
  if not errorlevel 1 winget install --id JRSoftware.InnoSetup -e --accept-source-agreements --accept-package-agreements
)
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC (
  echo ERROR: Inno Setup 6 was not found.
  if not defined BUILD_NO_PAUSE pause
  exit /b 1
)
if exist installer_output rmdir /s /q installer_output
mkdir installer_output
"%ISCC%" "ROVENTO_Repair_WebApp_Setup.iss"
if errorlevel 1 goto :fail
if not exist "installer_output\ROVENTO_Repair_WebApp_Setup.exe" goto :fail
echo.
echo BUILD INSTALLER SUCCESS
echo %CD%\installer_output\ROVENTO_Repair_WebApp_Setup.exe
if not defined BUILD_NO_PAUSE pause
exit /b 0
:fail
echo BUILD INSTALLER FAILED
if not defined BUILD_NO_PAUSE pause
exit /b 1
