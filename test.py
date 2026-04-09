import sys
from pathlib import Path
import openviking as ov

# ======================
# 你只需要确保运行在项目根目录即可
# ======================
def main(skill_slug):

    # 路径：当前目录 / skills / 技能名 / SKILL.md
    skill_file = Path.cwd() / "skills" / skill_slug / "SKILL.md"

    if not skill_file.exists():
        print(f"❌ 文件不存在：{skill_file}")
        return

    # 初始化 OpenViking（和你代码完全一致）
    data_path = Path.cwd() / "viking_data"
    client = ov.SyncOpenViking(path=str(data_path))
    client.initialize()

    print(f"开始导入：{skill_file}")

    try:
        result = client.add_skill(str(skill_file), wait=True)
        print(f"✅ 导入成功：{result.get('uri', '')}")
    except Exception as e:
        print(f"❌ 导入失败：{str(e)}")
main("qq")