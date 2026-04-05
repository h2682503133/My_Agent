import socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('127.0.0.1', 5001))

print("=== 模型对话独立日志窗口 ===")
while True:
    data = s.recv(4096)
    if not data:
        break
    print(data.decode("utf-8", errors="ignore"), end="")