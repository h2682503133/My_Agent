# main.py 唯一入口
import threading
import time
import json
from core.Task.scheduler import  start_scheduler, get_local_ip
from core.Task.task_creator import app
#from qq_bridge import run_qq_bot
from core.logger import gateway_log
from core.Gateway.image_server import start_local_image_server
from core.Task.timer_task import start_timer_service
if __name__ == "__main__":
    with open("config/gateway_setting.json", "r", encoding="utf-8") as f:
        CONFIG = json.load(f)
    print("✅ 启动调度中心...")
    start_scheduler()
    print("✅ 启动 AI端 服务...")
    
    #启动图像服务
    start_local_image_server()
    #启动定时任务服务
    start_timer_service()

    # 从配置读取
    host = CONFIG["main"]["host"]
    port = CONFIG["main"]["port"]
    flask_debug = CONFIG["flask_debug"]
    ip = get_local_ip()

    gateway_log(f"服务启动：http://{ip}:{port}")

    # 用配置启动 Flask
    threading.Thread(
        target=lambda: app.run(host=host, port=port, debug=flask_debug),
        daemon=True
    ).start()

    while True:
        time.sleep(100)