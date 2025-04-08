from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal

# 注意: Langchain 0.3.x 需要 Pydantic V2

class UploadResponse(BaseModel):
    """文件上传响应模型"""
    filename: str = Field(..., description="上传的文件名")
    message: str = Field(..., description="响应消息")
    document_id: Optional[str] = Field(None, description="处理/向量化成功后分配的文档ID") # 成功处理/向量化后分配的ID
    page: Optional[int] = None
    # 可以添加更多元数据字段

class AsyncTaskResponse(BaseModel):
    """异步任务响应模型"""
    message: str
    task_id: str
    filenames: List[str]
    collection_name: str

class QueryRequest(BaseModel):
    """查询请求模型"""
    query: str = Field(..., description="用户的查询语句")
    llm_provider: Optional[str] = Field(None, description="指定 LLM 提供商 (例如 'openai', 'deepseek', 'qwen') 或使用默认配置")
    top_k: int = Field(5, description="检索相关文档的数量")
    # 可根据需要添加其他参数, 如元数据过滤等

class DocumentSource(BaseModel):
    """文档来源信息模型"""
    filename: str = Field(..., description="来源文件名")
    page_number: Optional[int] = Field(None, description="页码 (如果适用)")
    score: float = Field(..., description="相关性得分")
    content_preview: str = Field(..., description="相关文本块的简短预览") # 相关块内容的简短预览

class QueryResponse(BaseModel):
    """查询响应模型"""
    answer: str = Field(..., description="生成的答案")
    sources: List[DocumentSource] = Field(..., description="答案依据的文档来源列表")
    llm_provider_used: str = Field(..., description="实际使用的 LLM 提供商")
    model_name_used: str = Field(..., description="实际使用的 LLM 模型名称")

# --- 错误响应模型 --- #

class ErrorDetail(BaseModel):
    """错误详情模型 (用于验证错误)"""
    loc: Optional[List[str]] = Field(None, description="错误发生的位置 (例如 ['body', 'query'])")
    msg: str = Field(..., description="错误信息")
    type: str = Field(..., description="错误类型")

class HTTPValidationError(BaseModel):
    """HTTP 验证错误响应模型 (FastAPI 默认使用)"""
    detail: List[ErrorDetail]

class GenericErrorResponse(BaseModel):
    """通用错误响应模型"""
    detail: str

class RAGResult(BaseModel):
    """RAG 查询结果模型"""
    answer: str
    source_documents: Optional[List[Dict[str, Any]]] = None

# --- 新增：对话消息模型 ---
class Message(BaseModel):
    """对话消息模型"""
    role: Literal["user", "assistant"]
    content: str

class RAGQueryRequest(BaseModel):
    """RAG 查询请求模型"""
    query: str
    collection_name: Optional[str] = None  # 允许指定知识库（Milvus Collection）
    retrieval_strategy: Literal["vector", "rerank", "hybrid"] = "vector" # 检索策略
    top_k: int = 5 # 检索文档数量
    rerank_top_n: Optional[int] = 3 # 重排后返回的文档数量 (仅当 strategy="rerank")
    conversation_history: Optional[List[Message]] = None # 对话历史
    # 可以添加更多检索参数，如相似度阈值等

# --- 新增：知识库管理模型 ---
class KnowledgeBaseCreateRequest(BaseModel):
    """创建知识库请求模型"""
    collection_name: str
    description: Optional[str] = None
    # 可以添加 schema 定义等参数

class KnowledgeBaseResponse(BaseModel):
    """知识库信息响应模型"""
    collection_name: str
    description: Optional[str] = None
    num_entities: Optional[int] = None # 向量数量
    # 可以添加更多信息

class KnowledgeBaseListResponse(BaseModel):
    """知识库列表响应模型"""
    collections: List[KnowledgeBaseResponse]

class DeleteResponse(BaseModel):
    """删除操作响应模型"""
    message: str 