import threading
import time
from typing import List, Dict, Any
from collections import defaultdict
from datetime import datetime


class BatchConversationSaver:
    def __init__(self, db_instance, batch_size: int = 20, flush_interval: int = 30):
        """
        初始化批量保存器
        :param db_instance: 数据库实例
        :param batch_size: 批量保存大小，默认20个用户
        :param flush_interval: 自动刷新间隔（秒），默认30秒
        """
        self.db = db_instance
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        # 存储待保存的数据
        self._conversation_buffer = {}
        self._detection_buffer = []
        
        # 线程安全锁
        self._lock = threading.RLock()
        
        # 统计信息
        self._stats = {
            'total_saved_users': 0,
            'total_saved_messages': 0,
            'total_saved_detections': 0,
            'last_save_time': None
        }
        
        # 启动自动刷新线程
        self._auto_flush_thread = threading.Thread(target=self._auto_flush_worker, daemon=True)
        self._running = True
        self._auto_flush_thread.start()
    
    def add_conversation(self, user_name: str, conversation_data: List[Dict], douyin_id: str = ""):
        """
        添加用户对话数据到缓冲区
        :param user_name: 用户名
        :param conversation_data: 对话数据
        :param douyin_id: 抖音ID
        """
        with self._lock:
            # 使用字典结构存储对话数据和抖音ID
            if user_name in self._conversation_buffer:
                # 合并现有数据，避免重复
                existing_payload = self._conversation_buffer[user_name]
                if isinstance(existing_payload, dict):
                    existing_data = existing_payload.get('data', [])
                    existing_douyin_id = existing_payload.get('douyin_id', '')
                else:
                    # 兼容旧格式
                    existing_data = existing_payload
                    existing_douyin_id = ''
                
                existing_messages = {msg.get('message', '') + str(msg.get('timestamp', '')): msg for msg in existing_data}
                new_messages = {msg.get('message', '') + str(msg.get('timestamp', '')): msg for msg in conversation_data}
                
                # 添加新消息
                for key, msg in new_messages.items():
                    if key not in existing_messages:
                        existing_messages[key] = msg
                
                # 更新缓冲区，保留抖音ID
                self._conversation_buffer[user_name] = {
                    'data': list(existing_messages.values()),
                    'douyin_id': douyin_id or existing_douyin_id
                }
            else:
                self._conversation_buffer[user_name] = {
                    'data': conversation_data,
                    'douyin_id': douyin_id
                }
            
            # 检查是否需要立即保存
            if len(self._conversation_buffer) >= self.batch_size:
                self.flush_conversations()
    
    def add_detection(self, detection_result: Dict):
        """
        添加检测结果到缓冲区
        :param detection_result: 检测结果
        """
        with self._lock:
            self._detection_buffer.append(detection_result)
            
            # 检测结果较多时也触发保存
            if len(self._detection_buffer) >= self.batch_size * 2:  # 检测结果通常是对话的2倍
                self.flush_detections()
    
    def flush_conversations(self) -> int:
        """
        立即保存所有缓冲的对话数据
        :return: 保存的用户数量
        """
        with self._lock:
            if not self._conversation_buffer:
                return 0
            
            try:
                # 构造批量保存参数：对话+douyin_id 映射
                conversations_only = {}
                user_to_douyin_id = {}
                for uname, payload in self._conversation_buffer.items():
                    if isinstance(payload, dict):
                        conversations_only[uname] = payload.get('data', [])
                        user_to_douyin_id[uname] = payload.get('douyin_id') or None
                    else:
                        # 兼容旧格式
                        conversations_only[uname] = payload
                        user_to_douyin_id[uname] = None

                # 批量保存对话数据（包含抖音ID）
                saved_count = self.db.batch_save_chat_conversations(conversations_only, user_to_douyin_id)
                
                if saved_count > 0:
                    # 更新统计信息
                    self._stats['total_saved_users'] += saved_count
                    total_msgs = 0
                    for payload in self._conversation_buffer.values():
                        if isinstance(payload, dict):
                            total_msgs += len(payload.get('data', []))
                        else:
                            total_msgs += len(payload)
                    self._stats['total_saved_messages'] += total_msgs
                    self._stats['last_save_time'] = datetime.now()
                    
                    # 清空缓冲区
                    self._conversation_buffer.clear()
                    
                    print(f"[批量保存] 成功保存 {saved_count} 个用户的对话数据")
                    return saved_count
                else:
                    print(f"[批量保存] 保存对话数据失败")
                    return 0
                    
            except Exception as e:
                print(f"[批量保存] 保存对话数据时出错: {e}")
                return 0
    
    def flush_detections(self) -> int:
        """
        立即保存所有缓冲的检测结果
        :return: 保存的检测结果数量
        """
        with self._lock:
            if not self._detection_buffer:
                return 0
            
            try:
                # 批量保存检测结果
                saved_count = self.db.batch_save_detection_records(self._detection_buffer)
                
                if saved_count > 0:
                    # 更新统计信息
                    self._stats['total_saved_detections'] += saved_count
                    
                    # 清空缓冲区
                    self._detection_buffer.clear()
                    
                    print(f"[批量保存] 成功保存 {saved_count} 条检测记录")
                    return saved_count
                else:
                    print(f"[批量保存] 保存检测记录失败")
                    return 0
                    
            except Exception as e:
                print(f"[批量保存] 保存检测记录时出错: {e}")
                return 0
    
    def flush_all(self) -> Dict[str, int]:
        """
        立即保存所有缓冲的数据
        :return: 保存统计信息
        """
        with self._lock:
            conv_count = self.flush_conversations()
            det_count = self.flush_detections()
            
            return {
                'conversations_saved': conv_count,
                'detections_saved': det_count,
                'total_users_in_buffer': len(self._conversation_buffer),
                'total_detections_in_buffer': len(self._detection_buffer)
            }
    
    def _auto_flush_worker(self):
        """
        自动刷新工作线程
        定期保存缓冲区中的数据
        """
        while self._running:
            try:
                time.sleep(self.flush_interval)
                
                if self._running:
                    with self._lock:
                        # 如果有数据则保存
                        if self._conversation_buffer or self._detection_buffer:
                            print(f"[自动刷新] 开始自动保存，对话用户: {len(self._conversation_buffer)}, 检测记录: {len(self._detection_buffer)}")
                            self.flush_all()
                            
            except Exception as e:
                print(f"[自动刷新] 自动保存时出错: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        :return: 统计信息字典
        """
        with self._lock:
            return {
                **self._stats,
                'buffer_users': len(self._conversation_buffer),
                'buffer_detections': len(self._detection_buffer),
                'batch_size': self.batch_size,
                'flush_interval': self.flush_interval
            }
    
    def get_buffer_info(self) -> Dict[str, Any]:
        """
        获取缓冲区信息
        :return: 缓冲区信息字典
        """
        with self._lock:
            return {
                'conversation_users': list(self._conversation_buffer.keys()),
                'conversation_count': len(self._conversation_buffer),
                'total_messages': sum(len(conv) for conv in self._conversation_buffer.values()),
                'detection_count': len(self._detection_buffer)
            }
    
    def stop(self):
        """
        停止批量保存器
        保存所有剩余数据并停止自动刷新线程
        """
        self._running = False
        
        # 等待自动刷新线程结束
        if self._auto_flush_thread.is_alive():
            self._auto_flush_thread.join(timeout=5)
        
        # 保存所有剩余数据
        final_stats = self.flush_all()
        print(f"[批量保存器] 已停止，最终保存统计: {final_stats}")
        
        return final_stats


# 全局批量保存器实例
_global_batch_saver = None
_saver_lock = threading.Lock()


def get_batch_saver(db_instance=None, batch_size: int = 20, flush_interval: int = 30) -> BatchConversationSaver:
    """
    获取全局批量保存器实例
    :param db_instance: 数据库实例
    :param batch_size: 批量保存大小
    :param flush_interval: 自动刷新间隔
    :return: 批量保存器实例
    """
    global _global_batch_saver
    
    with _saver_lock:
        if _global_batch_saver is None and db_instance is not None:
            _global_batch_saver = BatchConversationSaver(db_instance, batch_size, flush_interval)
        elif _global_batch_saver is None:
            raise ValueError("首次调用时必须提供db_instance参数")
        
        return _global_batch_saver


def stop_batch_saver():
    """
    停止全局批量保存器
    """
    global _global_batch_saver
    
    with _saver_lock:
        if _global_batch_saver is not None:
            _global_batch_saver.stop()
            _global_batch_saver = None
