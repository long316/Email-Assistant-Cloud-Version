"""
测试图片发送功能
"""
import sys
import os
import base64
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from image_manager import ImageManager
from template_manager import TemplateManager

def create_test_image():
    """创建一个简单的测试图片文件"""
    # 创建一个简单的1x1像素PNG图片的Base64数据
    # 这是一个透明的1x1像素PNG图片
    png_data = base64.b64decode(
        b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    )

    # 确保目录存在
    os.makedirs("files/pics", exist_ok=True)

    # 写入测试图片
    with open("files/pics/logo.png", "wb") as f:
        f.write(png_data)

    print("测试图片已创建: files/pics/logo.png")

def test_image_manager():
    """测试图片管理器功能"""
    print("\n=== 测试图片管理器 ===")

    # 创建测试图片
    create_test_image()

    # 初始化图片管理器
    image_manager = ImageManager()

    # 测试获取可用图片
    available_images = image_manager.get_available_images()
    print(f"可用图片: {available_images}")

    # 测试图片验证
    if "logo" in available_images:
        validation = image_manager.validate_image_file("logo")
        print(f"图片验证结果: {validation}")

        # 测试图片加载
        if validation["valid"]:
            image_data = image_manager.load_image_data("logo")
            print(f"图片加载成功: {image_data['success']}")
            print(f"图片大小: {image_data['size']} bytes")
            print(f"图片类型: {image_data['mime_type']}")

    # 测试缓存信息
    cache_info = image_manager.get_cache_info()
    print(f"缓存信息: {cache_info}")

def test_template_manager_with_images():
    """测试模板管理器的图片处理功能"""
    print("\n=== 测试模板管理器图片处理 ===")

    template_manager = TemplateManager()

    # 测试HTML图片ID提取
    test_html = '<p>Hello!</p><img id="logo" /><p>More text</p><img id="banner" />'
    image_ids = template_manager.extract_image_ids_from_html(test_html)
    print(f"提取的图片ID: {image_ids}")

    # 测试HTML图片处理
    processed_html, image_info = template_manager.process_html_images(test_html)
    print(f"处理后的HTML: {processed_html}")
    print(f"图片信息: {image_info}")

    # 测试HTML图片验证
    validation = template_manager.validate_html_images(test_html)
    print(f"HTML图片验证: {validation}")

def test_email_content_generation():
    """测试邮件内容生成"""
    print("\n=== 测试邮件内容生成 ===")

    template_manager = TemplateManager()

    # 测试数据
    test_data = {
        "达人ID": "TestUser",
        "钩子": "Love your outdoor content!",
        "某条视频内容总结": "camping tips for beginners"
    }

    # 使用包含图片的模板（如果存在）
    try:
        # 模拟包含图片的HTML内容
        test_html = """
        <p>Hi [达人ID],</p>
        <p>[钩子]</p>
        <div style="text-align: center;">
            <img id="logo" alt="Logo" />
        </div>
        <p>Great video about [某条视频内容总结]!</p>
        """

        # 处理图片
        processed_html, image_info = template_manager.process_html_images(test_html)
        print(f"原始HTML: {test_html}")
        print(f"处理后HTML: {processed_html}")
        print(f"图片信息: {image_info}")

        # 替换参数
        final_html = template_manager.replace_template_parameters(processed_html, test_data)
        print(f"最终HTML: {final_html}")

    except Exception as e:
        print(f"测试过程中出现错误: {e}")

if __name__ == "__main__":
    print("开始测试图片功能...")

    try:
        test_image_manager()
        test_template_manager_with_images()
        test_email_content_generation()

        print("\n✓ 所有测试完成!")

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()