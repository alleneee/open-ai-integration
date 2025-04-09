"""
文档处理相关的后台任务
提供异步文档解析、索引和错误恢复功能
"""
import logging
import os
import tempfile
from typing import List, Optional, Dict, Any, Union

from celery import shared_task
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.services.parser import parse_file_from_path_and_split
from app.services.document_chunker import document_chunker
from app.services.document_processor import document_processor
from app.services.vector_store import add_documents
from app.services.rag import perform_rag_query
from app.models.document import DocumentStatus, DocumentModel, SegmentModel
from app.task.celery_app import celery_app
from app.models.database import SessionLocal
from sqlalchemy.exc import IntegrityError, OperationalError

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def document_indexing_task(self, document_id: str, file_path: str, filename: str, 
                          collection_name: str, tenant_id: str) -> Dict[str, Any]:
    """
    文档解析和索引的后台任务
    
    Args:
        document_id: 文档ID
        file_path: 文件路径
        filename: 原始文件名
        collection_name: 向量存储集合名称
        tenant_id: 租户ID
        
    Returns:
        处理结果字典
    """
    from app.models.document import update_document_status
    
    # 创建数据库会话
    db = SessionLocal()
    
    try:
        # 更新状态为处理中
        update_document_status(document_id, DocumentStatus.PROCESSING, db=db)
        
        # 解析文档并分割
        logger.info(f"开始处理文档 {filename} (ID: {document_id})")
        document_chunks = parse_file_from_path_and_split(file_path, filename)
        
        if not document_chunks:
            logger.error(f"文档 {filename} 解析后没有内容")
            update_document_status(document_id, DocumentStatus.ERROR, error_message="文档解析后没有内容", db=db)
            return {"success": False, "error": "文档解析后没有内容"}
        
        # 添加到向量存储
        logger.info(f"索引文档 {filename}，共 {len(document_chunks)} 个块")
        
        # 准备元数据
        metadatas = [chunk.metadata for chunk in document_chunks]
        for i, metadata in enumerate(metadatas):
            metadata["document_id"] = document_id
            metadata["chunk_id"] = f"{document_id}_{i}"
            metadata["tenant_id"] = tenant_id
        
        # 添加到向量存储
        try:
            add_documents(
                documents=[chunk.page_content for chunk in document_chunks],
                metadatas=metadatas,
                collection_name=collection_name
            )
            
            # 更新状态为已完成
            update_document_status(document_id, DocumentStatus.COMPLETED, 
                                   segment_count=len(document_chunks), db=db)
            
            logger.info(f"文档 {filename} (ID: {document_id}) 索引完成")
            return {
                "success": True,
                "document_id": document_id,
                "segments_count": len(document_chunks)
            }
            
        except Exception as e:
            logger.exception(f"索引文档 {document_id} 时出错: {str(e)}")
            update_document_status(document_id, DocumentStatus.ERROR, 
                                  error_message=f"索引文档失败: {str(e)}", db=db)
            return {"success": False, "error": f"索引文档失败: {str(e)}"}
            
    except Exception as e:
        logger.exception(f"处理文档 {document_id} 时出错: {str(e)}")
        # 更新状态为错误
        update_document_status(document_id, DocumentStatus.ERROR, 
                              error_message=f"处理文档失败: {str(e)}", db=db)
        
        # 如果不是最后一次重试，则重试任务
        if self.request.retries < self.max_retries:
            logger.info(f"重试处理文档 {document_id}，第 {self.request.retries + 1} 次尝试")
            self.retry(exc=e, countdown=10 * (2 ** self.request.retries))
            
        return {"success": False, "error": str(e)}
    finally:
        db.close()

@shared_task(bind=True, max_retries=2)
def retry_document_indexing_task(self, document_id: str):
    """
    重试失败的文档索引任务
    
    Args:
        document_id: 失败的文档ID
    """
    from app.models.document import get_document_by_id, update_document_status
    
    # 创建数据库会话
    db = SessionLocal()
    
    try:
        # 获取文档信息
        document = get_document_by_id(document_id, db=db)
        if not document:
            logger.error(f"重试索引文档 {document_id} 失败: 文档不存在")
            return {"success": False, "error": "文档不存在"}
            
        if document.status != DocumentStatus.ERROR:
            logger.warning(f"文档 {document_id} 状态不是错误状态，不需要重试")
            return {"success": False, "error": "文档状态不是错误状态，不需要重试"}
        
        # 更新状态为待处理
        update_document_status(document_id, DocumentStatus.PENDING, db=db)
        
        # 重新启动文档索引任务
        document_indexing_task.delay(
            document_id=document_id,
            file_path=document.file_path,
            filename=document.filename,
            collection_name=document.collection_name,
            tenant_id=document.tenant_id
        )
        
        logger.info(f"已重新安排文档 {document_id} 的索引任务")
        return {"success": True}
        
    except Exception as e:
        logger.exception(f"重试文档 {document_id} 索引时出错: {str(e)}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()

@shared_task
def batch_delete_document_task(document_ids: List[str], collection_name: str):
    """
    批量删除文档的后台任务
    
    Args:
        document_ids: 要删除的文档ID列表
        collection_name: 向量存储集合名称
    """
    from app.models.document import delete_documents
    
    # 创建数据库会话
    db = SessionLocal()
    
    try:
        # 从向量存储中删除
        vector_store = get_vector_store(collection_name)
        for doc_id in document_ids:
            # 通常向量存储会有按过滤条件删除的API
            vector_store.delete(filter={"document_id": doc_id})
        
        # 从数据库中删除
        delete_documents(document_ids, db=db)
        
        logger.info(f"成功删除 {len(document_ids)} 个文档")
        return {"success": True, "deleted_count": len(document_ids)}
        
    except Exception as e:
        logger.exception(f"批量删除文档时出错: {str(e)}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()
