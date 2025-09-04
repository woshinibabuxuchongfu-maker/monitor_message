#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
关键词管理组件
"""

import sys
import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLineEdit, QPushButton, QLabel, QCheckBox, QGroupBox,
                             QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
                             QMessageBox, QFileDialog, QComboBox, QDialog)
from PyQt5.QtCore import Qt

# 导入项目模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.sqlite_db import KeywordDB
from database.mysql_db import MySQLKeywordDB
from config.database_config import DatabaseConfig
from config.system_config import Config


class KeywordManagerWidget(QWidget):
    """关键词管理组件"""
    
    def __init__(self):
        super().__init__()
        self.db = None  # 数据库实例，将在连接后设置
        self.use_mysql = True  # 默认使用MySQL
        self.init_ui()
        self.setup_database()
    
    def init_ui(self):
        layout = QVBoxLayout()

        # 数据库选择区域
        db_group = QGroupBox("数据库选择")
        db_layout = QHBoxLayout()

        self.mysql_radio = QCheckBox("使用MySQL数据库")
        self.mysql_radio.setChecked(True)
        self.mysql_radio.toggled.connect(self.on_database_type_changed)

        self.sqlite_radio = QCheckBox("使用SQLite数据库")
        self.sqlite_radio.toggled.connect(self.on_database_type_changed)

        self.db_config_btn = QPushButton("配置MySQL连接")
        self.db_config_btn.clicked.connect(self.show_db_config)

        db_layout.addWidget(self.mysql_radio)
        db_layout.addWidget(self.sqlite_radio)
        db_layout.addWidget(self.db_config_btn)
        db_layout.addStretch()

        db_group.setLayout(db_layout)
        
        # 操作区域
        operation_group = QGroupBox("关键词操作")
        operation_layout = QHBoxLayout()
        
        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("输入关键词...")
        self.keyword_input.returnPressed.connect(self.add_keyword)
        
        self.keyword_type_combo = QComboBox()
        self.keyword_type_combo.addItems(list(Config.KEYWORD_TYPES.keys()))
        self.keyword_type_combo.setCurrentText("keyword")
        
        self.add_btn = QPushButton("添加")
        self.add_btn.clicked.connect(self.add_keyword)
        
        self.delete_btn = QPushButton("删除选中")
        self.delete_btn.clicked.connect(self.delete_selected)
        
        self.clear_btn = QPushButton("清空所有")
        self.clear_btn.clicked.connect(self.clear_all)
        
        self.import_btn = QPushButton("导入文件")
        self.import_btn.clicked.connect(self.import_keywords)
        
        self.export_btn = QPushButton("导出文件")
        self.export_btn.clicked.connect(self.export_keywords)
        
        operation_layout.addWidget(QLabel("关键词:"))
        operation_layout.addWidget(self.keyword_input)
        operation_layout.addWidget(QLabel("类型:"))
        operation_layout.addWidget(self.keyword_type_combo)
        operation_layout.addWidget(self.add_btn)
        operation_layout.addWidget(self.delete_btn)
        operation_layout.addWidget(self.clear_btn)
        operation_layout.addWidget(self.import_btn)
        operation_layout.addWidget(self.export_btn)
        operation_layout.addStretch()
        
        operation_group.setLayout(operation_layout)
        
        # 关键词列表
        self.keyword_table = QTableWidget()
        self.keyword_table.setColumnCount(4)
        self.keyword_table.setHorizontalHeaderLabels(["ID", "关键词", "类型", "创建时间"])
        self.keyword_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.keyword_table.setSelectionBehavior(QAbstractItemView.SelectRows)

        layout.addWidget(db_group)
        layout.addWidget(operation_group)
        layout.addWidget(self.keyword_table)
        
        self.setLayout(layout)
    
    def setup_database(self):
        """设置数据库连接"""
        if self.use_mysql:
            config = DatabaseConfig.load_config()
            if config:
                self.db = MySQLKeywordDB(config)
            else:
                QMessageBox.information(self, "提示", "请先配置MySQL数据库连接")
        else:
            self.db = KeywordDB("BaseData/violation_keywords.db")
        
        if self.db:
            self.load_keywords()
    
    def on_database_type_changed(self):
        """数据库类型切换"""
        if self.sender() == self.mysql_radio and self.mysql_radio.isChecked():
            self.use_mysql = True
            self.sqlite_radio.setChecked(False)
        elif self.sender() == self.sqlite_radio and self.sqlite_radio.isChecked():
            self.use_mysql = False
            self.mysql_radio.setChecked(False)
        
        self.setup_database()
    
    def show_db_config(self):
        """显示数据库配置对话框"""
        from .database_config_dialog import DatabaseConfigDialog
        dialog = DatabaseConfigDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.setup_database()
    
    def load_keywords(self):
        """加载关键词列表"""
        if not self.db:
            return

        keywords = self.db.get_all_keywords()

        if self.use_mysql:
            keywords = sorted(keywords , key=lambda x: x[0])
        else:
            pass
        self.keyword_table.setRowCount(len(keywords))

        #去行号
        self.keyword_table.verticalHeader().setVisible(False)

        for i, keyword_data in enumerate(keywords):
            if self.use_mysql:
                keyword_id, keyword, keyword_type, created_at = keyword_data
                self.keyword_table.setItem(i, 0, QTableWidgetItem(str(keyword_id)))
                self.keyword_table.setItem(i, 1, QTableWidgetItem(keyword))
                self.keyword_table.setItem(i, 2, QTableWidgetItem(keyword_type))
                self.keyword_table.setItem(i, 3, QTableWidgetItem(str(created_at)))
            else:
                # SQLite返回格式: keyword字符串
                self.keyword_table.setItem(i, 0, QTableWidgetItem(str(keyword_id)))
                self.keyword_table.setItem(i, 1, QTableWidgetItem(keyword_data))
                self.keyword_table.setItem(i, 2, QTableWidgetItem("keyword"))
                self.keyword_table.setItem(i, 3, QTableWidgetItem(""))
    
    def add_keyword(self):
        """添加关键词"""
        keyword = self.keyword_input.text().strip()
        keyword_type = self.keyword_type_combo.currentText()
        
        if keyword:
            if self.use_mysql:
                success = self.db.add_keyword(keyword, keyword_type)
            else:
                success = self.db.add_keyword(keyword)
                
            if success:
                self.load_keywords()
                self.keyword_input.clear()
                QMessageBox.information(self, "成功", f"关键词 '{keyword}' 添加成功")
            else:
                QMessageBox.warning(self, "警告", f"关键词 '{keyword}' 已存在")
    
    def delete_selected(self):
        """删除选中的关键词"""
        current_row = self.keyword_table.currentRow()
        if current_row >= 0:
            keyword = self.keyword_table.item(current_row, 1).text()
            reply = QMessageBox.question(self, "确认删除", f"确定要删除关键词 '{keyword}' 吗？")
            if reply == QMessageBox.Yes:
                if self.db.remove_keyword(keyword):
                    self.load_keywords()
                    QMessageBox.information(self, "成功", "删除成功")
    
    def clear_all(self):
        """清空所有关键词"""
        reply = QMessageBox.question(self, "确认清空", "确定要清空所有关键词吗？此操作不可恢复！")
        if reply == QMessageBox.Yes:
            if self.db.clear_all_keywords():
                self.load_keywords()
                QMessageBox.information(self, "成功", "清空成功")
    
    def import_keywords(self):
        """从文件导入关键词"""
        file_path, _ = QFileDialog.getOpenFileName(self, "选择关键词文件", "", "文本文件 (*.txt)")
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    keywords = [line.strip() for line in f if line.strip()]
                
                if self.use_mysql:
                    # MySQL批量添加
                    keyword_tuples = [(kw, "keyword") for kw in keywords]
                    count = self.db.add_keywords(keyword_tuples)
                else:
                    # SQLite批量添加
                    count = self.db.add_keywords(keywords)
                
                self.load_keywords()
                QMessageBox.information(self, "导入成功", f"成功导入 {count} 个关键词")
            except Exception as e:
                QMessageBox.critical(self, "导入失败", f"导入失败: {str(e)}")
    
    def export_keywords(self):
        """导出关键词到文件"""
        file_path, _ = QFileDialog.getSaveFileName(self, "保存关键词文件", "keywords.txt", "文本文件 (*.txt)")
        if file_path:
            try:
                keywords = self.db.get_all_keywords()
                with open(file_path, 'w', encoding='utf-8') as f:
                    if self.use_mysql:
                        for keyword_data in keywords:
                            f.write(f"{keyword_data[1]}\n")  # 只写入关键词
                    else:
                        for keyword in keywords:
                            f.write(f"{keyword}\n")
                QMessageBox.information(self, "导出成功", f"成功导出 {len(keywords)} 个关键词")
            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"导出失败: {str(e)}")
