@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
set "BUILD_NO_PAUSE=1"
call 02_BUILD_EXE.cmd || goto failed
call 03_BUILD_INSTALLER.cmd || goto failed
echo.
echo ============================================================
echo BUILD COMPLETED
echo EXE: %CD%\dist\ROVENTO-Repair-WebApp\ROVENTO-Repair-Server.exe
echo SETUP: %CD%\installer_output\ROVENTO_Repair_WebApp_Setup.exe
echo ============================================================
pause
exit /b 0
:failed
echo BUILD ALL FAILED
pause
exit /b 1
