from typing import Optional, List, Dict, Any
from langchain.chains import RetrievalQA
# 检查 Langchain 0.3 文档以获取正确的提示模板类
# from langchain.prompts import PromptTemplate # 可能位于 langchain.prompts.prompt
from langchain import PromptTemplate
from langchain.vectorstores.base import VectorStoreRetriever # 检查导入路径
from langchain.docstore.document import Document
from fastapi import HTTPException, status

from app.services.llm import get_llm
from app.models.schemas import QueryResponse, DocumentSource

# 定义一个默认的提示模板
# 您可能需要根据 LLM 的要求调整此模板
DEFAULT_PROMPT_TEMPLATE = """
使用以下上下文信息来回答最后的问题。
如果你不知道答案, 就直接说不知道, 不要试图编造答案。
最多使用三个句子, 并保持答案简洁。

上下文:
{context}

问题: {question}

有用的回答:"""

# 创建提示模板实例
QA_PROMPT = PromptTemplate(
    template=DEFAULT_PROMPT_TEMPLATE, input_variables=["context", "question"]
)


def _create_rag_chain(llm_provider: Optional[str], retriever: VectorStoreRetriever) -> RetrievalQA:
    """使用指定的 LLM 和检索器创建 RetrievalQA 链。"""
    try:
        llm, provider_name, model_name = get_llm(llm_provider)

        # 检查 Langchain 0.3 文档中 RetrievalQA 的参数
        # 对于提示可能需要 `combine_documents_chain_kwargs` 或类似参数
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff", # 常用的链类型, 其他选项: map_reduce, refine, map_rerank
            retriever=retriever,
            return_source_documents=True, # 重要: 返回源文档
            chain_type_kwargs={"prompt": QA_PROMPT} # 传递提示模板
        )
        print(f"已创建 RetrievalQA 链, LLM: {provider_name} ({model_name})")
        return qa_chain
    except Exception as e:
        print(f"创建 RAG 链时出错: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"创建 RAG 链失败: {e}")

def format_sources(source_documents: List[Document]) -> List[DocumentSource]:
    """将 Langchain 文档格式化为 API 响应模式。"""
    sources = []
    for doc in source_documents:
        # 提取相关元数据
        filename = doc.metadata.get('source', 'Unknown') # 获取源文件名
        page_number = doc.metadata.get('page') # PyPDFLoader 可能会添加页码
        score = doc.metadata.get('score', 0.0) # 我们在 search_similar_documents 中添加了得分

        # 创建内容预览 (例如, 前 150 个字符)
        content_preview = doc.page_content[:150] + "..." if len(doc.page_content) > 150 else doc.page_content

        sources.append(DocumentSource(
            filename=filename,
            page_number=page_number,
            score=score,
            content_preview=content_preview
        ))
    # 按得分排序 (降序)
    sources.sort(key=lambda x: x.score, reverse=True)
    return sources

async def perform_rag_query(
    query: str,
    llm_provider: Optional[str],
    retriever: VectorStoreRetriever
) -> QueryResponse:
    """使用指定的提供商和检索器执行 RAG 查询。"""
    try:
        rag_chain = _create_rag_chain(llm_provider, retriever)

        # Langchain 0.3 的链可能是同步的, 或者有像 `acall` 或 `arun` 这样的异步方法
        # 检查具体版本的文档。这里使用同步的 `__call__`。
        # result = await rag_chain.acall({"query": query}) # 如果异步可用
        result = rag_chain({"query": query}) # 同步调用

        answer = result.get('result', '未能生成答案。')
        source_documents = result.get('source_documents', [])

        formatted_sources = format_sources(source_documents)

        # 获取实际使用的提供商/模型
        # 从缓存中检索或重新初始化
        _, actual_provider, actual_model = get_llm(llm_provider)

        return QueryResponse(
            answer=answer,
            sources=formatted_sources,
            llm_provider_used=actual_provider,
            model_name_used=actual_model
        )

    except HTTPException as http_exc: # 重新引发 HTTP 异常
        raise http_exc
    except Exception as e:
        print(f"执行 RAG 查询时出错: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"处理 RAG 查询时出错: {e}") 