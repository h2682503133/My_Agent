def parse_syntax(self, raw_text):
    """
    语法解析只负责“提取指令”，不直接执行跨智能体调用。
    这样 Agent 可继续以 Task 作为统一传输体。
    """
    reply = raw_text.strip()
    agent_call = None
    tool_call = None
    tool_result = ""

    lines = raw_text.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue

        line = line.replace(":", "：")

        # 对话：<target_agent>|<content>
        if line.startswith("对话："):
            content = line.replace("对话：", "", 1).strip()
            parts = [p.strip() for p in content.split("|") if p.strip()]
            if parts:
                agent_call = {
                    "target_id": parts[0],
                    "content": parts[1] if len(parts) >= 2 else ""
                }
                if len(parts) >= 2:
                    # 兼容旧格式；Task 模式下由 Agent 决定是否覆盖 task.content
                    reply = parts[1]

        # 工具：<tool_name>|arg1|arg2
        elif line.startswith("工具："):
            content = line.replace("工具：", "", 1).strip()
            parts = [p.strip() for p in content.split("|")]
            if parts and parts[0]:
                tool_call = {
                    "name": parts[0],
                    "args": parts[1:] if len(parts) > 1 else []
                }

        # 切换：<agent_id>
        elif line.startswith("切换："):
            agent_id = line.replace("切换：", "", 1).strip()
            if agent_id:
                self.set_default_agent(agent_id)

        elif "切换到" in line and "智能体" in line:
            import re
            match = re.search(r"切换到(\w+)智能体", line)
            if match:
                self.set_default_agent(match.group(1).strip())

    if tool_call:
        tool_result = self.run_tool(tool_call["name"], *tool_call["args"])
        reply = str(tool_result)

    return {
        "final_reply": reply,
        "reply": raw_text.strip(),
        # Task 模式下交给 Agent.handle_task 继续调度
        "agent_call": agent_call,
        "tool_call": tool_call,
        "tool_result": tool_result,
        # 兼容 Agent.chat 当前返回结构
        "command": tool_call,
    }
