"""
认证相关的API路由
处理用户登录、注册、令牌刷新等操作
"""
import logging
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, get_current_superuser
from app.core.security import decode_token
from app.models.user import User
from app.schemas.user import User as UserSchema, UserCreate, UserUpdate
from app.services.auth import AuthService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/login", summary="用户登录")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Any:
    """
    用户登录接口
    
    - **username**: 用户名
    - **password**: 密码
    
    返回JWT访问令牌和刷新令牌
    """
    auth_service = AuthService(db)
    user = auth_service.authenticate_user(form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码不正确",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return auth_service.create_tokens_for_user(user)


@router.post("/refresh-token", summary="刷新访问令牌")
async def refresh_token(
    refresh_token: str = Body(..., embed=True),
    db: Session = Depends(get_db)
) -> Any:
    """
    使用刷新令牌获取新的访问令牌
    
    - **refresh_token**: 刷新令牌
    
    返回新的访问令牌
    """
    try:
        payload = decode_token(refresh_token)
        user_id = payload.get("sub")
        token_type = payload.get("type")
        
        if not user_id or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的刷新令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        auth_service = AuthService(db)
        user = auth_service.get_user(user_id)
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的用户",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 只返回新的访问令牌，刷新令牌保持不变
        access_token = auth_service.create_tokens_for_user(user)["access_token"]
        return {"access_token": access_token, "token_type": "bearer"}
    
    except Exception as e:
        logger.error(f"刷新令牌出错: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/register", response_model=UserSchema, summary="用户注册")
async def register(
    user_in: UserCreate,
    db: Session = Depends(get_db)
) -> Any:
    """
    用户注册接口
    
    - **username**: 用户名（必填）
    - **email**: 邮箱（必填）
    - **password**: 密码（必填）
    - **full_name**: 全名（可选）
    - **tenant_id**: 租户ID（可选）
    
    返回创建的用户信息（不含密码）
    """
    auth_service = AuthService(db)
    user = auth_service.create_user(user_in)
    return user


@router.get("/me", response_model=UserSchema, summary="获取当前用户信息")
async def read_users_me(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    获取当前已登录用户的信息
    
    需要有效的JWT访问令牌
    """
    return current_user


@router.put("/me", response_model=UserSchema, summary="更新当前用户信息")
async def update_user_me(
    user_in: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    更新当前已登录用户的信息
    
    - **username**: 用户名（可选）
    - **email**: 邮箱（可选）
    - **password**: 密码（可选）
    - **full_name**: 全名（可选）
    
    需要有效的JWT访问令牌
    """
    auth_service = AuthService(db)
    user = auth_service.update_user(current_user.id, user_in)
    return user


@router.get("/users", response_model=List[UserSchema], summary="获取所有用户")
async def read_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
) -> Any:
    """
    获取所有用户列表
    
    仅超级管理员可访问
    """
    auth_service = AuthService(db)
    users = auth_service.get_users(skip=skip, limit=limit)
    return users


@router.get("/users/{user_id}", response_model=UserSchema, summary="获取指定用户信息")
async def read_user(
    user_id: str,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
) -> Any:
    """
    获取指定用户的信息
    
    仅超级管理员可访问
    """
    auth_service = AuthService(db)
    user = auth_service.get_user(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
        
    return user


@router.put("/users/{user_id}", response_model=UserSchema, summary="更新指定用户信息")
async def update_user(
    user_id: str,
    user_in: UserUpdate,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
) -> Any:
    """
    更新指定用户的信息
    
    仅超级管理员可访问
    """
    auth_service = AuthService(db)
    user = auth_service.update_user(user_id, user_in)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
        
    return user


@router.delete("/users/{user_id}", summary="删除用户")
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
) -> Any:
    """
    删除指定用户
    
    仅超级管理员可访问
    """
    auth_service = AuthService(db)
    success = auth_service.delete_user(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
        
    return {"status": "success", "message": "用户已删除"}
