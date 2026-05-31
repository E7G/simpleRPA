@echo off
chcp 65001 >nul
cd /d "%~dp0\.."
echo ============================================
echo   SimpleRPA 重置每日定时执行标记（调试用）
echo ============================================
echo.

where pixi >nul 2>nul
if %errorlevel%==0 (
    pixi run python reset_daily.py
) else (
    python reset_daily.py
)

echo.
pause
