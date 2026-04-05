@echo off
chcp 65001 >nul
echo ==============================================
echo           项目一键启动脚本
echo ==============================================
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
start "主程序 - Flask" cmd /k cmd /k "conda activate agent && python main.py"

:: 等待 2 秒让服务端先启动
timeout /t 2 /nobreak >nul

:: ======================
:: 启动 2：模型日志窗口
:: ======================
start "调试日志窗口" cmd /k "conda activate agent && python log_client.py"

:: ======================
:: 启动 3：任务日志窗口
:: ======================
start "对话日志窗口" cmd /k "conda activate agent && python log_client.py"



echo.
echo ✅ 服务启动完成！当前窗口为【总控制台】
echo.

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
    start "QQ连接" cmd /k "conda activate agent && python core\\Gateway\\qq_bridge.py"
    goto console
)
if /i "%cmd%"=="web" (
    start "web窗口" cmd /k "conda activate agent && python core\\Gateway\\web_server.py"
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
taskkill /f /im cmd.exe >nul 2>&1
echo ✅ 已全部关闭
pause
exit