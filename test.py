import os

# 第一步：必须先指定配置文件（你自己的路径）
os.environ["OPENVIKING_CONFIG_FILE"] = r"D:\DuanKou\tools\My_Agent\ov.conf"

# 第二步：导入官方库
import openviking as ov

# 第三步：官方初始化（完全按你给的示例写）
print("正在初始化 OpenViking...")
client = ov.OpenViking(path="./test_data")
client.initialize()
print("✅ 初始化成功！")

# 第四步：创建官方会话
print("创建会话...")
session = client.create_session()
print(f"✅ 会话创建成功，ID: {session.id}")

# 第五步：添加消息
print("添加测试对话...")
client.add_message(session.id, "user", "你好")
client.add_message(session.id, "assistant", "你好！我是智能助手！")
client.commit_session(session.id)
print("✅ 对话保存成功！")

# 第六步：读取历史消息
print("\n===== 读取历史对话 =====")
messages = client.get_messages(session.id)
for msg in messages:
    print(f"{msg['role']}: {msg['content']}")

# 结束
print("\n🎉 OpenViking 测试全部通过！能存、能读、正常工作！")
client.close()