"""
模板管理模块
负责加载和处理多语言邮件模板，支持内联图片处理
"""
import os
import re
import logging
from typing import Optional, Dict, Any, Set, List, Tuple
from pathlib import Path
from bs4 import BeautifulSoup

# 处理不同的导入路径
try:
    from src.image_manager import ImageManager
except ImportError:
    from image_manager import ImageManager

class TemplateManager:
    """模板管理器"""

    def __init__(self, template_dir: str = "template"):
        """
        初始化模板管理器

        Args:
            template_dir: 模板文件目录路径
        """
        self.template_dir = Path(template_dir)
        self.logger = logging.getLogger(__name__)

        # 确保模板目录存在
        self.template_dir.mkdir(exist_ok=True)

        # 初始化图片管理器
        self.image_manager = ImageManager()

        # 支持的语言映射
        self.language_map = {
            "English": "en",
            "Spanish": "esp",
            "French": "fr",
            "German": "de",
            "Chinese": "zh",
            "Japanese": "ja"
        }

    def get_language_code(self, language: str) -> str:
        """
        获取语言代码

        Args:
            language: 语言名称

        Returns:
            语言代码，如果找不到则返回'en'
        """
        return self.language_map.get(language, "en")

    def load_subject_template(self, language: str) -> Optional[str]:
        """
        加载主题模板

        Args:
            language: 语言名称

        Returns:
            主题模板内容，如果不存在则返回None
        """
        language_code = self.get_language_code(language)

        # 尝试加载指定语言的模板
        template_file = self.template_dir / f"{language_code}-subject"
        if template_file.exists():
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    self.logger.debug(f"加载主题模板成功: {language_code}-subject")
                    return content
            except Exception as e:
                self.logger.error(f"读取主题模板失败: {template_file}, {e}")

        # 如果不是英语且没找到对应模板，尝试加载英语模板
        if language_code != "en":
            en_template_file = self.template_dir / "en-subject"
            if en_template_file.exists():
                try:
                    with open(en_template_file, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        self.logger.info(f"使用默认英语主题模板代替 {language_code}")
                        return content
                except Exception as e:
                    self.logger.error(f"读取默认主题模板失败: {en_template_file}, {e}")

        self.logger.warning(f"未找到主题模板: {language} ({language_code})")
        return None

    def load_html_content_template(self, language: str) -> Optional[str]:
        """
        加载HTML内容模板

        Args:
            language: 语言名称

        Returns:
            HTML内容模板，如果不存在则返回None
        """
        language_code = self.get_language_code(language)

        # 尝试加载指定语言的模板
        template_file = self.template_dir / f"{language_code}-html_content"
        if template_file.exists():
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    self.logger.debug(f"加载HTML内容模板成功: {language_code}-html_content")
                    return content
            except Exception as e:
                self.logger.error(f"读取HTML内容模板失败: {template_file}, {e}")

        # 如果不是英语且没找到对应模板，尝试加载英语模板
        if language_code != "en":
            en_template_file = self.template_dir / "en-html_content"
            if en_template_file.exists():
                try:
                    with open(en_template_file, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        self.logger.info(f"使用默认英语HTML内容模板代替 {language_code}")
                        return content
                except Exception as e:
                    self.logger.error(f"读取默认HTML内容模板失败: {en_template_file}, {e}")

        self.logger.warning(f"未找到HTML内容模板: {language} ({language_code})")
        return None

    def extract_template_parameters(self, template: str) -> Set[str]:
        """
        提取模板中的参数

        Args:
            template: 模板字符串

        Returns:
            参数名称集合
        """
        # 匹配 [参数名] 格式的参数
        pattern = r'\[([^\]]+)\]'
        parameters = set(re.findall(pattern, template))
        return parameters

    def validate_template_parameters(self, template: str, data_columns: list) -> Dict[str, Any]:
        """
        验证模板参数是否在数据列中存在

        Args:
            template: 模板字符串
            data_columns: 数据列名列表

        Returns:
            验证结果字典
        """
        if not template:
            return {"valid": True, "missing_parameters": [], "template_parameters": []}

        # 提取模板参数
        template_parameters = self.extract_template_parameters(template)

        # 检查缺失的参数
        missing_parameters = []
        for param in template_parameters:
            if param not in data_columns:
                missing_parameters.append(param)

        validation_result = {
            "valid": len(missing_parameters) == 0,
            "missing_parameters": missing_parameters,
            "template_parameters": list(template_parameters)
        }

        if missing_parameters:
            self.logger.error(f"模板参数验证失败，缺失参数: {missing_parameters}")
        else:
            self.logger.debug(f"模板参数验证成功，参数: {list(template_parameters)}")

        return validation_result

    def replace_template_parameters(self, template: str, row_data: Dict[str, Any]) -> str:
        """
        替换模板中的参数

        Args:
            template: 模板字符串
            row_data: 行数据字典

        Returns:
            替换后的字符串
        """
        if not template:
            return ""

        result = template

        # 提取所有参数
        parameters = self.extract_template_parameters(template)

        for param in parameters:
            placeholder = f"[{param}]"
            # 获取参数值，如果不存在则保持占位符
            value = row_data.get(param, placeholder)

            # 处理None值
            if value is None:
                value = ""
            else:
                value = str(value)

            result = result.replace(placeholder, value)

        return result

    def html_to_text(self, html_content: str) -> str:
        """
        将HTML内容转换为纯文本

        Args:
            html_content: HTML内容

        Returns:
            纯文本内容
        """
        if not html_content:
            return ""

        try:
            # 使用BeautifulSoup解析HTML
            soup = BeautifulSoup(html_content, 'html.parser')

            # 获取纯文本内容
            text = soup.get_text()

            # 清理多余的空白字符
            lines = [line.strip() for line in text.splitlines()]
            lines = [line for line in lines if line]  # 移除空行

            return '\n'.join(lines)

        except Exception as e:
            self.logger.error(f"HTML转文本失败: {e}")
            # 如果转换失败，使用简单的标签移除方法
            import re
            text = re.sub(r'<[^>]+>', '', html_content)
            return text.strip()

    def generate_email_content(self, language: str, row_data: Dict[str, Any]) -> Dict[str, str]:
        """
        根据语言和行数据生成邮件内容

        Args:
            language: 语言名称
            row_data: 行数据字典

        Returns:
            包含subject, html_content, content的字典
        """
        result = {
            "subject": "",
            "html_content": "",
            "content": "",
            "language": language,
            "errors": []
        }

        try:
            # 加载主题模板
            subject_template = self.load_subject_template(language)
            if subject_template:
                result["subject"] = self.replace_template_parameters(subject_template, row_data)
            else:
                result["errors"].append(f"未找到语言 {language} 的主题模板")

            # 加载HTML内容模板
            html_template = self.load_html_content_template(language)
            if html_template:
                result["html_content"] = self.replace_template_parameters(html_template, row_data)
                # 自动生成纯文本内容
                result["content"] = self.html_to_text(result["html_content"])
            else:
                result["errors"].append(f"未找到语言 {language} 的HTML内容模板")

        except Exception as e:
            error_msg = f"生成邮件内容失败: {e}"
            self.logger.error(error_msg)
            result["errors"].append(error_msg)

        return result

    def validate_templates_for_data(self, data_columns: list, language: str = None) -> Dict[str, Any]:
        """
        验证模板与数据列的兼容性

        Args:
            data_columns: 数据列名列表
            language: 指定语言，如果为None则验证所有语言

        Returns:
            验证结果字典
        """
        validation_results = {
            "overall_valid": True,
            "languages": {}
        }

        # 要验证的语言列表
        if language:
            languages_to_check = [language]
        else:
            # 检查所有可用的模板语言
            languages_to_check = []
            for file in self.template_dir.glob("*-subject"):
                lang_code = file.stem.split('-')[0]
                # 通过语言映射找到对应的语言名
                for lang_name, code in self.language_map.items():
                    if code == lang_code:
                        languages_to_check.append(lang_name)
                        break

        for lang in languages_to_check:
            lang_result = {
                "subject_validation": {"valid": True, "missing_parameters": []},
                "html_content_validation": {"valid": True, "missing_parameters": []},
                "valid": True
            }

            # 验证主题模板
            subject_template = self.load_subject_template(lang)
            if subject_template:
                lang_result["subject_validation"] = self.validate_template_parameters(
                    subject_template, data_columns
                )

            # 验证HTML内容模板
            html_template = self.load_html_content_template(lang)
            if html_template:
                lang_result["html_content_validation"] = self.validate_template_parameters(
                    html_template, data_columns
                )

            # 总体验证结果
            lang_result["valid"] = (
                lang_result["subject_validation"]["valid"] and
                lang_result["html_content_validation"]["valid"]
            )

            if not lang_result["valid"]:
                validation_results["overall_valid"] = False

            validation_results["languages"][lang] = lang_result

        return validation_results

    def extract_image_ids_from_html(self, html_content: str) -> List[str]:
        """
        从HTML内容中提取图片ID

        Args:
            html_content: HTML内容字符串

        Returns:
            图片ID列表
        """
        image_ids = []

        if not html_content:
            return image_ids

        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            img_tags = soup.find_all('img')

            for img_tag in img_tags:
                img_id = img_tag.get('id')
                if img_id:
                    image_ids.append(img_id)
                    self.logger.debug(f"发现图片ID: {img_id}")

        except Exception as e:
            self.logger.error(f"解析HTML中的图片标签失败: {e}")

        return image_ids

    def process_html_images(self, html_content: str) -> Tuple[str, Dict[str, Dict[str, Any]]]:
        """
        处理HTML内容中的图片，转换为CID格式并收集图片信息

        Args:
            html_content: HTML内容字符串

        Returns:
            元组：(处理后的HTML内容, 图片信息字典)
        """
        if not html_content:
            return html_content, {}

        processed_html = html_content
        image_info = {}

        try:
            # 提取图片ID
            image_ids = self.extract_image_ids_from_html(html_content)

            if not image_ids:
                return html_content, {}

            soup = BeautifulSoup(html_content, 'html.parser')

            # 处理每个图片
            for image_id in image_ids:
                # 验证图片文件
                validation = self.image_manager.validate_image_file(image_id)

                if validation["valid"]:
                    # 生成CID
                    cid = f"image_{image_id}"

                    # 替换HTML中的img标签
                    img_tags = soup.find_all('img', {'id': image_id})
                    for img_tag in img_tags:
                        img_tag['src'] = f"cid:{cid}"
                        # 可以保留id属性，也可以移除
                        # img_tag.attrs.pop('id', None)
                        self.logger.debug(f"替换图片标签: {image_id} -> cid:{cid}")

                    # 记录图片信息
                    image_info[image_id] = {
                        "cid": cid,
                        "file_path": validation["file_path"],
                        "mime_type": validation["mime_type"],
                        "size": validation["size"],
                        "valid": True
                    }
                else:
                    # 图片无效，记录错误但继续处理
                    self.logger.warning(f"图片文件无效: {image_id} - {validation['error']}")
                    image_info[image_id] = {
                        "valid": False,
                        "error": validation["error"]
                    }

            processed_html = str(soup)

        except Exception as e:
            self.logger.error(f"处理HTML图片失败: {e}")
            return html_content, {}

        return processed_html, image_info

    def validate_html_images(self, html_content: str) -> Dict[str, Any]:
        """
        验证HTML内容中的图片是否有效

        Args:
            html_content: HTML内容字符串

        Returns:
            验证结果字典
        """
        result = {
            "valid": True,
            "total_images": 0,
            "valid_images": 0,
            "invalid_images": [],
            "images": {}
        }

        if not html_content:
            return result

        try:
            # 提取图片ID
            image_ids = self.extract_image_ids_from_html(html_content)
            result["total_images"] = len(image_ids)

            for image_id in image_ids:
                validation = self.image_manager.validate_image_file(image_id)
                result["images"][image_id] = validation

                if validation["valid"]:
                    result["valid_images"] += 1
                else:
                    result["invalid_images"].append({
                        "image_id": image_id,
                        "error": validation["error"]
                    })

            # 如果有无效图片，整体验证失败
            if result["invalid_images"]:
                result["valid"] = False

        except Exception as e:
            self.logger.error(f"验证HTML图片失败: {e}")
            result["valid"] = False
            result["error"] = str(e)

        return result

    def generate_email_content_with_images(self, language: str, row_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据语言和行数据生成邮件内容，包括图片处理

        Args:
            language: 语言名称
            row_data: 行数据字典

        Returns:
            包含subject, html_content, content, images的字典
        """
        result = {
            "subject": "",
            "html_content": "",
            "content": "",
            "language": language,
            "images": {},
            "has_images": False,
            "errors": []
        }

        try:
            # 生成基本邮件内容
            basic_content = self.generate_email_content(language, row_data)
            result.update(basic_content)

            # 处理HTML中的图片
            if result["html_content"]:
                processed_html, image_info = self.process_html_images(result["html_content"])

                result["html_content"] = processed_html
                result["images"] = image_info
                result["has_images"] = bool(image_info)

                # 检查是否有无效图片
                invalid_images = [img_id for img_id, info in image_info.items() if not info.get("valid", True)]
                if invalid_images:
                    result["errors"].extend([
                        f"图片无效: {img_id} - {image_info[img_id].get('error', '未知错误')}"
                        for img_id in invalid_images
                    ])

                self.logger.info(f"处理HTML图片完成: {len(image_info)} 个图片")

        except Exception as e:
            error_msg = f"生成包含图片的邮件内容失败: {e}"
            self.logger.error(error_msg)
            result["errors"].append(error_msg)

        return result