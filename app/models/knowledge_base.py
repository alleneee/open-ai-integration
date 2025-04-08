"""
知识库模型
定义与知识库相关的数据库模型
"""
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Column, String, DateTime, ForeignKey, Table, Boolean, Integer
from sqlalchemy.orm import relationship, mapped_column, Mapped

from app.models.database import Base
from app.models.document import Document

# 知识库与文档的多对多关联表
knowledge_base_document = Table(
    "knowledge_base_document",
    Base.metadata,
    Column("knowledge_base_id", String(36), ForeignKey("knowledge_bases.id")),
    Column("document_id", String(36), ForeignKey("documents.id")),
)


class KnowledgeBase(Base):
    """知识库模型"""
    __tablename__ = "knowledge_bases"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    vector_store: Mapped[str] = mapped_column(String(50), nullable=False, default="milvus")
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False, default="openai")
    
    # 分块策略
    chunk_size: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)
    chunk_overlap: Mapped[int] = mapped_column(Integer, nullable=False, default=200)
    chunking_strategy: Mapped[str] = mapped_column(String(50), nullable=False, default="paragraph")
    
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    
    # 与文档的多对多关系
    documents: Mapped[List["Document"]] = relationship(
        "Document", secondary=knowledge_base_document, backref="knowledge_bases"
    )
    
    # 与用户的多对一关系
    creator = relationship("User", backref="created_knowledge_bases")


# Pydantic 模型用于 API 请求和响应
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime


class KnowledgeBaseBase(BaseModel):
    """知识库基础信息模型"""
    name: str
    description: Optional[str] = None
    vector_store: str = "milvus"
    embedding_model: str = "openai"
    
    # 分块策略
    chunk_size: int = 1000
    chunk_overlap: int = 200
    chunking_strategy: str = "paragraph"


class KnowledgeBaseCreate(KnowledgeBaseBase):
    """创建知识库请求模型"""
    pass


class KnowledgeBaseUpdate(BaseModel):
    """更新知识库请求模型"""
    name: Optional[str] = None
    description: Optional[str] = None
    vector_store: Optional[str] = None
    embedding_model: Optional[str] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    chunking_strategy: Optional[str] = None
    is_active: Optional[bool] = None


class ChunkingConfig(BaseModel):
    """分块配置"""
    chunk_size: int
    chunk_overlap: int
    chunking_strategy: str
    rechunk_documents: bool = False
    
    @validator('chunk_size')
    def validate_chunk_size(cls, v):
        if v <= 0:
            raise ValueError('分块大小必须大于0')
        if v > 10000:
            raise ValueError('分块大小不能超过10000')
        return v
    
    @validator('chunk_overlap')
    def validate_chunk_overlap(cls, v, values):
        if v < 0:
            raise ValueError('分块重叠大小必须大于等于0')
        if 'chunk_size' in values and v >= values['chunk_size']:
            raise ValueError('分块重叠大小必须小于分块大小')
        return v
    
    @validator('chunking_strategy')
    def validate_chunking_strategy(cls, v):
        valid_strategies = ["paragraph", "token", "character", "markdown", "sentence"]
        if v not in valid_strategies:
            raise ValueError(f'无效的分块策略，有效的策略为: {", ".join(valid_strategies)}')
        return v


class KnowledgeBaseDocument(BaseModel):
    """知识库中的文档关联模型"""
    document_id: str


class KnowledgeBaseDocumentAdd(BaseModel):
    """向知识库添加文档的请求模型"""
    document_ids: List[str]


class KnowledgeBaseSchema(KnowledgeBaseBase):
    """知识库响应模型"""
    id: str
    is_active: bool
    chunk_size: int
    chunk_overlap: int
    chunking_strategy: str
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    
    class Config:
        from_attributes = True


class KnowledgeBaseDetailSchema(KnowledgeBaseSchema):
    """知识库详细信息响应模型，包含关联的文档"""
    documents: List["DocumentBriefSchema"] = []
    
    class Config:
        from_attributes = True


# 避免循环导入问题
from app.models.document import DocumentBriefSchema
KnowledgeBaseDetailSchema.model_rebuild()
