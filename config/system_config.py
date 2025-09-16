
import os
from typing import Dict, Any

class Config:
    """系统配置类"""
    
    # 数据库配置
    DATABASE_PATH = "BaseData/violation_keywords.db"
    MYSQL_CONFIG_FILE = "config/database_config.json"
    
    # MySQL默认配置
    MYSQL_DEFAULT_CONFIG = {
        "host": "192.168.100.27",
        "port": 3306,
        "user": "zmonv",
        "password": "rpa@2025",
        "database": "test_zmonv_rpa",
        "charset": "utf8mb4"
    }
    
    # 匹配器配置
    MATCHER_SAVE_PATH = "data/keyword_matcher.pkl"
    
    # 默认抖音URL
    DEFAULT_DOUYIN_URL = "https://leads.cluerich.com/pc/cs/chat/session?fullscreen=1"
    
    # 检测配置
    DETECTION_INTERVAL = 10  # 检测间隔（秒）
    MAX_MESSAGE_LENGTH = 1000  # 最大消息长度
    
    # 界面配置
    WINDOW_TITLE = "消息违规检测系统管理界面"
    WINDOW_SIZE = (1200, 800)
    WINDOW_POSITION = (100, 100)
    
    # 日志配置
    LOG_MAX_LINES = 1000
    LOG_LEVEL = "INFO"
    LOG_FILE = "logs/system.log"
    
    # 模糊匹配配置
    FUZZY_MATCH_ENABLED = True
    FUZZY_MAX_DISTANCE = 1
    
    # 正则表达式配置
    REGEX_PATTERNS = {
        "phone": r"\d{3}-\d{3}-\d{4}",
        "email": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        "url": r"https?://[^\s]+",
        "id_card": r"\d{17}[\dXx]",
        "bank_card": r"\d{16,19}"
    }
    
    # 关键词类型配置
    KEYWORD_TYPES = {
        "keyword": "普通关键词",
        "fraud": "诈骗类",
        "malware": "恶意软件类",
        "spam": "垃圾信息类",
        "adult": "成人内容类",
        "violence": "暴力内容类",
        "politics": "政治敏感类",
        "terrorism": "恐怖主义类"
    }
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """获取所有配置"""
        return {
            'database_path': cls.DATABASE_PATH,
            'mysql_config_file': cls.MYSQL_CONFIG_FILE,
            'mysql_default_config': cls.MYSQL_DEFAULT_CONFIG,
            'matcher_save_path': cls.MATCHER_SAVE_PATH,
            'default_douyin_url': cls.DEFAULT_DOUYIN_URL,
            'detection_interval': cls.DETECTION_INTERVAL,
            'max_message_length': cls.MAX_MESSAGE_LENGTH,
            'window_title': cls.WINDOW_TITLE,
            'window_size': cls.WINDOW_SIZE,
            'window_position': cls.WINDOW_POSITION,
            'log_max_lines': cls.LOG_MAX_LINES,
            'log_level': cls.LOG_LEVEL,
            'log_file': cls.LOG_FILE,
            'fuzzy_match_enabled': cls.FUZZY_MATCH_ENABLED,
            'fuzzy_max_distance': cls.FUZZY_MAX_DISTANCE,
            'regex_patterns': cls.REGEX_PATTERNS,
            'keyword_types': cls.KEYWORD_TYPES
        }
    
    @classmethod
    def ensure_directories(cls):
        """确保必要的目录存在"""
        directories = [
            "BaseData",
            "function",
            "logs",
            "data",
            "config"
        ]
        
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                print(f"创建目录: {directory}")
    
    @classmethod
    def validate_config(cls) -> bool:
        """验证配置"""
        try:
            # 检查必要的目录
            cls.ensure_directories()
            
            # 检查日志目录
            if not os.path.exists("logs"):
                os.makedirs("logs")
            
            # 检查数据目录
            if not os.path.exists("data"):
                os.makedirs("data")
            
            return True
            
        except Exception as e:
            print(f"配置验证失败: {str(e)}")
            return False

# 全局配置实例
config = Config()
