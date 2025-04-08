"""
用户数据模型
定义用户、角色和权限的SQLAlchemy模型
"""
import uuid
from datetime import datetime
from typing import List

from sqlalchemy import (
    Boolean, Column, String, Integer, DateTime, ForeignKey, Table
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.database import Base


# 用户-角色多对多关联表
user_role = Table(
    "user_role",
    Base.metadata,
    Column("user_id", String(36), ForeignKey("users.id"), primary_key=True),
    Column("role_id", String(36), ForeignKey("roles.id"), primary_key=True),
)


class User(Base):
    """用户模型"""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(100), nullable=False)
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    tenant_id = Column(String(36), index=True, nullable=True)

    # 关联
    roles = relationship("Role", secondary=user_role, back_populates="users")

    def __repr__(self):
        return f"<User {self.username}>"


class Role(Base):
    """角色模型"""
    __tablename__ = "roles"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(String(200))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关联
    users = relationship("User", secondary=user_role, back_populates="roles")
    permissions = relationship("Permission", back_populates="role")
    
    def __repr__(self):
        return f"<Role {self.name}>"


class Permission(Base):
    """权限模型"""
    __tablename__ = "permissions"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    role_id = Column(String(36), ForeignKey("roles.id"))
    resource = Column(String(100), nullable=False)  # 资源类型，如 "documents", "users"
    action = Column(String(100), nullable=False)    # 操作类型，如 "read", "write", "delete"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关联
    role = relationship("Role", back_populates="permissions")
    
    def __repr__(self):
        return f"<Permission {self.resource}:{self.action}>"
