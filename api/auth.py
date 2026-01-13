"""
认证模块

提供 JWT token 验证和用户认证功能。
"""

import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config import config
from utils.logger import Logger


security = HTTPBearer()


class AuthService:
    """认证服务类"""

    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        创建访问令牌

        Args:
            data: 要编码的数据
            expires_delta: 过期时间增量

        Returns:
            str: JWT token
        """
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=24)

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm="HS256")
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """
        验证令牌

        Args:
            token: JWT token

        Returns:
            Dict[str, Any]: 解码后的数据

        Raises:
            HTTPException: 令牌无效时抛出
        """
        try:
            payload = jwt.decode(token, config.SECRET_KEY, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            Logger.warning("Token expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token已过期",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError:
            Logger.warning("Invalid token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @staticmethod
    def verify_fixed_token(token: str) -> bool:
        """
        验证固定令牌

        Args:
            token: 固定令牌

        Returns:
            bool: 令牌是否有效
        """
        return token in config.API_TOKENS

    @staticmethod
    def verify_user(username: str, password: str) -> bool:
        """
        验证用户凭据

        Args:
            username: 用户名
            password: 密码

        Returns:
            bool: 凭据是否有效
        """
        import hashlib

        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        return config.USERS.get(username) == hashed_password


async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> Dict[str, Any]:
    """
    验证令牌的依赖函数

    Args:
        credentials: HTTP 认证凭据

    Returns:
        Dict[str, Any]: 解码后的数据

    Raises:
        HTTPException: 令牌无效时抛出
    """
    token = credentials.credentials

    # 检查是否为固定令牌
    if AuthService.verify_fixed_token(token):
        return {"type": "fixed", "token": token}

    # 验证 JWT 令牌
    payload = AuthService.verify_token(token)
    return payload


async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> Dict[str, Any]:
    """
    获取当前用户的依赖函数

    Args:
        credentials: HTTP 认证凭据

    Returns:
        Dict[str, Any]: 用户信息

    Raises:
        HTTPException: 令牌无效时抛出
    """
    token = credentials.credentials

    # 检查是否为固定令牌
    if AuthService.verify_fixed_token(token):
        return {
            "username": "automation",
            "type": "fixed",
            "token": token
        }

    # 验证 JWT 令牌
    payload = AuthService.verify_token(token)
    username = payload.get("sub")

    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "username": username,
        "type": "jwt",
        "payload": payload
    }


# 创建全局服务实例
auth_service = AuthService()