import json
from pathlib import Path
import requests
import asyncio
import re
from collections import OrderedDict

from core.response_parser import parse_response
from core.syntax_parser import parse_syntax

from core.logger import debug_log, chat_log
from core.Tools import tool_manager
from core.task import Task
from core.user import User

try:
    import openviking as ov
    from openviking.message import TextPart
except:
    # 找不到就模拟，不崩溃
    print("ov不存在")
    ov = None


    class TextPart:
        def __init__(self, text):
            self.text = text

GLOBAL_VIKING_CLIENT = ov.OpenViking(path="./viking_data")
GLOBAL_VIKING_CLIENT.initialize()


class Agent:
    BASE_ROOT_DIR = Path(__file__).parent.parent
    MAX_INSTANCES = 20
    _agent_instances: OrderedDict[str, "Agent"] = OrderedDict()
    default_agent = {}

    parse_response = parse_response
    parse_syntax = parse_syntax

    def __init__(self, agent_id, session_id="my_agent_session"):
        self.agent_id = agent_id
        self.working_dir = self.BASE_ROOT_DIR / "workspace"
        self.config = {}
        self.system_prompt = ""
        self.history = []
        self.session_id = session_id

        self.load_config()
        self.build_system_prompt()

        self.ov_client = GLOBAL_VIKING_CLIENT
        self.ov_session = self.ov_client.session(session_id=f"{self.agent_id}_{self.session_id}")
        self._load_viking_session()

    def _load_viking_session(self):
        print("加载viking")
        try:
            asyncio.run(self.ov_session.load())
            debug_log(f"加载历史会话成功: {self.agent_id}_{self.session_id}")
        except Exception:
            debug_log("创建新会话")

    @classmethod
    def get_agent(cls, agent_id: str, session_id) -> "Agent":
        key = f"{session_id}_{agent_id}"
        if key in cls._agent_instances:
            cls._agent_instances.move_to_end(key)
            return cls._agent_instances[key]

        if len(cls._agent_instances) >= cls.MAX_INSTANCES:
            oldest_key = next(iter(cls._agent_instances))
            del cls._agent_instances[oldest_key]
            debug_log(f"[实例上限] 删除最久未使用: {oldest_key}")

        agent = cls(agent_id, session_id)
        cls._agent_instances[key] = agent
        debug_log(f"{session_id} 新建智能体: {agent_id}")
        return agent

    @classmethod
    def _resolve_default_agent_id(cls, session_id: str) -> str:
        try:
            return cls.default_agent[session_id]
        except (KeyError, TypeError, AttributeError):
            cls.default_agent[session_id] = "talker"
            return "talker"

    @classmethod
    def handle_task(cls, task: Task, user: User) -> dict:
        """核心入口：以 task 作为跨层数据传输体。"""
        agent_id = cls._resolve_default_agent_id(user.session_id)
        target = cls.get_agent(agent_id, user.session_id)

        chat_log(f"{user.session_id}->{target.agent_id}\n{task.content}")
        debug_log(f"[handle_task]{user.session_id}->{target.agent_id}")

        task.status = "running"
        result = target._run_dialogue(caller="user", task=task)

        # 统一记录会话（用户原始输入 content 不变）
        target.add_message("user", f"<{user.session_id}>" + task.content)
        target.add_message("assistant", result["agent_reply"])

        task.final_result = result["agent_reply"]
        task.status = "completed"
        return result

    def set_default_agent(self, agent_id):
        Agent.default_agent[self.session_id] = agent_id

    @staticmethod
    def _get_task_input(task: Task) -> str:
        """读取本轮输入：优先取 Task 临时输入，不改 task.content。"""
        temp_input = task.consume_temp_dialog_input()
        if isinstance(temp_input, str):
            return temp_input
        return task.content

    def _run_dialogue(self, caller: str, task: Task) -> dict:
        """
        递归调度对话：
        1) 当前智能体先响应；
        2) 若解析到 对话:B|xxx，则压栈保存 A 当轮输入，并通过 temp_input 将 xxx 传给 B；
        3) B 返回后弹栈，拼接 "<A>历史输入 + <B>回复" 作为 A 的下一轮输入。
        """
        result = self.chat(caller, task)
        agent_call = result.get("agent_called")

        if not agent_call:
            return result

        target_id = agent_call.get("target_id")
        target_input = agent_call.get("content", "")
        if not target_id:
            return result

        # A -> B: 栈仅保存 A 的当轮输入；B 的输入通过 temp_input 透传
        current_input = result.get("dialog_input", "")
        task.push_context(self.agent_id, current_input)
        task.set_temp_dialog_input(target_input)
        child_agent = Agent.get_agent(target_id, self.session_id)
        child_result = child_agent._run_dialogue(caller=self.agent_id, task=task)
        popped = task.pop_context() or {}

        child_reply = child_result.get("agent_reply", "")

        # B -> A: 使用弹栈出的 A 历史输入，与 B 回复拼接后再回调 A
        parent_input = popped.get("input", "")
        stitched_input = f"<{self.agent_id}>{parent_input}\n<{target_id}>{child_reply}"
        task.set_temp_dialog_input(stitched_input)
        back_result = self._run_dialogue(caller=target_id, task=task)
        return back_result

    def get_context_sync(self, query: str):
        try:
            ctx = asyncio.run(self.ov_session.get_context_for_search(query=query))
            messages = []
            for msg in ctx["current_messages"][-16:]:
                content = msg.parts[0].text
                content = re.sub(r'</?think>', '', content).strip()
                if content and '智能体返回：' not in content:
                    messages.append({"role": msg.role, "content": content})

            if messages:
                messages.insert(0, {
                    "role": "system",
                    "content": "以下是你和用户的历史对话记录，请根据上下文继续回答"
                })
            return messages
        except Exception:
            return []

    def add_message(self, role: str, content: str):
        self.ov_session.add_message(role, [TextPart(text=content)])

    def load_config(self):
        config_path = self.BASE_ROOT_DIR / "config" / "agent_list.json"
        with open(config_path, "r", encoding="utf-8") as f:
            all_config = json.load(f)

        if self.agent_id not in all_config:
            raise KeyError(f"未找到智能体配置：{self.agent_id}")

        self.config = all_config[self.agent_id]

    def build_system_prompt(self):
        prompt_dir = self.BASE_ROOT_DIR / "system_prompt" / self.agent_id
        global_setting = self.BASE_ROOT_DIR / "system_prompt" / "GLOBAL_SETTING.md"

        parts = []
        with open(global_setting, "r", encoding="utf-8") as f:
            parts.append(f.read().strip())

        for filename in self.config.get("files", []):
            file_path = prompt_dir / filename
            with open(file_path, "r", encoding="utf-8") as f:
                parts.append(f.read().strip())

        self.system_prompt = "\n\n".join(parts)

    def chat(self, caller, task: Task):
        """对话逻辑改为 task 传输：输入/输出都回写 task。"""
        dialog_input = self._get_task_input(task)
        context = self.get_context_sync(dialog_input)

        messages = [{"role": "system", "content": self.system_prompt}] + context
        messages += [
            {"role": "system", "content": "以下为本次请求对话，请着重于下面部分"},
            {"role": "user", "content": f"<{caller}>" + dialog_input}
        ]

        resp = requests.post(
            self.config["api_url"],
            json={
                "model": self.config["model"],
                "messages": messages,
                "temperature": 0.7,
                "stream": False
            },
            timeout=60
        )
        resp.raise_for_status()

        raw_response = self.parse_response(resp)
        result = self.parse_syntax(raw_response)

        task.memory_log.append(f"{caller}:{dialog_input}")
        task.memory_log.append(f"{self.agent_id}:{result['final_reply']}")
        task.final_result = result["final_reply"]

        chat_log(f"{self.agent_id} 回复:\n {result['final_reply']}")
        return {
            "agent_reply": result["final_reply"],
            "command": result["command"],
            "agent_called": result["agent_call"],
            "dialog_input": dialog_input,
            "raw_response": raw_response
        }

    def call_agent(self, target_agent_id, task: Task):
        dialog_input = self._get_task_input(task)
        chat_log(f"<{self.session_id}>:{self.agent_id}->{target_agent_id}\n" + dialog_input)
        debug_log(f"[agent_call] <{self.session_id}>:{self.agent_id}->{target_agent_id}")
        target_agent = Agent.get_agent(target_agent_id, self.session_id)
        result = target_agent.chat(self.agent_id, task)
        return result["agent_reply"]

    def run_tool(self, tool_name: str, *args, **kwargs):
        return tool_manager.run_tool(tool_name, *args, **kwargs)
