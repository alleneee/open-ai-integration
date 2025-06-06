"""
数据库连接和会话管理
提供 SQLAlchemy 配置、连接池管理和会话处理
"""
import logging
from typing import Generator, List, Optional
from datetime import datetime
from uuid import uuid4

from sqlalchemy import create_engine, Column, String, Text, DateTime, ForeignKey, Integer, JSON, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship

from app.core.config import settings
from app.models.conversation import MessageRole, ConversationState

logger = logging.getLogger(__name__)

# 创建 SQLAlchemy 引擎
# 使用连接池配置以优化性能
engine = create_engine(
    settings.DATABASE_URI,
    pool_pre_ping=True,  # 检查连接是否有效
    pool_recycle=settings.DATABASE_POOL_RECYCLE,   # 连接回收时间
    pool_size=settings.DATABASE_POOL_SIZE,         # 连接池大小
    max_overflow=settings.DATABASE_MAX_OVERFLOW,   # 连接池最大溢出
    echo=settings.SQL_ECHO,  # 在开发环境中开启 SQL 日志
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建 Base 类作为所有模型的基类
Base = declarative_base()

# 对话模型
class Conversation(Base):
    """对话数据库模型"""
    __tablename__ = "conversations"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title = Column(String(255), nullable=False)
    created_by = Column(String(36), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    state = Column(Enum(ConversationState), default=ConversationState.ACTIVE)
    meta_data = Column(JSON, nullable=True)
    
    # 关系：一个对话有多个消息
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


# 消息模型
class Message(Base):
    """消息数据库模型"""
    __tablename__ = "messages"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False)
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    meta_data = Column(JSON, nullable=True)
    
    # 关系：一个消息属于一个对话
    conversation = relationship("Conversation", back_populates="messages")


def initialize_db() -> None:
    """初始化数据库，创建所有表"""
    try:
        # 在应用启动时创建所有表
        # 在生产环境中，应使用 Alembic 进行数据库迁移
        if settings.environment != "production":
            # 仅在非生产环境中自动创建表
            Base.metadata.create_all(bind=engine)
            logger.info("已创建所有数据库表")
        else:
            logger.info("生产环境不自动创建表，请使用 Alembic 迁移")
    except Exception as e:
        logger.error(f"初始化数据库时出错: {e}")
        raise

def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话的依赖
    
    使用 yield 以确保会话在请求结束时正确关闭
    这是 FastAPI 的依赖注入模式，用于在请求生命周期中管理数据库会话
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
