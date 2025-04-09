"""
知识库与文档关联的测试类
"""
import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.document import Document, DocumentStatus
from app.models.knowledge_base import KnowledgeBaseDB, ChunkingStrategy
from app.db.session import get_db
from app.api.deps import get_current_user
from tests.test_mocks import apply_mocks

# 应用模拟
apply_mocks()

client = TestClient(app)

# 模拟当前用户
def mock_current_user():
    return {
        "id": "test-user-id",
        "username": "testuser",
        "email": "test@example.com",
        "is_superuser": True
    }

# 替换依赖项
app.dependency_overrides[get_current_user] = mock_current_user

@pytest.fixture
def db():
    """数据库会话fixture"""
    try:
        db = next(get_db())
        yield db
    finally:
        db.close()

@pytest.fixture
def test_knowledge_base(db: Session):
    """测试知识库fixture"""
    test_kb = KnowledgeBaseDB(
        id=str(uuid.uuid4()),
        name="测试知识库",
        description="用于测试的知识库",
        meta_data={},
        tenant_id="test-tenant",
        is_active=True,
        chunk_size=1000,
        chunk_overlap=200,
        chunking_strategy=ChunkingStrategy.RECURSIVE,
        created_by="test-user-id"
    )
    db.add(test_kb)
    db.commit()
    db.refresh(test_kb)
    yield test_kb
    
    # 清理测试数据
    db.query(KnowledgeBaseDB).filter(KnowledgeBaseDB.id == test_kb.id).delete()
    db.commit()

@pytest.fixture
def test_document(db: Session):
    """测试文档fixture"""
    test_doc = Document(
        id=str(uuid.uuid4()),
        tenant_id="test-tenant",
        collection_name="test-collection",
        filename="test_document.txt",
        file_path="/tmp/test_document.txt",
        file_size=1024,
        file_type="text/plain",
        status=DocumentStatus.COMPLETED,
        segment_count=0
    )
    db.add(test_doc)
    db.commit()
    db.refresh(test_doc)
    yield test_doc
    
    # 清理测试数据
    db.query(Document).filter(Document.id == test_doc.id).delete()
    db.commit()

class TestKnowledgeBaseDocument:
    """知识库与文档关联测试类"""
    
    def test_add_document_to_knowledge_base(self, test_knowledge_base, test_document):
        """测试添加文档到知识库"""
        response = client.post(
            f"/api/v1/knowledge-bases/{test_knowledge_base.id}/documents",
            json={"document_id": test_document.id}
        )
        assert response.status_code == 200
        
        # 验证文档是否已添加到知识库
        response = client.get(f"/api/v1/knowledge-bases/{test_knowledge_base.id}/documents")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        doc_ids = [doc["id"] for doc in data]
        assert test_document.id in doc_ids
    
    def test_remove_document_from_knowledge_base(self, test_knowledge_base, test_document, db):
        """测试从知识库移除文档"""
        # 首先添加文档到知识库
        test_knowledge_base.documents.append(test_document)
        db.commit()
        
        response = client.delete(
            f"/api/v1/knowledge-bases/{test_knowledge_base.id}/documents/{test_document.id}"
        )
        assert response.status_code == 200
        
        # 验证文档是否已从知识库移除
        response = client.get(f"/api/v1/knowledge-bases/{test_knowledge_base.id}/documents")
        assert response.status_code == 200
        data = response.json()
        
        if data:  # 如果有文档列表
            doc_ids = [doc["id"] for doc in data]
            assert test_document.id not in doc_ids
    
    def test_list_knowledge_base_documents(self, test_knowledge_base, test_document, db):
        """测试获取知识库中的文档列表"""
        # 添加文档到知识库
        test_knowledge_base.documents.append(test_document)
        db.commit()
        
        response = client.get(f"/api/v1/knowledge-bases/{test_knowledge_base.id}/documents")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # 检查是否包含测试文档
        doc_ids = [doc["id"] for doc in data]
        assert test_document.id in doc_ids
        
        # 移除文档
        test_knowledge_base.documents.remove(test_document)
        db.commit()
    
    def test_batch_add_documents(self, test_knowledge_base, test_document, db):
        """测试批量添加文档到知识库"""
        # 创建额外的测试文档
        extra_doc = Document(
            id=str(uuid.uuid4()),
            tenant_id="test-tenant",
            collection_name="test-collection",
            filename="extra_document.txt",
            file_path="/tmp/extra_document.txt",
            file_size=512,
            file_type="text/plain",
            status=DocumentStatus.COMPLETED
        )
        db.add(extra_doc)
        db.commit()
        
        response = client.post(
            f"/api/v1/knowledge-bases/{test_knowledge_base.id}/documents/batch",
            json={"document_ids": [test_document.id, extra_doc.id]}
        )
        assert response.status_code == 200
        
        # 验证文档是否已添加到知识库
        response = client.get(f"/api/v1/knowledge-bases/{test_knowledge_base.id}/documents")
        assert response.status_code == 200
        data = response.json()
        
        doc_ids = [doc["id"] for doc in data]
        assert test_document.id in doc_ids
        assert extra_doc.id in doc_ids
        
        # 清理额外测试数据
        test_knowledge_base.documents.remove(test_document)
        test_knowledge_base.documents.remove(extra_doc)
        db.commit()
        db.query(Document).filter(Document.id == extra_doc.id).delete()
        db.commit()
    
    def test_get_document_knowledge_bases(self, test_knowledge_base, test_document, db):
        """测试获取文档所属的知识库列表"""
        # 添加文档到知识库
        test_knowledge_base.documents.append(test_document)
        db.commit()
        
        response = client.get(f"/api/v1/documents/{test_document.id}/knowledge-bases")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # 检查是否包含测试知识库
        kb_ids = [kb["id"] for kb in data]
        assert test_knowledge_base.id in kb_ids
        
        # 移除文档
        test_knowledge_base.documents.remove(test_document)
        db.commit() 