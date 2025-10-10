"""
文件附件管理模块
负责管理files目录下的文件附件，包括验证、加载和编码
"""
import os
import base64
import logging
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Any, List

class AttachmentManager:
    """文件附件管理器"""

    # Gmail附件大小限制 (25MB)
    MAX_FILE_SIZE = 25 * 1024 * 1024

    # 支持的文件类型及对应MIME类型
    SUPPORTED_MIME_TYPES = {
        # 文档类型
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xls': 'application/vnd.ms-excel',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.ppt': 'application/vnd.ms-powerpoint',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',

        # 文本类型
        '.txt': 'text/plain',
        '.csv': 'text/csv',
        '.rtf': 'application/rtf',

        # 压缩文件
        '.zip': 'application/zip',
        '.rar': 'application/x-rar-compressed',
        '.7z': 'application/x-7z-compressed',

        # 其他常用类型
        '.json': 'application/json',
        '.xml': 'application/xml'
    }

    def __init__(self, files_dir: str = "files"):
        """
        初始化附件管理器

        Args:
            files_dir: 文件目录路径
        """
        self.files_dir = Path(files_dir)
        self.logger = logging.getLogger(__name__)

        # 确保文件目录存在
        self.files_dir.mkdir(parents=True, exist_ok=True)

        # 文件缓存，避免重复读取和编码
        self._file_cache = {}

    def is_supported_file(self, file_path: Path) -> bool:
        """
        检查文件是否为支持的类型

        Args:
            file_path: 文件路径

        Returns:
            是否支持该文件类型
        """
        return file_path.suffix.lower() in self.SUPPORTED_MIME_TYPES

    def get_mime_type(self, file_path: Path) -> str:
        """
        获取文件的MIME类型

        Args:
            file_path: 文件路径

        Returns:
            MIME类型字符串
        """
        ext = file_path.suffix.lower()

        # 首先从预定义列表中查找
        if ext in self.SUPPORTED_MIME_TYPES:
            return self.SUPPORTED_MIME_TYPES[ext]

        # 使用系统默认方法
        mime_type, _ = mimetypes.guess_type(str(file_path))
        return mime_type or 'application/octet-stream'

    def validate_attachment_file(self, file_id: str) -> Dict[str, Any]:
        """
        验证附件文件是否存在且有效

        Args:
            file_id: 文件ID（文件名，可含扩展名）

        Returns:
            验证结果字典
        """
        result = {
            "valid": False,
            "file_path": None,
            "error": None,
            "size": 0,
            "mime_type": None,
            "filename": None
        }

        try:
            # 首先尝试直接匹配（包含扩展名）
            direct_path = self.files_dir / file_id
            matching_files = []

            if direct_path.exists() and direct_path.is_file():
                matching_files.append(direct_path)
            else:
                # 如果没有扩展名，搜索匹配的文件
                if '.' not in file_id:
                    for file_path in self.files_dir.glob(f"{file_id}.*"):
                        if file_path.is_file() and self.is_supported_file(file_path):
                            matching_files.append(file_path)

            if not matching_files:
                result["error"] = f"附件文件不存在: {file_id}"
                return result

            if len(matching_files) > 1:
                result["error"] = f"发现多个同名附件文件: {file_id}"
                return result

            file_path = matching_files[0]

            # 检查文件大小
            file_size = file_path.stat().st_size
            if file_size > self.MAX_FILE_SIZE:
                result["error"] = f"附件文件过大: {file_id} ({file_size / 1024 / 1024:.2f}MB > 25MB)"
                return result

            # 检查文件类型
            if not self.is_supported_file(file_path):
                result["error"] = f"不支持的附件文件类型: {file_id} ({file_path.suffix})"
                return result

            # 获取MIME类型
            mime_type = self.get_mime_type(file_path)

            result.update({
                "valid": True,
                "file_path": file_path,
                "size": file_size,
                "mime_type": mime_type,
                "filename": file_path.name
            })

            self.logger.debug(f"附件文件验证成功: {file_id}")

        except Exception as e:
            result["error"] = f"验证附件文件时出错: {file_id} - {e}"
            self.logger.error(result["error"])

        return result

    def load_attachment_data(self, file_id: str) -> Dict[str, Any]:
        """
        加载附件文件数据

        Args:
            file_id: 文件ID

        Returns:
            附件数据字典，包含base64编码的内容
        """
        # 检查缓存
        if file_id in self._file_cache:
            self.logger.debug(f"从缓存加载附件: {file_id}")
            return self._file_cache[file_id]

        result = {
            "success": False,
            "file_id": file_id,
            "base64_data": None,
            "mime_type": None,
            "filename": None,
            "size": 0,
            "error": None
        }

        try:
            # 验证文件
            validation = self.validate_attachment_file(file_id)
            if not validation["valid"]:
                result["error"] = validation["error"]
                return result

            file_path = validation["file_path"]

            # 读取文件并编码
            with open(file_path, 'rb') as file:
                file_data = file.read()
                base64_data = base64.b64encode(file_data).decode('utf-8')

            result.update({
                "success": True,
                "base64_data": base64_data,
                "mime_type": validation["mime_type"],
                "filename": validation["filename"],
                "size": validation["size"]
            })

            # 缓存结果
            self._file_cache[file_id] = result
            self.logger.info(f"附件加载成功: {file_id} ({validation['size']} bytes)")

        except Exception as e:
            result["error"] = f"加载附件文件失败: {file_id} - {e}"
            self.logger.error(result["error"])

        return result

    def get_available_files(self) -> List[str]:
        """
        获取所有可用的文件列表

        Returns:
            文件名列表
        """
        available_files = []

        try:
            if not self.files_dir.exists():
                return available_files

            for file_path in self.files_dir.iterdir():
                if file_path.is_file() and self.is_supported_file(file_path):
                    # 跳过pics目录下的图片文件
                    if file_path.parent.name != 'pics':
                        available_files.append(file_path.name)

            available_files.sort()
            self.logger.debug(f"发现 {len(available_files)} 个可用附件文件")

        except Exception as e:
            self.logger.error(f"扫描附件目录失败: {e}")

        return available_files

    def validate_attachment_list(self, attachment_list: List[str]) -> Dict[str, Any]:
        """
        验证附件文件列表

        Args:
            attachment_list: 附件文件ID列表

        Returns:
            验证结果字典
        """
        result = {
            "valid": True,
            "total_files": len(attachment_list),
            "valid_files": 0,
            "invalid_files": [],
            "total_size": 0,
            "files": {}
        }

        if not attachment_list:
            return result

        for file_id in attachment_list:
            validation = self.validate_attachment_file(file_id)
            result["files"][file_id] = validation

            if validation["valid"]:
                result["valid_files"] += 1
                result["total_size"] += validation["size"]
            else:
                result["invalid_files"].append({
                    "file_id": file_id,
                    "error": validation["error"]
                })

        # 如果有无效文件，整体验证失败
        if result["invalid_files"]:
            result["valid"] = False

        # 检查总大小
        if result["total_size"] > self.MAX_FILE_SIZE:
            result["valid"] = False
            result["size_error"] = f"附件总大小超限: {result['total_size'] / 1024 / 1024:.2f}MB > 25MB"

        return result

    def clear_cache(self):
        """清空文件缓存"""
        self._file_cache.clear()
        self.logger.debug("附件缓存已清空")

    def get_cache_info(self) -> Dict[str, Any]:
        """
        获取缓存信息

        Returns:
            缓存统计信息
        """
        cache_size = sum(
            len(data.get("base64_data", ""))
            for data in self._file_cache.values()
            if data.get("success", False)
        )

        return {
            "cached_files": len(self._file_cache),
            "cache_size_bytes": cache_size,
            "cache_size_mb": cache_size / 1024 / 1024
        }