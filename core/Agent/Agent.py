import json
import subprocess
from pathlib import Path
import requests
import asyncio
import re
from collections import OrderedDict
#from typing_inspection.typing_objects import target
from core.Task.Task import Task
from core.Agent.response_parser import parse_response
from core.Agent.syntax_parser import parse_syntax
import openviking as ov
from openviking.message import TextPart
from core.Agent.Tool_manager import tool_manager  # 你的工具管理器
from core.Agent.Skill_manager import skill_manager

from core.Task.task_creator import send_to_channel
from core.logger import debug_log,chat_log

GLOBAL_VIKING_CLIENT = ov.OpenViking(path="./viking_data")
GLOBAL_VIKING_CLIENT.initialize()

class Agent:
    # 静态变量：全局主程序根目录（所有命令执行依赖此路径）
    BASE_ROOT_DIR = Path(__file__).parent.parent.parent
    MAX_INSTANCES = 20
    _agent_instances: OrderedDict[str, "Agent"] = OrderedDict()
    default_agent={}

    parse_response = parse_response
    parse_syntax = parse_syntax

    def __init__(self, agent_id, session_id="my_agent_session"):
        # 智能体唯一标识
        self.id = agent_id

        # 智能体工作目录（默认可修改）
        self.working_dir = self.BASE_ROOT_DIR / "workspace"
        print(self.BASE_ROOT_DIR)

        # 智能体配置（字典格式）
        self.config = {}

        # 系统提示词
        self.system_prompt = ""

        # 对话历史记忆
        self.history = []

        self.session_id = session_id
        # 初始化加载
        self.load_config()
        self.build_system_prompt()

        self.ov_client = GLOBAL_VIKING_CLIENT
        self.ov_session = self.ov_client.session(session_id=f"{self.id}_{self.session_id}")

        self._load_viking_session()

    def _load_viking_session(self):
        print("加载viking")
        try:
            # 单独开循环执行异步load，不影响主程序
            asyncio.run(self.ov_session.load())
            debug_log(f"加载历史会话成功: {self.id}_{self.session_id}")
        except:
            debug_log("创建新会话")

    @classmethod
    def process_task(cls,task):
        call_agent=task.target
        call_agent.send(task)
        result=None
        while len(task.agent_context)>0:
            debug_log(f"此处为弹回复栈，当前栈长{len(task.agent_context)}")
            context = task.pop_context()  # 出栈，拿到字典
            task.target = context["from"]
            request = context["input"]
            result= [task.target.id,request,task.caller.id,task.consume_temp_dialog_output()]
            task.set_temp_dialog_input(result)
            task.target.send(task)
        #此处为总结预留
        call_agent.add_message("user", f"<{task.user.session_id}>" + task.content)
        call_agent.add_message("assistant", result)

    @classmethod
    def get_agent(cls, agent_id: str, session_id) -> "Agent":
        """
        智能体实例管理：
        1. 传入智能体ID + session_id
        2. 存在则直接返回实例
        3. 不存在则新建
        4. 超过上限 → 删除最旧的实例
        """
        key = f"{session_id}_{agent_id}"

        # 存在就直接返回
        if key in cls._agent_instances:
            # 刷新到最新位置
            cls._agent_instances.move_to_end(key)
            return cls._agent_instances[key]

        # 超过最大数量，删除最旧的
        if len(cls._agent_instances) >= cls.MAX_INSTANCES:
            # 获取字典第一个（最旧）键
            oldest_key = next(iter(cls._agent_instances))
            del cls._agent_instances[oldest_key]
            debug_log(f"[实例上限] 删除最久未使用: {oldest_key}")

        # 新建实例并存储
        agent = cls(agent_id, session_id)
        cls._agent_instances[key] = agent
        debug_log(f"{session_id} 新建智能体: {agent_id}")

        return agent

    @classmethod
    def user_chat(cls,task:Task):
        try:
            agent_id = Agent.default_agent[task.user.session_id]
        except (KeyError, TypeError, AttributeError):
            agent_id = "main"
            Agent.default_agent[task.user.session_id]="main"
        target = Agent.get_agent(agent_id,task.user.session_id)
        task.target=target
        chat_log(f"{task.user.session_id}->{target.id}\n{task.content}")
        debug_log(f"[user_chat]{task.user.session_id}->{target.id}")
        return cls.process_task(task)

    def set_default_agent(self,agent_id):
        Agent.default_agent[self.session_id]=agent_id

    def get_context_sync(self, query: str):
        """同步版本：从当前会话获取上下文"""
        try:
            import asyncio
            ctx = asyncio.run(self.ov_session.get_context_for_search(query=query))
            messages = []
            # 仅保留最近16条 + 清理脏数据
            for msg in ctx["current_messages"][-16:]:
                content = msg.parts[0].text
                content = re.sub(r'</?think>', '', content).strip()
                if content and '智能体返回：' not in content:
                    messages.append({"role": msg.role, "content": content})

            # ✅【正确做法】在最前面插入一条系统提示，告诉模型这是历史记录
            if messages:
                messages.insert(0, {
                    "role": "system",
                    "content": "以下是你和用户的历史对话记录，请根据上下文继续回答"
                })

            return messages  # 👈 保持返回数组，模型完全识别
        except:
            return []

    # ========== 你原样的添加消息函数（完全不动） ==========
    def add_message(self, role: str, content: str):
        self.ov_session.add_message(role, [TextPart(text=content)])

    def load_config(self):
        """加载当前智能体配置（源代码完全保留）"""
        config_path = self.BASE_ROOT_DIR / "config" / "agent_list.json"
        with open(config_path, "r", encoding="utf-8") as f:
            all_config = json.load(f)

        if self.id not in all_config:
            raise KeyError(f"未找到智能体配置：{self.id}")

        self.config = all_config[self.id]

    def build_system_prompt(self):
        """构建系统提示词（源代码完全保留）"""
        prompt_dir = self.BASE_ROOT_DIR / "system_prompt" / self.id
        global_setting = self.BASE_ROOT_DIR / "system_prompt" /"GLOBAL_SETTING.md"

        parts = []

        # 读取全局设置
        with open(global_setting, "r", encoding="utf-8") as f:
            parts.append(f.read().strip())

        # 读取智能体专属文件
        for filename in self.config.get("files", []):
            file_path = prompt_dir / filename
            with open(file_path, "r", encoding="utf-8") as f:
                parts.append(f.read().strip())

        self.system_prompt = "\n\n".join(parts)

    # ==================== 核心对话流程 ====================
    def send(self, task):
        """单轮对话主流程（支持自调用）"""
        content = task.consume_temp_dialog_input()
        if not isinstance(content, str):
            # 非字符串/None → 按你指定格式拼接
            if content is not None:
                if content[0]==content[2]:
                    content=f"\n{content[1]}，\n结果{content[3]}"
                else:
                    content = f"{content[0]}的请求：\n{content[1]},\n收到来自{content[2]}的回复：\n{content[3]}"
            else:
                content = "当你看到这条消息时，意味着出现某些问题导致输入为空了"
        task.set_temp_dialog_input(content)
        chat_log(f"{self.id}收到:\n{content}")
        # 2. 同步获取上下文
        context = self.get_context_sync(content)

        # 1. 添加用户输入到历史
        messages = [{"role": "system", "content": self.system_prompt}] + context
        messages += [{"role": "system", "content": "以下为本次请求对话，请着重于下面部分\n下面是该任务用户原始请求"}] + [
            {"role": "user", "content": f"<{task.user.id}>" + task.content},
            {"role": "system", "content": "以下为本次单轮对话内容"},
            {"role": "user", "content": f"<{task.caller.id}>" + content}]
        # 2. 调用大模型
        api_url = self.config["api_url"]
        model = self.config["model"]

        try:
            resp = requests.post(
                api_url,
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": 0.7,
                    "stream": False  # 强制关闭流式输出，保证返回完整JSON
                },
                timeout=600
            )
            resp.raise_for_status()
            task.set_temp_dialog_output(resp)
            self.parse_response(task)
            self.parse_syntax(task)
            result = task.consume_temp_dialog_output()
        # 捕获模型超时/网络错误
        except Exception as e:
            # 🔥 兜底：返回错误结果，防止后续取键崩溃
            result = {
                "final_reply": f"【模型请求失败】{str(e)}",
                "tool_call": None,
                "agent_call": None
            }

        # ======================
        # 你的原有逻辑（完全保留）
        # ======================
        chat_log(f"{self.id} 回复:\n {result['final_reply']}")
        task.set_temp_dialog_output(result["final_reply"])
        task.caller = self
        # ======================
        # 核心：最多执行一种操作
        # ======================
        if result["tool_call"]:
            task.set_temp_dialog_output(result["tool_call"])

            self._run_shell_command(task)

        elif result["agent_call"]:
            agent_call = result["agent_call"]
            task.set_temp_dialog_input(agent_call["content"])
            self.call_agent(agent_call["target_id"], task)

    # ==================== 智能体调用 ====================
    def call_agent(self, target_agent_id, task:Task):
        content=task.consume_temp_dialog_input()
        task.push_context(self,content)
        chat_log(f"<{self.session_id}>:{self.id}->{target_agent_id}\n{content}")
        debug_log(f"[agent_call] <{self.session_id}>:{self.id}->{target_agent_id}")
        """调用另一个智能体，内部会触发 chat()，支持自调用"""
        task.target = Agent.get_agent(target_agent_id,self.session_id)
        task.caller = self
        task.set_temp_dialog_input(content)
        task.target.send(task)


    def _run_shell_command(self, task):
        # 从解析结果中获取工具调用
        tool_call = task.consume_temp_dialog_output()

        if not tool_call:
            output = "没有可执行的工具指令"
            task.set_temp_dialog_output(output)
            return

        tool_name = tool_call["tool"]
        args = tool_call["args"]
        debug_log(f"[工具执行] {self.id} → {tool_name} {args}")

        task.caller = self
        try:
            if tool_name in tool_manager.tools:
                # 1. 优先执行原生工具（shell/file-read/codex等）
                output = tool_manager.run_tool(tool_name, *args)
            else:
                # 2. 无原生工具 → 自动执行 OpenViking 技能（ClawHub下载的技能）
                output = skill_manager.run_skill(tool_name, *args)

        except Exception as e:
            output = f"工具执行失败：{str(e)}"

        # 把结果写回任务
        task.set_temp_dialog_output(output)
        chat_log(f"{self.id} 执行工具 {tool_name}:\n结果: {output}")
        debug_log(f"[工具结果] {self.id} {output}")