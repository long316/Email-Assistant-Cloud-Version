"""
邮件发送调度器
负责按照时间间隔和计划发送邮件，包含智能重试和状态管理
"""
import time
import random
import logging
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable
from enum import Enum

from src.gmail_auth import GmailAuthManager
from src.email_sender import EmailSender
from src.excel_processor import ExcelProcessor
import pandas as pd

class SchedulerStatus(Enum):
    """调度器状态枚举"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"

class EmailScheduler:
    """邮件发送调度器"""

    def __init__(
        self,
        gmail_auth_manager: GmailAuthManager,
        excel_processor: ExcelProcessor,
        min_interval: int = 20,
        max_interval: int = 90
    ):
        """
        初始化邮件调度器

        Args:
            gmail_auth_manager: Gmail认证管理器
            excel_processor: Excel处理器
            min_interval: 最小发送间隔（秒）
            max_interval: 最大发送间隔（秒）
        """
        self.gmail_auth_manager = gmail_auth_manager
        self.excel_processor = excel_processor
        self.min_interval = min_interval
        self.max_interval = max_interval
        self.logger = logging.getLogger(__name__)

        # 调度器状态
        self.status = SchedulerStatus.IDLE
        self.current_task = None
        self.start_time = None
        self.pause_time = None

        # 统计信息
        self.stats = {
            "total_emails": 0,
            "success_count": 0,
            "failure_count": 0,
            "remaining": 0,
            "current_email": "",
            "estimated_completion": None
        }

        # 回调函数
        self.progress_callback: Optional[Callable] = None
        self.completion_callback: Optional[Callable] = None

        # 停止标志
        self._stop_flag = threading.Event()
        self._pause_flag = threading.Event()

    def _reset_status(self):
        """重置调度器状态和统计信息"""
        self.status = SchedulerStatus.IDLE
        self.start_time = None
        self.pause_time = None
        self.current_task = None
        self._stop_flag.clear()
        self._pause_flag.clear()

        # 重置统计信息为新格式
        self.stats.update({
            "total_emails": 0,
            "success_count": 0,
            "failure_count": 0,
            "remaining": 0,
            "current_email": "",
            "estimated_completion": None
        })

    def set_progress_callback(self, callback: Callable):
        """设置进度回调函数"""
        self.progress_callback = callback

    def set_completion_callback(self, callback: Callable):
        """设置完成回调函数"""
        self.completion_callback = callback

    def calculate_wait_time(self) -> int:
        """
        计算下次发送的等待时间

        Returns:
            等待时间（秒）
        """
        return random.randint(self.min_interval, self.max_interval)

    def estimate_completion_time(self, remaining_count: int) -> datetime:
        """
        估算完成时间

        Args:
            remaining_count: 剩余邮件数量

        Returns:
            预计完成时间
        """
        avg_interval = (self.min_interval + self.max_interval) / 2
        estimated_seconds = remaining_count * avg_interval
        return datetime.now() + timedelta(seconds=estimated_seconds)

    def update_stats(self, total: int, success: int, failed: int, remaining: int, current_email: str = ""):
        """更新统计信息"""
        self.stats.update({
            "total_emails": total,
            "success_count": success,
            "failure_count": failed,
            "remaining": remaining,
            "current_email": current_email,
            "estimated_completion": self.estimate_completion_time(remaining) if remaining > 0 else None
        })

        # 调用进度回调
        if self.progress_callback:
            self.progress_callback(self.stats.copy())

    def send_scheduled_emails(
        self,
        sender_email: str,
        excel_file_path: str,
        subject: str,
        content: str,
        html_content: Optional[str] = None,
        start_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        发送计划邮件

        Args:
            sender_email: 发件人邮箱
            excel_file_path: Excel文件路径
            subject: 邮件主题
            content: 邮件内容
            html_content: HTML内容（可选）
            start_time: 开始发送时间（可选，默认为当前时间）

        Returns:
            执行结果
        """
        try:
            # 设置默认开始时间为当前时刻
            if start_time is None:
                start_time = datetime.now()
                self.logger.info(f"未指定开始时间，使用当前时间: {start_time}")

            self.status = SchedulerStatus.RUNNING
            self.start_time = datetime.now()
            self._stop_flag.clear()
            self._pause_flag.clear()

            # 获取Gmail服务
            gmail_service = self.gmail_auth_manager.get_gmail_service(sender_email)
            if not gmail_service:
                self.status = SchedulerStatus.ERROR
                return {"success": False, "error": "Gmail服务初始化失败"}

            # 创建邮件发送器
            email_sender = EmailSender(gmail_service, sender_email)

            # 获取待发送邮箱列表
            email_list = self.excel_processor.get_pending_emails(excel_file_path)
            if not email_list:
                self.status = SchedulerStatus.IDLE
                return {"success": True, "message": "没有待发送的邮箱"}

            total_count = len(email_list)
            success_count = 0
            failed_count = 0

            self.logger.info(f"开始发送邮件，总数: {total_count}")

            # 等待到指定开始时间
            if start_time and start_time > datetime.now():
                wait_seconds = (start_time - datetime.now()).total_seconds()
                self.logger.info(f"等待到指定开始时间: {start_time}")

                if self._wait_with_interruption(wait_seconds):
                    self.status = SchedulerStatus.STOPPED
                    return {"success": False, "message": "任务已停止"}

            # 逐个发送邮件
            for i, email in enumerate(email_list):
                # 检查停止标志
                if self._stop_flag.is_set():
                    self.logger.info("收到停止信号，中止发送")
                    break

                # 检查暂停标志
                while self._pause_flag.is_set() and not self._stop_flag.is_set():
                    time.sleep(0.1)

                # 更新当前邮箱统计
                remaining = total_count - i
                self.update_stats(total_count, success_count, failed_count, remaining, email)

                self.logger.info(f"正在发送邮件 {i + 1}/{total_count}: {email}")

                # 发送邮件
                result = email_sender.send_email(email, subject, content, html_content)

                # 更新Excel状态
                status = 1 if result["success"] else -1
                self.excel_processor.update_email_status(excel_file_path, email, status)

                # 更新计数
                if result["success"]:
                    success_count += 1
                    self.logger.info(f"邮件发送成功: {email}")
                else:
                    failed_count += 1
                    self.logger.error(f"邮件发送失败: {email}, 错误: {result.get('error', '未知错误')}")

                # 如果不是最后一封邮件，等待随机间隔
                if i < len(email_list) - 1:
                    wait_time = self.calculate_wait_time()
                    self.logger.info(f"等待 {wait_time} 秒后发送下一封邮件")

                    if self._wait_with_interruption(wait_time):
                        self.logger.info("收到停止信号，中止发送")
                        break

            # 最终统计
            remaining = total_count - success_count - failed_count
            self.update_stats(total_count, success_count, failed_count, remaining)

            self.status = SchedulerStatus.IDLE
            end_time = datetime.now()
            duration = end_time - self.start_time

            result = {
                "success": True,
                "total": total_count,
                "success_count": success_count,
                "failed_count": failed_count,
                "duration": str(duration),
                "start_time": self.start_time.isoformat(),
                "end_time": end_time.isoformat()
            }

            self.logger.info(f"邮件发送完成: {result}")

            # 调用完成回调
            if self.completion_callback:
                self.completion_callback(result)

            return result

        except Exception as e:
            self.status = SchedulerStatus.ERROR
            error_msg = f"邮件发送调度失败: {e}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}

    def _wait_with_interruption(self, seconds: float) -> bool:
        """
        可中断的等待

        Args:
            seconds: 等待秒数

        Returns:
            是否被中断（True表示被中断）
        """
        end_time = time.time() + seconds
        while time.time() < end_time:
            if self._stop_flag.is_set():
                return True

            # 检查暂停
            while self._pause_flag.is_set() and not self._stop_flag.is_set():
                time.sleep(0.1)

            time.sleep(0.1)

        return False

    def pause(self):
        """暂停发送"""
        if self.status == SchedulerStatus.RUNNING:
            self._pause_flag.set()
            self.status = SchedulerStatus.PAUSED
            self.pause_time = datetime.now()
            self.logger.info("邮件发送已暂停")

    def resume(self):
        """恢复发送"""
        if self.status == SchedulerStatus.PAUSED:
            self._pause_flag.clear()
            self.status = SchedulerStatus.RUNNING
            self.logger.info("邮件发送已恢复")

    def stop(self):
        """停止发送"""
        self._stop_flag.set()
        self._pause_flag.clear()
        self.status = SchedulerStatus.STOPPED
        self.logger.info("邮件发送已停止")

    def get_status(self) -> Dict[str, Any]:
        """
        获取调度器状态

        Returns:
            状态信息字典
        """
        status_info = {
            "status": self.status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "pause_time": self.pause_time.isoformat() if self.pause_time else None,
            "stats": self.stats.copy()
        }

        if self.start_time:
            status_info["running_duration"] = str(datetime.now() - self.start_time)

        return status_info

    def run_in_background(
        self,
        sender_email: str,
        excel_file_path: str,
        subject: str,
        content: str,
        html_content: Optional[str] = None,
        start_time: Optional[datetime] = None
    ) -> threading.Thread:
        """
        在后台线程中运行邮件发送

        Args:
            sender_email: 发件人邮箱
            excel_file_path: Excel文件路径
            subject: 邮件主题
            content: 邮件内容
            html_content: HTML内容（可选）
            start_time: 开始发送时间（可选）

        Returns:
            后台线程对象
        """
        def run_task():
            self.current_task = self.send_scheduled_emails(
                sender_email, excel_file_path, subject, content, html_content, start_time
            )

        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()
        self.logger.info("邮件发送任务已在后台启动")
        return thread

    def send_template_emails_scheduled(
        self,
        email_sender: EmailSender,
        filtered_data: pd.DataFrame,
        excel_file_path: str,
        attachments: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        min_interval: Optional[int] = None,
        max_interval: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        基于模板的计划邮件发送

        Args:
            email_sender: 邮件发送器
            filtered_data: 过滤后的数据DataFrame
            excel_file_path: Excel文件路径
            attachments: 附件文件列表
            start_time: 开始时间（可选，默认为当前时间）
            min_interval: 最小间隔
            max_interval: 最大间隔

        Returns:
            发送结果字典
        """
        try:
            # 设置默认开始时间为当前时刻
            if start_time is None:
                start_time = datetime.now()
                self.logger.info(f"未指定开始时间，使用当前时间: {start_time}")
            # 设置间隔
            if min_interval is not None:
                self.min_interval = min_interval
            if max_interval is not None:
                self.max_interval = max_interval

            # 重置状态
            self._reset_status()
            self.stats["total_emails"] = len(filtered_data)

            # 等待开始时间
            if start_time and start_time > datetime.now():
                self.logger.info(f"等待开始时间: {start_time}")
                wait_seconds = (start_time - datetime.now()).total_seconds()
                if self._wait_with_interruption(wait_seconds):
                    return {"success": False, "error": "发送任务被用户停止"}

            # 开始发送
            self.status = SchedulerStatus.RUNNING
            self.start_time = datetime.now()
            self.logger.info(f"开始基于模板的邮件发送，总数: {len(filtered_data)}")

            # 发送邮件并更新状态
            for index, (_, row) in enumerate(filtered_data.iterrows()):
                # 检查停止标志
                if self._stop_flag.is_set():
                    self.status = SchedulerStatus.STOPPED
                    break

                # 检查暂停标志
                while self._pause_flag.is_set() and not self._stop_flag.is_set():
                    time.sleep(0.1)

                to_email = row["邮箱"]
                language = row.get("语言", "English")
                row_data = row.to_dict()

                self.logger.info(f"发送邮件 ({index + 1}/{len(filtered_data)}): {to_email} [{language}]")

                try:
                    # 发送邮件
                    result = email_sender.send_email_from_template(to_email, language, row_data, attachments)

                    # 更新Excel状态
                    status = 1 if result["success"] else -1
                    self.excel_processor.update_email_status(excel_file_path, to_email, status)

                    # 更新统计
                    if result["success"]:
                        self.stats["success_count"] += 1
                        self.logger.info(f"邮件发送成功: {to_email}")
                    else:
                        self.stats["failure_count"] += 1
                        self.logger.error(f"邮件发送失败: {to_email}, 错误: {result.get('error', '未知错误')}")

                    # 回调通知
                    if self.progress_callback:
                        self.progress_callback({
                            "current": index + 1,
                            "total": len(filtered_data),
                            "email": to_email,
                            "language": language,
                            "success": result["success"],
                            "error": result.get("error")
                        })

                except Exception as e:
                    self.stats["failure_count"] += 1
                    error_msg = f"处理邮件失败: {to_email}, {e}"
                    self.logger.error(error_msg)

                    # 更新Excel状态为失败
                    self.excel_processor.update_email_status(excel_file_path, to_email, -1)

                # 等待间隔（除了最后一个邮件）
                if index < len(filtered_data) - 1:
                    interval = random.randint(self.min_interval, self.max_interval)
                    self.logger.info(f"等待 {interval} 秒...")

                    if self._wait_with_interruption(interval):
                        self.status = SchedulerStatus.STOPPED
                        break

            # 完成发送
            if self.status != SchedulerStatus.STOPPED:
                self.status = SchedulerStatus.IDLE

            end_time = datetime.now()
            duration = end_time - self.start_time
            self.logger.info(
                f"模板邮件发送完成: 成功 {self.stats['success_count']}, "
                f"失败 {self.stats['failure_count']}, 耗时 {duration}"
            )

            return {
                "success": True,
                "stats": self.stats.copy(),
                "duration": str(duration),
                "status": self.status.value
            }

        except Exception as e:
            error_msg = f"模板邮件发送过程中出现错误: {e}"
            self.logger.error(error_msg)
            self.status = SchedulerStatus.ERROR
            return {"success": False, "error": error_msg}