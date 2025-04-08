"""
知识库服务
处理知识库的创建、查询、更新和文档管理等业务逻辑
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.knowledge_base import (
    KnowledgeBase,
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseSchema,
    KnowledgeBaseDetailSchema,
    ChunkingConfig
)
from app.models.document import Document
from app.services.document_processor import document_processor
from app.db.session import SessionLocal
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class KnowledgeBaseService:
    """知识库服务类"""
    
    @staticmethod
    def create_knowledge_base(
        db: Session, 
        kb_create: KnowledgeBaseCreate, 
        user_id: str
    ) -> KnowledgeBase:
        """
        创建新的知识库
        
        Args:
            db: 数据库会话
            kb_create: 知识库创建请求数据
            user_id: 创建者用户ID
            
        Returns:
            新创建的知识库对象
        """
        # 检查同名知识库是否已存在
        existing_kb = db.query(KnowledgeBase).filter(
            KnowledgeBase.name == kb_create.name
        ).first()
        
        if existing_kb:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="知识库名称已存在"
            )
        
        # 创建新知识库
        kb_data = kb_create.model_dump()
        kb_data["created_by"] = user_id
        
        new_kb = KnowledgeBase(**kb_data)
        db.add(new_kb)
        db.commit()
        db.refresh(new_kb)
        
        return new_kb
    
    @staticmethod
    def get_knowledge_bases(
        db: Session, 
        skip: int = 0, 
        limit: int = 100, 
        user_id: Optional[str] = None
    ) -> List[KnowledgeBase]:
        """
        获取知识库列表，可选按创建者筛选
        
        Args:
            db: 数据库会话
            skip: 分页起始位置
            limit: 分页大小
            user_id: 可选的创建者用户ID筛选
            
        Returns:
            知识库对象列表
        """
        query = db.query(KnowledgeBase)
        
        if user_id:
            query = query.filter(KnowledgeBase.created_by == user_id)
        
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def get_knowledge_base(db: Session, kb_id: str) -> Optional[KnowledgeBase]:
        """
        获取指定ID的知识库
        
        Args:
            db: 数据库会话
            kb_id: 知识库ID
            
        Returns:
            知识库对象，未找到则返回None
        """
        return db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    
    @staticmethod
    def get_knowledge_base_with_documents(db: Session, kb_id: str) -> Optional[KnowledgeBase]:
        """
        获取指定ID的知识库，包含其关联的所有文档
        
        Args:
            db: 数据库会话
            kb_id: 知识库ID
            
        Returns:
            包含文档关联的知识库对象，未找到则返回None
        """
        # 使用joined eager loading加载文档关联
        return db.query(KnowledgeBase).filter(
            KnowledgeBase.id == kb_id
        ).first()
    
    @staticmethod
    def update_knowledge_base(
        db: Session, 
        kb_id: str, 
        kb_update: KnowledgeBaseUpdate
    ) -> Optional[KnowledgeBase]:
        """
        更新知识库信息
        
        Args:
            db: 数据库会话
            kb_id: 知识库ID
            kb_update: 知识库更新数据
            
        Returns:
            更新后的知识库对象，未找到则返回None
        """
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        
        if not kb:
            return None
        
        # 只更新非None的字段
        update_data = kb_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(kb, key, value)
        
        db.commit()
        db.refresh(kb)
        
        return kb
    
    @staticmethod
    def delete_knowledge_base(db: Session, kb_id: str) -> bool:
        """
        删除指定知识库
        
        Args:
            db: 数据库会话
            kb_id: 知识库ID
            
        Returns:
            删除成功返回True，未找到则返回False
        """
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        
        if not kb:
            return False
        
        db.delete(kb)
        db.commit()
        
        return True
    
    @staticmethod
    def add_documents_to_knowledge_base(
        db: Session, 
        kb_id: str, 
        document_ids: List[str]
    ) -> Optional[KnowledgeBase]:
        """
        向知识库添加文档
        
        Args:
            db: 数据库会话
            kb_id: 知识库ID
            document_ids: 文档ID列表
            
        Returns:
            更新后的知识库对象，未找到则返回None
        """
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        
        if not kb:
            return None
        
        # 查询所有指定ID的文档
        documents = db.query(Document).filter(Document.id.in_(document_ids)).all()
        found_doc_ids = {doc.id for doc in documents}
        
        # 检查是否有文档未找到
        missing_ids = set(document_ids) - found_doc_ids
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"文档未找到: {', '.join(missing_ids)}"
            )
        
        # 添加文档到知识库
        for doc in documents:
            if doc not in kb.documents:
                kb.documents.append(doc)
                
                # 异步处理文档分块，使用知识库的分块策略
                document_processor.process_document(
                    db=db,
                    document_id=doc.id,
                    knowledge_base_id=kb_id
                )
        
        db.commit()
        db.refresh(kb)
        
        return kb
    
    @staticmethod
    def remove_document_from_knowledge_base(
        db: Session, 
        kb_id: str, 
        document_id: str
    ) -> Optional[KnowledgeBase]:
        """
        从知识库移除文档
        
        Args:
            db: 数据库会话
            kb_id: 知识库ID
            document_id: 文档ID
            
        Returns:
            更新后的知识库对象，未找到则返回None
        """
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        
        if not kb:
            return None
        
        # 查找文档
        document = db.query(Document).filter(Document.id == document_id).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"文档未找到: {document_id}"
            )
        
        # 移除文档
        if document in kb.documents:
            kb.documents.remove(document)
        
        db.commit()
        db.refresh(kb)
        
        return kb
        
    async def update_chunking_config(
        self,
        db: Session,
        kb_id: str,
        config: ChunkingConfig
    ) -> KnowledgeBase:
        """
        更新知识库的分块配置
        
        Args:
            db: 数据库会话
            kb_id: 知识库ID
            config: 分块配置
            
        Returns:
            更新后的知识库对象
        """
        try:
            # 使用显式事务管理
            kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).with_for_update().first()
            if not kb:
                logger.error(f"知识库不存在: {kb_id}")
                raise ValueError(f"知识库不存在: {kb_id}")
            
            # 验证分块配置
            if config.chunk_size <= 0:
                raise ValueError("分块大小必须大于0")
            if config.chunk_overlap < 0:
                raise ValueError("分块重叠大小必须大于等于0")
            if config.chunk_overlap >= config.chunk_size:
                raise ValueError("分块重叠大小必须小于分块大小")
            
            # 记录原始配置，用于判断是否需要重新处理文档
            original_config = {
                "chunk_size": kb.chunk_size,
                "chunk_overlap": kb.chunk_overlap,
                "chunking_strategy": kb.chunking_strategy
            }
            
            # 更新知识库分块配置
            kb.chunk_size = config.chunk_size
            kb.chunk_overlap = config.chunk_overlap
            kb.chunking_strategy = config.chunking_strategy
            kb.updated_at = datetime.now()
            
            # 提交事务
            db.commit()
            
            # 如果需要重新处理知识库中的所有文档
            if config.rechunk_documents:
                # 获取知识库中的所有文档
                documents = db.query(Document).join(
                    knowledge_base_documents,
                    knowledge_base_documents.c.document_id == Document.id
                ).filter(
                    knowledge_base_documents.c.knowledge_base_id == kb_id,
                    Document.status.in_([DocumentStatus.COMPLETED, DocumentStatus.ERROR])
                ).all()
                
                document_ids = [doc.id for doc in documents]
                
                # 批量处理文档
                if document_ids:
                    logger.info(f"开始批量重新处理知识库 {kb_id} 中的 {len(document_ids)} 个文档")
                    
                    # 在后台任务中处理文档
                    asyncio.create_task(
                        self._process_documents_batch(
                            db=db,
                            kb_id=kb_id,
                            document_ids=document_ids,
                            config_changed=self._is_config_changed(original_config, kb)
                        )
                    )
            
            return kb
            
        except Exception as e:
            db.rollback()
            logger.error(f"更新知识库分块配置失败: {str(e)}")
            raise

    @staticmethod
    def _is_config_changed(original: Dict[str, Any], kb: KnowledgeBase) -> bool:
        """
        检查分块配置是否有变化
        
        Args:
            original: 原始配置
            kb: 知识库对象
            
        Returns:
            如果配置有变化，返回True
        """
        return (
            original["chunk_size"] != kb.chunk_size or
            original["chunk_overlap"] != kb.chunk_overlap or
            original["chunking_strategy"] != kb.chunking_strategy
        )
    
    async def _process_documents_batch(
        self,
        db: Session, 
        kb_id: str,
        document_ids: List[str],
        config_changed: bool
    ) -> None:
        """
        批量处理文档（用于后台任务）
        
        Args:
            db: 数据库会话（使用新的会话）
            kb_id: 知识库ID
            document_ids: 文档ID列表
            config_changed: 配置是否有变化
        """
        from app.services.document_processor import document_processor
        
        # 创建新的数据库会话，避免使用传入的会话（可能已关闭）
        new_db = SessionLocal()
        
        try:
            # 获取最新的知识库信息
            kb = new_db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
            if not kb:
                logger.error(f"批量处理时找不到知识库: {kb_id}")
                return
                
            # 如果配置有变化，才重新处理文档
            if config_changed:
                batch_size = 5  # 每批处理的文档数量
                total_batches = (len(document_ids) + batch_size - 1) // batch_size
                
                for batch_idx in range(total_batches):
                    start_idx = batch_idx * batch_size
                    end_idx = min(start_idx + batch_size, len(document_ids))
                    batch_document_ids = document_ids[start_idx:end_idx]
                    
                    # 更新处理状态
                    new_db.query(Document).filter(
                        Document.id.in_(batch_document_ids)
                    ).update(
                        {"status": DocumentStatus.PENDING.value},
                        synchronize_session=False
                    )
                    new_db.commit()
                    
                    # 调用批量处理函数
                    await document_processor.batch_process_documents(
                        db=new_db,
                        document_ids=batch_document_ids,
                        knowledge_base_id=kb_id
                    )
                    
                    # 短暂休眠，避免服务器过载
                    await asyncio.sleep(0.5)
                
                logger.info(f"知识库 {kb_id} 中的所有文档已重新处理完成")
                
        except Exception as e:
            logger.error(f"批量处理文档失败: {str(e)}")
        finally:
            new_db.close()

    async def rebuild_index(
        self, 
        db: Session,
        kb_id: str
    ) -> bool:
        """
        重建知识库的向量索引
        
        Args:
            db: 数据库会话
            kb_id: 知识库ID
            
        Returns:
            重建成功返回True，否则返回False
        """
        from app.db.session import SessionLocal
        from app.services.document_processor import document_processor
        from app.services.document_chunker import document_chunker
        from app.services.vector_store import vector_store_service
        
        # 创建新的数据库会话
        new_db = SessionLocal()
        
        try:
            # 获取知识库信息
            kb = new_db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
            if not kb:
                logger.error(f"重建索引时找不到知识库: {kb_id}")
                return False
            
            # 获取知识库中的所有文档
            documents = new_db.query(Document).join(
                knowledge_base_documents,
                knowledge_base_documents.c.document_id == Document.id
            ).filter(
                knowledge_base_documents.c.knowledge_base_id == kb_id
            ).all()
            
            if not documents:
                logger.warning(f"知识库 {kb_id} 中没有文档，无需重建索引")
                return True
            
            # 清除文档缓存
            for doc in documents:
                document_chunker.clear_cache(doc.file_path)
            
            # 清除向量存储中的数据
            vector_store_service.clear_collection(kb.vector_store, kb_id)
            
            # 重新处理所有文档
            document_ids = [doc.id for doc in documents]
            logger.info(f"开始重建知识库 {kb_id} 的索引，共 {len(document_ids)} 个文档")
            
            # 批量处理文档并重新构建索引
            batch_size = 5  # 每批处理的文档数量
            total_batches = (len(document_ids) + batch_size - 1) // batch_size
            
            for batch_idx in range(total_batches):
                start_idx = batch_idx * batch_size
                end_idx = min(start_idx + batch_size, len(document_ids))
                batch_document_ids = document_ids[start_idx:end_idx]
                
                # 更新处理状态
                new_db.query(Document).filter(
                    Document.id.in_(batch_document_ids)
                ).update(
                    {"status": DocumentStatus.PENDING.value},
                    synchronize_session=False
                )
                new_db.commit()
                
                # 重新处理文档
                await document_processor.batch_process_documents(
                    db=new_db,
                    document_ids=batch_document_ids,
                    knowledge_base_id=kb_id
                )
                
                # 获取处理完的段落并添加到向量存储
                for doc_id in batch_document_ids:
                    segments = new_db.query(Segment).filter(
                        Segment.document_id == doc_id,
                        Segment.enabled == 1
                    ).all()
                    
                    # 将段落添加到向量存储
                    texts = [seg.content for seg in segments]
                    metadatas = [json.loads(seg.meta_data) if seg.meta_data else {} for seg in segments]
                    ids = [seg.id for seg in segments]
                    
                    if texts:
                        # 添加到向量存储
                        await vector_store_service.add_texts(
                            collection_name=kb_id,
                            vector_store=kb.vector_store,
                            texts=texts,
                            metadatas=metadatas,
                            ids=ids
                        )
                
                # 短暂休眠，避免服务器过载
                await asyncio.sleep(settings.DOCUMENT_BATCH_SLEEP)
            
            logger.info(f"知识库 {kb_id} 的索引重建完成")
            return True
            
        except Exception as e:
            logger.error(f"重建索引失败: {str(e)}")
            return False
        finally:
            new_db.close()

# 创建知识库服务单例
knowledge_base_service = KnowledgeBaseService()
