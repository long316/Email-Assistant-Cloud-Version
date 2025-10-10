"""
邮件发送模块
负责通过Gmail API发送邮件，支持图片内联附件
"""
import base64
import logging
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, Dict, Any, List
import pandas as pd

from googleapiclient.errors import HttpError
from src.template_manager import TemplateManager

# 处理不同的导入路径
try:
    from src.attachment_manager import AttachmentManager
except ImportError:
    from attachment_manager import AttachmentManager

class EmailSender:
    """邮件发送器"""

    def __init__(self, gmail_service, sender_email: str, template_dir: str = "template"):
        """
        初始化邮件发送器

        Args:
            gmail_service: Gmail API服务对象
            sender_email: 发件人邮箱地址
            template_dir: 模板目录路径
        """
        self.gmail_service = gmail_service
        self.sender_email = sender_email
        self.template_manager = TemplateManager(template_dir)
        self.attachment_manager = AttachmentManager()
        self.logger = logging.getLogger(__name__)

    def create_email_message(
        self,
        to_email: str,
        subject: str,
        content: str,
        html_content: Optional[str] = None
    ) -> Optional[EmailMessage]:
        """
        创建邮件消息

        Args:
            to_email: 收件人邮箱
            subject: 邮件主题
            content: 邮件文本内容
            html_content: 邮件HTML内容（可选）

        Returns:
            邮件消息对象，失败时返回None
        """
        try:
            message = EmailMessage()

            # 设置邮件基本信息
            message["To"] = to_email
            message["From"] = self.sender_email
            message["Subject"] = subject

            # 设置邮件内容
            if html_content:
                message.set_content(content)
                message.add_alternative(html_content, subtype="html")
            else:
                message.set_content(content)

            self.logger.debug(f"邮件消息创建成功: {to_email}")
            return message

        except Exception as e:
            self.logger.error(f"创建邮件消息失败: {e}")
            return None

    def send_email(
        self,
        to_email: str,
        subject: str,
        content: str,
        html_content: Optional[str] = None,
        attachments: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        发送邮件（自动支持附件）

        Args:
            to_email: 收件人邮箱
            subject: 邮件主题
            content: 邮件文本内容
            html_content: 邮件HTML内容（可选）
            attachments: 附件文件ID列表（可选）

        Returns:
            发送结果字典，包含success, message_id, error等字段
        """
        # 使用统一的附件发送方法
        return self.send_email_with_attachments(
            to_email, subject, content, html_content, None, attachments
        )

    def send_bulk_emails(
        self,
        email_list: list,
        subject: str,
        content: str,
        html_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        批量发送邮件

        Args:
            email_list: 收件人邮箱列表
            subject: 邮件主题
            content: 邮件文本内容
            html_content: 邮件HTML内容（可选）

        Returns:
            批量发送结果字典
        """
        results = {
            "total": len(email_list),
            "success_count": 0,
            "failure_count": 0,
            "results": []
        }

        for email in email_list:
            result = self.send_email(email, subject, content, html_content)
            results["results"].append(result)

            if result["success"]:
                results["success_count"] += 1
            else:
                results["failure_count"] += 1

        self.logger.info(
            f"批量邮件发送完成: 总数 {results['total']}, "
            f"成功 {results['success_count']}, 失败 {results['failure_count']}"
        )

        return results

    def validate_email_format(self, email: str) -> bool:
        """
        验证邮箱格式

        Args:
            email: 邮箱地址

        Returns:
            邮箱格式是否有效
        """
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def get_default_email_content(self, to_email: str) -> Dict[str, str]:
        """
        获取默认邮件内容

        Args:
            to_email: 收件人邮箱

        Returns:
            包含subject和content的字典
        """
        return {
            "subject": "合作邀请 - 期待与您建立联系",
            "content": f"""您好！

我是通过相关渠道了解到您的联系方式，希望能够与您建立业务合作关系。

我们公司专注于为客户提供优质的服务，相信我们的合作能够为双方带来互利共赢的结果。

如果您有兴趣了解更多合作详情，请随时回复此邮件或联系我们。

期待您的回复！

最好的祝愿，
{self.sender_email}

---
此邮件由自动化系统发送，如有疑问请回复此邮件。
"""
        }

    def preview_email(
        self,
        to_email: str,
        subject: str,
        content: str,
        html_content: Optional[str] = None
    ) -> str:
        """
        预览邮件内容

        Args:
            to_email: 收件人邮箱
            subject: 邮件主题
            content: 邮件文本内容
            html_content: 邮件HTML内容（可选）

        Returns:
            邮件预览文本
        """
        preview = f"""
邮件预览:
========================================
发件人: {self.sender_email}
收件人: {to_email}
主题: {subject}
========================================

内容:
{content}

========================================
"""
        if html_content:
            preview += f"\nHTML内容:\n{html_content}\n\n"

        return preview

    def send_email_from_template(self, to_email: str, language: str, row_data: Dict[str, Any], attachments: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        基于模板和数据行发送邮件（自动支持图片和附件）

        Args:
            to_email: 收件人邮箱
            language: 语言
            row_data: 行数据字典
            attachments: 附件文件列表

        Returns:
            发送结果字典
        """
        try:
            # 生成包含图片处理的邮件内容
            email_content = self.template_manager.generate_email_content_with_images(language, row_data)

            if email_content["errors"]:
                return {
                    "success": False,
                    "error": f"模板处理错误: {', '.join(email_content['errors'])}",
                    "to_email": to_email,
                    "language": language
                }

            # 根据是否有附件和图片选择发送方法
            if attachments or email_content["has_images"]:
                # 使用完整的多媒体发送方法
                result = self.send_email_with_attachments(
                    to_email=to_email,
                    subject=email_content["subject"],
                    content=email_content["content"],
                    html_content=email_content["html_content"],
                    attachments=attachments or [],
                    images=email_content["images"] if email_content["has_images"] else []
                )
            else:
                # 简单邮件发送
                result = self.send_email(
                    to_email=to_email,
                    subject=email_content["subject"],
                    content=email_content["content"],
                    html_content=email_content["html_content"]
                )

            # 添加模板和语言信息
            result["template_used"] = True
            result["language"] = language
            return result

        except Exception as e:
            self.logger.error(f"基于模板发送邮件失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "to_email": to_email,
                "language": language,
                "template_used": True
            }

    def send_bulk_emails_from_data(self, filtered_data: pd.DataFrame) -> Dict[str, Any]:
        """
        基于过滤后的数据批量发送邮件

        Args:
            filtered_data: 过滤后的DataFrame，包含邮箱、语言和其他参数列

        Returns:
            批量发送结果字典
        """
        results = {
            "total": len(filtered_data),
            "success_count": 0,
            "failure_count": 0,
            "results": [],
            "languages_used": set()
        }

        for _, row in filtered_data.iterrows():
            to_email = row["邮箱"]
            language = row.get("语言", "English")
            row_data = row.to_dict()

            # 记录使用的语言
            results["languages_used"].add(language)

            # 发送邮件
            result = self.send_email_from_template(to_email, language, row_data)
            results["results"].append(result)

            if result["success"]:
                results["success_count"] += 1
            else:
                results["failure_count"] += 1

        # 转换set为list以便JSON序列化
        results["languages_used"] = list(results["languages_used"])

        self.logger.info(
            f"批量邮件发送完成: 总数 {results['total']}, "
            f"成功 {results['success_count']}, 失败 {results['failure_count']}, "
            f"使用语言: {results['languages_used']}"
        )

        return results

    def preview_email_from_template(self, to_email: str, language: str, row_data: Dict[str, Any]) -> str:
        """
        基于模板预览邮件内容

        Args:
            to_email: 收件人邮箱
            language: 语言
            row_data: 行数据字典

        Returns:
            邮件预览文本
        """
        try:
            # 生成邮件内容
            email_content = self.template_manager.generate_email_content(language, row_data)

            if email_content["errors"]:
                return f"模板处理错误:\n{chr(10).join(email_content['errors'])}"

            # 生成预览
            preview = f"""
邮件预览 (基于模板):
========================================
发件人: {self.sender_email}
收件人: {to_email}
语言: {language}
主题: {email_content["subject"]}
========================================

纯文本内容:
{email_content["content"]}

========================================

HTML内容:
{email_content["html_content"]}

========================================
"""
            return preview

        except Exception as e:
            self.logger.error(f"预览邮件失败: {e}")
            return f"预览失败: {e}"

    def validate_email_templates(self, data_columns: list) -> Dict[str, Any]:
        """
        验证邮件模板与数据列的兼容性

        Args:
            data_columns: 数据列名列表

        Returns:
            验证结果字典
        """
        return self.template_manager.validate_templates_for_data(data_columns)

    def create_email_message_with_images(
        self,
        to_email: str,
        subject: str,
        content: str,
        html_content: Optional[str] = None,
        images: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> Optional[MIMEMultipart]:
        """
        创建包含图片附件的邮件消息

        Args:
            to_email: 收件人邮箱
            subject: 邮件主题
            content: 邮件文本内容
            html_content: 邮件HTML内容（可选）
            images: 图片信息字典

        Returns:
            MIME邮件消息对象，失败时返回None
        """
        try:
            # 创建multipart/related消息，支持内联图片
            message = MIMEMultipart('related')

            # 设置邮件基本信息
            message["To"] = to_email
            message["From"] = self.sender_email
            message["Subject"] = subject

            # 创建multipart/alternative部分，包含文本和HTML
            if html_content and images:
                # 有HTML内容和图片时，使用复杂结构
                msg_alternative = MIMEMultipart('alternative')

                # 添加纯文本部分
                text_part = MIMEText(content, 'plain', 'utf-8')
                msg_alternative.attach(text_part)

                # 添加HTML部分
                html_part = MIMEText(html_content, 'html', 'utf-8')
                msg_alternative.attach(html_part)

                # 将alternative部分附加到主消息
                message.attach(msg_alternative)

                # 添加图片附件
                self._attach_images_to_message(message, images)

            elif html_content:
                # 只有HTML内容，无图片
                msg_alternative = MIMEMultipart('alternative')

                text_part = MIMEText(content, 'plain', 'utf-8')
                msg_alternative.attach(text_part)

                html_part = MIMEText(html_content, 'html', 'utf-8')
                msg_alternative.attach(html_part)

                message.attach(msg_alternative)
            else:
                # 只有纯文本
                text_part = MIMEText(content, 'plain', 'utf-8')
                message.attach(text_part)

            self.logger.debug(f"包含图片的邮件消息创建成功: {to_email}")
            return message

        except Exception as e:
            self.logger.error(f"创建包含图片的邮件消息失败: {e}")
            return None

    def _attach_images_to_message(self, message: MIMEMultipart, images: Dict[str, Dict[str, Any]]):
        """
        将图片附加到邮件消息中

        Args:
            message: MIME邮件消息对象
            images: 图片信息字典
        """
        for image_id, image_info in images.items():
            if not image_info.get("valid", False):
                self.logger.warning(f"跳过无效图片: {image_id}")
                continue

            try:
                # 加载图片数据
                image_data = self.template_manager.image_manager.load_image_data(image_id)

                if not image_data["success"]:
                    self.logger.error(f"加载图片数据失败: {image_id} - {image_data['error']}")
                    continue

                # 解码Base64图片数据
                image_bytes = base64.b64decode(image_data["base64_data"])

                # 创建图片附件
                mime_image = MIMEImage(image_bytes)
                mime_image.add_header('Content-ID', f'<{image_info["cid"]}>')
                mime_image.add_header('Content-Disposition', 'inline', filename=f'{image_id}')

                # 添加到消息
                message.attach(mime_image)

                self.logger.debug(f"图片附件添加成功: {image_id} (CID: {image_info['cid']})")

            except Exception as e:
                self.logger.error(f"附加图片失败: {image_id} - {e}")

    def send_email_with_images(
        self,
        to_email: str,
        subject: str,
        content: str,
        html_content: Optional[str] = None,
        images: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        发送包含图片的邮件

        Args:
            to_email: 收件人邮箱
            subject: 邮件主题
            content: 邮件文本内容
            html_content: 邮件HTML内容（可选）
            images: 图片信息字典（可选）

        Returns:
            发送结果字典
        """
        try:
            # 如果没有图片或HTML，使用原始方法
            if not images or not html_content:
                return self.send_email(to_email, subject, content, html_content)

            # 创建包含图片的邮件消息
            message = self.create_email_message_with_images(
                to_email, subject, content, html_content, images
            )

            if not message:
                return {
                    "success": False,
                    "error": "创建包含图片的邮件消息失败",
                    "to_email": to_email
                }

            # 编码邮件消息
            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            create_message = {"raw": encoded_message}

            # 发送邮件
            result = (
                self.gmail_service.users()
                .messages()
                .send(userId="me", body=create_message)
                .execute()
            )

            message_id = result.get("id", "")
            self.logger.info(f"包含图片的邮件发送成功: {to_email}, Message ID: {message_id}")

            return {
                "success": True,
                "message_id": message_id,
                "to_email": to_email,
                "subject": subject,
                "image_count": len(images) if images else 0
            }

        except HttpError as e:
            error_msg = f"Gmail API错误: {e}"
            self.logger.error(f"发送包含图片的邮件失败: {to_email}, {error_msg}")

            return {
                "success": False,
                "error": error_msg,
                "to_email": to_email,
                "subject": subject
            }

        except Exception as e:
            error_msg = f"发送包含图片的邮件时发生未知错误: {e}"
            self.logger.error(f"发送包含图片的邮件失败: {to_email}, {error_msg}")

            return {
                "success": False,
                "error": error_msg,
                "to_email": to_email,
                "subject": subject
            }

    def send_email_from_template_with_images(self, to_email: str, language: str, row_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        基于模板和数据行发送邮件（支持图片）

        Args:
            to_email: 收件人邮箱
            language: 语言
            row_data: 行数据字典

        Returns:
            发送结果字典
        """
        try:
            # 生成包含图片处理的邮件内容
            email_content = self.template_manager.generate_email_content_with_images(language, row_data)

            if email_content["errors"]:
                return {
                    "success": False,
                    "error": f"模板处理错误: {', '.join(email_content['errors'])}",
                    "to_email": to_email,
                    "language": language
                }

            # 发送邮件（自动处理图片）
            if email_content["has_images"]:
                result = self.send_email_with_images(
                    to_email=to_email,
                    subject=email_content["subject"],
                    content=email_content["content"],
                    html_content=email_content["html_content"],
                    images=email_content["images"]
                )
            else:
                # 没有图片时使用原始方法
                result = self.send_email(
                    to_email=to_email,
                    subject=email_content["subject"],
                    content=email_content["content"],
                    html_content=email_content["html_content"]
                )

            # 添加语言信息到结果
            result["language"] = language
            result["has_images"] = email_content["has_images"]

            return result

        except Exception as e:
            self.logger.error(f"基于模板发送邮件失败: {e}")
            return {
                "success": False,
                "error": f"基于模板发送邮件失败: {e}",
                "to_email": to_email,
                "language": language
            }

    def _attach_files_to_message(self, message: MIMEMultipart, attachments: List[str]):
        """
        将文件附件添加到邮件消息中

        Args:
            message: MIME邮件消息对象
            attachments: 附件文件ID列表
        """
        if not attachments:
            return

        for file_id in attachments:
            try:
                # 加载附件数据
                attachment_data = self.attachment_manager.load_attachment_data(file_id)

                if not attachment_data["success"]:
                    self.logger.error(f"加载附件数据失败: {file_id} - {attachment_data['error']}")
                    continue

                # 解码Base64附件数据
                file_bytes = base64.b64decode(attachment_data["base64_data"])
                mime_type = attachment_data["mime_type"]
                filename = attachment_data["filename"]

                # 根据MIME类型创建附件
                if mime_type.startswith('text/'):
                    # 文本文件
                    mime_attachment = MIMEApplication(file_bytes, _subtype=mime_type.split('/')[-1])
                elif mime_type.startswith('application/'):
                    # 应用程序文件（PDF、Office文档等）
                    mime_attachment = MIMEApplication(file_bytes, _subtype=mime_type.split('/')[-1])
                else:
                    # 其他类型使用通用附件
                    mime_attachment = MIMEBase(*mime_type.split('/', 1))
                    mime_attachment.set_payload(file_bytes)
                    encoders.encode_base64(mime_attachment)

                # 设置附件头信息
                mime_attachment.add_header(
                    'Content-Disposition',
                    'attachment',
                    filename=filename
                )

                # 添加到消息
                message.attach(mime_attachment)
                self.logger.debug(f"文件附件添加成功: {filename}")

            except Exception as e:
                self.logger.error(f"附加文件失败: {file_id} - {e}")

    def create_email_message_with_attachments(
        self,
        to_email: str,
        subject: str,
        content: str,
        html_content: Optional[str] = None,
        images: Optional[Dict[str, Dict[str, Any]]] = None,
        attachments: Optional[List[str]] = None
    ) -> Optional[MIMEMultipart]:
        """
        创建包含文件附件的邮件消息

        Args:
            to_email: 收件人邮箱
            subject: 邮件主题
            content: 邮件文本内容
            html_content: 邮件HTML内容（可选）
            images: 图片信息字典（可选）
            attachments: 附件文件ID列表（可选）

        Returns:
            MIME邮件消息对象，失败时返回None
        """
        try:
            # 创建邮件消息（如果有图片或附件，使用mixed结构）
            has_attachments = bool(attachments and len(attachments) > 0)
            has_images = bool(images and len(images) > 0)

            if has_attachments:
                # 有附件时使用mixed结构
                message = MIMEMultipart('mixed')
            elif has_images:
                # 只有图片时使用related结构
                message = MIMEMultipart('related')
            else:
                # 普通邮件使用alternative结构
                message = MIMEMultipart('alternative')

            # 设置邮件基本信息
            message["To"] = to_email
            message["From"] = self.sender_email
            message["Subject"] = subject

            # 创建邮件内容部分
            if has_images:
                # 有图片时需要related容器
                related_container = MIMEMultipart('related')

                if html_content:
                    # 创建alternative容器包含文本和HTML
                    alt_container = MIMEMultipart('alternative')
                    alt_container.attach(MIMEText(content, 'plain', 'utf-8'))
                    alt_container.attach(MIMEText(html_content, 'html', 'utf-8'))
                    related_container.attach(alt_container)
                else:
                    related_container.attach(MIMEText(content, 'plain', 'utf-8'))

                # 添加图片
                self._attach_images_to_message(related_container, images)

                if has_attachments:
                    message.attach(related_container)
                else:
                    message = related_container
            else:
                # 没有图片，只处理文本内容
                if html_content and not has_attachments:
                    # 没有附件的HTML邮件
                    message.attach(MIMEText(content, 'plain', 'utf-8'))
                    message.attach(MIMEText(html_content, 'html', 'utf-8'))
                elif html_content and has_attachments:
                    # 有附件的HTML邮件
                    alt_container = MIMEMultipart('alternative')
                    alt_container.attach(MIMEText(content, 'plain', 'utf-8'))
                    alt_container.attach(MIMEText(html_content, 'html', 'utf-8'))
                    message.attach(alt_container)
                else:
                    # 纯文本邮件
                    text_part = MIMEText(content, 'plain', 'utf-8')
                    if has_attachments:
                        message.attach(text_part)
                    else:
                        message = text_part

            # 添加文件附件
            if has_attachments:
                self._attach_files_to_message(message, attachments)

            self.logger.debug(f"包含附件的邮件消息创建成功: {to_email}")
            return message

        except Exception as e:
            self.logger.error(f"创建包含附件的邮件消息失败: {e}")
            return None

    def send_email_with_attachments(
        self,
        to_email: str,
        subject: str,
        content: str,
        html_content: Optional[str] = None,
        images: Optional[Dict[str, Dict[str, Any]]] = None,
        attachments: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        发送包含附件的邮件

        Args:
            to_email: 收件人邮箱
            subject: 邮件主题
            content: 邮件文本内容
            html_content: 邮件HTML内容（可选）
            images: 图片信息字典（可选）
            attachments: 附件文件ID列表（可选）

        Returns:
            发送结果字典
        """
        try:
            # 如果没有附件，使用原有方法
            if not attachments:
                if images:
                    return self.send_email_with_images(to_email, subject, content, html_content, images)
                else:
                    return self.send_email(to_email, subject, content, html_content)

            # 验证附件
            attachment_validation = self.attachment_manager.validate_attachment_list(attachments)
            if not attachment_validation["valid"]:
                error_msg = "附件验证失败: "
                if attachment_validation.get("size_error"):
                    error_msg += attachment_validation["size_error"]
                else:
                    invalid_files = [f["file_id"] for f in attachment_validation["invalid_files"]]
                    error_msg += f"无效文件: {', '.join(invalid_files)}"

                return {
                    "success": False,
                    "error": error_msg,
                    "to_email": to_email
                }

            # 创建包含附件的邮件消息
            message = self.create_email_message_with_attachments(
                to_email, subject, content, html_content, images, attachments
            )

            if not message:
                return {
                    "success": False,
                    "error": "创建包含附件的邮件消息失败",
                    "to_email": to_email
                }

            # 编码邮件消息
            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            create_message = {"raw": encoded_message}

            # 发送邮件
            result = (
                self.gmail_service.users()
                .messages()
                .send(userId="me", body=create_message)
                .execute()
            )

            message_id = result.get("id", "")
            self.logger.info(f"包含附件的邮件发送成功: {to_email}, Message ID: {message_id}")

            return {
                "success": True,
                "message_id": message_id,
                "to_email": to_email,
                "subject": subject,
                "attachment_count": len(attachments),
                "image_count": len(images) if images else 0
            }

        except Exception as e:
            error_msg = f"发送包含附件的邮件失败: {e}"
            self.logger.error(f"{error_msg} - {to_email}")

            return {
                "success": False,
                "error": error_msg,
                "to_email": to_email,
                "subject": subject
            }