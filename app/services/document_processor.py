"""
文档处理服务
负责文档处理流程，包括文档分块、向量化等
"""
import logging
import json
import time
from functools import lru_cache
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.orm import Session

from app.models.document import Document, Segment, DocumentStatus, update_document_status, add_segment
from app.models.knowledge_base import KnowledgeBase
from app.services.document_chunker import document_chunker
from app.core.config import settings

logger = logging.getLogger(__name__)

# 创建线程池
_THREAD_POOL = ThreadPoolExecutor(max_workers=settings.DOCUMENT_PROCESSOR_WORKERS)


class DocumentProcessor:
    """文档处理服务"""
    
    @staticmethod
    async def process_document(
        db: Session,
        document_id: str,
        knowledge_base_id: Optional[str] = None
    ) -> bool:
        """
        处理文档，包括分块和向量化
        
        Args:
            db: 数据库会话
            document_id: 文档ID
            knowledge_base_id: 关联的知识库ID，如果提供则使用该知识库的分块策略
            
        Returns:
            处理成功返回True，否则返回False
        """
        start_time = time.time()
        try:
            # 更新文档状态为处理中
            update_document_status(
                document_id=document_id, 
                status=DocumentStatus.PROCESSING,
                db=db
            )
            
            # 获取文档信息
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                logger.error(f"文档不存在: {document_id}")
                return False
            
            # 获取分块策略
            chunk_size, chunk_overlap, chunking_strategy = DocumentProcessor._get_chunking_config(
                db, document, knowledge_base_id
            )
            
            # 分块文档
            chunks = await document_chunker.chunk_document_async(
                document_path=document.file_path,
                chunking_strategy=chunking_strategy,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            
            # 批量添加段落
            await DocumentProcessor._batch_add_segments(db, document_id, chunks)
            
            # 更新文档状态为已完成
            update_document_status(
                document_id=document_id, 
                status=DocumentStatus.COMPLETED,
                segment_count=len(chunks),
                db=db
            )
            
            processing_time = time.time() - start_time
            logger.info(f"文档处理完成: {document_id}, 共 {len(chunks)} 个段落, 耗时: {processing_time:.2f}秒")
            return True
            
        except Exception as e:
            # 记录错误并更新文档状态
            error_message = f"文档处理失败: {str(e)}"
            logger.error(error_message)
            update_document_status(
                document_id=document_id, 
                status=DocumentStatus.ERROR,
                error_message=error_message,
                db=db
            )
            return False
    
    @staticmethod
    async def rechunk_document(
        db: Session,
        document_id: str,
        chunk_size: int,
        chunk_overlap: int,
        chunking_strategy: str
    ) -> bool:
        """
        重新分块文档
        
        Args:
            db: 数据库会话
            document_id: 文档ID
            chunk_size: 分块大小
            chunk_overlap: 分块重叠大小
            chunking_strategy: 分块策略
            
        Returns:
            处理成功返回True，否则返回False
        """
        start_time = time.time()
        try:
            # 获取文档信息
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                logger.error(f"文档不存在: {document_id}")
                return False
            
            # 删除旧的段落，使用批处理提高性能
            db.query(Segment).filter(Segment.document_id == document_id).delete(synchronize_session=False)
            
            # 更新文档状态为处理中
            update_document_status(
                document_id=document_id, 
                status=DocumentStatus.PROCESSING,
                segment_count=0,
                db=db
            )
            
            # 重新分块文档
            chunks = await document_chunker.chunk_document_async(
                document_path=document.file_path,
                chunking_strategy=chunking_strategy,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            
            # 批量添加段落
            await DocumentProcessor._batch_add_segments(db, document_id, chunks)
            
            # 更新文档状态为已完成
            update_document_status(
                document_id=document_id, 
                status=DocumentStatus.COMPLETED,
                segment_count=len(chunks),
                db=db
            )
            
            processing_time = time.time() - start_time
            logger.info(f"文档重新分块完成: {document_id}, 共 {len(chunks)} 个段落, 耗时: {processing_time:.2f}秒")
            return True
            
        except Exception as e:
            # 记录错误并更新文档状态
            error_message = f"文档重新分块失败: {str(e)}"
            logger.error(error_message)
            update_document_status(
                document_id=document_id, 
                status=DocumentStatus.ERROR,
                error_message=error_message,
                db=db
            )
            return False
    
    @staticmethod
    async def batch_process_documents(
        db: Session,
        document_ids: List[str],
        knowledge_base_id: Optional[str] = None
    ) -> Tuple[int, int]:
        """
        批量处理多个文档
        
        Args:
            db: 数据库会话
            document_ids: 文档ID列表
            knowledge_base_id: 关联的知识库ID
            
        Returns:
            成功处理的文档数量和失败的文档数量
        """
        success_count = 0
        fail_count = 0
        
        # 获取分块策略
        chunk_size = 1000
        chunk_overlap = 200
        chunking_strategy = "paragraph"
        
        if knowledge_base_id:
            kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == knowledge_base_id).first()
            if kb:
                chunk_size = kb.chunk_size
                chunk_overlap = kb.chunk_overlap
                chunking_strategy = kb.chunking_strategy
        
        # 任务批处理
        for doc_id in document_ids:
            try:
                result = await DocumentProcessor.process_document(
                    db=db,
                    document_id=doc_id,
                    knowledge_base_id=knowledge_base_id
                )
                if result:
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                logger.error(f"批处理文档出错 {doc_id}: {str(e)}")
                fail_count += 1
        
        return success_count, fail_count
    
    @staticmethod
    @lru_cache(maxsize=32)
    def _get_chunking_config(
        db: Session, 
        document: Document, 
        knowledge_base_id: Optional[str]
    ) -> Tuple[int, int, str]:
        """
        获取分块配置（带缓存）
        
        Args:
            db: 数据库会话
            document: 文档对象
            knowledge_base_id: 知识库ID
            
        Returns:
            分块大小，分块重叠大小，分块策略
        """
        # 默认分块策略
        chunk_size = 1000
        chunk_overlap = 200
        chunking_strategy = "paragraph"
        
        # 如果提供了知识库ID，使用该知识库的分块策略
        if knowledge_base_id:
            kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == knowledge_base_id).first()
            if kb:
                chunk_size = kb.chunk_size
                chunk_overlap = kb.chunk_overlap
                chunking_strategy = kb.chunking_strategy
                
        # 根据文档类型调整策略
        file_extension = document.file_type.lower() if document.file_type else ""
        if file_extension == "md" or file_extension == "markdown":
            # Markdown文档使用专用分割器
            chunking_strategy = "markdown"
        
        return chunk_size, chunk_overlap, chunking_strategy
    
    @staticmethod
    async def _batch_add_segments(db: Session, document_id: str, chunks: List[Dict[str, Any]]) -> None:
        """
        批量添加段落记录以提高性能
        
        Args:
            db: 数据库会话
            document_id: 文档ID
            chunks: 分块结果列表
        """
        segments = []
        
        for chunk in chunks:
            # 转换元数据为JSON字符串
            if isinstance(chunk["meta_data"], dict):
                meta_data_json = json.dumps(chunk["meta_data"], ensure_ascii=False)
            else:
                meta_data_json = "{}"
            
            # 创建段落数据
            segment_data = {
                "document_id": document_id,
                "content": chunk["content"],
                "meta_data": meta_data_json,
                "chunk_index": chunk["chunk_index"],
                "enabled": 1
            }
            segments.append(segment_data)
        
        # 每批50条记录插入数据库
        batch_size = 50
        for i in range(0, len(segments), batch_size):
            batch = segments[i:i+batch_size]
            segment_objects = [Segment(**data) for data in batch]
            db.add_all(segment_objects)
            db.commit()


# 创建文档处理服务单例
document_processor = DocumentProcessor()
