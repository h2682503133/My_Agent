import threading
from core.queue_manager import start_scheduler
from core.web_server import start_web
from core.qq_bridge import start_qq
from core.logger import gateway_log,log_server
import time
if __name__ == "__main__":
    start_scheduler()


    web_thread = threading.Thread(target=start_web, daemon=True)
    web_thread.start()

    start_qq()
    gateway_log("调度器启动")
    threading.Thread(target=log_server, daemon=True).start()

    # 让窗口永远不退出（关键！）
    while True:
        time.sleep(1)