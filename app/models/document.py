"""
文档相关模型定义
提供文档及其段落的数据模型和状态管理
"""
import datetime
import logging
import uuid
import json
from enum import Enum, auto
from typing import List, Optional, Dict, Any, Union, Tuple

from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Enum as SQLAEnum, Boolean, Float, Table, JSON
from sqlalchemy.orm import relationship, Session
from pydantic import BaseModel, Field

from app.models.database import Base, SessionLocal

logger = logging.getLogger(__name__)

# 文档状态枚举
class DocumentStatus(str, Enum):
    PENDING = "pending"       # 等待处理
    PROCESSING = "processing" # 处理中
    PARSING = "parsing"       # 解析中
    SPLITTING = "splitting"   # 分块中
    INDEXING = "indexing"     # 索引中
    COMPLETED = "completed"   # 已完成
    ERROR = "error"           # 错误

# 文档格式枚举
class DocumentFormat(str, Enum):
    TEXT = "text"             # 纯文本
    MARKDOWN = "markdown"     # Markdown
    PDF = "pdf"               # PDF
    DOCX = "docx"             # Word
    HTML = "html"             # HTML
    CSV = "csv"               # CSV
    JSON = "json"             # JSON
    CODE = "code"             # 代码
    OTHER = "other"           # 其他

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
    doc_form = Column(String(50), nullable=True)
    doc_format = Column(SQLAEnum(DocumentFormat), nullable=True)
    
    status = Column(SQLAEnum(DocumentStatus), default=DocumentStatus.PENDING, nullable=False)
    error_message = Column(Text, nullable=True)
    
    enabled = Column(Boolean, default=True, nullable=False)
    archived = Column(Boolean, default=False, nullable=False)
    
    segment_count = Column(Integer, default=0)
    word_count = Column(Integer, default=0)
    token_count = Column(Integer, default=0)
    
    # 处理时间记录
    processing_started_at = Column(DateTime, nullable=True)
    parsing_started_at = Column(DateTime, nullable=True)
    parsing_completed_at = Column(DateTime, nullable=True)
    splitting_started_at = Column(DateTime, nullable=True)
    splitting_completed_at = Column(DateTime, nullable=True)
    indexing_started_at = Column(DateTime, nullable=True)
    indexing_completed_at = Column(DateTime, nullable=True)
    processing_completed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # 关联段落
    segments = relationship("Segment", back_populates="document", cascade="all, delete-orphan")
    
    # 与知识库的多对多关系
    knowledge_bases = relationship("KnowledgeBase", secondary="knowledge_base_documents", back_populates="documents")
    
    __table_args__ = (
        {'mysql_charset': 'utf8mb4', 'mysql_collate': 'utf8mb4_unicode_ci'},
    )
    
    @property
    def meta_info(self) -> Dict[str, Any]:
        """获取文档元信息"""
        return {
            "filename": self.filename,
            "file_size": self.file_size,
            "file_type": self.file_type,
            "segment_count": self.segment_count,
            "word_count": self.word_count,
            "token_count": self.token_count,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    @property
    def processing_time(self) -> Optional[float]:
        """获取文档处理总时间（秒）"""
        if self.processing_started_at and self.processing_completed_at:
            return (self.processing_completed_at - self.processing_started_at).total_seconds()
        return None
    
    @property
    def parsing_time(self) -> Optional[float]:
        """获取文档解析时间（秒）"""
        if self.parsing_started_at and self.parsing_completed_at:
            return (self.parsing_completed_at - self.parsing_started_at).total_seconds()
        return None
    
    @property
    def splitting_time(self) -> Optional[float]:
        """获取文档分块时间（秒）"""
        if self.splitting_started_at and self.splitting_completed_at:
            return (self.splitting_completed_at - self.splitting_started_at).total_seconds()
        return None
    
    @property
    def indexing_time(self) -> Optional[float]:
        """获取文档索引时间（秒）"""
        if self.indexing_started_at and self.indexing_completed_at:
            return (self.indexing_completed_at - self.indexing_started_at).total_seconds()
        return None

class Segment(Base):
    """文档段落数据库模型"""
    __tablename__ = "segments"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    dataset_id = Column(String(36), nullable=True, index=True)  # 关联的知识库ID
    
    content = Column(Text, nullable=False)
    meta_data = Column(Text, nullable=True)  # JSON存储，改名避免与SQLAlchemy保留字冲突
    
    chunk_index = Column(Integer, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    
    word_count = Column(Integer, default=0)
    token_count = Column(Integer, default=0)
    embedding_tokens = Column(Integer, default=0)
    
    embedding_vector = Column(Text, nullable=True)
    embedding_model = Column(String(100), nullable=True)
    score = Column(Float, nullable=True)
    
    indexing_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # 关联文档
    document = relationship("Document", back_populates="segments")
    
    # 关联子分块
    child_chunks = relationship("ChildChunk", back_populates="segment", cascade="all, delete-orphan")
    
    @property
    def meta_data_dict(self) -> Dict[str, Any]:
        """获取元数据字典"""
        if not self.meta_data:
            return {}
        try:
            return json.loads(self.meta_data)
        except:
            return {}

# Pydantic 模型
class SegmentModel(BaseModel):
    """段落 Pydantic 模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    dataset_id: Optional[str] = None
    content: str
    meta_data: Dict[str, Any] = {}  # 同样修改模型中的字段名
    chunk_index: int
    enabled: bool = True
    status: str = "pending"
    word_count: int = 0
    token_count: int = 0
    embedding_tokens: int = 0
    embedding_vector: Optional[str] = None
    embedding_model: Optional[str] = None
    score: Optional[float] = None
    indexing_at: Optional[datetime.datetime] = None
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
    doc_form: Optional[str] = None
    doc_format: Optional[DocumentFormat] = None
    status: DocumentStatus = DocumentStatus.PENDING
    error_message: Optional[str] = None
    enabled: bool = True
    archived: bool = False
    segment_count: int = 0
    word_count: int = 0
    token_count: int = 0
    processing_started_at: Optional[datetime.datetime] = None
    processing_completed_at: Optional[datetime.datetime] = None
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
    doc_format: Optional[DocumentFormat] = None

class DocumentResponse(BaseModel):
    """文档响应模型"""
    id: str
    filename: str
    file_type: Optional[str] = None
    status: DocumentStatus
    error_message: Optional[str] = None
    segment_count: int
    word_count: int = 0
    token_count: int = 0
    enabled: bool = True
    archived: bool = False
    processing_time: Optional[float] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    
    class Config:
        from_attributes = True

class DocumentListResponse(BaseModel):
    """文档列表响应模型"""
    items: List[DocumentResponse]
    total: int

class DocumentBriefSchema(BaseModel):
    """文档简要信息模型，用于知识库关联展示"""
    id: str
    filename: str
    file_type: Optional[str] = None
    status: DocumentStatus
    segment_count: int
    word_count: int = 0
    token_count: int = 0
    enabled: bool = True
    
    class Config:
        from_attributes = True

class SegmentResponse(BaseModel):
    """段落响应模型"""
    id: str
    content: str
    meta_data: Dict[str, Any] = {}
    chunk_index: int
    enabled: bool
    status: str
    word_count: int = 0
    token_count: int = 0
    score: Optional[float] = None
    created_at: datetime.datetime
    
    class Config:
        from_attributes = True

class SegmentListResponse(BaseModel):
    """段落列表响应模型"""
    items: List[SegmentResponse]
    total: int

class SegmentUpdateRequest(BaseModel):
    """段落更新请求"""
    content: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None

class ChildChunkResponse(BaseModel):
    """子分块响应模型"""
    id: str
    segment_id: str
    content: str
    meta_data: Dict[str, Any] = {}
    tokens: Optional[int] = None
    enabled: bool
    status: str
    created_at: datetime.datetime
    
    class Config:
        from_attributes = True

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

def update_document_status(
    document_id: str, 
    status: DocumentStatus, 
    error_message: Optional[str] = None, 
    segment_count: Optional[int] = None, 
    word_count: Optional[int] = None,
    token_count: Optional[int] = None,
    db: Optional[Session] = None
) -> bool:
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
        
        # 更新时间戳
        now = datetime.datetime.utcnow()
        if status == DocumentStatus.PROCESSING and not document.processing_started_at:
            document.processing_started_at = now
        elif status == DocumentStatus.PARSING and not document.parsing_started_at:
            document.parsing_started_at = now
        elif status == DocumentStatus.SPLITTING and document.parsing_started_at and not document.parsing_completed_at:
            document.parsing_completed_at = now
            document.splitting_started_at = now
        elif status == DocumentStatus.INDEXING and document.splitting_started_at and not document.splitting_completed_at:
            document.splitting_completed_at = now
            document.indexing_started_at = now
        elif status == DocumentStatus.COMPLETED and document.indexing_started_at and not document.indexing_completed_at:
            document.indexing_completed_at = now
            document.processing_completed_at = now
        elif status == DocumentStatus.ERROR:
            document.processing_completed_at = now
        
        if error_message is not None:
            document.error_message = error_message
        if segment_count is not None:
            document.segment_count = segment_count
        if word_count is not None:
            document.word_count = word_count
        if token_count is not None:
            document.token_count = token_count
        
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"更新文档状态失败: {str(e)}")
        return False
    finally:
        if close_session:
            db.close()

def create_segment(segment_data: Dict[str, Any], db: Optional[Session] = None) -> Segment:
    """创建段落记录"""
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True
    
    try:
        if "meta_data" in segment_data and not isinstance(segment_data["meta_data"], str):
            segment_data["meta_data"] = json.dumps(segment_data["meta_data"])
            
        segment = Segment(**segment_data)
        db.add(segment)
        db.commit()
        db.refresh(segment)
        return segment
    except Exception as e:
        db.rollback()
        logger.error(f"创建段落记录失败: {str(e)}")
        raise
    finally:
        if close_session:
            db.close()

def update_segment(segment_id: str, update_data: Dict[str, Any], db: Optional[Session] = None) -> Optional[Segment]:
    """更新段落记录"""
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True
    
    try:
        segment = db.query(Segment).filter(Segment.id == segment_id).first()
        if not segment:
            return None
        
        if "meta_data" in update_data and not isinstance(update_data["meta_data"], str):
            update_data["meta_data"] = json.dumps(update_data["meta_data"])
            
        for key, value in update_data.items():
            setattr(segment, key, value)
        
        db.commit()
        db.refresh(segment)
        return segment
    except Exception as e:
        db.rollback()
        logger.error(f"更新段落记录失败: {str(e)}")
        return None
    finally:
        if close_session:
            db.close()

def generate_id():
    """生成唯一ID"""
    return str(uuid.uuid4())

# 知识库与文档关联表
knowledge_base_documents = Table(
    "knowledge_base_documents",
    Base.metadata,
    Column("knowledge_base_id", String(36), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), primary_key=True),
    Column("document_id", String(36), ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True)
)

class DocumentCreate(BaseModel):
    """文档创建请求模型"""
    filename: str = Field(..., description="文件名")
    file_path: str = Field(..., description="文件路径")
    file_type: str = Field(..., description="文件类型")
    file_size: int = Field(..., description="文件大小(字节)")
    content: Optional[str] = Field(None, description="文本内容")
    metadata: Optional[Dict[str, Any]] = Field(None, description="文件元数据")
    
    class Config:
        from_attributes = True

class DocumentUpdate(BaseModel):
    """文档更新请求模型"""
    filename: Optional[str] = Field(None, description="文件名")
    file_path: Optional[str] = Field(None, description="文件路径")
    file_type: Optional[str] = Field(None, description="文件类型")
    file_size: Optional[int] = Field(None, description="文件大小(字节)")
    content: Optional[str] = Field(None, description="文本内容")
    metadata: Optional[Dict[str, Any]] = Field(None, description="文件元数据")
    processed: Optional[bool] = Field(None, description="是否已处理")
    error: Optional[str] = Field(None, description="处理错误信息")
    
    class Config:
        from_attributes = True

class DocumentSchema(BaseModel):
    """文档响应模型"""
    id: str
    filename: str
    file_path: str
    file_type: str
    file_size: int
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    processed: bool
    error: Optional[str] = None
    created_by: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
