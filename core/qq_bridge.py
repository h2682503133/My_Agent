import threading
import requests
from flask import Flask

from core.logger import gateway_log
from core.output import QQOutput
from core.user import User
from core.task import Task

app = Flask(__name__)
LLBOT_PORT = 5600
BRIDGE_PORT = 20214
AI_HOST = "http://127.0.0.1:5000"


@app.route("/", methods=["POST"])
def webhook():
    return "", 204


def qq_handler(user_id, content, channel):
    """
    QQ 入口兼容函数：围绕 User/Task 组织数据。
    这里的 output 采用多态 send 接口，具体发送能力由 channel 提供。
    """
    try:
        output = QQOutput(lambda text: channel.send(text) if hasattr(channel, "send") else None)
        user = User(user_id=str(user_id), session_id=str(user_id), output=output)
        task = Task(task_id=f"qq-{user.user_id}", user_id=user.user_id, content=content)

        s = requests.Session()
        s.post(f"{AI_HOST}/do_login", data={"user_id": user.user_id})
        r = s.post(f"{AI_HOST}/chat", json={"msg": task.content})
        reply = r.json().get("reply", "收到")

        user.send(reply)
        return reply
    except Exception:
        return "服务繁忙"


def start_qq():
    gateway_log("QQ服务启动")
    threading.Thread(
        target=app.run,
        kwargs={"host": "127.0.0.1", "port": BRIDGE_PORT, "debug": False},
        daemon=True,
    ).start()
