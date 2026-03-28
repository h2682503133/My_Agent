
def parse_syntax(self, raw_text):
    reply = raw_text
    command = ""
    agent_call = None

    lines = raw_text.splitlines()
    for line in lines:
        line = line.strip()

        # 统一把半角、全角冒号都换成全角，保证解析一致
        line = line.replace(":", "：")

        if line.startswith("对话："):
            content = line.replace("对话：", "").strip()
            parts = [p.strip() for p in content.split("|") if p.strip()]

            # 必须 ≥2 段：第1段=目标ID，第2段=内容
            if len(parts) >= 2:
                target_id = parts[0]  # 只取第一个为目标智能体
                send_content = parts[1]  # 第二个为消息内容
                agent_call = {
                    "target_id": target_id,
                    "content": send_content
                }

        elif line.startswith("命令："):
            command = line.replace("命令：", "").strip()

        elif line.startswith("切换："):
            agent_id = line.replace("切换：", "").strip()
            self.set_default_agent(agent_id)
        elif "切换到" in line and "智能体" in line:
            import re
            # 正则提取：切换到(XXX)智能体 → 拿到XXX
            match = re.search(r"切换到(\w+)智能体", line)
            if match:
                agent_id = match.group(1).strip()
                self.set_default_agent(agent_id)

    # 三个分支
    agent_result = ""
    command_result = ""

    if agent_call:
        from core.Agent import Agent
        agent_result = self.call_agent(agent_call["target_id"], agent_call["content"])
        agent_result = Agent.get_agent(agent_call["target_id"],self.session_id).call_agent(self.agent_id, agent_result)

    if command:
        command_result = self._run_shell_command(command)

    final_reply = reply
    if agent_result:
        final_reply += "\n智能体返回：" + agent_result
    if command_result:
        final_reply += "\n执行结果：" + command_result

    return {
        "final_reply": final_reply,
        "reply": reply,
        "command": command,
        "agent_call": agent_call,
        "command_result": command_result,
        "agent_result": agent_result
    }