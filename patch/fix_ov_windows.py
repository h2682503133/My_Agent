import os
import sys
import platform

def fix_openviking_windows_kill():
    if platform.system() != "Windows":
        return

    # 修复 Windows 不支持 os.kill(pid,0) 的BUG
    original_kill = os.kill
    def safe_kill(pid, sig):
        try:
            if sig == 0:
                # Windows 下安全检测进程是否存在
                return os.path.exists(f"/proc/{pid}")
            return original_kill(pid, sig)
        except:
            return False
    os.kill = safe_kill

# 必须在 导入 openviking 之前执行！
fix_openviking_windows_kill()