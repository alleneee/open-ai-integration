"""
文档处理相关的 API 路由
提供文档上传、检索、管理等 RESTful 接口
"""
import os
import uuid
import tempfile
import logging
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, BackgroundTasks, Query, Path, status
from fastapi.responses import JSONResponse
from pydantic import UUID4
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_tenant_id
from app.models.document import (
    DocumentModel, DocumentResponse, DocumentListResponse, 
    DocumentStatus, Document, get_document_by_id,
    list_documents, create_document
)
from app.services.parser import parse_uploaded_file_and_split
from app.services.vector_store import get_retriever
from app.task.document_tasks import (
    document_indexing_task, retry_document_indexing_task,
    batch_delete_document_task
)
from app.services.document_processor import document_processor

logger = logging.getLogger(__name__)

# 移除前缀，将由router.py中的include_router设置
router = APIRouter()

@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    collection_name: str = Form(...),
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db),
    chunk_size: int = Query(1000, description="文本块大小"),
    chunk_overlap: int = Query(150, description="文本块重叠大小")
):
    """
    上传文档并异步处理
    
    上传的文档将被解析、分块并存储到向量数据库中
    文档处理是异步进行的，API 会立即返回文档ID和状态信息
    """
    try:
        # 1. 解析上传的文件
        document_chunks, temp_file_path = await parse_uploaded_file_and_split(
            file=file,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        if not document_chunks:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="无法从文档中提取内容"
            )
            
        # 2. 创建文档记录
        document_id = str(uuid.uuid4())
        document_data = {
            "id": document_id,
            "tenant_id": tenant_id,
            "collection_name": collection_name,
            "filename": file.filename,
            "file_path": temp_file_path,
            "file_size": os.path.getsize(temp_file_path),
            "file_type": file.content_type,
            "status": DocumentStatus.PENDING,
            "segment_count": 0
        }
        
        document = create_document(document_data, db=db)
        
        # 3. 启动异步处理任务
        document_indexing_task.delay(
            document_id=document_id,
            file_path=temp_file_path,
            filename=file.filename,
            collection_name=collection_name,
            tenant_id=tenant_id
        )
        
        logger.info(f"文档 {file.filename} (ID: {document_id}) 已提交处理")
        
        return DocumentResponse(
            id=document.id,
            filename=document.filename,
            status=document.status,
            error_message=document.error_message,
            segment_count=document.segment_count,
            created_at=document.created_at,
            updated_at=document.updated_at
        )
        
    except HTTPException:
        # 传递 FastAPI 的 HTTPException
        raise
    except Exception as e:
        logger.exception(f"处理文档上传时出错: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理文档上传时出错: {str(e)}"
        )

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str = Path(..., description="文档ID"),
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    """
    获取指定文档的详细信息
    """
    document = get_document_by_id(document_id, db=db)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在"
        )
        
    if document.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此文档"
        )
        
    return DocumentResponse.from_orm(document)

@router.get("/", response_model=DocumentListResponse)
async def list_tenant_documents(
    tenant_id: str = Depends(get_current_tenant_id),
    collection_name: Optional[str] = Query(None, description="知识库名称"),
    status: Optional[DocumentStatus] = Query(None, description="文档状态"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """
    列出租户的所有文档
    """
    skip = (page - 1) * page_size
    
    documents, total = list_documents(
        tenant_id=tenant_id,
        collection_name=collection_name,
        status=status,
        skip=skip,
        limit=page_size,
        db=db
    )
    
    items = [DocumentResponse.from_orm(doc) for doc in documents]
    
    return DocumentListResponse(
        items=items,
        total=total
    )

@router.post("/{document_id}/retry", response_model=Dict[str, Any])
async def retry_document_indexing(
    document_id: str = Path(..., description="文档ID"),
    tenant_id: str = Depends(get_current_tenant_id),
    db: Session = Depends(get_db)
):
    """
    重试失败的文档索引
    """
    document = get_document_by_id(document_id, db=db)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在"
        )
        
    if document.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此文档"
        )
        
    if document.status != DocumentStatus.ERROR:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只能重试错误状态的文档"
        )
        
    # 启动异步重试任务
    retry_document_indexing_task.delay(document_id=document_id)
    
    return {
        "message": "文档索引重试任务已启动",
        "document_id": document_id
    }

@router.delete("/{document_id}", response_model=Dict[str, Any])
async def delete_document(
    document_id: str = Path(..., description="文档ID"),
    tenant_id: str = Depends(get_current_tenant_id),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    删除文档及其所有段落
    """
    document = get_document_by_id(document_id, db=db)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在"
        )
        
    if document.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权删除此文档"
        )
    
    # 在后台任务中删除文档
    batch_delete_document_task.delay(
        document_ids=[document_id],
        collection_name=document.collection_name
    )
    
    return {
        "message": "文档删除任务已启动",
        "document_id": document_id
    }

@router.delete("/batch", response_model=Dict[str, Any])
async def batch_delete_documents(
    document_ids: List[str],
    tenant_id: str = Depends(get_current_tenant_id),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    批量删除文档及其所有段落
    """
    if not document_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="至少需要提供一个文档ID"
        )
    
    valid_document_ids = []
    collection_name = None
    
    # 验证所有文档是否存在且用户有权限
    for doc_id in document_ids:
        document = get_document_by_id(doc_id, db=db)
        
        if not document:
            logger.warning(f"文档 {doc_id} 不存在，将跳过")
            continue
        
        if document.tenant_id != tenant_id:
            logger.warning(f"无权访问文档 {doc_id}，将跳过")
            continue
        
        valid_document_ids.append(doc_id)
        
        # 获取集合名称（假设所有文档都在同一个集合中）
        if not collection_name:
            collection_name = document.collection_name
    
    if not valid_document_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有找到有效的文档或无权限访问提供的文档"
        )
    
    # 在后台任务中删除文档
    batch_delete_document_task.delay(
        document_ids=valid_document_ids,
        collection_name=collection_name
    )
    
    return {
        "message": f"批量文档删除任务已启动，处理 {len(valid_document_ids)} 个文档",
        "document_ids": valid_document_ids
    } 