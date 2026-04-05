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
            result= f"{task.target.id}的请求：\n{request},\n收到来自{task.caller}的回复：\n{task.consume_temp_dialog_output()}"
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
    def send(self,task):
        """单轮对话主流程（支持自调用）"""
        content=task.consume_temp_dialog_input()
        # 2. 同步获取上下文（无异步！）
        context = self.get_context_sync(content)

        # 1. 添加用户输入到历史
        #self.history.append({"role": "user", "content": user_input})
        # messages = [{"role": "system", "content": self.system_prompt}] + history
        messages = [{"role": "system", "content": self.system_prompt}] + context
        messages += [{"role": "system", "content": "以下为本次请求对话，请着重于下面部分"}] + [{"role": "user", "content":f"<{task.caller.id}>"+content}]
        # 2. 调用大模型
        api_url = self.config["api_url"]
        model = self.config["model"]


        resp = requests.post(
            api_url,
            json={
                "model": model,
                "messages": messages,
                "temperature": 0.7,
                "stream": False  # 强制关闭流式输出，保证返回完整JSON
            },
            timeout=60
        )
        resp.raise_for_status()
        task.set_temp_dialog_output(resp)
        self.parse_response(task)
        self.parse_syntax(task)
        result=task.consume_temp_dialog_output()

        #此处留出 可用于其他逻辑

        chat_log(f"{self.id} 回复:\n {result['final_reply']}")
        task.set_temp_dialog_output(result["final_reply"])
        task.caller=self
        '''
        # 6. 返回结构化结果
        return {
            "agent_reply": result["final_reply"],
            "command": result["command"],
            "agent_called": result["agent_call"],
        }'''

    # ==================== 智能体调用 ====================
    def call_agent(self, target_agent_id, content):
        chat_log(f"<{self.session_id}>:{self.id}->{target_agent_id}\n"+content)
        debug_log(f"[agent_call] <{self.session_id}>:{self.id}->{target_agent_id}")
        """调用另一个智能体，内部会触发 chat()，支持自调用"""
        target_agent = Agent.get_agent(target_agent_id,self.session_id)
        result = target_agent.chat(self.id,content)
        return result["agent_reply"]

    # ==================== 通用命令执行（CMD/Codex） ====================
    def _run_shell_command(self, command):
        """执行系统命令，依赖静态主路径，源代码完全保留"""
        debug_log(f"[command]: {self.id} {command}")
        try:
            result = subprocess.run(
                command,
                cwd=self.BASE_ROOT_DIR / "workspace",
                shell=True,
                capture_output=True,
                text=False,  # 重要：关闭文本模式
            )
            def safe_decode(data):
                try:
                    return data.decode("utf-8").strip()
                except:
                    return data.decode("gbk", errors="replace").strip()

            stdout = safe_decode(result.stdout)
            stderr = safe_decode(result.stderr)
            output = (stdout + "\n" + stderr).strip()

            if not output:
                if result.returncode == 0:
                    return "命令执行成功"
                else:
                    return "命令执行失败"

            return output

        except Exception as e:
            return f"执行失败：{str(e)}"