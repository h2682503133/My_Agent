from core.agent_chat import single_round_agent_chat
from pathlib import Path

system_prompt_path = str(Path(__file__).parent/"system_prompt")
if __name__ == "__main__":
    # 外部传参示例
    API_URL = "http://127.0.0.1:11434/api/chat"
    MODEL = "qwen3-vl:235b-cloud"
    
    AgentID = "main"
    SystemPrompts=["SOUL.md","IDENTITY.md"]
    SYSTEM_PROMPT=""
    with open(f"{system_prompt_path}\\GLOBAL_SETTING.md","r", encoding="utf-8") as f:
        SYSTEM_PROMPT += f.read()
    for Prompt in SystemPrompts:
        with open(f"{system_prompt_path}\\{AgentID}\\{Prompt}","r", encoding="utf-8") as f:
            SYSTEM_PROMPT += f.read()
    Memory=""


    READER_API_URL = "http://127.0.0.1:11434/api/chat"
    READER_MODEL = "MFDoom/deepseek-r1-tool-calling:14b"
    READER_AgentID = "reader"
    with open(f"{system_prompt_path}\\{READER_AgentID}\\SOUL.md","r", encoding="utf-8") as f:
        READER_SYSTEM_PROMPT = f.read()
    while True:
        USER_INPUT = input("请输入：")
        INPUT="历史记录为"+Memory+"用户新发送的对话为"+USER_INPUT
        # 调用单轮对话函数
        chat_result = single_round_agent_chat(
            api_url=API_URL,
            model_name=MODEL,
            user_input=INPUT,
            system_prompt=SYSTEM_PROMPT
        )

        # 打印结果
        print("===== 单轮对话结果 =====")
        print(f"智能体回复：{chat_result['agent_reply']}")
        if chat_result["command_executed"]:
            print(f"执行命令：{chat_result['command']}")
            print(f"命令结果：{chat_result['command_result']}")
        if chat_result["error"]:
            print(f"错误信息：{chat_result['error']}")


        Memory=Memory+USER_INPUT+chat_result['agent_reply']

        Memory = single_round_agent_chat(
            api_url=READER_API_URL,
            model_name=READER_MODEL,
            user_input=Memory,
            system_prompt=READER_SYSTEM_PROMPT
        )['agent_reply']

        print("\n总结记忆为\n",Memory)