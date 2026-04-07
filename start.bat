@echo off
chcp 65001 >nul
echo ==============================================
echo           项目一键启动脚本
echo ==============================================
echo.

:: ======================
:: 让用户输入虚拟环境名称（直接回车=不使用）
:: ======================
set "CONDA_ENV_NAME="
set /p "CONDA_ENV_NAME=请输入虚拟环境名称（直接回车=不使用虚拟环境）："

if not defined CONDA_ENV_NAME (
    echo [信息] 未使用虚拟环境，直接使用系统 Python
    set "PY_CMD=python"
) else (
    echo [信息] 使用虚拟环境：%CONDA_ENV_NAME%
    set "PY_CMD=conda activate %CONDA_ENV_NAME% && python"
)
echo.

:: ======================
:: 设置环境变量
:: ======================
set PYTHONPATH=%~dp0
set ENV=production
echo 已设置环境变量：
echo PYTHONPATH=%PYTHONPATH%
echo ENV=%ENV%
echo.

if exist "viking_data\.openviking.pid" (
    del /f /q "viking_data\.openviking.pid"
    echo [已清理] OpenViking 残留锁文件
)

:: ======================
:: 启动 1：主程序 main.py
:: ======================
start "主程序 - Flask" cmd /k "%PY_CMD% main.py"

:: 等待 2 秒让服务端先启动
timeout /t 2 /nobreak >nul

:: ======================
:: 启动 2：模型日志窗口
:: ======================
start "调试日志窗口" cmd /k "%PY_CMD% log_client.py"

:: ======================
:: 启动 3：任务日志窗口
:: ======================
start "对话日志窗口" cmd /k "%PY_CMD% log_client.py"


echo.
echo ✅ 服务启动完成！当前窗口为【总控制台】
echo.

echo 请输入web或qq 在两种连接方式中至少选一种
:console
set /p "cmd=>>> 请输入命令："

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
if /i "%cmd%"=="qq" (
    start "QQ连接" cmd /k "%PY_CMD% core\\Gateway\\qq_bridge.py"
    goto console
)
if /i "%cmd%"=="web" (
    start "web窗口" cmd /k "%PY_CMD% core\\Gateway\\web_server.py"
    goto console
)

echo 未知命令！支持：exit, clean, qq, web
goto console


:exit_program
echo [安全关闭] 正在停止所有服务...
taskkill /f /im python.exe >nul 2>&1
if exist "viking_data\.openviking.pid" (
    del /f /q "viking_data\.openviking.pid"
)
taskkill /f /im cmd.exe >nul 2>&1
echo ✅ 已全部关闭
pause
exit