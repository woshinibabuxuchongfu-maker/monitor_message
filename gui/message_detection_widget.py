
import sys
import os
import time
from datetime import datetime
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor
from collections import deque
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                             QLineEdit, QPushButton, QLabel, QTableWidget,
                             QTableWidgetItem, QHeaderView, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# 导入项目模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from function.Filter import KeywordMatcher
from function.GetDouyinMsg import GetDouyinMsg
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
        # 异步数据库写入线程池（避免阻塞检测循环）
        try:
            max_workers = getattr(Config, 'DB_SAVE_MAX_WORKERS', 3)
        except Exception:
            max_workers = 3
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._pending_futures = deque()
        try:
            self._max_pending = getattr(Config, 'DB_SAVE_MAX_PENDING', 100)
        except Exception:
            self._max_pending = 100
        # 线程内初始化并复用数据库连接池
        try:
            from database.mysql_pool_db import MySQLKeywordDBPool
            from config.database_config import DatabaseConfig
            config = DatabaseConfig.load_config() or DatabaseConfig.get_default_config()
            self._db = MySQLKeywordDBPool(config)
            # 可选轻量健康检查（不在每次保存时重复）
            try:
                if not self._db.test_connection():
                    self._db = None
                    self.status_update.emit("数据库连接不可用，将跳过数据库写入")
            except Exception:
                self._db = None
                self.status_update.emit("数据库健康检查失败，将跳过数据库写入")
        except Exception:
            self._db = None
            # 不抛出，允许线程继续运行

    def run(self):
        self.running = True
        self.status_update.emit("开始监控消息...")

        while self.running:
            try:
                # 获取当前页用户列表；若为空则刷新后重试一轮
                user_list = self.douyin_msg._get_user_list()
                if not user_list:
                    self.status_update.emit("未获取到用户列表，尝试刷新页面...")
                    try:
                        if self.douyin_msg.refresh_and_wait_user_list(timeout=10):
                            user_list = self.douyin_msg._get_user_list()
                    except Exception:
                        pass

                if user_list:
                    for user in user_list:
                        if not self.running:
                            break

                        # 提取用户名
                        try:
                            user_name = user.child().child().child().text
                        except Exception:
                            user_name = "未知用户"

                        self.status_update.emit(f"检查用户: {user_name}")

                        # 点击用户并短暂等待对话加载
                        try:
                            user.click()
                        except Exception:
                            continue

                        try:
                            for _ in range(6):
                                if not self.running:
                                    break
                                try:
                                    if self.douyin_msg.tab.eles("xpath=//*[@class='leadsCsUI-MessageItem']"):
                                        break
                                except Exception:
                                    pass
                                time.sleep(0.1)
                        except Exception:
                            pass

                        # 获取对话、保存数据库并检测违规
                        conversation_data = self._thr_get_conversation_data(user_name)
                        if conversation_data:
                            self._thr_save_conversation_to_db(user_name, conversation_data)
                            self._thr_detect_violations_in_conversation(user_name, conversation_data)

                # 当前页处理完，刷新以获取下一页（每页仅显示约8个）
                try:
                    self.status_update.emit("刷新页面以加载更多用户...")
                    self.douyin_msg.refresh_and_wait_user_list(timeout=10)
                except Exception:
                    pass

                time.sleep(Config.DETECTION_INTERVAL)

            except Exception as e:
                self.status_update.emit(f"检测错误: {str(e)}")
                time.sleep(10)
    

    # def run(self):
    #     self.running = True
    #     self.status_update.emit("开始监控消息...")

    #     while self.running:
    #         try:

    #             try:
    #                 self.status_update.emit("刷新浏览器...")
    #                 self.douyin_msg.refresh_page()
    #                 # 等待页面刷新完成（原3秒等待移到这里）
    #                 time.sleep(3)

    #                 user_list = self.douyin_msg._get_user_list()
    #                 if not user_list:
    #                     self.status_update.emit("未获取到用户列表，跳过本轮")
    #                     time.sleep(1)
    #                     continue
    #                 # 调试：显示前8个用户名
    #                 user_names = []
    #                 for user in user_list:
    #                     try:
    #                         name = user.child().child().child().text
    #                         if name:
    #                             user_names.append(name)
    #                     except:
    #                         continue
    #                 self.status_update.emit(
    #                     f"当前用户: {', '.join(user_names[:8])}{'...' if len(user_names) > 8 else ''}")

    #             except Exception as e:
    #                 self.status_update.emit(f"获取用户列表异常: {str(e)}")
    #                 time.sleep(1)  # 不sleep太久，保持主循环节奏
    #                 continue

    #             # >>> 遍历用户（保持原节奏） <<<
    #             processed_users = set()
    #             for user in user_list:
    #                 if not self.running:
    #                     break

    #                 try:
    #                     user_name = user.child().child().child().text
    #                     if not user_name or user_name in processed_users:
    #                         continue

    #                     processed_users.add(user_name)
    #                     self.status_update.emit(f"检查用户: {user_name}")

    #                     # 点击用户
    #                     try:
    #                         user.click()
    #                         # 减少固定等待，改为短轮询等待对话加载，最多约0.6秒
    #                         try:
    #                             for _ in range(6):  # 6 * 0.1s = 0.6s 上限
    #                                 if not self.running:
    #                                     break
    #                                 try:
    #                                     # 检测是否已出现消息条目
    #                                     if self.douyin_msg.tab.eles("xpath=//*[@class='leadsCsUI-MessageItem']"):
    #                                         break
    #                                 except Exception:
    #                                     pass
    #                                 time.sleep(0.1)
    #                         except Exception:
    #                             # 安全降级，不影响主流程
    #                             pass
    #                     except Exception as e:
    #                         self.status_update.emit(f"点击用户失败: {str(e)}")
    #                         continue

    #                     # 获取对话数据（你原来的逻辑）
    #                     try:
    #                         conversation_data = self._thr_get_conversation_data(user_name)
    #                         if conversation_data:
    #                             self._thr_save_conversation_to_db(user_name, conversation_data)
    #                             self._thr_detect_violations_in_conversation(user_name, conversation_data)
    #                     except Exception as e:
    #                         self.status_update.emit(f"处理对话失败: {str(e)}")
    #                         continue

    #                 except Exception as e:
    #                     self.status_update.emit(f"处理用户 {user_name} 时出错: {str(e)}")
    #                     continue

    #             # >>> 主循环节奏控制（保持原样） <<<
    #             time.sleep(Config.DETECTION_INTERVAL)

    #         except Exception as e:
    #             self.status_update.emit(f"检测循环错误: {str(e)}")
    #             time.sleep(3)  # 出错时稍等，但不要太久，保持主节奏
    def stop(self):
        self.running = False
        self.status_update.emit("停止监控")
        try:
            # 尽量不阻塞，快速关闭线程池
            self._executor.shutdown(wait=False)
        except Exception:
            pass

    # 线程内工具方法（从组件中内联过来，避免属性不存在错误）
    def _thr_get_conversation_data(self, user_name: str) -> List[Dict]:
        try:
            message_elements = self.douyin_msg.tab.eles("xpath=//*[@class='leadsCsUI-MessageItem']")
            # 仅抓取最近 N 条，减少单用户解析时间
            try:
                from config.system_config import Config as _Cfg
                fetch_limit = getattr(_Cfg, 'CONVERSATION_FETCH_LIMIT', 100)
            except Exception:
                fetch_limit = 100
            if isinstance(message_elements, list) and fetch_limit > 0:
                message_elements = message_elements[-fetch_limit:]
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

    def _enqueue_db_task(self, func, *args, **kwargs):
        """将数据库写入任务加入线程池，超出上限时丢弃本次任务以防阻塞。"""
        try:
            # 清理已完成的任务
            while self._pending_futures and self._pending_futures[0].done():
                self._pending_futures.popleft()
            if len(self._pending_futures) >= self._max_pending:
                # 队列过多，跳过该任务，保持监控循环流畅
                try:
                    self.status_update.emit("数据库写入队列已满，跳过一次保存")
                except Exception:
                    pass
                return
            fut = self._executor.submit(func, *args, **kwargs)
            self._pending_futures.append(fut)
        except Exception as e:
            print(f"提交数据库任务失败: {e}")

    def _thr_save_conversation_to_db(self, user_name: str, conversation_data: List[Dict]):
        try:
            if not getattr(self, '_db', None):
                return
            # 在线程池中执行保存并反馈结果
            def _job(db, u, data):
                try:
                    ok = db.save_chat_conversation(u, data)
                    if ok:
                        self.status_update.emit(f"已保存 {u} 的对话数据 ({len(data)} 条消息)")
                    else:
                        self.status_update.emit(f"保存 {u} 的对话数据失败")
                except Exception as ex:
                    print(f"保存对话数据到数据库失败: {ex}")
                    self.status_update.emit(f"保存对话数据失败: {str(ex)}")
            self._enqueue_db_task(_job, self._db, user_name, conversation_data)
        except Exception as e:
            print(f"计划保存对话数据任务失败: {e}")

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
                        self._thr_save_detection_record_to_db(detection_result)
                        self.message_detected.emit(detection_result)
                        self.status_update.emit(f"检测到违规内容: {user_name} ({msg_data.get('sender', 'A')}) - {message_text}")
        except Exception as e:
            print(f"检测对话违规内容失败: {e}")

    def _thr_save_detection_record_to_db(self, detection_result: Dict):
        try:
            if not getattr(self, '_db', None):
                return
            def _job(db, res: Dict):
                try:
                    matched_keywords = []
                    for match in res['matches']:
                        if hasattr(match.keyword, 'keyword'):
                            matched_keywords.append({'keyword': match.keyword.keyword, 'type': match.keyword.type, 'match_type': match.match_type, 'start': match.start, 'end': match.end})
                        else:
                            matched_keywords.append({'keyword': str(match.keyword), 'type': 'unknown', 'match_type': match.match_type, 'start': match.start, 'end': match.end})
                    db.add_detection_record(res['user'], res['message'], matched_keywords)
                except Exception as ex:
                    print(f"保存检测记录到数据库失败: {ex}")
            self._enqueue_db_task(_job, self._db, detection_result)
        except Exception as e:
            print(f"计划保存检测记录任务失败: {e}")


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
