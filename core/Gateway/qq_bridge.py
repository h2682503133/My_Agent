import asyncio
import json
import requests
from flask import Flask, request, jsonify
from satori.client import App, WebsocketsInfo, Account
from satori.const import EventType
from satori.event import MessageEvent

# ======================
# 配置（和你原来一样）
# ======================
with open("config/gateway_setting.json", "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

MAIN_HOST = CONFIG["main"]["host"]
MAIN_PORT = CONFIG["main"]["port"]
QQ_CONFIG = CONFIG["channels"]["qq"]
QQ_SELF_PORT = QQ_CONFIG["self_port"]
SATORI_CFG = QQ_CONFIG["satori"]

# ======================
# Satori 客户端
# ======================
satori_app = App(WebsocketsInfo(
    host=SATORI_CFG["host"],
    port=SATORI_CFG["port"],
    token=SATORI_CFG["token"]
))

# 保存用户的发送通道（给main回调用）
qq_user_senders = {}

# ======================
# QQ 消息发送器（给main回调）
# ======================
class QQSender:
    def __init__(self, account: Account, channel):
        self.account = account
        self.channel = channel
        self.loop = asyncio.get_event_loop()

    def send(self, text: str):
        # 线程安全发送，不阻塞、不报错
        asyncio.run_coroutine_threadsafe(
            self.account.send_message(self.channel, text),
            self.loop
        )

# ======================
# Flask：接收 MAIN 回调消息
# ======================
qq_app = Flask("qq_bridge")

@qq_app.route("/send", methods=["POST"])
def receive_from_main():
    data = request.get_json()
    user_id = data["user_id"]
    text = data["text"]

    if user_id in qq_user_senders:
        qq_user_senders[user_id].send(text)

    return jsonify(ok=1)

# ======================
# Satori：接收QQ消息 → 转发给 MAIN
# ======================
@satori_app.register_on(EventType.MESSAGE_CREATED)
async def on_qq_message(account: Account, event: MessageEvent):
    user_id = event.user.id
    content = event.message.content.strip()

    # 保存发送器，用于 MAIN 回调
    qq_user_senders[user_id] = QQSender(account, event.channel)

    payload = {
        "user_id": user_id,
        "content": content,
        "channel_id": "qq",
        "callback_port": QQ_SELF_PORT
    }

    # 转发到 main
    requests.post(
        f"http://{MAIN_HOST}:{MAIN_PORT}/submit_task",
        json=payload
    )

# ======================
# 启动
# ======================
async def run_satori():
    await satori_app.run_async()

async def main():
    await asyncio.gather(
        run_satori(),
        asyncio.to_thread(
            qq_app.run,
            host="0.0.0.0",
            port=QQ_SELF_PORT,
            debug=False
        )
    )

if __name__ == "__main__":
    asyncio.run(main())