"""
知识库服务
处理知识库的创建、查询、更新和文档管理等业务逻辑
"""
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status, BackgroundTasks

from app.models.knowledge_base import (
    KnowledgeBase,
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseSchema,
    KnowledgeBaseDetailSchema,
    ChunkingConfig,
    DatasetPermissionEnum,
    KnowledgeBasePermission
)
from app.models.document import Document, DocumentStatus, Segment, knowledge_base_documents
from app.services.document_processor import document_processor
from app.models.database import SessionLocal, db
import asyncio
import logging
from datetime import datetime
import json
from app.services.vector_store import (
    create_collection,
    check_collection_exists,
    delete_collection,
    add_documents_to_knowledge_base as vector_add_documents,
    get_knowledge_base_stats,
    sync_knowledge_base_metadata,
    get_all_collections,
    ensure_collection_exists
)
from sqlalchemy.exc import IntegrityError
from app.models.user import User
from app.db.crud import create_item, get_items, get_item, update_item, delete_item
from app.db.models import KnowledgeBase as KnowledgeBaseDB, KnowledgeBaseDocument as KnowledgeBaseDocumentDB
from app.models.knowledge_base import KnowledgeBaseStats
import uuid

logger = logging.getLogger(__name__)

# 知识库表名
KNOWLEDGE_BASE_TABLE = "knowledge_bases"
KNOWLEDGE_BASE_DOCUMENT_TABLE = "knowledge_base_documents"

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
        
        # 创建新知识库数据库记录
        kb_data = kb_create.model_dump()
        kb_data["created_by"] = user_id
        
        new_kb = KnowledgeBase(**kb_data)
        db.add(new_kb)
        db.commit()
        db.refresh(new_kb)
        
        # 创建向量存储集合
        collection_created = ensure_collection_exists(new_kb.id)
        if not collection_created:
            # 如果向量存储集合创建失败，回滚数据库事务
            logger.error(f"创建向量存储集合失败: {new_kb.id}")
            db.delete(new_kb)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="创建向量存储集合失败"
            )
            
        # 同步知识库元数据到向量存储
        metadata = {
            "name": new_kb.name,
            "description": new_kb.description,
            "embedding_model": new_kb.embedding_model,
            "chunk_size": new_kb.chunk_size,
            "chunk_overlap": new_kb.chunk_overlap,
            "chunking_strategy": new_kb.chunking_strategy.value if hasattr(new_kb.chunking_strategy, 'value') else new_kb.chunking_strategy,
            "created_at": new_kb.created_at.isoformat(),
            "created_by": new_kb.created_by
        }
        sync_knowledge_base_metadata(new_kb.id, metadata)
        
        return new_kb
    
    @staticmethod
    def get_knowledge_bases(
        db: Session, 
        skip: int = 0, 
        limit: int = 100, 
        user_id: Optional[str] = None,
        search: Optional[str] = None,
        include_all: bool = False
    ) -> Tuple[List[KnowledgeBase], int]:
        """
        获取知识库列表，可选按创建者筛选
        
        Args:
            db: 数据库会话
            skip: 分页起始位置
            limit: 分页大小
            user_id: 可选的用户ID，用于过滤权限
            search: 搜索关键词
            include_all: 是否包括所有知识库（管理员用）
            
        Returns:
            知识库对象列表和总数
        """
        query = db.query(KnowledgeBase)
        
        # 如果提供了用户ID且不是获取所有知识库
        if user_id and not include_all:
            # 基于权限获取知识库列表
            permissions_query = db.query(KnowledgeBasePermission.knowledge_base_id).filter(
                KnowledgeBasePermission.user_id == user_id
            )
            
            permitted_kb_ids = [p[0] for p in permissions_query.all()]
            
            # 构建查询：包括用户创建的、有权限的和公开的知识库
            query = query.filter(
                (KnowledgeBase.created_by == user_id) |  # 用户创建的
                (KnowledgeBase.permission == DatasetPermissionEnum.ALL_TEAM) |  # 团队公开的
                (KnowledgeBase.id.in_(permitted_kb_ids))  # 用户有特定权限的
            )
        
        # 如果有搜索词，进行模糊匹配
        if search:
            query = query.filter(KnowledgeBase.name.ilike(f'%{search}%'))
        
        # 获取总数和分页数据
        total = query.count()
        knowledge_bases = query.order_by(KnowledgeBase.created_at.desc()).offset(skip).limit(limit).all()
        
        return knowledge_bases, total
    
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
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if kb:
            # 添加向量存储统计信息
            kb.vector_stats = get_knowledge_base_stats(kb_id)
        return kb
    
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
        kb = db.query(KnowledgeBase).filter(
            KnowledgeBase.id == kb_id
        ).first()
        
        if kb:
            # 添加向量存储统计信息
            kb.vector_stats = get_knowledge_base_stats(kb_id)
            
            # 获取文档完成处理的数量
            completed_docs = 0
            for doc in kb.documents:
                if doc.status == DocumentStatus.COMPLETED:
                    completed_docs += 1
            kb.completed_docs_count = completed_docs
            
        return kb
    
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
        
        # 同步知识库元数据到向量存储
        metadata = {
            "name": kb.name,
            "description": kb.description,
            "embedding_model": kb.embedding_model,
            "chunk_size": kb.chunk_size,
            "chunk_overlap": kb.chunk_overlap,
            "chunking_strategy": kb.chunking_strategy.value if hasattr(kb.chunking_strategy, 'value') else kb.chunking_strategy,
            "updated_at": kb.updated_at.isoformat()
        }
        sync_knowledge_base_metadata(kb.id, metadata)
        
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
        
        # 首先删除向量存储集合
        vector_deleted = delete_collection(kb_id)
        if not vector_deleted:
            logger.warning(f"删除向量存储集合 {kb_id} 失败")
        
        # 删除知识库权限记录
        db.query(KnowledgeBasePermission).filter(
            KnowledgeBasePermission.knowledge_base_id == kb_id
        ).delete(synchronize_session=False)
        
        # 然后删除数据库记录
        db.delete(kb)
        db.commit()
        
        return True
    
    @staticmethod
    def check_knowledge_base_permission(
        db: Session, 
        kb_id: str, 
        user_id: str
    ) -> bool:
        """
        检查用户是否有权限访问知识库
        
        Args:
            db: 数据库会话
            kb_id: 知识库ID
            user_id: 用户ID
            
        Returns:
            用户是否有权限访问
        """
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        
        if not kb:
            return False
        
        # 如果用户是知识库创建者，总是有权限
        if kb.created_by == user_id:
            return True
        
        # 如果知识库对团队所有成员开放，有权限
        if kb.permission == DatasetPermissionEnum.ALL_TEAM:
            return True
        
        # 如果知识库对部分成员开放，检查用户是否在权限列表中
        if kb.permission == DatasetPermissionEnum.PARTIAL_TEAM:
            permission = db.query(KnowledgeBasePermission).filter(
                KnowledgeBasePermission.knowledge_base_id == kb_id,
                KnowledgeBasePermission.user_id == user_id
            ).first()
            
            return permission is not None
        
        # 如果知识库是私有的（只有创建者可见），没有权限
        return False
    
    @staticmethod
    def grant_knowledge_base_permission(
        db: Session,
        kb_id: str,
        user_id: str
    ) -> bool:
        """
        为用户授予知识库访问权限
        
        Args:
            db: 数据库会话
            kb_id: 知识库ID
            user_id: 用户ID
            
        Returns:
            操作是否成功
        """
        # 检查知识库是否存在
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            return False
        
        # 检查权限是否已存在
        existing_permission = db.query(KnowledgeBasePermission).filter(
            KnowledgeBasePermission.knowledge_base_id == kb_id,
            KnowledgeBasePermission.user_id == user_id
        ).first()
        
        if existing_permission:
            # 权限已存在
            return True
        
        # 添加新的权限记录
        new_permission = KnowledgeBasePermission(
            knowledge_base_id=kb_id,
            user_id=user_id
        )
        
        try:
            db.add(new_permission)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"授予知识库权限失败: {str(e)}")
            return False
    
    @staticmethod
    def revoke_knowledge_base_permission(
        db: Session,
        kb_id: str,
        user_id: str
    ) -> bool:
        """
        撤销用户的知识库访问权限
        
        Args:
            db: 数据库会话
            kb_id: 知识库ID
            user_id: 用户ID
            
        Returns:
            操作是否成功
        """
        try:
            # 删除权限记录
            result = db.query(KnowledgeBasePermission).filter(
                KnowledgeBasePermission.knowledge_base_id == kb_id,
                KnowledgeBasePermission.user_id == user_id
            ).delete(synchronize_session=False)
            
            db.commit()
            return result > 0
        except Exception as e:
            db.rollback()
            logger.error(f"撤销知识库权限失败: {str(e)}")
            return False
    
    @staticmethod
    def get_knowledge_base_permissions(
        db: Session,
        kb_id: str
    ) -> List[Dict[str, Any]]:
        """
        获取知识库的权限列表
        
        Args:
            db: 数据库会话
            kb_id: 知识库ID
            
        Returns:
            权限用户列表
        """
        try:
            # 获取权限记录
            permissions = db.query(KnowledgeBasePermission).filter(
                KnowledgeBasePermission.knowledge_base_id == kb_id
            ).all()
            
            # 如果需要，可以在这里获取用户信息
            result = []
            for permission in permissions:
                # 这里可以查询用户表获取更多信息
                result.append({
                    "user_id": permission.user_id,
                    "created_at": permission.created_at
                })
            
            return result
        except Exception as e:
            logger.error(f"获取知识库权限失败: {str(e)}")
            return []
    
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
        # 首先确保知识库存在于数据库中
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"知识库 {kb_id} 不存在"
            )
        
        # 然后确保向量存储集合存在
        if not check_collection_exists(kb_id):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"知识库对应的向量存储集合 {kb_id} 不存在，请重建知识库"
            )
        
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
        
        # 添加向量存储统计信息
        kb.vector_stats = get_knowledge_base_stats(kb_id)
        
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
        knowledge_base_id: str, 
        chunking_config: ChunkingConfig,
        background_tasks: Optional[BackgroundTasks] = None
    ) -> Dict[str, Any]:
        """
        更新知识库分块配置
        
        Args:
            knowledge_base_id: 知识库ID
            chunking_config: 分块配置
            background_tasks: 后台任务
            
        Returns:
            更新结果
        """
        db_knowledge_base = self._get_knowledge_base_by_id(knowledge_base_id)
        if not db_knowledge_base:
            raise HTTPException(status_code=404, detail=f"未找到ID为 {knowledge_base_id} 的知识库")
            
        try:
            # 更新知识库分块配置
            db_knowledge_base.chunk_size = chunking_config.chunk_size
            db_knowledge_base.chunk_overlap = chunking_config.chunk_overlap
            db_knowledge_base.chunking_strategy = chunking_config.chunking_strategy
            
            # 处理自定义分隔符
            if chunking_config.custom_separators is not None:
                db_knowledge_base.custom_separators = json.dumps(chunking_config.custom_separators)
            else:
                db_knowledge_base.custom_separators = None
            
            self.db.add(db_knowledge_base)
            self.db.commit()
            self.db.refresh(db_knowledge_base)
            
            # 如果需要重新分块文档，则在后台处理
            if chunking_config.rechunk_documents and background_tasks:
                background_tasks.add_task(
                    self.rechunk_all_documents, 
                    knowledge_base_id=knowledge_base_id
                )
                
            return {
                "status": "success",
                "message": "知识库分块配置已更新",
                "rechunk_documents": chunking_config.rechunk_documents
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新知识库分块配置出错: {str(e)}")
            raise HTTPException(status_code=500, detail=f"更新知识库分块配置出错: {str(e)}")

    def _prepare_chunking_params(self, knowledge_base: KnowledgeBase) -> Dict[str, Any]:
        """
        准备分块参数
        
        Args:
            knowledge_base: 知识库实例
            
        Returns:
            分块参数字典
        """
        params = {
            "chunk_size": knowledge_base.chunk_size,
            "chunk_overlap": knowledge_base.chunk_overlap,
            "chunking_strategy": knowledge_base.chunking_strategy
        }
        
        # 如果有自定义分隔符，解析并添加到参数中
        if knowledge_base.custom_separators:
            try:
                custom_separators = json.loads(knowledge_base.custom_separators)
                if isinstance(custom_separators, list):
                    params["custom_separators"] = custom_separators
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"解析自定义分隔符出错: {str(e)}")
                
        return params

    async def rechunk_all_documents(self, knowledge_base_id: str) -> None:
        """
        重新分块知识库中的所有文档
        
        Args:
            knowledge_base_id: 知识库ID
        """
        db_knowledge_base = self._get_knowledge_base_by_id(knowledge_base_id)
        if not db_knowledge_base:
            logger.error(f"重新分块时找不到知识库: {knowledge_base_id}")
            return
        
        # 获取知识库中的所有文档
        documents = self.db.query(Document).join(
            knowledge_base_documents,
            knowledge_base_documents.c.document_id == Document.id
        ).filter(
            knowledge_base_documents.c.knowledge_base_id == knowledge_base_id
        ).all()
        
        if not documents:
            logger.warning(f"知识库 {knowledge_base_id} 中没有文档，无需重新分块")
            return
        
        # 重新分块所有文档
        document_ids = [doc.id for doc in documents]
        logger.info(f"开始重新分块知识库 {knowledge_base_id} 中的 {len(document_ids)} 个文档")
        
        # 批量处理文档
        batch_size = 5  # 每批处理的文档数量
        total_batches = (len(document_ids) + batch_size - 1) // batch_size
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(document_ids))
            batch_document_ids = document_ids[start_idx:end_idx]
            
            # 更新处理状态
            self.db.query(Document).filter(
                Document.id.in_(batch_document_ids)
            ).update(
                {"status": DocumentStatus.PENDING.value},
                synchronize_session=False
            )
            self.db.commit()
            
            # 重新处理文档
            await document_processor.batch_process_documents(
                db=self.db,
                document_ids=batch_document_ids,
                knowledge_base_id=knowledge_base_id
            )
            
            # 短暂休眠，避免服务器过载
            await asyncio.sleep(0.5)
        
        logger.info(f"知识库 {knowledge_base_id} 中的所有文档已重新分块完成")

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
        from app.models.database import SessionLocal
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
                await asyncio.sleep(0.5)
            
            logger.info(f"知识库 {kb_id} 的索引重建完成")
            return True
            
        except Exception as e:
            logger.error(f"重建索引失败: {str(e)}")
            return False
        finally:
            new_db.close()

# 创建知识库服务单例
knowledge_base_service = KnowledgeBaseService()

async def create_knowledge_base(kb_data: KnowledgeBaseCreate) -> KnowledgeBase:
    """
    创建新的知识库
    
    Args:
        kb_data: 知识库创建数据
        
    Returns:
        创建的知识库对象
    """
    # 检查是否已存在同名知识库
    existing = await get_knowledge_base_by_name(kb_data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"知识库 '{kb_data.name}' 已存在"
        )
    
    # 创建知识库记录
    kb_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    kb_dict = kb_data.dict(exclude_unset=True)
    kb_dict.update({
        "id": kb_id,
        "created_at": now,
        "updated_at": now,
        "document_count": 0
    })
    
    try:
        # 创建向量存储集合
        ensure_collection_exists(kb_data.name)
        
        # 保存到数据库
        await create_item(KNOWLEDGE_BASE_TABLE, kb_dict)
        
        return KnowledgeBase(**kb_dict)
    except Exception as e:
        logger.error(f"创建知识库失败: {str(e)}")
        # 清理已创建的向量存储集合
        try:
            delete_collection(kb_data.name)
        except Exception as cleanup_error:
            logger.error(f"清理向量存储集合失败: {str(cleanup_error)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建知识库失败: {str(e)}"
        )


async def get_all_knowledge_bases(
    skip: int = 0, 
    limit: int = 100,
    created_by: Optional[str] = None
) -> List[KnowledgeBase]:
    """
    获取所有知识库列表
    
    Args:
        skip: 跳过的记录数
        limit: 返回的最大记录数
        created_by: 按创建者筛选
        
    Returns:
        知识库列表
    """
    filters = {}
    if created_by:
        filters["created_by"] = created_by
        
    try:
        kb_dicts = await get_items(
            KNOWLEDGE_BASE_TABLE, 
            filters=filters,
            skip=skip, 
            limit=limit
        )
        return [KnowledgeBase(**kb) for kb in kb_dicts]
    except Exception as e:
        logger.error(f"获取知识库列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取知识库列表失败: {str(e)}"
        )


async def get_knowledge_base(kb_id: str) -> KnowledgeBase:
    """
    通过ID获取知识库
    
    Args:
        kb_id: 知识库ID
        
    Returns:
        知识库对象
    """
    try:
        kb_dict = await get_item(KNOWLEDGE_BASE_TABLE, kb_id)
        if not kb_dict:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"知识库ID '{kb_id}' 不存在"
            )
        
        return KnowledgeBase(**kb_dict)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取知识库失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取知识库失败: {str(e)}"
        )


async def get_knowledge_base_by_name(name: str) -> Optional[KnowledgeBase]:
    """
    通过名称获取知识库
    
    Args:
        name: 知识库名称
        
    Returns:
        知识库对象，如果不存在则返回None
    """
    try:
        kb_dicts = await get_items(KNOWLEDGE_BASE_TABLE, filters={"name": name}, limit=1)
        if not kb_dicts:
            return None
        
        return KnowledgeBase(**kb_dicts[0])
    except Exception as e:
        logger.error(f"通过名称获取知识库失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"通过名称获取知识库失败: {str(e)}"
        )


async def update_knowledge_base(
    kb_id: str, 
    updates: Dict[str, Any]
) -> KnowledgeBase:
    """
    更新知识库信息
    
    Args:
        kb_id: 知识库ID
        updates: 要更新的字段
        
    Returns:
        更新后的知识库对象
    """
    # 检查知识库是否存在
    kb = await get_knowledge_base(kb_id)
    
    # 准备更新数据
    update_data = {**updates, "updated_at": datetime.utcnow()}
    
    try:
        # 更新数据库记录
        updated_kb = await update_item(KNOWLEDGE_BASE_TABLE, kb_id, update_data)
        if not updated_kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"知识库ID '{kb_id}' 不存在"
            )
        
        return KnowledgeBase(**updated_kb)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新知识库失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新知识库失败: {str(e)}"
        )


async def delete_knowledge_base(kb_id: str) -> bool:
    """
    删除知识库
    
    Args:
        kb_id: 知识库ID
        
    Returns:
        删除是否成功
    """
    # 检查知识库是否存在
    kb = await get_knowledge_base(kb_id)
    
    try:
        # 删除向量存储集合
        delete_collection(kb.name)
        
        # 删除知识库与文档的关联关系
        await delete_item(KNOWLEDGE_BASE_DOCUMENT_TABLE, filters={"kb_id": kb_id}, is_filter=True)
        
        # 删除知识库记录
        result = await delete_item(KNOWLEDGE_BASE_TABLE, kb_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"知识库ID '{kb_id}' 不存在"
            )
        
        return True
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除知识库失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除知识库失败: {str(e)}"
        )


async def get_kb_statistics(kb_id: str) -> KnowledgeBaseStats:
    """
    获取知识库统计信息
    
    Args:
        kb_id: 知识库ID
        
    Returns:
        知识库统计信息
    """
    # 获取知识库基本信息
    kb = await get_knowledge_base(kb_id)
    
    try:
        # 获取向量存储统计信息
        vector_stats = get_knowledge_base_stats(kb.name)
        
        return KnowledgeBaseStats(
            id=kb.id,
            name=kb.name,
            document_count=kb.document_count,
            vector_count=vector_stats.get("count", 0),
            last_updated=vector_stats.get("last_updated"),
            metadata=kb.metadata
        )
    except Exception as e:
        logger.error(f"获取知识库统计信息失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取知识库统计信息失败: {str(e)}"
        )


async def add_document_to_kb(
    kb_id: str,
    document_id: str,
    document_content: str,
    document_metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    添加文档到知识库
    
    Args:
        kb_id: 知识库ID
        document_id: 文档ID
        document_content: 文档内容
        document_metadata: 文档元数据
        
    Returns:
        添加是否成功
    """
    # 检查知识库是否存在
    kb = await get_knowledge_base(kb_id)
    
    # 检查文档是否已添加到该知识库
    existing_docs = await get_items(
        KNOWLEDGE_BASE_DOCUMENT_TABLE, 
        filters={"kb_id": kb_id, "document_id": document_id},
        limit=1
    )
    
    if existing_docs:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"文档 '{document_id}' 已添加到知识库 '{kb.name}'"
        )
    
    try:
        # 添加文档到向量存储
        add_documents_to_knowledge_base(
            kb_name=kb.name,
            documents=[document_content],
            metadatas=[{"document_id": document_id, **(document_metadata or {})}]
        )
        
        # 创建关联记录
        now = datetime.utcnow()
        await create_item(KNOWLEDGE_BASE_DOCUMENT_TABLE, {
            "kb_id": kb_id,
            "document_id": document_id,
            "added_at": now
        })
        
        # 更新知识库文档计数
        await update_item(KNOWLEDGE_BASE_TABLE, kb_id, {
            "document_count": kb.document_count + 1,
            "updated_at": now
        })
        
        return True
    except Exception as e:
        logger.error(f"添加文档到知识库失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"添加文档到知识库失败: {str(e)}"
        )


async def remove_document_from_kb(kb_id: str, document_id: str) -> bool:
    """
    从知识库中移除文档
    
    Args:
        kb_id: 知识库ID
        document_id: 文档ID
        
    Returns:
        移除是否成功
    """
    # 检查知识库是否存在
    kb = await get_knowledge_base(kb_id)
    
    # 检查文档是否已添加到该知识库
    existing_docs = await get_items(
        KNOWLEDGE_BASE_DOCUMENT_TABLE, 
        filters={"kb_id": kb_id, "document_id": document_id},
        limit=1
    )
    
    if not existing_docs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"文档 '{document_id}' 未添加到知识库 '{kb.name}'"
        )
    
    try:
        # 删除关联记录
        result = await delete_item(
            KNOWLEDGE_BASE_DOCUMENT_TABLE, 
            filters={"kb_id": kb_id, "document_id": document_id},
            is_filter=True
        )
        
        if result:
            # 更新知识库文档计数
            now = datetime.utcnow()
            await update_item(KNOWLEDGE_BASE_TABLE, kb_id, {
                "document_count": max(0, kb.document_count - 1),
                "updated_at": now
            })
        
        # 注意: 目前不支持从向量存储中删除特定文档的向量，
        # 这将在未来版本中实现
        
        return True
    except Exception as e:
        logger.error(f"从知识库中移除文档失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"从知识库中移除文档失败: {str(e)}"
        )


async def get_kb_documents(
    kb_id: str,
    skip: int = 0,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    获取知识库中的文档列表
    
    Args:
        kb_id: 知识库ID
        skip: 跳过的记录数
        limit: 返回的最大记录数
        
    Returns:
        文档列表
    """
    # 检查知识库是否存在
    await get_knowledge_base(kb_id)
    
    try:
        # 获取知识库文档关联记录
        doc_records = await get_items(
            KNOWLEDGE_BASE_DOCUMENT_TABLE,
            filters={"kb_id": kb_id},
            skip=skip,
            limit=limit
        )
        
        # 注意: 理想情况下，我们应该同时获取文档的详细信息
        # 但由于文档服务可能在另一个模块中，这里只返回关联信息
        
        return doc_records
    except Exception as e:
        logger.error(f"获取知识库文档列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取知识库文档列表失败: {str(e)}"
        )
