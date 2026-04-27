import asyncio
import websockets
import json
from flask import Flask, request, jsonify
import threading

# ========================
# 按你要求的端口顺序
# ========================
HTTP_PORT = 5211   # 你指定：接收 webview 转发
WS_PORT   = 5212   # 你指定：给鸿蒙连接

HOST = "0.0.0.0"
connected_users = {}
loop = None

# ========================
# WebSocket：给鸿蒙（5212）+ 新增心跳回执
# ========================
async def handle_client(websocket):
    global loop
    loop = asyncio.get_event_loop()
    user_id = None
    try:
        # 先正常维持 WS 长连接循环，不阻塞握手
        async for data in websocket:
            try:
                obj = json.loads(data)
                
                # ==============================================
                # 🔥 唯一新增：接收鸿蒙心跳 + 自动返回回执（双向保活）
                # ==============================================
                if obj.get("type") == "heartbeat":
                    # 直接回传心跳确认包，解决长时间断连
                    await websocket.send(json.dumps({"type": "heartbeat_ack"}, ensure_ascii=False))
                    continue

                # 原有用户绑定逻辑（完全不动）
                user_id = obj.get("user_id")
                if user_id:
                    connected_users[user_id] = websocket
                    print(f"[5212] 鸿蒙 {user_id} 已连接")
            except Exception:
                continue
    except Exception as e:
        print(f"断开: {e}")
    finally:
        if user_id and user_id in connected_users:
            del connected_users[user_id]

# ========================
# 发给鸿蒙（原有逻辑不变）
# ========================
async def send_to_harmony(user_id, data):
    if user_id in connected_users:
        try:
            await connected_users[user_id].send(json.dumps(data, ensure_ascii=False))
        except:
            pass

# ========================
# HTTP：接收 webview 转发（5211）
# ========================
app = Flask("forward")

@app.route("/forward", methods=["POST"])
def forward():
    data = request.json
    user_id = data.get("user_id")
    if user_id and loop:
        asyncio.run_coroutine_threadsafe(send_to_harmony(user_id, data), loop)
    return jsonify(ok=1)

def run_http_server():
    app.run(host="127.0.0.1", port=HTTP_PORT)

# ========================
# 启动服务
# ========================
async def main():
    threading.Thread(target=run_http_server, daemon=True).start()
    async with websockets.serve(handle_client, HOST, WS_PORT):
        print(f"✅ 5211(转发) + 5212(鸿蒙) 启动成功")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())