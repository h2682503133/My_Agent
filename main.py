from core.Agent import Agent

# 启动主智能体
if __name__ == "__main__":
    main_agent = Agent("main")
    while True:
        user_input = input("你：")
        result = main_agent.chat(user_input)
        print("智能体：", result["agent_reply"])