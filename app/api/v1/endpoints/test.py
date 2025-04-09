"""
测试接口
提供简单的接口用于测试系统功能
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import datetime
import uuid
from typing import List, Optional, Dict, Any

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.knowledge_base import KnowledgeBase
from app.services.knowledge_base import kb_service
from app.services.vector_store import create_collection
from pydantic import BaseModel

router = APIRouter()

# 测试响应模型
class TestResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime.datetime

@router.get(
    "/list", 
    response_model=List[TestResponse],
    summary="测试列表接口"
)
async def test_list(
    current_user: User = Depends(get_current_user)
):
    """
    返回一个简单的测试列表
    """
    now = datetime.datetime.utcnow()
    
    return [
        TestResponse(
            id="test-1",
            name="测试项目1",
            description="第一个测试项目",
            created_at=now
        ),
        TestResponse(
            id="test-2",
            name="测试项目2",
            description="第二个测试项目",
            created_at=now
        )
    ]

@router.get(
    "/item/{item_id}", 
    response_model=TestResponse,
    summary="测试详情接口"
)
async def test_detail(
    item_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    返回一个简单的测试详情
    """
    now = datetime.datetime.utcnow()
    
    return TestResponse(
        id=item_id,
        name=f"测试项目 {item_id}",
        description=f"这是测试项目 {item_id} 的详细信息",
        created_at=now
    )

@router.get(
    "/create-kb", 
    response_model=Dict[str, Any],
    summary="测试创建知识库接口"
)
async def test_create_kb(
    name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    创建一个测试知识库，不需要认证
    """
    try:
        # 生成随机名称
        random_id = uuid.uuid4().hex[:8]
        kb_name = name or f"测试知识库_{random_id}"
        
        # 创建知识库参数
        from app.models.knowledge_base import KnowledgeBaseCreate, ChunkingStrategy
        
        # 直接创建知识库DB对象
        from app.models.knowledge_base import KnowledgeBaseDB
        
        # 创建知识库
        new_kb = KnowledgeBaseDB(
            id=str(uuid.uuid4()),
            name=kb_name,
            description=f"这是通过测试接口创建的知识库 - {random_id}",
            tenant_id="test",  # 添加测试租户ID
            is_active=True,
            chunk_size=1000,
            chunk_overlap=200,
            chunking_strategy=ChunkingStrategy.RECURSIVE,
            created_by="test-user",
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow()
        )
        
        db.add(new_kb)
        db.commit()
        db.refresh(new_kb)
        
        # 创建向量集合
        from app.services.vector_store import ensure_collection_exists
        
        # 将ID中的连字符替换为下划线，以符合Milvus命名要求
        collection_name = f"kb_{new_kb.id.replace('-', '_')}"
        ensure_collection_exists(collection_name)
        
        return {
            "message": "知识库创建成功",
            "knowledge_base": {
                "id": new_kb.id,
                "name": new_kb.name,
                "description": new_kb.description,
                "created_at": new_kb.created_at
            }
        }
    except Exception as e:
        db.rollback() if hasattr(db, 'rollback') else None
        return {
            "message": f"创建知识库失败: {str(e)}",
            "error": str(e)
        }

@router.post(
    "/upload-document", 
    response_model=Dict[str, Any],
    summary="测试文档上传接口"
)
async def test_upload_document(
    document: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    上传简单的文本文档到指定知识库
    
    Args:
        document: 包含以下字段的JSON对象
            - kb_id: 知识库ID
            - text_content: 文本内容
            - filename: 文件名（可选）
    """
    try:
        kb_id = document.get("kb_id")
        text_content = document.get("text_content")
        filename = document.get("filename", "测试文档.txt")
        
        if not kb_id:
            return {
                "message": "缺少必要参数：kb_id",
                "success": False
            }
            
        if not text_content:
            return {
                "message": "缺少必要参数：text_content",
                "success": False
            }
        
        import tempfile
        import os
        import uuid
        from app.models.document import DocumentCreate, DocumentStatus
        
        # 检查知识库是否存在
        kb = kb_service.get_knowledge_base(db=db, kb_id=kb_id)
        if not kb:
            return {
                "message": f"知识库不存在: {kb_id}",
                "success": False
            }
        
        # 创建临时文件
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, filename)
        
        # 写入文本内容
        with open(temp_file_path, 'w', encoding='utf-8') as f:
            f.write(text_content)
        
        # 处理文档
        from app.services.parser import parse_file_from_path_and_split
        document_chunks = parse_file_from_path_and_split(
            file_path=temp_file_path,
            original_filename=filename,
            chunk_size=kb.chunk_size,
            chunk_overlap=kb.chunk_overlap
        )
        
        if not document_chunks:
            return {
                "message": "无法从文档中提取内容",
                "success": False
            }
        
        # 创建文档记录
        document_id = str(uuid.uuid4())
        document_data = {
            "id": document_id,
            "tenant_id": "test",  # 使用测试租户ID
            "collection_name": kb_id,
            "filename": filename,
            "file_path": temp_file_path,
            "file_size": os.path.getsize(temp_file_path),
            "file_type": "text/plain",
            "status": DocumentStatus.PENDING.value,
            "segment_count": len(document_chunks)
        }
        
        from app.models.document import create_document
        document = create_document(document_data, db=db)
        
        # 确保使用有效的集合名称(添加前缀并替换连字符为下划线)
        from app.services.vector_store import get_standardized_collection_name, ensure_collection_exists
        collection_name = get_standardized_collection_name(kb_id)
        
        # 确保集合存在
        if not ensure_collection_exists(collection_name):
            document.status = DocumentStatus.ERROR.value
            document.error_message = "创建集合失败"
            db.commit()
            return {
                "message": f"创建集合 {collection_name} 失败",
                "success": False
            }
        
        # 将文档添加到向量存储
        from app.services.vector_store import add_documents
        try:
            # 生成唯一ID列表
            vector_ids = [str(uuid.uuid4()) for _ in range(len(document_chunks))]
            
            # 使用LangChain Document对象的page_content和metadata属性
            result = add_documents(
                collection_name=collection_name,
                documents=[chunk.page_content for chunk in document_chunks],
                metadatas=[{
                    "document_id": document_id,
                    "filename": filename,
                    "chunk_index": i,
                    **chunk.metadata  # 包含原始元数据
                } for i, chunk in enumerate(document_chunks)],
                ids=vector_ids  # 添加ID列表
            )
            
            if result:
                # 更新文档状态为已完成
                document.status = DocumentStatus.COMPLETED.value
                document.segment_count = len(document_chunks)
                db.commit()
                
                return {
                    "message": "文档上传并处理成功",
                    "document": {
                        "id": document.id,
                        "filename": document.filename,
                        "status": document.status,
                        "created_at": document.created_at,
                        "segment_count": document.segment_count
                    },
                    "success": True
                }
            else:
                document.status = DocumentStatus.ERROR.value
                document.error_message = "向量存储添加文档失败"
                db.commit()
                return {
                    "message": "向量存储添加文档失败",
                    "success": False
                }
                
        except Exception as e:
            document.status = DocumentStatus.ERROR.value
            document.error_message = str(e)
            db.commit()
            raise e
        
    except Exception as e:
        db.rollback() if hasattr(db, 'rollback') else None
        return {
            "message": f"上传文档失败: {str(e)}",
            "success": False,
            "error": str(e)
        }

@router.post(
    "/query", 
    response_model=Dict[str, Any],
    summary="测试查询接口"
)
async def test_query(
    kb_id: str,
    query_text: str,
    top_k: int = 3,
    db: Session = Depends(get_db)
):
    """
    测试查询知识库中的文档
    
    Args:
        kb_id: 知识库ID
        query_text: 查询文本
        top_k: 返回的结果数量
    """
    try:
        # 检查知识库是否存在
        kb = kb_service.get_knowledge_base(db=db, kb_id=kb_id)
        if not kb:
            return {
                "message": f"知识库不存在: {kb_id}",
                "success": False
            }
        
        # 导入查询服务
        from app.services.vector_store import similarity_search
        
        # 确保集合名称有效
        collection_name = f"kb_{kb_id.replace('-', '_')}" if "-" in kb_id else f"kb_{kb_id}"
        
        # 执行查询
        results = similarity_search(
            collection_name=collection_name, 
            query_text=query_text, 
            top_k=top_k
        )
        
        # 构造返回数据
        sources = []
        for result in results:
            sources.append({
                "content": result.content,
                "metadata": result.metadata,
                "score": result.score if hasattr(result, 'score') else None
            })
        
        return {
            "query": query_text,
            "sources": sources,
            "count": len(sources)
        }
        
    except Exception as e:
        return {
            "message": f"查询失败: {str(e)}",
            "success": False,
            "error": str(e)
        } 