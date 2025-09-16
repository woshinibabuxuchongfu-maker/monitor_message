import pymysql
import threading
from typing import List, Tuple, Dict, Any
import json
from contextlib import contextmanager

class MySQLConnectionPool:
    """
    MySQL连接池类
    使用PyMySQL实现简单的连接池功能
    """
    
    def __init__(self, connection_config: Dict[str, Any], pool_size: int = 10, max_overflow: int = 5):
        """
        初始化连接池
        :param connection_config: 数据库连接配置
        :param pool_size: 连接池大小
        :param max_overflow: 最大溢出连接数
        """
        self.connection_config = connection_config.copy()
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.max_connections = pool_size + max_overflow
        
        # 连接池存储
        self._pool = []
        self._overflow_connections = 0
        self._lock = threading.RLock()
        
        # 初始化连接池
        self._initialize_pool()

    def _initialize_pool(self):
        """初始化连接池"""
        try:
            for _ in range(self.pool_size):
                conn = self._create_connection()
                if conn:
                    self._pool.append(conn)
        except Exception as e:
            print(f"初始化连接池失败: {e}")
    
    def _create_connection(self):
        """创建新的数据库连接"""
        try:
            # 过滤掉连接池参数，只保留数据库连接参数
            db_config = {k: v for k, v in self.connection_config.items() 
                        if k not in ['pool_size', 'max_overflow']}
            
            conn = pymysql.connect(
                **db_config,
                autocommit=False
                # 使用默认的元组格式，保持与原有代码的兼容性
            )
            return conn
        except Exception as e:
            print(f"创建数据库连接失败: {e}")
            return None
    
    @contextmanager
    def get_connection(self):
        """
        获取数据库连接的上下文管理器
        使用with语句自动管理连接的获取和释放
        """
        conn = None
        try:
            conn = self._get_connection()
            if conn is None:
                raise Exception("无法获取数据库连接")
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                self._return_connection(conn)
    
    def _get_connection(self):
        """从连接池获取连接"""
        with self._lock:
            # 优先从连接池获取
            if self._pool:
                return self._pool.pop()
            
            # 连接池为空，尝试创建新连接
            if self._overflow_connections < self.max_overflow:
                conn = self._create_connection()
                if conn:
                    self._overflow_connections += 1
                    return conn
            
            # 无法获取连接，等待或抛出异常
            raise Exception("连接池已满，无法获取连接")
    
    def _return_connection(self, conn):
        """将连接返回到连接池"""
        with self._lock:
            try:
                # 检查连接是否有效
                if conn and conn.open:
                    # 重置连接状态
                    conn.rollback()
                    
                    # 如果是溢出连接，直接关闭
                    if self._overflow_connections > 0:
                        conn.close()
                        self._overflow_connections -= 1
                    # 如果是池内连接，返回池中
                    elif len(self._pool) < self.pool_size:
                        self._pool.append(conn)
                    else:
                        # 池已满，关闭连接
                        conn.close()
                else:
                    # 连接无效，减少溢出计数
                    if self._overflow_connections > 0:
                        self._overflow_connections -= 1
            except Exception as e:
                print(f"返回连接时出错: {e}")
                if conn:
                    try:
                        conn.close()
                    except:
                        pass
                if self._overflow_connections > 0:
                    self._overflow_connections -= 1
    
    def close_all(self):
        """关闭所有连接"""
        with self._lock:
            # 关闭池内连接
            for conn in self._pool:
                try:
                    if conn and conn.open:
                        conn.close()
                except:
                    pass
            self._pool.clear()
            
            # 重置溢出连接计数
            self._overflow_connections = 0
    
    def get_pool_status(self):
        """获取连接池状态"""
        with self._lock:
            return {
                'pool_size': len(self._pool),
                'max_pool_size': self.pool_size,
                'overflow_connections': self._overflow_connections,
                'max_overflow': self.max_overflow,
                'total_connections': len(self._pool) + self._overflow_connections
            }


class MySQLKeywordDBPool:
    """
    使用连接池的MySQL数据库关键词管理类
    支持连接池和关键词的增删改查操作
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, connection_config: Dict[str, Any] = None, pool_size: int = 10, max_overflow: int = 5):
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance.connection_config = connection_config
                    
                    # 从配置中提取连接池参数，如果没有则使用默认值
                    if connection_config:
                        cls._instance.pool_size = connection_config.get('pool_size', pool_size)
                        cls._instance.max_overflow = connection_config.get('max_overflow', max_overflow)
                    else:
                        cls._instance.pool_size = pool_size
                        cls._instance.max_overflow = max_overflow
                    
                    cls._instance.connection_pool = None
                    cls._instance._initialize_db()
        return cls._instance

    def _initialize_db(self):
        """初始化数据库连接池并创建表"""
        if self.connection_config:
            try:
                self.connection_pool = MySQLConnectionPool(
                    self.connection_config, 
                    self.pool_size, 
                    self.max_overflow
                )
                self._create_tables()
            except Exception as e:
                print(f"MySQL连接池初始化失败: {e}")
                self.connection_pool = None

    def _create_tables(self):
        """创建关键词表"""
        if not self.connection_pool:
            return
            
        try:
            with self.connection_pool.get_connection() as conn:
                with conn.cursor() as cursor:
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
                            douyin_id VARCHAR(255) NULL,
                            message TEXT,
                            matched_keywords JSON,
                            detection_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            INDEX idx_user (user_name),
                            INDEX idx_douyin_id (douyin_id),
                            INDEX idx_time (detection_time)
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    ''')
                    
                    # 创建聊天对话表
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS chat_conversations (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            user_name VARCHAR(255) NOT NULL,
                            douyin_id VARCHAR(255) NULL,
                            conversation_data JSON NOT NULL,
                            message_count INT DEFAULT 0,
                            last_message_time TIMESTAMP NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                            INDEX idx_user (user_name),
                            INDEX idx_chat_douyin_id (douyin_id),
                            INDEX idx_last_message_time (last_message_time),
                            INDEX idx_created_at (created_at)
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    ''')

                    # 兼容已有表，尝试添加缺失字段（忽略失败）
                    try:
                        cursor.execute("ALTER TABLE detection_records ADD COLUMN douyin_id VARCHAR(255) NULL")
                    except Exception:
                        pass
                    try:
                        cursor.execute("ALTER TABLE detection_records ADD INDEX idx_douyin_id (douyin_id)")
                    except Exception:
                        pass
                    try:
                        cursor.execute("ALTER TABLE chat_conversations ADD COLUMN douyin_id VARCHAR(255) NULL")
                    except Exception:
                        pass
                    try:
                        cursor.execute("ALTER TABLE chat_conversations ADD INDEX idx_chat_douyin_id (douyin_id)")
                    except Exception:
                        pass
                    
                    conn.commit()
        except Exception as e:
            print(f"创建表失败: {e}")

    def set_connection_config(self, config: Dict[str, Any], pool_size: int = 10, max_overflow: int = 5):
        """设置数据库连接配置"""
        self.connection_config = config
        
        # 从配置中提取连接池参数，如果没有则使用传入的参数
        if config:
            self.pool_size = config.get('pool_size', pool_size)
            self.max_overflow = config.get('max_overflow', max_overflow)
        else:
            self.pool_size = pool_size
            self.max_overflow = max_overflow
        
        if self.connection_pool:
            self.connection_pool.close_all()
        
        self._initialize_db()

    def test_connection(self) -> bool:
        """测试数据库连接"""
        try:
            if not self.connection_pool:
                return False
                
            with self.connection_pool.get_connection() as conn:
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
            if not self.connection_pool:
                return False
                
            with self.connection_pool.get_connection() as conn:
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
            if not self.connection_pool:
                return 0
                
            with self.connection_pool.get_connection() as conn:
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
            if not self.connection_pool:
                return False
                
            with self.connection_pool.get_connection() as conn:
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
            if not self.connection_pool:
                return []
                
            with self.connection_pool.get_connection() as conn:
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
            if not self.connection_pool:
                return []
                
            with self.connection_pool.get_connection() as conn:
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
            if not self.connection_pool:
                return False
                
            with self.connection_pool.get_connection() as conn:
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
            if not self.connection_pool:
                return False
                
            with self.connection_pool.get_connection() as conn:
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
            if not self.connection_pool:
                return False
                
            with self.connection_pool.get_connection() as conn:
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
            if not self.connection_pool:
                return []
                
            with self.connection_pool.get_connection() as conn:
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
            if not self.connection_pool:
                return {}
                
            with self.connection_pool.get_connection() as conn:
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

    def get_pool_status(self) -> Dict[str, Any]:
        """
        获取连接池状态信息
        :return: 连接池状态字典
        """
        if self.connection_pool:
            return self.connection_pool.get_pool_status()
        return {}

    def close(self):
        """关闭数据库连接池"""
        if self.connection_pool:
            self.connection_pool.close_all()

    def save_chat_conversation(self, user_name: str, conversation_data: List[Dict], douyin_id: str = None) -> bool:
        """
        保存聊天对话
        :param user_name: 用户名
        :param conversation_data: 对话数据，格式为 [{"sender": "A", "message": "消息内容", "timestamp": "时间"}, ...]
        :return: 是否成功
        """
        try:
            if not self.connection_pool:
                return False
                
            with self.connection_pool.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 检查是否已存在该用户的对话记录
                    cursor.execute("SELECT id, conversation_data FROM chat_conversations WHERE user_name = %s", (user_name,))
                    existing_record = cursor.fetchone()
                    
                    if existing_record:
                        # 更新现有记录
                        existing_data = json.loads(existing_record[1]) if existing_record[1] else []
                        
                        # 合并对话数据，避免重复
                        existing_messages = {msg.get('message', '') + str(msg.get('timestamp', '')): msg for msg in existing_data}
                        new_messages = {msg.get('message', '') + str(msg.get('timestamp', '')): msg for msg in conversation_data}
                        
                        # 合并数据
                        merged_messages = list(existing_messages.values())
                        for key, msg in new_messages.items():
                            if key not in existing_messages:
                                merged_messages.append(msg)
                        
                        # 按时间排序
                        merged_messages.sort(key=lambda x: x.get('timestamp', ''))
                        
                        # 更新记录（包含抖音ID）
                        if douyin_id:
                            cursor.execute(
                                "UPDATE chat_conversations SET conversation_data = %s, message_count = %s, last_message_time = %s, douyin_id = %s WHERE user_name = %s",
                                (json.dumps(merged_messages, ensure_ascii=False), len(merged_messages), 
                                 merged_messages[-1].get('timestamp') if merged_messages else None, douyin_id, user_name)
                            )
                        else:
                            cursor.execute(
                                "UPDATE chat_conversations SET conversation_data = %s, message_count = %s, last_message_time = %s WHERE user_name = %s",
                                (json.dumps(merged_messages, ensure_ascii=False), len(merged_messages), 
                                 merged_messages[-1].get('timestamp') if merged_messages else None, user_name)
                            )
                    else:
                        # 创建新记录（包含抖音ID）
                        if douyin_id:
                            cursor.execute(
                                "INSERT INTO chat_conversations (user_name, douyin_id, conversation_data, message_count, last_message_time) VALUES (%s, %s, %s, %s, %s)",
                                (user_name, douyin_id, json.dumps(conversation_data, ensure_ascii=False), len(conversation_data),
                                 conversation_data[-1].get('timestamp') if conversation_data else None)
                            )
                        else:
                            cursor.execute(
                                "INSERT INTO chat_conversations (user_name, conversation_data, message_count, last_message_time) VALUES (%s, %s, %s, %s)",
                                (user_name, json.dumps(conversation_data, ensure_ascii=False), len(conversation_data),
                                 conversation_data[-1].get('timestamp') if conversation_data else None)
                            )
                    
                    conn.commit()
                    return True
        except Exception as e:
            print(f"保存聊天对话失败: {e}")
            return False

    def get_chat_conversation(self, user_name: str) -> List[Dict]:
        """
        获取指定用户的聊天对话
        :param user_name: 用户名
        :return: 对话数据列表
        """
        try:
            if not self.connection_pool:
                return []
                
            with self.connection_pool.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT conversation_data FROM chat_conversations WHERE user_name = %s", (user_name,))
                    result = cursor.fetchone()
                    
                    if result and result[0]:
                        return json.loads(result[0])
                    return []
        except Exception as e:
            print(f"获取聊天对话失败: {e}")
            return []

    def get_all_chat_conversations(self) -> List[Tuple]:
        """
        获取所有聊天对话记录
        :return: 对话记录列表
        """
        try:
            if not self.connection_pool:
                return []
                
            with self.connection_pool.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id, user_name, message_count, last_message_time, created_at, updated_at FROM chat_conversations ORDER BY last_message_time DESC"
                    )
                    return cursor.fetchall()
        except Exception as e:
            print(f"获取所有聊天对话失败: {e}")
            return []

    def delete_chat_conversation(self, user_name: str) -> bool:
        """
        删除指定用户的聊天对话
        :param user_name: 用户名
        :return: 是否成功
        """
        try:
            if not self.connection_pool:
                return False
                
            with self.connection_pool.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM chat_conversations WHERE user_name = %s", (user_name,))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            print(f"删除聊天对话失败: {e}")
            return False

    def update_user_douyin_id(self, user_name: str, douyin_id: str) -> bool:
        """
        根据用户名更新聊天表中的 douyin_id 字段。
        :param user_name: 用户名
        :param douyin_id: 抖音ID
        :return: 是否成功
        """
        try:
            if not self.connection_pool:
                return False

            with self.connection_pool.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 先检查用户是否存在
                    cursor.execute("SELECT id FROM chat_conversations WHERE user_name = %s", (user_name,))
                    existing_record = cursor.fetchone()
                    
                    if existing_record:
                        # 更新现有记录
                        cursor.execute(
                            "UPDATE chat_conversations SET douyin_id = %s WHERE user_name = %s",
                            (douyin_id, user_name)
                        )
                        conn.commit()
                        print(f"[DEBUG] 更新用户 {user_name} 的抖音ID为 {douyin_id}")
                        return cursor.rowcount > 0
                    else:
                        print(f"[DEBUG] 用户 {user_name} 不存在于 chat_conversations 表中，无法更新抖音ID")
                        return False
        except Exception as e:
            print(f"更新 douyin_id 失败: {e}")
            return False

    def get_chat_statistics(self) -> Dict[str, Any]:
        """
        获取聊天对话统计信息
        :return: 统计信息字典
        """
        try:
            if not self.connection_pool:
                return {}
                
            with self.connection_pool.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 总对话数
                    cursor.execute("SELECT COUNT(*) FROM chat_conversations")
                    total_conversations = cursor.fetchone()[0]
                    
                    # 总消息数
                    cursor.execute("SELECT SUM(message_count) FROM chat_conversations")
                    total_messages = cursor.fetchone()[0] or 0
                    
                    # 今日新增对话数
                    cursor.execute("SELECT COUNT(*) FROM chat_conversations WHERE DATE(created_at) = CURDATE()")
                    today_conversations = cursor.fetchone()[0]
                    
                    # 最近活跃用户
                    cursor.execute(
                        "SELECT user_name, last_message_time FROM chat_conversations ORDER BY last_message_time DESC LIMIT 5"
                    )
                    recent_users = cursor.fetchall()
                    
                    return {
                        'total_conversations': total_conversations,
                        'total_messages': total_messages,
                        'today_conversations': today_conversations,
                        'recent_users': recent_users
                    }
        except Exception as e:
            print(f"获取聊天统计信息失败: {e}")
            return {}

    def batch_save_chat_conversations(self, conversations_data: Dict[str, List[Dict]], user_to_douyin_id: Dict[str, str] = None) -> int:
        """
        批量保存聊天对话
        :param conversations_data: 对话数据字典，格式为 {user_name: [conversation_data, ...], ...}
        :param user_to_douyin_id: 用户到抖音ID的映射，格式为 {user_name: douyin_id, ...}
        :return: 成功保存的用户数量
        """
        try:
            if not self.connection_pool or not conversations_data:
                return 0
                
            saved_count = 0
            with self.connection_pool.get_connection() as conn:
                with conn.cursor() as cursor:
                    for user_name, conversation_data in conversations_data.items():
                        try:
                            # 检查是否已存在该用户的对话记录
                            cursor.execute("SELECT id, conversation_data FROM chat_conversations WHERE user_name = %s", (user_name,))
                            existing_record = cursor.fetchone()
                            
                            if existing_record:
                                # 更新现有记录
                                existing_data = json.loads(existing_record[1]) if existing_record[1] else []
                                
                                # 合并对话数据，避免重复
                                existing_messages = {msg.get('message', '') + str(msg.get('timestamp', '')): msg for msg in existing_data}
                                new_messages = {msg.get('message', '') + str(msg.get('timestamp', '')): msg for msg in conversation_data}
                                
                                # 合并数据
                                merged_messages = list(existing_messages.values())
                                for key, msg in new_messages.items():
                                    if key not in existing_messages:
                                        merged_messages.append(msg)
                                
                                # 按时间排序
                                merged_messages.sort(key=lambda x: x.get('timestamp', ''))
                                
                                # 更新记录（包含抖音ID）
                                douyin_id = user_to_douyin_id.get(user_name) if user_to_douyin_id else None
                                if douyin_id:
                                    cursor.execute(
                                        "UPDATE chat_conversations SET conversation_data = %s, message_count = %s, last_message_time = %s, douyin_id = %s WHERE user_name = %s",
                                        (json.dumps(merged_messages, ensure_ascii=False), len(merged_messages), 
                                         merged_messages[-1].get('timestamp') if merged_messages else None, douyin_id, user_name)
                                    )
                                else:
                                    cursor.execute(
                                        "UPDATE chat_conversations SET conversation_data = %s, message_count = %s, last_message_time = %s WHERE user_name = %s",
                                        (json.dumps(merged_messages, ensure_ascii=False), len(merged_messages), 
                                         merged_messages[-1].get('timestamp') if merged_messages else None, user_name)
                                    )
                            else:
                                # 创建新记录（包含抖音ID）
                                douyin_id = user_to_douyin_id.get(user_name) if user_to_douyin_id else None
                                if douyin_id:
                                    cursor.execute(
                                        "INSERT INTO chat_conversations (user_name, douyin_id, conversation_data, message_count, last_message_time) VALUES (%s, %s, %s, %s, %s)",
                                        (user_name, douyin_id, json.dumps(conversation_data, ensure_ascii=False), len(conversation_data),
                                         conversation_data[-1].get('timestamp') if conversation_data else None)
                                    )
                                else:
                                    cursor.execute(
                                        "INSERT INTO chat_conversations (user_name, conversation_data, message_count, last_message_time) VALUES (%s, %s, %s, %s)",
                                        (user_name, json.dumps(conversation_data, ensure_ascii=False), len(conversation_data),
                                         conversation_data[-1].get('timestamp') if conversation_data else None)
                                    )
                            
                            saved_count += 1
                            
                        except Exception as e:
                            print(f"保存用户 {user_name} 的对话数据失败: {e}")
                            continue
                    
                    conn.commit()
                    return saved_count
                    
        except Exception as e:
            print(f"批量保存聊天对话失败: {e}")
            return 0

    def batch_save_detection_records(self, detection_records: List[Dict]) -> int:
        """
        批量保存检测记录
        :param detection_records: 检测记录列表
        :return: 成功保存的记录数量
        """
        try:
            if not self.connection_pool or not detection_records:
                return 0
                
            saved_count = 0
            with self.connection_pool.get_connection() as conn:
                with conn.cursor() as cursor:
                    for detection_result in detection_records:
                        try:
                            # 准备匹配关键词数据
                            matched_keywords = []
                            for match in detection_result.get('matches', []):
                                if hasattr(match.keyword, 'keyword'):
                                    matched_keywords.append({
                                        'keyword': match.keyword.keyword,
                                        'type': match.keyword.type,
                                        'match_type': match.match_type,
                                        'start': match.start,
                                        'end': match.end
                                    })
                                else:
                                    matched_keywords.append({
                                        'keyword': str(match.keyword),
                                        'type': 'unknown',
                                        'match_type': match.match_type,
                                        'start': match.start,
                                        'end': match.end
                                    })
                            
                            # 插入检测记录
                            cursor.execute(
                                "INSERT INTO detection_records (user_name, message, matched_keywords) VALUES (%s, %s, %s)",
                                (detection_result['user'], detection_result['message'], json.dumps(matched_keywords, ensure_ascii=False))
                            )
                            
                            saved_count += 1
                            
                        except Exception as e:
                            print(f"保存检测记录失败: {e}")
                            continue
                    
                    conn.commit()
                    return saved_count
                    
        except Exception as e:
            print(f"批量保存检测记录失败: {e}")
            return 0

    def __del__(self):
        """析构函数"""
        self.close()


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
    
    # 创建数据库实例（使用连接池）
    db = MySQLKeywordDBPool(config, pool_size=5, max_overflow=3)
    
    # 测试连接
    if db.test_connection():
        print("数据库连接成功")
        
        # 查看连接池状态
        pool_status = db.get_pool_status()
        print("连接池状态:", pool_status)
        
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
        
        # 再次查看连接池状态
        pool_status = db.get_pool_status()
        print("使用后连接池状态:", pool_status)
        
    else:
        print("数据库连接失败")
