"""
API 路由模块

包含所有 API 路由定义和认证相关功能。
"""

from .auth import AuthService, verify_token, get_current_user
from .routes import register_routes

__all__ = [
    'AuthService',
    'verify_token',
    'get_current_user',
    'register_routes'
]