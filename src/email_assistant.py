"""
邮件助手主模块
提供命令行和API接口
"""
import os
import logging
import argparse
from datetime import datetime
from typing import Optional, Dict, Any, List

from src.gmail_auth import GmailAuthManager
from src.email_sender import EmailSender
from src.excel_processor import ExcelProcessor
from src.email_scheduler import EmailScheduler

class EmailAssistant:
    """邮件助手主类"""

    def __init__(self, credentials_file: str = "credentials.json"):
        """
        初始化邮件助手

        Args:
            credentials_file: Google OAuth凭据文件路径
        """
        self.gmail_auth_manager = GmailAuthManager(credentials_file)
        self.excel_processor = ExcelProcessor()
        self.scheduler = EmailScheduler(self.gmail_auth_manager, self.excel_processor)

        # 配置日志
        self._setup_logging()
        self.logger = logging.getLogger(__name__)

    def _setup_logging(self):
        """配置日志系统"""
        # 确保logs目录存在
        os.makedirs("logs", exist_ok=True)

        # 配置日志格式
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        # 配置文件日志
        log_file = f"logs/email_assistant_{datetime.now().strftime('%Y%m%d')}.log"
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler(log_file, encoding="utf-8"),
                logging.StreamHandler()
            ]
        )

    def authenticate_sender(self, sender_email: str) -> bool:
        """
        认证发件人邮箱

        Args:
            sender_email: 发件人邮箱地址

        Returns:
            认证是否成功
        """
        try:
            # 直接尝试认证，让认证管理器处理token重用逻辑
            creds = self.gmail_auth_manager.authenticate(sender_email)
            if creds:
                self.logger.info(f"邮箱认证成功: {sender_email}")
                return True
            else:
                self.logger.error(f"邮箱认证失败: {sender_email}")
                return False

        except Exception as e:
            self.logger.error(f"认证过程出错: {e}")
            return False

    def validate_excel_file(self, excel_file_path: str) -> bool:
        """
        验证Excel文件

        Args:
            excel_file_path: Excel文件路径

        Returns:
            文件是否有效
        """
        if not os.path.exists(excel_file_path):
            self.logger.error(f"Excel文件不存在: {excel_file_path}")
            return False

        return self.excel_processor.validate_excel_file(excel_file_path)

    def preview_email_list(self, excel_file_path: str) -> Dict[str, Any]:
        """
        预览待发送邮箱列表

        Args:
            excel_file_path: Excel文件路径

        Returns:
            预览结果
        """
        try:
            email_list = self.excel_processor.get_pending_emails(excel_file_path)
            stats = self.excel_processor.get_statistics(excel_file_path)

            return {
                "success": True,
                "email_list": email_list,
                "statistics": stats
            }

        except Exception as e:
            self.logger.error(f"预览邮箱列表失败: {e}")
            return {"success": False, "error": str(e)}

    def send_emails(
        self,
        sender_email: str,
        excel_file_path: str,
        subject: Optional[str] = None,
        content: Optional[str] = None,
        html_content: Optional[str] = None,
        attachments: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        min_interval: int = 20,
        max_interval: int = 90
    ) -> Dict[str, Any]:
        """
        发送邮件

        Args:
            sender_email: 发件人邮箱
            excel_file_path: Excel文件路径
            subject: 邮件主题
            content: 邮件内容
            html_content: HTML内容
            start_time: 开始时间（可选，默认为当前时间）
            min_interval: 最小间隔
            max_interval: 最大间隔

        Returns:
            发送结果
        """
        try:
            # 检查发件人认证
            if not self.authenticate_sender(sender_email):
                return {"success": False, "error": "发件人邮箱认证失败"}

            # 验证Excel文件
            if not self.validate_excel_file(excel_file_path):
                return {"success": False, "error": "Excel文件验证失败"}

            # 获取默认邮件内容（如果未提供）
            if not subject or not content:
                gmail_service = self.gmail_auth_manager.get_gmail_service(sender_email)
                email_sender = EmailSender(gmail_service, sender_email)
                default_content = email_sender.get_default_email_content(sender_email)

                if not subject:
                    subject = default_content["subject"]
                if not content:
                    content = default_content["content"]

            # 设置调度器参数
            self.scheduler.min_interval = min_interval
            self.scheduler.max_interval = max_interval

            # 发送邮件
            result = self.scheduler.send_scheduled_emails(
                sender_email=sender_email,
                excel_file_path=excel_file_path,
                subject=subject,
                content=content,
                html_content=html_content,
                start_time=start_time
            )

            return result

        except Exception as e:
            self.logger.error(f"发送邮件失败: {e}")
            return {"success": False, "error": str(e)}

    def get_statistics(self, excel_file_path: str) -> Dict[str, Any]:
        """
        获取统计信息

        Args:
            excel_file_path: Excel文件路径

        Returns:
            统计信息
        """
        try:
            stats = self.excel_processor.get_statistics(excel_file_path)
            return {"success": True, "statistics": stats}
        except Exception as e:
            self.logger.error(f"获取统计信息失败: {e}")
            return {"success": False, "error": str(e)}

    def get_scheduler_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        return self.scheduler.get_status()

    def pause_sending(self):
        """暂停发送"""
        self.scheduler.pause()

    def resume_sending(self):
        """恢复发送"""
        self.scheduler.resume()

    def stop_sending(self):
        """停止发送"""
        self.scheduler.stop()

    def validate_templates(self, excel_file_path: str) -> Dict[str, Any]:
        """
        验证Excel文件与模板的兼容性

        Args:
            excel_file_path: Excel文件路径

        Returns:
            验证结果
        """
        try:
            validation_result = self.excel_processor.validate_templates_for_excel(excel_file_path)
            return {"success": True, "validation": validation_result}
        except Exception as e:
            self.logger.error(f"验证模板失败: {e}")
            return {"success": False, "error": str(e)}

    def preview_template_emails(self, excel_file_path: str, max_previews: int = 3) -> Dict[str, Any]:
        """
        预览基于模板的邮件内容

        Args:
            excel_file_path: Excel文件路径
            max_previews: 最大预览数量

        Returns:
            预览结果
        """
        try:
            # 获取过滤后的数据
            filtered_data = self.excel_processor.get_filtered_data_with_language(excel_file_path)
            if filtered_data.empty:
                return {"success": False, "error": "没有找到符合条件的邮箱数据"}

            # 预览前几个邮件
            previews = []
            for i, (_, row) in enumerate(filtered_data.head(max_previews).iterrows()):
                to_email = row["邮箱"]
                language = row.get("语言", "English")
                row_data = row.to_dict()

                # 创建临时的EmailSender来生成预览
                if hasattr(self, '_temp_email_sender'):
                    email_sender = self._temp_email_sender
                else:
                    # 使用虚拟的gmail_service进行预览
                    from src.email_sender import EmailSender
                    email_sender = EmailSender(None, "preview@example.com")

                preview_text = email_sender.preview_email_from_template(to_email, language, row_data)
                previews.append({
                    "index": i + 1,
                    "to_email": to_email,
                    "language": language,
                    "preview": preview_text
                })

            return {
                "success": True,
                "total_emails": len(filtered_data),
                "previews": previews,
                "statistics": {
                    "待发送数": len(filtered_data),
                    "预览数": len(previews),
                    "语言分布": filtered_data["语言"].value_counts().to_dict()
                }
            }

        except Exception as e:
            self.logger.error(f"预览模板邮件失败: {e}")
            return {"success": False, "error": str(e)}

    def send_template_emails(
        self,
        sender_email: str,
        excel_file_path: str,
        attachments: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        min_interval: int = 20,
        max_interval: int = 90
    ) -> Dict[str, Any]:
        """
        基于模板发送邮件

        Args:
            sender_email: 发件人邮箱
            excel_file_path: Excel文件路径
            attachments: 附件文件列表
            start_time: 开始时间（可选，默认为当前时间）
            min_interval: 最小间隔
            max_interval: 最大间隔

        Returns:
            发送结果
        """
        try:
            # 首先验证认证
            if not self.authenticate_sender(sender_email):
                return {"success": False, "error": "邮箱认证失败"}

            # 验证Excel文件
            if not self.validate_excel_file(excel_file_path):
                return {"success": False, "error": "Excel文件验证失败"}

            # 验证模板兼容性
            template_validation = self.validate_templates(excel_file_path)
            if not template_validation["success"]:
                return {"success": False, "error": f"模板验证失败: {template_validation['error']}"}

            if not template_validation["validation"]["overall_valid"]:
                return {"success": False, "error": "模板参数与Excel数据不兼容"}

            # 获取Gmail服务
            gmail_service = self.gmail_auth_manager.get_gmail_service(sender_email)
            if not gmail_service:
                return {"success": False, "error": "无法获取Gmail服务"}

            # 创建EmailSender
            email_sender = EmailSender(gmail_service, sender_email)

            # 获取过滤后的数据
            filtered_data = self.excel_processor.get_filtered_data_with_language(excel_file_path)
            if filtered_data.empty:
                return {"success": False, "error": "没有找到符合条件的邮箱数据"}

            # 使用调度器发送邮件
            return self.scheduler.send_template_emails_scheduled(
                email_sender=email_sender,
                filtered_data=filtered_data,
                excel_file_path=excel_file_path,
                attachments=attachments,
                start_time=start_time,
                min_interval=min_interval,
                max_interval=max_interval
            )

        except Exception as e:
            self.logger.error(f"发送模板邮件失败: {e}")
            return {"success": False, "error": str(e)}


def main():
    """命令行主函数"""
    parser = argparse.ArgumentParser(description="Gmail邮件助手")

    # 基本参数
    parser.add_argument("--sender", required=True, help="发件人邮箱地址")
    parser.add_argument("--excel", required=True, help="Excel文件路径")
    parser.add_argument("--credentials", default="credentials.json", help="Google OAuth凭据文件")

    # 邮件内容参数
    parser.add_argument("--subject", help="邮件主题")
    parser.add_argument("--content", help="邮件内容")
    parser.add_argument("--html-content", help="HTML邮件内容")

    # 调度参数
    parser.add_argument("--start-time", help="开始发送时间 (格式: YYYY-MM-DD HH:MM:SS)")
    parser.add_argument("--min-interval", type=int, default=20, help="最小发送间隔（秒）")
    parser.add_argument("--max-interval", type=int, default=90, help="最大发送间隔（秒）")

    # 操作参数
    parser.add_argument("--preview", action="store_true", help="仅预览待发送邮箱列表")
    parser.add_argument("--preview-templates", action="store_true", help="预览模板邮件内容")
    parser.add_argument("--stats", action="store_true", help="显示统计信息")

    # 模板参数
    parser.add_argument("--use-templates", action="store_true", help="使用模板发送邮件")

    # 附件参数
    parser.add_argument("--attachments", nargs="*", help="附件文件列表（多个文件用空格分隔）")

    args = parser.parse_args()

    # 处理附件参数
    attachments = args.attachments if args.attachments else []

    # 创建邮件助手实例
    assistant = EmailAssistant(args.credentials)

    try:
        if args.stats:
            # 显示统计信息
            result = assistant.get_statistics(args.excel)
            if result["success"]:
                print("统计信息:")
                for key, value in result["statistics"].items():
                    print(f"  {key}: {value}")
            else:
                print(f"获取统计信息失败: {result['error']}")
            return

        if args.preview_templates:
            # 预览模板邮件内容
            result = assistant.preview_template_emails(args.excel, max_previews=3)
            if result["success"]:
                print(f"总邮箱数: {result['total_emails']}")
                print(f"预览数量: {result['statistics']['预览数']}")
                print(f"语言分布: {result['statistics']['语言分布']}")

                for preview_data in result["previews"]:
                    print(f"\n=== 预览 {preview_data['index']}: {preview_data['to_email']} [{preview_data['language']}] ===")
                    print(preview_data["preview"])
            else:
                print(f"模板预览失败: {result['error']}")
            return

        if args.preview:
            # 预览邮箱列表
            result = assistant.preview_email_list(args.excel)
            if result["success"]:
                print(f"待发送邮箱数量: {len(result['email_list'])}")
                print("邮箱列表:")
                for i, email in enumerate(result["email_list"][:10], 1):
                    print(f"  {i}. {email}")
                if len(result["email_list"]) > 10:
                    print(f"  ... 还有 {len(result['email_list']) - 10} 个邮箱")

                print("\n统计信息:")
                for key, value in result["statistics"].items():
                    print(f"  {key}: {value}")
            else:
                print(f"预览失败: {result['error']}")
            return

        # 解析开始时间
        start_time = None
        if args.start_time:
            try:
                start_time = datetime.strptime(args.start_time, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                print("开始时间格式错误，请使用格式: YYYY-MM-DD HH:MM:SS")
                return
        else:
            # 未指定开始时间时使用当前时间
            start_time = datetime.now()
            print(f"未指定开始时间，将使用当前时间: {start_time}")

        # 发送邮件
        print(f"开始发送邮件...")
        print(f"发件人: {args.sender}")
        print(f"Excel文件: {args.excel}")
        print(f"发送间隔: {args.min_interval}-{args.max_interval}秒")
        if args.use_templates:
            print("使用模板模式发送")
        else:
            print("使用传统模式发送")
        if attachments:
            print(f"附件: {', '.join(attachments)}")
        if start_time:
            print(f"开始时间: {start_time}")

        if args.use_templates:
            # 使用模板发送
            result = assistant.send_template_emails(
                sender_email=args.sender,
                excel_file_path=args.excel,
                attachments=attachments,
                start_time=start_time,
                min_interval=args.min_interval,
                max_interval=args.max_interval
            )
        else:
            # 使用传统方式发送
            result = assistant.send_emails(
                sender_email=args.sender,
                excel_file_path=args.excel,
                subject=args.subject,
                content=args.content,
                html_content=args.html_content,
                attachments=attachments,
                start_time=start_time,
                min_interval=args.min_interval,
                max_interval=args.max_interval
            )

        if result["success"]:
            print("\n邮件发送完成!")
            # 从stats对象中获取统计信息
            stats = result.get('stats', {})
            print(f"总数: {stats.get('total_emails', 0)}")
            print(f"成功: {stats.get('success_count', 0)}")
            print(f"失败: {stats.get('failure_count', 0)}")
            print(f"耗时: {result.get('duration', '未知')}")
        else:
            print(f"邮件发送失败: {result['error']}")

    except KeyboardInterrupt:
        print("\n用户中断，正在停止...")
        assistant.stop_sending()
    except Exception as e:
        print(f"程序异常: {e}")


if __name__ == "__main__":
    main()