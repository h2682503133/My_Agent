@echo off
chcp 65001 >nul
setlocal

echo ==============================================
echo           My_Agent 一键启动脚本
echo ==============================================
echo.

set "ACTIVATE=conda activate agent"

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
echo.



:: 启动主程序（自动进虚拟环境）
echo [startup] 启动主窗口 main.py
start "主程序 - My_Agent" cmd /k "%ACTIVATE% && %PY_CMD% "main.py""

timeout /t 2 /nobreak >nul

:: 启动日志1
echo [startup] 启动调试日志窗口
start "调试日志窗口" cmd /k "%ACTIVATE% && %PY_CMD% "log_client.py""

:: 启动日志2
echo [startup] 启动对话日志窗口
start "对话日志窗口" cmd /k "%ACTIVATE% && %PY_CMD% "log_client.py""

echo.
echo ✅ 多窗口已启动：主程序 + 2个日志窗口
echo.

:console
set /p "cmd=>>> 请输入命令（exit/clean）："

if /i "%cmd%"=="exit" (
    goto exit_program
)
if /i "%cmd%"=="clean" (
    if exist "viking_data\.openviking.pid" (
        del /f /q "viking_data\.openviking.pid"
        echo [已清理] 锁文件
    ) else (
        echo [无锁文件]
    )
    goto console
)

echo 未知命令！支持：exit, clean
goto console

:exit_program
echo [安全关闭] 正在停止所有服务...
taskkill /f /im python.exe >nul 2>&1
if exist "viking_data\.openviking.pid" (
    del /f /q "viking_data\.openviking.pid"
)
echo ✅ 已全部关闭
pause