import asyncio
import websockets
import json

async def test_client():
    uri = "ws://127.0.0.1:5211"
    async with websockets.connect(uri) as websocket:
        # 发送 user_id 认证
        await websocket.send(json.dumps({"user_id": "1001"}))
        print("已发送认证，等待消息...")
        # 等待服务端推送消息
        while True:
            message = await websocket.recv()
            print(f"收到消息: {message}")

asyncio.run(test_client())