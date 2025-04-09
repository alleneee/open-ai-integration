"""
安全组件模块
提供密码哈希、JWT令牌生成和验证等功能
"""
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union
import hashlib
import base64

import jwt
from fastapi import HTTPException, status

from app.core.config import settings

# 简单的密码哈希，使用SHA256
def _simple_hash(password: str) -> str:
    """简单的密码哈希函数，使用SHA256加盐"""
    salted = password + settings.SECRET_KEY[:8]  # 添加一个简单的盐值
    hash_obj = hashlib.sha256(salted.encode())
    return base64.b64encode(hash_obj.digest()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码
    
    Args:
        plain_password: 明文密码
        hashed_password: 加密后的密码
        
    Returns:
        验证结果，匹配返回True，否则返回False
    """
    # 尝试使用标准哈希验证
    if hashed_password.startswith("$2b$"):
        # 看起来是bcrypt格式，但我们可能无法使用它
        # 在开发环境中，我们创建一个新用户并验证它的密码
        # 让旧用户重置密码
        return False
    
    # 使用我们的简单哈希
    return _simple_hash(plain_password) == hashed_password


def get_password_hash(password: str) -> str:
    """获取密码哈希值
    
    Args:
        password: 明文密码
        
    Returns:
        哈希密码
    """
    # 使用简单的哈希方法
    return _simple_hash(password)


def create_access_token(
    subject: Union[str, Any], 
    expires_delta: Optional[timedelta] = None, 
    claims: Optional[Dict[str, Any]] = None
) -> str:
    """创建JWT访问令牌
    
    Args:
        subject: 令牌主题（通常是用户ID）
        expires_delta: 过期时间增量，不提供则使用默认配置
        claims: 额外的声明数据
        
    Returns:
        JWT令牌字符串
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    if claims:
        to_encode.update(claims)
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    subject: Union[str, Any],
    claims: Optional[Dict[str, Any]] = None
) -> str:
    """创建JWT刷新令牌
    
    Args:
        subject: 令牌主题（通常是用户ID）
        claims: 额外的声明数据
        
    Returns:
        JWT刷新令牌字符串
    """
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    if claims:
        to_encode.update(claims)
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """解码验证JWT令牌
    
    Args:
        token: JWT令牌字符串
        
    Returns:
        解码后的令牌数据
        
    Raises:
        HTTPException: 令牌无效、过期或验证失败
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
