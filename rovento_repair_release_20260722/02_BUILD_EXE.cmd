@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title ROVENTO Repair WebApp - Build EXE

set "VENV=%LOCALAPPDATA%\ROVENTORepairBuildPy311"
set "PYTHON_CMD="
py -3.11 --version >nul 2>&1 && set "PYTHON_CMD=py -3.11"
if not defined PYTHON_CMD python --version >nul 2>&1 && set "PYTHON_CMD=python"
if not defined PYTHON_CMD (
  echo ERROR: Python 3.11 x64 was not found.
  pause
  exit /b 1
)
if not exist "%VENV%\Scripts\python.exe" %PYTHON_CMD% -m venv "%VENV%"
call "%VENV%\Scripts\activate.bat"
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
if errorlevel 1 goto :fail
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
python -m PyInstaller --clean --noconfirm ROVENTO-Repair-WebApp.spec
if errorlevel 1 goto :fail
if not exist "dist\ROVENTO-Repair-WebApp\ROVENTO-Repair-WebApp.exe" goto :fail
copy /y "start.bat" "dist\ROVENTO-Repair-WebApp\start.bat" >nul
if errorlevel 1 goto :fail
echo.
echo BUILD EXE SUCCESS
echo %CD%\dist\ROVENTO-Repair-WebApp\ROVENTO-Repair-WebApp.exe
echo %CD%\dist\ROVENTO-Repair-WebApp\start.bat
if not defined BUILD_NO_PAUSE pause
exit /b 0
:fail
echo.
echo BUILD EXE FAILED
if not defined BUILD_NO_PAUSE pause
exit /b 1
