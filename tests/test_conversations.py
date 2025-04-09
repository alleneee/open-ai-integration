"""
对话管理功能的测试类
"""
import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.database import Conversation, Message
from app.models.conversation import MessageRole, ConversationState
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
def test_conversation(db: Session):
    """测试对话fixture"""
    test_conv = Conversation(
        id=str(uuid.uuid4()),
        title="测试对话",
        created_by="test-user-id",
        state=ConversationState.ACTIVE,
        meta_data={"test": "metadata"}
    )
    db.add(test_conv)
    db.commit()
    db.refresh(test_conv)
    
    # 添加一条测试消息
    test_message = Message(
        id=str(uuid.uuid4()),
        conversation_id=test_conv.id,
        role=MessageRole.USER,
        content="测试消息内容"
    )
    db.add(test_message)
    db.commit()
    
    yield test_conv
    
    # 清理测试数据
    db.query(Message).filter(Message.conversation_id == test_conv.id).delete()
    db.query(Conversation).filter(Conversation.id == test_conv.id).delete()
    db.commit()

class TestConversation:
    """对话管理测试类"""
    
    def test_create_conversation(self):
        """测试创建对话"""
        response = client.post(
            "/api/v1/conversations/",
            json={
                "title": "新建测试对话",
                "metadata": {"source": "test"}
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "新建测试对话"
        assert data["metadata"]["source"] == "test"
        
        # 清理测试数据
        client.delete(f"/api/v1/conversations/{data['id']}")
    
    def test_get_conversation(self, test_conversation):
        """测试获取对话详情"""
        response = client.get(f"/api/v1/conversations/{test_conversation.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_conversation.id
        assert data["title"] == test_conversation.title
        assert len(data["messages"]) >= 1
    
    def test_list_conversations(self, test_conversation):
        """测试获取对话列表"""
        response = client.get("/api/v1/conversations/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # 检查是否包含测试对话
        conv_ids = [conv["id"] for conv in data]
        assert test_conversation.id in conv_ids
    
    def test_update_conversation(self, test_conversation):
        """测试更新对话"""
        response = client.put(
            f"/api/v1/conversations/{test_conversation.id}",
            json={
                "title": "更新后的对话标题",
                "state": "ARCHIVED",
                "metadata": {"updated": True}
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "更新后的对话标题"
        assert data["state"] == "ARCHIVED"
        assert data["metadata"]["updated"] is True
    
    def test_delete_conversation(self, db):
        """测试删除对话"""
        # 创建临时对话用于删除测试
        temp_conv = Conversation(
            id=str(uuid.uuid4()),
            title="临时对话",
            created_by="test-user-id"
        )
        db.add(temp_conv)
        db.commit()
        db.refresh(temp_conv)
        
        response = client.delete(f"/api/v1/conversations/{temp_conv.id}")
        assert response.status_code == 200
        
        # 验证是否已删除
        conv = db.query(Conversation).filter(Conversation.id == temp_conv.id).first()
        assert conv is None
    
    def test_add_message(self, test_conversation):
        """测试向对话添加消息"""
        response = client.post(
            f"/api/v1/conversations/{test_conversation.id}/messages",
            json={
                "role": "assistant",
                "content": "这是一条测试回复",
                "metadata": {"test": True}
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "assistant"
        assert data["content"] == "这是一条测试回复"
        assert data["metadata"]["test"] is True
        
        # 验证消息是否已添加到数据库
        response = client.get(f"/api/v1/conversations/{test_conversation.id}")
        conv_data = response.json()
        messages = [msg for msg in conv_data["messages"] if msg["role"] == "assistant"]
        assert any(msg["content"] == "这是一条测试回复" for msg in messages) 