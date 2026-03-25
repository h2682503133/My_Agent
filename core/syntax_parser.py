def parse_syntax(self, raw_text):
    reply = raw_text
    command = ""
    agent_call = None

    lines = raw_text.splitlines()
    for line in lines:
        line = line.strip()

        # 统一把半角、全角冒号都换成全角，保证解析一致
        line = line.replace(":", "：")
        line = line.replace("，", ",")

        if line.startswith("对话："):
            content = line.replace("对话：", "").strip()
            parts = [p.strip() for p in content.split(",") if p.strip()]

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

    # 三个分支
    agent_result = ""
    command_result = ""

    if agent_call:
        agent_result = self.call_agent(agent_call["target_id"], agent_call["content"])

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