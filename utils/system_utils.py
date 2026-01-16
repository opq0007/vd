"""
系统工具类

提供系统级操作，如命令执行、FFmpeg检测等。
"""

import subprocess
import logging
from typing import List

from config import config

logger = logging.getLogger(__name__)


class SystemUtils:
    """系统工具类"""

    _ffmpeg_path = None

    @classmethod
    def run_cmd(cls, cmd: List[str], capture_output: bool = False, text: bool = True, encoding: str = None) -> str or dict:
        """
        执行命令并返回输出

        Args:
            cmd: 命令列表
            capture_output: 是否捕获输出（返回字典格式）
            text: 是否以文本模式返回
            encoding: 指定编码（默认根据系统自动选择）

        Returns:
            str or dict: 命令输出（字符串或字典格式）

        Raises:
            RuntimeError: 命令执行失败时抛出
        """
        import os
        if os.name == 'nt':  # Windows
            cmd = [str(c) for c in cmd]

        # 在 Windows 系统上使用 GBK 编码，在其他系统上使用 UTF-8
        if encoding is None:
            encoding = 'gbk' if os.name == 'nt' else 'utf-8'
        
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=text,
            encoding=encoding,
            shell=os.name == 'nt'
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"Command failed: {' '.join(cmd)}\n"
                f"stdout:\n{proc.stdout}\n"
                f"stderr:\n{proc.stderr}"
            )
        
        if capture_output:
            return {
                'stdout': proc.stdout,
                'stderr': proc.stderr,
                'returncode': proc.returncode
            }
        else:
            return proc.stdout

    @classmethod
    def check_ffmpeg_available(cls) -> bool:
        """
        检查ffmpeg是否可用

        Returns:
            bool: FFmpeg是否可用
        """
        if cls._ffmpeg_path:
            return True

        for ffmpeg_path in config.FFMPEG_PATHS:
            try:
                subprocess.run([ffmpeg_path, "-version"], capture_output=True, check=True)
                cls._ffmpeg_path = ffmpeg_path
                logger.info(f"Found ffmpeg at: {ffmpeg_path}")
                return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue

        logger.warning("FFmpeg not found in system PATH or configured paths")
        return False

    @classmethod
    def get_ffmpeg_path(cls) -> str:
        """
        获取ffmpeg路径

        Returns:
            str: FFmpeg可执行文件路径

        Raises:
            RuntimeError: FFmpeg不可用时抛出
        """
        if not cls.check_ffmpeg_available():
            raise RuntimeError(
                "FFmpeg 未安装或不在 PATH 中。请安装 FFmpeg: https://ffmpeg.org/download.html"
            )
        return cls._ffmpeg_path

    @classmethod
    def get_system_info(cls) -> dict:
        """
        获取系统信息

        Returns:
            dict: 包含系统信息的字典
        """
        import platform
        import psutil

        return {
            'platform': platform.system(),
            'platform_release': platform.release(),
            'platform_version': platform.version(),
            'architecture': platform.machine(),
            'processor': platform.processor(),
            'cpu_count': psutil.cpu_count(logical=True),
            'memory_total': psutil.virtual_memory().total,
            'memory_available': psutil.virtual_memory().available
        }

    @classmethod
    def check_disk_space(cls, path: str, required_mb: int = 100) -> bool:
        """
        检查磁盘空间是否足够

        Args:
            path: 检查的路径
            required_mb: 需要的空间（MB）

        Returns:
            bool: 磁盘空间是否足够
        """
        import shutil
        disk_usage = shutil.disk_usage(path)
        available_mb = disk_usage.free / (1024 * 1024)
        return available_mb >= required_mb
