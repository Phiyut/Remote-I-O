@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title ROVENTO Repair WebApp - Build EXE
set "VENV=%LOCALAPPDATA%\ROVENTORepairBuildPy311"
set "OUT=%CD%\dist\ROVENTO-Repair-WebApp\ROVENTO-Repair-Server.exe"
call :find_python || goto failed
if not exist "%VENV%\Scripts\python.exe" %PY% -m venv "%VENV%" || goto failed
call "%VENV%\Scripts\activate.bat" || goto failed
python -m pip install --upgrade pip setuptools wheel || goto failed
python -m pip install -r requirements-build.txt || goto failed
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
python -m PyInstaller --clean --noconfirm RepairWebApp.spec || goto failed
if not exist "%OUT%" goto failed
echo.
echo BUILD EXE SUCCESS
echo %OUT%
if not defined BUILD_NO_PAUSE pause
exit /b 0
:find_python
set "PY="
py -3.11 --version >nul 2>&1 && set "PY=py -3.11"
if not defined PY python --version >nul 2>&1 && set "PY=python"
if not defined PY echo Python 3.11 x64 was not found.&exit /b 1
exit /b 0
:failed
echo.
echo BUILD EXE FAILED
if not defined BUILD_NO_PAUSE pause
exit /b 1
