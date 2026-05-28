@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ============================================
echo Daily Report System
echo ============================================
echo Starting pipeline...
echo.

REM Try py launcher first.
echo Trying Python launcher: py
where py >nul 2>nul
if errorlevel 1 (
    echo SKIP: py was not found in PATH.
) else (
    where py
    py scripts\run_all.py 2>&1
    set "LAST_EXIT=!errorlevel!"
    if "!LAST_EXIT!"=="0" goto success
    echo WARN: py failed with exit code !LAST_EXIT!.
)
echo.

REM Try python command second.
echo Trying python command: python
where python >nul 2>nul
if errorlevel 1 (
    echo SKIP: python was not found in PATH.
) else (
    where python
    python scripts\run_all.py 2>&1
    set "LAST_EXIT=!errorlevel!"
    if "!LAST_EXIT!"=="0" goto success
    echo WARN: python failed with exit code !LAST_EXIT!.
)
echo.

REM Try uv-managed Python after py and python fail.
set "UV_PYTHON=%USERPROFILE%\AppData\Roaming\uv\python\cpython-3.14.5-windows-x86_64-none\python.exe"
echo Trying uv-managed Python: %UV_PYTHON%
if exist "%UV_PYTHON%" (
    "%UV_PYTHON%" scripts\run_all.py 2>&1
    set "LAST_EXIT=!errorlevel!"
    if "!LAST_EXIT!"=="0" goto success
    echo WARN: uv-managed Python failed with exit code !LAST_EXIT!.
) else (
    echo SKIP: uv-managed Python was not found at this path.
)
echo.

REM Try uv-managed Python 3.14 alias.
set "UV_PYTHON=%USERPROFILE%\AppData\Roaming\uv\python\cpython-3.14-windows-x86_64-none\python.exe"
echo Trying uv-managed Python: %UV_PYTHON%
if exist "%UV_PYTHON%" (
    "%UV_PYTHON%" scripts\run_all.py 2>&1
    set "LAST_EXIT=!errorlevel!"
    if "!LAST_EXIT!"=="0" goto success
    echo WARN: uv-managed Python failed with exit code !LAST_EXIT!.
) else (
    echo SKIP: uv-managed Python was not found at this path.
)

echo.
echo FAILED: Cannot find a working Python interpreter.
echo Options:
echo   1. Install Python from https://python.org
echo   2. Or use uv: uv python install 3.14
echo.
exit /b 1

:success
echo.
echo SUCCESS: Daily report pipeline completed.
exit /b 0
