
import sys
import os
import time
from datetime import datetime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                            QLineEdit, QPushButton, QLabel, QTableWidget, 
                            QTableWidgetItem, QHeaderView)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# 导入项目模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Test.Filter import KeywordMatcher
from Test.GetDouyinMsg import GetDouyinMsg
from config.system_config import Config


class MessageDetectionThread(QThread):
    """消息检测线程"""
    message_detected = pyqtSignal(dict)  # 检测到违规消息时发出信号
    status_update = pyqtSignal(str)      # 状态更新信号
    
    def __init__(self, matcher, douyin_msg):
        super().__init__()
        self.matcher = matcher
        self.douyin_msg = douyin_msg
        self.running = False
        
    def run(self):
        self.running = True
        self.status_update.emit("开始监控消息...")
        
        while self.running:
            try:
                # 获取用户列表
                user_list = self.douyin_msg._get_user_list()
                if user_list:
                    for user in user_list:
                        if not self.running:
                            break
                            
                        user_name = user.child().child().child().text
                        self.status_update.emit(f"检查用户: {user_name}")
                        
                        # 点击用户获取消息
                        user.click()
                        time.sleep(1)
                        
                        # 获取消息内容
                        messages = self.douyin_msg.tab.eles('xpath=//*[@class=\'leadsCsUI-MessageItem\']//*[@class=\'leadsCsUI-Text\']')
                        
                        for msg_element in messages:
                            if not self.running:
                                break
                                
                            message_text = msg_element.text
                            if message_text:
                                # 检测违规内容
                                matches = list(self.matcher.search(message_text))
                                if matches:
                                    detection_result = {
                                        'user': user_name,
                                        'message': message_text,
                                        'matches': matches,
                                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                    }
                                    self.message_detected.emit(detection_result)
                
                time.sleep(Config.DETECTION_INTERVAL)  # 使用配置的检测间隔
                
            except Exception as e:
                self.status_update.emit(f"检测错误: {str(e)}")
                time.sleep(10)
    
    def stop(self):
        self.running = False
        self.status_update.emit("停止监控")


class MessageDetectionWidget(QWidget):
    """消息检测监控组件"""
    
    def __init__(self):
        super().__init__()
        self.matcher = KeywordMatcher()
        self.douyin_msg = GetDouyinMsg()
        self.detection_thread = None
        self.init_ui()
        self.load_matcher()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 控制区域
        control_group = QGroupBox("检测控制")
        control_layout = QHBoxLayout()
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("输入抖音客服URL...")
        self.url_input.setText(Config.DEFAULT_DOUYIN_URL)
        
        self.set_url_btn = QPushButton("设置URL")
        self.set_url_btn.clicked.connect(self.set_url)
        
        self.start_btn = QPushButton("开始监控")
        self.start_btn.clicked.connect(self.start_detection)
        
        self.stop_btn = QPushButton("停止监控")
        self.stop_btn.clicked.connect(self.stop_detection)
        self.stop_btn.setEnabled(False)
        
        self.status_label = QLabel("状态: 未启动")
        
        control_layout.addWidget(QLabel("URL:"))
        control_layout.addWidget(self.url_input)
        control_layout.addWidget(self.set_url_btn)
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addWidget(self.status_label)
        control_layout.addStretch()
        
        control_group.setLayout(control_layout)
        
        # 检测结果区域
        result_group = QGroupBox("检测结果")
        result_layout = QVBoxLayout()
        
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(4)
        self.result_table.setHorizontalHeaderLabels(["时间", "用户", "消息", "匹配结果"])
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        result_layout.addWidget(self.result_table)
        result_group.setLayout(result_layout)
        
        layout.addWidget(control_group)
        layout.addWidget(result_group)
        
        self.setLayout(layout)
    
    def load_matcher(self):
        """加载匹配器"""
        try:
            if os.path.exists(Config.MATCHER_SAVE_PATH):
                self.matcher.load(Config.MATCHER_SAVE_PATH)
            else:
                # 从数据库加载关键词
                from database.mysql_db import MySQLKeywordDB
                from database.sqlite_db import KeywordDB
                from config.database_config import DatabaseConfig
                
                # 尝试使用MySQL，如果失败则使用SQLite
                try:
                    config = DatabaseConfig.load_config()
                    if config:
                        db = MySQLKeywordDB(config)
                        if db.test_connection():
                            keywords = db.get_all_keywords()
                            for keyword_data in keywords:
                                from BaseData.KeyWord import KeyWord
                                kw_obj = KeyWord(keyword_data[1], keyword_data[2])  # keyword, type
                                self.matcher.add_keyword(kw_obj)
                        else:
                            raise Exception("MySQL连接失败")
                    else:
                        raise Exception("MySQL配置不存在")
                except:
                    # 回退到SQLite
                    db = KeywordDB("BaseData/violation_keywords.db")
                    keywords = db.get_all_keywords()
                    for keyword in keywords:
                        from BaseData.KeyWord import KeyWord
                        kw_obj = KeyWord(keyword)
                        self.matcher.add_keyword(kw_obj)
                
                self.matcher.build()
        except Exception as e:
            QMessageBox.warning(self, "警告", f"加载匹配器失败: {str(e)}")
    
    def set_url(self):
        """设置URL"""
        url = self.url_input.text().strip()
        if url:
            self.douyin_msg.set_url(url)
            QMessageBox.information(self, "成功", "URL设置成功")
    
    def start_detection(self):
        """开始检测"""
        if not self.douyin_msg.get_url():
            QMessageBox.warning(self, "警告", "请先设置URL")
            return
        
        self.detection_thread = MessageDetectionThread(self.matcher, self.douyin_msg)
        self.detection_thread.message_detected.connect(self.add_detection_result)
        self.detection_thread.status_update.connect(self.update_status)
        self.detection_thread.start()
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
    
    def stop_detection(self):
        """停止检测"""
        if self.detection_thread:
            self.detection_thread.stop()
            self.detection_thread.wait()
            self.detection_thread = None
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("状态: 已停止")
    
    def add_detection_result(self, result):
        """添加检测结果"""
        row = self.result_table.rowCount()
        self.result_table.insertRow(row)
        
        self.result_table.setItem(row, 0, QTableWidgetItem(result['timestamp']))
        self.result_table.setItem(row, 1, QTableWidgetItem(result['user']))
        self.result_table.setItem(row, 2, QTableWidgetItem(result['message']))
        
        matches_text = ", ".join([f"{m.keyword.keyword if hasattr(m.keyword, 'keyword') else m.keyword}({m.match_type})" 
                                for m in result['matches']])
        self.result_table.setItem(row, 3, QTableWidgetItem(matches_text))
    
    def update_status(self, status):
        """更新状态"""
        self.status_label.setText(f"状态: {status}")
