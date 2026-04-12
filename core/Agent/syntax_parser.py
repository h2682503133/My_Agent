from core.logger import chat_log
from datetime import datetime
import re

def clean_ai_thinking(text: str) -> str:
    """彻底清洗 AI 思考内容，防止语法解析误触发"""
    if not text or not isinstance(text, str):
        return ""
    # 只保留 </think> 之后的内容
    if "</think>" in text:
        text = text.split("</think>")[-1]
    return text.strip()

def to_timestamp(time_str: str) -> float:
    """时间字符串 2025-12-31 23:59:59 转时间戳"""
    dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
    return dt.timestamp()

def parse_syntax(self, task):
    raw_text = task.consume_temp_dialog_output()
    raw_text = clean_ai_thinking(raw_text)
    full_text = raw_text.strip()

    reply = full_text
    command = ""
    agent_call = None
    tool_call = None
    question = None
    timer_task = None  # 🔥 新增：定时任务结构

    # ==============================
    # 全局替换全角符号，统一格式
    # ==============================
    full_text = full_text.replace("：", ":")

    # ==============================
    # 1. 提取：对话:target|content
    # ==============================
    match_agent = re.search(r"对话:(.*?)\|(.*)", full_text)
    if match_agent:
        target_id = match_agent.group(1).strip()
        content = match_agent.group(2).strip()
        agent_call = {
            "target_id": target_id,
            "content": content
        }

    # ==============================
    # 2. 提取：工具调用:xxx|xxx|xxx
    # ==============================
    match_tool = re.search(r"工具调用:(.*)", full_text)
    if match_tool:
        line = match_tool.group(1).strip()
        memory = task.consume_temp_dialog_input() or "本条记录因不知名原因丢失"
        memory += "\n调用了工具:" + line
        task.tool_log.append("调用了工具:" + line)
        task.push_context(self, memory)

        parts = line.split("|")
        tool_name = parts[0].strip()
        args = [p.strip() for p in parts[1:] if p.strip()]
        tool_call = {
            "tool": tool_name,
            "args": args
        }

    # ==============================
    # 3. 提取：询问:xxx
    # ==============================
    match_question = re.search(r"询问:(.*)", full_text)
    if match_question:
        question = match_question.group(1).strip()

    # ==============================
    # 4. 提取：切换:xxx
    # ==============================
    match_switch1 = re.search(r"切换:(.*)", full_text)
    if match_switch1:
        agent_id = match_switch1.group(1).strip()
        self.set_default_agent(agent_id)

    match_switch2 = re.search(r"切换到(\w+)智能体", full_text)
    if match_switch2:
        agent_id = match_switch2.group(1).strip()
        self.set_default_agent(agent_id)

    # ==============================
    # 🔥 5. 新增：定时任务:类型|时间|内容
    # ==============================
    match_timer = re.search(r"定时任务:(.*?)\|(.*?)\|(.*)", full_text)
    if match_timer:
        task_type = match_timer.group(1).strip()
        time_str = match_timer.group(2).strip()
        content = match_timer.group(3).strip()

        try:
            trigger_ts = to_timestamp(time_str)
            timer_task = {
                "task_type": task_type,
                "time_str": time_str,
                "trigger_timestamp": trigger_ts,
                "content": content
            }
        except:
            pass

    # ==============================
    # 返回结构化数据（不变）
    # ==============================
    task.set_temp_dialog_output({
        "final_reply": reply,
        "reply": full_text,
        "tool_call": tool_call,
        "agent_call": agent_call,
        "question": question,
        "timer_task": timer_task  
    })