from core.logger import chat_log


def parse_syntax(self, task):
    raw_text=task.consume_temp_dialog_output()
    reply = raw_text.strip()
    command = ""
    agent_call = None
    command_result = ""
    agent_result = ""

    lines = raw_text.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 统一冒号
        line = line.replace(":", "：")

        # 调用其他智能体
        if line.startswith("对话："):
            content = line.replace("对话：", "").strip()
            parts = [p.strip() for p in content.split("|") if p.strip()]
            if len(parts) >= 2:
                agent_call = {
                    "target_id": parts[0],
                    "content": parts[1]
                }

        # 执行命令
        elif line.startswith("命令："):
            command = line.replace("命令：", "").strip()

        # 切换智能体
        elif line.startswith("切换："):
            agent_id = line.replace("切换：", "").strip()
            self.set_default_agent(agent_id)
        elif "切换到" in line and "智能体" in line:
            import re
            match = re.search(r"切换到(\w+)智能体", line)
            if match:
                agent_id = match.group(1).strip()
                self.set_default_agent(agent_id)

    # ======================
    # 核心：最多执行一种
    # ======================
    if command:
        command_result = self._run_shell_command(command)
        reply = command_result  # 最终展示命令结果

    elif agent_call:
        from core.Agent.Agent import Agent
        agent_result = self.call_agent(agent_call["target_id"], agent_call["content"])
        agent_result = Agent.get_agent(agent_call["target_id"], self.session_id).call_agent(self.agent_id, agent_result)
        reply = agent_result  # 最终展示智能体返回

    # 统一 return，完全复用
    task.set_temp_dialog_output( {
        "final_reply": reply,
        "reply": raw_text.strip(),
        "command": command,
        "agent_call": agent_call,
        "command_result": command_result,
        "agent_result": agent_result
    })