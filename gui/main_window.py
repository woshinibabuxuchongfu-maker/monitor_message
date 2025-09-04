#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口
"""

import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QTabWidget, QStatusBar, QMenuBar, QAction, QMessageBox)
from PyQt5.QtCore import QSettings

# 导入项目模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .keyword_manager_widget import KeywordManagerWidget
from .message_detection_widget import MessageDetectionWidget
from .database_config_dialog import DatabaseManagerWidget
from .system_status_widget import SystemStatusWidget


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.settings = QSettings("FilterSystem", "MainWindow")
        self.init_ui()
        self.restore_settings()
    
    def init_ui(self):
        self.setWindowTitle("消息违规检测系统管理界面")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("系统就绪")
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建标签页
        self.tab_widget = QTabWidget()


        # 消息检测标签页
        self.detection_widget = MessageDetectionWidget()
        self.tab_widget.addTab(self.detection_widget, "消息检测")

        # 关键词管理标签页
        self.keyword_widget = KeywordManagerWidget()
        self.tab_widget.addTab(self.keyword_widget, "关键词管理")
        

        
        # 数据库管理标签页
        self.database_widget = DatabaseManagerWidget()
        self.tab_widget.addTab(self.database_widget, "数据库管理")
        
        # 系统状态标签页
        self.status_widget = SystemStatusWidget()
        self.tab_widget.addTab(self.status_widget, "系统状态")
        
        # 布局
        layout = QVBoxLayout()
        layout.addWidget(self.tab_widget)
        central_widget.setLayout(layout)
    
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        save_action = QAction('保存配置', self)
        save_action.triggered.connect(self.save_settings)
        file_menu.addAction(save_action)
        
        load_action = QAction('加载配置', self)
        load_action.triggered.connect(self.load_settings)
        file_menu.addAction(load_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('退出', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        about_action = QAction('关于', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def save_settings(self):
        """保存设置"""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        QMessageBox.information(self, "成功", "设置已保存")
    
    def load_settings(self):
        """加载设置"""
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        window_state = self.settings.value("windowState")
        if window_state:
            self.restoreState(window_state)
    
    def restore_settings(self):
        """恢复设置"""
        self.load_settings()
    
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于", 
                         "消息违规检测系统 v1.0\n\n"
                         "基于关键字匹配、正则表达式和模糊匹配的\n"
                         "智能消息违规检测系统")
    
    def closeEvent(self, event):
        """关闭事件"""
        # 停止检测线程
        if hasattr(self.detection_widget, 'detection_thread') and self.detection_widget.detection_thread:
            self.detection_widget.stop_detection()
        
        # 保存设置
        self.save_settings()
        event.accept()


def main():
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle('Fusion')
    
    # 创建主窗口
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
