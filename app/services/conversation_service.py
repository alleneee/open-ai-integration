"""
对话管理服务
负责创建和管理对话会话、存储和检索消息等
"""
import logging
from typing import List, Dict, Any, Optional, Union, Tuple, AsyncGenerator
from datetime import datetime
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.database import Conversation, Message
from app.models.conversation import (
    ConversationCreate, ConversationUpdate, ConversationSchema, 
    ConversationDetailSchema, MessageCreate, MessageSchema,
    MessageRole, ConversationState, LLMConfig,
    ConversationGenerateRequest, GenerateResponse, RAGGenerateRequest
)
from app.services.llm_service import get_llm_service
from app.services.vector_store import search_knowledge_base

logger = logging.getLogger(__name__)

class ConversationService:
    """对话管理服务类"""
    
    @staticmethod
    def create_conversation(
        db: Session,
        user_id: str,
        conversation_create: ConversationCreate
    ) -> ConversationSchema:
        """
        创建新的对话
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            conversation_create: 对话创建数据
            
        Returns:
            创建的对话
        """
        # 创建对话
        new_conversation = Conversation(
            title=conversation_create.title,
            created_by=user_id,
            meta_data=conversation_create.metadata
        )
        
        # 如果提供了系统提示，添加系统消息
        if conversation_create.metadata and "system_prompt" in conversation_create.metadata:
            system_message = Message(
                conversation_id=new_conversation.id,
                role=MessageRole.SYSTEM,
                content=conversation_create.metadata["system_prompt"]
            )
            new_conversation.messages.append(system_message)
        
        db.add(new_conversation)
        db.commit()
        db.refresh(new_conversation)
        
        # 转换为响应模型
        result = ConversationSchema(
            id=new_conversation.id,
            title=new_conversation.title,
            created_by=new_conversation.created_by,
            created_at=new_conversation.created_at,
            updated_at=new_conversation.updated_at,
            state=new_conversation.state,
            metadata=new_conversation.meta_data,
            message_count=len(new_conversation.messages)
        )
        
        return result
    
    @staticmethod
    def get_conversation(
        db: Session,
        conversation_id: str,
        include_messages: bool = False
    ) -> Union[ConversationSchema, ConversationDetailSchema]:
        """
        获取对话详情
        
        Args:
            db: 数据库会话
            conversation_id: 对话ID
            include_messages: 是否包含消息
            
        Returns:
            对话详情
        """
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if not conversation:
            return None
        
        # 计算消息数量
        message_count = len(conversation.messages)
        
        if include_messages:
            # 包含消息的详细响应
            messages = []
            for msg in conversation.messages:
                messages.append(MessageSchema(
                    id=msg.id,
                    role=msg.role,
                    content=msg.content,
                    created_at=msg.created_at,
                    metadata=msg.meta_data,
                    conversation_id=msg.conversation_id
                ))
            
            return ConversationDetailSchema(
                id=conversation.id,
                title=conversation.title,
                created_by=conversation.created_by,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at,
                state=conversation.state,
                metadata=conversation.meta_data,
                message_count=message_count,
                messages=messages
            )
        else:
            # 不包含消息的简单响应
            return ConversationSchema(
                id=conversation.id,
                title=conversation.title,
                created_by=conversation.created_by,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at,
                state=conversation.state,
                metadata=conversation.meta_data,
                message_count=message_count
            )
    
    @staticmethod
    def list_conversations(
        db: Session,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
        state: Optional[ConversationState] = None
    ) -> List[ConversationSchema]:
        """
        获取用户的对话列表
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            skip: 分页起始位置
            limit: 分页大小
            state: 对话状态过滤
            
        Returns:
            对话列表
        """
        query = db.query(Conversation).filter(
            Conversation.created_by == user_id
        )
        
        if state:
            query = query.filter(Conversation.state == state)
        
        conversations = query.order_by(
            desc(Conversation.updated_at)
        ).offset(skip).limit(limit).all()
        
        # 转换为响应模型
        result = []
        for conv in conversations:
            message_count = len(conv.messages)
            result.append(ConversationSchema(
                id=conv.id,
                title=conv.title,
                created_by=conv.created_by,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                state=conv.state,
                metadata=conv.meta_data,
                message_count=message_count
            ))
        
        return result
    
    @staticmethod
    def update_conversation(
        db: Session,
        conversation_id: str,
        conversation_update: ConversationUpdate
    ) -> Optional[ConversationSchema]:
        """
        更新对话信息
        
        Args:
            db: 数据库会话
            conversation_id: 对话ID
            conversation_update: 更新数据
            
        Returns:
            更新后的对话
        """
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if not conversation:
            return None
        
        # 更新字段
        if conversation_update.title is not None:
            conversation.title = conversation_update.title
            
        if conversation_update.state is not None:
            conversation.state = conversation_update.state
            
        if conversation_update.metadata is not None:
            conversation.meta_data = conversation_update.metadata
        
        # 更新时间
        conversation.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(conversation)
        
        # 转换为响应模型
        message_count = len(conversation.messages)
        return ConversationSchema(
            id=conversation.id,
            title=conversation.title,
            created_by=conversation.created_by,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            state=conversation.state,
            metadata=conversation.meta_data,
            message_count=message_count
        )
    
    @staticmethod
    def delete_conversation(db: Session, conversation_id: str) -> bool:
        """
        删除对话
        
        Args:
            db: 数据库会话
            conversation_id: 对话ID
            
        Returns:
            是否成功删除
        """
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if not conversation:
            return False
        
        # 删除对话（消息会级联删除）
        db.delete(conversation)
        db.commit()
        
        return True
    
    @staticmethod
    def add_message(
        db: Session,
        conversation_id: str,
        message_create: MessageCreate
    ) -> Optional[MessageSchema]:
        """
        向对话添加消息
        
        Args:
            db: 数据库会话
            conversation_id: 对话ID
            message_create: 消息创建数据
            
        Returns:
            创建的消息
        """
        # 检查对话是否存在
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if not conversation:
            return None
        
        # 创建消息
        new_message = Message(
            conversation_id=conversation_id,
            role=message_create.role,
            content=message_create.content,
            meta_data=message_create.metadata
        )
        
        db.add(new_message)
        
        # 更新对话的更新时间
        conversation.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(new_message)
        
        # 转换为响应模型
        return MessageSchema(
            id=new_message.id,
            role=new_message.role,
            content=new_message.content,
            created_at=new_message.created_at,
            metadata=new_message.meta_data,
            conversation_id=new_message.conversation_id
        )
    
    @staticmethod
    async def generate_message(
        db: Session,
        request: ConversationGenerateRequest,
        user_id: str
    ) -> GenerateResponse:
        """
        生成对话消息
        
        Args:
            db: 数据库会话
            request: 消息生成请求
            user_id: 用户ID
            
        Returns:
            生成的消息
        """
        # 获取对话
        conversation = db.query(Conversation).filter(
            Conversation.id == request.conversation_id
        ).first()
        
        if not conversation:
            raise ValueError(f"对话 {request.conversation_id} 不存在")
        
        # 检查用户权限
        if conversation.created_by != user_id:
            raise ValueError(f"用户 {user_id} 无权访问此对话")
        
        # 添加用户消息
        user_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=request.message
        )
        
        db.add(user_message)
        db.commit()
        db.refresh(user_message)
        
        # 获取上下文消息
        context_messages = []
        for msg in conversation.messages:
            context_messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        llm_service = get_llm_service()
        formatted_messages = llm_service.format_messages_for_llm(context_messages)
        
        # 检查是否需要知识库检索
        sources = None
        if request.knowledge_base_ids:
            # 从知识库检索相关文档
            try:
                retrieved_docs = await search_knowledge_base(
                    request.message,
                    request.knowledge_base_ids,
                    top_k=5
                )
                
                # 如果有检索结果，构建RAG提示
                if retrieved_docs:
                    system_prompt = conversation.meta_data.get("system_prompt") if conversation.meta_data else None
                    formatted_messages = llm_service.build_rag_prompt(
                        request.message,
                        retrieved_docs,
                        system_prompt
                    )
                    
                    # 记录检索到的文档源
                    sources = []
                    for doc in retrieved_docs:
                        sources.append({
                            "content": doc.get("content", ""),
                            "source": doc.get("source", ""),
                            "score": doc.get("score", 0.0)
                        })
            except Exception as e:
                logger.error(f"知识库检索失败: {e}")
        
        # 生成助手回复
        try:
            llm_config = request.llm_config or LLMConfig()
            if not request.stream:
                response_text = await llm_service.generate_response(
                    formatted_messages,
                    llm_config,
                    stream=False
                )
                
                # 保存生成的消息
                assistant_message = Message(
                    conversation_id=conversation.id,
                    role=MessageRole.ASSISTANT,
                    content=response_text,
                    meta_data={"sources": sources} if sources else None
                )
                
                db.add(assistant_message)
                
                # 更新对话的更新时间
                conversation.updated_at = datetime.utcnow()
                
                db.commit()
                db.refresh(assistant_message)
                
                # 转换为响应模型
                assistant_message_schema = MessageSchema(
                    id=assistant_message.id,
                    role=assistant_message.role,
                    content=assistant_message.content,
                    created_at=assistant_message.created_at,
                    metadata=assistant_message.meta_data,
                    conversation_id=assistant_message.conversation_id
                )
                
                return GenerateResponse(
                    conversation_id=conversation.id,
                    message=assistant_message_schema,
                    sources=sources
                )
            else:
                # 流式生成需要在API层处理
                return None
        except Exception as e:
            logger.error(f"生成回复失败: {e}")
            raise
    
    @staticmethod
    async def generate_rag_message(
        db: Session,
        request: RAGGenerateRequest,
        user_id: str
    ) -> GenerateResponse:
        """
        生成RAG消息
        
        Args:
            db: 数据库会话
            request: RAG生成请求
            user_id: 用户ID
            
        Returns:
            生成的消息
        """
        conversation_id = request.conversation_id
        
        # 如果未提供对话ID，创建新对话
        if not conversation_id:
            new_conversation = Conversation(
                title=request.message[:30] + "..." if len(request.message) > 30 else request.message,
                created_by=user_id,
                meta_data={"mode": "rag"}
            )
            
            db.add(new_conversation)
            db.commit()
            db.refresh(new_conversation)
            
            conversation_id = new_conversation.id
        else:
            # 检查对话是否存在
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            
            if not conversation:
                raise ValueError(f"对话 {conversation_id} 不存在")
            
            # 检查用户权限
            if conversation.created_by != user_id:
                raise ValueError(f"用户 {user_id} 无权访问此对话")
        
        # 添加用户消息
        user_message = Message(
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=request.message
        )
        
        db.add(user_message)
        db.commit()
        db.refresh(user_message)
        
        # 从知识库检索相关文档
        sources = None
        try:
            retrieved_docs = await search_knowledge_base(
                request.message,
                request.knowledge_base_ids,
                top_k=request.search_top_k,
                score_threshold=request.search_score_threshold
            )
            
            if not retrieved_docs:
                # 没有检索到相关文档
                response_text = "抱歉，我在知识库中没有找到与您问题相关的信息。请尝试调整问题或选择其他知识库。"
                
                assistant_message = Message(
                    conversation_id=conversation_id,
                    role=MessageRole.ASSISTANT,
                    content=response_text
                )
                
                db.add(assistant_message)
                db.commit()
                db.refresh(assistant_message)
                
                # 转换为响应模型
                assistant_message_schema = MessageSchema(
                    id=assistant_message.id,
                    role=assistant_message.role,
                    content=assistant_message.content,
                    created_at=assistant_message.created_at,
                    metadata=assistant_message.meta_data,
                    conversation_id=assistant_message.conversation_id
                )
                
                return GenerateResponse(
                    conversation_id=conversation_id,
                    message=assistant_message_schema,
                    sources=None
                )
                
            # 记录检索到的文档源
            sources = []
            for doc in retrieved_docs:
                sources.append({
                    "content": doc.get("content", ""),
                    "source": doc.get("source", ""),
                    "score": doc.get("score", 0.0)
                })
                
            # 构建RAG提示
            llm_service = get_llm_service()
            system_prompt = None  # 可以从请求或配置中获取
            formatted_messages = llm_service.build_rag_prompt(
                request.message,
                retrieved_docs,
                system_prompt
            )
            
            # 生成助手回复
            llm_config = request.llm_config or LLMConfig()
            if not request.stream:
                response_text = await llm_service.generate_response(
                    formatted_messages,
                    llm_config,
                    stream=False
                )
                
                # 保存生成的消息
                assistant_message = Message(
                    conversation_id=conversation_id,
                    role=MessageRole.ASSISTANT,
                    content=response_text,
                    meta_data={"sources": sources}
                )
                
                db.add(assistant_message)
                
                # 更新对话的更新时间
                conversation = db.query(Conversation).filter(
                    Conversation.id == conversation_id
                ).first()
                conversation.updated_at = datetime.utcnow()
                
                db.commit()
                db.refresh(assistant_message)
                
                # 转换为响应模型
                assistant_message_schema = MessageSchema(
                    id=assistant_message.id,
                    role=assistant_message.role,
                    content=assistant_message.content,
                    created_at=assistant_message.created_at,
                    metadata=assistant_message.meta_data,
                    conversation_id=assistant_message.conversation_id
                )
                
                return GenerateResponse(
                    conversation_id=conversation_id,
                    message=assistant_message_schema,
                    sources=sources
                )
            else:
                # 流式生成需要在API层处理
                return None
        except Exception as e:
            logger.error(f"RAG生成失败: {e}")
            raise

    @staticmethod
    async def generate_message_stream(
        db: Session,
        request: ConversationGenerateRequest,
        user_id: str
    ) -> AsyncGenerator[str, None]:
        """
        流式生成对话消息
        
        Args:
            db: 数据库会话
            request: 消息生成请求
            user_id: 用户ID
            
        Returns:
            生成的消息流
        """
        # 获取对话
        conversation = db.query(Conversation).filter(
            Conversation.id == request.conversation_id
        ).first()
        
        if not conversation:
            raise ValueError(f"对话 {request.conversation_id} 不存在")
        
        # 检查用户权限
        if conversation.created_by != user_id:
            raise ValueError(f"用户 {user_id} 无权访问此对话")
        
        # 添加用户消息
        user_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=request.message
        )
        
        db.add(user_message)
        db.commit()
        db.refresh(user_message)
        
        # 获取上下文消息
        context_messages = []
        for msg in conversation.messages:
            context_messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        llm_service = get_llm_service()
        formatted_messages = llm_service.format_messages_for_llm(context_messages)
        
        # 检查是否需要知识库检索
        sources = None
        if request.knowledge_base_ids:
            # 从知识库检索相关文档
            try:
                retrieved_docs = await search_knowledge_base(
                    request.message,
                    request.knowledge_base_ids,
                    top_k=5
                )
                
                # 如果有检索结果，构建RAG提示
                if retrieved_docs:
                    system_prompt = conversation.meta_data.get("system_prompt") if conversation.meta_data else None
                    formatted_messages = llm_service.build_rag_prompt(
                        request.message,
                        retrieved_docs,
                        system_prompt
                    )
                    
                    # 记录检索到的文档源
                    sources = []
                    for doc in retrieved_docs:
                        sources.append({
                            "content": doc.get("content", ""),
                            "source": doc.get("source", ""),
                            "score": doc.get("score", 0.0)
                        })
            except Exception as e:
                logger.error(f"知识库检索失败: {e}")
        
        # 创建空的助手消息，后续会更新内容
        assistant_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content="",  # 初始内容为空，将通过流式生成填充
            meta_data={"sources": sources} if sources else None
        )
        
        db.add(assistant_message)
        db.commit()
        db.refresh(assistant_message)
        
        # 生成助手回复流
        try:
            llm_config = request.llm_config or LLMConfig()
            response_stream = await llm_service.generate_response(
                formatted_messages,
                llm_config,
                stream=True
            )
            
            full_content = ""
            async for chunk in response_stream:
                full_content += chunk
                yield chunk
            
            # 更新消息内容和对话更新时间
            assistant_message.content = full_content
            conversation.updated_at = datetime.utcnow()
            db.commit()
            
        except Exception as e:
            logger.error(f"流式生成回复失败: {e}")
            # 更新消息为错误信息
            assistant_message.content = f"生成回复时发生错误: {str(e)}"
            assistant_message.meta_data = {"error": str(e)}
            db.commit()
            
            # 将错误传递给调用者
            raise

    @staticmethod
    async def generate_rag_message_stream(
        db: Session,
        request: RAGGenerateRequest,
        user_id: str
    ) -> AsyncGenerator[str, None]:
        """
        流式生成RAG知识库增强回复
        
        Args:
            db: 数据库会话
            request: RAG生成请求
            user_id: 用户ID
            
        Returns:
            生成的消息流
        """
        conversation_id = request.conversation_id
        
        # 如果未提供对话ID，创建新对话
        if not conversation_id:
            new_conversation = Conversation(
                title=request.message[:30] + "..." if len(request.message) > 30 else request.message,
                created_by=user_id,
                meta_data={"mode": "rag"}
            )
            
            db.add(new_conversation)
            db.commit()
            db.refresh(new_conversation)
            
            conversation_id = new_conversation.id
        else:
            # 检查对话是否存在
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            
            if not conversation:
                raise ValueError(f"对话 {conversation_id} 不存在")
            
            # 检查用户权限
            if conversation.created_by != user_id:
                raise ValueError(f"用户 {user_id} 无权访问此对话")
        
        # 添加用户消息
        user_message = Message(
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=request.message
        )
        
        db.add(user_message)
        db.commit()
        db.refresh(user_message)
        
        # 从知识库检索相关文档
        sources = None
        try:
            retrieved_docs = await search_knowledge_base(
                request.message,
                request.knowledge_base_ids,
                top_k=request.search_top_k,
                score_threshold=request.search_score_threshold
            )
            
            if not retrieved_docs:
                # 没有检索到相关文档
                error_message = "抱歉，我在知识库中没有找到与您问题相关的信息。请尝试调整问题或选择其他知识库。"
                
                # 创建助手回复消息
                assistant_message = Message(
                    conversation_id=conversation_id,
                    role=MessageRole.ASSISTANT,
                    content=error_message
                )
                
                db.add(assistant_message)
                db.commit()
                
                # 返回错误消息
                yield error_message
                return
            
            # 记录检索到的文档源
            sources = []
            for doc in retrieved_docs:
                sources.append({
                    "content": doc.get("content", ""),
                    "source": doc.get("source", ""),
                    "score": doc.get("score", 0.0)
                })
            
            # 创建空的助手消息，后续会更新内容
            assistant_message = Message(
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                content="",  # 初始内容为空，将通过流式生成填充
                meta_data={"sources": sources}
            )
            
            db.add(assistant_message)
            db.commit()
            db.refresh(assistant_message)
            
            # 构建RAG提示
            llm_service = get_llm_service()
            system_prompt = None  # 可以从请求或配置中获取
            formatted_messages = llm_service.build_rag_prompt(
                request.message,
                retrieved_docs,
                system_prompt
            )
            
            # 生成助手回复流
            llm_config = request.llm_config or LLMConfig()
            response_stream = await llm_service.generate_response(
                formatted_messages,
                llm_config,
                stream=True
            )
            
            full_content = ""
            async for chunk in response_stream:
                full_content += chunk
                yield chunk
            
            # 更新消息内容和对话更新时间
            assistant_message.content = full_content
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            conversation.updated_at = datetime.utcnow()
            db.commit()
            
        except Exception as e:
            logger.error(f"RAG流式生成失败: {e}")
            # 尝试创建错误消息
            try:
                error_message = Message(
                    conversation_id=conversation_id,
                    role=MessageRole.ASSISTANT,
                    content=f"生成回复时发生错误: {str(e)}",
                    meta_data={"error": str(e)}
                )
                db.add(error_message)
                db.commit()
            except:
                logger.error("无法保存错误消息")
            
            # 将错误传递给调用者
            raise

# 创建对话服务单例
conversation_service = ConversationService()

def get_conversation_service() -> ConversationService:
    """获取对话服务实例"""
    return conversation_service 