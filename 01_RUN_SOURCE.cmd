@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
set "VENV=%LOCALAPPDATA%\ROVENTORepairBuildPy311"
call :find_python || goto failed
if not exist "%VENV%\Scripts\python.exe" %PY% -m venv "%VENV%" || goto failed
call "%VENV%\Scripts\activate.bat" || goto failed
python -m pip install --upgrade pip setuptools wheel || goto failed
python -m pip install -r requirements.txt || goto failed
python app.py
exit /b %errorlevel%
:find_python
set "PY="
py -3.11 --version >nul 2>&1 && set "PY=py -3.11"
if not defined PY python --version >nul 2>&1 && set "PY=python"
if not defined PY echo Python 3.11 x64 was not found.&exit /b 1
exit /b 0
:failed
echo.
echo RUN SOURCE FAILED
pause
exit /b 1
