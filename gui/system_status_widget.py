
import sys
import os
from datetime import datetime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QLabel, 
                            QTextEdit, QPushButton, QHBoxLayout, QLineEdit, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal

# 导入项目模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.mysql_pool_db import MySQLKeywordDBPool
from database.sqlite_db import KeywordDB
from config.database_config import DatabaseConfig
from config.system_config import Config
from function.GetDouyinMsg import GetDouyinMsg
from function.Filter import KeywordMatcher


class UserMessageLogThread(QThread):
    """后台线程：抓取用户消息并输出为日志"""
    log_line = pyqtSignal(str)
    status_line = pyqtSignal(str)

    def __init__(self, douyin_msg: GetDouyinMsg, poll_interval_sec: int = 3):
        super().__init__()
        self.douyin_msg = douyin_msg
        self.poll_interval_sec = poll_interval_sec
        self._running = False
        self._seen_keys = set()

    def run(self):
        import time
        self._running = True
        self.status_line.emit("开始获取用户消息日志…")
        last_check = 0
        CHECK_INTERVAL = 60
        while self._running:
            try:
                if not self.douyin_msg.is_connected():
                    self.status_line.emit("浏览器未连接或未打开目标页，等待中…")
                    time.sleep(5)
                    continue

                # 不主动刷新页面，只做轻量连接检查
                now = time.time()
                if now - last_check > CHECK_INTERVAL:
                    try:
                        _ = self.douyin_msg.tab.url
                    except Exception as e:
                        self.status_line.emit(f"连接检查失败: {e}")
                    last_check = now

                # 优先抓取当前会话消息文本
                try:
                    msg_nodes = self.douyin_msg.tab.eles("xpath=//*[@class='leadsCsUI-MessageItem']//*[@class='leadsCsUI-Text']")
                    for node in msg_nodes[-100:]:  # 仅查看最近的消息，避免过多日志
                        try:
                            text = node.text
                            if not text:
                                continue
                            # 去重：使用文本+index作为粗略key
                            key = f"{hash(text)}"
                            if key in self._seen_keys:
                                continue
                            self._seen_keys.add(key)
                            self.log_line.emit(text)
                        except Exception:
                            continue
                except Exception as e:
                    self.status_line.emit(f"获取消息失败: {e}")

                # 限制已见集合大小
                if len(self._seen_keys) > 5000:
                    # 简单清理，防止内存增长
                    self._seen_keys = set(list(self._seen_keys)[-1000:])

                time.sleep(self.poll_interval_sec)
            except Exception as e:
                self.status_line.emit(f"消息抓取线程异常: {e}")
                time.sleep(5)

    def stop(self):
        self._running = False


class SystemStatusWidget(QWidget):
    """系统状态监控组件"""
    
    def __init__(self):
        super().__init__()
        self.message_thread = None
        self.douyin_msg = GetDouyinMsg()
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
        
        # 消息检测控制区域（红框1位置，占比小）
        detection_group = QGroupBox("消息检测控制")
        detection_layout = QVBoxLayout()
        
        controls_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        from config.system_config import Config as _Cfg
        self.url_input.setPlaceholderText("输入抖音客服URL...")
        self.url_input.setText(_Cfg.DEFAULT_DOUYIN_URL)

        self.set_url_btn = QPushButton("设置URL")
        self.set_url_btn.clicked.connect(self.set_url)

        self.start_detect_btn = QPushButton("开始监控")
        self.start_detect_btn.clicked.connect(self.start_detection)

        self.stop_detect_btn = QPushButton("停止监控")
        self.stop_detect_btn.clicked.connect(self.stop_detection)
        self.stop_detect_btn.setEnabled(False)

        self.check_status_btn = QPushButton("检查状态")
        self.check_status_btn.clicked.connect(self.check_status)

        controls_layout.addWidget(QLabel("URL:"))
        controls_layout.addWidget(self.url_input)
        controls_layout.addWidget(self.set_url_btn)
        controls_layout.addWidget(self.start_detect_btn)
        controls_layout.addWidget(self.stop_detect_btn)
        controls_layout.addWidget(self.check_status_btn)
        controls_layout.addStretch()
        
        detection_layout.addLayout(controls_layout)
        detection_group.setLayout(detection_layout)
        
        # 系统日志区域（占比大，与消息检测控制分开）
        log_group = QGroupBox("系统日志")
        log_layout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        # 移除最大高度限制，让日志区域占据更多空间

        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        
        layout.addWidget(info_group)
        layout.addWidget(detection_group)
        layout.addWidget(log_group)
        
        # 设置布局比例：系统信息固定，检测控制小，日志区域大
        layout.setStretch(0, 0)  # 系统信息固定高度
        layout.setStretch(1, 0)  # 检测控制固定高度
        layout.setStretch(2, 1)   # 日志区域占据剩余空间
        
        self.setLayout(layout)
        self.update_status()
        self.add_log("系统启动完成")

    # ---- 消息检测控制（移植自消息检测页） ----
    def set_url(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "警告", "请输入有效的URL")
            return
        current_url = self.douyin_msg.get_url()
        if current_url == url:
            self.add_log(f"URL已经设置: {url}")
            return
        try:
            if self.douyin_msg.browser is not None and self.douyin_msg.tab is not None:
                current_page_url = self.douyin_msg.tab.url
                if current_page_url and url in current_page_url:
                    self.add_log("浏览器已经打开目标页面，无需重复设置")
                    return
        except Exception as e:
            print(f"检查当前页面URL时出错: {e}")
        self.douyin_msg.set_url(url)
        self.add_log(f"URL设置成功: {url}")

    def _ensure_matcher(self):
        if not hasattr(self, 'matcher'):
            self.matcher = KeywordMatcher()
        if not getattr(self.matcher, '_keywords', None):
            try:
                from config.system_config import Config
                if os.path.exists(Config.MATCHER_SAVE_PATH):
                    self.matcher.load(Config.MATCHER_SAVE_PATH)
                else:
                    from database.mysql_pool_db import MySQLKeywordDBPool
                    from database.sqlite_db import KeywordDB
                    from config.database_config import DatabaseConfig
                    try:
                        config = DatabaseConfig.load_config()
                        if config:
                            db = MySQLKeywordDBPool(config)
                            if db.test_connection():
                                keywords = db.get_all_keywords()
                                for keyword_data in keywords:
                                    from BaseData.KeyWord import KeyWord
                                    kw_obj = KeyWord(keyword_data[1], keyword_data[2])
                                    self.matcher.add_keyword(kw_obj)
                            else:
                                raise Exception("MySQL连接失败")
                        else:
                            raise Exception("MySQL配置不存在")
                    except:
                        db = KeywordDB("BaseData/violation_keywords.db")
                        keywords = db.get_all_keywords()
                        for keyword in keywords:
                            from BaseData.KeyWord import KeyWord
                            kw_obj = KeyWord(keyword)
                            self.matcher.add_keyword(kw_obj)
                    self.matcher.build()
            except Exception as e:
                QMessageBox.warning(self, "警告", f"加载匹配器失败: {str(e)}")

    def start_detection(self):
        if not self.douyin_msg.get_url():
            QMessageBox.warning(self, "警告", "请先设置URL")
            return
        if self.douyin_msg.browser is None or self.douyin_msg.tab is None:
            QMessageBox.warning(self, "警告", "浏览器未打开，请先设置URL")
            return
        if hasattr(self, 'detection_thread') and self.detection_thread and self.detection_thread.isRunning():
            self.add_log("检测已经在运行中")
            return
        self._ensure_matcher()
        if not self.matcher or not self.matcher._keywords:
            QMessageBox.warning(self, "警告", "关键词匹配器未加载，请检查关键词配置")
            return
        from gui.message_detection_widget import MessageDetectionThread
        self.detection_thread = MessageDetectionThread(self.matcher, self.douyin_msg)
        self.detection_thread.message_detected.connect(lambda r: self.add_log(f"违规: {r['user']} - {r['message']}"))
        self.detection_thread.status_update.connect(self.add_log)
        self.detection_thread.start()
        
        # 同时启动用户消息抓取
        self.start_user_message_logging()
        
        self.start_detect_btn.setEnabled(False)
        self.stop_detect_btn.setEnabled(True)

    def stop_detection(self):
        if hasattr(self, 'detection_thread') and self.detection_thread:
            self.detection_thread.stop()
            self.detection_thread.wait()
            self.detection_thread = None
        
        # 同时停止用户消息抓取
        self.stop_user_message_logging()
        
        self.start_detect_btn.setEnabled(True)
        self.stop_detect_btn.setEnabled(False)

    def check_status(self):
        status_info = []
        current_url = self.douyin_msg.get_url()
        if current_url:
            status_info.append(f"✓ URL已设置: {current_url}")
        else:
            status_info.append("✗ URL未设置")
        if self.douyin_msg.browser is not None and self.douyin_msg.tab is not None:
            status_info.append("✓ 浏览器已打开")
            try:
                current_page_url = self.douyin_msg.tab.url
                if current_page_url:
                    status_info.append(f"✓ 当前页面: {current_page_url}")
                else:
                    status_info.append("✗ 无法获取当前页面URL")
            except Exception as e:
                status_info.append(f"✗ 获取页面URL失败: {e}")
        else:
            status_info.append("✗ 浏览器未打开")
        if hasattr(self, 'matcher') and self.matcher and getattr(self.matcher, '_keywords', None):
            status_info.append(f"✓ 匹配器已加载，关键词数量: {len(self.matcher._keywords)}")
        else:
            status_info.append("✗ 匹配器未加载")
        if hasattr(self, 'detection_thread') and self.detection_thread and self.detection_thread.isRunning():
            status_info.append("✓ 检测线程正在运行")
        else:
            status_info.append("✗ 检测线程未运行")
        if hasattr(self, 'message_thread') and self.message_thread and self.message_thread.isRunning():
            status_info.append("✓ 用户消息抓取正在运行")
        else:
            status_info.append("✗ 用户消息抓取未运行")
        QMessageBox.information(self, "系统状态", "\n".join(status_info))

    def start_user_message_logging(self):
        """启动后台线程，抓取用户消息并输出到日志"""
        if self.message_thread and self.message_thread.isRunning():
            self.add_log("用户消息抓取已在运行")
            return
        self.message_thread = UserMessageLogThread(self.douyin_msg, poll_interval_sec=3)
        self.message_thread.log_line.connect(lambda text: self.add_log(f"用户消息: {text}"))
        self.message_thread.status_line.connect(self.add_log)
        self.message_thread.start()
        # 这些按钮在新布局中已移除，做兼容性判断
        if hasattr(self, 'start_msg_btn'):
            self.start_msg_btn.setEnabled(False)
        if hasattr(self, 'stop_msg_btn'):
            self.stop_msg_btn.setEnabled(True)

    def stop_user_message_logging(self):
        """停止后台消息抓取线程"""
        if self.message_thread:
            self.message_thread.stop()
            self.message_thread.wait()
            self.message_thread = None
        if hasattr(self, 'start_msg_btn'):
            self.start_msg_btn.setEnabled(True)
        if hasattr(self, 'stop_msg_btn'):
            self.stop_msg_btn.setEnabled(False)
    
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
                    db = MySQLKeywordDBPool(config)
                    if db.test_connection():
                        keywords = db.get_all_keywords()
                        keyword_count = len(keywords)
                        db_type = "MySQL"
                        
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
