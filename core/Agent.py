import json
import subprocess
from pathlib import Path
import requests

from core.response_parser import parse_response
from core.syntax_parser import parse_syntax

class Agent:
    # 静态变量：全局主程序根目录（所有命令执行依赖此路径）
    BASE_ROOT_DIR = Path(__file__).parent.parent

    parse_response = parse_response
    parse_syntax = parse_syntax

    def __init__(self, agent_id):
        # 智能体唯一标识
        self.agent_id = agent_id
        
        # 智能体工作目录（默认可修改）
        self.working_dir = self.BASE_ROOT_DIR / "workspace"
        
        # 智能体配置（字典格式）
        self.config = {}
        
        # 系统提示词
        self.system_prompt = ""
        
        # 对话历史记忆
        self.history = []
        
        # 初始化加载
        self.load_config()
        self.build_system_prompt()

    def load_config(self):
        """加载当前智能体配置（源代码完全保留）"""
        config_path = self.BASE_ROOT_DIR / "config" / "agent_list.json"
        with open(config_path, "r", encoding="utf-8") as f:
            all_config = json.load(f)
        
        if self.agent_id not in all_config:
            raise KeyError(f"未找到智能体配置：{self.agent_id}")
        
        self.config = all_config[self.agent_id]

    def build_system_prompt(self):
        """构建系统提示词（源代码完全保留）"""
        prompt_dir = self.BASE_ROOT_DIR / "system_prompt" / self.agent_id
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
    def chat(self, user_input):
        """单轮对话主流程（支持自调用）"""
        # 1. 添加用户输入到历史
        self.history.append({"role": "user", "content": user_input})

        # 2. 调用大模型
        api_url = self.config["api_url"]
        model = self.config["model"]

        messages = [{"role": "system", "content": self.system_prompt}] + self.history

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

        raw_response = self.parse_response(resp)
        result = self.parse_syntax(raw_response)

        # 5. 更新历史


        # 6. 返回结构化结果
        return {
            "agent_reply": result["final_reply"],
            "command": result["command"],
            "agent_called": result["agent_call"],
            "raw_response": raw_response
        }

    # ==================== 智能体调用 ====================
    def call_agent(self, target_agent_id, content):
        print(f"{self.agent_id}->{target_agent_id}")
        """调用另一个智能体，内部会触发 chat()，支持自调用"""
        target_agent = Agent(target_agent_id)
        result = target_agent.chat(content)
        return result["agent_reply"]

    # ==================== 通用命令执行（CMD/Codex） ====================
    def _run_shell_command(self, command):
        """执行系统命令，依赖静态主路径，源代码完全保留"""
        try:
            result = subprocess.run(
                command,
                cwd=self.BASE_ROOT_DIR / "workspace",
                shell=True,
                capture_output=True,
                text=False,  # 重要：关闭文本模式
            )
            # 手动解码：先试 utf8，失败自动用 gbk，不抛错
            try:
                stdout = result.stdout.decode("utf-8")
            except:
                stdout = result.stdout.decode("gbk")

            try:
                stderr = result.stderr.decode("utf-8")
            except:
                stderr = result.stderr.decode("gbk")

            return stdout + stderr
        except Exception as e:
            return f"执行失败：{str(e)}"