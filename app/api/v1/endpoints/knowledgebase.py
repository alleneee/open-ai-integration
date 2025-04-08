# app/api/v1/endpoints/knowledgebase.py

from fastapi import APIRouter, HTTPException, status, Depends, Body
from typing import List, Optional

# Updated import paths
from app.schemas.schemas import (
    KnowledgeBaseCreateRequest, KnowledgeBaseResponse, KnowledgeBaseListResponse, DeleteResponse
)
from app.services.vector_store import (
    create_knowledge_base as create_kb,
    list_knowledge_bases as list_kbs,
    get_knowledge_base as get_kb_info,
    delete_knowledge_base as delete_kb,
)
# Optional: Import dependency to verify connection
from app.api.dependencies import verify_milvus_connection

import logging
logger = logging.getLogger(__name__)

# REMOVED prefix from router definition
router = APIRouter()

@router.post(
    "/", # Path relative to prefix defined in v1/router.py (e.g., /knowledgebases/)
    response_model=KnowledgeBaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建知识库 (Create Knowledge Base)",
    description="在 Milvus 中创建一个新的 Collection 作为知识库。",
    dependencies=[Depends(verify_milvus_connection)] # Example: Ensure connection before creating
)
async def create_knowledge_base_endpoint(
    request: KnowledgeBaseCreateRequest = Body(...)
):
    """
    创建知识库 (Milvus Collection)。
    """
    try:
        logger.info(f"收到创建知识库请求: name='{request.collection_name}'", extra={"collection_name": request.collection_name})
        existing_kb = get_kb_info(request.collection_name)
        if existing_kb:
            logger.warning(f"尝试创建已存在的知识库 '{request.collection_name}'")
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"知识库 '{request.collection_name}' 已存在。")
        success = create_kb(request.collection_name, request.description)
        if success:
            kb_info = get_kb_info(request.collection_name)
            if kb_info:
                 logger.info(f"知识库 '{request.collection_name}' 创建成功。", extra={"kb_info": kb_info.dict()})
                 return kb_info
            else:
                 logger.error(f"知识库 '{request.collection_name}' 创建后无法获取信息。")
                 raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="知识库可能已创建但无法立即获取其信息。")
        else:
             logger.error(f"创建知识库 '{request.collection_name}' 在 vector_store 层面失败。")
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"创建知识库 '{request.collection_name}' 失败。请检查服务日志。")
    except ConnectionError as ce: # Catch ConnectionError specifically if verify_milvus_connection isn't used
         logger.error(f"创建知识库时连接 Milvus 失败: {ce}")
         raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"无法连接到向量数据库: {ce}")
    except HTTPException as http_exc: raise http_exc
    except Exception as e:
        logger.exception(f"创建知识库 '{request.collection_name}' 时发生未处理错误: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"创建知识库时发生服务器内部错误: {e}")

@router.get(
    "/", # Path relative to prefix (e.g., /knowledgebases/)
    response_model=KnowledgeBaseListResponse,
    summary="列出所有知识库 (List Knowledge Bases)",
    description="获取系统中所有可用的知识库 (Milvus Collections) 列表及其基本信息。",
    dependencies=[Depends(verify_milvus_connection)]
)
async def list_knowledge_bases_endpoint():
    """获取所有知识库的列表。"""
    try:
        logger.info("收到列出知识库请求")
        collections = list_kbs()
        logger.info(f"找到 {len(collections)} 个知识库。")
        return KnowledgeBaseListResponse(collections=collections)
    except ConnectionError as ce:
         logger.error(f"列出知识库时连接 Milvus 失败: {ce}")
         raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"无法连接到向量数据库: {ce}")
    except Exception as e:
        logger.exception(f"列出知识库时发生错误: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"列出知识库时发生服务器内部错误: {e}")

@router.get(
    "/{collection_name}", # Path relative to prefix (e.g., /knowledgebases/{name})
    response_model=KnowledgeBaseResponse,
    summary="获取知识库信息 (Get Knowledge Base Info)",
    description="获取指定知识库的详细信息，如描述和向量数量。",
    dependencies=[Depends(verify_milvus_connection)]
)
async def get_knowledge_base_info_endpoint(collection_name: str):
    """获取单个知识库的详细信息。"""
    try:
        logger.info(f"收到获取知识库信息请求: name='{collection_name}'", extra={"collection_name": collection_name})
        info = get_kb_info(collection_name)
        if info:
            logger.info(f"成功获取知识库 '{collection_name}' 的信息。", extra={"kb_info": info.dict()})
            return info
        else:
            logger.warning(f"请求的知识库 '{collection_name}' 未找到或获取信息时出错。")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"知识库 '{collection_name}' 未找到或无法访问。")
    except ConnectionError as ce:
         logger.error(f"获取知识库 '{collection_name}' 信息时连接 Milvus 失败: {ce}")
         raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"无法连接到向量数据库: {ce}")
    except Exception as e:
        logger.exception(f"获取知识库 '{collection_name}' 信息时发生错误: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"获取知识库 '{collection_name}' 信息时发生服务器内部错误: {e}")

@router.delete(
    "/{collection_name}", # Path relative to prefix (e.g., /knowledgebases/{name})
    response_model=DeleteResponse,
    summary="删除知识库 (Delete Knowledge Base)",
    description="永久删除指定的知识库及其所有数据。这是一个不可逆的操作！",
    dependencies=[Depends(verify_milvus_connection)]
)
async def delete_knowledge_base_endpoint(collection_name: str):
    """删除一个知识库。"""
    try:
        logger.warning(f"收到删除知识库请求: name='{collection_name}' - 这是一个危险操作！", extra={"collection_name": collection_name})
        info = get_kb_info(collection_name) # Check existence first
        if not info:
             logger.warning(f"尝试删除不存在的知识库 '{collection_name}'")
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"无法删除：知识库 '{collection_name}' 未找到。")
        success = delete_kb(collection_name)
        if success:
            logger.info(f"知识库 '{collection_name}' 已成功删除。")
            return DeleteResponse(message=f"知识库 '{collection_name}' 已成功删除。")
        else:
             logger.error(f"删除知识库 '{collection_name}' 在 vector_store 层面失败。")
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"删除知识库 '{collection_name}' 时发生内部错误。请检查服务日志。")
    except ConnectionError as ce:
         logger.error(f"删除知识库 '{collection_name}' 时连接 Milvus 失败: {ce}")
         raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"无法连接到向量数据库: {ce}")
    except HTTPException as http_exc: raise http_exc
    except Exception as e:
        logger.exception(f"删除知识库 '{collection_name}' 时发生未处理错误: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"删除知识库时发生服务器内部错误: {e}") 