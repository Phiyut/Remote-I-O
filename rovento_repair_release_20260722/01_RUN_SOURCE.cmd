@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title ROVENTO Repair WebApp - Run Source

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
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 goto :fail
set "APP_HOST=0.0.0.0"
set "APP_PORT=5058"
set "OPEN_BROWSER=1"
python app.py
exit /b %errorlevel%
:fail
echo Installation of Python packages failed.
pause
exit /b 1
