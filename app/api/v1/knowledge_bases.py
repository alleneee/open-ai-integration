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
    """
    kb = knowledge_base_service.create_knowledge_base(
        db=db, 
        kb_create=kb_create, 
        user_id=current_user.id
    )
    return kb


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


@router.put(
    "/{kb_id}", 
    response_model=KnowledgeBaseSchema,
    summary="更新知识库"
)
async def update_knowledge_base(
    kb_update: KnowledgeBaseUpdate,
    kb_id: str = Path(..., description="知识库ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新知识库信息
    
    - **name**: 知识库名称（可选）
    - **description**: 知识库描述（可选）
    - **vector_store**: 向量存储类型（可选）
    - **embedding_model**: 嵌入模型（可选）
    - **is_active**: 是否激活（可选）
    """
    # 先检查知识库是否存在
    kb = knowledge_base_service.get_knowledge_base(db=db, kb_id=kb_id)
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="知识库未找到"
        )
    
    # TODO: 权限检查，例如只有创建者或管理员可以更新
    
    updated_kb = knowledge_base_service.update_knowledge_base(
        db=db, 
        kb_id=kb_id, 
        kb_update=kb_update
    )
    return updated_kb


@router.delete(
    "/{kb_id}", 
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除知识库"
)
async def delete_knowledge_base(
    kb_id: str = Path(..., description="知识库ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除指定知识库
    """
    # 先检查知识库是否存在
    kb = knowledge_base_service.get_knowledge_base(db=db, kb_id=kb_id)
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="知识库未找到"
        )
    
    # TODO: 权限检查，例如只有创建者或管理员可以删除
    
    result = knowledge_base_service.delete_knowledge_base(db=db, kb_id=kb_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除知识库失败"
        )


@router.post(
    "/{kb_id}/documents", 
    response_model=KnowledgeBaseDetailSchema,
    summary="向知识库添加文档"
)
async def add_documents_to_knowledge_base(
    doc_add: KnowledgeBaseDocumentAdd,
    kb_id: str = Path(..., description="知识库ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    向知识库添加一个或多个文档
    
    - **document_ids**: 文档ID列表
    """
    # 先检查知识库是否存在
    kb = knowledge_base_service.get_knowledge_base(db=db, kb_id=kb_id)
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="知识库未找到"
        )
    
    # TODO: 权限检查
    
    updated_kb = knowledge_base_service.add_documents_to_knowledge_base(
        db=db, 
        kb_id=kb_id, 
        document_ids=doc_add.document_ids
    )
    return updated_kb


@router.delete(
    "/{kb_id}/documents/{document_id}", 
    response_model=KnowledgeBaseDetailSchema,
    summary="从知识库移除文档"
)
async def remove_document_from_knowledge_base(
    kb_id: str = Path(..., description="知识库ID"),
    document_id: str = Path(..., description="文档ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    从知识库移除指定文档
    """
    # 先检查知识库是否存在
    kb = knowledge_base_service.get_knowledge_base(db=db, kb_id=kb_id)
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="知识库未找到"
        )
    
    # TODO: 权限检查
    
    updated_kb = knowledge_base_service.remove_document_from_knowledge_base(
        db=db, 
        kb_id=kb_id, 
        document_id=document_id
    )
    return updated_kb


@router.put(
    "/{kb_id}/chunking-config", 
    response_model=KnowledgeBaseSchema,
    summary="更新知识库分块策略"
)
async def update_chunking_config(
    chunking_config: ChunkingConfig,
    kb_id: str = Path(..., description="知识库ID"),
    background_tasks: BackgroundTasks = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新知识库的分块策略，并可选择重新处理所有文档
    
    - **chunk_size**: 分块大小（字符数）
    - **chunk_overlap**: 分块重叠大小
    - **chunking_strategy**: 分块策略，支持 "paragraph", "token", "character", "markdown"
    - **rechunk_documents**: 是否重新处理知识库中的所有文档
    """
    # 先检查知识库是否存在
    kb = knowledge_base_service.get_knowledge_base(db=db, kb_id=kb_id)
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="知识库未找到"
        )
    
    # 检查分块策略是否有效
    valid_strategies = ["paragraph", "token", "character", "markdown"]
    if chunking_config.chunking_strategy not in valid_strategies:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的分块策略，支持的策略有: {', '.join(valid_strategies)}"
        )
    
    # TODO: 权限检查
    
    # 如果需要重新处理文档，使用后台任务
    if chunking_config.rechunk_documents:
        background_tasks.add_task(
            knowledge_base_service.update_chunking_config,
            db=db,
            kb_id=kb_id,
            config=chunking_config
        )
        return kb  # 立即返回当前知识库状态
    else:
        # 否则直接更新分块策略
        updated_kb = await knowledge_base_service.update_chunking_config(
            db=db,
            kb_id=kb_id,
            config=chunking_config
        )
        return updated_kb


@router.post(
    "/{kb_id}/documents/{document_id}/rechunk",
    response_model=KnowledgeBaseDetailSchema,
    summary="重新处理单个文档"
)
async def rechunk_single_document(
    kb_id: str = Path(..., description="知识库ID"),
    document_id: str = Path(..., description="文档ID"),
    background_tasks: BackgroundTasks = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    使用知识库当前的分块策略重新处理单个文档
    """
    # 先检查知识库是否存在
    kb = knowledge_base_service.get_knowledge_base(db=db, kb_id=kb_id)
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="知识库未找到"
        )
    
    # 检查文档是否存在于知识库中
    document_found = False
    for doc in kb.documents:
        if doc.id == document_id:
            document_found = True
            break
    
    if not document_found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不在该知识库中"
        )
    
    # 添加后台任务来重新处理文档
    from app.services.document_processor import document_processor
    background_tasks.add_task(
        document_processor.rechunk_document,
        db=db,
        document_id=document_id,
        chunk_size=kb.chunk_size,
        chunk_overlap=kb.chunk_overlap,
        chunking_strategy=kb.chunking_strategy
    )
    
    return knowledge_base_service.get_knowledge_base_with_documents(db=db, kb_id=kb_id)


@router.get(
    "/{kb_id}/chunking-status",
    response_model=Dict[str, Any],
    summary="获取知识库文档分块状态"
)
async def get_chunking_status(
    kb_id: str = Path(..., description="知识库ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取知识库中所有文档的分块处理状态
    
    返回:
    - total_documents: 文档总数
    - completed: 已完成分块的文档数
    - pending: 待处理的文档数
    - processing: 处理中的文档数
    - error: 处理失败的文档数
    - documents: 文档处理状态列表
    """
    # 检查知识库是否存在
    kb = knowledge_base_service.get_knowledge_base(db=db, kb_id=kb_id)
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="知识库未找到"
        )
    
    # 获取知识库中所有文档的状态
    documents = db.query(Document).join(
        knowledge_base_documents,
        knowledge_base_documents.c.document_id == Document.id
    ).filter(
        knowledge_base_documents.c.knowledge_base_id == kb_id
    ).all()
    
    # 统计不同状态的文档数量
    status_counts = {
        "total_documents": len(documents),
        "completed": 0,
        "pending": 0,
        "processing": 0,
        "error": 0
    }
    
    # 文档详情列表
    doc_status_list = []
    
    for doc in documents:
        # 更新状态计数
        if doc.status == DocumentStatus.COMPLETED.value:
            status_counts["completed"] += 1
        elif doc.status == DocumentStatus.PENDING.value:
            status_counts["pending"] += 1
        elif doc.status == DocumentStatus.PROCESSING.value:
            status_counts["processing"] += 1
        elif doc.status == DocumentStatus.ERROR.value:
            status_counts["error"] += 1
        
        # 添加文档状态信息
        doc_status_list.append({
            "id": doc.id,
            "name": doc.name,
            "status": doc.status,
            "segment_count": doc.segment_count,
            "error_message": doc.error_message,
            "updated_at": doc.updated_at.isoformat() if doc.updated_at else None
        })
    
    # 计算处理进度百分比
    if status_counts["total_documents"] > 0:
        status_counts["progress_percentage"] = round(
            (status_counts["completed"] / status_counts["total_documents"]) * 100, 2
        )
    else:
        status_counts["progress_percentage"] = 100.0
    
    return {
        **status_counts,
        "documents": doc_status_list
    }


@router.post(
    "/{kb_id}/rechunk-all",
    response_model=Dict[str, Any],
    summary="重新处理知识库所有文档"
)
async def rechunk_all_documents(
    kb_id: str = Path(..., description="知识库ID"),
    background_tasks: BackgroundTasks = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    使用知识库当前的分块策略重新处理所有文档
    
    返回:
    - message: 操作结果消息
    - total_documents: 将被重新处理的文档总数
    """
    # 检查知识库是否存在
    kb = knowledge_base_service.get_knowledge_base(db=db, kb_id=kb_id)
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="知识库未找到"
        )
    
    # 获取知识库中所有文档
    documents = db.query(Document).join(
        knowledge_base_documents,
        knowledge_base_documents.c.document_id == Document.id
    ).filter(
        knowledge_base_documents.c.knowledge_base_id == kb_id
    ).all()
    
    document_ids = [doc.id for doc in documents]
    
    if not document_ids:
        return {
            "message": "知识库中没有文档需要处理",
            "total_documents": 0
        }
    
    # 创建分块配置对象
    chunking_config = ChunkingConfig(
        chunk_size=kb.chunk_size,
        chunk_overlap=kb.chunk_overlap,
        chunking_strategy=kb.chunking_strategy,
        rechunk_documents=True
    )
    
    # 添加后台任务重新处理所有文档
    background_tasks.add_task(
        knowledge_base_service.update_chunking_config,
        db=db,
        kb_id=kb_id,
        config=chunking_config
    )
    
    return {
        "message": f"已安排重新处理 {len(document_ids)} 个文档的后台任务",
        "total_documents": len(document_ids)
    }


@router.delete(
    "/chunking-cache",
    response_model=Dict[str, Any],
    summary="清除分块缓存"
)
async def clear_chunking_cache(
    document_id: Optional[str] = Query(None, description="指定文档ID，不提供则清除所有缓存"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    清除文档分块缓存，可指定清除特定文档的缓存或全部缓存
    
    - **document_id**: 可选，指定要清除缓存的文档ID
    
    返回:
    - cleared_count: 清除的缓存文件数量
    """
    from app.services.document_chunker import document_chunker
    
    # 如果提供了文档ID，获取文档路径
    document_path = None
    if document_id:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文档未找到"
            )
        document_path = document.file_path
    
    # 清除缓存
    cleared_count = document_chunker.clear_cache(document_path)
    
    return {
        "message": f"已清除 {cleared_count} 个缓存文件",
        "cleared_count": cleared_count
    }


@router.post(
    "/{kb_id}/rebuild-index",
    response_model=Dict[str, Any],
    summary="重建知识库索引"
)
async def rebuild_knowledge_base_index(
    kb_id: str = Path(..., description="知识库ID"),
    background_tasks: BackgroundTasks = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    重建知识库的向量索引，会重新处理所有文档并更新向量存储
    
    返回:
    - message: 操作结果消息
    """
    # 检查知识库是否存在
    kb = knowledge_base_service.get_knowledge_base(db=db, kb_id=kb_id)
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="知识库未找到"
        )
    
    # 添加后台任务重建索引
    background_tasks.add_task(
        knowledge_base_service.rebuild_index,
        db=db,
        kb_id=kb_id
    )
    
    return {
        "message": f"已安排重建知识库 '{kb.name}' 的索引的后台任务"
    }
