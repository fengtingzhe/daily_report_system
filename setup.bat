@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul

echo ============================================
echo Daily Report System - 一键安装
echo ============================================
echo.

REM 找一个可用的 Python 来创建虚拟环境
set "BOOT="
where py >nul 2>nul && set "BOOT=py"
if not defined BOOT (
    where python >nul 2>nul && set "BOOT=python"
)
if not defined BOOT (
    echo FAILED: 未找到 Python。请先安装 Python 3.10+ 并加入 PATH。
    echo 下载: https://www.python.org/downloads/windows/
    echo.
    pause
    exit /b 1
)

echo 使用 %BOOT% 创建虚拟环境 .venv ...
%BOOT% -m venv .venv
if errorlevel 1 (
    echo FAILED: 创建虚拟环境失败。
    pause
    exit /b 1
)

echo.
echo 升级 pip ...
".venv\Scripts\python.exe" -m pip install --upgrade pip

echo.
echo 安装依赖 (requirements.txt) ...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo FAILED: 依赖安装失败，请检查网络后重试。
    pause
    exit /b 1
)

echo.
echo ============================================
echo SUCCESS: 安装完成。
echo 现在双击 open_web_console.bat 即可启动控制台。
echo ============================================
echo.
pause
exit /b 0
