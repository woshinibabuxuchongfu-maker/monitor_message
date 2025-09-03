import sqlite3
import threading
from datetime import datetime
from typing import List, Optional, Tuple

class KeywordDB:
    """
    单例类：用于管理违规关键词的SQLite数据库操作。
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path: str = "keywords.db"):
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance.db_path = db_path
                    cls._instance._initialize_db()
        return cls._instance

    def _initialize_db(self):
        """初始化数据库连接并创建表"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT NOT NULL UNIQUE,
                    type TEXT NOT NULL DEFAULT 'keyword',
                    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
                )
            ''')
            conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接（线程安全）"""
        # sqlite3.Connection 是非线程安全的，这里每个线程使用自己的连接
        # 但我们在单例中不共享连接，每次操作都新建或使用线程局部连接
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def add_keyword(self, keyword: str) -> bool:
        """
        添加一个违规关键词。
        :param keyword: 要添加的关键词（字符串）
        :return: 成功返回 True，已存在则返回 False
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT OR IGNORE INTO keywords (keyword) VALUES (?)", (keyword,))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"添加关键词失败: {e}")
            return False

    def add_keywords(self, keywords: List[str]) -> int:
        """
        批量添加关键词。
        :param keywords: 关键词列表
        :return: 实际新增的数量
        """
        count = 0
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                for kw in keywords:
                    cursor.execute("INSERT OR IGNORE INTO keywords (keyword) VALUES (?)", (kw,))
                    if cursor.rowcount > 0:
                        count += 1
                conn.commit()
        except Exception as e:
            print(f"批量添加关键词失败: {e}")
        return count

    def remove_keyword(self, keyword: str) -> bool:
        """
        删除一个关键词。
        :param keyword: 要删除的关键词
        :return: 成功删除返回 True
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM keywords WHERE keyword = ?", (keyword,))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"删除关键词失败: {e}")
            return False

    def get_all_keywords(self) -> List[str]:
        """
        获取所有关键词。
        :return: 关键词列表
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT keyword FROM keywords ORDER BY keyword")
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"查询所有关键词失败: {e}")
            return []

    def search_keywords(self, pattern: str) -> List[str]:
        """
        模糊搜索关键词（LIKE 查询）。
        :param pattern: 搜索模式，如 '%赌博%'，或直接传入字符串自动加 %
        :return: 匹配的关键词列表
        """
        if not pattern.startswith('%'):
            pattern = '%' + pattern + '%'
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT keyword FROM keywords WHERE keyword LIKE ?", (pattern,))
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"搜索关键词失败: {e}")
            return []

    def keyword_exists(self, keyword: str) -> bool:
        """
        检查关键词是否存在。
        :param keyword: 要检查的关键词
        :return: 存在返回 True
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM keywords WHERE keyword = ? LIMIT 1", (keyword,))
                return cursor.fetchone() is not None
        except Exception as e:
            print(f"检查关键词是否存在时出错: {e}")
            return False

    def clear_all_keywords(self) -> bool:
        """
        清空所有关键词（谨慎使用）。
        :return: 是否成功
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM keywords")
                return True
        except Exception as e:
            print(f"清空关键词失败: {e}")
            return False

    def close(self):
        """
        关闭数据库连接（可选，SQLite 通常不需要显式关闭）
        """
        # 在单例中，通常不主动关闭，由程序退出自动处理
        pass

# 示例用法
if __name__ == "__main__":
    # 获取单例实例
    db = KeywordDB("violation_keywords.db")

    # 添加关键词
    db.add_keyword("赌博")
    db.add_keyword("色情")
    db.add_keywords(["诈骗", "病毒", "恶意软件"])

    # 查询所有
    print("所有关键词:", db.get_all_keywords())

    # 搜索
    print("包含'赌'的词:", db.search_keywords("赌"))

    # 检查存在
    print("是否存在'赌博':", db.keyword_exists("赌博"))

    # 删除
    db.remove_keyword("赌博")
    print("删除后:", db.get_all_keywords())