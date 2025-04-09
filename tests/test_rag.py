"""
检索增强生成(RAG)功能的测试类
"""
import pytest
import uuid
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.database import Conversation, Message
from app.models.knowledge_base import KnowledgeBaseDB
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
        name="测试RAG知识库",
        description="用于RAG测试的知识库",
        meta_data={},
        tenant_id="test-tenant",
        is_active=True,
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
def test_conversation(db: Session):
    """测试对话fixture"""
    test_conv = Conversation(
        id=str(uuid.uuid4()),
        title="测试RAG对话",
        created_by="test-user-id",
        meta_data={"mode": "rag"}
    )
    db.add(test_conv)
    db.commit()
    db.refresh(test_conv)
    yield test_conv
    
    # 清理测试数据
    db.query(Message).filter(Message.conversation_id == test_conv.id).delete()
    db.query(Conversation).filter(Conversation.id == test_conv.id).delete()
    db.commit()

class TestRAG:
    """RAG功能测试类"""
    
    @patch("app.services.vector_store.search_knowledge_base")
    @patch("app.services.llm_service.LLMService.generate_response")
    @patch("app.services.llm_service.LLMService.build_rag_prompt")
    def test_rag_generation(self, mock_build_prompt, mock_gen, mock_search, test_knowledge_base, test_conversation):
        """测试RAG生成功能"""
        # 设置检索结果模拟
        mock_search.return_value = [
            {
                "content": "中国的首都是北京",
                "source": "geography.txt",
                "score": 0.95
            },
            {
                "content": "北京是中华人民共和国的首都",
                "source": "china.txt",
                "score": 0.92
            }
        ]
        
        # 设置提示构建模拟
        mock_build_prompt.return_value = [
            {"role": "system", "content": "你是一个基于检索的问答助手"},
            {"role": "user", "content": "根据以下信息回答问题：\n\n中国的首都是北京\n北京是中华人民共和国的首都\n\n问题：中国的首都是哪里？"}
        ]
        
        # 设置生成结果模拟
        mock_gen.return_value = "根据检索的信息，中国的首都是北京。"
        
        # 发送RAG请求
        response = client.post(
            "/api/v1/conversations/rag",
            json={
                "message": "中国的首都是哪里？",
                "knowledge_base_ids": [test_knowledge_base.id],
                "conversation_id": test_conversation.id,
                "stream": False
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert data["content"] == "根据检索的信息，中国的首都是北京。"
        assert "sources" in data
        assert len(data["sources"]) == 2
        assert data["sources"][0]["source"] == "geography.txt"
        assert data["sources"][1]["source"] == "china.txt"
    
    @patch("app.services.vector_store.search_knowledge_base")
    def test_no_search_results(self, mock_search, test_knowledge_base, test_conversation):
        """测试无检索结果的情况"""
        # 设置空检索结果
        mock_search.return_value = []
        
        # 发送RAG请求
        response = client.post(
            "/api/v1/conversations/rag",
            json={
                "message": "这个问题在知识库中没有相关信息",
                "knowledge_base_ids": [test_knowledge_base.id],
                "conversation_id": test_conversation.id,
                "stream": False
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert "找不到" in data["content"] or "没有找到" in data["content"] or "未找到" in data["content"]
    
    @patch("app.services.vector_store.search_knowledge_base")
    @patch("app.services.llm_service.LLMService.generate_response")
    @patch("app.services.llm_service.LLMService.build_rag_prompt")
    def test_rag_with_score_threshold(self, mock_build_prompt, mock_gen, mock_search, test_knowledge_base):
        """测试带有分数阈值的RAG检索"""
        # 设置检索结果模拟
        mock_search.return_value = [
            {
                "content": "Python是一种编程语言",
                "source": "python.txt",
                "score": 0.85
            }
        ]
        
        # 设置提示构建模拟
        mock_build_prompt.return_value = [
            {"role": "system", "content": "你是一个基于检索的问答助手"},
            {"role": "user", "content": "根据以下信息回答问题：\n\nPython是一种编程语言\n\n问题：Python是什么？"}
        ]
        
        # 设置生成结果模拟
        mock_gen.return_value = "Python是一种编程语言。"
        
        # 发送RAG请求，设置较高的分数阈值
        response = client.post(
            "/api/v1/conversations/rag",
            json={
                "message": "Python是什么？",
                "knowledge_base_ids": [test_knowledge_base.id],
                "stream": False,
                "search_score_threshold": 0.8
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert data["content"] == "Python是一种编程语言。"
        
        # 验证搜索调用时使用了正确的分数阈值
        mock_search.assert_called_with(
            "Python是什么？", 
            [test_knowledge_base.id], 
            top_k=5,
            score_threshold=0.8
        )
    
    @patch("app.services.vector_store.search_knowledge_base")
    @patch("app.services.llm_service.LLMService.generate_response")
    def test_new_conversation_with_rag(self, mock_gen, mock_search, test_knowledge_base):
        """测试创建新对话并使用RAG生成回复"""
        # 设置检索结果模拟
        mock_search.return_value = [
            {
                "content": "太阳系有8个行星",
                "source": "astronomy.txt",
                "score": 0.9
            }
        ]
        
        # 设置生成结果模拟
        mock_gen.return_value = "太阳系有8个行星，它们是：水星、金星、地球、火星、木星、土星、天王星和海王星。"
        
        # 发送没有conversation_id的RAG请求
        response = client.post(
            "/api/v1/conversations/rag",
            json={
                "message": "太阳系有多少个行星？",
                "knowledge_base_ids": [test_knowledge_base.id],
                "stream": False
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert "conversation_id" in data
        assert data["content"] == "太阳系有8个行星，它们是：水星、金星、地球、火星、木星、土星、天王星和海王星。"
        
        # 检查是否正确创建了新对话
        new_conversation_id = data["conversation_id"]
        response = client.get(f"/api/v1/conversations/{new_conversation_id}")
        assert response.status_code == 200
        conv_data = response.json()
        assert conv_data["id"] == new_conversation_id
        assert "mode" in conv_data["metadata"]
        assert conv_data["metadata"]["mode"] == "rag"
        
        # 验证对话包含正确的消息
        assert len(conv_data["messages"]) >= 2  # 至少包含用户问题和AI回复
        
        # 清理测试数据
        client.delete(f"/api/v1/conversations/{new_conversation_id}") 