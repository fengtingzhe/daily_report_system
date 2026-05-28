@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

set "RAW_DIR=data\raw\unity"
set "CLEAN_DIR=data\clean\unity"
set "RAW_CSV=%RAW_DIR%\unity_test_sample.csv"
set "CLEAN_CSV=%CLEAN_DIR%\unity_test_sample.csv"
set "SCRIPT=scripts\import_raw_csv.py"

echo ============================================
echo Test Raw CSV Import
echo ============================================
echo.

echo Creating sample Unity CSV...
if not exist "%RAW_DIR%" mkdir "%RAW_DIR%"
if not exist "%CLEAN_DIR%" mkdir "%CLEAN_DIR%"

> "%RAW_CSV%" echo Date,Project Name,Revenue($),Ad-Revenue,Country / Region
>> "%RAW_CSV%" echo 2026-05-28,TestGame,123.45,67.89,US
>> "%RAW_CSV%" echo 2026-05-29,TestGame,234.56,88.12,BR

if exist "%CLEAN_CSV%" del /q "%CLEAN_CSV%"

echo Sample CSV:
type "%RAW_CSV%"
echo.
echo.
echo Running import_raw_csv.py...
echo Note: Existing CSV files under data\raw may also be imported.
echo.

set "UV_PYTHON=%USERPROFILE%\AppData\Roaming\uv\python\cpython-3.14.5-windows-x86_64-none\python.exe"
echo Trying uv-managed Python 3.14.5: %UV_PYTHON%
if exist "%UV_PYTHON%" (
    "%UV_PYTHON%" "%SCRIPT%" 2>&1
    set "LAST_EXIT=!errorlevel!"
    if "!LAST_EXIT!"=="0" goto import_ok
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
    if "!LAST_EXIT!"=="0" goto import_ok
    echo WARN: uv-managed Python 3.14 failed with exit code !LAST_EXIT!.
) else (
    echo SKIP: uv-managed Python 3.14 was not found.
)
echo.

echo Trying Python launcher: py
where py >nul 2>nul
if errorlevel 1 (
    echo SKIP: py was not found in PATH.
) else (
    where py
    py "%SCRIPT%" 2>&1
    set "LAST_EXIT=!errorlevel!"
    if "!LAST_EXIT!"=="0" goto import_ok
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
    if "!LAST_EXIT!"=="0" goto import_ok
    echo WARN: python failed with exit code !LAST_EXIT!.
)
echo.

echo FAILED: import_raw_csv.py could not run with any Python interpreter.
echo.
pause
exit /b 1

:import_ok
echo.
if not exist "%CLEAN_CSV%" (
    echo FAILED: Clean CSV was not created: %CLEAN_CSV%
    echo.
    pause
    exit /b 1
)

echo ============================================
echo Clean CSV Preview
echo ============================================
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-Content -LiteralPath '%CD%\%CLEAN_CSV%' -Encoding UTF8"
if errorlevel 1 type "%CLEAN_CSV%"
echo.
echo.
echo Test completed.
echo.
pause
exit /b 0
