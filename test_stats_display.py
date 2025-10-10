"""
测试统计信息显示修复
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# 模拟发送结果数据
mock_result = {
    "success": True,
    "stats": {
        "total_emails": 2,
        "success_count": 1,
        "failure_count": 1,
        "remaining": 0
    },
    "duration": "0:00:30.123456",
    "status": "idle"
}

# 测试修复后的显示逻辑
if mock_result["success"]:
    print("\n邮件发送完成!")
    # 从stats对象中获取统计信息
    stats = mock_result.get('stats', {})
    print(f"总数: {stats.get('total_emails', 0)}")
    print(f"成功: {stats.get('success_count', 0)}")
    print(f"失败: {stats.get('failure_count', 0)}")
    print(f"耗时: {mock_result.get('duration', '未知')}")
else:
    print(f"邮件发送失败: {mock_result.get('error', '未知错误')}")