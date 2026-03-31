import asyncio
from satori import EventType
from satori.event import MessageEvent
from satori.client import Account, App, WebsocketsInfo

async def main():
    app = App(WebsocketsInfo(
        host="127.0.0.1",
        port=5600,    # LLBot 默认端口
        token=""      # 默认为空
    ))

    @app.register_on(EventType.MESSAGE_CREATED)
    async def on_message(account: Account, event: MessageEvent):
        # 打印消息
        print(f"[{event.user.id}] {event.message.content}")

        # 自动回复（真正机器人功能）
        if event.message.content == "hello":
            await account.send(event.channel, "你好！我是机器人！")

        if event.message.content == "测试":
            await account.send(event.channel, "测试成功！运行正常！")

    await app.run_async()

if __name__ == "__main__":
    asyncio.run(main())