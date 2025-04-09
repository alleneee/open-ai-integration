"""
知识库管理的测试类
"""
import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
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

class TestKnowledgeBase:
    """知识库管理测试类"""
    
    def test_create_knowledge_base(self):
        """测试创建知识库"""
        response = client.post(
            "/api/v1/knowledge-bases/",
            json={
                "name": "新知识库",
                "description": "这是一个测试创建的知识库",
                "tenant_id": "test-tenant"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "新知识库"
        assert data["description"] == "这是一个测试创建的知识库"
        
        # 清理测试数据
        client.delete(f"/api/v1/knowledge-bases/{data['id']}")
    
    def test_get_knowledge_base(self, test_knowledge_base):
        """测试获取知识库详情"""
        response = client.get(f"/api/v1/knowledge-bases/{test_knowledge_base.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_knowledge_base.id
        assert data["name"] == test_knowledge_base.name
    
    def test_update_knowledge_base(self, test_knowledge_base):
        """测试更新知识库"""
        response = client.put(
            f"/api/v1/knowledge-bases/{test_knowledge_base.id}",
            json={
                "description": "更新后的描述",
                "metadata": {"test_key": "test_value"}
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "更新后的描述"
        assert data["metadata"]["test_key"] == "test_value"
    
    def test_delete_knowledge_base(self, db):
        """测试删除知识库"""
        # 创建临时知识库用于删除测试
        temp_kb = KnowledgeBaseDB(
            id=str(uuid.uuid4()),
            name="临时知识库",
            description="用于删除测试的知识库",
            meta_data={},
            tenant_id="test-tenant",
            is_active=True,
            created_by="test-user-id"
        )
        db.add(temp_kb)
        db.commit()
        db.refresh(temp_kb)
        
        response = client.delete(f"/api/v1/knowledge-bases/{temp_kb.id}")
        assert response.status_code == 200
        
        # 验证是否已删除
        kb = db.query(KnowledgeBaseDB).filter(KnowledgeBaseDB.id == temp_kb.id).first()
        assert kb is None
    
    def test_list_knowledge_bases(self, test_knowledge_base):
        """测试获取知识库列表"""
        response = client.get("/api/v1/knowledge-bases/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["items"], list)
        assert data["total"] >= 1
        
        # 检查是否包含测试知识库
        kb_ids = [kb["id"] for kb in data["items"]]
        assert test_knowledge_base.id in kb_ids 