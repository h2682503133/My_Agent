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

# ======================
# 全局调度控制（优化用）
# ======================
scan_interval = 5.0         # 默认 5 秒刷新
NEED_FAST_SCAN = False      # 是否需要快速扫描
LAST_TASK_ADD_TIME = 0     # 最后一次添加任务的时间

# ======================
# 1. 添加定时任务
# ======================
def add_timer_task(
    user_id: str,
    channel_id: str,
    callback_port: int,
    trigger_timestamp: float,
    content: str = "system:auto_commit",
    task_type: str = "submit_task"  # submit_task / send_message
) -> str:
    global NEED_FAST_SCAN, LAST_TASK_ADD_TIME
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
        # 新增：添加任务 → 立刻开启快速扫描
        # ======================
        NEED_FAST_SCAN = True
        LAST_TASK_ADD_TIME = time.time()

        try:
            test_payload = {
                "user_id": user_id,
                "text": f"[定时任务] {task_type}:{content}",
                "images": []
            }
            url = f"http://127.0.0.1:{callback_port}/send"
            requests.post(url, json=test_payload, timeout=2)
        except:
            gateway_log(f"创建定时任务：{user_id} {task_type} {trigger_timestamp} {content}，但测试通道失败")
            return f"定时任务创建成功：{task_type}，但测试通道失败，请告知用户"
        
        gateway_log(f"创建定时任务：{user_id} {task_type} {trigger_timestamp} {content}")
        return f"定时任务{task_type}:{content}创建成功，将在指定时间执行"

    except Exception as e:
        gateway_log(f"定时任务创建失败：{user_id} {task_type} {trigger_timestamp} {content}")
        return f"定时任务创建失败：{str(e)}"

# ======================
# 2. 查询当前用户所有定时任务（只return，不发消息）
# ======================
def list_user_tasks(user_id: str) -> str:
    tasks = []
    try:
        for filename in os.listdir(TASK_DIR):
            if not filename.endswith(".json"):
                continue

            path = os.path.join(TASK_DIR, filename)
            with open(path, "r", encoding="utf-8") as f:
                task = json.load(f)

            if task.get("user_id") == user_id:
                trigger_time = task.get("trigger_time", 0)
                task["trigger_time_str"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(trigger_time))
                tasks.append(task)

        tasks.sort(key=lambda x: x["trigger_time"])

        # ======================
        # 直接在这里拼成文本
        # ======================
        if not tasks:
            return "当前无任何定时任务"

        msg = "当前定时任务列表：\n\n"
        for idx, t in enumerate(tasks, 1):
            msg += f"{idx}. {t['trigger_time_str']}\n"
            msg += f"   类型：{t['task_type']}\n"
            msg += f"   内容：{t['content']}\n"
            msg += f"   任务ID：{t['task_id']}\n\n"

        return msg.strip()

    except:
        return "查询定时任务失败"

# ======================
# 3. 删除指定任务（删除后自动发消息通知用户）
# ======================
def delete_user_task(user_id: str, task_id: str) -> str:
    try:
        print(user_id,task_id)
        target_file = None
        task_info = None

        for filename in os.listdir(TASK_DIR):
            if not filename.endswith(".json"):
                continue
            path = os.path.join(TASK_DIR, filename)
            with open(path, "r", encoding="utf-8") as f:
                task = json.load(f)

            if task.get("user_id") == user_id and task.get("task_id") == task_id:
                target_file = path
                task_info = task
                break

        if not target_file or not os.path.exists(target_file):
            return "未找到该定时任务"

        os.remove(target_file)
        gateway_log(f"用户 {user_id} 删除定时任务 {task_id} 成功")

        try:
            callback_port = task_info["callback_port"]
            text = f"[系统] 已删除定时任务\n任务ID：{task_id}\n内容：{task_info['content']}"
            payload = {
                "user_id": user_id,
                "text": text,
                "images": []
            }
            url = f"http://127.0.0.1:{callback_port}/send"
            requests.post(url, json=payload, timeout=2)
        except:
            pass

        return "定时任务已删除"

    except Exception as e:
        gateway_log(f"删除定时任务失败：{user_id} {task_id} {str(e)}")
        return "删除定时任务失败"

# ======================
# 智能扫描核心：检查是否有 3 分钟内的任务
# ======================
def has_nearby_task(seconds=180):
    now = time.time()
    try:
        for filename in os.listdir(TASK_DIR):
            if not filename.endswith(".json"):
                continue
            path = os.path.join(TASK_DIR, filename)
            with open(path, "r", encoding="utf-8") as f:
                task = json.load(f)
            t = task.get("trigger_time", 0)
            if 0 < t <= now + seconds:
                return True
    except:
        pass
    return False

# ======================
# 后台扫描线程（智能调度）
# ======================
def timer_scan_loop():
    global scan_interval, NEED_FAST_SCAN
    while True:
        now = time.time()

        # ======================
        # 智能调度核心
        # ======================
        if NEED_FAST_SCAN:
            # 最近添加过任务 → 5 秒扫描
            scan_interval = 5.0
            # 30 秒内没新任务 → 自动退出快速扫描
            if now - LAST_TASK_ADD_TIME > 30:
                NEED_FAST_SCAN = False
        else:
            # 检查有无 3 分钟内要执行的任务
            if has_nearby_task(180):
                scan_interval = 5.0
            else:
                scan_interval = 60.0  # 无紧急任务 → 1 分钟一次

        # ======================
        # 执行扫描
        # ======================
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

        time.sleep(scan_interval)

# ======================
# 执行任务
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