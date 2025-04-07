from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
# 从 fastapi.exceptions 移除 RequestValidationError 的特定导入
# from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError # 保留用于处理配置验证错误
import uvicorn
import time

from app.config import settings
from app.routers import upload, query
from app.core.dependencies import get_cached_vector_store # 用于在启动时触发初始化
# 确保 schema 可导入 (应该没问题)
# from app.models.schemas import HTTPValidationError, GenericErrorResponse

def create_app() -> FastAPI:
    _app = FastAPI(
        title="企业级 RAG API",
        description="使用 FastAPI、Langchain 和 Milvus 构建的用于上传文档和查询 RAG 系统的 API。",
        version="0.1.0",
        # 如果需要, 添加其他 OpenAPI 元数据
    )

    # --- 中间件 ---
    _app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], # 为生产环境正确配置允许的源
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    @_app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        """添加处理时间头部的中间件。"""
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response

    # --- 异常处理器 ---
    # 移除自定义的 RequestValidationError 处理器; FastAPI 的默认处理器足以应对 Pydantic V2
    # @_app.exception_handler(RequestValidationError)
    # async def validation_exception_handler(request: Request, exc: RequestValidationError):
    #     return JSONResponse(
    #         status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    #         content={"detail": exc.errors()}, # 使用 Pydantic v1 的 errors()
    #     )

    @_app.exception_handler(ValidationError) # 捕获请求之外的 Pydantic 验证错误 (例如配置)
    async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
        """处理 Pydantic 配置或其他非请求验证错误的处理器。"""
        # Pydantic V2 的 exc.errors() 返回一个字典列表, 对 JSONResponse 来说没问题
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"配置验证错误: {exc.errors()}"},
        )

    @_app.exception_handler(Exception) # 通用后备处理器
    async def generic_exception_handler(request: Request, exc: Exception):
        """处理所有未捕获异常的通用处理器。"""
        # 在实际应用中在此处记录异常回溯信息
        print(f"未处理的异常: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "发生意外的内部服务器错误。"},
        )

    # --- 路由 ---
    # 使用 API 版本控制前缀
    _app.include_router(upload.router, prefix="/api/v1/documents", tags=["文档"])
    _app.include_router(query.router, prefix="/api/v1/rag", tags=["RAG"])

    # --- 生命周期事件 (可选但推荐) ---
    # 在较新的 FastAPI 中, 使用 lifespan 上下文管理器
    # 对于旧版本, 使用 startup/shutdown 事件
    @_app.on_event("startup")
    async def startup_event():
        """应用启动时执行的事件。"""
        print("应用程序启动中...")
        # 尝试在启动时初始化向量存储连接以尽早发现问题
        try:
            _ = get_cached_vector_store() # 调用依赖项以触发连接
            print("向量存储连接检查/初始化成功。")
        except Exception as e:
            print(f"严重: 启动期间初始化向量存储失败: {e}")
            # 决定应用是否应启动失败或以 degraded 状态运行
            # raise RuntimeError("启动时连接向量存储失败。") from e
        print("应用程序启动完成。")

    @_app.on_event("shutdown")
    async def shutdown_event():
        """应用关闭时执行的事件。"""
        print("应用程序关闭中...")
        # 在此处添加任何清理逻辑 (例如, 如果需要, 显式关闭连接)
        # from pymilvus import connections
        # connections.disconnect("default") # 如果需要显式断开连接的示例
        print("应用程序关闭完成。")

    # --- 根路径端点 ---
    @_app.get("/", tags=["健康检查"], include_in_schema=False) # 不在 OpenAPI 文档中显示根路径
    async def read_root():
        """根路径, 返回欢迎信息。"""
        return {"message": "欢迎使用企业级 RAG API"}

    @_app.get("/health", tags=["健康检查"], status_code=status.HTTP_200_OK)
    async def health_check():
        """执行健康检查, 包括检查向量存储连接。"""
        # 基本健康检查 - 可扩展以检查数据库连接等
        try:
            # 如果可能, 检查 Milvus 连接状态
            # from pymilvus import utility
            # 这可能很慢, 谨慎使用或使用专用检查
            # utility.get_connection("default").connected()
            # 一个更简单的检查可能是确保依赖项不引发 503
            _ = get_cached_vector_store()
            return {"status": "ok", "vector_store": "connected"}
        except Exception as e:
            print(f"健康检查失败: {e}")
            # 返回 503 服务不可用状态码
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "error", "detail": "向量存储不可用"}
            )

    return _app

# 创建 FastAPI 应用实例
app = create_app()

# --- 直接使用 uvicorn 运行的主执行块 (通常用于开发) ---
# if __name__ == "__main__":
#     print(f"服务器启动于 {settings.api_host}:{settings.api_port}")
#     uvicorn.run(
#         "app.main:app", # 指向 FastAPI 实例
#         host=settings.api_host,
#         port=settings.api_port,
#         reload=True # 为开发启用重新加载, 在生产中禁用
#     )
