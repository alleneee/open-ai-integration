"""
用户相关的Pydantic模型
提供用户创建、更新、验证等请求和响应模型
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# 基础模式 - 共享属性
class UserBase(BaseModel):
    """用户基础信息模式"""
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    is_active: Optional[bool] = True
    tenant_id: Optional[str] = None


# 创建用户请求模式
class UserCreate(UserBase):
    """创建用户请求模式"""
    password: str
    is_superuser: Optional[bool] = False
    roles: Optional[List[str]] = []


# 用户更新请求模式
class UserUpdate(BaseModel):
    """用户更新请求模式"""
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    tenant_id: Optional[str] = None
    roles: Optional[List[str]] = None


# 角色模式
class RoleBase(BaseModel):
    """角色基础模式"""
    name: str
    description: Optional[str] = None


class RoleCreate(RoleBase):
    """创建角色请求模式"""
    pass


class RoleUpdate(BaseModel):
    """更新角色请求模式"""
    name: Optional[str] = None
    description: Optional[str] = None


class RoleInDB(RoleBase):
    """数据库角色模式"""
    id: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# 用户响应模式
class User(UserBase):
    """用户响应模式"""
    id: str
    is_superuser: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    roles: List[RoleInDB] = []
    
    model_config = ConfigDict(from_attributes=True)


# 权限模式
class PermissionBase(BaseModel):
    """权限基础模式"""
    resource: str
    action: str


class PermissionCreate(PermissionBase):
    """创建权限请求模式"""
    role_id: str


class PermissionUpdate(BaseModel):
    """更新权限请求模式"""
    resource: Optional[str] = None
    action: Optional[str] = None


class PermissionInDB(PermissionBase):
    """数据库权限模式"""
    id: str
    role_id: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
