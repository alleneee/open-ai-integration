"""
文档分块管理的测试类
"""
import pytest
import uuid
import json
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.document import Document, Segment, DocumentStatus
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
        segment_count=0
    )
    db.add(test_doc)
    db.commit()
    db.refresh(test_doc)
    yield test_doc
    
    # 清理测试数据
    db.query(Document).filter(Document.id == test_doc.id).delete()
    db.commit()

@pytest.fixture
def test_segment(db: Session, test_document):
    """测试段落fixture"""
    metadata = {"page": 1, "position": "top"}
    test_seg = Segment(
        id=str(uuid.uuid4()),
        document_id=test_document.id,
        content="This is a test segment content for testing purposes.",
        meta_data=json.dumps(metadata),
        chunk_index=1,
        enabled=True,
        status="completed",
        word_count=10,
        token_count=15
    )
    db.add(test_seg)
    db.commit()
    db.refresh(test_seg)
    
    # 更新文档段落数量
    test_document.segment_count = 1
    db.commit()
    
    yield test_seg
    
    # 清理测试数据
    db.query(Segment).filter(Segment.id == test_seg.id).delete()
    db.commit()

class TestSegment:
    """文档分块管理测试类"""
    
    def test_create_segment(self, test_document):
        """测试创建段落"""
        response = client.post(
            "/api/v1/segments/",
            json={
                "document_id": test_document.id,
                "content": "This is a new segment created for testing.",
                "meta_data": {"page": 2, "position": "middle"},
                "chunk_index": 2,
                "enabled": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == test_document.id
        assert data["content"] == "This is a new segment created for testing."
        assert data["meta_data"]["page"] == 2
        
        # 清理测试数据
        client.delete(f"/api/v1/segments/{data['id']}")
    
    def test_get_segment(self, test_segment):
        """测试获取段落详情"""
        response = client.get(f"/api/v1/segments/{test_segment.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_segment.id
        assert data["content"] == test_segment.content
        assert data["meta_data"]["page"] == 1
    
    def test_update_segment(self, test_segment):
        """测试更新段落"""
        response = client.put(
            f"/api/v1/segments/{test_segment.id}",
            json={
                "content": "Updated segment content",
                "meta_data": {"page": 1, "position": "top", "updated": True},
                "enabled": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Updated segment content"
        assert data["meta_data"]["updated"] is True
    
    def test_delete_segment(self, db, test_document):
        """测试删除段落"""
        # 创建临时段落用于删除测试
        metadata = {"page": 3, "temporary": True}
        temp_seg = Segment(
            id=str(uuid.uuid4()),
            document_id=test_document.id,
            content="Temporary segment for deletion test.",
            meta_data=json.dumps(metadata),
            chunk_index=3,
            enabled=True,
            status="completed"
        )
        db.add(temp_seg)
        db.commit()
        db.refresh(temp_seg)
        
        response = client.delete(f"/api/v1/segments/{temp_seg.id}")
        assert response.status_code == 200
        
        # 验证是否已删除
        seg = db.query(Segment).filter(Segment.id == temp_seg.id).first()
        assert seg is None
    
    def test_list_segments(self, test_segment, test_document):
        """测试获取段落列表"""
        response = client.get(
            "/api/v1/segments/",
            params={"document_id": test_document.id}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["items"], list)
        assert data["total"] >= 1
        
        # 检查是否包含测试段落
        seg_ids = [seg["id"] for seg in data["items"]]
        assert test_segment.id in seg_ids
    
    def test_bulk_update_segments(self, test_segment, db, test_document):
        """测试批量更新段落"""
        # 创建额外的测试段落
        metadata = {"page": 4}
        extra_seg = Segment(
            id=str(uuid.uuid4()),
            document_id=test_document.id,
            content="Additional segment for bulk update test.",
            meta_data=json.dumps(metadata),
            chunk_index=4,
            enabled=True,
            status="pending"
        )
        db.add(extra_seg)
        db.commit()
        db.refresh(extra_seg)
        
        response = client.post(
            "/api/v1/segments/bulk-update",
            json={
                "segment_ids": [test_segment.id, extra_seg.id],
                "updates": {
                    "status": "indexed",
                    "enabled": True
                }
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["updated_count"] == 2
        
        # 验证更新是否生效
        updated_segs = db.query(Segment).filter(
            Segment.id.in_([test_segment.id, extra_seg.id])
        ).all()
        for seg in updated_segs:
            assert seg.status == "indexed"
        
        # 清理额外测试数据
        db.query(Segment).filter(Segment.id == extra_seg.id).delete()
        db.commit() 