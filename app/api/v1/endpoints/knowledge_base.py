from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional, Dict, Any
import logging

from app.api.deps import get_db
from app.models.knowledge_base import (
    KnowledgeBase, 
    KnowledgeBaseCreate, 
    KnowledgeBaseResponse, 
    KnowledgeBaseUpdate,
    KnowledgeBaseDetail,
    KnowledgeBaseList
)
from app.models.document import DocumentStatus
from app.services.knowledge_base import kb_service
from app.services.vector_store import (
    create_collection,
    check_collection_exists,
    get_knowledge_base_stats
)

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", response_model=KnowledgeBaseResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(
    kb_create: KnowledgeBaseCreate,
    db: Session = Depends(get_db)
):
    """
    创建知识库
    
    Args:
        kb_create: 知识库创建参数
        db: 数据库会话
    
    Returns:
        创建的知识库信息
    """
    try:
        # 检查是否已存在同名知识库
        existing_kb = db.query(KnowledgeBase).filter(
            KnowledgeBase.name == kb_create.name
        ).first()
        
        if existing_kb:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"已存在同名知识库: {kb_create.name}"
            )
        
        # 创建知识库
        new_kb = kb_service.create_knowledge_base(
            db=db,
            name=kb_create.name,
            description=kb_create.description,
            vector_store=kb_create.vector_store,
            embedding_model=kb_create.embedding_model,
            chunk_size=kb_create.chunk_size,
            chunk_overlap=kb_create.chunk_overlap,
            chunking_strategy=kb_create.chunking_strategy,
            custom_separators=kb_create.custom_separators
        )
        
        # 创建向量存储集合
        collection_created = create_collection(
            collection_name=new_kb.id,
            dimension=kb_create.embedding_dimension or 1536
        )
        
        if not collection_created:
            # 如果向量存储创建失败，删除知识库记录
            db.delete(new_kb)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="向量存储集合创建失败"
            )
        
        logger.info(f"知识库创建成功: {new_kb.name} (ID: {new_kb.id})")
        return new_kb
        
    except IntegrityError as e:
        db.rollback()
        logger.error(f"创建知识库失败 - 数据完整性错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"创建知识库失败: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"创建知识库失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建知识库失败: {str(e)}"
        )

@router.get("/", response_model=KnowledgeBaseList)
async def get_knowledge_bases(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    获取知识库列表
    
    Args:
        skip: 分页偏移量
        limit: 分页大小
        db: 数据库会话
    
    Returns:
        知识库列表
    """
    try:
        kb_list, total = kb_service.get_knowledge_bases(
            db=db,
            skip=skip,
            limit=limit
        )
        
        # 获取每个知识库的文档统计信息
        for kb in kb_list:
            # 统计文档数量和状态
            doc_stats = db.query(
                DocumentStatus,
                db.func.count()
            ).join(
                KnowledgeBase.documents
            ).filter(
                KnowledgeBase.id == kb.id
            ).group_by(
                DocumentStatus
            ).all()
            
            # 初始化统计信息
            kb.document_stats = {
                "total": 0,
                "pending": 0,
                "processing": 0,
                "completed": 0,
                "error": 0
            }
            
            # 填充统计信息
            for status, count in doc_stats:
                kb.document_stats["total"] += count
                if status == DocumentStatus.PENDING:
                    kb.document_stats["pending"] = count
                elif status == DocumentStatus.PROCESSING:
                    kb.document_stats["processing"] = count
                elif status == DocumentStatus.COMPLETED:
                    kb.document_stats["completed"] = count
                elif status == DocumentStatus.ERROR:
                    kb.document_stats["error"] = count
        
        return KnowledgeBaseList(
            total=total,
            items=kb_list
        )
    except Exception as e:
        logger.exception(f"获取知识库列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取知识库列表失败: {str(e)}"
        )

@router.get("/{kb_id}", response_model=KnowledgeBaseDetail)
async def get_knowledge_base(
    kb_id: str = Path(...),
    db: Session = Depends(get_db)
):
    """
    获取知识库详情
    
    Args:
        kb_id: 知识库ID
        db: 数据库会话
    
    Returns:
        知识库详情
    """
    try:
        kb = kb_service.get_knowledge_base(db=db, kb_id=kb_id)
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"知识库不存在: {kb_id}"
            )
        
        # 获取知识库文档列表
        kb_detail = kb_service.get_knowledge_base_with_documents(db=db, kb_id=kb_id)
        
        # 获取向量存储统计信息
        vector_stats = get_knowledge_base_stats(kb_id)
        if vector_stats:
            kb_detail.vector_stats = vector_stats
        
        return kb_detail
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"获取知识库详情失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取知识库详情失败: {str(e)}"
        )

@router.put("/{kb_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(
    kb_update: KnowledgeBaseUpdate,
    kb_id: str = Path(...),
    db: Session = Depends(get_db)
):
    """
    更新知识库
    
    Args:
        kb_update: 知识库更新参数
        kb_id: 知识库ID
        db: 数据库会话
    
    Returns:
        更新后的知识库信息
    """
    try:
        # 检查知识库是否存在
        kb = kb_service.get_knowledge_base(db=db, kb_id=kb_id)
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"知识库不存在: {kb_id}"
            )
        
        # 检查向量存储集合是否存在
        if not check_collection_exists(kb_id):
            # 向量存储不存在，创建新的集合
            collection_created = create_collection(
                collection_name=kb_id,
                dimension=kb_update.embedding_dimension or 1536
            )
            
            if not collection_created:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="向量存储集合创建失败"
                )
        
        # 更新知识库
        updated_kb = kb_service.update_knowledge_base(
            db=db,
            kb_id=kb_id,
            name=kb_update.name,
            description=kb_update.description,
            vector_store=kb_update.vector_store,
            embedding_model=kb_update.embedding_model,
            chunk_size=kb_update.chunk_size,
            chunk_overlap=kb_update.chunk_overlap,
            chunking_strategy=kb_update.chunking_strategy,
            custom_separators=kb_update.custom_separators
        )
        
        logger.info(f"知识库更新成功: {updated_kb.name} (ID: {kb_id})")
        return updated_kb
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"更新知识库失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新知识库失败: {str(e)}"
        )

@router.delete("/{kb_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_base(
    kb_id: str = Path(...),
    db: Session = Depends(get_db)
):
    """
    删除知识库
    
    Args:
        kb_id: 知识库ID
        db: 数据库会话
    """
    try:
        # 检查知识库是否存在
        kb = kb_service.get_knowledge_base(db=db, kb_id=kb_id)
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"知识库不存在: {kb_id}"
            )
        
        # 删除知识库
        kb_service.delete_knowledge_base(db=db, kb_id=kb_id)
        
        logger.info(f"知识库删除成功: {kb.name} (ID: {kb_id})")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"删除知识库失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除知识库失败: {str(e)}"
        )

@router.post("/{kb_id}/documents", response_model=Dict[str, Any])
async def add_documents_to_knowledge_base(
    document_ids: List[str],
    kb_id: str = Path(...),
    db: Session = Depends(get_db)
):
    """
    向知识库添加文档
    
    Args:
        document_ids: 文档ID列表
        kb_id: 知识库ID
        db: 数据库会话
    
    Returns:
        添加结果
    """
    try:
        # 检查知识库是否存在
        kb = kb_service.get_knowledge_base(db=db, kb_id=kb_id)
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"知识库不存在: {kb_id}"
            )
        
        # 检查向量存储集合是否存在
        if not check_collection_exists(kb_id):
            # 向量存储不存在，创建新的集合
            collection_created = create_collection(
                collection_name=kb_id,
                dimension=1536
            )
            
            if not collection_created:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="向量存储集合创建失败"
                )
        
        # 添加文档到知识库
        result = kb_service.add_documents_to_knowledge_base(
            db=db,
            kb_id=kb_id,
            document_ids=document_ids
        )
        
        logger.info(f"向知识库添加文档成功: {kb.name} (ID: {kb_id}), 文档数量: {len(document_ids)}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"向知识库添加文档失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"向知识库添加文档失败: {str(e)}"
        )

@router.delete("/{kb_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_document_from_knowledge_base(
    kb_id: str = Path(...),
    document_id: str = Path(...),
    db: Session = Depends(get_db)
):
    """
    从知识库移除文档
    
    Args:
        kb_id: 知识库ID
        document_id: 文档ID
        db: 数据库会话
    """
    try:
        # 检查知识库是否存在
        kb = kb_service.get_knowledge_base(db=db, kb_id=kb_id)
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"知识库不存在: {kb_id}"
            )
        
        # 从知识库移除文档
        kb_service.remove_document_from_knowledge_base(
            db=db,
            kb_id=kb_id,
            document_id=document_id
        )
        
        logger.info(f"从知识库移除文档成功: {kb.name} (ID: {kb_id}), 文档ID: {document_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"从知识库移除文档失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"从知识库移除文档失败: {str(e)}"
        )

@router.get("/stats", response_model=Dict[str, Any])
async def get_knowledge_base_statistics(
    db: Session = Depends(get_db)
):
    """
    获取知识库统计信息
    
    Args:
        db: 数据库会话
    
    Returns:
        知识库统计信息
    """
    try:
        # 统计知识库总数
        kb_count = db.query(KnowledgeBase).count()
        
        # 统计文档总数和状态分布
        doc_stats = db.query(
            DocumentStatus,
            db.func.count()
        ).join(
            KnowledgeBase.documents
        ).group_by(
            DocumentStatus
        ).all()
        
        # 初始化统计信息
        document_stats = {
            "total": 0,
            "pending": 0,
            "processing": 0,
            "completed": 0,
            "error": 0
        }
        
        # 填充统计信息
        for status, count in doc_stats:
            document_stats["total"] += count
            if status == DocumentStatus.PENDING:
                document_stats["pending"] = count
            elif status == DocumentStatus.PROCESSING:
                document_stats["processing"] = count
            elif status == DocumentStatus.COMPLETED:
                document_stats["completed"] = count
            elif status == DocumentStatus.ERROR:
                document_stats["error"] = count
        
        return {
            "knowledge_bases": {
                "total": kb_count
            },
            "documents": document_stats
        }
        
    except Exception as e:
        logger.exception(f"获取知识库统计信息失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取知识库统计信息失败: {str(e)}"
        ) 