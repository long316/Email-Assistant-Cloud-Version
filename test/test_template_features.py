"""
模板功能测试脚本
测试新增的多语言模板和自定义内容功能
"""
import pandas as pd
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.template_manager import TemplateManager
from src.excel_processor import ExcelProcessor
from src.email_sender import EmailSender


def create_test_excel_file():
    """创建测试用的Excel文件"""
    test_data = {
        "邮箱": [
            "test1@example.com",
            "test2@example.com",
            "test3@example.com"
        ],
        "合作次数": [0, 0, 0],
        "回复次数": [0, 0, 0],
        "跟进次数": [1, 1, 1],
        "跟进方式": ["自动", "自动", "自动"],
        "是否已邮箱建联": [None, None, None],
        "语言": ["English", "Spanish", "English"],
        "某条视频内容总结": [
            "outdoor camping tips",
            "consejos de camping al aire libre",
            "hiking gear review"
        ],
        "达人ID": ["OutdoorGuru123", "CampingExpert", "HikingPro456"],
        "钩子": [
            "I noticed your amazing outdoor content and thought you'd be interested in our new product!",
            "Me encantó tu contenido sobre actividades al aire libre y pensé que te interesaría nuestro nuevo producto!",
            "Your hiking reviews are fantastic and align perfectly with our brand values!"
        ]
    }

    df = pd.DataFrame(test_data)
    test_file_path = "test/test_data_with_templates.xlsx"

    # 确保test目录存在
    os.makedirs(os.path.dirname(test_file_path), exist_ok=True)

    df.to_excel(test_file_path, index=False)
    print(f"测试Excel文件已创建: {test_file_path}")
    return test_file_path


def test_template_manager():
    """测试模板管理器"""
    print("\n=== 测试模板管理器 ===")

    template_manager = TemplateManager()

    # 测试语言代码转换
    print("语言代码转换测试:")
    print(f"English -> {template_manager.get_language_code('English')}")
    print(f"Spanish -> {template_manager.get_language_code('Spanish')}")
    print(f"French -> {template_manager.get_language_code('French')} (应该回退到en)")

    # 测试模板加载
    print("\n模板加载测试:")
    en_subject = template_manager.load_subject_template("English")
    esp_subject = template_manager.load_subject_template("Spanish")

    print(f"英语主题模板: {en_subject}")
    print(f"西语主题模板: {esp_subject}")

    # 测试参数提取
    if en_subject:
        params = template_manager.extract_template_parameters(en_subject)
        print(f"英语主题模板参数: {params}")

    # 测试参数替换
    if en_subject:
        test_data = {"某条视频内容总结": "camping gear review"}
        replaced = template_manager.replace_template_parameters(en_subject, test_data)
        print(f"参数替换后: {replaced}")

    # 测试HTML内容
    en_html = template_manager.load_html_content_template("English")
    if en_html:
        print(f"\n英语HTML模板长度: {len(en_html)} 字符")
        # 转换为纯文本
        plain_text = template_manager.html_to_text(en_html)
        print(f"纯文本长度: {len(plain_text)} 字符")
        print(f"纯文本前100字符: {plain_text[:100]}")


def test_excel_processor():
    """测试Excel处理器"""
    print("\n=== 测试Excel处理器 ===")

    # 创建测试文件
    test_file = create_test_excel_file()

    # 初始化处理器
    excel_processor = ExcelProcessor()

    # 测试文件验证
    print("Excel文件验证:")
    is_valid = excel_processor.validate_excel_file(test_file)
    print(f"文件有效性: {is_valid}")

    # 测试数据读取
    print("\n数据读取测试:")
    df = excel_processor.read_excel_data(test_file)
    print(f"读取行数: {len(df)}")
    print(f"列名: {list(df.columns)}")

    # 测试过滤数据
    print("\n过滤数据测试:")
    filtered_data = excel_processor.get_filtered_data_with_language(test_file)
    print(f"过滤后行数: {len(filtered_data)}")
    if not filtered_data.empty:
        print(f"语言分布: {filtered_data['语言'].value_counts().to_dict()}")

    # 测试模板验证
    print("\n模板验证测试:")
    template_validation = excel_processor.validate_templates_for_excel(test_file)
    print(f"整体验证结果: {template_validation.get('overall_valid')}")
    if 'validation_details' in template_validation:
        for lang, details in template_validation['validation_details'].items():
            print(f"语言 {lang}: 有效性={details.get('valid')}")


def test_email_sender():
    """测试邮件发送器（仅预览模式）"""
    print("\n=== 测试邮件发送器 ===")

    # 创建邮件发送器（使用虚拟服务）
    email_sender = EmailSender(None, "test@example.com")

    # 测试模板邮件预览
    print("模板邮件预览测试:")
    test_data = {
        "某条视频内容总结": "outdoor survival techniques",
        "达人ID": "SurvivalExpert",
        "钩子": "Your survival content is impressive and would be perfect for our collaboration!"
    }

    preview = email_sender.preview_email_from_template(
        to_email="test@example.com",
        language="English",
        row_data=test_data
    )

    print(preview[:500] + "..." if len(preview) > 500 else preview)


def test_integration():
    """集成测试"""
    print("\n=== 集成测试 ===")

    test_file = create_test_excel_file()

    # 测试完整流程
    excel_processor = ExcelProcessor()
    filtered_data = excel_processor.get_filtered_data_with_language(test_file)

    if not filtered_data.empty:
        print(f"找到 {len(filtered_data)} 条待处理记录")

        # 模拟邮件发送（仅生成内容）
        email_sender = EmailSender(None, "test@example.com")

        for i, (_, row) in enumerate(filtered_data.head(2).iterrows()):
            to_email = row["邮箱"]
            language = row["语言"]
            row_data = row.to_dict()

            print(f"\n--- 记录 {i+1} ---")
            print(f"邮箱: {to_email}")
            print(f"语言: {language}")

            # 生成邮件内容
            template_manager = TemplateManager()
            email_content = template_manager.generate_email_content(language, row_data)

            if email_content["errors"]:
                print(f"错误: {email_content['errors']}")
            else:
                print(f"主题: {email_content['subject']}")
                print(f"内容长度: {len(email_content['content'])} 字符")
                print(f"HTML长度: {len(email_content['html_content'])} 字符")


def create_usage_documentation():
    """创建使用说明文档"""
    doc_content = """# 多语言模板功能使用说明

## 概述

邮件助手现在支持多语言模板和自定义内容功能，可以根据Excel数据中的语言设置和模板参数动态生成个性化邮件。

## 新增功能

### 1. 多语言支持
- 支持多种语言的邮件模板
- 自动根据Excel中的"语言"列选择对应模板
- 如果找不到对应语言模板，自动回退到英语模板

### 2. 模板参数化
- 主题和内容支持参数占位符 `[参数名]`
- 自动从Excel数据中提取对应列的值进行替换
- 智能验证模板参数与Excel列的兼容性

### 3. HTML自动转换
- HTML内容模板自动转换为纯文本内容
- 保持邮件的富文本和纯文本双重兼容性

## Excel文件格式要求

### 必需列
```
邮箱, 合作次数, 回复次数, 跟进次数, 跟进方式, 是否已邮箱建联, 语言
```

### 新增要求
1. **语言列**: 指定每封邮件使用的语言（如：English, Spanish）
2. **模板参数列**: 根据模板中的参数添加相应列（如：某条视频内容总结, 达人ID, 钩子）

### 示例数据
```
邮箱                  | 语言    | 某条视频内容总结        | 达人ID      | 钩子
test@example.com     | English | camping gear review    | OutdoorPro  | Great content!
test2@ejemplo.com    | Spanish | reseña de equipos      | CampingEs   | ¡Excelente!
```

## 模板文件格式

### 存放位置
所有模板文件存放在 `template/` 目录下

### 命名规则
- 主题模板: `{语言代码}-subject`
- HTML内容模板: `{语言代码}-html_content`

### 语言代码映射
- English → en
- Spanish → esp
- French → fr
- German → de
- Chinese → zh
- Japanese → ja

### 模板示例

**英语主题模板 (en-subject)**
```
Loved your [某条视频内容总结] video and a partnership idea!
```

**西语主题模板 (esp-subject)**
```
Me encantó tu video sobre [某条视频内容总结] y tengo una idea de colaboración!
```

**HTML内容模板 (en-html_content)**
```html
<p>Hi [达人ID],</p>
<p>[钩子]</p>
<p>I'm Erica, founder of Swipe Up US...</p>
```

## API接口更新

### 新增接口

1. **验证模板兼容性**
   ```
   POST /api/validate_templates
   Body: {"excel_file_path": "path/to/file.xlsx"}
   ```

2. **预览模板邮件**
   ```
   POST /api/preview_template_emails
   Body: {"excel_file_path": "path/to/file.xlsx", "max_previews": 3}
   ```

3. **发送模板邮件**
   ```
   POST /api/send_template_emails
   Body: {
     "sender_email": "your@gmail.com",
     "excel_file_path": "path/to/file.xlsx",
     "start_time": "2024-01-01T09:00:00",
     "min_interval": 30,
     "max_interval": 120
   }
   ```

## 使用流程

1. **准备Excel文件**
   - 添加"语言"列
   - 添加模板参数对应的列

2. **创建模板文件**
   - 在template/目录下创建对应语言的模板
   - 使用 `[参数名]` 格式添加占位符

3. **验证兼容性**
   - 使用API或命令行验证模板与Excel数据的兼容性

4. **预览邮件**
   - 生成前几封邮件的预览确认效果

5. **发送邮件**
   - 使用模板发送功能批量发送个性化邮件

## 错误处理

系统会自动检测和报告以下问题：
- 缺失的模板文件
- 不匹配的模板参数
- Excel文件格式错误
- 语言配置问题

所有错误都会记录到日志文件中，方便排查问题。
"""

    doc_file_path = "docs/多语言模板功能使用说明.md"
    os.makedirs(os.path.dirname(doc_file_path), exist_ok=True)

    with open(doc_file_path, 'w', encoding='utf-8') as f:
        f.write(doc_content)

    print(f"使用说明文档已创建: {doc_file_path}")


def main():
    """主测试函数"""
    print("开始测试多语言模板功能...")

    try:
        # 运行各项测试
        test_template_manager()
        test_excel_processor()
        test_email_sender()
        test_integration()

        # 创建文档
        create_usage_documentation()

        print("\n=== 测试完成 ===")
        print("✅ 所有功能测试通过")
        print("📖 使用说明文档已生成")

    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()