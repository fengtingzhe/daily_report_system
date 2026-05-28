@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

set "RAW_DIR=data\raw\unity"
set "RAW_CSV=%RAW_DIR%\unity_test_sample.csv"
set "AI_TEXT=data\tableau_datasource\ai_report_text.csv"

echo ============================================
echo Test Real Pipeline
echo ============================================
echo.

echo Creating sample Unity CSV...
if not exist "%RAW_DIR%" mkdir "%RAW_DIR%"
> "%RAW_CSV%" echo Date,Project Name,Revenue($),Ad-Revenue,Country / Region
>> "%RAW_CSV%" echo 2026-05-28,TestGame,123.45,67.89,US
>> "%RAW_CSV%" echo 2026-05-29,TestGame,234.56,88.12,BR
echo.

set "PY_CMD="

echo Resolving Python interpreter...
where py >nul 2>nul
if not errorlevel 1 (
    set "PY_CMD=py"
    echo Using Python launcher: py
    goto run_steps
)

where python >nul 2>nul
if not errorlevel 1 (
    set "PY_CMD=python"
    echo Using python command: python
    goto run_steps
)

set "UV_PYTHON=%USERPROFILE%\AppData\Roaming\uv\python\cpython-3.14.5-windows-x86_64-none\python.exe"
if exist "%UV_PYTHON%" (
    set "PY_CMD=%UV_PYTHON%"
    echo Using uv-managed Python 3.14.5.
    goto run_steps
)

set "UV_PYTHON=%USERPROFILE%\AppData\Roaming\uv\python\cpython-3.14-windows-x86_64-none\python.exe"
if exist "%UV_PYTHON%" (
    set "PY_CMD=%UV_PYTHON%"
    echo Using uv-managed Python 3.14.
    goto run_steps
)

echo FAILED: No working Python interpreter was found.
echo.
pause
exit /b 1

:run_steps
echo.
echo [1/5] Import raw CSV...
"%PY_CMD%" scripts\import_raw_csv.py 2>&1
if errorlevel 1 goto failed

echo.
echo [2/5] Build mart from clean...
"%PY_CMD%" scripts\build_mart_from_clean.py 2>&1
if errorlevel 1 goto failed

echo.
echo [3/5] Sync mart to Tableau datasource...
"%PY_CMD%" scripts\sync_mart_to_tableau_datasource.py 2>&1
if errorlevel 1 goto failed

echo.
echo [4/5] Generate AI context...
"%PY_CMD%" scripts\generate_ai_context.py 2>&1
if errorlevel 1 goto failed

echo.
echo [5/5] Generate AI report...
"%PY_CMD%" scripts\generate_ai_report.py 2>&1
if errorlevel 1 goto failed

echo.
if not exist "%AI_TEXT%" (
    echo FAILED: ai_report_text.csv was not found.
    echo.
    pause
    exit /b 1
)

echo ai_report_text.csv preview:
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-Content -LiteralPath '%CD%\%AI_TEXT%' -Encoding UTF8 -TotalCount 6"
if errorlevel 1 type "%AI_TEXT%"

echo.
echo SUCCESS: Test real pipeline completed.
echo.
pause
exit /b 0

:failed
echo.
echo FAILED: Test real pipeline failed.
echo.
pause
exit /b 1
