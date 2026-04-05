from satori.client import App, WebsocketsInfo, Account
from satori.const import EventType
from satori.event import MessageEvent
import asyncio
import requests
from flask import Flask, request, jsonify
import json

# ======================
# 你bat启动的正确路径
# ======================
with open("config/gateway_setting.json", "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

# ======================
# 配置读取
# ======================
MAIN_HOST = CONFIG["main"]["host"]
MAIN_PORT = CONFIG["main"]["port"]
QQ_CONFIG = CONFIG["channels"]["qq"]
QQ_SELF_PORT = QQ_CONFIG["self_port"]
SATORI_CFG = QQ_CONFIG["satori"]

# ======================
# QQ 机器人
# ======================
satori_app = App(WebsocketsInfo(
    host=SATORI_CFG["host"],
    port=SATORI_CFG["port"],
    token=SATORI_CFG["token"]
))

qq_sessions = {}

class QQOutput:
    def __init__(self, account, channel):
        self.account = account
        self.channel = channel
        # 保存异步主线程的事件循环（关键）
        self.loop = asyncio.get_event_loop()

    def send(self, text):
        # 线程安全提交，永不报错
        asyncio.run_coroutine_threadsafe(
            self.account.send_message(self.channel, text),
            self.loop
        )

# ======================
# Flask 接收回调
# ======================
qq_app = Flask("qq_bridge")

@qq_app.route("/send", methods=["POST"])
def on_recv_from_main():
    data = request.get_json()
    user_id = data["user_id"]
    text = data["text"]
    if user_id in qq_sessions:
        qq_sessions[user_id].send(text)
    return jsonify(ok=1)

# ======================
# QQ 消息监听
# ======================
@satori_app.register_on(EventType.MESSAGE_CREATED)
async def on_qq_message(account: Account, event: MessageEvent):
    user_id = event.user.id
    content = event.message.content.strip()
    qq_sessions[user_id] = QQOutput(account, event.channel)

    requests.post(f"http://{MAIN_HOST}:{MAIN_PORT}/submit_task", json={
        "user_id": user_id,
        "content": content,
        "channel_id": "qq",
        "callback_port": QQ_SELF_PORT
    })

# ======================
# 启动
# ======================
async def run_qq_bot():
    await satori_app.run_async()

async def main():
    await asyncio.gather(
        run_qq_bot(),
        asyncio.to_thread(
            qq_app.run,
            host="0.0.0.0",
            port=QQ_SELF_PORT,
            debug=CONFIG["flask_debug"]
        )
    )

if __name__ == "__main__":
    asyncio.run(main())