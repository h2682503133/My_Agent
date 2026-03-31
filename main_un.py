import queue
import time
import datetime
import os
import threading
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, Response
from functools import wraps
import socket
import json
from core.Agent import Agent
from core.logger import gateway_log
import patch.fix_ov_windows

app = Flask(__name__)
app.secret_key = "123"

# ======================
# 全局单线程 FIFO 队列
# ======================
TASK_QUEUE = queue.Queue(maxsize=100)
MAX_RETRY = 2
MAX_TASK_TIME = 120


# ======================
# SSE 队列推送
# ======================
queue_clients = set()

def notify_queue_update():
    for client in list(queue_clients):
        try:
            client.put(True)
        except:
            queue_clients.discard(client)

@app.route('/queue/stream')
def queue_stream():
    def gen():
        q = queue.Queue()
        queue_clients.add(q)
        try:
            while True:
                q.get()
                waiting = TASK_QUEUE.qsize()
                yield f"data: {json.dumps({'waiting': waiting})}\n\n"
        except:
            queue_clients.discard(q)
    return Response(gen(), mimetype='text/event-stream')

# ======================
# 队列装饰器
# ======================
def queue_and_retry(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        ip = request.remote_addr
        now = time.strftime("%d/%b/%Y %H:%M:%S")
        print(f'{ip} - - [{now}] "{request.method} {request.path}" - 请求进入FIFO队列')
        gateway_log(f'{ip} - - [{now}] "{request.method} {request.path}" - 请求进入FIFO队列')

        user_id = session.get("user_id")
        user_msg = request.json.get("msg")
        if not user_id:
            return jsonify(error="请先登录")

        result = {}
        cond = threading.Condition()

        def callback(success, data):
            with cond:
                result["success"] = success
                result["data"] = data
                cond.notify()

        # 放入全局FIFO队列
        TASK_QUEUE.put((func, (user_id, user_msg), {}, callback, user_id))
        notify_queue_update()

        # 等待执行完毕
        with cond:
            cond.wait()

        notify_queue_update()
        return jsonify(result["data"]) if result["success"] else jsonify(error="请求失败")
    return wrapper

# ======================
# 单线程串行调度器（真正的简单FIFO）
# ======================
def fifo_scheduler():
    while True:
        try:
            # 阻塞取任务，没有任务就休眠，不占CPU
            func, args, kwargs, callback , user_id = TASK_QUEUE.get(timeout=0.5)
        except queue.Empty:
            continue
        print(f"[FIFO] 开始处理任务 → 用户ID: {user_id}")
        gateway_log(f"[FIFO] 开始处理任务 → 用户ID: {user_id}")
        success = False
        res = None

        # 重试机制
        for retry_idx in range(MAX_RETRY):
            try:
                # 直接在调度线程里执行，无并发
                res = func(*args, **kwargs)
                success = True
                break
            except Exception as e:
                print(f"[失败] 第{retry_idx+1}次重试")
                gateway_log(f"[失败] 第{retry_idx + 1}次重试")
                continue

        callback(success, res)
        TASK_QUEUE.task_done()
        gateway_log(f"[FIFO] 任务已完成 → 用户ID: {user_id}")

# 启动单线程调度器
threading.Thread(target=fifo_scheduler, daemon=True).start()

# ======================
# 路由逻辑完全不变
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

@app.route('/chat', methods=['POST'])
@queue_and_retry
def chat(user_id, user_msg):
    result = Agent.user_chat(user_msg, user_id)
    return {
        "reply": f"{Agent.default_agent[user_id]}：{result['agent_reply']}"
    }

@app.route('/queue/status')
def queue_status():
    return jsonify(waiting=TASK_QUEUE.qsize())

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

    gateway_log(f"网关在 http://{ip}:5000 启动")
    print(f"✅ 局域网访问地址：http://{ip}:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)