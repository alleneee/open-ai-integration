# app/api/v1/router.py
from fastapi import APIRouter

# Import endpoint routers from the endpoints directory
from app.api.v1.endpoints import upload, query, knowledgebase

api_router = APIRouter()

# Include the endpoint routers.
# Prefixes defined here will be relative to the prefix applied in main.py (e.g., /api/v1)

# Example: Include upload router directly at /api/v1/upload
api_router.include_router(upload.router, prefix="/upload", tags=["Document Upload"])

# Example: Include query router directly at /api/v1/query
api_router.include_router(query.router, prefix="/query", tags=["RAG Query"])

# Example: Include knowledgebase router under /api/v1/knowledgebases
api_router.include_router(knowledgebase.router, prefix="/knowledgebases", tags=["Knowledge Base Management"])

# You can adjust the prefixes and tags as needed for your API structure. 