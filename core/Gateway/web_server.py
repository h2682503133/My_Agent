from flask import Flask, request, render_template, redirect, url_for, session, Response, jsonify
import queue
import requests
import json

# 加载配置
with open("config/gateway_setting.json", "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

MAIN_HOST = CONFIG["main"]["host"]
MAIN_PORT = CONFIG["main"]["port"]
WEB_PORT = CONFIG["channels"]["web"]["self_port"]  # 5201

app = Flask("user_web")
app.secret_key = "123"

# ============================
# 用户消息队列（SSE推送用）
# ============================
user_streams = {}

# ============================
# 你的网页路由（完全保留）
# ============================
@app.route('/')
def login():
    return render_template("login.html")

@app.route('/do_login', methods=['POST'])
def do_login():
    session['user_id'] = request.form.get('user_id')
    return redirect(url_for('chat_page'))

@app.route('/chat')
def chat_page():
    if not session.get("user_id"):
        return redirect('/')
    return render_template("chat.html")

# ============================
# ✅ 修复 404：SSE 推送接口
# ============================
@app.route('/queue/stream')
def queue_stream():
    user_id = session.get("user_id")
    if not user_id:
        return "", 401

    q = queue.Queue()
    user_streams[user_id] = q

    def gen():
        while True:
            msg = q.get()
            yield f"data: {msg}\n\n"

    return Response(gen(), mimetype="text/event-stream")

# ============================
# ✅ 发送消息到 main（5000）
# ============================
@app.route('/chat', methods=['POST'])
def chat():
    user_id = session.get("user_id")
    msg = request.json.get("msg")

    # 发送给 main
    requests.post(f"http://{MAIN_HOST}:{MAIN_PORT}/submit_task", json={
        "user_id": user_id,
        "content": msg,
        "channel_id": "web",
        "callback_port": WEB_PORT
    })

    return jsonify(ok=1)

# ============================
# ✅ 接收 main 回调 → 推送给网页
# ============================
@app.route("/send", methods=["POST"])
def receive_from_main():
    data = request.json
    user_id = data.get("user_id")
    text = data.get("text")

    if user_id in user_streams:
        user_streams[user_id].put(text)

    return jsonify(ok=1)

# ============================
# 启动 5201
# ============================
if __name__ == '__main__':
    app.run(host="127.0.0.1", port=WEB_PORT, debug=False)