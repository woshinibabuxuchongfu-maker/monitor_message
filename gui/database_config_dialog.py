import sys
import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                            QLineEdit, QPushButton, QLabel, QSpinBox, QCheckBox,
                            QGroupBox, QMessageBox, QTabWidget, QTextEdit,
                            QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon

# 导入项目模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.mysql_pool_db import MySQLKeywordDBPool
from config.database_config import DatabaseConfig

from PyQt5.QtWidgets import QWidget
class DatabaseConfigDialog(QDialog):

    config_saved = pyqtSignal(dict)  # 配置保存信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("数据库连接配置")
        self.setModal(True)
        self.setFixedSize(500, 400)
        
        self.current_config = {}
        self.init_ui()
        self.load_config()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 配置表单
        config_group = QGroupBox("MySQL数据库配置")
        config_layout = QFormLayout()
        
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("localhost")
        
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(3306)
        
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("root")
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("输入密码")
        
        self.database_input = QLineEdit()
        self.database_input.setPlaceholderText("filter_system")
        
        self.charset_input = QLineEdit()
        self.charset_input.setText("utf8mb4")
        
        config_layout.addRow("主机地址:", self.host_input)
        config_layout.addRow("端口:", self.port_input)
        config_layout.addRow("用户名:", self.user_input)
        config_layout.addRow("密码:", self.password_input)
        config_layout.addRow("数据库名:", self.database_input)
        config_layout.addRow("字符集:", self.charset_input)
        
        config_group.setLayout(config_layout)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.test_btn = QPushButton("测试连接")
        self.test_btn.clicked.connect(self.test_connection)
        
        self.save_btn = QPushButton("保存配置")
        self.save_btn.clicked.connect(self.save_config)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.test_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        
        # 状态显示
        self.status_label = QLabel("状态: 未连接")
        self.status_label.setStyleSheet("color: gray;")
        
        layout.addWidget(config_group)
        layout.addWidget(self.status_label)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def load_config(self):
        """加载配置"""
        config = DatabaseConfig.load_config()
        if config:
            self.host_input.setText(config.get("host", ""))
            self.port_input.setValue(config.get("port", 3306))
            self.user_input.setText(config.get("user", ""))
            self.password_input.setText(config.get("password", ""))
            self.database_input.setText(config.get("database", ""))
            self.charset_input.setText(config.get("charset", "utf8mb4"))
    
    def get_config(self):
        """获取当前配置"""
        return {
            "host": self.host_input.text().strip() or "localhost",
            "port": self.port_input.value(),
            "user": self.user_input.text().strip() or "root",
            "password": self.password_input.text(),
            "database": self.database_input.text().strip() or "filter_system",
            "charset": self.charset_input.text().strip() or "utf8mb4"
        }
    
    def test_connection(self):
        """测试数据库连接"""
        config = self.get_config()
        
        # 验证必填字段
        if not config["user"]:
            QMessageBox.warning(self, "警告", "请输入用户名")
            return
        
        try:
            # 创建临时数据库实例进行测试
            test_db = MySQLKeywordDBPool(config)
            if test_db.test_connection():
                self.status_label.setText("状态: 连接成功")
                self.status_label.setStyleSheet("color: green;")
                QMessageBox.information(self, "成功", "数据库连接测试成功！")
            else:
                self.status_label.setText("状态: 连接失败")
                self.status_label.setStyleSheet("color: red;")
                QMessageBox.warning(self, "失败", "数据库连接测试失败，请检查配置信息")
        except Exception as e:
            self.status_label.setText("状态: 连接错误")
            self.status_label.setStyleSheet("color: red;")
            QMessageBox.critical(self, "错误", f"连接测试出错: {str(e)}")
    
    def save_config(self):
        """保存配置"""
        config = self.get_config()
        
        # 验证必填字段
        if not config["user"]:
            QMessageBox.warning(self, "警告", "请输入用户名")
            return
        
        if not config["database"]:
            QMessageBox.warning(self, "警告", "请输入数据库名")
            return
        
        # 保存到文件
        if DatabaseConfig.save_config(config):
            self.current_config = config
            self.config_saved.emit(config)
            QMessageBox.information(self, "成功", "配置保存成功！")
            self.accept()
        else:
            QMessageBox.critical(self, "错误", "配置保存失败！")


class DatabaseManagerWidget(QWidget):
    """数据库管理组件"""
    
    def __init__(self):
        super().__init__()
        self.db = None
        self.init_ui()
        self.load_config()
        self.auto_connect_database()

    def auto_connect_database(self):
        """启动时自动尝试连接数据库"""
        config = self.current_config
        if not config:
            return

        try:
            self.db = MySQLKeywordDBPool(config)
            if self.db.test_connection():
                self.connection_status.setText("状态: 已连接")
                self.connection_status.setStyleSheet("color: green; font-weight: bold;")
                self.connect_btn.setEnabled(False)
                self.disconnect_btn.setEnabled(True)
                self.refresh_info()  # ✅ 自动刷新信息
            else:
                # 连接失败，释放 db
                self.db.close()
                self.db = None
                self.connection_status.setText("状态: 连接失败")
                self.connection_status.setStyleSheet("color: orange; font-weight: bold;")
        except Exception as e:
            print(f"自动连接失败: {e}")
            self.db = None
            self.connection_status.setText("状态: 连接异常")
            self.connection_status.setStyleSheet("color: orange; font-weight: bold;")
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 连接控制区域
        connection_group = QGroupBox("数据库连接")
        connection_layout = QHBoxLayout()
        
        self.connection_status = QLabel("状态: 未连接")
        self.connection_status.setStyleSheet("color: red; font-weight: bold;")
        
        self.config_btn = QPushButton("配置连接")
        self.config_btn.clicked.connect(self.show_config_dialog)
        
        self.connect_btn = QPushButton("连接数据库")
        self.connect_btn.clicked.connect(self.connect_database)
        
        self.disconnect_btn = QPushButton("断开连接")
        self.disconnect_btn.clicked.connect(self.disconnect_database)
        self.disconnect_btn.setEnabled(False)
        
        connection_layout.addWidget(self.connection_status)
        connection_layout.addStretch()
        connection_layout.addWidget(self.config_btn)
        connection_layout.addWidget(self.connect_btn)
        connection_layout.addWidget(self.disconnect_btn)
        
        connection_group.setLayout(connection_layout)
        
        # 数据库统计信息区域
        stats_group = QGroupBox("数据库统计")
        stats_layout = QVBoxLayout()
        
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(2)
        self.stats_table.setHorizontalHeaderLabels(["统计项目", "数值"])
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stats_table.setMaximumHeight(200)
        
        stats_layout.addWidget(self.stats_table)
        stats_group.setLayout(stats_layout)
        
        # 数据库信息区域
        info_group = QGroupBox("数据库信息")
        info_layout = QVBoxLayout()
        
        self.info_table = QTableWidget()
        self.info_table.setColumnCount(2)
        self.info_table.setHorizontalHeaderLabels(["项目", "值"])
        self.info_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.info_table.setMaximumHeight(150)
        
        info_layout.addWidget(self.info_table)
        info_group.setLayout(info_layout)
        
        # 操作区域
        operation_group = QGroupBox("数据库操作")
        operation_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("刷新信息")
        self.refresh_btn.clicked.connect(self.refresh_info)
        
        self.backup_btn = QPushButton("备份数据")
        self.backup_btn.clicked.connect(self.backup_data)
        
        self.restore_btn = QPushButton("恢复数据")
        self.restore_btn.clicked.connect(self.restore_data)
        
        operation_layout.addWidget(self.refresh_btn)
        operation_layout.addWidget(self.backup_btn)
        operation_layout.addWidget(self.restore_btn)
        operation_layout.addStretch()
        
        operation_group.setLayout(operation_layout)
        
        layout.addWidget(connection_group)
        layout.addWidget(stats_group)
        layout.addWidget(info_group)
        layout.addWidget(operation_group)
        
        self.setLayout(layout)
    
    def load_config(self):
        """加载配置"""
        config = DatabaseConfig.load_config()
        if config:
            self.current_config = config
        else:
            self.current_config = DatabaseConfig.get_default_config()
    
    def show_config_dialog(self):
        """显示配置对话框"""
        dialog = DatabaseConfigDialog(self)
        dialog.config_saved.connect(self.on_config_saved)
        dialog.exec_()
    
    def on_config_saved(self, config):
        """配置保存回调"""
        self.current_config = config
        self.load_config()
    
    def connect_database(self):
        """连接数据库"""
        try:
            self.db = MySQLKeywordDBPool(self.current_config)
            if self.db.test_connection():
                self.connection_status.setText("状态: 已连接")
                self.connection_status.setStyleSheet("color: green; font-weight: bold;")
                self.connect_btn.setEnabled(False)
                self.disconnect_btn.setEnabled(True)
                self.refresh_info()
                QMessageBox.information(self, "成功", "数据库连接成功！")
            else:
                QMessageBox.warning(self, "失败", "数据库连接失败，请检查配置")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"连接数据库时出错: {str(e)}")
    
    def disconnect_database(self):
        """断开数据库连接"""
        if self.db:
            self.db.close()
            self.db = None
        
        self.connection_status.setText("状态: 未连接")
        self.connection_status.setStyleSheet("color: red; font-weight: bold;")
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.info_table.setRowCount(0)
        self.stats_table.setRowCount(0)
    
    def refresh_info(self):
        """刷新数据库信息"""
        if not self.db:
            return
        
        try:
            # 更新数据库统计信息
            stats = self.db.get_statistics()
            
            stats_data = [
                ("关键词总数", str(stats.get('total_keywords', 0))),
                ("检测记录总数", str(stats.get('total_detections', 0))),
                ("今日检测数", str(stats.get('today_detections', 0))),
            ]
            
            # 添加按类型统计的关键词
            keywords_by_type = stats.get('keywords_by_type', {})
            for keyword_type, count in keywords_by_type.items():
                stats_data.append((f"关键词类型({keyword_type})", str(count)))
            
            self.stats_table.setRowCount(len(stats_data))
            for i, (key, value) in enumerate(stats_data):
                self.stats_table.setItem(i, 0, QTableWidgetItem(key))
                self.stats_table.setItem(i, 1, QTableWidgetItem(value))
            
            # 更新数据库连接信息
            info_data = [
                ("数据库", self.current_config.get('database', '')),
                ("主机", self.current_config.get('host', '')),
                ("端口", str(self.current_config.get('port', ''))),
                ("字符集", self.current_config.get('charset', '')),
            ]
            
            # 添加连接池状态信息
            pool_status = self.db.get_pool_status()
            if pool_status:
                info_data.extend([
                    ("连接池大小", str(pool_status.get('pool_size', 0))),
                    ("最大连接数", str(pool_status.get('max_pool_size', 0))),
                    ("当前连接数", str(pool_status.get('total_connections', 0))),
                ])
            
            self.info_table.setRowCount(len(info_data))
            for i, (key, value) in enumerate(info_data):
                self.info_table.setItem(i, 0, QTableWidgetItem(key))
                self.info_table.setItem(i, 1, QTableWidgetItem(value))
                
        except Exception as e:
            QMessageBox.warning(self, "警告", f"刷新信息失败: {str(e)}")
    
    def backup_data(self):
        """备份数据"""
        if not self.db:
            QMessageBox.warning(self, "警告", "请先连接数据库")
            return
        
        QMessageBox.information(self, "提示", "数据备份功能待实现")
    
    def restore_data(self):
        """恢复数据"""
        if not self.db:
            QMessageBox.warning(self, "警告", "请先连接数据库")
            return
        
        QMessageBox.information(self, "提示", "数据恢复功能待实现")
    
    def get_database(self):
        """获取数据库实例"""
        return self.db


if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 测试配置对话框
    dialog = DatabaseConfigDialog()
    dialog.show()
    
    sys.exit(app.exec_())
