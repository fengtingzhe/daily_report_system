@echo off
chcp 65001 >nul
echo ============================================
echo   游戏运营日报自动化系统
echo ============================================

cd /d "%~dp0"

echo [%date% %time%] 开始执行日报流程...
echo.

REM 尝试多种方式找到 Python 解释器
set PYTHON_CMD=
for %%p in (python python3 py) do (
    where %%p >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON_CMD=%%p
        goto :found_python
    )
)

REM 尝试 uv 安装的 Python
if exist "%LOCALAPPDATA%\Programs\Python\Launcher\py.exe" (
    set PYTHON_CMD="%LOCALAPPDATA%\Programs\Python\Launcher\py.exe"
    goto :found_python
)

REM 最后尝试 AppData 下的 Python
for /d %%d in ("%USERPROFILE%\AppData\Roaming\uv\python\*") do (
    if exist "%%d\python.exe" (
        set PYTHON_CMD="%%d\python.exe"
        goto :found_python
    )
)

echo [错误] 找不到 Python 解释器，请确认 Python 已安装。
pause
exit /b 1

:found_python
echo 使用 Python: %PYTHON_CMD%
%PYTHON_CMD% scripts\run_all.py

if %errorlevel% == 0 (
    echo.
    echo [%date% %time%] 日报流程执行完成
) else (
    echo.
    echo [%date% %time%] 日报流程执行失败，请查看 logs 文件夹
)

echo.
pause
