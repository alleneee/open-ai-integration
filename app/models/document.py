"""
文档相关模型定义
提供文档及其段落的数据模型和状态管理
"""
import datetime
import logging
import uuid
from enum import Enum, auto
from typing import List, Optional, Dict, Any, Union, Tuple

from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Enum as SQLAEnum
from sqlalchemy.orm import relationship, Session
from pydantic import BaseModel, Field

from app.models.database import Base, SessionLocal

logger = logging.getLogger(__name__)

# 文档状态枚举
class DocumentStatus(str, Enum):
    PENDING = "pending"       # 等待处理
    PROCESSING = "processing" # 处理中
    COMPLETED = "completed"   # 已完成
    ERROR = "error"           # 错误

# SQLAlchemy 模型
class Document(Base):
    """文档数据库模型"""
    __tablename__ = "documents"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    collection_name = Column(String(255), nullable=False, index=True)
    
    filename = Column(String(255), nullable=False)
    file_path = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=True)
    file_type = Column(String(50), nullable=True)
    
    status = Column(SQLAEnum(DocumentStatus), default=DocumentStatus.PENDING, nullable=False)
    error_message = Column(Text, nullable=True)
    
    segment_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # 关联段落
    segments = relationship("Segment", back_populates="document", cascade="all, delete-orphan")

class Segment(Base):
    """文档段落数据库模型"""
    __tablename__ = "segments"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    
    content = Column(Text, nullable=False)
    meta_data = Column(Text, nullable=True)  # JSON存储，改名避免与SQLAlchemy保留字冲突
    
    chunk_index = Column(Integer, nullable=False)
    enabled = Column(Integer, default=1, nullable=False)  # 1=启用, 0=禁用
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # 关联文档
    document = relationship("Document", back_populates="segments")

# Pydantic 模型
class SegmentModel(BaseModel):
    """段落 Pydantic 模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    content: str
    meta_data: Dict[str, Any] = {}  # 同样修改模型中的字段名
    chunk_index: int
    enabled: int = 1
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    
    class Config:
        from_attributes = True

class DocumentModel(BaseModel):
    """文档 Pydantic 模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    collection_name: str
    filename: str
    file_path: str
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    status: DocumentStatus = DocumentStatus.PENDING
    error_message: Optional[str] = None
    segment_count: int = 0
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    
    class Config:
        from_attributes = True

class DocumentCreate(BaseModel):
    """文档创建请求模型"""
    filename: str
    tenant_id: str
    collection_name: str
    file_size: Optional[int] = None
    file_type: Optional[str] = None

class DocumentResponse(BaseModel):
    """文档响应模型"""
    id: str
    filename: str
    status: DocumentStatus
    error_message: Optional[str] = None
    segment_count: int
    created_at: datetime.datetime
    updated_at: datetime.datetime
    
    class Config:
        from_attributes = True

class DocumentListResponse(BaseModel):
    """文档列表响应模型"""
    items: List[DocumentResponse]
    total: int

# 数据库操作函数
def create_document(document_data: Dict[str, Any], db: Optional[Session] = None) -> Document:
    """创建文档记录"""
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True
    
    try:
        document = Document(**document_data)
        db.add(document)
        db.commit()
        db.refresh(document)
        return document
    except Exception as e:
        db.rollback()
        logger.error(f"创建文档记录失败: {str(e)}")
        raise
    finally:
        if close_session:
            db.close()

def get_document_by_id(document_id: str, db: Optional[Session] = None) -> Optional[Document]:
    """通过ID获取文档"""
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True
    
    try:
        return db.query(Document).filter(Document.id == document_id).first()
    finally:
        if close_session:
            db.close()

def update_document_status(document_id: str, status: DocumentStatus, error_message: Optional[str] = None, 
                          segment_count: Optional[int] = None, db: Optional[Session] = None) -> bool:
    """更新文档状态"""
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True
    
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return False
        
        document.status = status
        if error_message is not None:
            document.error_message = error_message
        if segment_count is not None:
            document.segment_count = segment_count
        
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"更新文档状态失败: {str(e)}")
        return False
    finally:
        if close_session:
            db.close()

def delete_documents(document_ids: List[str], db: Optional[Session] = None) -> bool:
    """删除多个文档"""
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True
    
    try:
        # 删除关联的段落记录会通过级联删除自动处理
        db.query(Document).filter(Document.id.in_(document_ids)).delete(synchronize_session=False)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"删除文档失败: {str(e)}")
        return False
    finally:
        if close_session:
            db.close()

def list_documents(tenant_id: str, collection_name: Optional[str] = None, status: Optional[DocumentStatus] = None, 
                  skip: int = 0, limit: int = 100, db: Optional[Session] = None) -> Tuple[List[Document], int]:
    """列出文档"""
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True
    
    try:
        query = db.query(Document).filter(Document.tenant_id == tenant_id)
        
        if collection_name:
            query = query.filter(Document.collection_name == collection_name)
        
        if status:
            query = query.filter(Document.status == status)
        
        total = query.count()
        
        documents = query.order_by(Document.created_at.desc()).offset(skip).limit(limit).all()
        return documents, total
    finally:
        if close_session:
            db.close()

def add_segment(segment_data: Dict[str, Any], db: Optional[Session] = None) -> Segment:
    """添加段落记录"""
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True
    
    try:
        segment = Segment(**segment_data)
        db.add(segment)
        db.commit()
        db.refresh(segment)
        return segment
    except Exception as e:
        db.rollback()
        logger.error(f"添加段落记录失败: {str(e)}")
        raise
    finally:
        if close_session:
            db.close()

def get_segments_by_document_id(document_id: str, enabled_only: bool = True, db: Optional[Session] = None) -> List[Segment]:
    """获取文档的所有段落"""
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True
    
    try:
        query = db.query(Segment).filter(Segment.document_id == document_id)
        
        if enabled_only:
            query = query.filter(Segment.enabled == 1)
            
        return query.order_by(Segment.chunk_index).all()
    finally:
        if close_session:
            db.close()
