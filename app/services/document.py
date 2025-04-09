import logging
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, and_
from fastapi import HTTPException, status
import os

from app.models.document import Document
from app.schemas.document import DocumentCreate, DocumentUpdate
from app.db.models import DocumentModel
from app.services.vector_store import add_documents_to_knowledge_base, remove_document_from_knowledge_base

# 初始化日志
logger = logging.getLogger(__name__)

async def create_document(
    db: AsyncSession,
    document_data: DocumentCreate,
    user_id: Optional[str] = None
) -> Document:
    """
    创建新文档记录
    
    参数:
        db: 数据库会话
        document_data: 文档数据
        user_id: 用户ID
        
    返回:
        Document: 创建的文档对象
    """
    try:
        # 创建数据库模型对象
        db_document = DocumentModel(
            id=document_data.id,
            filename=document_data.filename,
            file_path=document_data.file_path,
            file_type=document_data.file_type,
            file_size=document_data.file_size,
            content=document_data.content,
            metadata=document_data.metadata,
            processed=document_data.processed,
            error=document_data.error,
            created_by=user_id or document_data.created_by,
        )
        
        # 添加到数据库
        db.add(db_document)
        await db.commit()
        await db.refresh(db_document)
        
        # 转换为应用模型并返回
        return Document.from_orm(db_document)
    
    except Exception as e:
        await db.rollback()
        logger.error(f"创建文档失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建文档失败: {str(e)}"
        )

async def get_document(
    db: AsyncSession,
    document_id: str,
    user_id: Optional[str] = None,
    check_permission: bool = True
) -> Document:
    """
    获取文档详情
    
    参数:
        db: 数据库会话
        document_id: 文档ID
        user_id: 用户ID（用于权限检查）
        check_permission: 是否检查权限
        
    返回:
        Document: 文档对象
    """
    try:
        # 查询文档
        query = select(DocumentModel).where(DocumentModel.id == document_id)
        result = await db.execute(query)
        db_document = result.scalar_one_or_none()
        
        # 检查文档是否存在
        if not db_document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"找不到ID为 {document_id} 的文档"
            )
        
        # 检查权限（如果需要）
        if check_permission and user_id and db_document.created_by and db_document.created_by != user_id:
            # TODO: 未来可以实现更复杂的权限检查（如共享权限）
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您没有查看该文档的权限"
            )
            
        # 转换为应用模型并返回
        return Document.from_orm(db_document)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文档失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文档失败: {str(e)}"
        )

async def update_document(
    db: AsyncSession,
    document_id: str,
    document_data: DocumentUpdate,
    user_id: Optional[str] = None,
    check_permission: bool = True
) -> Document:
    """
    更新文档
    
    参数:
        db: 数据库会话
        document_id: 文档ID
        document_data: 更新数据
        user_id: 用户ID（用于权限检查）
        check_permission: 是否检查权限
        
    返回:
        Document: 更新后的文档对象
    """
    try:
        # 获取现有文档
        existing_document = await get_document(db, document_id, user_id, check_permission)
        
        # 更新文档
        # 防止更改文档ID
        update_data = document_data.dict(exclude_unset=True)
        if 'id' in update_data:
            del update_data['id']
            
        # 获取数据库对象
        query = select(DocumentModel).where(DocumentModel.id == document_id)
        result = await db.execute(query)
        db_document = result.scalar_one()
        
        # 更新字段
        for field, value in update_data.items():
            setattr(db_document, field, value)
            
        # 提交更改
        await db.commit()
        await db.refresh(db_document)
        
        # 转换为应用模型并返回
        return Document.from_orm(db_document)
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"更新文档失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"更新文档失败: {str(e)}"
        )

async def delete_document(
    db: AsyncSession,
    document_id: str,
    user_id: Optional[str] = None,
    check_permission: bool = True,
    delete_file: bool = True,
    file_store_path: Optional[str] = None
) -> bool:
    """
    删除文档
    
    参数:
        db: 数据库会话
        document_id: 文档ID
        user_id: 用户ID（用于权限检查）
        check_permission: 是否检查权限
        delete_file: 是否同时删除物理文件
        file_store_path: 文件存储路径（如果需要删除物理文件）
        
    返回:
        bool: 删除成功返回True
    """
    try:
        # 获取现有文档
        existing_document = await get_document(db, document_id, user_id, check_permission)
        
        # 删除物理文件（如果需要）
        if delete_file and existing_document.file_path and file_store_path:
            file_path = os.path.join(file_store_path, existing_document.file_path)
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"已删除文件: {file_path}")
            except Exception as e:
                logger.error(f"删除文件失败: {file_path} - {str(e)}")
        
        # 删除数据库记录
        query = delete(DocumentModel).where(DocumentModel.id == document_id)
        await db.execute(query)
        await db.commit()
        
        return True
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"删除文档失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除文档失败: {str(e)}"
        )

async def list_documents(
    db: AsyncSession,
    user_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    filter_by: Optional[Dict[str, Any]] = None
) -> Tuple[List[Document], int]:
    """
    列出文档
    
    参数:
        db: 数据库会话
        user_id: 用户ID（用于过滤）
        skip: 分页偏移
        limit: 分页限制
        filter_by: 过滤条件
        
    返回:
        Tuple[List[Document], int]: 文档列表和总数
    """
    try:
        # 构建基本查询
        filters = []
        
        # 添加用户ID过滤
        if user_id:
            filters.append(DocumentModel.created_by == user_id)
        
        # 添加其他过滤条件
        if filter_by:
            for field, value in filter_by.items():
                if hasattr(DocumentModel, field):
                    filters.append(getattr(DocumentModel, field) == value)
        
        # 查询总数
        count_query = select(func.count()).select_from(DocumentModel)
        if filters:
            count_query = count_query.where(and_(*filters))
        
        count_result = await db.execute(count_query)
        total_count = count_result.scalar_one()
        
        # 查询文档
        query = select(DocumentModel)
        if filters:
            query = query.where(and_(*filters))
        
        query = query.offset(skip).limit(limit).order_by(DocumentModel.created_at.desc())
        result = await db.execute(query)
        db_documents = result.scalars().all()
        
        # 转换为应用模型
        documents = [Document.from_orm(doc) for doc in db_documents]
        
        return documents, total_count
    
    except Exception as e:
        logger.error(f"列出文档失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"列出文档失败: {str(e)}"
        )

async def add_document_to_kb(
    db: AsyncSession,
    document_id: str,
    kb_name: str,
    user_id: Optional[str] = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> bool:
    """
    将文档添加到知识库
    
    参数:
        db: 数据库会话
        document_id: 文档ID
        kb_name: 知识库名称
        user_id: 用户ID
        chunk_size: 分块大小
        chunk_overlap: 分块重叠
        
    返回:
        bool: 添加成功返回True
    """
    try:
        # 获取文档
        document = await get_document(db, document_id, user_id)
        
        # 检查文档内容
        if not document.content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文档没有可添加到知识库的内容"
            )
        
        # 构建文档元数据
        metadata = {
            "document_id": document.id,
            "filename": document.filename,
            "file_type": document.file_type,
            **document.metadata
        }
        
        # 添加到知识库
        result = add_documents_to_knowledge_base(
            kb_name=kb_name, 
            docs=[document.content], 
            metadatas=[metadata],
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"将文档添加到知识库失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"将文档添加到知识库失败: {str(e)}"
        )

async def remove_document_from_kb(
    db: AsyncSession,
    document_id: str,
    kb_name: str,
    user_id: Optional[str] = None
) -> bool:
    """
    从知识库移除文档
    
    参数:
        db: 数据库会话
        document_id: 文档ID
        kb_name: 知识库名称
        user_id: 用户ID
        
    返回:
        bool: 移除成功返回True
    """
    try:
        # 获取文档（权限检查）
        document = await get_document(db, document_id, user_id)
        
        # 从知识库移除
        result = remove_document_from_knowledge_base(
            kb_name=kb_name,
            filter_dict={"document_id": document_id}
        )
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"从知识库移除文档失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"从知识库移除文档失败: {str(e)}"
        ) 