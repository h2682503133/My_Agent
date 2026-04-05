from satori.client import App, WebsocketsInfo, Account
from satori.const import EventType
from satori.event import MessageEvent
import asyncio
import requests
from flask import Flask, request, jsonify
import json

# 加载配置
with open("config/gateway_setting.json", "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

# ======================
# 从配置读取所有内容
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

# 会话管理（不跨进程，绝对安全）
qq_sessions = {}

class QQOutput:
    def __init__(self, account, channel):
        self.account = account
        self.channel = channel

    def send(self, text):
        # 拿全局事件循环 + 安全提交协程
        loop = asyncio.get_event_loop()
        future = asyncio.run_coroutine_threadsafe(
            self.account.send_message(self.channel, text), loop
        )
        # 等待任务完成，防止被销毁
        future.result()

# ======================
# Flask 接收 main 发送
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

    # 传给 main：只传数据
    requests.post(f"http://{MAIN_HOST}:{MAIN_PORT}/submit_task", json={
        "user_id": user_id,
        "content": content,
        "channel_id": "qq",
        "callback_port": QQ_SELF_PORT
    })

# ======================
# 同时启动 QQ + 接收服务
# ======================
async def run_qq_bot():
    await satori_app.run_async()

async def main():
    print(f"[QQ] 渠道启动，监听回调端口：{QQ_SELF_PORT}")
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