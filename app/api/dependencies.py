from fastapi import Depends, HTTPException, status

# Update import path for vector_store service
from app.services.vector_store import get_milvus_connection

import logging
logger = logging.getLogger(__name__)

def verify_milvus_connection(_=Depends(get_milvus_connection)):
    """
    一个简单的依赖项，它调用 get_milvus_connection 来确保连接尝试成功。
    如果 get_milvus_connection 内部发生连接错误并抛出 ConnectionError，
    FastAPI 的异常处理器会捕获它。
    这个依赖项本身不返回任何值，仅用于触发连接检查。
    """
    logger.debug("Milvus connection verified via dependency (verify_milvus_connection).")
    pass

# --- 其他潜在的依赖项可以放在这里 ---
# 例如：获取当前用户的依赖项 (如果实现了认证)
# from app.auth.service import get_current_active_user 