import requests
import yaml
import os
import argparse
from pathlib import Path

# 解决 Windows GBK 编码问题
import sys
sys.stdout.reconfigure(encoding='utf-8')

class PixivClient:
    def __init__(self, config_path="config.yaml"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.cookie = self.config["pixiv"]["cookie"]
        self.download_dir = os.path.abspath(self.config["pixiv"]["download_dir"])
        self.default_limit = self.config.get("search", {}).get("default_limit", 5)
        self.session = requests.Session()

    def _headers(self):
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.pixiv.net/",
            "Cookie": self.cookie,
        }

    def search(self, keyword, page=1, limit=None):
        fetch_limit = limit if limit is not None else self.default_limit
        start = (page - 1) * fetch_limit
        end = start + fetch_limit

        url = f"https://www.pixiv.net/ajax/search/illustrations/{keyword}"
        params = {"p": page, "mode": "all", "order": "date_d"}
        
        r = self.session.get(url, params=params, headers=self._headers())
        data = r.json()
        items = data["body"]["illust"]["data"]
        return items[start:end]

    def get_illust_info(self, illust_id):
        url = f"https://www.pixiv.net/ajax/illust/{illust_id}"
        r = self.session.get(url, headers=self._headers())
        return r.json()["body"]

    def download(self, illust_id):
        info = self.get_illust_info(illust_id)
        page_count = info.get("pageCount", 1)
        saved_paths = []

        for p in range(page_count):
            img_url = info["urls"]["original"].replace("_p0", f"_p{p}")
            proxy_url = img_url.replace("i.pximg.net", "i.pixiv.re")

            os.makedirs(self.download_dir, exist_ok=True)
            filename = os.path.basename(img_url)
            save_path = os.path.join(self.download_dir, filename)

            # ====================== 我加的优化 ======================
            # 1. 下载超时 30 秒（防止卡死）
            # 2. 异常捕获（网络失败不会崩整个脚本）
            # ======================================================
            try:
                resp = requests.get(
                    proxy_url,
                    headers=self._headers(),
                    timeout=30  # 👈 关键：单张图片下载超时30秒
                )
                resp.raise_for_status()  # 404/500 直接抛错

                with open(save_path, "wb") as f:
                    f.write(resp.content)

                saved_paths.append(save_path)

            except Exception as e:
                print(f"[下载失败] {proxy_url}，错误：{str(e)}")
                continue  # 失败一张不影响其他

        return saved_paths


def main():
    parser = argparse.ArgumentParser(description="Pixiv 搜索下载工具")
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    # 搜索命令
    search_parser = subparsers.add_parser("search", help="搜索插画")
    search_parser.add_argument("--keywords", required=True, help="搜索关键词")
    search_parser.add_argument("--page", type=int, default=1, help="页码，默认1")
    search_parser.add_argument("--limit", type=int, help="单次获取上限，默认读取config")

    # 下载命令
    download_parser = subparsers.add_parser("download", help="下载插画（支持多页）")
    download_parser.add_argument("--id", required=True, help="作品ID")

    # 配置信息
    info_parser = subparsers.add_parser("info", help="查看当前配置信息")

    args = parser.parse_args()
    client = PixivClient()

    if args.cmd == "search":
        items = client.search(args.keywords, page=args.page, limit=args.limit)
        print(f"[搜索] {args.keywords} | 第{args.page}页\n")

        for item in items:
            print(f"[ID] {item['id']}")
            print(f"[标题] {item['title']}")
            print(f"[分辨率] {item.get('width','?')}x{item.get('height','?')}")
            print(f"[页数] {item.get('pageCount',1)}")
            print(f"[标签] {', '.join(item.get('tags', []))}")
            print(f"[分级] {'R18' if item.get('xRestrict',0) else '全年龄'}")
            print("-" * 60)

    elif args.cmd == "download":
        print(f"[下载] 作品ID: {args.id}")
        paths = client.download(args.id)
        for p in paths:
            print(f"[完成] {p}")

    elif args.cmd == "info":
        print("=" * 50)
        print(f"[下载目录] {client.download_dir}")
        print(f"[默认搜索限制] {client.default_limit} 条")
        print(f"[Cookie状态] 已配置" if client.cookie else "[Cookie状态] 未配置")
        print("=" * 50)

if __name__ == "__main__":
    main()