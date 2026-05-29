@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM Headless daily report runner for Windows Task Scheduler.
REM Usage: scheduled_daily_report.bat [project_id]
REM   project_id defaults to "default".
REM Output is appended to projects\<project_id>\logs\scheduled_YYYYMMDD.log
REM This file is created/updated by the web console scheduling panel,
REM but can also be registered manually via register / schtasks.
REM ============================================================

cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

set "PROJECT_ID=%~1"
if "%PROJECT_ID%"=="" set "PROJECT_ID=default"

set "LOG_DIR=%~dp0projects\%PROJECT_ID%\logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM Build a date stamp (YYYYMMDD) independent of locale.
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd"') do set "STAMP=%%i"
set "LOG_FILE=%LOG_DIR%\scheduled_%STAMP%.log"

REM Resolve a Python interpreter (prefer the project venv).
set "PY="
set "VENV_PY=%~dp0.venv\Scripts\python.exe"
if exist "%VENV_PY%" (
    set "PY=%VENV_PY%"
) else (
    where py >nul 2>nul && set "PY=py"
)
if "%PY%"=="" (
    where python >nul 2>nul && set "PY=python"
)
if "%PY%"=="" (
    echo [%date% %time%] FAILED: no Python interpreter found.>>"%LOG_FILE%"
    exit /b 1
)

echo ============================================================>>"%LOG_FILE%"
echo [%date% %time%] Start scheduled run, project=%PROJECT_ID%, py=%PY%>>"%LOG_FILE%"

"%PY%" scripts\run_real_daily_report.py --project "%PROJECT_ID%" >>"%LOG_FILE%" 2>&1
set "RC=%ERRORLEVEL%"

echo [%date% %time%] Finished with exit code %RC%.>>"%LOG_FILE%"
exit /b %RC%
