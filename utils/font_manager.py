"""
字体管理工具类

提供字体文件管理和加载功能。
"""

import os
from pathlib import Path
from typing import List, Optional
from PIL import ImageFont

from utils.logger import Logger


class FontManager:
    """字体管理工具类"""

    _instance = None
    _fonts_dir = None
    _available_fonts = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self._fonts_dir = Path(__file__).parent.parent / "fonts"
            self._fonts_dir.mkdir(exist_ok=True)
            self._available_fonts = []
            self._scan_fonts()
            self.initialized = True

    @property
    def fonts_dir(self) -> Path:
        """获取字体目录"""
        return self._fonts_dir

    def _scan_fonts(self):
        """扫描字体目录中的所有字体文件"""
        self._available_fonts = []

        if not self._fonts_dir.exists():
            Logger.warning(f"字体目录不存在: {self._fonts_dir}")
            return

        # 支持的字体文件扩展名
        font_extensions = ['.ttf', '.ttc', '.otf', '.woff', '.woff2']

        for font_file in self._fonts_dir.iterdir():
            if font_file.suffix.lower() in font_extensions:
                self._available_fonts.append(font_file.name)

        if self._available_fonts:
            Logger.info(f"找到 {len(self._available_fonts)} 个字体文件: {self._available_fonts}")
        else:
            Logger.warning(f"字体目录中没有找到字体文件: {self._fonts_dir}")
            Logger.info("请将字体文件（.ttf, .ttc, .otf等）放入 fonts 目录")

    def get_available_fonts(self) -> List[str]:
        """
        获取可用的字体列表

        Returns:
            List[str]: 字体文件名列表
        """
        return self._available_fonts.copy()

    def get_font_path(self, font_name: str) -> Optional[Path]:
        """
        获取字体文件的完整路径

        Args:
            font_name: 字体文件名

        Returns:
            Optional[Path]: 字体文件路径，如果不存在则返回 None
        """
        font_path = self._fonts_dir / font_name
        if font_path.exists():
            return font_path
        return None

    def load_font(self, font_name: str, size: int) -> Optional[ImageFont.FreeTypeFont]:
        """
        加载字体

        Args:
            font_name: 字体文件名
            size: 字体大小

        Returns:
            Optional[ImageFont.FreeTypeFont]: 字体对象，如果加载失败则返回 None
        """
        font_path = self.get_font_path(font_name)

        if font_path is None:
            Logger.error(f"字体文件不存在: {font_name}")
            return None

        try:
            font = ImageFont.truetype(str(font_path), size)
            Logger.info(f"成功加载字体: {font_name} (大小: {size})")
            return font
        except Exception as e:
            Logger.error(f"加载字体失败: {font_name}, 错误: {e}")
            return None

    def add_font(self, font_path: str) -> bool:
        """
        添加字体文件到字体目录

        Args:
            font_path: 字体文件路径

        Returns:
            bool: 是否成功添加
        """
        try:
            source_path = Path(font_path)
            if not source_path.exists():
                Logger.error(f"字体文件不存在: {font_path}")
                return False

            # 检查是否是字体文件
            font_extensions = ['.ttf', '.ttc', '.otf', '.woff', '.woff2']
            if source_path.suffix.lower() not in font_extensions:
                Logger.error(f"不是有效的字体文件: {font_path}")
                return False

            # 复制到字体目录
            dest_path = self._fonts_dir / source_path.name
            import shutil
            shutil.copy2(source_path, dest_path)

            # 重新扫描字体
            self._scan_fonts()

            Logger.info(f"成功添加字体: {source_path.name}")
            return True
        except Exception as e:
            Logger.error(f"添加字体失败: {e}")
            return False

    def get_default_font(self) -> str:
        """
        获取默认字体

        Returns:
            str: 默认字体名称，如果没有可用字体则返回空字符串
        """
        if self._available_fonts:
            return self._available_fonts[0]
        return ""

    def refresh_fonts(self):
        """刷新字体列表"""
        self._scan_fonts()


# 创建全局字体管理器实例
font_manager = FontManager()