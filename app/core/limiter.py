"""
速率限制模块
提供API请求速率限制功能，防止API滥用
"""
import logging
from typing import Callable, Optional

from fastapi import Request, Response, Depends
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from redis import asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

async def setup_limiter(app) -> None:
    """
    初始化速率限制器
    
    需要Redis作为后端存储
    """
    try:
        if settings.REDIS_URL:
            redis = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf8",
                decode_responses=True
            )
            await FastAPILimiter.init(redis)
            logger.info("速率限制器已初始化")
        else:
            logger.warning("未提供Redis URL，速率限制未启用")
    except Exception as e:
        logger.error(f"初始化速率限制器时出错: {e}")

def rate_limit(
    times: int = 100, 
    seconds: int = 60,
    is_exempt: Optional[Callable] = None
):
    """
    自定义速率限制装饰器
    
    Args:
        times: 在指定时间段内允许的最大请求次数
        seconds: 时间段（秒）
        is_exempt: 可选的函数，用于判断请求是否豁免速率限制
    
    示例:
    ```python
    # 限制每分钟10个请求
    @router.get("/limited-endpoint")
    @rate_limit(times=10, seconds=60)
    async def limited_endpoint():
        return {"message": "This endpoint is rate limited"}
        
    # 内部API豁免速率限制
    def is_internal_api(request: Request) -> bool:
        return request.headers.get("X-Internal-API") == "true"
        
    @router.get("/api/internal")
    @rate_limit(is_exempt=is_internal_api)
    async def internal_api():
        return {"message": "Internal API"}
    ```
    """
    if is_exempt:
        async def custom_rate_limiter(request: Request, response: Response):
            if await is_exempt(request):
                return
            return await RateLimiter(times=times, seconds=seconds)(request, response)
        return custom_rate_limiter
    else:
        return RateLimiter(times=times, seconds=seconds)

# 常用限制器依赖
strict_limiter = Depends(RateLimiter(times=20, seconds=60))  # 每分钟20个请求
normal_limiter = Depends(RateLimiter(times=60, seconds=60))  # 每分钟60个请求
generous_limiter = Depends(RateLimiter(times=300, seconds=60))  # 每分钟300个请求
