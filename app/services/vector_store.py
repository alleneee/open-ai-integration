from typing import List, Optional, Dict, Any, Literal
from pymilvus import connections, utility, Collection
from langchain.vectorstores import Milvus
from langchain.embeddings.base import Embeddings
from langchain.docstore.document import Document
from fastapi import HTTPException, status
from langchain.retrievers import ContextualCompressionRetriever
try:
    from langchain_cohere import CohereRerank
except ImportError:
    from langchain.retrievers.document_compressors import CohereRerank
from app.core.config import settings
from app.schemas.schemas import KnowledgeBaseResponse
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
try:
    from langchain_community.embeddings import HuggingFaceEmbeddings, OllamaEmbeddings, JinaEmbeddings
except ImportError:
    logger.warning("Could not import embeddings from langchain_community, ensure it's installed and updated.")
    HuggingFaceEmbeddings = OllamaEmbeddings = JinaEmbeddings = None
import requests
import logging
import os

# --- Setup Logger ---
logging.basicConfig(level=settings.log_level.upper(), format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Global Milvus connection (or manage within functions/dependencies) ---
def get_milvus_connection():
    """获取或建立Milvus连接"""
    connection_alias = "default"
    if not connections.has_connection(connection_alias):
        try:
            logger.info(f"尝试连接 Milvus: URI={settings.milvus_uri}, Secure={'*'*(len(settings.milvus_token) -2) if settings.milvus_token else 'False'}")
            connections.connect(
                alias=connection_alias,
                uri=settings.milvus_uri,
                token=settings.milvus_token,
            )
            logger.info(f"成功连接到 Milvus (alias: '{connection_alias}').")
        except Exception as e:
            logger.error(f"连接 Milvus (alias: '{connection_alias}') 失败: {e}")
            raise ConnectionError(f"无法连接到 Milvus: {e}") from e

# Call connect on module load? Or handle in dependency? For now, call before use.

# --- Custom Embedding Classes (Keep from previous steps) ---
class QwenEmbeddings(Embeddings):
    """Custom Embeddings class for Qwen via Dashscope API."""
    def __init__(self, model_name: str = "text-embedding-v1"):
        try:
            import dashscope
        except ImportError:
            raise ImportError("Dashscope package not found, please run `poetry add dashscope`")
        self.model_name = model_name
        self._check_api_key()
        self._dashscope = dashscope

    def _check_api_key(self):
        if not settings.dashscope_api_key:
            raise ValueError("Dashscope API key not found in settings. Please set DASHSCOPE_API_KEY.")
        self._dashscope.api_key = settings.dashscope_api_key

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple documents."""
        embeddings = []
        for text in texts:
            try:
                resp = self._dashscope.TextEmbedding.call(model=self.model_name, input=text)
                if resp.status_code == 200 and resp.output and resp.output.get('embeddings'):
                    embedding_data = resp.output['embeddings'][0].get('embedding')
                    if embedding_data:
                        embeddings.append(embedding_data)
                    else:
                        logger.error(f"Dashscope embedding succeeded but no embedding data found for a text. Response: {resp}")
                        embeddings.append([0.0] * self._get_dimension())
                else:
                    logger.error(f"Dashscope embedding failed for a text. Status: {resp.status_code}, Message: {getattr(resp, 'message', 'N/A')}, RequestId: {resp.request_id}")
                    embeddings.append([0.0] * self._get_dimension())
            except Exception as e:
                logger.error(f"Error calling Dashscope API during embed_documents: {e}")
                embeddings.append([0.0] * self._get_dimension())
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query."""
        try:
            resp = self._dashscope.TextEmbedding.call(model=self.model_name, input=text)
            if resp.status_code == 200 and resp.output and resp.output.get('embeddings'):
                embedding_data = resp.output['embeddings'][0].get('embedding')
                if embedding_data:
                    return embedding_data
                else:
                    logger.error(f"Dashscope query embedding succeeded but no embedding data found. Response: {resp}")
                    return [0.0] * self._get_dimension()
            else:
                logger.error(f"Dashscope query embedding failed. Status: {resp.status_code}, Message: {getattr(resp, 'message', 'N/A')}, RequestId: {resp.request_id}")
                return [0.0] * self._get_dimension()
        except Exception as e:
            logger.error(f"Error calling Dashscope API for query: {e}")
            return [0.0] * self._get_dimension()

    def _get_dimension(self) -> int:
        dimensions = {
            "text-embedding-v1": 1536,
            "text-embedding-v2": 1536,
        }
        dim = dimensions.get(self.model_name)
        if dim:
            return dim
        else:
            logger.warning(f"Unknown dimension for Qwen model {self.model_name}, returning default 1024. Please verify.")
            return 1024

# --- get_embedding_model (Refined) ---
def get_embedding_model() -> Embeddings:
    """根据配置初始化并返回嵌入模型。"""
    provider = settings.embedding_provider
    logger.info(f"正在初始化嵌入模型提供商: {provider}")

    try:
        if provider == "openai":
            if not settings.openai_api_key:
                raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY.")
            return OpenAIEmbeddings(
                openai_api_key=settings.openai_api_key,
                model=settings.openai_embedding_model_name
            )

        elif provider == "huggingface":
            if HuggingFaceEmbeddings is None: raise ImportError("HuggingFaceEmbeddings not available.")
            logger.info(f"加载 HuggingFace 模型: {settings.huggingface_model_name}")
            device = settings.embedding_device if settings.embedding_device else 'cpu'
            logger.info(f"使用设备: {device} for HuggingFace model.")
            return HuggingFaceEmbeddings(
                model_name=settings.huggingface_model_name,
                model_kwargs={'device': device},
                encode_kwargs={'normalize_embeddings': True}
            )

        elif provider == "qwen":
            return QwenEmbeddings(model_name=settings.qwen_embedding_model_name)

        elif provider == "ollama":
            if OllamaEmbeddings is None: raise ImportError("OllamaEmbeddings not available.")
            logger.info(f"使用 Ollama 嵌入模型: {settings.ollama_embedding_model} at {settings.ollama_base_url}")
            return OllamaEmbeddings(
                model=settings.ollama_embedding_model,
                base_url=settings.ollama_base_url
            )

        elif provider == "jina":
            if JinaEmbeddings is None: raise ImportError("JinaEmbeddings not available.")
            if not settings.jina_api_key:
                raise ValueError("Jina API key not found. Please set JINA_API_KEY.")
            logger.info(f"使用 Jina 嵌入模型: {settings.jina_embedding_model}")
            return JinaEmbeddings(
                jina_api_key=settings.jina_api_key,
                model_name=settings.jina_embedding_model
            )

        elif provider == "custom":
            if HuggingFaceEmbeddings is None: raise ImportError("HuggingFaceEmbeddings not available for custom model loading.")
            if not settings.custom_embedding_model_path:
                raise ValueError("Custom model path not set. Please set CUSTOM_EMBEDDING_MODEL_PATH.")
            logger.info(f"加载自定义本地模型: {settings.custom_embedding_model_path}")
            device = settings.embedding_device if settings.embedding_device else 'cpu'
            logger.info(f"使用设备: {device} for custom model.")
            return HuggingFaceEmbeddings(
                model_name=settings.custom_embedding_model_path,
                model_kwargs={**(settings.custom_embedding_model_kwargs or {}), 'device': device},
                encode_kwargs={'normalize_embeddings': True}
            )

        else:
            raise ValueError(f"不支持的嵌入模型提供商: {provider}")

    except ImportError as e:
        logger.error(f"初始化嵌入模型 '{provider}' 失败：缺少依赖 - {e}")
        raise RuntimeError(f"缺少 '{provider}' 的依赖: {e}. 请确保已安装必要的包 (e.g., poetry add langchain-openai langchain-community sentence-transformers dashscope langchain-cohere).") from e
    except ValueError as e:
        logger.error(f"初始化嵌入模型 '{provider}' 失败：配置错误 - {e}")
        raise RuntimeError(f"配置错误 '{provider}': {e}") from e
    except Exception as e:
        logger.exception(f"初始化嵌入模型 '{provider}' 时发生未知错误: {e}")
        raise RuntimeError(f"初始化嵌入模型失败: {e}") from e

# --- 知识库管理函数 ---

def create_knowledge_base(collection_name: str, description: Optional[str] = None, embedding_function: Optional[Embeddings] = None) -> bool:
    """
    在 Milvus 中创建一个新的 Collection (知识库)。
    Args:
        collection_name: 要创建的 Collection 名称。
        description: Collection 的描述 (可选)。
        embedding_function: (可选) 用于确定维度的嵌入函数实例。如果未提供，将尝试初始化。

    Returns:
        如果创建成功或已存在，返回 True。否则返回 False。

    Raises:
        ConnectionError: 如果无法连接到 Milvus。
        RuntimeError: 如果无法确定嵌入维度或创建失败。
    """
    get_milvus_connection()
    try:
        if utility.has_collection(collection_name):
            logger.warning(f"Collection '{collection_name}' 已存在。跳过创建。")
            return True

        logger.info(f"Collection '{collection_name}' 不存在，开始创建...")

        if embedding_function is None:
            embedding_function = get_embedding_model()

        dim = -1
        try:
            if hasattr(embedding_function, 'client') and hasattr(embedding_function.client, 'dimensions'):
                dim = embedding_function.client.dimensions
            elif hasattr(embedding_function, 'client') and hasattr(embedding_function.client, 'embedding_size'):
                dim = embedding_function.client.embedding_size
            elif isinstance(embedding_function, HuggingFaceEmbeddings):
                logger.info("尝试通过嵌入获取 HuggingFace 模型维度...")
                dummy_embedding = embedding_function.embed_query("dimension test")
                dim = len(dummy_embedding)
            elif isinstance(embedding_function, QwenEmbeddings):
                dim = embedding_function._get_dimension()
            elif isinstance(embedding_function, OllamaEmbeddings):
                logger.warning("自动检测 Ollama 模型维度可能不可靠，使用默认值 1024。建议在配置中指定。")
                dim = 1024
            elif isinstance(embedding_function, JinaEmbeddings):
                logger.info("尝试通过嵌入获取 Jina 模型维度...")
                dummy_embedding = embedding_function.embed_query("dimension test")
                dim = len(dummy_embedding)
            else:
                logger.info("尝试通过嵌入通用后备方法获取维度...")
                dummy_embedding = embedding_function.embed_query("dimension test")
                dim = len(dummy_embedding)

            if dim <= 0:
                raise ValueError("无法确定有效的嵌入维度 (> 0)。")
            logger.info(f"推断嵌入维度为: {dim} for collection '{collection_name}'.")

        except Exception as e:
            logger.error(f"无法自动获取嵌入维度 for '{collection_name}': {e}")
            raise RuntimeError(f"无法获取嵌入维度: {e}") from e

        from pymilvus import FieldSchema, CollectionSchema, DataType
        fields = [
            FieldSchema(name="pk", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=settings.milvus_text_max_length),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dim),
        ]
        schema = CollectionSchema(
            fields=fields,
            description=description or f"RAG Knowledge Base: {collection_name}",
            enable_dynamic_field=True
        )
        logger.info(f"使用 Schema 为 Collection '{collection_name}' 创建...")
        collection = Collection(name=collection_name, schema=schema, using='default')
        logger.info(f"Collection '{collection_name}' 定义成功。")

        index_params = settings.milvus_index_params or {
            "metric_type": "L2",
            "index_type": "AUTOINDEX",
            "params": {}
        }
        logger.info(f"为 Collection '{collection_name}' 的 'vector' 字段创建索引，参数: {index_params}")
        collection.create_index(field_name="vector", index_params=index_params)
        logger.info(f"索引创建请求已发送 for '{collection_name}'. (可能是异步的)")

        logger.info(f"正在加载 Collection '{collection_name}' 到内存...")
        collection.load()
        logger.info(f"Collection '{collection_name}' 已加载。")
        return True

    except ConnectionError as ce:
        logger.error(f"创建 Collection '{collection_name}' 时连接 Milvus 失败: {ce}")
        raise ce
    except Exception as e:
        logger.exception(f"创建 Collection '{collection_name}' 失败: {e}")
        return False

def list_knowledge_bases() -> List[KnowledgeBaseResponse]:
    """列出 Milvus 中所有的 Collections (知识库)"""
    get_milvus_connection()
    try:
        collection_names = utility.list_collections()
        response_list = []
        logger.info(f"发现 Milvus Collections: {collection_names}")
        for name in collection_names:
            info = get_knowledge_base_info(name)
            if info:
                response_list.append(info)
            else:
                response_list.append(KnowledgeBaseResponse(collection_name=name, description="<error fetching details>", num_entities=None))
        return response_list
    except Exception as e:
        logger.error(f"列出 Collections 失败: {e}")
        return []

def get_knowledge_base_info(collection_name: str) -> Optional[KnowledgeBaseResponse]:
    """获取指定 Collection 的信息"""
    get_milvus_connection()
    try:
        if not utility.has_collection(collection_name):
            logger.warning(f"请求信息的 Collection '{collection_name}' 不存在。")
            return None

        logger.debug(f"获取 Collection '{collection_name}' 的信息...")
        collection = Collection(collection_name, using='default')
        logger.debug(f"确保 Collection '{collection_name}' 已加载以获取实体数...")
        collection.load()
        logger.debug(f"Collection '{collection_name}' 状态: loaded={collection.is_empty}, entities={collection.num_entities}")

        return KnowledgeBaseResponse(
            collection_name=collection.name,
            description=collection.description,
            num_entities=collection.num_entities
        )
    except Exception as e:
        if "CollectionNotExistException" in str(e) or "collection not found" in str(e).lower():
            logger.warning(f"获取信息时发现 Collection '{collection_name}' 不存在。")
            return None
        logger.error(f"获取 Collection '{collection_name}' 信息失败: {e}")
        return None

def delete_knowledge_base(collection_name: str) -> bool:
    """删除 Milvus 中的一个 Collection"""
    get_milvus_connection()
    try:
        if not utility.has_collection(collection_name):
            logger.warning(f"尝试删除不存在的 Collection: '{collection_name}'")
            return False

        logger.info(f"正在删除 Collection: '{collection_name}'...")
        utility.drop_collection(collection_name, using='default')
        logger.info(f"成功删除 Collection: '{collection_name}'")
        global vector_store_instances
        if collection_name in vector_store_instances:
            del vector_store_instances[collection_name]
            logger.debug(f"已从缓存中移除 '{collection_name}' 的向量存储实例。")
        return True
    except Exception as e:
        logger.error(f"删除 Collection '{collection_name}' 失败: {e}")
        return False

# --- 更新向量存储和检索器逻辑 ---

vector_store_instances: Dict[str, Milvus] = {}
embedding_function_instance: Optional[Embeddings] = None

def _get_embedding_instance() -> Embeddings:
    """获取或初始化嵌入函数单例"""
    global embedding_function_instance
    if embedding_function_instance is None:
        logger.info("首次调用，初始化嵌入函数实例...")
        embedding_function_instance = get_embedding_model()
    return embedding_function_instance

def get_vector_store_instance(collection_name: Optional[str] = None) -> Milvus:
    """
    获取或初始化指定 Collection 的 Milvus 向量存储实例。
    如果 Collection 不存在，将尝试自动创建。
    """
    global vector_store_instances
    target_collection = collection_name or settings.milvus_collection_name

    if target_collection in vector_store_instances:
        try:
            utility.has_collection(target_collection)
            return vector_store_instances[target_collection]
        except Exception as e:
            logger.warning(f"缓存实例的连接可能已失效 for '{target_collection}': {e}. 尝试重新初始化。")
            del vector_store_instances[target_collection]

    logger.info(f"缓存未命中或失效，正在初始化向量存储实例 for '{target_collection}'...")
    embedding_func = _get_embedding_instance()
    get_milvus_connection()

    if not utility.has_collection(target_collection):
        logger.warning(f"目标 Collection '{target_collection}' 不存在。将尝试自动创建。")
        created = create_knowledge_base(target_collection, f"Auto-created RAG collection: {target_collection}", embedding_function=embedding_func)
        if not created:
            logger.error(f"无法自动创建所需的 Collection '{target_collection}'。请检查日志并手动创建。")
            raise RuntimeError(f"无法自动创建所需的 Collection '{target_collection}'。请检查日志并手动创建。")

    try:
        logger.debug(f"使用 Langchain Milvus Wrapper 连接到 '{target_collection}'...")
        instance = Milvus(
            embedding_function=embedding_func,
            collection_name=target_collection,
            connection_args={
                "uri": settings.milvus_uri,
                "token": settings.milvus_token,
                "alias": "default",
            },
            consistency_level=settings.milvus_consistency_level,
        )
        logger.info(f"Milvus 向量存储实例 '{target_collection}' 初始化成功。")
        vector_store_instances[target_collection] = instance
        return instance
    except Exception as e:
        logger.exception(f"初始化 Langchain Milvus 实例 '{target_collection}' 失败: {e}")
        raise RuntimeError(f"向量存储实例初始化失败: {e}") from e

def add_documents(docs: List[Document], collection_name: Optional[str] = None):
    """
    将文档添加到指定的 Milvus Collection。
    Args:
        docs: Langchain Document 对象列表。
        collection_name: 目标 Collection 名称。如果为 None, 使用默认配置。
    """
    if not docs:
        logger.warning("尝试添加空文档列表，操作跳过。")
        return

    target_collection = collection_name or settings.milvus_collection_name
    vector_store = get_vector_store_instance(target_collection)

    try:
        logger.info(f"正在向 Collection '{target_collection}' 添加 {len(docs)} 个文档片段...")
        vector_store.add_documents(docs)
        logger.info(f"成功向 Collection '{target_collection}' 添加 {len(docs)} 个文档片段。")

    except Exception as e:
        logger.exception(f"向 Collection '{target_collection}' 添加文档失败: {e}")
        raise

def get_retriever(
    collection_name: Optional[str] = None,
    strategy: Literal["vector", "rerank", "hybrid"] = "vector",
    top_k: int = 5,
    rerank_top_n: Optional[int] = 3,
):
    """
    获取基于指定策略的 Langchain Retriever。
    Args:
        collection_name: 目标 Collection 名称。
        strategy: 检索策略 ('vector', 'rerank', 'hybrid').
        top_k: 初始检索的文档数量 (传递给 Milvus)。
        rerank_top_n: 重排后返回的文档数量 (仅用于 'rerank' 策略)。

    Returns:
        一个 Langchain BaseRetriever 实例。
    """
    target_collection = collection_name or settings.milvus_collection_name
    vector_store = get_vector_store_instance(target_collection)

    if top_k <= 0:
        logger.warning(f"top_k ({top_k}) 必须是正数，将使用默认值 5。")
        top_k = 5
    final_rerank_top_n = rerank_top_n or min(3, top_k)
    if final_rerank_top_n <= 0:
        logger.warning(f"rerank_top_n ({rerank_top_n}) 必须是正数，将使用调整后的值 {min(3, top_k)}。")
        final_rerank_top_n = min(3, top_k)
    if final_rerank_top_n > top_k:
        logger.warning(f"rerank_top_n ({final_rerank_top_n}) 大于 top_k ({top_k})。将 rerank_top_n 调整为 {top_k}。")
        final_rerank_top_n = top_k

    search_kwargs = {'k': top_k}
    base_retriever = vector_store.as_retriever(search_kwargs=search_kwargs)

    if strategy == "vector":
        logger.info(f"使用 Vector 检索策略 (k={top_k}) for '{target_collection}'.")
        return base_retriever

    elif strategy == "rerank":
        logger.info(f"尝试使用 Rerank 检索策略 (base_k={top_k}, rerank_n={final_rerank_top_n}) for '{target_collection}'.")
        if not settings.cohere_api_key:
            logger.warning("Cohere API Key 未配置 ('COHERE_API_KEY')，无法使用 'rerank' 策略。回退到 'vector' 策略。")
            return base_retriever

        try:
            if CohereRerank is None:
                raise ImportError("CohereRerank class not available.")

            cohere_model = "rerank-multilingual-v3.0"
            logger.debug(f"初始化 CohereRerank (model={cohere_model}, top_n={final_rerank_top_n})")
            compressor = CohereRerank(
                cohere_api_key=settings.cohere_api_key,
                top_n=final_rerank_top_n,
                model=cohere_model
            )
            compression_retriever = ContextualCompressionRetriever(
                base_compressor=compressor,
                base_retriever=base_retriever
            )
            logger.info(f"成功初始化 Rerank 检索策略 using Cohere.")
            return compression_retriever
        except ImportError:
            logger.error("Cohere package or CohereRerank class 未找到。请运行 'poetry add langchain-cohere'。回退到 'vector' 策略。")
            return base_retriever
        except Exception as e:
            logger.error(f"初始化 Cohere Reranker 失败: {e}。回退到 'vector' 策略。")
            return base_retriever

    elif strategy == "hybrid":
        logger.warning("Hybrid 检索策略当前未完全实现。回退到 'vector' 策略。")
        return base_retriever

    else:
        logger.warning(f"未知的检索策略: '{strategy}'。回退到 'vector' 策略。")
        return base_retriever

# Ensure Document is imported if not already at the top
# from langchain_core.documents import Document

# Initialize store globally or use dependency injection
# Global initialization can be problematic in some async contexts or testing
# For simplicity here, but consider FastAPI dependencies for production
# try:
#     vector_store_instance = get_vector_store()
# except Exception as e:
#     print(f"CRITICAL: Failed to initialize vector store on startup: {e}")
#     vector_store_instance = None # Handle inability to connect gracefully

async def add_documents_to_vector_store(documents: List[Document], vector_store: Milvus):
    """Embeds and adds document chunks to the Milvus vector store."""
    if not documents:
        print("No documents provided to add.")
        return None
    if not vector_store:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Vector store not initialized.")

    try:
        ids = await vector_store.aadd_documents(documents)
        print(f"Added {len(documents)} chunks to Milvus. IDs: {ids[:5]}... ({len(ids)} total)")

        return ids
    except Exception as e:
        print(f"Error adding documents to Milvus: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to add documents to vector store: {e}")

async def search_similar_documents(query: str, k: int, vector_store: Milvus) -> List[Document]:
    """Searches for documents similar to the query in the vector store."""
    if not vector_store:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Vector store not initialized.")

    try:
        results_with_scores = await vector_store.asimilarity_search_with_score(query, k=k)

        results = []
        for doc, score in results_with_scores:
            doc.metadata['score'] = score
            results.append(doc)

        print(f"Found {len(results)} similar documents for query.")
        return results
    except Exception as e:
        print(f"Error searching documents in Milvus: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to search documents in vector store: {e}") 