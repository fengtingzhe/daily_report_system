@echo off
chcp 65001 >nul
echo ============================================
echo   游戏运营日报自动化系统
echo ============================================

cd /d "%~dp0"

echo [%date% %time%] 开始执行日报流程...
echo.

python scripts\run_all.py

if %errorlevel% == 0 (
    echo.
    echo [%date% %time%] 日报流程执行完成
) else (
    echo.
    echo [%date% %time%] 日报流程执行失败，请查看 logs 文件夹
)

echo.
pause
