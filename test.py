import subprocess


def shell(*args):
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
        workspace = str("D:\\DuanKou\\tools\\My_Agent\\" + "workspace")
        full_cmd = f"Set-Location '{workspace}'; {command}"
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", full_cmd],
            capture_output=True,
            text=False,
            timeout=20
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
            return f"执行失败：{stdout+stderr}"
        return stdout or "执行成功（无输出）"

    except Exception as e:
        return f"执行异常：{str(e)}"
print(shell("cd 'D:\\DuanKou\\tools\\My_Agent\\skills\\pixiv' ; python scripts/pixiv.py search --keyword 键山雏"))