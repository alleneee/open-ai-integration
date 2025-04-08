import time
import logging
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from contextlib import asynccontextmanager

# Updated import paths
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.cache import setup_cache
from app.api.api import api_router # 导入主API路由
from app.models.database import initialize_db
from app.services.vector_store import get_milvus_connection, _get_embedding_instance

# Configure logging
logging.basicConfig(level=settings.log_level.upper(), format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Application Lifecycle ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic - runs before application startup
    logger.info("应用程序启动...")
    
    # 初始化数据库
    try:
        initialize_db()
        logger.info("数据库初始化成功")
    except Exception as e:
        logger.critical(f"数据库初始化失败: {e}")
    
    # 初始化缓存系统
    try:
        await setup_cache(app)
        logger.info("缓存系统初始化成功")
    except Exception as e:
        logger.warning(f"缓存系统初始化失败: {e}，将继续运行但无缓存支持")
        
    # 确保 Milvus 连接在启动时尝试
    try:
        get_milvus_connection()  # 此函数现在处理连接逻辑
        logger.info("启动期间 Milvus 连接检查成功")
    except ConnectionError as e:
        logger.critical(f"严重错误: 启动期间连接到 Milvus 失败: {e}。应用程序可能无法正常运行。")
    except Exception as e:
        logger.critical(f"严重错误: 启动时 Milvus 连接检查期间发生意外错误: {e}")

    # 初始化嵌入模型实例（可选，有助于尽早捕获错误）
    try:
        _get_embedding_instance()
        logger.info("启动期间嵌入模型实例初始化成功")
    except Exception as e:
        logger.critical(f"严重错误: 启动期间初始化嵌入模型失败: {e}")

    logger.info("应用程序启动完成")
    
    yield  # 这里会暂停执行，直到应用关闭
    
    # Shutdown logic - runs during application shutdown
    logger.info("应用程序关闭...")
    # 清理资源
    try:
        from pymilvus import connections
        if connections.has_connection("default"):
            connections.disconnect("default")
            logger.info("Milvus 连接 'default' 已关闭")
    except Exception as e:
        logger.error(f"关闭期间断开与 Milvus 的连接时出错: {e}")
    logger.info("应用程序关闭完成")

# Create the FastAPI application
app = FastAPI(
    title=settings.project_name,
    version=settings.project_version,
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    docs_url=f"{settings.api_v1_prefix}/docs",
    redoc_url=f"{settings.api_v1_prefix}/redoc",
    lifespan=lifespan
)

# --- 注册统一异常处理器 ---
register_exception_handlers(app)

# --- Middleware ---
# CORS
if settings.cors_origins:
    # Convert comma-separated string in env var to list if needed
    origins = []
    if isinstance(settings.cors_origins, str):
        origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
    elif isinstance(settings.cors_origins, list):
        origins = [str(origin) for origin in settings.cors_origins]

    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        logger.info(f"CORS middleware enabled for origins: {origins}")
    else:
        logger.warning("CORS_ORIGINS is set but resulted in an empty list. CORS disabled.")

# Add X-Process-Time header
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}"
    logger.debug(f"Request {request.method} {request.url.path} processed in {process_time:.4f} secs")
    return response

# --- Routers ---
# 包含主 API 路由
app.include_router(api_router, prefix=settings.api_v1_prefix)

# --- Root Endpoint ---
@app.get("/", tags=["Root"], include_in_schema=False)  # 从文档中隐藏根目录
async def read_root():
    """根路径，提供一个简单的欢迎消息和版本信息。"""
    return {
        "message": f"欢迎使用 {settings.project_name}!",
        "version": settings.project_version,
        "docs_url": app.docs_url
    }

# 添加健康检查端点
@app.get("/health", tags=["Health Check"], status_code=status.HTTP_200_OK)
async def health_check():
    """执行基本健康检查，检查 Milvus 连接。"""
    # 检查 Milvus 连接状态
    milvus_status = "unavailable"
    try:
        from pymilvus import connections, utility
        if not connections.has_connection("default"):
            get_milvus_connection()  # 如果尚未连接，请尝试连接
        utility.list_collections(using="default")  # 轻量级检查
        milvus_status = "ok"
    except Exception as e:
        logger.warning(f"健康检查: Milvus 连接失败 - {e}")
        milvus_status = "error"

    # 未来: 添加 LLM 可用性检查
    if milvus_status == "ok":
        return {"status": "ok", "milvus_connection": milvus_status}
    else:
        # 如果关键依赖项出现故障，则返回 503
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail={"status": "error", "milvus_connection": milvus_status}
        )
