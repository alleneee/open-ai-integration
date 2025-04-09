"""
LLM服务功能的测试类
"""
import pytest
import os
from unittest.mock import patch, AsyncMock, MagicMock
import asyncio

from app.services.llm_service import LLMService
from app.models.conversation import LLMConfig, MessageRole

class TestLLMService:
    """LLM服务测试类"""
    
    def setup_method(self):
        """每个测试方法执行前的设置"""
        self.llm_service = LLMService()
    
    @patch("app.services.llm_service.AsyncOpenAI")
    def test_format_messages_for_llm(self, mock_openai):
        """测试消息格式化功能"""
        # 测试输入
        messages = [
            {"role": "system", "content": "你是一个有帮助的AI助手"},
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！有什么可以帮助你的吗？"},
            {"role": "user", "content": "讲个笑话"}
        ]
        
        # 调用格式化方法
        formatted = self.llm_service.format_messages_for_llm(messages)
        
        # 验证格式是否正确
        assert len(formatted) == 4
        assert formatted[0]["role"] == "system"
        assert formatted[0]["content"] == "你是一个有帮助的AI助手"
        assert formatted[1]["role"] == "user"
        assert formatted[1]["content"] == "你好"
        assert formatted[2]["role"] == "assistant"
        assert formatted[2]["content"] == "你好！有什么可以帮助你的吗？"
        assert formatted[3]["role"] == "user"
        assert formatted[3]["content"] == "讲个笑话"
    
    def test_build_rag_prompt(self):
        """测试RAG提示构建功能"""
        # 模拟检索结果
        retrieved_docs = [
            {
                "content": "太阳系有8个行星",
                "source": "astronomy.txt",
                "score": 0.95
            },
            {
                "content": "海王星是太阳系最远的行星",
                "source": "planets.txt",
                "score": 0.9
            }
        ]
        
        query = "太阳系有多少个行星？"
        system_prompt = "你是一个专注于天文学的AI助手"
        
        # 构建RAG提示
        rag_messages = self.llm_service.build_rag_prompt(query, retrieved_docs, system_prompt)
        
        # 验证提示构建
        assert len(rag_messages) == 2
        assert rag_messages[0]["role"] == "system"
        assert "天文学" in rag_messages[0]["content"]
        assert rag_messages[1]["role"] == "user"
        assert "太阳系有8个行星" in rag_messages[1]["content"]
        assert "海王星是太阳系最远的行星" in rag_messages[1]["content"]
        assert "太阳系有多少个行星？" in rag_messages[1]["content"]
    
    @patch("app.services.llm_service.AsyncOpenAI")
    async def test_generate_response(self, mock_openai):
        """测试生成回复功能"""
        # 配置模拟返回值
        mock_completion = AsyncMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content="这是一个模拟的回复"))]
        
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        mock_openai.return_value = mock_client
        
        # 测试消息
        messages = [
            {"role": "system", "content": "你是一个有帮助的AI助手"},
            {"role": "user", "content": "你好，请介绍一下自己"}
        ]
        
        # 测试配置
        config = LLMConfig(
            temperature=0.7,
            max_tokens=100,
            model="test-model"
        )
        
        # 调用生成方法
        response = await self.llm_service.generate_response(messages, config)
        
        # 验证结果
        assert response == "这是一个模拟的回复"
        
        # 验证调用参数
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args[1]
        assert call_args["model"] == "test-model"
        assert call_args["temperature"] == 0.7
        assert call_args["max_tokens"] == 100
        assert call_args["messages"] == messages
    
    @patch("app.services.llm_service.AsyncOpenAI")
    async def test_stream_generate_response(self, mock_openai):
        """测试流式生成回复功能"""
        # 模拟流式返回值
        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [MagicMock(delta=MagicMock(content="这是"))]
        
        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [MagicMock(delta=MagicMock(content="一个"))]
        
        mock_chunk3 = MagicMock()
        mock_chunk3.choices = [MagicMock(delta=MagicMock(content="测试回复"))]
        
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=[mock_chunk1, mock_chunk2, mock_chunk3])
        mock_openai.return_value = mock_client
        
        # 测试消息
        messages = [
            {"role": "system", "content": "你是一个有帮助的AI助手"},
            {"role": "user", "content": "你好"}
        ]
        
        # 测试配置
        config = LLMConfig(
            temperature=0.7,
            max_tokens=100,
            model="test-model"
        )
        
        # 调用流式生成方法
        stream_generator = self.llm_service.generate_response(messages, config, stream=True)
        
        # 收集生成的内容
        chunks = []
        async for chunk in stream_generator:
            chunks.append(chunk)
        
        # 验证结果
        assert len(chunks) == 3
        assert chunks[0] == "这是"
        assert chunks[1] == "一个"
        assert chunks[2] == "测试回复"
        
        # 验证调用参数
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args[1]
        assert call_args["model"] == "test-model"
        assert call_args["temperature"] == 0.7
        assert call_args["max_tokens"] == 100
        assert call_args["messages"] == messages
        assert call_args["stream"] is True
    
    def test_parse_llm_config(self):
        """测试LLM配置解析功能"""
        # 创建配置对象
        config = LLMConfig(
            temperature=0.5,
            max_tokens=2000,
            top_p=0.95,
            top_k=40,
            model="test-custom-model"
        )
        
        # 解析配置
        parsed = self.llm_service._parse_llm_config(config)
        
        # 验证解析结果
        assert parsed["temperature"] == 0.5
        assert parsed["max_tokens"] == 2000
        assert parsed["top_p"] == 0.95
        assert "model" in parsed
        assert parsed["model"] == "test-custom-model" 