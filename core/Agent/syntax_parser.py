from core.logger import chat_log
def clean_ai_thinking(text: str) -> str:
    """彻底清洗 AI 思考内容，防止语法解析误触发"""
    def clean_ai_thinking(text: str) -> str:
        if not text or not isinstance(text, str):
            return ""
    
    # 🔥 核心：只保留 </think> 之后的内容
    if "</think>" in text:
        text = text.split("</think>")[-1]

    return text.strip()


def parse_syntax(self, task):
    raw_text = task.consume_temp_dialog_output()
    raw_text = clean_ai_thinking(raw_text)

    reply = raw_text.strip()
    command = ""
    agent_call = None
    tool_call = None  # 新增:工具调用结构

    lines = raw_text.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 统一冒号
        line = line.replace("：", ":")

        # 调用其他智能体
        if "对话:" in line:
            # 切割掉 "对话:" 之前的所有内容，只保留后面的
            idx = line.find("对话:")
            line = line[idx:] 

            # 你原来的逻辑不变
            content = line.replace("对话:", "").strip()
            parts = [p.strip() for p in content.split("|") if p.strip()]
            if len(parts) >= 2:
                agent_call = {
                    "target_id": parts[0],
                    "content": parts[1]
                }

        # 工具调用（格式:工具名|参数1|参数2...）
        elif "工具调用:" in line:
            # 自动去掉智能体加的「工具调用:」前缀，兼容两种格式
            line = line.replace("工具调用:", "").strip()

            memory = task.consume_temp_dialog_input()
            memory = memory if memory else "本条记录因不知名原因丢失"
            memory = memory + "\n调用了工具:" + line
            task.tool_log.append("调用了工具:" + line)
            task.push_context(self, memory)
            # 剩余逻辑完全不变，解析标准工具格式
            parts = line.split("|")
            tool_name = parts[0].strip()
            args = [p.strip() for p in parts[1:] if p.strip()]
            tool_call = {
                "tool": tool_name,
                "args": args
            }

        # 切换智能体
        elif line.startswith("切换:"):
            agent_id = line.replace("切换:", "").strip()
            self.set_default_agent(agent_id)
        elif "切换到" in line and "智能体" in line:
            import re
            match = re.search(r"切换到(\w+)智能体", line)
            if match:
                agent_id = match.group(1).strip()
                self.set_default_agent(agent_id)

    # 只返回结构化数据，不执行
    task.set_temp_dialog_output({
        "final_reply": reply,
        "reply": raw_text.strip(),
        "tool_call": tool_call,    # 工具:名称+参数
        "agent_call": agent_call,  # 对话:目标+内容
    })