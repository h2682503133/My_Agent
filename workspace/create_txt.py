from pathlib import Path


def main() -> None:
    Path("hello.txt").write_text("你好", encoding="utf-8")
    print("所有任务已完成")


if __name__ == "__main__":
    main()
