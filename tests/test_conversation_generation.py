"""
对话生成功能的测试类
"""
import pytest
import uuid
import json
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.database import Conversation, Message
from app.models.conversation import MessageRole, LLMConfig
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

# 模拟LLM服务
async def mock_generate_response(messages, config, stream=False):
    """模拟生成回复"""
    if stream:
        async def _stream():
            chunks = ["这是", "一个", "测试", "的", "流式", "回复"]
            for chunk in chunks:
                yield chunk
        return _stream()
    else:
        return "这是一个测试回复"

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
        title="测试对话生成",
        created_by="test-user-id",
        meta_data={}
    )
    db.add(test_conv)
    db.commit()
    db.refresh(test_conv)
    
    # 添加系统提示消息
    system_message = Message(
        id=str(uuid.uuid4()),
        conversation_id=test_conv.id,
        role=MessageRole.SYSTEM,
        content="你是一个有帮助的AI助手"
    )
    db.add(system_message)
    
    # 添加一条用户消息
    user_message = Message(
        id=str(uuid.uuid4()),
        conversation_id=test_conv.id,
        role=MessageRole.USER,
        content="你好，请介绍一下自己"
    )
    db.add(user_message)
    
    # 添加一条助手消息
    assistant_message = Message(
        id=str(uuid.uuid4()),
        conversation_id=test_conv.id,
        role=MessageRole.ASSISTANT,
        content="你好！我是一个AI助手，很高兴为你服务。"
    )
    db.add(assistant_message)
    
    db.commit()
    
    yield test_conv
    
    # 清理测试数据
    db.query(Message).filter(Message.conversation_id == test_conv.id).delete()
    db.query(Conversation).filter(Conversation.id == test_conv.id).delete()
    db.commit()

class TestConversationGeneration:
    """对话生成功能测试类"""
    
    @patch("app.services.llm_service.LLMService.generate_response")
    def test_generate_message(self, mock_gen, test_conversation):
        """测试生成对话消息"""
        # 设置模拟返回值
        mock_gen.return_value = "这是一个测试回复"
        
        response = client.post(
            "/api/v1/conversations/generate",
            json={
                "conversation_id": test_conversation.id,
                "message": "请告诉我今天的天气",
                "stream": False,
                "llm_config": {
                    "temperature": 0.7,
                    "max_tokens": 1000
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert data["content"] == "这是一个测试回复"
        assert data["conversation_id"] == test_conversation.id
    
    @patch("app.services.llm_service.LLMService.generate_response")
    @patch("app.services.vector_store.search_knowledge_base")
    def test_generate_rag_message(self, mock_search, mock_gen, test_conversation):
        """测试生成RAG回复"""
        # 设置模拟检索结果
        mock_search.return_value = [
            {
                "content": "今天是晴天，气温25度",
                "source": "weather.txt",
                "score": 0.95
            }
        ]
        
        # 设置模拟生成结果
        mock_gen.return_value = "根据查询，今天是晴天，气温25度"
        
        response = client.post(
            "/api/v1/conversations/rag",
            json={
                "conversation_id": test_conversation.id,
                "message": "今天天气怎么样？",
                "knowledge_base_ids": ["kb-test-id"],
                "stream": False,
                "search_top_k": 5
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert data["content"] == "根据查询，今天是晴天，气温25度"
        assert "sources" in data
        assert len(data["sources"]) > 0
        assert data["sources"][0]["source"] == "weather.txt"
    
    @patch("app.services.llm_service.LLMService.generate_response")
    def test_generate_with_new_conversation(self, mock_gen):
        """测试同时创建对话并生成消息"""
        # 设置模拟返回值
        mock_gen.return_value = "这是一个新对话的回复"
        
        response = client.post(
            "/api/v1/conversations/generate",
            json={
                "message": "这是一个新的对话",
                "stream": False
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data
        assert "content" in data
        assert data["content"] == "这是一个新对话的回复"
        
        # 清理测试数据
        conversation_id = data["conversation_id"]
        client.delete(f"/api/v1/conversations/{conversation_id}")
    
    @patch("app.services.llm_service.LLMService.generate_response")
    def test_generate_with_custom_llm_config(self, mock_gen, test_conversation):
        """测试使用自定义LLM配置生成消息"""
        # 设置模拟返回值
        mock_gen.return_value = "这是使用自定义配置的回复"
        
        response = client.post(
            "/api/v1/conversations/generate",
            json={
                "conversation_id": test_conversation.id,
                "message": "使用自定义配置",
                "stream": False,
                "llm_config": {
                    "temperature": 0.1,
                    "max_tokens": 500,
                    "top_p": 0.9,
                    "model": "test-model"
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "这是使用自定义配置的回复"
        
        # 验证配置是否正确传递给LLM服务
        call_args = mock_gen.call_args
        assert call_args is not None
        
        config_arg = call_args[0][1]  # 获取第二个位置参数（config）
        assert config_arg.temperature == 0.1
        assert config_arg.max_tokens == 500
        assert config_arg.top_p == 0.9
        assert config_arg.model == "test-model" 