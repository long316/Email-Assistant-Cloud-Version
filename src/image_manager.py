"""
图片文件管理模块
负责管理files/pics目录下的图片文件，包括验证、加载和编码
"""
import os
import base64
import logging
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

class ImageManager:
    """图片文件管理器"""

    # 支持的图片格式
    SUPPORTED_FORMATS = {
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'
    }

    # Gmail附件大小限制 (25MB)
    MAX_FILE_SIZE = 25 * 1024 * 1024

    def __init__(self, pics_dir: str = "files/pics"):
        """
        初始化图片管理器

        Args:
            pics_dir: 图片文件目录路径
        """
        self.pics_dir = Path(pics_dir)
        self.logger = logging.getLogger(__name__)

        # 确保图片目录存在
        self.pics_dir.mkdir(parents=True, exist_ok=True)

        # 图片缓存，避免重复读取和编码
        self._image_cache = {}

    def is_supported_format(self, file_path: Path) -> bool:
        """
        检查文件是否为支持的图片格式

        Args:
            file_path: 文件路径

        Returns:
            是否支持该格式
        """
        return file_path.suffix.lower() in self.SUPPORTED_FORMATS

    def validate_image_file(self, image_id: str) -> Dict[str, Any]:
        """
        验证图片文件是否存在且有效

        Args:
            image_id: 图片ID（文件名，不含扩展名）

        Returns:
            验证结果字典
        """
        result = {
            "valid": False,
            "file_path": None,
            "error": None,
            "size": 0,
            "mime_type": None
        }

        try:
            # 查找匹配的图片文件
            matching_files = []
            for ext in self.SUPPORTED_FORMATS:
                file_path = self.pics_dir / f"{image_id}{ext}"
                if file_path.exists():
                    matching_files.append(file_path)

            if not matching_files:
                result["error"] = f"图片文件不存在: {image_id}"
                return result

            if len(matching_files) > 1:
                result["error"] = f"发现多个同名图片文件: {image_id}"
                return result

            file_path = matching_files[0]

            # 检查文件大小
            file_size = file_path.stat().st_size
            if file_size > self.MAX_FILE_SIZE:
                result["error"] = f"图片文件过大: {image_id} ({file_size / 1024 / 1024:.2f}MB > 25MB)"
                return result

            # 获取MIME类型
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if not mime_type or not mime_type.startswith('image/'):
                result["error"] = f"无法识别图片文件类型: {image_id}"
                return result

            result.update({
                "valid": True,
                "file_path": file_path,
                "size": file_size,
                "mime_type": mime_type
            })

            self.logger.debug(f"图片文件验证成功: {image_id}")

        except Exception as e:
            result["error"] = f"验证图片文件时出错: {image_id} - {e}"
            self.logger.error(result["error"])

        return result

    def load_image_data(self, image_id: str) -> Dict[str, Any]:
        """
        加载图片文件数据

        Args:
            image_id: 图片ID

        Returns:
            图片数据字典，包含base64编码的内容
        """
        # 检查缓存
        if image_id in self._image_cache:
            self.logger.debug(f"从缓存加载图片: {image_id}")
            return self._image_cache[image_id]

        result = {
            "success": False,
            "image_id": image_id,
            "base64_data": None,
            "mime_type": None,
            "size": 0,
            "error": None
        }

        try:
            # 验证文件
            validation = self.validate_image_file(image_id)
            if not validation["valid"]:
                result["error"] = validation["error"]
                return result

            file_path = validation["file_path"]

            # 读取文件并编码
            with open(file_path, 'rb') as image_file:
                image_data = image_file.read()
                base64_data = base64.b64encode(image_data).decode('utf-8')

            result.update({
                "success": True,
                "base64_data": base64_data,
                "mime_type": validation["mime_type"],
                "size": validation["size"]
            })

            # 缓存结果
            self._image_cache[image_id] = result
            self.logger.info(f"图片加载成功: {image_id} ({validation['size']} bytes)")

        except Exception as e:
            result["error"] = f"加载图片文件失败: {image_id} - {e}"
            self.logger.error(result["error"])

        return result

    def get_available_images(self) -> List[str]:
        """
        获取所有可用的图片ID列表

        Returns:
            图片ID列表
        """
        available_images = []

        try:
            if not self.pics_dir.exists():
                return available_images

            for file_path in self.pics_dir.iterdir():
                if file_path.is_file() and self.is_supported_format(file_path):
                    image_id = file_path.stem  # 文件名不含扩展名
                    if image_id not in available_images:
                        available_images.append(image_id)

            available_images.sort()
            self.logger.debug(f"发现 {len(available_images)} 个可用图片")

        except Exception as e:
            self.logger.error(f"扫描图片目录失败: {e}")

        return available_images

    def clear_cache(self):
        """清空图片缓存"""
        self._image_cache.clear()
        self.logger.debug("图片缓存已清空")

    def get_cache_info(self) -> Dict[str, Any]:
        """
        获取缓存信息

        Returns:
            缓存统计信息
        """
        cache_size = sum(
            len(data.get("base64_data", ""))
            for data in self._image_cache.values()
            if data.get("success", False)
        )

        return {
            "cached_images": len(self._image_cache),
            "cache_size_bytes": cache_size,
            "cache_size_mb": cache_size / 1024 / 1024
        }