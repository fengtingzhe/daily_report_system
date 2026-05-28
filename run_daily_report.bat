@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ============================================
echo Daily Report System
echo ============================================
echo Starting pipeline...
echo.

REM Try uv-managed Python first (fast, avoids Windows App Store stub)
set "UV_PYTHON=%USERPROFILE%\AppData\Roaming\uv\python\cpython-3.14.5-windows-x86_64-none\python.exe"
if exist "%UV_PYTHON%" (
    echo Using uv Python 3.14.5...
    "%UV_PYTHON%" scripts\run_all.py
    if !errorlevel! equ 0 goto success
)

REM Fallback: try uv-managed Python 3.14 (symlink to latest 3.14.x)
set "UV_PYTHON=%USERPROFILE%\AppData\Roaming\uv\python\cpython-3.14-windows-x86_64-none\python.exe"
if exist "%UV_PYTHON%" (
    echo Using uv Python 3.14...
    "%UV_PYTHON%" scripts\run_all.py
    if !errorlevel! equ 0 goto success
)

REM Fallback: try py launcher
echo Trying py launcher...
py scripts\run_all.py
if !errorlevel! equ 0 goto success

REM Fallback: try python (may be Windows App Store stub on some systems)
echo Trying python...
python scripts\run_all.py
if !errorlevel! equ 0 goto success

echo.
echo FAILED: Cannot find a working Python interpreter.
echo Options:
echo   1. Install Python from https://python.org
echo   2. Or use uv: uv python install 3.14
echo.
pause
exit /b 1

:success
echo.
echo SUCCESS: Daily report pipeline completed.
pause
exit /b 0
