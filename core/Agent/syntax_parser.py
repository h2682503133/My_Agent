from core.logger import chat_log

def parse_syntax(self, task):
    raw_text = task.consume_temp_dialog_output()
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
        if line.startswith("对话:"):
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
            memory = memory + "\n调用了工具:" + line
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