"""
任务状态管理模型
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from enum import Enum

from sqlalchemy import Column, String, DateTime, Integer, Float, Text, Index, JSON
from sqlalchemy.orm import relationship, mapped_column, Mapped
from pydantic import BaseModel, Field, validator

from app.models.database import Base


class TaskState(str, Enum):
    """任务状态枚举"""
    PENDING = "PENDING"     # 等待中
    RECEIVED = "RECEIVED"   # 已接收
    STARTED = "STARTED"     # 已开始
    RUNNING = "RUNNING"     # 运行中
    PROGRESS = "PROGRESS"   # 进行中
    RETRYING = "RETRYING"   # 重试中
    SUCCESS = "SUCCESS"     # 成功
    FAILURE = "FAILURE"     # 失败
    REVOKED = "REVOKED"     # 被撤销
    CANCELLED = "CANCELLED" # 已取消
    RETRY = "RETRY"         # 重试
    IGNORED = "IGNORED"     # 被忽略
    REJECTED = "REJECTED"   # 被拒绝
    COMPLETED = "COMPLETED" # 已完成
    FAILED = "FAILED"       # 已失败


class TaskStatus(Base):
    """任务状态表"""
    __tablename__ = "task_status"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    task_name: Mapped[str] = mapped_column(String(255), nullable=False)
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=TaskState.PENDING.value)
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="任务元数据，JSON格式")
    retries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    
    # 时间追踪
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, 
                                              default=datetime.now, onupdate=datetime.now)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # 增加索引
    __table_args__ = (
        Index("ix_task_status_status_created_at", "status", "created_at"),
        Index("ix_task_status_task_type_status", "task_type", "status"),
    )


# ========== Pydantic 模型 ==========

class TaskStatusBase(BaseModel):
    """任务状态基础模型"""
    task_name: str
    task_type: str
    status: TaskState
    progress: float = 0.0
    metadata: Optional[Dict[str, Any]] = None
    retries: int = 0
    max_retries: int = 3


class TaskStatusCreate(TaskStatusBase):
    """任务状态创建模型"""
    task_id: str
    user_id: Optional[str] = None


class TaskStatusUpdate(BaseModel):
    """任务状态更新模型"""
    status: Optional[TaskState] = None
    progress: Optional[float] = None
    result: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    retries: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    @validator('progress')
    def check_progress_range(cls, v):
        if v is not None and (v < 0.0 or v > 100.0):
            raise ValueError('进度必须在0到100之间')
        return v


class TaskStatusResponse(TaskStatusBase):
    """任务状态响应模型"""
    id: str
    task_id: str
    result: Optional[str] = None
    error: Optional[str] = None
    user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True


class TaskStatusFilterParams(BaseModel):
    """任务状态过滤参数"""
    task_type: Optional[str] = None
    status: Optional[TaskState] = None
    user_id: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
