"""
文档处理服务
提供文档的解析、分块和索引功能
"""
import logging
import json
import asyncio
from typing import List, Dict, Any, Optional, Union
from sqlalchemy.orm import Session

from app.models.document import Document, Segment, DocumentStatus
from app.models.knowledge_base import KnowledgeBase
from app.services.document_chunker import document_chunker
from app.services.vector_store import add_documents_to_knowledge_base
from app.models.database import SessionLocal

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """
    文档处理类
    提供文档分块、索引和管理功能
    """
    
    async def batch_process_documents(
        self, 
        db: Session, 
        document_ids: List[str],
        knowledge_base_id: str
    ) -> Dict[str, Any]:
        """
        批量处理多个文档
        
        Args:
            db: 数据库会话
            document_ids: 要处理的文档ID列表
            knowledge_base_id: 知识库ID
            
        Returns:
            处理结果统计
        """
        # 获取知识库信息
        knowledge_base = db.query(KnowledgeBase).filter(
            KnowledgeBase.id == knowledge_base_id
        ).first()
        
        if not knowledge_base:
            return {
                "success": False,
                "error": f"知识库 {knowledge_base_id} 不存在"
            }
        
        # 获取分块参数
        chunking_params = {
            "chunk_size": knowledge_base.chunk_size,
            "chunk_overlap": knowledge_base.chunk_overlap,
            "chunking_strategy": knowledge_base.chunking_strategy
        }
        
        # 如果有自定义分隔符
        if knowledge_base.custom_separators:
            try:
                custom_separators = json.loads(knowledge_base.custom_separators)
                if isinstance(custom_separators, list):
                    chunking_params["custom_separators"] = custom_separators
            except:
                logger.warning(f"解析知识库 {knowledge_base_id} 的自定义分隔符失败")
        
        # 处理每个文档
        results = {
            "total": len(document_ids),
            "success": 0,
            "failed": 0,
            "details": []
        }
        
        for doc_id in document_ids:
            try:
                # 获取文档信息
                document = db.query(Document).filter(
                    Document.id == doc_id
                ).first()
                
                if not document:
                    results["failed"] += 1
                    results["details"].append({
                        "document_id": doc_id,
                        "status": "failed",
                        "error": "文档不存在"
                    })
                    continue
                
                # 更新文档状态为处理中
                document.status = DocumentStatus.PROCESSING
                db.commit()
                
                # 处理文档（分块）
                await self.process_single_document(
                    db=db,
                    document=document,
                    kb_id=knowledge_base_id,
                    chunking_params=chunking_params
                )
                
                results["success"] += 1
                results["details"].append({
                    "document_id": doc_id,
                    "filename": document.filename,
                    "status": "success",
                    "segment_count": document.segment_count
                })
                
            except Exception as e:
                logger.exception(f"处理文档 {doc_id} 时出错: {e}")
                
                # 更新文档状态为错误
                try:
                    document = db.query(Document).filter(
                        Document.id == doc_id
                    ).first()
                    if document:
                        document.status = DocumentStatus.ERROR
                        document.error_message = str(e)
                        db.commit()
                except:
                    pass
                
                results["failed"] += 1
                results["details"].append({
                    "document_id": doc_id,
                    "status": "failed",
                    "error": str(e)
                })
        
        return results
    
    async def process_single_document(
        self, 
        db: Session,
        document: Document,
        kb_id: str,
        chunking_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        处理单个文档
        
        Args:
            db: 数据库会话
            document: 文档对象
            kb_id: 知识库ID
            chunking_params: 分块参数
            
        Returns:
            处理结果
        """
        try:
            # 如果未提供分块参数，获取知识库的分块参数
            if not chunking_params:
                knowledge_base = db.query(KnowledgeBase).filter(
                    KnowledgeBase.id == kb_id
                ).first()
                
                if not knowledge_base:
                    raise ValueError(f"知识库 {kb_id} 不存在")
                
                chunking_params = {
                    "chunk_size": knowledge_base.chunk_size,
                    "chunk_overlap": knowledge_base.chunk_overlap,
                    "chunking_strategy": knowledge_base.chunking_strategy
                }
                
                # 如果有自定义分隔符
                if knowledge_base.custom_separators:
                    try:
                        custom_separators = json.loads(knowledge_base.custom_separators)
                        if isinstance(custom_separators, list):
                            chunking_params["custom_separators"] = custom_separators
                    except:
                        logger.warning(f"解析知识库 {kb_id} 的自定义分隔符失败")
            
            # 更新文档状态为处理中
            document.status = DocumentStatus.PROCESSING
            db.commit()
            
            # 分块
            chunks = document_chunker.chunk_document(
                document.file_path,
                document.filename,
                **chunking_params
            )
            
            if not chunks:
                raise ValueError("文档分块后未产生任何内容")
            
            # 清除之前的段落
            db.query(Segment).filter(
                Segment.document_id == document.id
            ).delete(synchronize_session=False)
            
            # 添加新段落
            for i, chunk in enumerate(chunks):
                # 准备元数据
                metadata = chunk.metadata
                metadata["document_id"] = document.id
                metadata["chunk_id"] = f"{document.id}_{i}"
                metadata["knowledge_base_id"] = kb_id
                
                # 序列化元数据
                metadata_json = json.dumps(metadata)
                
                # 创建段落记录
                segment = Segment(
                    document_id=document.id,
                    content=chunk.page_content,
                    meta_data=metadata_json,
                    chunk_index=i,
                    enabled=1
                )
                db.add(segment)
            
            # 更新文档状态
            document.status = DocumentStatus.COMPLETED
            document.segment_count = len(chunks)
            document.error_message = None
            db.commit()
            
            # 准备向量存储添加的数据
            texts = [chunk.page_content for chunk in chunks]
            metadatas = [chunk.metadata for chunk in chunks]
            
            # 添加到向量存储
            add_documents_to_knowledge_base(
                kb_id=kb_id,
                documents=texts,
                metadatas=metadatas
            )
            
            return {
                "success": True,
                "document_id": document.id,
                "segment_count": len(chunks)
            }
            
        except Exception as e:
            logger.exception(f"处理文档 {document.id} 时出错: {e}")
            
            # 更新文档状态为错误
            document.status = DocumentStatus.ERROR
            document.error_message = str(e)
            db.commit()
            
            raise
    
    def process_document(
        self, 
        db: Session, 
        document_id: str, 
        knowledge_base_id: str
    ) -> None:
        """
        异步处理文档，适合在API调用中使用
        
        Args:
            db: 数据库会话
            document_id: 文档ID
            knowledge_base_id: 知识库ID
        """
        # 获取文档对象
        document = db.query(Document).filter(
            Document.id == document_id
        ).first()
        
        if not document:
            logger.error(f"文档 {document_id} 不存在")
            return
        
        # 创建异步任务处理文档
        async def _process():
            # 创建新的数据库会话
            new_db = SessionLocal()
            try:
                # 重新获取文档和知识库信息
                doc = new_db.query(Document).filter(
                    Document.id == document_id
                ).first()
                
                kb = new_db.query(KnowledgeBase).filter(
                    KnowledgeBase.id == knowledge_base_id
                ).first()
                
                if not doc:
                    logger.error(f"文档 {document_id} 不存在")
                    return
                
                if not kb:
                    logger.error(f"知识库 {knowledge_base_id} 不存在")
                    return
                
                # 处理文档
                await self.process_single_document(
                    db=new_db,
                    document=doc,
                    kb_id=knowledge_base_id
                )
                
            except Exception as e:
                logger.exception(f"异步处理文档 {document_id} 时出错: {e}")
            finally:
                new_db.close()
        
        # 更新文档状态为处理中
        document.status = DocumentStatus.PROCESSING
        db.commit()
        
        # 启动异步任务
        asyncio.create_task(_process())
        

# 创建单例
document_processor = DocumentProcessor()
