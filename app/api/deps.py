"""
API 依赖注入模块
提供可重用的依赖项，如数据库会话、当前用户和租户信息等
"""
import logging
from typing import Generator, Optional, Union

from fastapi import Depends, HTTPException, Header, status, Security
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from app.models.database import SessionLocal
from app.models.user import User
from app.core.config import settings
from app.core.security import decode_token

logger = logging.getLogger(__name__)

# OAuth2 认证处理
# 设置 auto_error=False，这样即使没有令牌也不会自动报错
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=settings.TOKEN_URL, auto_error=False)

def get_db() -> Generator[Session, None, None]:
    """
    提供数据库会话依赖项
    在请求结束时自动关闭会话
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_tenant_id(
    x_tenant_id: Optional[str] = Header(None, description="租户 ID")
) -> str:
    """
    从请求头获取当前租户 ID
    如果未提供，则返回默认租户 ID
    
    Headers:
        X-Tenant-ID: 租户标识符
        
    Returns:
        租户 ID 字符串
    
    Raises:
        HTTPException: 如果未提供租户 ID 且没有默认值
    """
    if not x_tenant_id:
        # 可以在此设置默认租户 ID 或返回错误
        # 例如: return "default_tenant"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供租户 ID，请在请求头中添加 X-Tenant-ID"
        )
    return x_tenant_id

def get_current_user_id(
    x_user_id: Optional[str] = Header(None, description="用户 ID")
) -> Optional[str]:
    """
    从请求头获取当前用户 ID
    如果未提供，则返回匿名用户
    
    Headers:
        X-User-ID: 用户标识符
        
    Returns:
        用户 ID 字符串或 None
    """
    # 此处可以根据需求进行身份验证检查
    return x_user_id

def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    获取当前已认证用户
    
    Args:
        token: JWT访问令牌 (现在是可选的)
        db: 数据库会话
        
    Returns:
        当前用户对象
        
    Raises:
        HTTPException: 认证失败或用户不存在时
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if token is None: # 如果 auto_error=False 且没有提供 token，显式抛出异常
        raise credentials_exception
        
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception # 保持不变
    except JWTError:
        raise credentials_exception # 保持不变
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        # 改为 401 可能更合适，因为令牌可能有效但用户不存在
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="用户不存在或令牌无效" # 更新消息
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, # 保持 400
            detail="用户已停用"
        )
    
    return user

def get_current_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    获取当前超级管理员用户
    
    Args:
        current_user: 当前用户
        
    Returns:
        当前超级管理员用户
        
    Raises:
        HTTPException: 用户不是超级管理员时
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，需要超级管理员权限"
        )
    return current_user

def require_admin_permission(
    x_user_role: Optional[str] = Header(None, description="用户角色")
) -> bool:
    """
    检查用户是否具有管理员权限
    
    Headers:
        X-User-Role: 用户角色
        
    Returns:
        如果用户是管理员则返回 True
        
    Raises:
        HTTPException: 如果用户不是管理员
    """
    if x_user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return True

def check_resource_permission(
    resource: str,
    action: str,
    current_user: User = Depends(get_current_user),
) -> bool:
    """
    检查用户是否有权限访问特定资源
    
    Args:
        resource: 资源名称
        action: 操作(read, write, delete等)
        current_user: 当前用户
        
    Returns:
        是否有权限
        
    Raises:
        HTTPException: 没有权限时
    """
    # 超级管理员拥有所有权限
    if current_user.is_superuser:
        return True
    
    # 检查用户角色权限
    for role in current_user.roles:
        for permission in role.permissions:
            if (permission.resource == resource and permission.action == action) or \
               (permission.resource == "*" and permission.action == "*") or \
               (permission.resource == resource and permission.action == "*") or \
               (permission.resource == "*" and permission.action == action):
                return True
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"没有权限执行此操作: {action} {resource}"
    )

async def get_current_user_optional(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None)
) -> Optional[User]:
    """
    获取当前用户，如果有提供有效的认证令牌
    
    与 get_current_user 不同，认证失败时不抛出异常，而是返回 None
    
    Args:
        db: 数据库会话
        authorization: Authorization 请求头，格式为 "Bearer {token}"
        
    Returns:
        当前用户对象，如果认证失败则返回 None
    """
    if authorization is None:
        return None
        
    # 获取token，格式应该是 "Bearer {token}"
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            return None
    except (ValueError, AttributeError):
        return None
    
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        return None
    
    return user
