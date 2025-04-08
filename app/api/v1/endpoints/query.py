from fastapi import APIRouter, HTTPException, status, Depends, Body
from typing import List, Optional

# Updated import paths
from app.schemas.schemas import RAGQueryRequest, RAGResult
from app.services.rag import perform_rag_query
# Remove dependencies if not used directly in the endpoint
# from app.api.dependencies import verify_milvus_connection

import logging
logger = logging.getLogger(__name__)

# REMOVED prefix from router definition
router = APIRouter()

@router.post(
    "/query", # Path relative to the router included in main.py
    response_model=RAGResult,
    summary="执行 RAG 查询 (Execute RAG Query)",
    description="""接收用户查询、可选的知识库名称、检索策略和对话历史，
                   使用 RAG 链生成答案并返回源文档。"""
    # Removed explicit responses, rely on default FastAPI/Starlette handling and exception handlers
)
async def query_rag(
    request: RAGQueryRequest = Body(...)
    # Example: Add dependency if needed, e.g. for auth or direct connection check
    # _=Depends(verify_milvus_connection)
):
    """
    处理 RAG 查询请求。
    """
    try:
        logger.info(f"路由 /query 收到请求: collection='{request.collection_name}', strategy='{request.retrieval_strategy}'", extra={"request_details": request.dict(exclude={'conversation_history'})})
        # Call the RAG service function
        result = await perform_rag_query(request)
        # perform_rag_query handles internal errors and returns RAGResult with error message
        return result
    except Exception as e:
        # Catch unexpected errors during request handling itself (outside RAG service)
        logger.exception(f"处理 /query 请求时发生意外错误: {e}")
        # Let the generic exception handler in main.py handle this
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理查询时发生意外服务器错误。"
        ) 