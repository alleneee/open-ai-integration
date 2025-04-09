"""
知识库管理API
提供知识库的创建、查询、更新和删除等功能
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, BackgroundTasks
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseSchema,
    KnowledgeBaseDetailSchema,
    KnowledgeBaseDocumentAdd,
    ChunkingConfig
)
from app.services.knowledge_base import knowledge_base_service

router = APIRouter()


@router.post(
    "/", 
    response_model=KnowledgeBaseSchema, 
    status_code=status.HTTP_201_CREATED,
    summary="创建知识库"
)
async def create_knowledge_base(
    kb_create: KnowledgeBaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建新的知识库
    
    - **name**: 知识库名称（必填）
    - **description**: 知识库描述（可选）
    - **vector_store**: 向量存储类型，默认为milvus
    - **embedding_model**: 嵌入模型，默认为openai
    
    创建后的知识库同时会在向量存储中建立对应的集合，准备接收文档。
    """
    try:
        kb = knowledge_base_service.create_knowledge_base(
            db=db, 
            kb_create=kb_create, 
            user_id=current_user.id
        )
        return kb
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception(f"创建知识库失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建知识库失败: {str(e)}"
        )


@router.get(
    "/", 
    response_model=List[KnowledgeBaseSchema],
    summary="获取知识库列表"
)
async def get_knowledge_bases(
    skip: int = Query(0, ge=0, description="分页起始位置"),
    limit: int = Query(100, ge=1, le=500, description="分页大小"),
    my_only: bool = Query(False, description="是否只显示我创建的知识库"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取知识库列表，支持分页和筛选
    
    - 可选参数 **my_only**: 设置为true时只返回当前用户创建的知识库
    """
    user_id = current_user.id if my_only else None
    kbs = knowledge_base_service.get_knowledge_bases(
        db=db, 
        skip=skip, 
        limit=limit,
        user_id=user_id
    )
    return kbs


@router.get(
    "/{kb_id}", 
    response_model=KnowledgeBaseDetailSchema,
    summary="获取知识库详情"
)
async def get_knowledge_base(
    kb_id: str = Path(..., description="知识库ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取指定知识库的详细信息，包括关联的文档
    """
    kb = knowledge_base_service.get_knowledge_base_with_documents(db=db, kb_id=kb_id)
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="知识库未找到"
        )
    return kb 