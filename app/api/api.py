"""
API 路由注册
集中注册和管理所有 API 路由
"""
from fastapi import APIRouter

from app.api.routes import documents
from app.api.v1 import auth, knowledge_bases, tasks

# 创建主 API 路由
api_router = APIRouter()

# 注册各个功能模块的路由
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(knowledge_bases.router, prefix="/knowledge-bases", tags=["知识库"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["任务管理"])

# 可在此处添加更多路由，例如：
# from app.api.routes import users
# api_router.include_router(users.router, prefix="/users", tags=["Users"])
