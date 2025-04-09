"""
对话管理API
提供对话的创建、查询、更新、删除和消息生成功能
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import asyncio
import json

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.database import Conversation, Message
from app.models.conversation import (
    ConversationCreate,
    ConversationUpdate,
    ConversationSchema,
    ConversationDetailSchema,
    MessageCreate,
    MessageSchema,
    MessageRole,
    ConversationState,
    LLMConfig,
    ConversationGenerateRequest,
    GenerateResponse,
    RAGGenerateRequest
)
from app.services.conversation_service import get_conversation_service
from app.services.llm_service import get_llm_service

router = APIRouter()


@router.post(
    "/",
    response_model=ConversationSchema,
    status_code=status.HTTP_201_CREATED,
    summary="创建对话"
)
async def create_conversation(
    conversation_create: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建新的对话
    
    - **title**: 对话标题（必填）
    - **metadata**: 元数据（可选）
    """
    conversation_service = get_conversation_service()
    try:
        conversation = conversation_service.create_conversation(
            db=db,
            user_id=current_user.id,
            conversation_create=conversation_create
        )
        return conversation
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建对话失败: {str(e)}"
        )


@router.get(
    "/",
    response_model=List[ConversationSchema],
    summary="获取对话列表"
)
async def list_conversations(
    skip: int = Query(0, ge=0, description="分页起始位置"),
    limit: int = Query(20, ge=1, le=100, description="分页大小"),
    state: Optional[ConversationState] = Query(None, description="对话状态"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户的对话列表，支持分页和状态过滤
    """
    conversation_service = get_conversation_service()
    try:
        conversations = conversation_service.list_conversations(
            db=db,
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            state=state
        )
        return conversations
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取对话列表失败: {str(e)}"
        )


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetailSchema,
    summary="获取对话详情"
)
async def get_conversation(
    conversation_id: str = Path(..., description="对话ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取指定对话的详细信息，包括消息历史
    """
    conversation_service = get_conversation_service()
    try:
        conversation = conversation_service.get_conversation(
            db=db,
            conversation_id=conversation_id,
            include_messages=True
        )
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"对话 {conversation_id} 未找到"
            )
        
        # 检查权限
        if conversation.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限访问此对话"
            )
            
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取对话详情失败: {str(e)}"
        )


@router.put(
    "/{conversation_id}",
    response_model=ConversationSchema,
    summary="更新对话"
)
async def update_conversation(
    conversation_update: ConversationUpdate,
    conversation_id: str = Path(..., description="对话ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新对话信息
    
    - **title**: 对话标题（可选）
    - **state**: 对话状态（可选）
    - **metadata**: 元数据（可选）
    """
    conversation_service = get_conversation_service()
    try:
        # 检查对话是否存在
        conversation = conversation_service.get_conversation(
            db=db,
            conversation_id=conversation_id
        )
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"对话 {conversation_id} 未找到"
            )
        
        # 检查权限
        if conversation.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限更新此对话"
            )
        
        # 更新对话
        updated_conversation = conversation_service.update_conversation(
            db=db,
            conversation_id=conversation_id,
            conversation_update=conversation_update
        )
        
        return updated_conversation
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新对话失败: {str(e)}"
        )


@router.delete(
    "/{conversation_id}",
    response_model=Dict[str, Any],
    summary="删除对话"
)
async def delete_conversation(
    conversation_id: str = Path(..., description="对话ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除指定的对话
    """
    conversation_service = get_conversation_service()
    try:
        # 检查对话是否存在
        conversation = conversation_service.get_conversation(
            db=db,
            conversation_id=conversation_id
        )
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"对话 {conversation_id} 未找到"
            )
        
        # 检查权限
        if conversation.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限删除此对话"
            )
        
        # 删除对话
        success = conversation_service.delete_conversation(
            db=db,
            conversation_id=conversation_id
        )
        
        if success:
            return {"message": "对话已成功删除"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="删除对话失败"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除对话失败: {str(e)}"
        )


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageSchema,
    summary="向对话添加消息"
)
async def add_message(
    message_create: MessageCreate,
    conversation_id: str = Path(..., description="对话ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    向指定对话添加新消息
    
    - **role**: 消息角色（system/user/assistant）
    - **content**: 消息内容
    - **metadata**: 元数据（可选）
    """
    conversation_service = get_conversation_service()
    try:
        # 检查对话是否存在
        conversation = conversation_service.get_conversation(
            db=db,
            conversation_id=conversation_id
        )
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"对话 {conversation_id} 未找到"
            )
        
        # 检查权限
        if conversation.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="没有权限向此对话添加消息"
            )
        
        # 添加消息
        message = conversation_service.add_message(
            db=db,
            conversation_id=conversation_id,
            message_create=message_create
        )
        
        return message
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"添加消息失败: {str(e)}"
        )


@router.post(
    "/generate",
    response_model=GenerateResponse,
    summary="生成对话消息"
)
async def generate_message(
    request: ConversationGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    生成对话消息
    
    - **conversation_id**: 对话ID
    - **message**: 用户消息
    - **knowledge_base_ids**: 知识库ID列表（可选）
    - **llm_config**: LLM配置（可选）
    - **stream**: 是否流式生成（默认False）
    
    如果设置了stream=True，请使用/generate/stream端点
    """
    if request.stream:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="流式生成请使用 /generate/stream 端点"
        )
    
    conversation_service = get_conversation_service()
    try:
        response = await conversation_service.generate_message(
            db=db,
            request=request,
            user_id=current_user.id
        )
        
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成消息失败: {str(e)}"
        )


@router.post(
    "/generate/stream",
    summary="流式生成对话消息"
)
async def generate_message_stream(
    request: ConversationGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    流式生成对话消息
    
    返回Server-Sent Events流，前端需要使用EventSource接收
    """
    if not request.stream:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="非流式生成请使用 /generate 端点"
        )
    
    try:
        # 获取对话
        conversation_service = get_conversation_service()
        llm_service = get_llm_service()
        
        # 检查对话是否存在和权限
        conversation = db.query(Conversation).filter(
            Conversation.id == request.conversation_id
        ).first()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"对话 {request.conversation_id} 不存在"
            )
        
        if conversation.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此对话"
            )
        
        # 添加用户消息
        user_message = MessageCreate(
            role=MessageRole.USER,
            content=request.message
        )
        
        conversation_service.add_message(
            db=db, 
            conversation_id=request.conversation_id,
            message_create=user_message
        )
        
        # 获取上下文消息
        context_messages = []
        for msg in conversation.messages:
            context_messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        formatted_messages = llm_service.format_messages_for_llm(context_messages)
        
        # 检查是否需要知识库检索
        sources = None
        if request.knowledge_base_ids:
            from app.services.vector_store import search_knowledge_base
            # 从知识库检索相关文档
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
        
        # 获取流式响应生成器
        llm_config = request.llm_config or LLMConfig()
        stream_generator = llm_service.generate_response(
            formatted_messages,
            llm_config,
            stream=True
        )
        
        # 创建新的助手消息
        assistant_message = MessageCreate(
            role=MessageRole.ASSISTANT,
            content="",  # 将在流式生成过程中更新
            metadata={"sources": sources} if sources else None
        )
        
        assistant_msg = conversation_service.add_message(
            db=db,
            conversation_id=request.conversation_id,
            message_create=assistant_message
        )
        
        # 转为流式响应
        async def event_generator():
            full_content = ""
            
            try:
                async for content_chunk in stream_generator:
                    full_content += content_chunk
                    
                    # 构建SSE事件
                    data = {
                        "type": "chunk",
                        "content": content_chunk,
                        "message_id": assistant_msg.id,
                        "conversation_id": request.conversation_id
                    }
                    
                    yield f"data: {json.dumps(data)}\n\n"
                    
                    # 适当暂停，避免过快发送
                    await asyncio.sleep(0.01)
                
                # 更新消息内容
                db.query(Message).filter(
                    Message.id == assistant_msg.id
                ).update({
                    "content": full_content
                })
                db.commit()
                
                # 发送完成事件
                data = {
                    "type": "done",
                    "message_id": assistant_msg.id,
                    "conversation_id": request.conversation_id,
                    "sources": sources
                }
                yield f"data: {json.dumps(data)}\n\n"
                
            except Exception as e:
                # 发送错误事件
                error_data = {
                    "type": "error",
                    "error": str(e),
                    "message_id": assistant_msg.id,
                    "conversation_id": request.conversation_id
                }
                yield f"data: {json.dumps(error_data)}\n\n"
                
                # 更新消息内容，标记为错误
                db.query(Message).filter(
                    Message.id == assistant_msg.id
                ).update({
                    "content": full_content + "\n[生成错误]",
                    "meta_data": {"error": str(e), "sources": sources}
                })
                db.commit()
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"流式生成失败: {str(e)}"
        )


@router.post(
    "/rag",
    response_model=GenerateResponse,
    summary="生成RAG知识库增强回复"
)
async def generate_rag_message(
    request: RAGGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    生成基于检索增强的回复
    
    - **message**: 用户消息
    - **knowledge_base_ids**: 知识库ID列表
    - **conversation_id**: 对话ID（可选，不提供则创建新对话）
    - **llm_config**: LLM配置（可选）
    - **stream**: 是否流式生成（默认False）
    - **search_top_k**: 检索结果数量（默认5）
    - **search_score_threshold**: 检索分数阈值（默认0.5）
    
    如果设置了stream=True，请使用/rag/stream端点
    """
    if request.stream:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="流式生成请使用 /rag/stream 端点"
        )
    
    if not request.knowledge_base_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="必须提供至少一个知识库ID"
        )
    
    conversation_service = get_conversation_service()
    try:
        response = await conversation_service.generate_rag_message(
            db=db,
            request=request,
            user_id=current_user.id
        )
        
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成RAG回复失败: {str(e)}"
        )


@router.post(
    "/rag/stream",
    summary="流式生成RAG知识库增强回复"
)
async def generate_rag_message_stream(
    request: RAGGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    流式生成基于检索增强的回复
    
    返回Server-Sent Events流，前端需要使用EventSource接收
    """
    if not request.stream:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="非流式生成请使用 /rag 端点"
        )
    
    if not request.knowledge_base_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="必须提供至少一个知识库ID"
        )
    
    try:
        # 获取服务
        conversation_service = get_conversation_service()
        llm_service = get_llm_service()
        
        # 处理对话ID（创建或检查）
        conversation_id = request.conversation_id
        conversation = None
        
        if conversation_id:
            # 检查对话是否存在
            conversation = db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            
            if not conversation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"对话 {conversation_id} 不存在"
                )
            
            # 检查权限
            if conversation.created_by != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权访问此对话"
                )
        else:
            # 创建新对话
            new_conversation = Conversation(
                title=request.message[:30] + "..." if len(request.message) > 30 else request.message,
                created_by=current_user.id,
                meta_data={"mode": "rag"}
            )
            
            db.add(new_conversation)
            db.commit()
            db.refresh(new_conversation)
            
            conversation = new_conversation
            conversation_id = conversation.id
        
        # 添加用户消息
        user_message = MessageCreate(
            role=MessageRole.USER,
            content=request.message
        )
        
        conversation_service.add_message(
            db=db, 
            conversation_id=conversation_id,
            message_create=user_message
        )
        
        # 从知识库检索相关文档
        from app.services.vector_store import search_knowledge_base
        retrieved_docs = await search_knowledge_base(
            request.message,
            request.knowledge_base_ids,
            top_k=request.search_top_k,
            score_threshold=request.search_score_threshold
        )
        
        if not retrieved_docs:
            # 创建助手消息
            no_results_msg = "抱歉，我在知识库中没有找到与您问题相关的信息。请尝试调整问题或选择其他知识库。"
            assistant_message = MessageCreate(
                role=MessageRole.ASSISTANT,
                content=no_results_msg
            )
            
            assistant_msg = conversation_service.add_message(
                db=db,
                conversation_id=conversation_id,
                message_create=assistant_message
            )
            
            # 返回无结果响应
            async def no_results_generator():
                data = {
                    "type": "done",
                    "message_id": assistant_msg.id,
                    "conversation_id": conversation_id,
                    "content": no_results_msg,
                    "sources": None
                }
                yield f"data: {json.dumps(data)}\n\n"
            
            return StreamingResponse(
                no_results_generator(),
                media_type="text/event-stream"
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
        system_prompt = None
        formatted_messages = llm_service.build_rag_prompt(
            request.message,
            retrieved_docs,
            system_prompt
        )
        
        # 获取流式响应生成器
        llm_config = request.llm_config or LLMConfig()
        stream_generator = llm_service.generate_response(
            formatted_messages,
            llm_config,
            stream=True
        )
        
        # 创建新的助手消息
        assistant_message = MessageCreate(
            role=MessageRole.ASSISTANT,
            content="",  # 将在流式生成过程中更新
            metadata={"sources": sources}
        )
        
        assistant_msg = conversation_service.add_message(
            db=db,
            conversation_id=conversation_id,
            message_create=assistant_message
        )
        
        # 转为流式响应
        async def event_generator():
            full_content = ""
            
            try:
                # 发送检索结果事件
                retrieval_data = {
                    "type": "retrieval",
                    "sources": sources,
                    "message_id": assistant_msg.id,
                    "conversation_id": conversation_id
                }
                yield f"data: {json.dumps(retrieval_data)}\n\n"
                
                # 流式生成
                async for content_chunk in stream_generator:
                    full_content += content_chunk
                    
                    # 构建SSE事件
                    data = {
                        "type": "chunk",
                        "content": content_chunk,
                        "message_id": assistant_msg.id,
                        "conversation_id": conversation_id
                    }
                    
                    yield f"data: {json.dumps(data)}\n\n"
                    
                    # 适当暂停，避免过快发送
                    await asyncio.sleep(0.01)
                
                # 更新消息内容
                db.query(Message).filter(
                    Message.id == assistant_msg.id
                ).update({
                    "content": full_content
                })
                db.commit()
                
                # 发送完成事件
                data = {
                    "type": "done",
                    "message_id": assistant_msg.id,
                    "conversation_id": conversation_id,
                    "sources": sources
                }
                yield f"data: {json.dumps(data)}\n\n"
                
            except Exception as e:
                # 发送错误事件
                error_data = {
                    "type": "error",
                    "error": str(e),
                    "message_id": assistant_msg.id,
                    "conversation_id": conversation_id
                }
                yield f"data: {json.dumps(error_data)}\n\n"
                
                # 更新消息内容，标记为错误
                db.query(Message).filter(
                    Message.id == assistant_msg.id
                ).update({
                    "content": full_content + "\n[生成错误]",
                    "meta_data": {"error": str(e), "sources": sources}
                })
                db.commit()
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"流式生成RAG回复失败: {str(e)}"
        ) 