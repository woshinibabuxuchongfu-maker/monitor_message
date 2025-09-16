import sys
import os
import time
from datetime import datetime
from typing import List, Dict

from DrissionPage._functions.by import By
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QLineEdit, QPushButton, QLabel, QTableWidget,
                             QTableWidgetItem, QHeaderView, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# 导入项目模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from function.Filter import KeywordMatcher
from function.GetDouyinMsg import GetDouyinMsg
from config.system_config import Config
from database.batch_saver import get_batch_saver, stop_batch_saver

class MessageDetectionThread(QThread):
    """消息检测线程"""
    message_detected = pyqtSignal(dict)  # 检测到违规消息时发出信号
    status_update = pyqtSignal(str)      # 状态更新信号
    
    def __init__(self, matcher, douyin_msg):
        super().__init__()
        self.matcher = matcher
        self.douyin_msg = douyin_msg
        self.running = False
        # 首次进入监控时先进行一次刷新并等待
        self._initial_refresh_done = False
        # 初始化批量保存器
        self.batch_saver = None
        self._init_batch_saver()
        
    def run(self):
        self.running = True
        self.status_update.emit("开始监控消息...")
        
        # 刷新与批处理控制
        last_refresh_ts = 0
        REFRESH_INTERVAL = 20   # 秒
        BATCH_SIZE = 8          # 每批处理的用户数量
        PER_USER_DWELL = 1      # 点击后页面稳定等待（秒）
        PER_USER_CYCLE = 3      # 单个用户完整处理耗时目标（秒）

        while self.running:
            try:
                # 检查浏览器和标签页是否有效
                if not self.douyin_msg.is_connected():
                    self.status_update.emit("浏览器连接已断开，请重新设置URL")
                    time.sleep(5)
                    continue
                
                # 首次启动：先刷新浏览器并等待5秒，再获取列表
                if not self._initial_refresh_done:
                    try:
                        self.status_update.emit("开始监控，先刷新页面并等待5秒")
                        self.douyin_msg.refresh_page()
                        time.sleep(5)
                        self.douyin_msg.wait_for_user_list(timeout=10)
                    except Exception as e:
                        self.status_update.emit(f"首次刷新失败: {str(e)}")
                    finally:
                        self._initial_refresh_done = True

                # 定期刷新页面
                now_ts = time.time()
                if now_ts - last_refresh_ts >= REFRESH_INTERVAL:
                    try:
                        # 只要刷新浏览器，就等待5秒，然后等待列表条件通过
                        self.douyin_msg.refresh_page()
                        time.sleep(5)
                        self.douyin_msg.wait_for_user_list(timeout=10)
                        self.status_update.emit("定时刷新页面（20秒），已等待5秒并确认列表加载")
                    except Exception as e:
                        self.status_update.emit(f"页面刷新失败: {str(e)}")
                    last_refresh_ts = now_ts
                
                # 获取用户列表
                try:
                    # 若刚刷新或首次进入，确保等待用户列表加载完成并再次查询
                    if not self.douyin_msg.wait_for_user_list(timeout=10):
                        self.status_update.emit("用户列表加载超时，重试中...")
                        time.sleep(3)
                    user_list = self.douyin_msg._get_user_list()
                    if not user_list:
                        self.status_update.emit("未找到用户列表，等待页面加载...")
                        time.sleep(3)
                        continue
                    
                    # 添加调试信息
                    user_names = []
                    for user in user_list:
                        try:
                            user_name = user.child().child().child().text
                            if user_name:
                                user_names.append(user_name)
                        except:
                            continue
                    
                    self.status_update.emit(f"当前用户列表: {', '.join(user_names[:8])}{'...' if len(user_names) > 8 else ''}")
                    # 本次只处理前 BATCH_SIZE 个用户，通过频繁刷新获取更多
                    user_batch = user_list[:BATCH_SIZE]
                    
                except Exception as e:
                    self.status_update.emit(f"获取用户列表失败: {str(e)}")
                    time.sleep(5)
                    continue
                
                # 遍历本批用户
                for user in user_batch:
                    if not self.running:
                        break
                    
                    try:
                        # 获取用户名
                        user_name = user.child().child().child().text
                        if not user_name:
                            continue
                        
                        self.status_update.emit(f"检查用户: {user_name}")
                        
                        # 点击用户获取消息
                        try:
                            user.click()
                            time.sleep(PER_USER_DWELL)  # 每个用户停留固定时长
                            
                            # 获取抖音ID（点击后从剪贴板读取）
                            douyin_id = self.get_douyin_id()
                            if douyin_id:
                                self.status_update.emit(f"获取到抖音ID: {douyin_id}")
                            else:
                                self.status_update.emit("未获取到抖音ID")
                                
                        except Exception as e:
                            self.status_update.emit(f"点击用户失败: {str(e)}")
                            continue
                        
                        start_ts = time.time()
                        # 获取完整对话内容
                        try:
                            conversation_data = self._thr_get_conversation_data(user_name)
                            if conversation_data:
                                # 使用批量保存器保存对话到数据库（包含抖音ID）
                                self._thr_save_conversation_to_batch(user_name, conversation_data, douyin_id)
                                
                                # 检测违规内容
                                self._thr_detect_violations_in_conversation(user_name, conversation_data)
                                
                                # 抖音ID已通过批量保存器一起保存，无需单独处理
                                if douyin_id:
                                    self.status_update.emit(f"✓ 抖音ID已获取: {user_name} -> {douyin_id}")
                                else:
                                    self.status_update.emit(f"⚠ 用户 {user_name} 未获取到抖音ID")
                                
                                # 立即刷新批量保存器，确保数据及时保存
                                if self.batch_saver:
                                    flush_stats = self.batch_saver.flush_all()
                                    self.status_update.emit(f"批量保存状态: {flush_stats}")
                                    if flush_stats.get('conversations_saved', 0) > 0:
                                        self.status_update.emit(f"已保存 {user_name} 的对话数据")
                                    else:
                                        self.status_update.emit(f"用户 {user_name} 数据已缓存，等待批量保存")
                        except Exception as e:
                            self.status_update.emit(f"处理对话失败: {str(e)}")
                            continue
                        finally:
                            # 保证单个用户处理总耗时不小于 PER_USER_CYCLE 秒
                            elapsed = time.time() - start_ts
                            if elapsed < PER_USER_CYCLE:
                                time.sleep(PER_USER_CYCLE - elapsed)
                                
                    except Exception as e:
                        # 单个用户处理失败，继续处理下一个用户
                        self.status_update.emit(f"处理用户时出错: {str(e)}")
                        continue
                
                # 一批处理完成后，立即刷新浏览器以获取更多用户
                try:
                    self.status_update.emit("本批处理完成，刷新页面获取更多用户")
                    
                    # 批处理完成后强制保存所有缓存的数据
                    if self.batch_saver:
                        flush_stats = self.batch_saver.flush_all()
                        if flush_stats.get('conversations_saved', 0) > 0:
                            self.status_update.emit(f"批量保存完成: {flush_stats.get('conversations_saved', 0)} 个用户对话")
                    
                    self.douyin_msg.refresh_page()
                    time.sleep(5)
                    self.douyin_msg.wait_for_user_list(timeout=10)
                except Exception as e:
                    self.status_update.emit(f"批处理后刷新失败: {str(e)}")
                
            except Exception as e:
                self.status_update.emit(f"检测循环错误: {str(e)}")
                time.sleep(10)
    
    def _init_batch_saver(self):
        """初始化批量保存器"""
        try:
            from database.mysql_pool_db import MySQLKeywordDBPool
            from config.database_config import DatabaseConfig
            
            config = DatabaseConfig.load_config() or DatabaseConfig.get_default_config()
            db = MySQLKeywordDBPool(config)
            
            if db.test_connection():
                self.batch_saver = get_batch_saver(db, batch_size=5, flush_interval=10)
                print("[批量保存] 批量保存器初始化成功")
            else:
                print("[批量保存] 数据库连接失败，批量保存器初始化失败")
        except Exception as e:
            print(f"[批量保存] 批量保存器初始化失败: {e}")

    def stop(self):
        self.running = False
        # 停止前保存所有剩余数据
        if self.batch_saver:
            final_stats = self.batch_saver.flush_all()
            self.status_update.emit(f"批量保存完成，保存了 {final_stats.get('conversations_saved', 0)} 个用户对话")
        self.status_update.emit("停止监控")

    def get_douyin_id(self) -> str:
        try:
            import pyperclip
            from time import sleep

            # 使用正确的浏览器对象和定位方式
            user_element = self.douyin_msg.tab.ele("xpath=//*[@id='layout-scroller']/div[3]/div/div/div[3]/div/div[1]/div[1]/div[1]/div[1]/div/span[2]")
            # 清空剪贴板
            pyperclip.copy("")
            sleep(0.1)
            
            # 点击用户名元素以触发复制
            try:
                user_element.click()
                print(f"[DEBUG] 成功点击用户名元素")
            except Exception as e:
                print(f"[DEBUG] 点击用户名元素失败: {e}")
                return ""
            
            # 等待复制完成
            sleep(0.5)
            
            # 从剪贴板读取
            douyin_id = pyperclip.paste() or ""
            douyin_id = douyin_id.strip()
            
            # 调试信息
            print(f"[DEBUG] 剪贴板内容: '{douyin_id}'")
            
            return douyin_id
        except Exception as e:
            print(f"[DEBUG] 获取抖音ID失败: {e}")
            return ""


    # 线程内工具方法（从组件中内联过来，避免属性不存在错误）
    def _thr_get_conversation_data(self, user_name: str) -> List[Dict]:
        try:
            message_elements = self.douyin_msg.tab.eles("xpath=//*[@class='leadsCsUI-MessageItem']")
            conversation_data = []
            for msg_element in message_elements:
                try:
                    text_element = msg_element.ele("xpath=.//*[@class='leadsCsUI-Text']")
                    if not text_element:
                        continue
                    message_text = text_element.text
                    if not message_text:
                        continue
                    sender = "A"
                    msg_classes = msg_element.attr('class') or ''
                    if 'leadsCsUI-MessageItem_right' in msg_classes:
                        sender = "B"
                    elif 'leadsCsUI-MessageItem_left' in msg_classes:
                        sender = "A"
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    time_element = msg_element.ele('xpath=.//*[contains(@class, "time") or contains(@class, "timestamp")]')
                    if time_element:
                        try:
                            timestamp = time_element.text
                        except:
                            pass
                    conversation_data.append({'sender': sender, 'message': message_text, 'timestamp': timestamp})
                except Exception as e:
                    print(f"处理单个消息时出错: {e}")
                    continue
            return conversation_data
        except Exception as e:
            print(f"获取对话数据失败: {e}")
            return []

    def _thr_save_conversation_to_batch(self, user_name: str, conversation_data: List[Dict], douyin_id: str = ""):
        """使用批量保存器保存对话数据"""
        try:
            if self.batch_saver:
                self.batch_saver.add_conversation(user_name, conversation_data, douyin_id)
                self.status_update.emit(f"已缓存 {user_name} 的对话数据 ({len(conversation_data)} 条消息)")
            else:
                # 回退到单个保存
                self._thr_save_conversation_to_db(user_name, conversation_data, douyin_id)
        except Exception as e:
            print(f"批量保存对话数据失败: {e}")
            self.status_update.emit(f"保存对话数据失败: {str(e)}")

    def _thr_save_conversation_to_db(self, user_name: str, conversation_data: List[Dict], douyin_id: str = ""):
        """单个保存对话数据（备用方法）"""
        try:
            from database.mysql_pool_db import MySQLKeywordDBPool
            from config.database_config import DatabaseConfig
            config = DatabaseConfig.load_config() or DatabaseConfig.get_default_config()
            db = MySQLKeywordDBPool(config)
            if db.test_connection():
                success = db.save_chat_conversation(user_name, conversation_data, douyin_id)
                if success:
                    self.status_update.emit(f"已保存 {user_name} 的对话数据 ({len(conversation_data)} 条消息)")
                else:
                    self.status_update.emit(f"保存 {user_name} 的对话数据失败")
            else:
                self.status_update.emit("数据库连接失败，无法保存对话数据")
        except Exception as e:
            print(f"保存对话数据到数据库失败: {e}")
            self.status_update.emit(f"保存对话数据失败: {str(e)}")

    def _thr_detect_violations_in_conversation(self, user_name: str, conversation_data: List[Dict]):
        try:
            for msg_data in conversation_data:
                message_text = msg_data.get('message', '')
                if message_text:
                    matches = list(self.matcher.search(message_text))
                    if matches:
                        detection_result = {
                            'user': user_name,
                            'message': message_text,
                            'matches': matches,
                            'timestamp': msg_data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                            'sender': msg_data.get('sender', 'A')
                        }
                        self._thr_save_detection_record_to_batch(detection_result)
                        self.message_detected.emit(detection_result)
                        self.status_update.emit(f"检测到违规内容: {user_name} ({msg_data.get('sender', 'A')}) - {message_text}")
        except Exception as e:
            print(f"检测对话违规内容失败: {e}")

    def _thr_save_detection_record_to_batch(self, detection_result: Dict):
        """使用批量保存器保存检测记录"""
        try:
            if self.batch_saver:
                self.batch_saver.add_detection(detection_result)
            else:
                # 回退到单个保存
                self._thr_save_detection_record_to_db(detection_result)
        except Exception as e:
            print(f"批量保存检测记录失败: {e}")

    def _thr_save_detection_record_to_db(self, detection_result: Dict):
        """单个保存检测记录（备用方法）"""
        try:
            from database.mysql_pool_db import MySQLKeywordDBPool
            from config.database_config import DatabaseConfig
            config = DatabaseConfig.load_config() or DatabaseConfig.get_default_config()
            db = MySQLKeywordDBPool(config)
            if db.test_connection():
                matched_keywords = []
                for match in detection_result['matches']:
                    if hasattr(match.keyword, 'keyword'):
                        matched_keywords.append({'keyword': match.keyword.keyword, 'type': match.keyword.type, 'match_type': match.match_type, 'start': match.start, 'end': match.end})
                    else:
                        matched_keywords.append({'keyword': str(match.keyword), 'type': 'unknown', 'match_type': match.match_type, 'start': match.start, 'end': match.end})
                db.add_detection_record(detection_result['user'], detection_result['message'], matched_keywords)
        except Exception as e:
            print(f"保存检测记录到数据库失败: {e}")


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

        # 仅保留“检测结果”区域（移除控制区）
        result_group = QGroupBox("检测结果")
        result_layout = QVBoxLayout()

        self.result_table = QTableWidget()
        self.result_table.setColumnCount(4)
        self.result_table.setHorizontalHeaderLabels(["时间", "用户", "消息", "匹配结果"])
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        result_layout.addWidget(self.result_table)
        result_group.setLayout(result_layout)

        layout.addWidget(result_group)

        self.setLayout(layout)

        # 加载历史检测记录
        self.load_detection_history()
    
    def load_matcher(self):
        """加载匹配器"""
        try:
            if os.path.exists(Config.MATCHER_SAVE_PATH):
                self.matcher.load(Config.MATCHER_SAVE_PATH)
            else:
                # 从数据库加载关键词
                from database.mysql_pool_db import MySQLKeywordDBPool
                from database.sqlite_db import KeywordDB
                from config.database_config import DatabaseConfig
                
                # 尝试使用MySQL，如果失败则使用SQLite
                try:
                    config = DatabaseConfig.load_config()
                    if config:
                        db = MySQLKeywordDBPool(config)
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
    
    def load_detection_history(self):
        """加载历史检测记录"""
        try:
            from database.mysql_pool_db import MySQLKeywordDBPool
            from database.sqlite_db import KeywordDB
            from config.database_config import DatabaseConfig
            
            # 尝试使用MySQL，如果失败则使用SQLite
            try:
                config = DatabaseConfig.load_config()
                if config:
                    db = MySQLKeywordDBPool(config)
                    if db.test_connection():
                        records = db.get_detection_records(limit=100)  # 加载最近100条记录
                        for record in records:
                            # record格式: (id, user_name, message, matched_keywords, detection_time)
                            detection_result = {
                                'timestamp': record[4].strftime('%Y-%m-%d %H:%M:%S') if record[4] else '',
                                'user': record[1],
                                'message': record[2],
                                'matches': []  # 这里简化处理，不解析matched_keywords
                            }
                            self.add_detection_result(detection_result)
                        return
                    else:
                        raise Exception("MySQL连接失败")
                else:
                    raise Exception("MySQL配置不存在")
            except:
                # SQLite数据库没有检测记录功能，跳过
                pass
        except Exception as e:
            print(f"加载历史检测记录失败: {e}")
    
    def set_url(self):
        """设置URL"""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "警告", "请输入有效的URL")
            return
        
        # 检查是否已经有相同的URL
        current_url = self.douyin_msg.get_url()
        if current_url == url:
            QMessageBox.information(self, "提示", f"URL已经设置: {url}")
            return
        
        # 检查浏览器是否已经打开
        if self.douyin_msg.browser is not None and self.douyin_msg.tab is not None:
            try:
                # 获取当前页面URL
                current_page_url = self.douyin_msg.tab.url
                if current_page_url and url in current_page_url:
                    QMessageBox.information(self, "提示", f"浏览器已经打开目标页面，无需重复设置")
                    return
            except Exception as e:
                print(f"检查当前页面URL时出错: {e}")
        
        # 设置新URL
        self.douyin_msg.set_url(url)
        QMessageBox.information(self, "成功", f"URL设置成功: {url}")

    
    def start_detection(self):
        """开始检测"""
        # 检查URL是否已设置
        if not self.douyin_msg.get_url():
            QMessageBox.warning(self, "警告", "请先设置URL")
            return
        
        # 检查浏览器是否已打开
        if self.douyin_msg.browser is None or self.douyin_msg.tab is None:
            QMessageBox.warning(self, "警告", "浏览器未打开，请先设置URL")
            return
        
        # 检查是否已经在运行检测
        if self.detection_thread and self.detection_thread.isRunning():
            QMessageBox.information(self, "提示", "检测已经在运行中")
            return
        
        # 检查匹配器是否已加载
        if not self.matcher or not self.matcher._keywords:
            QMessageBox.warning(self, "警告", "关键词匹配器未加载，请检查关键词配置")
            return
        
        # 开始检测
        self.detection_thread = MessageDetectionThread(self.matcher, self.douyin_msg)
        self.detection_thread.message_detected.connect(self.add_detection_result)
        self.detection_thread.status_update.connect(self.update_status)
        self.detection_thread.start()
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("状态: 正在启动检测...")
    
    def stop_detection(self):
        """停止检测"""
        if self.detection_thread:
            self.detection_thread.stop()
            self.detection_thread.wait()
            self.detection_thread = None
        
        # 停止批量保存器
        try:
            stop_batch_saver()
        except Exception as e:
            print(f"停止批量保存器失败: {e}")
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("状态: 已停止")
    
    def add_detection_result(self, result):
        """添加检测结果"""
        row = self.result_table.rowCount()
        self.result_table.insertRow(row)
        
        self.result_table.setItem(row, 0, QTableWidgetItem(result['timestamp']))
        
        # 显示用户名和发送者信息
        user_info = result['user']
        if 'sender' in result:
            sender_name = "客服" if result['sender'] == 'B' else "用户"
            user_info += f" ({sender_name})"
        self.result_table.setItem(row, 1, QTableWidgetItem(user_info))
        
        self.result_table.setItem(row, 2, QTableWidgetItem(result['message']))
        
        matches_text = ", ".join([f"{m.keyword.keyword if hasattr(m.keyword, 'keyword') else m.keyword}({m.match_type})" 
                                for m in result['matches']])
        self.result_table.setItem(row, 3, QTableWidgetItem(matches_text))
    
    def check_status(self):
        """检查当前状态"""
        status_info = []
        
        # 检查URL状态
        current_url = self.douyin_msg.get_url()
        if current_url:
            status_info.append(f"✓ URL已设置: {current_url}")
        else:
            status_info.append("✗ URL未设置")
        
        # 检查浏览器状态
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
        
        # 检查匹配器状态
        if self.matcher and self.matcher._keywords:
            status_info.append(f"✓ 匹配器已加载，关键词数量: {len(self.matcher._keywords)}")
        else:
            status_info.append("✗ 匹配器未加载")
        
        # 检查检测线程状态
        if self.detection_thread and self.detection_thread.isRunning():
            status_info.append("✓ 检测线程正在运行")
        else:
            status_info.append("✗ 检测线程未运行")
        
        # 显示状态信息
        status_text = "\n".join(status_info)
        QMessageBox.information(self, "系统状态", status_text)
    
    def _get_conversation_data(self, user_name: str) -> List[Dict]:
        """
        获取用户的完整对话数据
        :param user_name: 用户名
        :return: 对话数据列表
        """
        try:
            # 获取所有消息元素
            message_elements = self.douyin_msg.tab.eles('xpath=//*[@class=\'leadsCsUI-MessageItem\']')
            conversation_data = []
            
            for msg_element in message_elements:
                try:
                    # 获取消息文本
                    text_element = msg_element.ele('xpath=.//*[@class=\'leadsCsUI-Text\']')
                    if not text_element:
                        continue
                    
                    message_text = text_element.text
                    if not message_text:
                        continue
                    
                    # 判断消息发送者（A或B）
                    # 通过CSS类或其他属性判断是用户发送还是客服发送
                    sender = "A"  # 默认为用户A
                    
                    # 检查消息元素的类名或其他属性来判断发送者
                    msg_classes = msg_element.attr('class') or ''
                    if 'leadsCsUI-MessageItem_right' in msg_classes:
                        sender = "B"  # 客服发送
                    elif 'leadsCsUI-MessageItem_left' in msg_classes:
                        sender = "A"  # 用户发送
                    
                    # 获取时间戳（如果有的话）
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    time_element = msg_element.ele('xpath=.//*[contains(@class, "time") or contains(@class, "timestamp")]')
                    if time_element:
                        try:
                            timestamp = time_element.text
                        except:
                            pass
                    
                    conversation_data.append({
                        'sender': sender,
                        'message': message_text,
                        'timestamp': timestamp
                    })
                    
                except Exception as e:
                    print(f"处理单个消息时出错: {e}")
                    continue
            
            return conversation_data
            
        except Exception as e:
            print(f"获取对话数据失败: {e}")
            return []

    def _save_conversation_to_db(self, user_name: str, conversation_data: List[Dict]):
        """
        保存对话数据到数据库
        :param user_name: 用户名
        :param conversation_data: 对话数据
        """
        try:
            from database.mysql_pool_db import MySQLKeywordDBPool
            from config.database_config import DatabaseConfig
            
            config = DatabaseConfig.load_config()
            if not config:
                config = DatabaseConfig.get_default_config()
            
            db = MySQLKeywordDBPool(config)
            if db.test_connection():
                success = db.save_chat_conversation(user_name, conversation_data)
                if success:
                    self.status_update.emit(f"已保存 {user_name} 的对话数据 ({len(conversation_data)} 条消息)")
                else:
                    self.status_update.emit(f"保存 {user_name} 的对话数据失败")
            else:
                self.status_update.emit("数据库连接失败，无法保存对话数据")
                
        except Exception as e:
            print(f"保存对话数据到数据库失败: {e}")
            self.status_update.emit(f"保存对话数据失败: {str(e)}")

    def _detect_violations_in_conversation(self, user_name: str, conversation_data: List[Dict]):
        """
        检测对话中的违规内容
        :param user_name: 用户名
        :param conversation_data: 对话数据
        """
        try:
            for msg_data in conversation_data:
                message_text = msg_data.get('message', '')
                if message_text:
                    # 检测违规内容
                    matches = list(self.matcher.search(message_text))
                    if matches:
                        detection_result = {
                            'user': user_name,
                            'message': message_text,
                            'matches': matches,
                            'timestamp': msg_data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                            'sender': msg_data.get('sender', 'A')
                        }
                        
                        # 保存检测记录到数据库
                        self._save_detection_record_to_db(detection_result)
                        
                        # 发出信号显示检测结果
                        self.message_detected.emit(detection_result)
                        self.status_update.emit(f"检测到违规内容: {user_name} ({msg_data.get('sender', 'A')}) - {message_text}")
                        
        except Exception as e:
            print(f"检测对话违规内容失败: {e}")

    def _save_detection_record_to_db(self, detection_result: Dict):
        """
        保存检测记录到数据库
        :param detection_result: 检测结果字典
        """
        try:
            from database.mysql_pool_db import MySQLKeywordDBPool
            from config.database_config import DatabaseConfig
            
            config = DatabaseConfig.load_config()
            if not config:
                config = DatabaseConfig.get_default_config()
            
            db = MySQLKeywordDBPool(config)
            if db.test_connection():
                # 准备匹配关键词数据
                matched_keywords = []
                for match in detection_result['matches']:
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
                
                # 保存检测记录
                success = db.add_detection_record(
                    detection_result['user'],
                    detection_result['message'],
                    matched_keywords
                )
                
                if success:
                    print(f"✓ 检测记录已保存到数据库: {detection_result['user']} - {detection_result['message']}")
                else:
                    print(f"✗ 保存检测记录失败: {detection_result['user']} - {detection_result['message']}")
            else:
                print("✗ 数据库连接失败，无法保存检测记录")
                
        except Exception as e:
            print(f"保存检测记录到数据库失败: {e}")

    def update_status(self, status):
        """更新状态"""
        self.status_label.setText(f"状态: {status}")
