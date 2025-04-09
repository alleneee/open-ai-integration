"""
LLM服务
提供与语言模型的交互功能，支持对话生成、流式输出等
"""
import os
import logging
import json
from typing import List, Dict, Any, Optional, Union, Generator, AsyncGenerator
import asyncio
from abc import ABC, abstractmethod

from app.core.config import settings
from app.models.conversation import LLMConfig, MessageRole

logger = logging.getLogger(__name__)

class BaseLLMProvider(ABC):
    """LLM提供商基类"""
    
    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        config: LLMConfig,
        stream: bool = False
    ) -> Union[str, AsyncGenerator[str, None]]:
        """
        生成文本
        
        Args:
            messages: 消息列表
            config: LLM配置
            stream: 是否启用流式输出
            
        Returns:
            生成的文本或文本流
        """
        pass

    @abstractmethod
    async def embed_query(self, text: str) -> List[float]:
        """
        获取文本的嵌入向量
        
        Args:
            text: 输入文本
            
        Returns:
            嵌入向量
        """
        pass

class OpenAIProvider(BaseLLMProvider):
    """OpenAI API提供商"""
    
    def __init__(self):
        """初始化OpenAI客户端"""
        try:
            from openai import AsyncOpenAI
            api_key = settings.openai_api_key
            base_url = getattr(settings, "openai_api_base", None)
            
            client_kwargs = {"api_key": api_key}
            if base_url:
                client_kwargs["base_url"] = base_url
                
            self.client = AsyncOpenAI(**client_kwargs)
            logger.info("OpenAI客户端初始化成功")
        except ImportError:
            logger.error("缺少OpenAI Python库，请安装: pip install openai")
            raise
        except Exception as e:
            logger.error(f"初始化OpenAI客户端失败: {e}")
            raise
    
    async def generate(
        self,
        messages: List[Dict[str, str]],
        config: LLMConfig,
        stream: bool = False
    ) -> Union[str, AsyncGenerator[str, None]]:
        """
        使用OpenAI API生成文本
        
        Args:
            messages: 消息列表，格式为[{"role": "user", "content": "你好"}]
            config: LLM配置
            stream: 是否启用流式输出
            
        Returns:
            生成的文本或文本流
        """
        try:
            if stream:
                return self._generate_stream(messages, config)
            
            response = await self.client.chat.completions.create(
                model=config.model_name,
                messages=messages,
                temperature=config.temperature,
                top_p=config.top_p,
                max_tokens=config.max_tokens,
                presence_penalty=config.presence_penalty,
                frequency_penalty=config.frequency_penalty
            )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI生成文本失败: {e}")
            raise
    
    async def _generate_stream(
        self,
        messages: List[Dict[str, str]],
        config: LLMConfig
    ) -> AsyncGenerator[str, None]:
        """生成流式文本"""
        try:
            response = await self.client.chat.completions.create(
                model=config.model_name,
                messages=messages,
                temperature=config.temperature,
                top_p=config.top_p,
                max_tokens=config.max_tokens,
                presence_penalty=config.presence_penalty,
                frequency_penalty=config.frequency_penalty,
                stream=True
            )
            
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"OpenAI流式生成失败: {e}")
            raise
    
    async def embed_query(self, text: str) -> List[float]:
        """获取文本的嵌入向量"""
        try:
            embedding_model = settings.embedding_model_name
            response = await self.client.embeddings.create(
                model=embedding_model,
                input=text
            )
            
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"获取嵌入向量失败: {e}")
            raise

class LLMService:
    """LLM服务类，封装不同LLM提供商的接口"""
    
    def __init__(self):
        """初始化LLM服务"""
        self.providers = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """初始化所有可用的LLM提供商"""
        # 初始化OpenAI提供商
        if settings.openai_api_key:
            try:
                self.providers["openai"] = OpenAIProvider()
                self.default_provider = "openai"
                logger.info("已初始化OpenAI提供商")
            except Exception as e:
                logger.warning(f"初始化OpenAI提供商失败: {e}")
        else:
            logger.warning("未配置OpenAI API密钥，无法使用OpenAI模型")
        
        # 将来可以添加其他提供商（如本地模型）
        # if settings.local_model_path:
        #     try:
        #         self.providers["local"] = LocalModelProvider()
        #         logger.info("已初始化本地模型提供商")
        #     except Exception as e:
        #         logger.warning(f"初始化本地模型提供商失败: {e}")
    
    def get_provider(self, provider_name: Optional[str] = None) -> BaseLLMProvider:
        """获取指定的提供商实例"""
        provider = provider_name or self.default_provider
        
        if not provider or provider not in self.providers:
            available = ", ".join(self.providers.keys())
            raise ValueError(f"提供商 '{provider}' 不可用，可用的提供商: {available}")
        
        return self.providers[provider]
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        config: Optional[LLMConfig] = None,
        stream: bool = False,
        provider_name: Optional[str] = None
    ) -> Union[str, AsyncGenerator[str, None]]:
        """
        生成响应
        
        Args:
            messages: 消息列表
            config: LLM配置
            stream: 是否启用流式输出
            provider_name: LLM提供商名称
            
        Returns:
            生成的文本或文本流
        """
        provider = self.get_provider(provider_name)
        config = config or LLMConfig()
        
        return await provider.generate(messages, config, stream)
    
    def format_messages_for_llm(
        self,
        conversation_messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        格式化消息列表，用于发送给LLM
        
        Args:
            conversation_messages: 对话消息列表
            system_prompt: 系统提示，用于设置助手的行为
            
        Returns:
            格式化后的消息列表
        """
        formatted_messages = []
        
        # 添加系统提示（如果提供）
        if system_prompt:
            formatted_messages.append({
                "role": MessageRole.SYSTEM.value,
                "content": system_prompt
            })
        
        # 添加对话消息
        for msg in conversation_messages:
            formatted_messages.append({
                "role": msg["role"].value if hasattr(msg["role"], "value") else msg["role"],
                "content": msg["content"]
            })
        
        return formatted_messages
    
    def build_rag_prompt(
        self,
        query: str,
        retrieved_docs: List[Dict[str, Any]],
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        构建检索增强生成（RAG）提示
        
        Args:
            query: 用户查询
            retrieved_docs: 检索到的文档列表
            system_prompt: 系统提示
            
        Returns:
            格式化的消息列表
        """
        messages = []
        
        # 系统提示
        if not system_prompt:
            system_prompt = """你是一个智能助手，下面是用户的问题和从知识库中检索到的相关信息。
请基于检索到的信息回答用户问题。如果检索信息中没有相关内容，请如实告知用户。
回答应专业、准确、有条理，并引用相关的知识库内容。"""
        
        messages.append({
            "role": MessageRole.SYSTEM.value,
            "content": system_prompt
        })
        
        # 构建上下文信息
        context = "以下是从知识库中检索到的相关信息：\n\n"
        
        for i, doc in enumerate(retrieved_docs):
            content = doc.get("content", "")
            source = doc.get("source", "未知来源")
            context += f"[{i+1}] {source}\n{content}\n\n"
        
        # 将上下文作为系统消息发送
        messages.append({
            "role": MessageRole.SYSTEM.value,
            "content": context
        })
        
        # 用户查询
        messages.append({
            "role": MessageRole.USER.value,
            "content": query
        })
        
        return messages

# 创建LLM服务单例
llm_service = LLMService()

def get_llm_service() -> LLMService:
    """获取LLM服务实例"""
    return llm_service 