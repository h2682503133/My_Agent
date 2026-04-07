# core/logger.py
import os
import time
import datetime
import socket
import threading
# ======================
# 配置
# ======================
LOG_HOST = '127.0.0.1'
LOG_PORT = 5001

# 两个客户端连接
chat_conn = None  # 模型日志窗口
debug_conn = None  # 任务/队列日志窗口


# ======================
# 日志服务（支持双客户端）
# ======================
def log_server():
    global chat_conn, debug_conn
    import socket

    # 🔥 检测端口是否被占用（关键修复）
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)
    port_in_use = s.connect_ex(('127.0.0.1', LOG_PORT)) == 0
    s.close()

    # 如果端口被占用，直接不启动，不退出程序
    if port_in_use:
        print("[日志服务] 端口已被占用，当前进程不启动日志服务")
        return

    # 端口没被占用，才继续启动
    print("[日志服务] 启动日志服务...")

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((LOG_HOST, LOG_PORT))
    server.listen(2)
    print("[日志服务] 等待双客户端连接...")

    while True:
        conn, addr = server.accept()
        if chat_conn is None:
            chat_conn = conn
            print("[日志服务] 对话日志客户端已连接")
        elif debug_conn is None:
            debug_conn = conn
            print("[日志服务] 调试日志客户端已连接")

# 启动线程（不动）
threading.Thread(target=log_server, daemon=True).start()


# ======================
# 公共写文件函数
# ======================
def log_to_file(msg: str, log_type: str):
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    log_dir = f"logs/{log_type}"
    log_path = f"{log_dir}/{date_str}.log"

    os.makedirs(log_dir, exist_ok=True)

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")


# ======================
# 对外日志接口
# ======================
def chat_log(msg):
    log_to_file(msg, "chat")
    try:
        if chat_conn:
            chat_conn.sendall(f"[{time.strftime('%H:%M:%S')}] {msg}\n".encode("utf-8"))
    except:
        pass


def debug_log(msg):
    log_to_file(msg, "debug")
    try:
        if debug_conn:
            debug_conn.sendall(f"[{time.strftime('%H:%M:%S')}] {msg}\n".encode("utf-8"))
    except:
        pass


def gateway_log(msg):
    log_to_file(msg, "gateway")
    print(msg)