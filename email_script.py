#!/usr/bin/env python3
"""
邮件助手脚本
简化的命令行界面
"""
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.email_assistant import main

if __name__ == "__main__":
    main()