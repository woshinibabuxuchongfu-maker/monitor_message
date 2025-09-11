from datetime import time


def run(self):
    self.running = True
    self.status_update.emit("开始监控消息...")

    while self.running:
        try:

            # >>> 获取用户列表（使用智能等待） <<<
            try:
                self.status_update.emit("刷新浏览器...")
                self.douyin_msg.refresh_page()
                # 等待页面刷新完成（原3秒等待移到这里）
                time.sleep(3)

                user_list = self.douyin_msg._get_user_list()
                if not user_list:
                    self.status_update.emit("未获取到用户列表，跳过本轮")
                    time.sleep(1)
                    continue
                # 调试：显示前8个用户名
                user_names = []
                for user in user_list:
                    try:
                        name = user.child().child().child().text
                        if name:
                            user_names.append(name)
                    except:
                        continue
                self.status_update.emit(
                    f"当前用户: {', '.join(user_names[:8])}{'...' if len(user_names) > 8 else ''}")

            except Exception as e:
                self.status_update.emit(f"获取用户列表异常: {str(e)}")
                time.sleep(1)  # 不sleep太久，保持主循环节奏
                continue

            # >>> 遍历用户（保持原节奏） <<<
            processed_users = set()
            for user in user_list:
                if not self.running:
                    break

                try:
                    user_name = user.child().child().child().text
                    if not user_name or user_name in processed_users:
                        continue

                    processed_users.add(user_name)
                    self.status_update.emit(f"检查用户: {user_name}")

                    # 点击用户
                    try:
                        user.click()
                        time.sleep(1)  # <<< 保持你原来的1秒节奏 >>>
                    except Exception as e:
                        self.status_update.emit(f"点击用户失败: {str(e)}")
                        continue

                    # 获取对话数据（你原来的逻辑）
                    try:
                        conversation_data = self._thr_get_conversation_data(user_name)
                        if conversation_data:
                            self._thr_save_conversation_to_db(user_name, conversation_data)
                            self._thr_detect_violations_in_conversation(user_name, conversation_data)
                    except Exception as e:
                        self.status_update.emit(f"处理对话失败: {str(e)}")
                        continue

                except Exception as e:
                    self.status_update.emit(f"处理用户 {user_name} 时出错: {str(e)}")
                    continue

            # >>> 主循环节奏控制（保持原样） <<<
            time.sleep(Config.DETECTION_INTERVAL)

        except Exception as e:
            self.status_update.emit(f"检测循环错误: {str(e)}")
            time.sleep(3)  # 出错时稍等，但不要太久，保持主节奏