"""
认证模块

提供 JWT token 验证和用户认证功能。
"""

import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import hashlib
import secrets

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config import config
from utils.logger import Logger


security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)  # 新增：用于可选的token验证


class AuthService:
    """认证服务类"""

    # 会话存储：{session_id: {"username": str, "expire_time": datetime}}
    _sessions: Dict[str, Dict[str, Any]] = {}

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
        return token == config.API_TOKEN

    @staticmethod
    def verify_user(username: str, password: str) -> bool:
        """
        验证用户凭据

        Args:
            username: 用户名
            password: 密码

        Returns:
            bool: 凭据是否有效

        注意：
        - 只支持 admin 用户
        - 密码必须与 API_TOKEN 配置值一致
        - 实现 API 和界面鉴权的统一
        """
        # 只验证 admin 用户
        if username != config.GRADIO_USERNAME:
            Logger.warning(f"Invalid username attempt: {username}")
            return False
        
        # 验证密码是否与 API_TOKEN 一致
        if password != config.GRADIO_PASSWORD:
            Logger.warning(f"Invalid password attempt for user: {username}")
            return False
        
        return True

    @staticmethod
    def create_gradio_session(username: str) -> str:
        """
        创建 Gradio 界面登录会话

        Args:
            username: 用户名

        Returns:
            str: 会话ID
        """
        # 生成随机会话ID
        session_id = secrets.token_urlsafe(32)
        
        # 计算过期时间
        expire_time = datetime.utcnow() + timedelta(seconds=config.GRADIO_AUTH_TIMEOUT)
        
        # 存储会话信息
        AuthService._sessions[session_id] = {
            "username": username,
            "expire_time": expire_time
        }
        
        Logger.info(f"Gradio session created for user: {username}, session_id: {session_id}")
        return session_id

    @staticmethod
    def verify_gradio_session(session_id: str) -> Optional[str]:
        """
        验证 Gradio 界面会话

        Args:
            session_id: 会话ID

        Returns:
            Optional[str]: 用户名，如果会话无效则返回None
        """
        if session_id not in AuthService._sessions:
            Logger.warning(f"Invalid Gradio session: {session_id}")
            return None
        
        session = AuthService._sessions[session_id]
        
        # 检查会话是否过期
        if datetime.utcnow() > session["expire_time"]:
            Logger.info(f"Gradio session expired: {session_id}")
            del AuthService._sessions[session_id]
            return None
        
        return session["username"]

    @staticmethod
    def revoke_gradio_session(session_id: str) -> bool:
        """
        撤销 Gradio 界面会话

        Args:
            session_id: 会话ID

        Returns:
            bool: 是否成功撤销
        """
        if session_id in AuthService._sessions:
            username = AuthService._sessions[session_id]["username"]
            del AuthService._sessions[session_id]
            Logger.info(f"Gradio session revoked for user: {username}, session_id: {session_id}")
            return True
        return False

    @staticmethod
    def cleanup_expired_sessions() -> int:
        """
        清理过期的会话

        Returns:
            int: 清理的会话数量
        """
        current_time = datetime.utcnow()
        expired_sessions = [
            session_id for session_id, session in AuthService._sessions.items()
            if current_time > session["expire_time"]
        ]
        
        for session_id in expired_sessions:
            del AuthService._sessions[session_id]
        
        if expired_sessions:
            Logger.info(f"Cleaned up {len(expired_sessions)} expired Gradio sessions")
        
        return len(expired_sessions)


async def verify_token(credentials: Optional[HTTPAuthorizationCredentials] = Security(security_optional)) -> Optional[Dict[str, Any]]:
    """
    验证令牌的依赖函数（根据配置决定是否强制验证）

    注意：此函数的行为由 config.ENABLE_TOKEN_AUTH 配置控制：
    - ENABLE_TOKEN_AUTH=false（默认）：不验证token，始终返回None，所有API接口无需token即可访问
    - ENABLE_TOKEN_AUTH=true：验证token，token无效时抛出HTTPException

    Args:
        credentials: HTTP 认证凭据（可选）

    Returns:
        Optional[Dict[str, Any]]: 解码后的数据，如果未启用校验则返回None

    Raises:
        HTTPException: 令牌无效时抛出（仅在启用token校验时）
    """
    # 如果未启用token校验，直接返回None
    if not config.ENABLE_TOKEN_AUTH:
        return None
    
    # 如果未提供token，返回None（允许无token访问）
    if credentials is None or credentials.credentials is None:
        return None
    
    token = credentials.credentials

    # 检查是否为固定令牌
    if AuthService.verify_fixed_token(token):
        return {"type": "fixed", "token": token}

    # 验证 JWT 令牌
    payload = AuthService.verify_token(token)
    return payload


async def verify_token_required(credentials: HTTPAuthorizationCredentials = Security(security)) -> Dict[str, Any]:
    """
    强制验证令牌的依赖函数（始终需要token）

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


async def verify_token_optional(credentials: Optional[HTTPAuthorizationCredentials] = Security(security_optional)) -> Optional[Dict[str, Any]]:
    """
    可选的令牌验证依赖函数（仅在启用token校验时才验证）
    
    Args:
        credentials: HTTP 认证凭据（可选）

    Returns:
        Optional[Dict[str, Any]]: 解码后的数据，如果未启用校验或未提供token则返回None
    """
    # 如果未启用token校验，直接返回None
    if not config.ENABLE_TOKEN_AUTH:
        return None
    
    # 如果未提供token，返回None
    if credentials is None or credentials.credentials is None:
        return None
    
    token = credentials.credentials

    # 检查是否为固定令牌
    if AuthService.verify_fixed_token(token):
        return {"type": "fixed", "token": token}

    # 验证 JWT 令牌
    payload = AuthService.verify_token(token)
    return payload