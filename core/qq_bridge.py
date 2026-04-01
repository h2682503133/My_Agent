import threading
import requests
from flask import Flask
from core.logger import gateway_log

app = Flask(__name__)
LLBOT_PORT = 5600
BRIDGE_PORT = 20214
AI_HOST = "http://127.0.0.1:5000"

@app.route("/", methods=["POST"])
def webhook():
    return "", 204

def qq_handler(user_id, content, channel):
    try:
        s = requests.Session()
        s.post(f"{AI_HOST}/do_login", data={"user_id": user_id})
        r = s.post(f"{AI_HOST}/chat", json={"msg": content})
        return r.json().get("reply", "收到")
    except:
        return "服务繁忙"

def start_qq():
    gateway_log("QQ服务启动")
    threading.Thread(target=app.run, kwargs={"host":"127.0.0.1","port":BRIDGE_PORT,"debug":False}, daemon=True).start()