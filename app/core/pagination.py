"""
分页工具模块
提供标准化的分页支持和响应格式
"""
import logging
from typing import TypeVar, Generic, Sequence, List, Optional, Union, Dict, Any

from fastapi import Query, Depends
from fastapi_pagination import Page, Params, paginate
from fastapi_pagination.bases import AbstractPage, AbstractParams
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

T = TypeVar('T')

class PaginationParams(BaseModel):
    """自定义分页参数"""
    page: int = Field(1, ge=1, description="页码，从1开始")
    size: int = Field(20, ge=1, le=100, description="每页条数，最大100")

    def to_fastapi_params(self) -> Params:
        """转换为FastAPI分页参数"""
        return Params(page=self.page, size=self.size)

    @classmethod
    def as_query_params(
        cls,
        page: int = Query(1, ge=1, description="页码，从1开始"),
        size: int = Query(20, ge=1, le=100, description="每页条数，最大100"),
    ) -> "PaginationParams":
        """作为查询参数使用"""
        return cls(page=page, size=size)

class PageResponse(Page[T], Generic[T]):
    """标准分页响应"""
    # 继承自fastapi_pagination的Page，保持一致的响应格式
    
    @classmethod
    def create(cls, items: Sequence[T], total: int, params: PaginationParams) -> "PageResponse[T]":
        """创建分页响应"""
        size = params.size
        page = params.page
        pages = (total + size - 1) // size if size > 0 else 0
        
        return cls(
            items=items,
            page=page,
            size=size,
            total=total,
            pages=pages
        )

def paginate_query_results(results: Sequence[T], total: int, params: PaginationParams) -> PageResponse[T]:
    """
    将查询结果分页
    
    Args:
        results: 当前页的结果数据
        total: 总记录数
        params: 分页参数
        
    Returns:
        标准分页响应
    """
    return PageResponse.create(items=results, total=total, params=params)

def get_pagination_params(
    pagination: PaginationParams = Depends(PaginationParams.as_query_params)
) -> PaginationParams:
    """
    分页参数依赖
    
    使用示例:
    ```python
    @router.get("/items")
    async def list_items(pagination: PaginationParams = Depends(get_pagination_params)):
        # 使用 pagination.page 和 pagination.size
        # ...
    ```
    """
    return pagination
