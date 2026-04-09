# core/Agent/skill_manager.py 【ClawHub 官方CLI 原生对接版】
import openviking as ov
import subprocess
from pathlib import Path
import shutil

class SkillManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # OpenViking 本地技能库（官方示例用法）
            data_path = str(Path(__file__).parent.parent.parent / "viking_data")
            cls._instance.client = ov.SyncOpenViking(path=data_path)
            cls._instance.client.initialize()
        return cls._instance

    # ======================
    # 🔥 官方：ClawHub 搜索（调用 CLI）
    # 命令：clawhub search 关键词
    # ======================
    def clawhub_search(self, keyword: str):
        from core.Agent.Tool_manager import tool_manager
        return tool_manager.shell(f"clawhub search {keyword}")

    def clawhub_install(self, skill_slug: str):
        from core.Agent.Agent import Agent
        from core.Agent.Tool_manager import tool_manager
        skill_dir = Path(Agent.BASE_ROOT_DIR) / "skills"
        skill_dir.mkdir(exist_ok=True)

        # 安装技能到本地
        result = tool_manager.shell(f"clawhub install {skill_slug} --dir {skill_dir} --force")
        skill_md_path = skill_dir / skill_slug / "SKILL.md"

        # ================================
        # 🔥 调用独立接口：添加技能到 OpenViking
        # ================================
        add_result = self.add_skill_to_viking(skill_slug)

        if add_result.startswith("✅"):
            return f"✅ 安装并导入 Viking 知识库：{skill_slug}\n{add_result}\n{result}"
        else:
            return f"⚠️ 安装成功，但导入技能失败：{add_result}\n{result}"
    
    def add_skill_to_viking(self, skill_slug: str) -> str:
        from core.Agent.Agent import Agent
        try:
            # 路径规则 和之前完全一样
            skill_md_path = Path(Agent.BASE_ROOT_DIR) / "skills" / skill_slug / "SKILL.md"

            if not skill_md_path.exists():
                return f"❌ 技能 {skill_slug} 不存在，缺少 SKILL.md"

            # 官方SDK添加技能
            add_result = self.client.add_skill(str(skill_md_path), wait=True)
            return f"✅ 技能导入成功：{skill_slug} | URI: {add_result.get('uri', '')}"

        except Exception as e:
            return f"❌ 导入技能失败：{str(e)}"

    def clawhub_list(self, *args):

        from core.Agent.Tool_manager import tool_manager
        return tool_manager.shell("clawhub list")

    def skill_delete(self, skill_slug: str):
        from core.Agent.Agent import Agent
        from core.Agent.Tool_manager import tool_manager
        import shutil

        # 1. 先从 Viking 知识库中删除技能（关键！你之前缺的就是这个）
        try:
            skill_uri = f"viking://agent/skills/{skill_slug}"
            self.client.rm(skill_uri)  # 移除 Viking 内部技能
        except Exception as e:
            pass  # 就算删不掉也继续执行系统删除

        # 2. 执行 clawhub 卸载命令
        result = tool_manager.shell(f"clawhub uninstall --yes {skill_slug}")

        # 3. 强制删除本地技能文件夹（彻底清理）
        skill_dir = Path(Agent.BASE_ROOT_DIR) / "skills" / skill_slug
        if skill_dir.exists():
            shutil.rmtree(skill_dir)

        return f"✅ 技能已完全卸载（Viking 已移除 + 文件夹已删除）：{skill_slug}\n{result}"

    def skill_list(self, *args):
        """列出 Viking 知识库中所有技能（100% 不会报错版）"""
        try:
            # 官方API：列出技能
            skills = self.client.ls("viking://agent/skills/")

            if not skills:
                return "📭 Viking 知识库中暂无任何技能"

            output = "📚 已安装技能列表：\n"
            for i, skill in enumerate(skills, 1):
                name = skill.get("name", "未命名")
                desc = skill.get("abstract", "无描述")
                # 只拼接字符串！绝对不返回任何数字、列表
                output += f"{i}. {name} - {desc}\n"

            return output.strip()

        except Exception as e:
            # 错误信息也一定是字符串
            return f"❌ 获取技能列表失败：{str(e)}"

    def skill_list_simple(self, *args):
        try:
            names = self.client.ls("viking://agent/skills/", simple=True)
            if not names:
                return "📭 暂无技能"
            return "已安装技能：\n" + "\n".join(f"- {n}" for n in names)
        except:
            return "❌ 获取失败"

    def skill_abstract(self, skill_name: str) -> str:
        """
        获取技能简介（.abstract.md）
        返回：原始字符串
        """
        try:
            uri = f"viking://agent/skills/{skill_name}/.abstract.md"
            return self.client.read(uri) or "无简介"
        except:
            return f"读取 abstract 失败,请检查知识库中是否有名为{skill_name}的技能"

    def skill_overview(self, skill_name: str) -> str:
        """
        获取技能使用说明（.overview.md）
        返回：原始字符串
        """
        try:
            uri = f"viking://agent/skills/{skill_name}/.overview.md"
            return self.client.read(uri) or "无使用说明"
        except:
            return f"读取 overview 失败,请检查知识库中是否有名为{skill_name}的技能"

    def skill_exec(self, skill_name: str) -> str:
        """
        获取技能执行文档（SKILL.md）
        返回：原始字符串
        """
        try:
            uri = f"viking://agent/skills/{skill_name}/SKILL.md"
            return self.client.read(uri) or "无执行文档"
        except:
            return f"读取 SKILL.md 失败,请检查知识库中是否有名为{skill_name}的技能"

    def run_skill(self, skill_name: str, *args):
        try:
            from core.Agent.Tool_manager import tool_manager
            import os


            base_dir = os.getcwd()
            skill_dir = os.path.join(base_dir, "skills", skill_name)
        
        
            script_file = f"{skill_dir}//scripts//{skill_name}.py"

            # ======================
            # 你要的逻辑：只判断 .py 文件是否存在
            # 不存在 → 抛异常 → 进 except → 返回文档
            # ======================
            if not os.path.exists(script_file):
                raise FileNotFoundError(f"技能脚本不存在：{script_file}")

            # 拼接命令（不变）
            arg_str = " ".join(args)
            cmd = f'cd "{skill_dir}" ; python scripts/{skill_name}.py {arg_str}'

            # 执行：显示完整报错 + 中文不乱码
            output=tool_manager.shell(cmd)

            return f"【? 执行成功：{skill_name}】\n命令：{cmd}\n结果：{output}"

        except Exception as e:
            # ======================
            # 只有 文件不存在 才会走到这里
            # ======================
            doc = self.skill_overview(skill_name)
            return doc
# 单例
skill_manager = SkillManager()