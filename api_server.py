#!/usr/bin/env python3
"""
邮件助手API服务器启动脚本
"""
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.api_server import run_server

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="邮件助手API服务器")
    parser.add_argument("--host", default="127.0.0.1", help="服务器地址")
    parser.add_argument("--port", type=int, default=5000, help="服务器端口")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")

    args = parser.parse_args()
    run_server(args.host, args.port, args.debug)