"""
公共 API 路由
包含不需要认证的端点
"""
from fastapi import APIRouter
import datetime
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter()

# --- Test Endpoint Schemas ---
class TestResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime.datetime

# --- Knowledge Base Endpoint Schemas ---
class TestKnowledgeBaseSchema(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    created_by: Optional[str] = None

# --- Public Test Endpoint ---
@router.get(
    "/test", 
    response_model=List[TestResponse],
    summary="公开测试接口，无需认证"
)
async def public_test():
    """
    返回一个简单的测试列表，无需认证
    """
    now = datetime.datetime.utcnow()
    
    return [
        TestResponse(
            id="public-1",
            name="公开测试项目1",
            description="第一个公开测试项目",
            created_at=now
        ),
        TestResponse(
            id="public-2",
            name="公开测试项目2",
            description="第二个公开测试项目",
            created_at=now
        )
    ]

# --- Public Knowledge Base Endpoint ---
@router.get(
    "/knowledge-bases", 
    response_model=List[TestKnowledgeBaseSchema],
    summary="公开的知识库列表，无需认证"
)
async def public_list_knowledge_bases():
    """
    公开接口，直接返回一个硬编码的知识库列表，无需认证
    """
    # 直接构造一个硬编码的响应
    now = datetime.datetime.utcnow()
    
    return [
        TestKnowledgeBaseSchema(
            id="public-kb-1",
            name="公开测试知识库1",
            description="第一个公开测试知识库",
            created_at=now,
            updated_at=now,
            created_by="system"
        ),
        TestKnowledgeBaseSchema(
            id="public-kb-2",
            name="公开测试知识库2",
            description="第二个公开测试知识库",
            created_at=now,
            updated_at=now,
            created_by="system"
        )
    ] 