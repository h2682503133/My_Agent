import json
import subprocess
import requests
import os
from core.Task.Task import Task
with open("config/gateway_setting.json", "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

# 读取图片服务配置
IMAGE_SERVER_CFG = CONFIG["image_server"]
IMAGE_SERVER_HOST = IMAGE_SERVER_CFG["host"]
IMAGE_SERVER_PORT = IMAGE_SERVER_CFG["port"]
IMAGE_ASSET_DIR = IMAGE_SERVER_CFG["asset_dir"]
class ToolManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.tools = {}
            cls._instance.register_native_tools()
        return cls._instance

    def register_tool(self, name, func):
        self.tools[name] = func

    def run_tool(self, task: Task, name: str, *args, **kwargs):
        if name not in self.tools:
            return f"【错误】工具 {name} 未实现"
        try:
            return self.tools[name](task,*args, **kwargs)
        except Exception as e:
            return f"【工具错误】{name} 执行失败：{str(e)}"

    def shell(self,task, command: str):
        return self.run_tool(task,"shell", [command])
    # 仅注册：原生底层工具（纯Tools，无Skills）
    def register_native_tools(self):

        def shell(task: Task,*args):
            from core.Agent.Agent import Agent
            try:

                if not args:
                    return "错误：命令不能为空"
                clean_args = []
                for arg in args:
                    if isinstance(arg, list):
                        clean_args.extend(arg)  # 列表就把内容倒出来
                    else:
                        clean_args.append(str(arg))
                # 严格按你的协议：| 分隔
                command = "|".join(clean_args)
                workspace = str(Agent.BASE_ROOT_DIR / "workspace")
                full_cmd = f"Set-Location '{workspace}'; {command}"
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", full_cmd],
                    capture_output=True,
                    text=False,
                    timeout=120 # 超时时间 120秒
                )

                # ✅ 安全解码
                def decode_safe(b: bytes) -> str:
                    if not b:
                        return ""
                    try:
                        return b.decode("utf-8").strip()
                    except UnicodeDecodeError:
                        try:
                            return b.decode("gbk").strip()
                        except UnicodeDecodeError:
                            return "[非文本内容]"

                stdout = decode_safe(result.stdout)
                stderr = decode_safe(result.stderr)

                if result.returncode != 0:
                    return f"执行失败：{stdout}\n{stderr}"
                return stdout or "执行成功（无输出）"

            except Exception as e:
                return f"执行异常：{str(e)}"
        def list_workspace(task: Task):
            return shell(task,[f"ls -R ."])
        def fetch(task: Task,url: str, method="GET", data=None):
            try:
                r = requests.get(url, timeout=10) if method.upper() == "GET" else requests.post(url, json=data, timeout=10)
                return r.text
            except:
                return "请求失败"

        def websearch(task: Task,query: str):
            try:
                from bs4 import BeautifulSoup

                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Connection": "close",
                    "Upgrade-Insecure-Requests": "1"
                }

                r = requests.get(
                    f"https://www.baidu.com/s",
                    params={"wd": query},
                    headers=headers,
                    timeout=15
                )
                r.raise_for_status()

                soup = BeautifulSoup(r.text, "html.parser")
                results = []

                # 兼容百度所有结果样式 + 提取网址
                for item in soup.find_all("div", class_=["result", "c-container", "result-op"]):
                    if len(results) >= 4:
                        break
                    try:
                        # 标题
                        title = item.find("h3").get_text(strip=True) if item.find("h3") else "无标题"
                        
                        # 真实网址
                        link_tag = item.find("a")
                        url = link_tag["href"] if link_tag and "href" in link_tag.attrs else "无链接"
                        
                        # 内容摘要
                        content = item.get_text(strip=True)[:160]

                        # 把网址也加进去！
                        results.append(f"? {title}\n【网址】{url}\n{content}\n")
                    except:
                        continue

                if not results:
                    return f"【百度搜索：{query}】未找到相关内容（或被百度拦截）"

                return f"【百度搜索：{query}】\n" + "\n".join(results)

            except Exception as e:
                return f"搜索失败：{str(e)}"

        def file_read(task: Task,path: str):
            from core.Agent.Agent import Agent
            import os
            try:
                # 如果不是绝对路径 → 拼 workspace
                if not os.path.isabs(path):
                    path = Agent.BASE_ROOT_DIR / "workspace" / path

                with open(path, "r", encoding="utf-8") as f:
                    return "内容为:"+f.read()
            except:
                return "读取失败"

        def file_write(task: Task,path: str, content: str):
            from core.Agent.Agent import Agent
            import os
            try:
                # 如果不是绝对路径 → 拼 workspace
                if not os.path.isabs(path):
                    path = Agent.BASE_ROOT_DIR / "workspace" / path

                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                return "写入成功"
            except:
                return "写入失败"

        def codex(task: Task,*args):
            from core.Agent.Agent import Agent
            if len(args) == 1:
                working_dir = Agent.BASE_ROOT_DIR / "workspace"
                prompt = args[0]
            else:
                working_dir = args[0] if args[0] else Agent.BASE_ROOT_DIR / "workspace"
                prompt = args[1]
            if not prompt:
                return "错误：请输入需求"
            script_path = os.path.join(os.path.dirname(__file__), "codex_call.py")
            cmd = ["python", script_path, str(working_dir), prompt]
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=330, encoding="utf-8")
                return result.stdout.strip() or result.stderr.strip()
            except Exception as e:
                return f"Codex 调用失败：{str(e)}"
            
        def get_image_url_from_local(task: Task, local_path: str) -> str:
            from core.Agent.Agent import Agent
            workspace = Agent.BASE_ROOT_DIR / "workspace"
            if not os.path.isabs(local_path):
                local_path = os.path.join(workspace, local_path)

            # 2. 检查文件是否存在
            if not os.path.exists(local_path):
                return f"本地文件不存在：{local_path}"

            # 3. 提取文件名
            filename = os.path.basename(local_path)
            target_path = os.path.join(IMAGE_ASSET_DIR, filename)

            # 4. 复制到图床目录
            try:
                with open(local_path, "rb") as fsrc:
                    with open(target_path, "wb") as fdst:
                        fdst.write(fsrc.read())
            except Exception as e:
                return f"复制图片失败：{str(e)}"

            # 5. 生成最终可访问 URL
            url = f"http://127.0.0.1:{IMAGE_SERVER_PORT}/{filename}"

            return f"此图片URL为：{url}"
        def send_image_by_url(task: Task, image_url: str) -> str:
            """
            发送网络图片（直接填 URL）
            """
            if not image_url:
                return "❌ 图片 URL 不能为空"
            
            task.send_images.append(image_url)
            task.user.send(task)
            return f"URL为{image_url}的图片已发送"

        #注册skill管理方法
        from core.Agent.Skill_manager import skill_manager

        def clawhub_search(task: Task,keyword: str):
            return skill_manager.clawhub_search(task,keyword)

        def clawhub_install(task: Task,skill_slug: str):
            return skill_manager.clawhub_install(task,skill_slug)

        def clawhub_list(task: Task):
            return skill_manager.clawhub_list(task)

        def skill_list(task: Task):
            return skill_manager.skill_list(task)

        def skill_list_simple(task: Task):
            return skill_manager.skill_list_simple(task)

        def skill_delete(task: Task,skill_slug: str):
            return skill_manager.skill_delete(task,skill_slug)

        def skill_abstract(task: Task,skill_name: str):
            return skill_manager.skill_abstract(task,skill_name)

        def skill_overview(task: Task,skill_name: str):
            return skill_manager.skill_overview(task,skill_name)

        def skill_manual(task: Task,skill_name: str):
            return skill_manager.skill_manual(task,skill_name)
        def add_skill_to_viking(task: Task,skill_name: str):
            return skill_manager.add_skill_to_viking(task,skill_name)
        
        self.register_tool("add-skill-to-viking", add_skill_to_viking)
        self.register_tool("clawhub-search", clawhub_search)
        self.register_tool("clawhub-install", clawhub_install)
        self.register_tool("clawhub-list", clawhub_list)
        self.register_tool("skill-list", skill_list)
        self.register_tool("skill-list-simple", skill_list_simple)
        self.register_tool("skill-delete", skill_delete)

        self.register_tool("skill-abstract", skill_abstract)
        self.register_tool("skill-overview", skill_overview)
        self.register_tool("skill-manual", skill_manual)

        # 注册原生工具
        self.register_tool("shell", shell)
        self.register_tool("list-workspace", list_workspace)
        self.register_tool("fetch", fetch)
        self.register_tool("web-search", websearch)
        self.register_tool("file-read", file_read)
        self.register_tool("file-write", file_write)
        self.register_tool("codex", codex)
        self.register_tool("get-image-url-from-local", get_image_url_from_local)
        self.register_tool("send-image-by-url", send_image_by_url)

tool_manager = ToolManager()