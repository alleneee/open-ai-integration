"""
文档管理的测试类
"""
import pytest
import uuid
import io
import os
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.document import Document, DocumentStatus
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
        segment_count=5,
        word_count=200,
        token_count=250
    )
    db.add(test_doc)
    db.commit()
    db.refresh(test_doc)
    yield test_doc
    
    # 清理测试数据
    db.query(Document).filter(Document.id == test_doc.id).delete()
    db.commit()

class TestDocument:
    """文档管理测试类"""
    
    def test_upload_document(self):
        """测试上传文档"""
        # 创建测试文件
        content = b"This is a test document for document upload testing."
        file = io.BytesIO(content)
        
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test_upload.txt", file, "text/plain")},
            data={
                "tenant_id": "test-tenant",
                "collection_name": "test-collection"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test_upload.txt"
        assert data["file_type"] == "text/plain"
        assert data["status"] == "pending"
        
        # 清理测试数据（如果API不自动删除）
        try:
            client.delete(f"/api/v1/documents/{data['id']}")
        except:
            pass
    
    def test_get_document(self, test_document):
        """测试获取文档详情"""
        response = client.get(f"/api/v1/documents/{test_document.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_document.id
        assert data["filename"] == test_document.filename
        assert data["status"] == test_document.status.value
    
    def test_delete_document(self, db):
        """测试删除文档"""
        # 创建临时文档用于删除测试
        temp_doc = Document(
            id=str(uuid.uuid4()),
            tenant_id="test-tenant",
            collection_name="test-collection",
            filename="temp_document.txt",
            file_path="/tmp/temp_document.txt",
            file_size=512,
            file_type="text/plain",
            status=DocumentStatus.COMPLETED
        )
        db.add(temp_doc)
        db.commit()
        db.refresh(temp_doc)
        
        response = client.delete(f"/api/v1/documents/{temp_doc.id}")
        assert response.status_code == 200
        
        # 验证是否已删除
        doc = db.query(Document).filter(Document.id == temp_doc.id).first()
        assert doc is None
    
    def test_list_documents(self, test_document):
        """测试获取文档列表"""
        response = client.get(
            "/api/v1/documents/",
            params={
                "tenant_id": "test-tenant",
                "collection_name": "test-collection"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["items"], list)
        assert data["total"] >= 1
        
        # 检查是否包含测试文档
        doc_ids = [doc["id"] for doc in data["items"]]
        assert test_document.id in doc_ids
    
    def test_update_document_status(self, test_document, db):
        """测试更新文档状态"""
        response = client.put(
            f"/api/v1/documents/{test_document.id}/status",
            json={
                "status": "processing",
                "error_message": None
            }
        )
        assert response.status_code == 200
        
        # 验证状态是否已更新
        updated_doc = db.query(Document).filter(Document.id == test_document.id).first()
        assert updated_doc.status.value == "processing" 