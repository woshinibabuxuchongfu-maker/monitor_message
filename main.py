#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
消息违规检测系统 - 主启动脚本
"""

import sys
import os
import traceback


def check_dependencies():
    """检查依赖是否安装"""
    # (包安装名, 导入名)
    required_packages = [
        ('PyQt5', 'PyQt5'),
        ('DrissionPage', 'DrissionPage'),
        ('cachetools', 'cachetools'),
        ('pyahocorasick', 'ahocorasick'),
        ('rapidfuzz', 'rapidfuzz'),
        ('pymysql', 'pymysql')
    ]

    missing_packages = []

    for install_name, import_name in required_packages:
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(install_name)

    if missing_packages:
        print("缺少以下依赖包:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\n请运行以下命令安装:")
        print("pip install -r requirements.txt")
        return False

    return True
def ensure_directories():
    """确保必要的目录存在"""
    directories = [
        "BaseData",
        "Test", 
        "logs",
        "data",
        "config"
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"创建目录: {directory}")

def main():
    """主函数"""
    print("=" * 60)
    print("消息违规检测系统 - GUI管理界面")
    print("=" * 60)
    
    # 检查依赖
    if not check_dependencies():
        input("按回车键退出...")
        return
    
    # 确保目录存在
    ensure_directories()
    
    try:
        # 导入并启动GUI
        from gui.main_window import main as gui_main
        gui_main()
        
    except Exception as e:
        print(f"启动失败: {str(e)}")
        print("\n详细错误信息:")
        traceback.print_exc()
        input("按回车键退出...")

if __name__ == '__main__':
    main()
