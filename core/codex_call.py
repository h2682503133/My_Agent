import subprocess
import sys
import os
def call_codex(prompt: str, working_dir: str):
    def win_to_wsl_path(path):
        if path.startswith("/mnt/"):
            return path

            # 👇 统一全角冒号 → 半角冒号（核心兼容）
        path = path.replace("：", ":")

        # 👇 按第一个半角冒号分割（你要的逻辑）
        parts = path.split(":", 1)
        if len(parts) < 2:
            return path

        # 盘符
        drive_letter = parts[0].lower()

        # 剩余路径
        rest = parts[1]

        # 统一斜杠
        rest = rest.replace("\\", "/")

        # 最终WSL路径
        return f"/mnt/{drive_letter}{rest}"

    working_dir = win_to_wsl_path(working_dir)
    # 正确转义单引号
    escaped_prompt = prompt.replace("'", "'\\''")

    codex_cmd = [
        "wsl",
        "bash", "-li", "-c",
        f"cd '{working_dir}' && codex exec --sandbox workspace-write --full-auto '{escaped_prompt}'"
    ]

    result = subprocess.run(
        args=codex_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=300,
        shell=False,
        encoding="utf-8"  # 直接用utf-8，不玩bytes混合
    )

    if result.returncode == 0:
        if "所有任务已完成" in result.stdout:
            return f"成功：{result.stdout}"
        else:
            return f"失败：未输出完成标志，输出：{result.stdout}"
    else:
        return f"失败：{result.stderr}"

if __name__ == "__main__":
    if len(sys.argv) > 2:
        res = call_codex(sys.argv[2]+",完成后输出：所有任务已完成", sys.argv[1])
        print(res)
    else:
        res = call_codex(
            "生成打印你好的Python程序，完成后输出：所有任务已完成",
            r"D:\DuanKou\tools\My_Agent\workspace"
        )
        print(res)