from flask import Flask, request
import requests
import threading
import asyncio
from satori import EventType
from satori.event import MessageEvent
from satori.client import Account, App, WebsocketsInfo

# ==================== 配置 ====================
LLBOT_SATORI_PORT = 5600
BRIDGE_PORT = 20214
AI_SERVER = "http://127.0.0.1:5000"

app = Flask(__name__)
satori_app = App(WebsocketsInfo(
    host="127.0.0.1",
    port=LLBOT_SATORI_PORT,
    token=""
))

bot_account = None

# ==================== 【核心：异步函数里直接回复！】====================
@satori_app.register_on(EventType.MESSAGE_CREATED)
async def on_qq_message(account: Account, event: MessageEvent):
    user_id = event.user.id
    content = event.message.content.strip()
    channel_id = event.channel.id

    if not all([user_id, content, channel_id]):
        return

    print("\n" + "=" * 50)
    print(f"📩 已接收 QQ 消息")
    print(f"👤 QQ 号: {user_id}")
    print(f"💬 内容: {content}")
    print("=" * 50)

    # ====================
    # 直接在这里访问AI！不在线程里！
    # ====================
    try:
        session = requests.Session()
        session.post(f"{AI_SERVER}/do_login", data={"user_id": user_id}, timeout=5)
        resp = session.post(f"{AI_SERVER}/chat", json={"msg": content}, timeout=120)
        reply = resp.json().get("reply", "✅ 收到！")
    except Exception as e:
        reply = "❌ 服务繁忙"
        print("AI错误:", e)

    try:
        # 方案 A：send_message（最稳）
        await account.send_message(event.channel, reply)

        # 方案 B：message_create（最底层，一定发）
        # await account.message_create(event.channel.id, reply)

        print(f"✅ 已发送: {reply}")
    except Exception as e:
        print("❌ 发送失败:", e)


# ==================== WebHook（兼容旧接口）====================
@app.route("/", methods=["POST"])
def webhook_receive():
    return "", 204

# ==================== 启动服务 ====================
def run_flask():
    app.run(host="127.0.0.1", port=BRIDGE_PORT, debug=False, use_reloader=False)

if __name__ == "__main__":
    print("✅ QQ机器人服务启动（LLBot + Satori）")
    print(f"✅ 端口: {LLBOT_SATORI_PORT}")
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(satori_app.run_async())