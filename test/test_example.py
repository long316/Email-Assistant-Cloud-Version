"""
测试示例文件
演示如何使用邮件助手的各种功能
"""
import sys
import os
import pandas as pd
from datetime import datetime

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.email_assistant import EmailAssistant

def create_test_excel():
    """创建测试用的Excel文件"""
    # 创建测试数据
    test_data = {
        '邮箱': [
            'test1@example.com',
            'test2@example.com',
            'test3@example.com',
            'invalid@example.com',  # 这个不符合筛选条件
            'test5@example.com'
        ],
        '合作次数': [0, 0, 0, 1, 0],  # invalid@example.com 合作次数为1，不符合条件
        '回复次数': [0, 0, 0, 0, 0],
        '跟进次数': [1, 1, 1, 1, 1],
        '跟进方式': ['自动', '自动', '自动', '自动', '手动'],  # test5@example.com 跟进方式为手动，不符合条件
        '是否已邮箱建联': [None, None, None, None, None]
    }

    df = pd.DataFrame(test_data)
    df.to_excel('test_emails.xlsx', index=False)
    print("测试Excel文件已创建: test_emails.xlsx")
    print("符合筛选条件的邮箱: test1@example.com, test2@example.com, test3@example.com")

def test_email_assistant():
    """测试邮件助手功能"""

    # 创建测试Excel文件
    create_test_excel()

    # 初始化邮件助手（注意：需要有效的credentials.json文件）
    try:
        assistant = EmailAssistant()
        print("✓ 邮件助手初始化成功")
    except Exception as e:
        print(f"✗ 邮件助手初始化失败: {e}")
        return

    # 测试Excel文件验证
    print("\n=== 测试Excel文件验证 ===")
    if assistant.validate_excel_file('test_emails.xlsx'):
        print("✓ Excel文件验证成功")
    else:
        print("✗ Excel文件验证失败")

    # 测试预览邮箱列表
    print("\n=== 测试预览邮箱列表 ===")
    preview_result = assistant.preview_email_list('test_emails.xlsx')
    if preview_result['success']:
        print(f"✓ 预览成功")
        print(f"  待发送邮箱数量: {len(preview_result['email_list'])}")
        print(f"  邮箱列表: {preview_result['email_list']}")
        print(f"  统计信息: {preview_result['statistics']}")
    else:
        print(f"✗ 预览失败: {preview_result['error']}")

    # 测试获取统计信息
    print("\n=== 测试获取统计信息 ===")
    stats_result = assistant.get_statistics('test_emails.xlsx')
    if stats_result['success']:
        print("✓ 获取统计信息成功")
        for key, value in stats_result['statistics'].items():
            print(f"  {key}: {value}")
    else:
        print(f"✗ 获取统计信息失败: {stats_result['error']}")

    # 注意：下面的测试需要有效的Gmail认证，在实际环境中谨慎运行
    print("\n=== 邮件发送测试（已跳过）===")
    print("⚠️  实际邮件发送测试需要：")
    print("   1. 有效的credentials.json文件")
    print("   2. 已认证的Gmail邮箱")
    print("   3. 将测试邮箱替换为真实邮箱")
    print("   4. 谨慎使用，避免发送垃圾邮件")

    # 清理测试文件
    if os.path.exists('test_emails.xlsx'):
        os.remove('test_emails.xlsx')
        print("\n✓ 测试文件已清理")

def test_api_client():
    """测试API客户端"""
    import requests
    import json

    print("\n=== API客户端测试 ===")
    print("请先启动API服务器: python api_server.py")

    base_url = "http://127.0.0.1:5000"

    # 测试健康检查
    try:
        response = requests.get(f"{base_url}/api/health")
        if response.status_code == 200:
            print("✓ API服务器健康检查通过")
        else:
            print("✗ API服务器健康检查失败")
    except requests.exceptions.ConnectionError:
        print("✗ 无法连接到API服务器，请确保服务器已启动")
        return

    # 创建测试Excel文件
    create_test_excel()

    # 测试预览邮箱列表
    try:
        response = requests.post(f"{base_url}/api/preview",
                               json={"excel_file_path": "test_emails.xlsx"})
        if response.status_code == 200:
            result = response.json()
            if result['success']:
                print("✓ API预览邮箱列表成功")
                print(f"  待发送邮箱: {result['email_list']}")
            else:
                print(f"✗ API预览失败: {result['error']}")
        else:
            print(f"✗ API请求失败: {response.status_code}")
    except Exception as e:
        print(f"✗ API测试异常: {e}")

    # 清理测试文件
    if os.path.exists('test_emails.xlsx'):
        os.remove('test_emails.xlsx')

if __name__ == "__main__":
    print("邮件助手测试程序")
    print("==================")

    # 基础功能测试
    test_email_assistant()

    # API测试
    test_api_client()

    print("\n测试完成！")