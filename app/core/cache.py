"""
缓存模块
提供应用程序范围的缓存功能
"""
import logging
from typing import Any, Optional, Union, List, Dict

from fastapi import FastAPI
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
from redis import asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

async def setup_cache(app: FastAPI) -> None:
    """配置并初始化缓存系统"""
    try:
        if settings.REDIS_URL:
            redis = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf8",
                decode_responses=True
            )
            FastAPICache.init(
                RedisBackend(redis),
                prefix=f"{settings.project_name}_cache",
                expire=settings.CACHE_EXPIRE_SECONDS
            )
            logger.info(f"缓存已初始化，使用Redis后端 {settings.REDIS_URL}")
        else:
            logger.warning("未提供Redis URL，缓存未启用")
    except Exception as e:
        logger.error(f"初始化缓存时出错: {e}")
