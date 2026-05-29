@echo off
setlocal
cd /d "%~dp0"

REM ============================================================
REM Create or delete the daily report Windows scheduled task.
REM Writing to Task Scheduler needs admin rights, so the web
REM console launches this file elevated (UAC). Quoting for the
REM schtasks /tr argument is kept here, where it is reliable.
REM
REM Usage:
REM   manage_schedule.bat create <project_id> <HH:MM>
REM   manage_schedule.bat delete <project_id>
REM ============================================================

set "ACTION=%~1"
set "PROJECT=%~2"
set "RUNTIME=%~3"
if "%PROJECT%"=="" set "PROJECT=default"
set "TASK=DailyReportSystem_%PROJECT%"

if /i "%ACTION%"=="create" (
    schtasks /create /tn "%TASK%" /tr "\"%~dp0scheduled_daily_report.bat\" %PROJECT%" /sc daily /st %RUNTIME% /f
    exit /b %ERRORLEVEL%
)
if /i "%ACTION%"=="delete" (
    schtasks /delete /tn "%TASK%" /f
    exit /b %ERRORLEVEL%
)

echo Unknown action: %ACTION%
exit /b 2
