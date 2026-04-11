import json
import subprocess
from pathlib import Path
import time
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
    def process_task(cls,task:Task):
        print(f"{task.user.id}的任务正被处理")
        result=[task.user.id,task.content,"unknown","如果你看到这条信息，说明输出因某些原因丢失了"]
        if len(task.agent_context)==1:
            cls.first_call(task)
            task.default_agent=task.target
            task.default_agent.send(task)
        while len(task.agent_context)>0 and task.status=="running":
            time.sleep(2)
            debug_log(f"此处为弹回复栈，当前栈长{len(task.agent_context)}")
            context = task.pop_context()  # 出栈，拿到字典
            task.target = context["from"]
            request = context["input"]
            result= [task.target.id,request,task.caller.id,task.consume_temp_dialog_output() or "因不知名原因输出已丢失"]
            task.set_temp_dialog_input(result)
            task.target.send(task)

        #此处为总结
        if task.status=="running":
            task.status="completed"
            context=""
            if len(task.tool_log)>10:
                debug_log(f"共{len(task.tool_log)}条工具调用记录，开始总结")
                for i in task.tool_log:
                    context=context+i
                task.set_temp_dialog_input(f"本次的任务是\n{task.content}\n，请结合任务目标仅从下面的工具调用过程中筛选出不重复的对提高工具调用正确率来说有用的事实，主要着重于工具调用的方式上，不要自己添加信息,如果没有，请回答“无可用经验”\n{context}")
                Agent.get_agent("reader",task.user.session_id).send(task)
                context = task.consume_temp_dialog_output()
                if "无可用经验" not in context:
                    Agent.get_agent("tool",task.user.session_id).add_message("user",task.content)
                    Agent.get_agent("tool", task.user.session_id).add_message("assistant", "本次任务需要注意"+context)

            context = ""
            if len(task.main_log)>3:
                debug_log(f"共{len(task.main_log)}条智能体调度记录，开始总结")
                for i in task.main_log:
                    context = context + i
                task.set_temp_dialog_input(f"本次的任务是\n{task.content}\n，请结合任务目标从下面的智能体调度过程中总结出对“如何向其他智能体更准确地表达”有用的经验，如果没有，请回答“无可用经验”\n{context}")
                Agent.get_agent("reader", task.user.session_id).send(task)
                context=task.consume_temp_dialog_output()
                if "无可用经验" not in context:
                    Agent.get_agent("tool", task.user.session_id).add_message("user", task.content)
                    Agent.get_agent("tool", task.user.session_id).add_message("assistant","本次任务需要注意" + context)
            debug_log(f"[session]任务完成{task.default_agent.id}开始记录记忆")
            task.default_agent.add_message("user", f"<{task.user.session_id}>" + task.content)
            task.default_agent.add_message("assistant", f"{result[2]}:{result[3]}")
            commit_limit =task.default_agent.config.get("commit_limit",0)
            commit_limit = commit_limit if commit_limit is not None else 0
            print(commit_limit)
            if  commit_limit and len(task.default_agent.ov_session.messages) > commit_limit :
                debug_log(f"[session]-commit {task.default_agent.id}提交{len(task.default_agent.ov_session.messages)}条记录")
                task.default_agent.ov_session.commit()
            
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
    def first_call(cls,task:Task):
        try:
            agent_id = Agent.default_agent[task.user.session_id]
        except (KeyError, TypeError, AttributeError):
            agent_id = "main"
            Agent.default_agent[task.user.session_id]="main"
        target = Agent.get_agent(agent_id,task.user.session_id)
        task.target=target
        chat_log(f"{task.user.session_id}->{target.id}\n{task.content}")
        debug_log(f"[user_chat]{task.user.session_id}->{target.id}")

    def set_default_agent(self,agent_id):
        Agent.default_agent[self.session_id]=agent_id

    def get_context_sync(self, query: str):
        """同步版本：严格匹配真实返回结构，不丢内容、无报错"""
        try:
            ctx = asyncio.run(
                self.ov_session.get_context_for_search(
                    query=query,
                    max_messages=16
                )
            )

            messages = []
            # 打印真实上下文，调试用
            # print("真实ctx:", ctx)

            # 1. 最新归档历史（唯一的历史记录）
            latest_archive = ctx.get("latest_archive_overview", "").strip()
            if latest_archive:
                messages.append({
                    "role": "system",
                    "content": f"历史记忆：{latest_archive}"
                })

            # 2. 当前会话消息（正确字段：current_messages）
            for msg in ctx.get("current_messages", []):
                if not msg.parts:
                    continue
                content = msg.parts[0].text
                content = re.sub(r'</?think>', '', content).strip()
                # 过滤无效前缀
                if content and '智能体返回：' not in content:
                    messages.append({
                        "role": msg.role,
                        "content": content
                    })

            # 系统提示
            if messages:
                messages.insert(0, {
                    "role": "system",
                    "content": "以下是你和用户的历史对话记录，请根据上下文继续回答"
                })

            return messages
        except Exception as e:
            print("获取上下文异常:", e)
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
                    task.tool_log.append("结果" + content[3])
                    content=f"\n{content[1]}，\n结果{content[3]}"
                else:
                    content = f"{content[0]}的请求：\n{content[1]},\n收到来自{content[2]}的回复：\n{content[3]}"
                    task.main_log.append(content)
                    if(content[0]=="main"):
                        task.main_memory.append(content)
            else:
                content = "当你看到这条消息时，意味着出现某些问题导致输入为空了"
        task.set_temp_dialog_input(content)
        chat_log(f"{self.id}收到:\n{content}")
        # 2. 同步获取上下文
        context = self.get_context_sync(content)

        # 1. 添加用户输入到历史
        messages = [{"role": "system", "content": self.system_prompt}] + context

        #目前的对话内容构成 环境提示词+viking记忆(长期记忆+session记忆)+任务记忆(仅main)+用户原始请求+本次单轮对话请求(用户原始请求/自己的上次请求+回复内容/工具调用过程)

        if self.id == "main":
            memory="以下是你在本次任务中的记忆:"
            for i in task.main_memory:
                memory+="\n"+i
            messages += [{"role": "system", "content": memory }]
        
        messages += [{"role": "system", "content": "以下为本次请求对话，请着重于下面部分\n下面是该任务用户原始请求"}] + [
            {"role": "user", "content": f"<{task.user.id}>" + task.content},
            {"role": "system", "content": "以下为本次单轮对话内容"},
            {"role": "user", "content": f"<{task.caller.id}>" + content}]
        # 2. 调用大模型
        # 读取配置
        api_url = self.config["api_url"]
        method = self.config.get("method", "POST")
        model = self.config["model"]
        api_key = self.config.get("api_key", "")

        # 请求头
        headers = {"Content-Type": "application/json"}
        if api_key.strip():
                headers["Authorization"] = f"Bearer {api_key}"

            # 请求体
        json_data = {
                "model": model,
                "messages": messages,
                "temperature" : self.config.get("temperature", 1),
                "stream": False
        }

        resp = None
        success = False

        # 500 重试 1 次
        for attempt in range(2):
            try:
                if method.upper() == "GET":
                    resp = requests.get(api_url, headers=headers, json=json_data, timeout=150)
                else:
                    resp = requests.post(api_url, headers=headers, json=json_data, timeout=150)

                if resp.status_code < 500:
                    success = True
                    break
                print(f"模型返回 500 错误，重试第 {attempt+1} 次...")
            except Exception as e:
                print(f"请求异常：{str(e)}")
                continue

        task.set_temp_dialog_output(resp)
        parse_response(self,task)
        parse_syntax(self,task)
        result = task.consume_temp_dialog_output()

        # 最终失败 → 返回你统一的错误格式
        if not success or resp is None:
            result = {
                "final_reply": "【模型请求失败】API 调用超时，请稍后重试",
                "tool_call": None,
                "agent_call": None
                }

    # HTTP 错误（4xx等）
        if resp.status_code >= 400:
            result= {
                "final_reply": f"【模型返回错误】{resp.status_code} {resp.text}",
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

        elif result["question"]:
            debug_log(f"[询问] {self.id}")
            task.status = "pause"
            task.push_context(self,result["question"])
            task.set_temp_dialog_input(f"{self.id}:{result['question']}")
            task.user.send(task)
            task.caller = task.user
            Task.save_pending_task(task.user.id, task)

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
                output = tool_manager.run_tool(task,tool_name, *args)
            else:
                # 2. 无原生工具 → 自动执行 OpenViking 技能（ClawHub下载的技能）
                output = skill_manager.run_skill(task,tool_name, *args)

        except Exception as e:
            output = f"工具执行失败：{str(e)}"

        # 把结果写回任务
        task.set_temp_dialog_output(output)
        chat_log(f"{self.id} 执行工具 {tool_name}:\n结果: {output}")
        debug_log(f"[工具结果] {self.id} {output}")