# main.py 唯一入口
import threading
import time

from core.Task.scheduler import  start_scheduler, get_local_ip
from core.Task.task_creator import app
#from qq_bridge import run_qq_bot
from core.logger import gateway_log

if __name__ == "__main__":
    print("✅ 启动调度中心...")
    start_scheduler()
    print("✅ 启动 AI端 服务...")
    ip = get_local_ip()
    gateway_log(f"服务启动：http://{ip}:5000")
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=5000, debug=False), daemon=True).start()
    while True:
        time.sleep(100)