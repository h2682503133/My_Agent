def parse_syntax(self, raw_text):
    reply = raw_text.strip()
    agent_call = None
    tool_call = None  # ClawHub 工具调用
    agent_result = ""
    tool_result = ""

    lines = raw_text.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 统一冒号
        line = line.replace(":", "：")

        # ==============================
        # 调用其他智能体（保留）
        # ==============================
        if line.startswith("对话："):
            content = line.replace("对话：", "").strip()
            parts = [p.strip() for p in content.split("|") if p.strip()]
            if len(parts) >= 2:
                agent_call = {
                    "target_id": parts[0],
                    "content": parts[1]
                }

        # ==============================
        # ClawHub 标准工具调用（新增）
        # ==============================
        elif line.startswith("工具："):
            content = line.replace("工具：", "").strip()
            parts = [p.strip() for p in content.split("|")]
            if len(parts) >= 1:
                tool_call = {
                    "name": parts[0],
                    "args": parts[1:] if len(parts) > 1 else []
                }

        # ==============================
        # 切换智能体（保留）
        # ==============================
        elif line.startswith("切换："):
            agent_id = line.replace("切换：", "").strip()
            self.set_default_agent(agent_id)
        elif "切换到" in line and "智能体" in line:
            import re
            match = re.search(r"切换到(\w+)智能体", line)
            if match:
                agent_id = match.group(1).strip()
                self.set_default_agent(agent_id)

    # ==============================
    # 执行优先级：工具 > 智能体
    # ==============================
    if tool_call:
        # 执行 ClawHub 工具
        tool_result = self.run_tool(
            tool_call["name"],
            *tool_call["args"]
        )
        reply = tool_result

    elif agent_call:
        from core.Agent import Agent
        agent_result = self.call_agent(agent_call["target_id"], agent_call["content"])
        agent_result = Agent.get_agent(agent_call["target_id"], self.session_id).call_agent(self.agent_id, agent_result)
        reply = agent_result

    # 统一 return，完全复用
    return {
        "final_reply": reply,
        "reply": raw_text.strip(),
        "agent_call": agent_call,
        "tool_call": tool_call,
        "agent_result": agent_result,
        "tool_result": tool_result
    }