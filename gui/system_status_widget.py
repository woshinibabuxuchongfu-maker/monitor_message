#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统状态监控组件
"""

import sys
import os
from datetime import datetime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QLabel, 
                            QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt5.QtCore import Qt, QTimer

# 导入项目模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.mysql_db import MySQLKeywordDB
from database.sqlite_db import KeywordDB
from config.database_config import DatabaseConfig
from config.system_config import Config


class SystemStatusWidget(QWidget):
    """系统状态监控组件"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(5000)  # 每5秒更新一次
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 系统信息
        info_group = QGroupBox("系统信息")
        info_layout = QVBoxLayout()
        
        self.keyword_count_label = QLabel("关键词数量: 0")
        self.matcher_status_label = QLabel("匹配器状态: 未加载")
        self.db_status_label = QLabel("数据库状态: 未连接")
        self.system_time_label = QLabel("系统时间: --")
        
        info_layout.addWidget(self.keyword_count_label)
        info_layout.addWidget(self.matcher_status_label)
        info_layout.addWidget(self.db_status_label)
        info_layout.addWidget(self.system_time_label)
        
        info_group.setLayout(info_layout)
        
        # 数据库统计信息
        stats_group = QGroupBox("数据库统计")
        stats_layout = QVBoxLayout()
        
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(2)
        self.stats_table.setHorizontalHeaderLabels(["统计项目", "数值"])
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stats_table.setMaximumHeight(150)
        
        stats_layout.addWidget(self.stats_table)
        stats_group.setLayout(stats_layout)
        
        # 日志区域
        log_group = QGroupBox("系统日志")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(200)
        self.log_text.setReadOnly(True)
        
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        
        layout.addWidget(info_group)
        layout.addWidget(stats_group)
        layout.addWidget(log_group)
        
        self.setLayout(layout)
        self.update_status()
        self.add_log("系统启动完成")
    
    def update_status(self):
        """更新系统状态"""
        try:
            # 更新系统时间
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.system_time_label.setText(f"系统时间: {current_time}")
            
            # 更新关键词数量
            keyword_count = 0
            db_type = "未连接"
            
            # 尝试连接MySQL
            try:
                config = DatabaseConfig.load_config()
                if config:
                    db = MySQLKeywordDB(config)
                    if db.test_connection():
                        keywords = db.get_all_keywords()
                        keyword_count = len(keywords)
                        db_type = "MySQL"
                        
                        # 更新统计信息
                        self.update_stats_table(db)
                    else:
                        raise Exception("MySQL连接失败")
                else:
                    raise Exception("MySQL配置不存在")
            except:
                # 回退到SQLite
                try:
                    db = KeywordDB("BaseData/violation_keywords.db")
                    keywords = db.get_all_keywords()
                    keyword_count = len(keywords)
                    db_type = "SQLite"
                except Exception as e:
                    db_type = f"错误: {str(e)}"
            
            self.keyword_count_label.setText(f"关键词数量: {keyword_count}")
            self.db_status_label.setText(f"数据库状态: {db_type}")
            
            # 更新匹配器状态
            if os.path.exists(Config.MATCHER_SAVE_PATH):
                self.matcher_status_label.setText("匹配器状态: 已加载")
            else:
                self.matcher_status_label.setText("匹配器状态: 未保存")
                
        except Exception as e:
            self.db_status_label.setText(f"数据库状态: 错误 - {str(e)}")
    
    def update_stats_table(self, db):
        """更新统计信息表格"""
        try:
            if hasattr(db, 'get_statistics'):
                stats = db.get_statistics()
                
                stats_data = [
                    ("关键词总数", str(stats.get('total_keywords', 0))),
                    ("检测记录总数", str(stats.get('total_detections', 0))),
                    ("今日检测数", str(stats.get('today_detections', 0))),
                ]
                
                # 添加按类型统计的关键词
                keywords_by_type = stats.get('keywords_by_type', {})
                for keyword_type, count in keywords_by_type.items():
                    type_name = Config.KEYWORD_TYPES.get(keyword_type, keyword_type)
                    stats_data.append((f"关键词类型({type_name})", str(count)))
                
                self.stats_table.setRowCount(len(stats_data))
                for i, (key, value) in enumerate(stats_data):
                    self.stats_table.setItem(i, 0, QTableWidgetItem(key))
                    self.stats_table.setItem(i, 1, QTableWidgetItem(value))
            else:
                # SQLite数据库没有统计功能
                self.stats_table.setRowCount(0)
        except Exception as e:
            self.stats_table.setRowCount(0)
    
    def add_log(self, message):
        """添加日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.log_text.append(f"[{timestamp}] {message}")
        
        # 限制日志行数
        if self.log_text.document().blockCount() > Config.LOG_MAX_LINES:
            cursor = self.log_text.textCursor()
            cursor.movePosition(cursor.Start)
            cursor.movePosition(cursor.Down, cursor.KeepAnchor, 10)  # 删除前10行
            cursor.removeSelectedText()
    
    def clear_log(self):
        """清空日志"""
        self.log_text.clear()
        self.add_log("日志已清空")
