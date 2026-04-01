@echo off
chcp 65001 >nul
setlocal

echo ==============================================
echo           My_Agent 一键启动脚本
echo ==============================================
echo.

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

set "PYTHONPATH=%ROOT_DIR%"
if "%ENV%"=="" set "ENV=production"

echo [startup] ROOT_DIR=%ROOT_DIR%
echo [startup] PYTHONPATH=%PYTHONPATH%
echo [startup] ENV=%ENV%
echo.

if exist "viking_data\.openviking.pid" (
    del /f /q "viking_data\.openviking.pid"
    echo [startup] 已清理 OpenViking 残留锁文件
)

where py >nul 2>&1
if %errorlevel%==0 (
    set "PY_CMD=py -3"
) else (
    set "PY_CMD=python"
)

echo [startup] 使用解释器：%PY_CMD%
echo [startup] 启动 main.py（内部会拉起调度器 + Web + QQ）
start "My_Agent" cmd /k "%PY_CMD% main.py"

echo.
echo ✅ 已启动，请查看新窗口日志。
echo.
pause
