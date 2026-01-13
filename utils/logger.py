"""
日志工具类

提供统一的日志记录接口。
"""

import logging
import os
from datetime import datetime
from pathlib import Path

from config import config


class Logger:
    """日志工具类"""

    _logger = None
    _initialized = False

    @classmethod
    def _initialize(cls):
        """初始化日志系统"""
        if cls._initialized:
            return

        # 创建日志目录
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        # 配置日志格式
        log_format = config.LOG_FORMAT
        date_format = '%Y-%m-%d %H:%M:%S'

        # 创建日志文件名
        log_file = log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"

        # 配置日志处理器
        handlers = [
            logging.StreamHandler(),  # 控制台输出
            logging.FileHandler(log_file, encoding='utf-8')  # 文件输出
        ]

        # 配置日志级别
        level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)

        # 配置日志系统
        logging.basicConfig(
            level=level,
            format=log_format,
            datefmt=date_format,
            handlers=handlers
        )

        cls._logger = logging.getLogger(__name__)
        cls._initialized = True

    @classmethod
    def get_logger(cls) -> logging.Logger:
        """获取日志记录器"""
        if not cls._initialized:
            cls._initialize()
        return cls._logger

    @classmethod
    def debug(cls, message: str):
        """记录调试信息"""
        cls.get_logger().debug(message)

    @classmethod
    def info(cls, message: str):
        """记录一般信息"""
        cls.get_logger().info(message)

    @classmethod
    def warning(cls, message: str):
        """记录警告信息"""
        cls.get_logger().warning(message)

    @classmethod
    def error(cls, message: str, exc_info=False):
        """记录错误信息"""
        cls.get_logger().error(message, exc_info=exc_info)

    @classmethod
    def critical(cls, message: str, exc_info=False):
        """记录严重错误信息"""
        cls.get_logger().critical(message, exc_info=exc_info)

    @classmethod
    def exception(cls, message: str):
        """记录异常信息（包含堆栈）"""
        cls.get_logger().exception(message)