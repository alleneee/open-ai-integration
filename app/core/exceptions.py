"""
异常处理模块
提供自定义异常类和全局异常处理
"""
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.core.config import settings


class BaseAppException(Exception):
    """应用基础异常"""
    def __init__(self, code: int = 500, message: str = "服务器内部错误"):
        self.code = code
        self.message = message
        super().__init__(self.message)


class DocumentProcessingException(BaseAppException):
    """文档处理异常"""
    def __init__(self, message: str = "文档处理失败", code: int = 500):
        super().__init__(code=code, message=message)


class DocumentNotFoundException(BaseAppException):
    """文档不存在异常"""
    def __init__(self, document_id: str):
        super().__init__(code=404, message=f"文档不存在: {document_id}")


class PermissionDeniedException(BaseAppException):
    """权限拒绝异常"""
    def __init__(self, message: str = "无权限执行此操作"):
        super().__init__(code=403, message=message)


class TenantRequiredException(BaseAppException):
    """租户必需异常"""
    def __init__(self):
        super().__init__(code=401, message="未提供租户ID")


# 异常处理器
async def app_exception_handler(request: Request, exc: BaseAppException):
    """处理自定义应用异常"""
    return JSONResponse(
        status_code=exc.code,
        content={"detail": exc.message}
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """处理HTTPException异常"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理请求验证异常"""
    errors = []
    for error in exc.errors():
        error_msg = {
            "loc": error.get("loc", []),
            "msg": error.get("msg", ""),
            "type": error.get("type", "")
        }
        errors.append(error_msg)
        
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "输入验证错误",
            "errors": errors
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """处理通用异常"""
    # 在生产环境不返回详细错误信息，而只返回通用错误消息
    if settings.ENVIRONMENT == "production":
        content = {"detail": "服务器内部错误"}
    else:
        content = {"detail": str(exc)}
        
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
        content=content
    )


def register_exception_handlers(app):
    """注册所有异常处理器到FastAPI应用"""
    app.add_exception_handler(BaseAppException, app_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
