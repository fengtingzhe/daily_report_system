@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ============================================
echo Daily Report System - Web Console
echo ============================================
echo Starting web console...
echo.
echo Open: http://127.0.0.1:8000
echo Press Ctrl+C to stop.
echo.

REM Try uv-managed Python first (all project deps installed here).
set "UV_PYTHON=%USERPROFILE%\AppData\Roaming\uv\python\cpython-3.14.5-windows-x86_64-none\python.exe"
if exist "%UV_PYTHON%" (
    echo Using uv Python 3.14.5...
    "%UV_PYTHON%" web_console\app.py
    goto done
)

REM Fallback: try uv-managed Python 3.14 symlink.
set "UV_PYTHON=%USERPROFILE%\AppData\Roaming\uv\python\cpython-3.14-windows-x86_64-none\python.exe"
if exist "%UV_PYTHON%" (
    echo Using uv Python 3.14...
    "%UV_PYTHON%" web_console\app.py
    goto done
)

REM Fallback: try py launcher.
where py >nul 2>nul
if not errorlevel 1 (
    echo Using py launcher...
    py web_console\app.py
    goto done
)

REM Fallback: try python command.
where python >nul 2>nul
if not errorlevel 1 (
    echo Using python...
    python web_console\app.py
    goto done
)

echo.
echo FAILED: Cannot find a working Python interpreter.
echo Options:
echo   1. Install Python from https://python.org
echo   2. Or use uv: uv python install 3.14
echo.
pause
exit /b 1

:done
echo.
echo Web console stopped.
pause
exit /b 0
