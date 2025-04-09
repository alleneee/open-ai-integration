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