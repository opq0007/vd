"""
API 响应格式化工具

提供统一的 API 响应格式，方便调用方统一处理。
"""

from typing import Any, Optional
from utils.logger import Logger


class ResponseFormatter:
    """API 响应格式化工具类"""

    @staticmethod
    def success(data: Any = None, message: str = "操作成功") -> dict:
        """
        格式化成功响应

        Args:
            data: 响应数据（可以是任意类型）
            message: 成功消息

        Returns:
            dict: 统一格式的成功响应
        """
        return {
            "success": True,
            "message": message,
            "data": data if data is not None else {}
        }

    @staticmethod
    def error(message: str, error_code: Optional[str] = None, data: Any = None) -> dict:
        """
        格式化错误响应

        Args:
            message: 错误消息
            error_code: 错误代码（可选）
            data: 错误相关数据（可选）

        Returns:
            dict: 统一格式的错误响应
        """
        response = {
            "success": False,
            "message": message,
            "data": data if data is not None else {}
        }

        if error_code:
            response["error_code"] = error_code

        return response

    @staticmethod
    def wrap_exception(e: Exception, context: str = "") -> dict:
        """
        包装异常为错误响应

        Args:
            e: 异常对象
            context: 上下文信息（可选）

        Returns:
            dict: 统一格式的错误响应
        """
        error_message = str(e)
        if context:
            error_message = f"{context}: {error_message}"

        Logger.error(error_message)

        return ResponseFormatter.error(
            message=error_message,
            error_code=type(e).__name__
        )


# 创建全局实例
response_formatter = ResponseFormatter()