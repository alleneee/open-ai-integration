"""
知识库模型
定义与知识库相关的数据库模型
"""
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
import json

from sqlalchemy import Column, String, DateTime, ForeignKey, Table, Boolean, Integer, Text, Enum as SQLAlchemyEnum, JSON
from sqlalchemy.orm import relationship, mapped_column, Mapped
from sqlalchemy.dialects.postgresql import JSONB
from pydantic import BaseModel, Field, validator

from app.models.database import Base
from app.models.document import Document, DocumentResponse

# 添加 ChunkingConfig 类
class ChunkingConfig(BaseModel):
    """文本分块配置"""
    chunk_size: int = Field(1000, ge=50, le=4000, description="分块大小")
    chunk_overlap: int = Field(200, ge=0, le=500, description="分块重叠大小")
    chunking_strategy: str = Field("recursive", description="分块策略")
    
    class Config:
        from_attributes = True

# 添加 KnowledgeBaseDocumentAdd 类
class KnowledgeBaseDocumentAdd(BaseModel):
    """知识库添加文档的请求模型"""
    document_ids: List[str] = Field(..., description="文档ID列表")
    chunking_config: Optional[ChunkingConfig] = None
    
    class Config:
        from_attributes = True

class ChunkingStrategy(str, Enum):
    """文本分块策略枚举"""
    RECURSIVE = "recursive"
    FIXED_SIZE = "fixed_size"
    SEMANTIC = "semantic"
    CUSTOM = "custom"


class DatasetPermissionEnum(str, Enum):
    """知识库权限枚举"""
    ONLY_ME = "only_me"  # 仅创建者
    ALL_TEAM = "all_team_members"  # 所有团队成员
    PARTIAL_TEAM = "partial_members"  # 指定团队成员


class RetrievalMethod(str, Enum):
    """检索方法枚举"""
    SEMANTIC_SEARCH = "semantic_search"  # 语义检索
    KEYWORD_SEARCH = "keyword_search"    # 关键词检索
    HYBRID_SEARCH = "hybrid_search"      # 混合检索

# 知识库表定义
class KnowledgeBaseDB(Base):
    """知识库数据库模型"""
    __tablename__ = "knowledge_bases"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    meta_data = Column(JSON, nullable=True)
    
    tenant_id = Column(String(36), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    chunk_size = Column(Integer, default=1000, nullable=False)
    chunk_overlap = Column(Integer, default=200, nullable=False)
    chunking_strategy = Column(SQLAlchemyEnum(ChunkingStrategy), default=ChunkingStrategy.RECURSIVE, nullable=False)
    
    created_by = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联文档
    documents = relationship("Document", secondary="knowledge_base_document", back_populates="knowledge_bases")
    
    built_in_field_enabled = Column(Boolean, default=False, nullable=False)

# 知识库与文档的多对多关联表
knowledge_base_document = Table(
    "knowledge_base_document",
    Base.metadata,
    Column("knowledge_base_id", String(36), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), primary_key=True),
    Column("document_id", String(36), ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True),
    extend_existing=True
)


class KnowledgeBaseBase(BaseModel):
    """知识库基础模型"""
    name: str = Field(..., description="知识库名称")
    description: Optional[str] = Field(None, description="知识库描述")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="知识库元数据")


class KnowledgeBaseCreate(KnowledgeBaseBase):
    """创建知识库的请求模型"""
    created_by: Optional[str] = Field(None, description="创建者ID")


class KnowledgeBaseUpdate(BaseModel):
    """更新知识库的请求模型"""
    description: Optional[str] = Field(None, description="知识库描述")
    metadata: Optional[Dict[str, Any]] = Field(None, description="知识库元数据")


class KnowledgeBase(KnowledgeBaseBase):
    """知识库完整模型"""
    id: str = Field(..., description="知识库ID")
    document_count: int = Field(0, description="知识库中的文档数量")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="最后更新时间")
    created_by: Optional[str] = Field(None, description="创建者ID")

    class Config:
        orm_mode = True


class KnowledgeBaseDocument(BaseModel):
    """知识库文档关联模型"""
    kb_id: str = Field(..., description="知识库ID")
    document_id: str = Field(..., description="文档ID")
    added_at: datetime = Field(..., description="添加时间")

    class Config:
        orm_mode = True


class KnowledgeBaseStats(BaseModel):
    """知识库统计信息模型"""
    id: str = Field(..., description="知识库ID")
    name: str = Field(..., description="知识库名称")
    document_count: int = Field(0, description="知识库中的文档数量")
    vector_count: int = Field(0, description="向量存储中的向量数量")
    last_updated: Optional[datetime] = Field(None, description="最后更新时间")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="知识库元数据")


# 子分块表定义
class ChildChunk(Base):
    """子分块模型，用于存储段落的进一步分割"""
    __tablename__ = "child_chunks"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    segment_id: Mapped[str] = mapped_column(String(36), ForeignKey("segments.id", ondelete="CASCADE"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    meta_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tokens: Mapped[int] = mapped_column(Integer, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    embedding_vector: Mapped[Optional[Any]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    
    # 关系定义
    segment = relationship("Segment", back_populates="child_chunks")
    
    @property
    def meta_data_dict(self) -> Dict[str, Any]:
        """获取元数据字典"""
        return json.loads(self.meta_data) if self.meta_data else {}


# 知识库权限表
class KnowledgeBasePermission(Base):
    """知识库权限模型，用于存储部分用户的访问权限"""
    __tablename__ = "knowledge_base_permissions"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    knowledge_base_id: Mapped[str] = mapped_column(String(36), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    
    # 关系定义
    knowledge_base = relationship("KnowledgeBaseDB")
    user = relationship("User")


# Pydantic 模型用于 API 请求和响应


class KnowledgeBaseSchema(KnowledgeBaseBase):
    """知识库响应模型"""
    id: str
    is_active: bool
    chunk_size: int
    chunk_overlap: int
    chunking_strategy: ChunkingStrategy
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    built_in_field_enabled: bool = False
    
    class Config:
        from_attributes = True


class KnowledgeBaseDetailSchema(KnowledgeBaseSchema):
    """知识库详细信息响应模型，包含关联的文档"""
    documents: List["DocumentBriefSchema"] = []
    retrieval_model: Optional[Dict[str, Any]] = None
    document_stats: Optional[Dict[str, int]] = None
    
    class Config:
        from_attributes = True


# 避免循环导入问题
from app.models.document import DocumentBriefSchema, DocumentStatus, Segment
KnowledgeBaseDetailSchema.model_rebuild()


class KnowledgeBaseResponse(KnowledgeBaseBase):
    """知识库响应模型"""
    id: str
    created_at: str
    updated_at: str
    retrieval_model: Optional[Dict[str, Any]] = None
    built_in_field_enabled: bool = False
    
    class Config:
        orm_mode = True


class KnowledgeBaseWithStats(KnowledgeBaseResponse):
    """带统计信息的知识库模型"""
    document_stats: Dict[str, int] = Field(
        default_factory=lambda: {
            "total": 0,
            "pending": 0,
            "processing": 0,
            "completed": 0,
            "error": 0
        }
    )
    embedding_available: bool = True


class KnowledgeBaseDetail(KnowledgeBaseWithStats):
    """知识库详细信息模型，包含更多信息"""
    documents: List[DocumentBriefSchema] = []
    retrieval_model: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class KnowledgeBaseList(BaseModel):
    """知识库列表模型"""
    total: int
    items: List[KnowledgeBaseWithStats]
    
    class Config:
        orm_mode = True


class ChildChunkSchema(BaseModel):
    """子分块响应模型"""
    id: str
    segment_id: str
    content: str
    meta_data: Optional[Dict[str, Any]] = None
    tokens: Optional[int] = None
    enabled: bool
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class KnowledgeBasePermissionSchema(BaseModel):
    """知识库权限响应模型"""
    user_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# 知识库权限请求模型
class GrantPermissionRequest(BaseModel):
    """授予权限请求模型"""
    user_id: str = Field(..., description="用户ID")
    
    class Config:
        from_attributes = True


class RevokePermissionRequest(BaseModel):
    """撤销权限请求模型"""
    user_id: str = Field(..., description="用户ID")
    
    class Config:
        from_attributes = True
