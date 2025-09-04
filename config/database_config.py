#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库配置管理
"""

import os
import json
from typing import Dict, Any

class DatabaseConfig:
    """数据库配置管理类"""
    
    CONFIG_FILE = "config/database_config.json"
    
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
            # 确保config目录存在
            os.makedirs(os.path.dirname(cls.CONFIG_FILE), exist_ok=True)
            
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
            "host": "192.168.100.27",
            "port": 3306,
            "user": "zmonv",
            "password": "rpa@2025",
            "database": "test_zmonv_rpa",
            "charset": "utf8mb4"
        }
    
    @classmethod
    def validate_config(cls, config: Dict[str, Any]) -> tuple[bool, str]:
        """验证配置"""
        required_fields = ["host", "port", "user", "database"]
        
        for field in required_fields:
            if not config.get(field):
                return False, f"缺少必填字段: {field}"
        
        # 验证端口号
        try:
            port = int(config.get("port", 0))
            if not (1 <= port <= 65535):
                return False, "端口号必须在1-65535之间"
        except ValueError:
            return False, "端口号必须是数字"
        
        return True, "配置验证通过"
    
    @classmethod
    def get_connection_string(cls, config: Dict[str, Any]) -> str:
        """获取连接字符串（用于显示）"""
        return f"mysql://{config.get('user', '')}@{config.get('host', '')}:{config.get('port', '')}/{config.get('database', '')}"
