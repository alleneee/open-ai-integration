from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

# 注意: Langchain 0.0.x 可能需要 Pydantic V1。如果已更新到 V2, 请确保兼容。

class UploadResponse(BaseModel):
    """文件上传响应模型"""
    filename: str = Field(..., description="上传的文件名")
    message: str = Field(..., description="响应消息")
    document_id: Optional[str] = Field(None, description="处理/向量化成功后分配的文档ID") # 成功处理/向量化后分配的ID

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