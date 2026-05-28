@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ============================================
echo Daily Report System
echo ============================================
echo Starting pipeline...
echo.

REM Try python first
python scripts\run_all.py
if %errorlevel% equ 0 goto success

REM Try py launcher
echo python not found, trying py...
py scripts\run_all.py
if %errorlevel% equ 0 goto success

REM Fallback: try uv-managed Python (3.14.5)
echo py not found, trying uv Python...
set "UV_PYTHON=%USERPROFILE%\AppData\Roaming\uv\python\cpython-3.14.5-windows-x86_64-none\python.exe"
if exist "%UV_PYTHON%" (
    "%UV_PYTHON%" scripts\run_all.py
    if !errorlevel! equ 0 goto success
)

REM Fallback: try uv-managed Python (3.14)
set "UV_PYTHON=%USERPROFILE%\AppData\Roaming\uv\python\cpython-3.14-windows-x86_64-none\python.exe"
if exist "%UV_PYTHON%" (
    "%UV_PYTHON%" scripts\run_all.py
    if !errorlevel! equ 0 goto success
)

echo.
echo FAILED: Cannot find Python interpreter.
echo Please install Python or set PATH correctly.
pause
exit /b 1

:success
echo.
echo SUCCESS: Daily report pipeline completed.
pause
exit /b 0
