from operator import itemgetter
from typing import List, Optional, Tuple, Dict, Any

from langchain_core.runnables import RunnablePassthrough, RunnableParallel, RunnableLambda
from langchain_core.messages import get_buffer_string, BaseMessage, AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, format_document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever # Import BaseRetriever

# --- New Imports --- 
from rank_bm25 import BM25Okapi # Import BM25
# Consider adding jieba for Chinese tokenization if needed
# import jieba

from app.services.llm import get_llm # Reuse LLM initialization
from app.services.vector_store import get_retriever # Reuse retriever logic
from app.services.conversation import conversation_service # Import conversation service
from app.schemas.schemas import RAGQueryRequest, RAGResult, Message # Import request/response models
from app.core.config import settings # Import settings from new core path

import logging

logger = logging.getLogger(__name__)

# --- Constants ---
DEFAULT_DOCUMENT_PROMPT = ChatPromptTemplate.from_template(template="{page_content}")

# --- Helper Functions (Existing and New) ---

def _combine_documents(
    docs: List[Document], document_prompt=DEFAULT_DOCUMENT_PROMPT, document_separator="\n\n"
) -> str:
    """将检索到的文档格式化为字符串，用于输入到LLM。"""
    doc_strings = [format_document(doc, document_prompt) for doc in docs]
    return document_separator.join(doc_strings)

def _format_chat_history(chat_history: List[Message]) -> str:
    """将 Pydantic 模型的聊天历史格式化为适合提示的字符串。 (Alternative formatting)"""
    buffer: List[BaseMessage] = []
    for msg in chat_history:
        if msg.role == "user":
            buffer.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            buffer.append(AIMessage(content=msg.content))
        else:
            logger.warning(f"未知的聊天历史角色: {msg.role}")
            buffer.append(HumanMessage(content=f"[{msg.role}] {msg.content}")) # Example handling

    return get_buffer_string(buffer)

def _convert_to_base_messages(messages: List[Message]) -> List[BaseMessage]:
     """将 Pydantic Message 列表转换为 Langchain BaseMessage 列表。"""
     base_messages: List[BaseMessage] = []
     for msg in messages:
          if msg.role == "user":
               base_messages.append(HumanMessage(content=msg.content))
          elif msg.role == "assistant":
               base_messages.append(AIMessage(content=msg.content))
     return base_messages

# --- 新增：混合搜索相关函数 ---
def _tokenize(text: str) -> List[str]:
    """简单的分词器，需要为中文等语言改进。"""
    # TODO: Replace with a better tokenizer, e.g., jieba.lcut(text) for Chinese
    return text.lower().split()

def _get_bm25_retriever(query: str, docs: List[Document], k: int = 5) -> List[Document]:
    """
    使用 BM25 对文档列表进行排序并返回 top-k。

    Args:
        query: 用户查询字符串。
        docs: 要进行 BM25 排序的 Langchain Document 列表。
        k: 返回的文档数量。

    Returns:
        按 BM25 分数排序后的 top-k 文档列表。
    """
    if not docs:
        return []
    if not query:
        logger.warning("BM25 检索收到空查询，返回空结果。")
        return []

    # 1. 准备 BM25 的语料库 (分词)
    try:
         # Use the new tokenizer
         tokenized_corpus = [_tokenize(doc.page_content) for doc in docs]
         # Filter out potentially empty documents after tokenization if necessary
         valid_indices = [i for i, tokens in enumerate(tokenized_corpus) if tokens]
         if not valid_indices:
              logger.warning("BM25: 所有文档在分词后均为空。")
              return []
         # Map corpus and docs to only valid ones
         filtered_corpus = [tokenized_corpus[i] for i in valid_indices]
         filtered_docs = [docs[i] for i in valid_indices]

    except Exception as e:
         logger.error(f"BM25 分词失败: {e}")
         return docs[:k] # Fallback

    # 2. 初始化 BM25 模型
    try:
        bm25 = BM25Okapi(filtered_corpus)
    except ValueError as e:
        logger.error(f"初始化 BM25 失败 (可能是空语料库?): {e}")
        return filtered_docs[:k] # Return filtered docs if BM25 fails
    except Exception as e:
         logger.error(f"初始化 BM25 时发生未知错误: {e}")
         return filtered_docs[:k]

    # 3. 对查询进行分词
    tokenized_query = _tokenize(query)
    if not tokenized_query:
         logger.warning("BM25: 查询分词后为空，返回原始排序文档。")
         return filtered_docs[:k]

    # 4. 获取 BM25 分数
    try:
         doc_scores = bm25.get_scores(tokenized_query)
    except Exception as e:
         logger.error(f"计算 BM25 分数时出错: {e}")
         return filtered_docs[:k] # Fallback

    # 5. 结合分数和文档，并排序
    docs_with_scores = list(zip(filtered_docs, doc_scores))
    sorted_docs_with_scores = sorted(docs_with_scores, key=lambda item: item[1], reverse=True)

    # 6. 返回 top-k 文档
    sorted_docs = [doc for doc, score in sorted_docs_with_scores]
    logger.debug(f"BM25 排序完成，返回 top {min(k, len(sorted_docs))} 个文档。")
    return sorted_docs[:k]

def _reciprocal_rank_fusion(
    results: List[List[Document]], k: int = 60
) -> List[Document]:
    """
    使用 Reciprocal Rank Fusion (RRF) 融合多个检索结果列表。

    Args:
        results: 一个包含多个文档列表的列表 (例如, [[vec_doc1, vec_doc2], [bm25_doc2, bm25_doc1]])。
        k: RRF 公式中的常数，通常设为 60。

    Returns:
        融合并重新排序后的文档列表。
    """
    if not results or not any(results):
        return []

    # Use a unique identifier for each document for robust ranking
    # Option 1: Use a unique ID from metadata if available (e.g., doc_id)
    # Option 2: Use page_content (prone to issues if content isn't unique)
    # We need a way to map the scored ID/content back to the Document object.
    doc_map: Dict[str, Document] = {}
    ranked_lists: List[Dict[str, int]] = []

    for result_list in results:
        ranks = {}
        for i, doc in enumerate(result_list):
            # Define the unique key for the document
            doc_key = doc.metadata.get("doc_id") or doc.page_content # Prioritize ID
            if not doc_key: # Skip docs without a usable key
                logger.warning("RRF: 文档缺少 doc_id 或 page_content，跳过。")
                continue

            if doc_key not in ranks: # Keep the first encountered rank for this key
                ranks[doc_key] = i + 1
            if doc_key not in doc_map:
                doc_map[doc_key] = doc # Store the first encountered doc object
        ranked_lists.append(ranks)

    # Calculate RRF scores
    rrf_scores: Dict[str, float] = {}
    all_doc_keys = set(doc_map.keys())

    for ranks in ranked_lists:
        for doc_key, rank in ranks.items():
            if doc_key in all_doc_keys: # Ensure key is valid
                if doc_key not in rrf_scores:
                    rrf_scores[doc_key] = 0.0
                rrf_scores[doc_key] += 1.0 / (k + rank)

    # Sort document keys based on RRF score
    sorted_doc_keys = sorted(rrf_scores.keys(), key=lambda item: rrf_scores[item], reverse=True)

    # Get the final list of Document objects in fused order
    fused_docs = [doc_map[key] for key in sorted_doc_keys]

    logger.debug(f"RRF 融合完成，生成 {len(fused_docs)} 个唯一文档。")
    return fused_docs

class HybridRetriever(BaseRetriever):
    """
    简单的混合检索器 (Vector + BM25 on initial results + RRF)。
    """
    vector_retriever: BaseRetriever
    # bm25_k is implicitly the number of vector results here
    final_k: int = 5 # Final number of documents to return after fusion
    rrf_k: int = 60  # RRF constant

    def _get_relevant_documents(
        self, query: str, *, run_manager=None # run_manager might be needed for callbacks
    ) -> List[Document]:
        """
        执行混合检索的核心逻辑。
        """
        logger.info(f"HybridRetriever: 开始处理查询: '{query[:50]}...'")

        # 1. Vector Search
        try:
             vector_results = self.vector_retriever.get_relevant_documents(query)
             logger.debug(f"HybridRetriever: 向量搜索返回 {len(vector_results)} 个文档。")
        except Exception as e:
            logger.error(f"HybridRetriever: 向量搜索失败: {e}")
            return []

        if not vector_results:
             return []

        # 2. BM25 Ranking on Vector Results
        bm25_ranked_docs = _get_bm25_retriever(query, vector_results, k=len(vector_results))
        logger.debug(f"HybridRetriever: BM25 对向量结果重排序完成，得到 {len(bm25_ranked_docs)} 个文档。")

        # 3. Reciprocal Rank Fusion (RRF)
        # If BM25 failed, fuse only with vector results (effectively no fusion)
        results_to_fuse = [vector_results]
        if bm25_ranked_docs:
            results_to_fuse.append(bm25_ranked_docs)

        fused_results = _reciprocal_rank_fusion(
            results=results_to_fuse,
            k=self.rrf_k
        )
        logger.info(f"HybridRetriever: RRF 融合后得到 {len(fused_results)} 个文档。")

        # 4. Return final top-k results
        final_results = fused_results[:self.final_k]
        logger.info(f"HybridRetriever: 返回最终 top {len(final_results)} 个文档。")
        return final_results

    async def _aget_relevant_documents(
        self, query: str, *, run_manager=None
    ) -> List[Document]:
        """
        混合检索的异步实现。
        """
        logger.info(f"HybridRetriever (async): 开始处理查询: '{query[:50]}...'")

        # 1. Async Vector Search
        try:
            vector_results = await self.vector_retriever.aget_relevant_documents(query)
            logger.debug(f"HybridRetriever (async): 向量搜索返回 {len(vector_results)} 个文档。")
        except Exception as e:
             logger.error(f"HybridRetriever (async): 异步向量搜索失败: {e}")
             return []

        if not vector_results:
             return []

        # 2. BM25 Ranking (Run synchronously for now)
        # TODO: Run _get_bm25_retriever in executor for true async
        bm25_ranked_docs = _get_bm25_retriever(query, vector_results, k=len(vector_results))
        logger.debug(f"HybridRetriever (async): BM25 对向量结果重排序完成，得到 {len(bm25_ranked_docs)} 个文档。")

        # 3. RRF (Synchronous)
        # TODO: Run _reciprocal_rank_fusion in executor if needed
        results_to_fuse = [vector_results]
        if bm25_ranked_docs:
            results_to_fuse.append(bm25_ranked_docs)

        fused_results = _reciprocal_rank_fusion(
            results=results_to_fuse,
            k=self.rrf_k
        )
        logger.info(f"HybridRetriever (async): RRF 融合后得到 {len(fused_results)} 个文档。")

        # 4. Return final top-k results
        final_results = fused_results[:self.final_k]
        logger.info(f"HybridRetriever (async): 返回最终 top {len(final_results)} 个文档。")
        return final_results

# --- RAG Chain Definition (Updated) ---

def create_rag_chain(
    collection_name: Optional[str] = None,
    retrieval_strategy: str = "vector",
    top_k: int = 5, # For base vector search
    rerank_top_n: Optional[int] = 3, # For 'rerank' strategy
    hybrid_final_k: int = 5, # For 'hybrid' strategy
):
    """
    使用 LCEL 创建 RAG 链，支持混合检索。
    """
    logger.info(
        f"创建 RAG 链: collection='{collection_name}', strategy='{retrieval_strategy}', "
        f"top_k={top_k}, rerank_top_n={rerank_top_n}, hybrid_final_k={hybrid_final_k}"
    )

    # 1. Configure the retriever based on strategy
    try:
        if retrieval_strategy == "hybrid":
            if top_k <= 0:
                 logger.warning(f"Hybrid search requires positive top_k for initial vector search. Using default 10.")
                 top_k = 10 # Ensure base retriever gets enough candidates
            if hybrid_final_k <= 0:
                 logger.warning(f"hybrid_final_k must be positive. Using default 5.")
                 hybrid_final_k = 5

            base_vector_retriever = get_retriever(
                collection_name=collection_name,
                strategy="vector",
                top_k=top_k, # Retrieve more candidates initially
            )
            logger.debug(f"混合检索：基础向量检索器 (k={top_k}) 获取成功。")
            retriever = HybridRetriever(
                vector_retriever=base_vector_retriever,
                final_k=hybrid_final_k
            )
            logger.info(f"使用 Hybrid 检索策略 (base_k={top_k}, final_k={hybrid_final_k})。")

        elif retrieval_strategy == "rerank":
            retriever = get_retriever(
                collection_name=collection_name,
                strategy="rerank",
                top_k=top_k,
                rerank_top_n=rerank_top_n,
            )
            logger.info(f"使用 Rerank 检索策略 (base_k={top_k}, rerank_n={rerank_top_n or 3})。")
        else: # Default to vector
            if top_k <= 0:
                 logger.warning(f"Vector search top_k must be positive. Using default 5.")
                 top_k = 5
            retriever = get_retriever(
                collection_name=collection_name,
                strategy="vector",
                top_k=top_k,
            )
            logger.info(f"使用 Vector 检索策略 (k={top_k})。")

        logger.debug("检索器实例配置完成。")

    except Exception as e:
        logger.exception(f"创建 RAG 链时无法配置检索器: {e}")
        raise RuntimeError(f"无法初始化检索器: {e}") from e

    # --- Subsequent steps (prompts, LLM, chain assembly) remain the same ---

    # 2. Define Prompt (same as before)
    template = """基于以下上下文信息回答问题。如果上下文没有提供足够信息，请明确说明你不知道，不要编造答案。

上下文:```
{context}
```
问题: {question}
回答:"""
    ANSWER_PROMPT = ChatPromptTemplate.from_messages(
        [
            ("system", template),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}"),
        ]
    )

    # 3. Get LLM (same as before)
    llm = get_llm()
    logger.debug("LLM 实例获取成功。")

    # 4. Runnable for history (same as before)
    format_memory_messages = RunnableLambda(_convert_to_base_messages)

    # 5. Build LCEL Chain (same structure, uses the configured retriever)
    rag_chain_with_source = RunnableParallel(
        {
            "context_docs": itemgetter("question") | retriever,
            "question": itemgetter("question"),
            "conversation_history": itemgetter("conversation_history")
        }
    ).assign(
        answer= RunnablePassthrough.assign(
            chat_history=itemgetter("conversation_history") | format_memory_messages,
            context=lambda x: _combine_documents(x["context_docs"])
        )
        | ANSWER_PROMPT
        | llm
        | StrOutputParser(),
        source_documents=itemgetter("context_docs")
    )
    final_chain = rag_chain_with_source | RunnableLambda(lambda x: {"answer": x["answer"], "source_documents": x["source_documents"]})

    logger.info("RAG 链构建完成。")
    return final_chain

# --- Main Service Function (Updated) ---
async def perform_rag_query(request: RAGQueryRequest) -> RAGResult:
    """
    执行 RAG 查询，并管理会话历史。
    """
    logger.info(f"收到 RAG 查询请求: collection='{request.collection_name}', strategy='{request.retrieval_strategy}', query='{request.query[:50]}...", extra={'request_details': request.dict(exclude={'conversation_history'})})
    
    # 使用 session_id (需要添加到请求模型中)
    session_id = request.session_id # 假设 session_id 在 RAGQueryRequest 中
    if not session_id:
        logger.error("请求中缺少 session_id")
        return RAGResult(
            answer="请求错误: 缺少 session_id",
            source_documents=[]
        )

    # 从 Redis 获取历史记录
    chat_history = conversation_service.get_history(session_id)
    logger.debug(f"会话 {session_id}: 检索到 {len(chat_history)} 条历史消息。")

    try:
        # Add hybrid_final_k to request schema or pass top_k as default
        hybrid_final_k = getattr(request, 'hybrid_final_k', request.top_k)

        rag_chain = create_rag_chain(
            collection_name=request.collection_name,
            retrieval_strategy=request.retrieval_strategy,
            top_k=request.top_k,
            rerank_top_n=request.rerank_top_n,
            hybrid_final_k=hybrid_final_k # Pass the final K for hybrid
        )
    except Exception as e:
         logger.error(f"创建 RAG 链失败: {e}")
         return RAGResult(
             answer=f"处理请求时发生内部错误: 无法创建 RAG 链 ({e})",
             source_documents=[]
         )

    # Prepare input using history from Redis
    chain_input = {
        "question": request.query,
        "conversation_history": chat_history # 使用从 Redis 获取的历史
    }

    # Execute chain
    try:
        logger.info("正在异步执行 RAG 链...", extra={"chain_input": {"question": chain_input["question"], "history_len": len(chain_input["conversation_history"])}})
        result_dict = await rag_chain.ainvoke(chain_input)
        logger.info("RAG 链执行成功。")

        # Process result
        source_docs_list = []
        if result_dict.get("source_documents"):
            for doc in result_dict["source_documents"]:
                if isinstance(doc, Document):
                    # Add a fallback for metadata if it's None
                    metadata = doc.metadata or {}
                    source_docs_list.append(
                        {"page_content": doc.page_content, "metadata": metadata}
                    )
                else:
                     logger.warning(f"检索到的源文档格式不符合预期: {type(doc)}")

        final_answer = result_dict.get("answer", "(无法生成答案)")
        logger.info(f"RAG 查询完成，生成答案: {final_answer[:100]}...", extra={"answer": final_answer, "num_sources": len(source_docs_list)})

        # 更新 Redis 中的历史记录
        conversation_service.add_message(session_id, Message(role="user", content=request.query))
        conversation_service.add_message(session_id, Message(role="assistant", content=final_answer))
        logger.debug(f"会话 {session_id}: 已更新历史记录。")

        return RAGResult(
            answer=final_answer,
            source_documents=source_docs_list
        )

    except Exception as e:
        logger.exception(f"执行 RAG 链时出错: {e}")
        return RAGResult(
            answer=f"处理查询时发生错误: {e}",
            source_documents=[]
        ) 