"""
导入测试，验证项目中的关键模块可以成功导入
"""

def test_core_imports():
    """测试核心模块导入"""
    from app.core.config import settings
    assert settings is not None
    assert settings.project_name == "Enterprise RAG System"

def test_schema_imports():
    """测试模式导入"""
    from app.schemas.schemas import RAGQueryRequest, KnowledgeBaseResponse
    assert RAGQueryRequest is not None
    assert KnowledgeBaseResponse is not None

def test_service_imports():
    """测试服务模块导入"""
    from app.services.llm import get_llm
    from app.services.vector_store import get_retriever
    from app.services.rag import generate_rag_response
    from app.services.parser import parse_and_split_document
    
    assert get_llm is not None
    assert get_retriever is not None
    assert generate_rag_response is not None
    assert parse_and_split_document is not None

def test_api_imports():
    """测试API模块导入"""
    from app.api.v1.router import api_router
    from app.api.v1.endpoints.upload import router as upload_router
    from app.api.v1.endpoints.query import router as query_router
    from app.api.v1.endpoints.knowledgebase import router as kb_router
    
    assert api_router is not None
    assert upload_router is not None
    assert query_router is not None
    assert kb_router is not None

def test_celery_imports():
    """测试Celery模块导入"""
    from app.task.celery_app import celery_app
    from app.task.tasks import process_document_batch
    
    assert celery_app is not None
    assert process_document_batch is not None 