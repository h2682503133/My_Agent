import socket
import time

while True:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('127.0.0.1', 5001))
        print("=== 日志窗口已连接 ===")
        break
    except:
        print("[等待日志服务启动中...]")
        time.sleep(1)

while True:
    data = s.recv(4096)
    if not data:
        break
    print(data.decode("utf-8"), end="")