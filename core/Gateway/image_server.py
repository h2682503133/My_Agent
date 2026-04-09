# image_server.py
import os
from pathlib import Path
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

import json
import os



def start_local_image_server():
    # 加载配置
    with open("config/gateway_setting.json", "r", encoding="utf-8") as f:
        CONFIG = json.load(f)
    BASE_ROOT_DIR = Path(__file__).parent.parent.parent
    # 读取图片服务配置（和你 qq / web 写法完全统一）
    IMAGE_SERVER_CFG = CONFIG["image_server"]
    IMAGE_SERVER_HOST = IMAGE_SERVER_CFG["host"]
    IMAGE_SERVER_PORT = IMAGE_SERVER_CFG["port"]
    IMAGE_ASSET_DIR = IMAGE_SERVER_CFG["asset_dir"]
    os.makedirs(IMAGE_ASSET_DIR, exist_ok=True)
    asset_full_path = BASE_ROOT_DIR / IMAGE_ASSET_DIR
    os.makedirs(asset_full_path, exist_ok=True)

    class SafeHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            # 关键：只传目录，不改全局任何东西！
            super().__init__(*args, directory=str(asset_full_path), **kwargs)

    def run():
        try:
            httpd = HTTPServer((IMAGE_SERVER_HOST, IMAGE_SERVER_PORT), SafeHandler)
            print(f"[图床] 运行在 http://127.0.0.1:{IMAGE_SERVER_PORT}")
            httpd.serve_forever()
        except Exception as e:
            print(f"[图床] 异常：{e}")

    thread = threading.Thread(target=run, daemon=True)
    thread.start()