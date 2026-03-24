# -*- coding: utf-8 -*-
from pathlib import Path
import json
import requests
import subprocess
import os
def load_agent_config(agent_id: str) -> dict:
    """
    读取目标智能体的配置（API地址、模型名等）
    Args:
        agent_id: 目标智能体ID
    Returns:
        目标智能体配置字典
    Raises:
        FileNotFoundError: 当agent_list.json不存在时抛出
        KeyError: 当目标agent_id不在配置文件中时抛出
    """
    project_root = Path(__file__).parent.parent
    agent_config_path = project_root / "system_prompt" / "agent_list.json"

    if not agent_config_path.exists():
        raise FileNotFoundError(
            f"智能体配置文件不存在！请先创建 {agent_config_path} 文件，"
            "并配置目标智能体的API地址和模型名。"
        )

    # 读取配置文件
    with open(agent_config_path, "r", encoding="utf-8") as f:
        all_config = json.load(f)

    if agent_id not in all_config:
        raise KeyError(
            f"智能体ID「{agent_id}」不存在！配置文件中可用的智能体ID：{list(all_config.keys())}"
        )

    return all_config[agent_id]

def load_agent_md_file(agent_id: str, file_name: str) -> str:
    """
    读取目标智能体的MD配置文件（SOUL.md/TOOL.md）
    Args:
        agent_id: 目标智能体ID
        file_name: 要读取的文件名（SOUL.md/TOOL.md）
    Returns:
        文件内容字符串（文件不存在则抛错）
    Raises:
        FileNotFoundError: 文件不存在时抛出
    """
    # 智能体MD文件路径：system_prompt/agent_details/{agent_id}/{file_name}
    project_root = Path(__file__).parent.parent
    md_file_path = project_root / "system_prompt" / agent_id / file_name

    if not md_file_path.exists():
        raise FileNotFoundError(
            f"智能体「{agent_id}」的{file_name}文件不存在！请创建：{md_file_path}"
        )

    with open(md_file_path, "r", encoding="utf-8") as f:
        return f.read().strip()
def agent_call_agent(
    caller_agent_id: str,       # 发起调用的智能体ID
    target_agent_id: str,       # 被调用的智能体ID
    call_input: str,            # 调用的输入内容
    target_system_prompt: str = ""  # 基础系统提示词（可选）
) -> dict:
    """
    智能体调用其他智能体的封装函数（自动加载被调用方的SOUL.md/TOOL.md）
    Args:
        caller_agent_id: 发起调用的智能体ID（如 main_agent）
        target_agent_id: 被调用的智能体ID（如 sub_agent/tool_agent）
        call_input: 调用的输入内容（如 "帮我解答Python问题"）
        target_system_prompt: 给目标智能体的基础系统提示词（可选）
    Returns:
        同single_round_agent_chat的返回结果（新增caller/target agent ID）
    Raises:
        FileNotFoundError: 配置文件/MD文件不存在时抛出
        KeyError: 目标agent_id不存在时抛出
    """
    # 1. 读取目标智能体的核心配置（API/模型）
    target_agent_config = load_agent_config(target_agent_id)
    api_url = target_agent_config["api_url"]
    model_name = target_agent_config["model"]

    # 2. 读取目标智能体的SOUL.md和TOOL.md
    try:
        soul_content = load_agent_md_file(target_agent_id, "SOUL.md")
        tool_content = load_agent_md_file(target_agent_id, "TOOL.md")
    except FileNotFoundError as e:
        raise FileNotFoundError(f"加载被调用方配置失败：{e}")

    # 3. 拼接完整的系统提示词（基础提示词 + SOUL + TOOL + 调用规则）
    full_system_prompt = f"""
{target_system_prompt}

### 核心人格（SOUL）
{soul_content}

### 工具能力（TOOL）
{tool_content}

### 调用规则
1. 你是{target_agent_id}，当前被{caller_agent_id}调用；
2. 严格遵守上述人格和工具能力要求处理输入内容；
3. 仅回复与调用内容相关的信息，不闲聊。
"""

    # 清理空行，避免提示词冗余
    full_system_prompt = "\n".join([line.strip() for line in full_system_prompt.split("\n") if line.strip()])

    # 4. 复用单轮对话函数，调用目标智能体
    call_result = single_round_agent_chat(
        api_url=api_url,
        model_name=model_name,
        user_input=call_input,
        system_prompt=full_system_prompt
    )

    # 5. 补充调用元信息
    call_result["caller_agent_id"] = caller_agent_id
    call_result["target_agent_id"] = target_agent_id

    return call_result
def single_round_agent_chat(
    api_url: str,
    model_name: str,
    user_input: str,
    system_prompt: str = ""
) -> dict:
    """
    智能体单轮对话全流程函数（含命令执行）
    Args:
        api_url: Ollama API地址（如 http://127.0.0.1:11434/api/chat）
        model_name: 模型名称（如 MFDoom/deepseek-r1-tool-calling:14b）
        user_input: 用户输入内容
        system_prompt: 系统提示词（可选，不传则为空）
    Returns:
        对话结果字典：{
            "agent_reply": 智能体回复内容,
            "command_executed": 是否执行了命令（True/False）,
            "command": 执行的命令（无则为空）,
            "command_result": 命令执行结果（无则为空）,
            "error": 错误信息（无则为空）
        }
    """
    # 初始化返回结果
    result = {
        "agent_reply": "",
        "command_executed": False,
        "command": "",
        "command_result": "",
        "error": ""
    }

    # 1. 构造对话上下文
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_input})

    try:
        # 2. 调用模型
        response = requests.post(
            api_url,
            json={
                "model": model_name,
                "messages": messages,
                "stream": False
            },
            timeout=60
        )
        response.raise_for_status()  # 捕获HTTP错误
        reply = response.json()["message"]["content"]
        result["agent_reply"] = reply

        # 3. 检测并执行命令（兼容全角/半角冒号）
        for cmd_flag in ["命令：", "命令:"]:
            if cmd_flag in reply:
                command = reply.strip().split(cmd_flag)[1].strip()
                result["command"] = command
                # 执行命令（解决中文乱码）
                print(command)
                proc = subprocess.Popen(
                    f"chcp 65001 >nul && {command}",
                    shell=True,
                    text=True,
                    encoding="utf-8",
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                cmd_out, cmd_err = proc.communicate()
                cmd_result=cmd_out + cmd_err
                print(f"\n{cmd_result}\n")
                result["command_result"] = cmd_result if cmd_result else "命令执行无输出"
                result["command_executed"] = True
                break
        if "对话:"in reply:
            params = reply.strip().split("对话:")[1].strip().split(",")
            print(result["agent_reply"])
            params.append("")
            result=agent_call_agent(params[0],params[1],params[2],params[3])
            print(result["target_agent_id"]+"->"+result["caller_agent_id"])
            print(result["agent_reply"])
            print(result["command_result"])
            result=single_round_agent_chat(api_url,model_name,result["target_agent_id"]+"回复为"+result["agent_reply"]+"指令执行结果为"+result["command_result"],system_prompt)

    except Exception as e:
        result["error"] = str(e)

    return result