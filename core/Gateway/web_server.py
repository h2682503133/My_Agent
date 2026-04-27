from flask import Flask, request, render_template, session, jsonify, redirect
import json
import asyncio
import websockets
import threading
from flask_sock import Sock

# 加载你的配置（完全不变！）
with open("config/gateway_setting.json", "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

MAIN_HOST = CONFIG["main"]["host"]
MAIN_PORT = CONFIG["main"]["port"]
WEB_PORT = CONFIG["channels"]["web"]["self_port"]

# Flask + WebSocket 单端口（不冲突！）
app = Flask("user_web")
app.secret_key = "123"
sock = Sock(app)

# 在线用户
connected_users = {}

# ------------------------------
# 页面路由（完全不变）
# ------------------------------
@app.route('/')
def index():
    if not session.get("user_id"):
        return redirect("/login")
    return redirect("/chat")

@app.route('/login')
def login():
    return render_template("login.html")

@app.route('/do_login', methods=['POST'])
def do_login():
    user_id = request.form.get("user_id")
    session["user_id"] = user_id
    return redirect("/chat")

@app.route('/chat')
def chat():
    if not session.get("user_id"):
        return redirect("/login")
    return render_template("chat.html")

# ------------------------------
# 发送消息给AI（完全不变）
# ------------------------------
@app.route('/chat', methods=['POST'])
def send_chat():
    user_id = session.get("user_id")
    text = request.json.get("msg")

    # 发给你的main服务（不变）
    import requests
    requests.post(f"http://{MAIN_HOST}:{MAIN_PORT}/submit_task", json={
        "user_id": user_id,
        "content": text,
        "channel_id": "web",
        "callback_port": WEB_PORT
    })
    return jsonify(ok=1)

# ------------------------------
# 单端口 WebSocket（不冲突！）
# ------------------------------
@sock.route('/ws')
def ws(ws):
    user_id = session.get("user_id")
    if not user_id:
        return

    connected_users[user_id] = ws
    print(f"[web] {user_id} 已连接")

    try:
        while True:
            ws.receive()
    except:
        pass
    finally:
        if user_id in connected_users:
            del connected_users[user_id]

# ------------------------------
# main服务回调：推送消息
# ------------------------------
@app.route('/send', methods=['POST'])
def push_msg():
    data = request.json
    user_id = data.get("user_id")

    if user_id in connected_users:
        try:
            connected_users[user_id].send(json.dumps(data, ensure_ascii=False))
        except:
            pass

        try:
            import requests
            requests.post(f"http://127.0.0.1:{WEB_PORT+1}/forward", json=data)
        except:
            pass


    return jsonify(ok=1)

@app.route('/logout')
def logout():
    session.clear()
    return redirect("/login")

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=WEB_PORT)