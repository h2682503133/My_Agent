from satori.client import App, WebsocketsInfo, Account
from satori.const import EventType
from satori.event import MessageEvent
from satori.element import Text, Image  # 移除不支持的Message
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

main_loop = None
qq_sessions = {}


class QQOutput:
    def __init__(self, account: Account, event: MessageEvent):
        self.account = account
        self.event = event  # 直接保存完整event对象（官方协议要求）

    def send(self, message):
        asyncio.run_coroutine_threadsafe(
            self.account.send(self.event, message),
            main_loop
        )


# ======================
# Flask 接收 main 发送
# ======================
qq_app = Flask("qq_bridge")


@qq_app.route("/send", methods=["POST"])
def on_recv_from_main():
    data = request.get_json()
    user_id = data["user_id"]
    text = data.get("text", "")
    images = data.get("images", [])

    # 改用列表（验证通过格式）
    msg = []
    if text:
        msg.append(Text(text))
    
    for item in images:
        try:
            # 修复Image参数：src（验证通过）
            msg.append(Image(src=item))
        except Exception as e:
            print(f"图片加载失败: {item}, {e}")

    if user_id in qq_sessions:
        qq_sessions[user_id].send(msg)

    return jsonify(ok=1)


# ======================
# QQ 消息监听
# ======================
@satori_app.register_on(EventType.MESSAGE_CREATED)
async def on_qq_message(account: Account, event: MessageEvent):
    user_id = event.user.id
    content = event.message.content.strip()
    # 传入 account + event（不再传channel）
    qq_sessions[user_id] = QQOutput(account, event)

    requests.post(f"http://{MAIN_HOST}:{MAIN_PORT}/submit_task", json={
        "user_id": user_id,
        "content": content,
        "channel_id": "qq",
        "callback_port": QQ_SELF_PORT
    })


async def run_qq_bot():
    await satori_app.run_async()


async def main():
    global main_loop
    main_loop = asyncio.get_running_loop()

    await asyncio.gather(
        run_qq_bot(),
        asyncio.to_thread(
            qq_app.run, host="0.0.0.0", port=QQ_SELF_PORT, debug=CONFIG["flask_debug"]
        )
    )


if __name__ == "__main__":
    asyncio.run(main())