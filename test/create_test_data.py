import pandas as pd

# 创建新的测试数据，状态为未发送
test_data = {
    "邮箱": [
        "test1_new@example.com",
        "test2_new@example.com"
    ],
    "合作次数": [0, 0],
    "回复次数": [0, 0],
    "跟进次数": [1, 1],
    "跟进方式": ["自动", "自动"],
    "是否已邮箱建联": [None, None],  # 未发送状态
    "语言": ["English", "Spanish"],
    "某条视频内容总结": ["test video content 1", "contenido de video de prueba"],
    "达人ID": ["TestUser1", "TestUser2"],
    "钩子": ["Test hook 1", "Gancho de prueba"]
}

df = pd.DataFrame(test_data)
df.to_excel("test_fresh_data.xlsx", index=False)
print("新测试文件已创建")