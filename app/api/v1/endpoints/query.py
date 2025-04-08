from fastapi import APIRouter, HTTPException, status, Depends, Body
from typing import List, Optional, Annotated

# Updated import paths
from app.schemas.schemas import RAGQueryRequest, RAGResult
from app.services.rag import perform_rag_query
# Remove dependencies if not used directly in the endpoint
# from app.api.dependencies import verify_milvus_connection
from app.core.config import settings # If needed for other dependencies

import logging
logger = logging.getLogger(__name__)

# REMOVED prefix from router definition
router = APIRouter()

@router.post(
    "", # Path relative to the prefix in api/v1/router.py
    response_model=RAGResult,
    summary="Perform RAG Query",
    description="Send a query to the RAG system, optionally specifying a knowledge base and retrieval strategy.",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Validation error"}
    }
)
async def query_rag(
    request: Annotated[RAGQueryRequest, Body(..., description="RAG query details including session ID")]
):
    """
    处理 RAG 查询请求:

    - **session_id**: 用于跟踪对话的唯一标识符。
    - **query**: 用户的查询文本。
    - **collection_name**: (可选) 要查询的特定知识库名称。如果未提供，则使用默认知识库。
    - **retrieval_strategy**: (可选) 检索策略 ('vector', 'rerank', 'hybrid'). 默认为 'vector'。
    - **top_k**: (可选) 检索的相关文档数量。
    - **rerank_top_n**: (可选) 在 'rerank' 策略中，重排后返回的文档数量。
    """
    logger.info(f"Received RAG query request for session {request.session_id}")
    
    try:
        # perform_rag_query now takes the request object directly
        result = await perform_rag_query(request)
        # perform_rag_query handles internal errors and returns RAGResult with error message
        return result
    except Exception as e:
        # This is a fallback for unexpected errors *before* calling perform_rag_query
        logger.exception(f"Unexpected error processing RAG request for session {request.session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}"
        ) 