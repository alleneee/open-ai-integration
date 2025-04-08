"""
认证服务模块
提供用户认证、注册、权限验证等功能
"""
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status

from app.models.user import User, Role, Permission
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token
from app.api.deps import get_db

logger = logging.getLogger(__name__)


class AuthService:
    """认证服务类，处理用户认证和授权相关操作"""
    
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db
        
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """验证用户身份
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            验证成功时返回用户对象，否则返回None
        """
        user = self.get_user_by_username(username)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        # 更新最后登录时间
        user.last_login = datetime.utcnow()
        self.db.commit()
        return user
    
    def create_user(self, user_in: UserCreate) -> User:
        """创建新用户
        
        Args:
            user_in: 用户创建数据
            
        Returns:
            创建的用户对象
            
        Raises:
            HTTPException: 当用户名或邮箱已存在时
        """
        # 检查用户名和邮箱是否已存在
        if self.get_user_by_username(user_in.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已被使用"
            )
        if self.get_user_by_email(user_in.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被使用"
            )
        
        # 创建用户对象
        user_data = user_in.model_dump(exclude={"password", "roles"})
        db_user = User(
            **user_data,
            hashed_password=get_password_hash(user_in.password)
        )
        
        # 添加角色
        if user_in.roles:
            roles = self.db.query(Role).filter(Role.name.in_(user_in.roles)).all()
            if roles:
                db_user.roles = roles
        
        # 保存用户
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        
        return db_user
    
    def update_user(self, user_id: str, user_in: UserUpdate) -> Optional[User]:
        """更新用户信息
        
        Args:
            user_id: 用户ID
            user_in: 更新数据
            
        Returns:
            更新后的用户对象，用户不存在则返回None
        """
        user = self.get_user(user_id)
        if not user:
            return None
        
        update_data = user_in.model_dump(exclude_unset=True)
        
        # 处理密码更新
        if "password" in update_data:
            hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]
            update_data["hashed_password"] = hashed_password
        
        # 处理角色更新
        if "roles" in update_data:
            roles = update_data.pop("roles", [])
            if roles:
                db_roles = self.db.query(Role).filter(Role.name.in_(roles)).all()
                user.roles = db_roles
        
        # 更新其他字段
        for field, value in update_data.items():
            setattr(user, field, value)
        
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def delete_user(self, user_id: str) -> bool:
        """删除用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            是否成功删除
        """
        user = self.get_user(user_id)
        if not user:
            return False
        
        self.db.delete(user)
        self.db.commit()
        
        return True
    
    def get_user(self, user_id: str) -> Optional[User]:
        """根据ID获取用户
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户对象，不存在则返回None
        """
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户
        
        Args:
            username: 用户名
            
        Returns:
            用户对象，不存在则返回None
        """
        return self.db.query(User).filter(User.username == username).first()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户
        
        Args:
            email: 邮箱地址
            
        Returns:
            用户对象，不存在则返回None
        """
        return self.db.query(User).filter(User.email == email).first()
    
    def get_users(self, skip: int = 0, limit: int = 100, tenant_id: Optional[str] = None) -> List[User]:
        """获取用户列表
        
        Args:
            skip: 跳过记录数
            limit: 限制返回记录数
            tenant_id: 可选的租户ID筛选
            
        Returns:
            用户列表
        """
        query = self.db.query(User)
        if tenant_id:
            query = query.filter(User.tenant_id == tenant_id)
        
        return query.offset(skip).limit(limit).all()
    
    def create_tokens_for_user(self, user: User) -> Dict[str, str]:
        """为用户创建访问令牌和刷新令牌
        
        Args:
            user: 用户对象
            
        Returns:
            包含访问令牌和刷新令牌的字典
        """
        # 准备额外声明数据
        claims = {
            "username": user.username,
            "is_superuser": user.is_superuser,
            "tenant_id": user.tenant_id,
            "roles": [role.name for role in user.roles]
        }
        
        # 创建令牌
        access_token = create_access_token(subject=user.id, claims=claims)
        refresh_token = create_refresh_token(subject=user.id)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    
    def has_permission(self, user: User, resource: str, action: str) -> bool:
        """检查用户是否有特定资源的操作权限
        
        Args:
            user: 用户对象
            resource: 资源名称
            action: 操作名称
            
        Returns:
            是否有权限
        """
        # 超级管理员拥有全部权限
        if user.is_superuser:
            return True
        
        # 检查用户角色权限
        for role in user.roles:
            for permission in role.permissions:
                if permission.resource == resource and permission.action == action:
                    return True
                if permission.resource == "*" and permission.action == "*":
                    return True
                if permission.resource == resource and permission.action == "*":
                    return True
                if permission.resource == "*" and permission.action == action:
                    return True
        
        return False
