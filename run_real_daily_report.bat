@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

set "SCRIPT=scripts\run_real_daily_report.py"

echo ============================================
echo Real Daily Report Pipeline
echo ============================================
echo.

echo Trying Python launcher: py
where py >nul 2>nul
if errorlevel 1 (
    echo SKIP: py was not found in PATH.
) else (
    where py
    py "%SCRIPT%" 2>&1
    set "LAST_EXIT=!errorlevel!"
    if "!LAST_EXIT!"=="0" goto success
    echo WARN: py failed with exit code !LAST_EXIT!.
)
echo.

echo Trying python command: python
where python >nul 2>nul
if errorlevel 1 (
    echo SKIP: python was not found in PATH.
) else (
    where python
    python "%SCRIPT%" 2>&1
    set "LAST_EXIT=!errorlevel!"
    if "!LAST_EXIT!"=="0" goto success
    echo WARN: python failed with exit code !LAST_EXIT!.
)
echo.

set "UV_PYTHON=%USERPROFILE%\AppData\Roaming\uv\python\cpython-3.14.5-windows-x86_64-none\python.exe"
echo Trying uv-managed Python 3.14.5: %UV_PYTHON%
if exist "%UV_PYTHON%" (
    "%UV_PYTHON%" "%SCRIPT%" 2>&1
    set "LAST_EXIT=!errorlevel!"
    if "!LAST_EXIT!"=="0" goto success
    echo WARN: uv-managed Python 3.14.5 failed with exit code !LAST_EXIT!.
) else (
    echo SKIP: uv-managed Python 3.14.5 was not found.
)
echo.

set "UV_PYTHON=%USERPROFILE%\AppData\Roaming\uv\python\cpython-3.14-windows-x86_64-none\python.exe"
echo Trying uv-managed Python 3.14: %UV_PYTHON%
if exist "%UV_PYTHON%" (
    "%UV_PYTHON%" "%SCRIPT%" 2>&1
    set "LAST_EXIT=!errorlevel!"
    if "!LAST_EXIT!"=="0" goto success
    echo WARN: uv-managed Python 3.14 failed with exit code !LAST_EXIT!.
) else (
    echo SKIP: uv-managed Python 3.14 was not found.
)

echo.
echo FAILED: Real daily report pipeline failed with all Python interpreters.
echo.
pause
exit /b 1

:success
echo.
echo SUCCESS: Real daily report pipeline completed.
echo.
pause
exit /b 0
