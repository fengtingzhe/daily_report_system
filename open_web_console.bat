@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

set "URL=http://127.0.0.1:8000"
set "HEALTH_URL=http://127.0.0.1:8000/api/projects"
set "SCRIPT=web_console\app.py"

echo ============================================
echo Daily Report Web Console
echo ============================================
echo URL: %URL%
echo Host: 127.0.0.1 only
echo.

echo Checking whether the web console is already running...
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r = Invoke-WebRequest -UseBasicParsing -Uri '%HEALTH_URL%' -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }"
if not errorlevel 1 goto open_browser

echo Web console is not running. Starting server...
echo.

set "VENV_PY=%~dp0.venv\Scripts\python.exe"
echo Trying venv Python: %VENV_PY%
if exist "%VENV_PY%" (
    start "Daily Report Web Console" "%VENV_PY%" "%SCRIPT%"
    goto wait_for_server
) else (
    echo SKIP: .venv not found. Run setup.bat to create it.
)
echo.

echo Trying Python launcher: py
where py >nul 2>nul
if errorlevel 1 (
    echo SKIP: py was not found in PATH.
) else (
    where py
    start "Daily Report Web Console" py "%SCRIPT%"
    goto wait_for_server
)
echo.

echo Trying python command: python
where python >nul 2>nul
if errorlevel 1 (
    echo SKIP: python was not found in PATH.
) else (
    where python
    start "Daily Report Web Console" python "%SCRIPT%"
    goto wait_for_server
)
echo.

set "UV_PYTHON=%USERPROFILE%\AppData\Roaming\uv\python\cpython-3.14.5-windows-x86_64-none\python.exe"
echo Trying uv-managed Python 3.14.5: %UV_PYTHON%
if exist "%UV_PYTHON%" (
    start "Daily Report Web Console" "%UV_PYTHON%" "%SCRIPT%"
    goto wait_for_server
) else (
    echo SKIP: uv-managed Python 3.14.5 was not found.
)
echo.

set "UV_PYTHON=%USERPROFILE%\AppData\Roaming\uv\python\cpython-3.14-windows-x86_64-none\python.exe"
echo Trying uv-managed Python 3.14: %UV_PYTHON%
if exist "%UV_PYTHON%" (
    start "Daily Report Web Console" "%UV_PYTHON%" "%SCRIPT%"
    goto wait_for_server
) else (
    echo SKIP: uv-managed Python 3.14 was not found.
)
echo.

echo FAILED: Could not find a usable Python interpreter.
echo Please install Python dependencies first:
echo   py -m pip install -r requirements.txt
echo.
pause
exit /b 1

:wait_for_server
echo Waiting for server to become ready...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ok = $false; for ($i = 0; $i -lt 15; $i++) { try { $r = Invoke-WebRequest -UseBasicParsing -Uri '%HEALTH_URL%' -TimeoutSec 2; if ($r.StatusCode -eq 200) { $ok = $true; break } } catch { }; Start-Sleep -Seconds 1 }; if ($ok) { exit 0 } else { exit 1 }"
if errorlevel 1 (
    echo FAILED: Server did not become ready.
    echo You can try running manually:
    echo   py web_console\app.py
    echo.
    pause
    exit /b 1
)

:open_browser
echo Opening browser...
start "" "%URL%"
echo.
echo SUCCESS: Web console opened.
echo.
pause
exit /b 0
