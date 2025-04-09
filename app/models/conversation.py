"""
对话管理模型
定义对话、消息和相关API请求响应模型
"""
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from uuid import uuid4, UUID

# 消息角色枚举
class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

# 对话状态枚举
class ConversationState(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"

# 基础消息模型
class MessageBase(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    role: MessageRole
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None

# 消息创建模型
class MessageCreate(BaseModel):
    role: MessageRole
    content: str
    metadata: Optional[Dict[str, Any]] = None

# 消息响应模型
class MessageSchema(MessageBase):
    conversation_id: str
    
    model_config = ConfigDict(from_attributes=True)

# 基础对话模型
class ConversationBase(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    state: ConversationState = ConversationState.ACTIVE
    metadata: Optional[Dict[str, Any]] = None

# 对话创建模型
class ConversationCreate(BaseModel):
    title: str
    metadata: Optional[Dict[str, Any]] = None

# 对话更新模型
class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    state: Optional[ConversationState] = None
    metadata: Optional[Dict[str, Any]] = None

# 对话响应模型（不包含消息）
class ConversationSchema(ConversationBase):
    message_count: int = 0
    
    model_config = ConfigDict(from_attributes=True)

# 对话详情响应模型（包含消息）
class ConversationDetailSchema(ConversationSchema):
    messages: List[MessageSchema] = []

# LLM配置模型
class LLMConfig(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    
    model_name: str = "gpt-3.5-turbo"
    temperature: float = 0.7
    top_p: float = 1.0
    max_tokens: Optional[int] = None
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0

# 对话生成请求模型
class ConversationGenerateRequest(BaseModel):
    conversation_id: str
    message: str
    knowledge_base_ids: Optional[List[str]] = None
    llm_config: Optional[LLMConfig] = None
    stream: bool = False
    
# 带知识库检索的消息生成请求
class RAGGenerateRequest(BaseModel):
    message: str
    knowledge_base_ids: List[str]
    conversation_id: Optional[str] = None
    llm_config: Optional[LLMConfig] = None
    stream: bool = False
    search_top_k: int = 5
    search_score_threshold: float = 0.5

# 消息生成响应
class GenerateResponse(BaseModel):
    conversation_id: str
    message: MessageSchema
    sources: Optional[List[Dict[str, Any]]] = None 