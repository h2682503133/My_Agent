import os
import json
import time
import threading
import requests
from datetime import datetime
from pathlib import Path
from core.logger import gateway_log 

# ======================
# 加载配置
# ======================
with open("config/gateway_setting.json", "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

BASE_ROOT_DIR = Path(__file__).parent.parent.parent

# 定时任务服务配置
TIMER_CFG = CONFIG["timer_task"]
TIMER_HOST = TIMER_CFG["host"]
TIMER_PORT = TIMER_CFG["port"]
TIMER_TASK_DIR = TIMER_CFG["task_dir"]

# 自动创建任务目录
task_full_path = BASE_ROOT_DIR / TIMER_TASK_DIR
os.makedirs(task_full_path, exist_ok=True)

MAIN_API = f"http://{CONFIG['main']['host']}:{CONFIG['main']['port']}/submit_task"
TASK_DIR = str(task_full_path)

def add_timer_task(
    user_id: str,
    channel_id: str,
    callback_port: int,
    trigger_timestamp: float,
    content: str = "system:auto_commit",
    task_type: str = "submit_task"  # submit_task / send_message
) -> str:
    """
    添加定时任务
    - task_type = submit_task：创建普通任务
    - task_type = send_message：直接发送消息给用户
    返回：成功/失败提示字符串
    """
    try:
        task_id = f"task_{int(time.time() * 1000)}_{user_id}"

        task_data = {
            "task_id": task_id,
            "user_id": user_id,
            "channel_id": channel_id,
            "callback_port": callback_port,
            "trigger_time": trigger_timestamp,
            "content": content,
            "task_type": task_type,
            "created_at": datetime.now().isoformat()
        }

        path = os.path.join(TASK_DIR, f"{task_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(task_data, f, ensure_ascii=False, indent=2)

        # ======================
        # 【已修改】通道验证消息（完全匹配你的 send 格式）
        # ======================
        try:
            test_payload = {
                "user_id": user_id,
                "text": "[系统] 定时任务已创建，通道正常",
                "images": []
            }
            url = f"http://127.0.0.1:{callback_port}/send"
            requests.post(url, json=test_payload, timeout=2)
        except:
            gateway_log(f"创建定时任务：{user_id} {task_type} {trigger_timestamp} {content}，但测试通道失败")
            return f"定时任务创建成功：{task_type}，但测试通道失败，请告知用户"
        
        gateway_log(f"创建定时任务：{user_id} {task_type} {trigger_timestamp} {content}")
        return f"定时任务创建成功：{task_type}，将在指定时间执行"

    except Exception as e:
        gateway_log(f"定时任务创建失败：{user_id} {task_type} {trigger_timestamp} {content}")
        return f"定时任务创建失败：{str(e)}"

# ======================
# 后台扫描线程
# ======================
def timer_scan_loop():
    while True:
        now = time.time()

        for filename in os.listdir(TASK_DIR):
            if not filename.endswith(".json"):
                continue

            path = os.path.join(TASK_DIR, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    task = json.load(f)

                trigger_time = task.get("trigger_time", 0)
                if now >= trigger_time:
                    execute_timer_task(task)
                    os.remove(path)
            except:
                continue

        time.sleep(1)

# ======================
# 执行任务（支持两种类型）
# ======================
def execute_timer_task(task):
    task_type = task.get("task_type", "submit_task")
    user_id = task["user_id"]
    channel_id = task["channel_id"]
    callback_port = task["callback_port"]
    content = task["content"]
    
    gateway_log(f"{user_id}于{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}的定时任务[{content}]开始执行")
    
    if task_type == "submit_task":
        payload = {
            "user_id": user_id,
            "channel_id": channel_id,
            "callback_port": callback_port,
            "content": content
        }
        try:
            requests.post(MAIN_API, json=payload, timeout=3)
        except:
            pass

    elif task_type == "send_message":
        # ======================
        # 【已修改】直接发送消息格式（完全匹配你的 output.send）
        # ======================
        try:
            send_url = f"http://127.0.0.1:{callback_port}/send"
            send_payload = {
                "user_id": user_id,
                "text": content,
                "images": []
            }
            requests.post(send_url, json=send_payload, timeout=3)
        except:
            gateway_log(f"{user_id}定时任务发送消息失败：{content}")

# ======================
# 启动服务
# ======================
def start_timer_service():
    t = threading.Thread(target=timer_scan_loop, daemon=True)
    t.start()
    print(f"✅ 定时任务服务已启动 on http://{TIMER_HOST}:{TIMER_PORT}")