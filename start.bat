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

:: ======================
:: 启动 1：主程序 main.py
:: ======================
start "主程序 - Flask" cmd /k cmd /k "conda activate agent && python main.py"

:: 等待 2 秒让服务端先启动
timeout /t 2 /nobreak >nul

:: ======================
:: 启动 2：模型日志窗口
:: ======================
start "对话日志窗口" cmd /k "conda activate agent && python log_client.py"

:: ======================
:: 启动 3：任务日志窗口
:: ======================
start "调试日志窗口" cmd /k "conda activate agent && python log_client.py"

echo.
echo 所有窗口已启动完成！
echo.
pause