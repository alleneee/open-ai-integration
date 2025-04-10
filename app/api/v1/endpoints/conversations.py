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
    # current_user: User = Depends(get_current_user)  # 临时注释认证要求
):
    """
    创建新的对话
    
    - **title**: 对话标题（必填）
    - **metadata**: 元数据（可选）
    """
    conversation_service = get_conversation_service()
    try:
        # 临时硬编码用户ID用于测试
        user_id = "test_user_id"  # 正常情况下应该使用 current_user.id
        conversation = conversation_service.create_conversation(
            db=db,
            user_id=user_id,
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
    # current_user: User = Depends(get_current_user)  # 临时注释认证要求
):
    """
    获取当前用户的对话列表，支持分页和状态过滤
    """
    conversation_service = get_conversation_service()
    try:
        # 临时硬编码用户ID用于测试
        user_id = "test_user_id"  # 正常情况下应该使用 current_user.id
        conversations = conversation_service.list_conversations(
            db=db,
            user_id=user_id,
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
async def get_conversation_detail(
    conversation_id: str = Path(..., description="对话ID"),
    db: Session = Depends(get_db),
    # current_user: User = Depends(get_current_user)  # 临时注释认证要求
):
    """
    获取对话详情，包括消息历史
    
    - **conversation_id**: 对话ID（必填）
    """
    conversation_service = get_conversation_service()
    try:
        # 临时硬编码用户ID用于测试
        user_id = "test_user_id"  # 正常情况下应该使用 current_user.id
        
        # 获取对话
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.created_by == user_id
        ).first()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在或您无权访问"
            )
        
        # 获取消息历史
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
        
        # 组装响应
        return ConversationDetailSchema(
            id=conversation.id,
            title=conversation.title,
            created_by=conversation.created_by,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            state=conversation.state,
            metadata=conversation.meta_data,
            messages=messages
        )
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
    summary="更新对话信息"
)
async def update_conversation(
    conversation_update: ConversationUpdate,
    conversation_id: str = Path(..., description="对话ID"),
    db: Session = Depends(get_db),
    # current_user: User = Depends(get_current_user)  # 临时注释认证要求
):
    """
    更新对话信息
    
    - **conversation_id**: 对话ID（必填）
    - **title**: 新的对话标题（可选）
    - **state**: 新的对话状态（可选）
    - **metadata**: 新的元数据（可选）
    """
    conversation_service = get_conversation_service()
    try:
        # 临时硬编码用户ID用于测试
        user_id = "test_user_id"  # 正常情况下应该使用 current_user.id
        
        # 检查对话是否存在
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.created_by == user_id
        ).first()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在或您无权访问"
            )
        
        # 更新对话
        updated_conversation = conversation_service.update_conversation(
            db=db,
            conversation_id=conversation_id,
            conversation_update=conversation_update
        )
        
        if not updated_conversation:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="更新对话失败"
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
    summary="删除对话"
)
async def delete_conversation(
    conversation_id: str = Path(..., description="对话ID"),
    db: Session = Depends(get_db),
    # current_user: User = Depends(get_current_user)  # 临时注释认证要求
):
    """
    删除指定对话
    
    - **conversation_id**: 对话ID（必填）
    """
    conversation_service = get_conversation_service()
    try:
        # 临时硬编码用户ID用于测试
        user_id = "test_user_id"  # 正常情况下应该使用 current_user.id
        
        # 检查对话是否存在
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.created_by == user_id
        ).first()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在或您无权访问"
            )
        
        # 删除对话
        success = conversation_service.delete_conversation(
            db=db,
            conversation_id=conversation_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="删除对话失败"
            )
        
        return {"message": "对话已成功删除"}
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
    # current_user: User = Depends(get_current_user)  # 临时注释认证要求
):
    """
    向对话添加新消息
    
    - **conversation_id**: 对话ID（必填）
    - **role**: 消息角色（必填）
    - **content**: 消息内容（必填）
    - **metadata**: 元数据（可选）
    """
    conversation_service = get_conversation_service()
    try:
        # 临时硬编码用户ID用于测试
        user_id = "test_user_id"  # 正常情况下应该使用 current_user.id
        
        # 检查对话是否存在
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.created_by == user_id
        ).first()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在或您无权访问"
            )
        
        # 添加消息
        message = conversation_service.add_message(
            db=db,
            conversation_id=conversation_id,
            message_create=message_create
        )
        
        if not message:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="添加消息失败"
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
    # current_user: User = Depends(get_current_user)  # 临时注释认证要求
):
    """
    生成对话消息
    
    - **conversation_id**: 对话ID
    - **message**: 用户输入消息
    - **knowledge_base_ids**: 知识库ID列表（可选）
    - **llm_config**: LLM配置（可选）
    - **stream**: 是否使用流式返回（默认为False）
    """
    conversation_service = get_conversation_service()
    try:
        # 临时硬编码用户ID用于测试
        user_id = "test_user_id"  # 正常情况下应该使用 current_user.id
        
        # 检查是否指定了流式输出
        if request.stream:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请使用 /generate/stream 端点进行流式生成"
            )
        
        # 如果未指定对话ID，创建新的对话
        if not request.conversation_id:
            conversation = conversation_service.create_conversation(
                db=db,
                user_id=user_id,
                conversation_create=ConversationCreate(
                    title=request.message[:30] + "..." if len(request.message) > 30 else request.message,
                    metadata={"source": "generate_api"}
                )
            )
            request.conversation_id = conversation.id
            
        # 生成回复
        response = await conversation_service.generate_message(
            db=db,
            request=request,
            user_id=user_id
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
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    # current_user: User = Depends(get_current_user)  # 临时注释认证要求
):
    """
    流式生成对话消息
    
    - **conversation_id**: 对话ID
    - **message**: 用户输入消息
    - **knowledge_base_ids**: 知识库ID列表（可选）
    - **llm_config**: LLM配置（可选）
    - **stream**: 必须为True
    """
    conversation_service = get_conversation_service()
    try:
        # 临时硬编码用户ID用于测试
        user_id = "test_user_id"  # 正常情况下应该使用 current_user.id
        
        # 检查是否指定了流式输出
        if not request.stream:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="此端点仅支持流式生成，请将stream设置为true"
            )
        
        # 如果未指定对话ID，创建新的对话
        if not request.conversation_id:
            conversation = conversation_service.create_conversation(
                db=db,
                user_id=user_id,
                conversation_create=ConversationCreate(
                    title=request.message[:30] + "..." if len(request.message) > 30 else request.message,
                    metadata={"source": "generate_stream_api"}
                )
            )
            request.conversation_id = conversation.id
        
        # 创建并返回流式响应
        async def event_generator():
            try:
                async for chunk in conversation_service.generate_message_stream(
                    db=db,
                    request=request,
                    user_id=user_id
                ):
                    # 将chunk序列化为JSON
                    if isinstance(chunk, str):
                        yield f"data: {json.dumps({'content': chunk})}\n\n"
                    else:
                        yield f"data: {json.dumps(chunk)}\n\n"
                
                # 发送结束事件
                yield "data: [DONE]\n\n"
            except Exception as e:
                error_msg = str(e)
                yield f"data: {json.dumps({'error': error_msg})}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"流式生成消息失败: {str(e)}"
        )


@router.post(
    "/rag",
    response_model=GenerateResponse,
    summary="生成RAG知识库增强回复"
)
async def generate_rag_message(
    request: RAGGenerateRequest,
    db: Session = Depends(get_db),
    # current_user: User = Depends(get_current_user)  # 临时注释认证要求
):
    """
    生成RAG知识库增强回复
    
    - **conversation_id**: 对话ID
    - **message**: 用户输入消息
    - **knowledge_base_ids**: 知识库ID列表（必填）
    - **llm_config**: LLM配置（可选）
    - **stream**: 是否使用流式返回（默认为False）
    """
    conversation_service = get_conversation_service()
    try:
        # 临时硬编码用户ID用于测试
        user_id = "test_user_id"  # 正常情况下应该使用 current_user.id
        
        # 检查是否指定了流式输出
        if request.stream:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请使用 /rag/stream 端点进行流式生成"
            )
        
        # 检查是否提供了知识库ID
        if not request.knowledge_base_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="必须提供至少一个知识库ID"
            )
        
        # 如果未指定对话ID，创建新的对话
        if not request.conversation_id:
            conversation = conversation_service.create_conversation(
                db=db,
                user_id=user_id,
                conversation_create=ConversationCreate(
                    title=request.message[:30] + "..." if len(request.message) > 30 else request.message,
                    metadata={"source": "rag_api", "knowledge_base_ids": request.knowledge_base_ids}
                )
            )
            request.conversation_id = conversation.id
            
        # 包装为ConversationGenerateRequest，添加知识库ID标识
        generate_request = ConversationGenerateRequest(
            conversation_id=request.conversation_id,
            message=request.message,
            knowledge_base_ids=request.knowledge_base_ids,
            llm_config=request.llm_config,
            stream=False
        )
        
        # 生成回复
        response = await conversation_service.generate_message(
            db=db,
            request=generate_request,
            user_id=user_id
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
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    # current_user: User = Depends(get_current_user)  # 临时注释认证要求
):
    """
    流式生成RAG知识库增强回复
    
    - **conversation_id**: 对话ID
    - **message**: 用户输入消息
    - **knowledge_base_ids**: 知识库ID列表（必填）
    - **llm_config**: LLM配置（可选）
    - **stream**: 必须为True
    """
    conversation_service = get_conversation_service()
    try:
        # 临时硬编码用户ID用于测试
        user_id = "test_user_id"  # 正常情况下应该使用 current_user.id
        
        # 检查是否指定了流式输出
        if not request.stream:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="此端点仅支持流式生成，请将stream设置为true"
            )
        
        # 检查是否提供了知识库ID
        if not request.knowledge_base_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="必须提供至少一个知识库ID"
            )
        
        # 如果未指定对话ID，创建新的对话
        if not request.conversation_id:
            conversation = conversation_service.create_conversation(
                db=db,
                user_id=user_id,
                conversation_create=ConversationCreate(
                    title=request.message[:30] + "..." if len(request.message) > 30 else request.message,
                    metadata={"source": "rag_stream_api", "knowledge_base_ids": request.knowledge_base_ids}
                )
            )
            request.conversation_id = conversation.id
        
        # 包装为ConversationGenerateRequest，添加知识库ID标识
        generate_request = ConversationGenerateRequest(
            conversation_id=request.conversation_id,
            message=request.message,
            knowledge_base_ids=request.knowledge_base_ids,
            llm_config=request.llm_config,
            stream=True
        )
        
        # 创建并返回流式响应
        async def event_generator():
            try:
                async for chunk in conversation_service.generate_message_stream(
                    db=db,
                    request=generate_request,
                    user_id=user_id
                ):
                    # 将chunk序列化为JSON
                    if isinstance(chunk, str):
                        yield f"data: {json.dumps({'content': chunk})}\n\n"
                    else:
                        yield f"data: {json.dumps(chunk)}\n\n"
                
                # 发送结束事件
                yield "data: [DONE]\n\n"
            except Exception as e:
                error_msg = str(e)
                yield f"data: {json.dumps({'error': error_msg})}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"流式生成RAG回复失败: {str(e)}"
        )