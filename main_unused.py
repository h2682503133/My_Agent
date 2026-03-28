import queue
import time
import threading
from collections import OrderedDict
from core.Agent import Agent
from flask import Flask, render_template, request, jsonify, redirect, url_for, session,Response
from functools import wraps
import socket
import json
app = Flask(__name__)
app.secret_key = "123"

import patch.fix_ov_windows

# 原SSE客户端集合（完全不变）
queue_clients = set()
#正在处理的任务数
processed=0
# 原全局队列（保留变量名，改为用户隔离队列管理器）
MESSAGE_QUEUE = queue.Queue(maxsize=50)
SCHED_COND = threading.Condition()
# 原重试次数（完全不变）
MAX_RETRY = 2
MAX_TASK_TIME=120

# ======================
# 🔥 新核心逻辑：用户隔离 + 槽位跳过 + 公平轮询（嵌入原有变量）
# ======================
USER_QUEUES: OrderedDict[str, queue.Queue] = OrderedDict()
BATCH_SIZE = 2  # 固定并发槽位（可修改）
BATCH_SLOTS = [None] * BATCH_SIZE
BUSY_USERS: set[str] = set()
USER_LOCK = threading.Lock()
BUSY_LOCK = threading.Lock()
SLOTS_LOCK = threading.Lock()


# ======================
# 你原有 SSE 推送函数（完全不动）
# ======================
def notify_queue_update():
    # 通知所有前端队列变化
    for client in list(queue_clients):
        try:
            client.put(True)
        except:
            queue_clients.remove(client)


# 你原有 SSE 接口（完全不动，HTML无感知）
@app.route('/queue/stream')
def queue_stream():
    def gen():
        q = queue.Queue()
        queue_clients.add(q)
        try:
            while True:
                q.get()
                waiting = MESSAGE_QUEUE.qsize()
                yield f"data: {json.dumps({'waiting': waiting})}\n\n"
        except:
            queue_clients.remove(q)

    return Response(gen(), mimetype='text/event-stream')


# ======================
# 队列重试装饰器
# ======================
def queue_and_retry(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        ip = request.remote_addr
        now = time.strftime("%d/%b/%Y %H:%M:%S")
        method = request.method
        path = request.path
        print(f'{ip} - - [{now}] "{method} {path} {request.environ.get("SERVER_PROTOCOL", "HTTP/1.1")}" - 请求已接收，进入队列')

        user_id = session.get('user_id')
        if not user_id:
            return {"error": "请先登录"}

        user_msg = request.json.get('msg')
        # 获取用户独立队列（保留原入队逻辑）
        with USER_LOCK:
            if user_id not in USER_QUEUES:
                USER_QUEUES[user_id] = queue.Queue(maxsize=10)
            user_q = USER_QUEUES[user_id]

        # 原等待逻辑 + 队列通知
        try:
            MESSAGE_QUEUE.put(time.time(), timeout=5)
            notify_queue_update()
        except:
            return {"error": "服务繁忙，请稍后重试"}

        # 任务回调（原结果返回逻辑）
        result = {}
        cond = threading.Condition()

        def callback(success, data):
            with cond:
                result["success"] = success
                result["data"] = data
                cond.notify()

        # 加入用户队列
        user_q.put((func, (user_id, user_msg), {}, callback))

        # 等待执行完成
        with cond:
            cond.wait()

        # 原出队逻辑 + 队列通知
        MESSAGE_QUEUE.get()
        MESSAGE_QUEUE.task_done()
        notify_queue_update()

        if result["success"]:
            return jsonify(result["data"])
        return jsonify({"error": "请求失败"})

    return wrapper


# ======================
# 调度器：槽位跳过 + 公平轮询（后台运行，不影响原有代码）
# ======================
def slot_scheduler():
    global SCHED_COND
    global processed
    while True:
        if not MESSAGE_QUEUE.qsize():
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
                    slot_idx = BATCH_SLOTS.index(None)
                    BATCH_SLOTS[slot_idx] = user_id

                with BUSY_LOCK:
                    BUSY_USERS.add(user_id)

                # 取任务
                task = user_q.get_nowait()
                func, args, kwargs, callback = task
                processed += 1

                # 启动独立任务
                threading.Thread(
                    target=run_task,
                    args=(user_id, func, args, kwargs, callback, slot_idx),
                    daemon=True
                ).start()

            except Exception:
                try:
                    with SLOTS_LOCK:
                        BATCH_SLOTS[slot_idx] = None
                    with BUSY_LOCK:
                        BUSY_USERS.discard(user_id)
                except:
                    pass
                continue

        # 无任务休息
        if processed == 0:
            time.sleep(0.1)

# ======================
# 任务处理器
# ======================
def run_task(user_id, func, args, kwargs, callback, slot_idx):
    print(f"[处理开始] 用户 {user_id}")
    try:
        # 重试循环
        for retry_idx in range(MAX_RETRY):
            try:
                res = None

                # 执行函数 + 超时控制
                def task_func():
                    nonlocal res
                    res = func(*args, **kwargs)

                t = threading.Thread(target=task_func, daemon=True)
                t.start()
                t.join(timeout=MAX_TASK_TIME)

                # 超时
                if t.is_alive():
                    print(f"[超时失败] 用户 {user_id} 第{retry_idx+1}次，重试")
                    continue

                # 成功
                callback(True, res)
                return

            except Exception as e:
                print(f"[报错失败] 用户 {user_id} 第{retry_idx+1}次，重试")
                continue

        # 彻底失败
        callback(False, None)

    finally:
        # 释放槽位 + 标记不忙
        with SLOTS_LOCK:
            BATCH_SLOTS[slot_idx] = None
        with BUSY_LOCK:
            BUSY_USERS.discard(user_id)
        global processed
        processed-=1

# 启动调度器
threading.Thread(target=slot_scheduler, daemon=True).start()


# ======================
# 你原有 所有页面/接口（完全不动！Agent/HTML 100%兼容）
# ======================
@app.route('/')
def login():
    return render_template("login.html")


@app.route('/do_login', methods=['POST'])
def do_login():
    user_id = request.form.get('user_id')
    session['user_id'] = user_id
    return redirect(url_for('chat_page'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


@app.route('/chat')
def chat_page():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    return render_template("chat.html", user_id=user_id)


# 对话接口（完全保留你的Agent调用，HTML无修改）
@app.route('/chat', methods=['POST'])
@queue_and_retry
def chat(user_id, user_msg):
    # Agent请求
    result = Agent.user_chat(user_msg, user_id)
    # HTML渲染
    return {
        "reply": f"{Agent.default_agent[user_id]}：{result['agent_reply']}"
    }


# 你原有 队列状态接口（完全不动）
@app.route('/queue/status')
def queue_status():
    waiting = MESSAGE_QUEUE.qsize()
    return jsonify(waiting=waiting)


# 你原有 获取本地IP（完全不动）
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.244.0.0', 80))
        ip = s.getsockname()[0]
    except:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip
if __name__ == "__main__":
    ip = get_local_ip()
    print(f"✅ 局域网访问地址：http://{ip}:5000")
    print(f"✅ 所有校园网设备（10.244开头）均可直接打开！")
    # 核心：host='0.0.0.0' 开放所有局域网IP
    app.run(host='0.0.0.0', port=5000, debug=False)