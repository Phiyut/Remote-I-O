@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title ROVENTO Repair WebApp - Build Installer
set "EXE=%CD%\dist\ROVENTO-Repair-WebApp\ROVENTO-Repair-Server.exe"
if not exist "%EXE%" echo Build EXE first.&goto failed
set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC (
  where winget >nul 2>&1 && winget install --id JRSoftware.InnoSetup -e --accept-source-agreements --accept-package-agreements
  if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
)
if not defined ISCC echo Inno Setup 6 was not found.&goto failed
if exist installer_output rmdir /s /q installer_output
mkdir installer_output
"%ISCC%" RepairWebApp_Setup.iss || goto failed
echo.
echo BUILD INSTALLER SUCCESS
echo %CD%\installer_output\ROVENTO_Repair_WebApp_Setup.exe
if not defined BUILD_NO_PAUSE pause
exit /b 0
:failed
echo.
echo BUILD INSTALLER FAILED
if not defined BUILD_NO_PAUSE pause
exit /b 1
