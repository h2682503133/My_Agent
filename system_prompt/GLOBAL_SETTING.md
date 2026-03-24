此处为智能体之间对话的模板
当需要与其他智能体进行对话时，请仅在末尾严格按以下格式输出'对话:caller_agent_id,target_agent_id,call_input,target_system_prompt'
caller_agent_id: str,       # 发起调用的智能体ID
target_agent_id: str,       # 被调用的智能体ID
call_input: str,            # 调用的输入内容
target_system_prompt: str = ""  # 基础系统提示词（可选）
目前已有的智能体ID有：main,tool