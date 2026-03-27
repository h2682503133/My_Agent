import sqlite3
import json

# 你的数据库路径
DB_PATH = r"D:\DuanKou\tools\My_Agent\viking_data\viking\sqlite.db"

def view_viking_history():
    print("🔍 直接读取 Viking 本地上下文（不依赖任何库）\n")

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, session_id, role, parts, created_at FROM messages ORDER BY created_at")
        rows = cursor.fetchall()

        if not rows:
            print("📭 暂无历史记录")
            return

        for r in rows:
            msg_id, session_id, role, parts, created_at = r
            try:
                content = json.loads(parts)[0]["text"]
            except:
                content = parts

            print(f"[{session_id}] {role}: {content.strip()[:150]}")
            print("-" * 80)

        conn.close()
    except Exception as e:
        print(f"❌ 读取失败: {e}")

if __name__ == "__main__":
    view_viking_history()