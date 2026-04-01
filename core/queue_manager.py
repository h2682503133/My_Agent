import queue
import time
import threading
from collections import OrderedDict
from functools import wraps

from core.logger import gateway_log
from core.task import Task
from core.user import User
from core.output import WebOutput

MAX_RETRY = 2
MAX_TASK_TIME = 120
BATCH_SIZE = 2

MESSAGE_QUEUE = queue.Queue(maxsize=50)
USER_QUEUES: OrderedDict[str, queue.Queue] = OrderedDict()
BATCH_SLOTS = [None] * BATCH_SIZE
BUSY_USERS: set[str] = set()

USER_LOCK = threading.Lock()
BUSY_LOCK = threading.Lock()
SLOTS_LOCK = threading.Lock()
processed = 0

queue_clients = set()


def notify_queue_update():
    for client in list(queue_clients):
        try:
            client.put(MESSAGE_QUEUE.qsize())
        except Exception:
            queue_clients.remove(client)


def _build_web_task(user_id: str, user_msg: str) -> tuple[Task, User, WebOutput]:
    output = WebOutput()
    user = User(user_id=user_id, session_id=user_id, output=output)
    task_id = f"{user_id}-{int(time.time() * 1000)}"
    task = Task(task_id=task_id, user_id=user_id, content=user_msg)
    return task, user, output


def queue_and_retry(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        from flask import request, session

        ip = request.remote_addr
        now = time.strftime("%d/%b/%Y %H:%M:%S")
        method = request.method
        path = request.path
        gateway_log(f'{ip} - - [{now}] "{method} {path}" - 请求进入队列')

        user_id = session.get('user_id')
        if not user_id:
            return {"error": "请先登录"}

        user_msg = (request.json or {}).get('msg', '')
        task, user, output = _build_web_task(user_id, user_msg)

        with USER_LOCK:
            if user_id not in USER_QUEUES:
                USER_QUEUES[user_id] = queue.Queue(maxsize=10)
            user_q = USER_QUEUES[user_id]

        try:
            MESSAGE_QUEUE.put(time.time(), timeout=5)
            notify_queue_update()
        except Exception:
            return {"error": "服务繁忙"}

        result = {}
        cond = threading.Condition()

        def callback(success, data):
            with cond:
                result["success"] = success
                result["data"] = data
                cond.notify()

        user_q.put((task, user, output, func, callback))

        with cond:
            cond.wait()

        MESSAGE_QUEUE.get()
        MESSAGE_QUEUE.task_done()
        notify_queue_update()

        return result["data"] if result["success"] else {"error": "失败"}

    return wrapper


def slot_scheduler():
    global processed
    while True:
        if not MESSAGE_QUEUE.qsize():
            time.sleep(0.1)
            continue

        user_list = list(USER_QUEUES.keys())
        for user_id in user_list:
            if processed >= BATCH_SIZE:
                break
            try:
                user_q = USER_QUEUES[user_id]
                if user_q.empty():
                    continue
                with BUSY_LOCK:
                    if user_id in BUSY_USERS:
                        continue
                with SLOTS_LOCK:
                    if None not in BATCH_SLOTS:
                        break
                    slot = BATCH_SLOTS.index(None)
                    BATCH_SLOTS[slot] = user_id
                with BUSY_LOCK:
                    BUSY_USERS.add(user_id)
                task_item = user_q.get_nowait()
                processed += 1
                threading.Thread(target=run_task, args=(user_id, task_item, slot), daemon=True).start()
            except Exception:
                pass

        if processed == 0:
            time.sleep(0.1)


def run_task(user_id, task_item, slot):
    gateway_log(f"[处理] 用户{user_id}")
    task, user, output, func, callback = task_item
    try:
        for _ in range(MAX_RETRY):
            try:
                res = None

                def tf():
                    nonlocal res
                    task.status = "running"
                    res = func(task, user)

                t = threading.Thread(target=tf, daemon=True)
                t.start()
                t.join(MAX_TASK_TIME)
                if not t.is_alive():
                    task.status = "completed"
                    if task.final_result and not output.messages:
                        user.send(task.final_result)
                    callback(True, res)
                    return
            except Exception:
                task.retry_count += 1

        task.status = "pending"
        Task.save_pending_task(user.user_id, task)
        callback(False, None)
    finally:
        with SLOTS_LOCK:
            BATCH_SLOTS[slot] = None
        with BUSY_LOCK:
            BUSY_USERS.discard(user_id)
        global processed
        processed -= 1


def start_scheduler():
    threading.Thread(target=slot_scheduler, daemon=True).start()
