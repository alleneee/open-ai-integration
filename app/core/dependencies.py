from functools import lru_cache
from fastapi import Depends, HTTPException, status
from langchain.vectorstores import Milvus
from langchain.vectorstores.base import VectorStoreRetriever

from app.services.vector_store import get_vector_store
from app.config import settings

# 缓存 vector store 实例以避免每次请求都重新连接
@lru_cache()
def get_cached_vector_store() -> Milvus:
    """提供缓存的 Milvus 向量存储实例的依赖项。"""
    try:
        return get_vector_store()
    except Exception as e:
        # 在实际应用中应妥善记录错误
        print(f"严重: 获取向量存储依赖失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="向量数据库当前不可用。请稍后再试。"
        )

def get_retriever(vector_store: Milvus = Depends(get_cached_vector_store)) -> VectorStoreRetriever:
    """提供来自向量存储的检索器实例的依赖项。"""
    try:
        # Langchain 0.3 可能有不同的创建检索器的参数
        retriever = vector_store.as_retriever(
            search_type="similarity", # 或 "mmr" 等
            # search_kwargs={'k': settings.retriever_top_k} # 改为使用查询请求中的 k
        )
        return retriever
    except Exception as e:
        print(f"从向量存储创建检索器时出错: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建文档检索器失败。"
        ) 