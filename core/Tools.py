import subprocess
import requests
import json
import os

class ToolManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.tools = {}
            cls._instance.register_builtin_tools()
        return cls._instance

    # 注册工具
    def register_tool(self, name, func):
        self.tools[name] = func

    # 执行工具（Skill 调用这里）
    def run_tool(self, name: str, *args, **kwargs):
        if name not in self.tools:
            return f"【错误】工具 {name} 未实现"
        try:
            return self.tools[name](*args, **kwargs)
        except Exception as e:
            return f"【工具错误】{name} 执行失败：{str(e)}"

    # ------------------------------
    # 内置标准工具（OpenClaw 官方标准）
    # ------------------------------
    def register_builtin_tools(self):
        # 1. shell 命令执行
        def shell(command: str, timeout=15):
            try:
                # Windows 官方现代 shell：PowerShell
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", command],
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                output = result.stdout.strip()
                error = result.stderr.strip()
                return output or error
            except subprocess.TimeoutExpired:
                return "执行超时"
            except Exception as e:
                return f"执行错误：{str(e)}"

        # 2. fetch 网络请求
        def fetch(url: str, method="GET", data=None):
            try:
                if method.upper() == "GET":
                    r = requests.get(url, timeout=10)
                else:
                    r = requests.post(url, json=data, timeout=10)
                return r.text
            except:
                return "请求失败"

        # 3. websearch 搜索（这里用百度简易版，可换）
        def websearch(query: str):
            try:
                r = requests.get(f"https://www.baidu.com/s?wd={query}", timeout=10)
                return f"搜索 {query} 成功（返回长度：{len(r.text)}）"
            except:
                return "搜索失败"

        # 4. file_read 文件读取
        def file_read(path: str):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
            except:
                return "读取失败"

        # 5. file_write 文件写入
        def file_write(path: str, content: str):
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                return "写入成功"
            except:
                return "写入失败"

        def codex(*args):
            default_dir = r"D:\DuanKou\tools\My_Agent\workspace"

            # 参数解析
            if len(args) == 1:
                working_dir = default_dir
                prompt = args[0]
            else:
                working_dir = args[0] if args[0] else default_dir
                prompt = args[1]

            if not prompt:
                return "错误：请输入需求"

            # 调用外部 codex_call.py
            script_path = os.path.join(os.path.dirname(__file__), "codex_call.py")
            cmd = [
                "python", script_path,
                working_dir,
                prompt
            ]

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=330,
                    encoding="utf-8"
                )
                return result.stdout.strip() or result.stderr.strip()
            except Exception as e:
                return f"Codex 调用失败：{str(e)}"

        # 注册
        self.register_tool("shell", shell)
        self.register_tool("fetch", fetch)
        self.register_tool("websearch", websearch)
        self.register_tool("file_read", file_read)
        self.register_tool("file_write", file_write)
        self.register_tool("codex", codex)

# 全局单例
tool_manager = ToolManager()