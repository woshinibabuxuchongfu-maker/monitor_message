import pymysql
import threading
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
import json
import os

class MySQLKeywordDB:
    """
    MySQL数据库关键词管理类
    支持连接配置和关键词的增删改查操作
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, connection_config: Dict[str, Any] = None):
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance.connection_config = connection_config
                    cls._instance.connection = None
                    cls._instance._initialize_db()
        return cls._instance

    def _initialize_db(self):
        """初始化数据库连接并创建表"""
        if self.connection_config:
            try:
                self.connection = pymysql.connect(**self.connection_config)
                self._create_tables()
            except Exception as e:
                print(f"MySQL连接失败: {e}")
                self.connection = None

    def _create_tables(self):
        """创建关键词表"""
        if not self.connection:
            return
            
        try:
            with self.connection.cursor() as cursor:
                # 创建数据库（如果不存在）
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.connection_config.get('database', 'filter_system')}")
                cursor.execute(f"USE {self.connection_config.get('database', 'filter_system')}")
                
                # 创建关键词表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS keywords (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        keyword VARCHAR(255) NOT NULL UNIQUE,
                        type VARCHAR(50) NOT NULL DEFAULT 'keyword',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_keyword (keyword),
                        INDEX idx_type (type)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                ''')
                
                # 创建检测记录表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS detection_records (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_name VARCHAR(255),
                        message TEXT,
                        matched_keywords JSON,
                        detection_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_user (user_name),
                        INDEX idx_time (detection_time)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                ''')
                
                self.connection.commit()
        except Exception as e:
            print(f"创建表失败: {e}")

    def _get_connection(self):
        """获取数据库连接"""
        if not self.connection or not self.connection.open:
            if self.connection_config:
                try:
                    self.connection = pymysql.connect(**self.connection_config)
                except Exception as e:
                    print(f"重新连接MySQL失败: {e}")
                    return None
        return self.connection

    def set_connection_config(self, config: Dict[str, Any]):
        """设置数据库连接配置"""
        self.connection_config = config
        if self.connection:
            self.connection.close()
        self._initialize_db()

    def test_connection(self) -> bool:
        """测试数据库连接"""
        try:
            conn = self._get_connection()
            if conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    return True
        except Exception as e:
            print(f"连接测试失败: {e}")
        return False

    def add_keyword(self, keyword: str, keyword_type: str = 'keyword') -> bool:
        """
        添加一个违规关键词
        :param keyword: 要添加的关键词
        :param keyword_type: 关键词类型
        :return: 成功返回 True，已存在则返回 False
        """
        try:
            conn = self._get_connection()
            if not conn:
                return False
                
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT IGNORE INTO keywords (keyword, type) VALUES (%s, %s)",
                    (keyword, keyword_type)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"添加关键词失败: {e}")
            return False

    def add_keywords(self, keywords: List[Tuple[str, str]]) -> int:
        """
        批量添加关键词
        :param keywords: 关键词列表，格式为 [(keyword, type), ...]
        :return: 实际新增的数量
        """
        count = 0
        try:
            conn = self._get_connection()
            if not conn:
                return 0
                
            with conn.cursor() as cursor:
                for keyword, keyword_type in keywords:
                    cursor.execute(
                        "INSERT IGNORE INTO keywords (keyword, type) VALUES (%s, %s)",
                        (keyword, keyword_type)
                    )
                    if cursor.rowcount > 0:
                        count += 1
                conn.commit()
        except Exception as e:
            print(f"批量添加关键词失败: {e}")
        return count

    def remove_keyword(self, keyword: str) -> bool:
        """
        删除一个关键词
        :param keyword: 要删除的关键词
        :return: 成功删除返回 True
        """
        try:
            conn = self._get_connection()
            if not conn:
                return False
                
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM keywords WHERE keyword = %s", (keyword,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"删除关键词失败: {e}")
            return False

    def get_all_keywords(self) -> List[Tuple[int, str, str, str]]:
        """
        获取所有关键词
        :return: 关键词列表，格式为 [(id, keyword, type, created_at), ...]
        """
        try:
            conn = self._get_connection()
            if not conn:
                return []
                
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, keyword, type, created_at FROM keywords ORDER BY keyword"
                )
                return cursor.fetchall()
        except Exception as e:
            print(f"查询所有关键词失败: {e}")
            return []

    def search_keywords(self, pattern: str) -> List[Tuple[int, str, str, str]]:
        """
        模糊搜索关键词
        :param pattern: 搜索模式
        :return: 匹配的关键词列表
        """
        try:
            conn = self._get_connection()
            if not conn:
                return []
                
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, keyword, type, created_at FROM keywords WHERE keyword LIKE %s ORDER BY keyword",
                    (f"%{pattern}%",)
                )
                return cursor.fetchall()
        except Exception as e:
            print(f"搜索关键词失败: {e}")
            return []

    def keyword_exists(self, keyword: str) -> bool:
        """
        检查关键词是否存在
        :param keyword: 要检查的关键词
        :return: 存在返回 True
        """
        try:
            conn = self._get_connection()
            if not conn:
                return False
                
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 FROM keywords WHERE keyword = %s LIMIT 1", (keyword,))
                return cursor.fetchone() is not None
        except Exception as e:
            print(f"检查关键词是否存在时出错: {e}")
            return False

    def clear_all_keywords(self) -> bool:
        """
        清空所有关键词
        :return: 是否成功
        """
        try:
            conn = self._get_connection()
            if not conn:
                return False
                
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM keywords")
                conn.commit()
                return True
        except Exception as e:
            print(f"清空关键词失败: {e}")
            return False

    def add_detection_record(self, user_name: str, message: str, matched_keywords: List[Dict]) -> bool:
        """
        添加检测记录
        :param user_name: 用户名
        :param message: 消息内容
        :param matched_keywords: 匹配的关键词信息
        :return: 是否成功
        """
        try:
            conn = self._get_connection()
            if not conn:
                return False
                
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO detection_records (user_name, message, matched_keywords) VALUES (%s, %s, %s)",
                    (user_name, message, json.dumps(matched_keywords, ensure_ascii=False))
                )
                conn.commit()
                return True
        except Exception as e:
            print(f"添加检测记录失败: {e}")
            return False

    def get_detection_records(self, limit: int = 100) -> List[Tuple]:
        """
        获取检测记录
        :param limit: 限制数量
        :return: 检测记录列表
        """
        try:
            conn = self._get_connection()
            if not conn:
                return []
                
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, user_name, message, matched_keywords, detection_time FROM detection_records ORDER BY detection_time DESC LIMIT %s",
                    (limit,)
                )
                return cursor.fetchall()
        except Exception as e:
            print(f"获取检测记录失败: {e}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        :return: 统计信息字典
        """
        try:
            conn = self._get_connection()
            if not conn:
                return {}
                
            with conn.cursor() as cursor:
                # 关键词总数
                cursor.execute("SELECT COUNT(*) FROM keywords")
                total_keywords = cursor.fetchone()[0]
                
                # 按类型统计关键词
                cursor.execute("SELECT type, COUNT(*) FROM keywords GROUP BY type")
                keywords_by_type = dict(cursor.fetchall())
                
                # 检测记录总数
                cursor.execute("SELECT COUNT(*) FROM detection_records")
                total_detections = cursor.fetchone()[0]
                
                # 今日检测数
                cursor.execute("SELECT COUNT(*) FROM detection_records WHERE DATE(detection_time) = CURDATE()")
                today_detections = cursor.fetchone()[0]
                
                return {
                    'total_keywords': total_keywords,
                    'keywords_by_type': keywords_by_type,
                    'total_detections': total_detections,
                    'today_detections': today_detections
                }
        except Exception as e:
            print(f"获取统计信息失败: {e}")
            return {}

    def close(self):
        """关闭数据库连接"""
        if self.connection and self.connection.open:
            self.connection.close()

    def __del__(self):
        """析构函数"""
        self.close()


# 配置管理类
class DatabaseConfig:
    """数据库配置管理"""
    
    CONFIG_FILE = "database_config.json"
    
    @classmethod
    def load_config(cls) -> Dict[str, Any]:
        """加载数据库配置"""
        if os.path.exists(cls.CONFIG_FILE):
            try:
                with open(cls.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载配置失败: {e}")
        return {}
    
    @classmethod
    def save_config(cls, config: Dict[str, Any]) -> bool:
        """保存数据库配置"""
        try:
            with open(cls.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False
    
    @classmethod
    def get_default_config(cls) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "host": "localhost",
            "port": 3306,
            "user": "root",
            "password": "",
            "database": "filter_system",
            "charset": "utf8mb4"
        }


# 示例用法
if __name__ == "__main__":
    # 测试配置
    config = {
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "password": "your_password",
        "database": "filter_system",
        "charset": "utf8mb4"
    }
    
    # 创建数据库实例
    db = MySQLKeywordDB(config)
    
    # 测试连接
    if db.test_connection():
        print("数据库连接成功")
        
        # 添加关键词
        db.add_keyword("赌博")
        db.add_keyword("色情")
        db.add_keywords([("诈骗", "fraud"), ("病毒", "malware")])
        
        # 查询关键词
        keywords = db.get_all_keywords()
        print("所有关键词:", keywords)
        
        # 获取统计信息
        stats = db.get_statistics()
        print("统计信息:", stats)
        
    else:
        print("数据库连接失败")
