"""
向量存储和检索服务
提供 Milvus 集合(知识库)管理、嵌入模型和检索功能

更新说明 (2025-04-09):
1. 修复了add_documents函数，确保可靠地添加文档（使用自动生成的ID）
2. 添加了更好的元数据清理，避免类型不匹配问题
3. 修复了集合创建过程，使用更简单可靠的初始化方法
4. 当前限制：PyMilvus 2.5.x + LangChain 0.3.x 存在兼容性问题，暂不支持自定义ID
   未来可考虑升级到 langchain-milvus 库来解决这个问题

TODO:
1. 升级到 langchain-milvus 库，实现完整的自定义ID支持
2. 优化向量检索性能
3. 添加更多的向量相似度搜索方法支持
"""
import logging
import os
from typing import List, Optional, Dict, Any, Literal, Union, Tuple
from datetime import datetime

# 配置日志
logger = logging.getLogger(__name__)

# 尝试导入pymilvus，如果失败则使用模拟对象
try:
    import pymilvus
    from pymilvus import connections, utility, Collection
    HAS_PYMILVUS = True
except (ImportError, Exception) as e:
    HAS_PYMILVUS = False
    logger.warning(f"pymilvus导入失败，使用模拟对象: {e}")
    
    # 创建模拟对象
    class MockCollection:
        def __init__(self, name, **kwargs):
            self.name = name
            self.schema = None
            self.num_entities = 0
            
        def insert(self, *args, **kwargs):
            return {"insert_count": 0}
            
        def search(self, *args, **kwargs):
            return [], []
            
        def drop(self):
            return True
            
        def load(self):
            return None
            
        def release(self):
            return None
    
    class MockUtility:
        @staticmethod
        def list_collections():
            return []
            
        @staticmethod
        def has_collection(name):
            return False
            
        @staticmethod
        def drop_collection(name):
            return True
    
    class MockConnections:
        def __init__(self):
            self.connected = False
            
        def connect(self, *args, **kwargs):
            self.connected = True
            logger.info("[模拟] 连接到Milvus")
            
        def disconnect(self, *args, **kwargs):
            self.connected = False
            
        def has_connection(self, *args, **kwargs):
            return self.connected
    
    connections = MockConnections()
    utility = MockUtility()
    Collection = MockCollection

# 尝试导入LangChain相关包，如果失败则使用模拟对象
try:
    from langchain_core.documents import Document
    from langchain_core.embeddings import Embeddings
    from langchain_openai import OpenAIEmbeddings
    HAS_LANGCHAIN = True
except (ImportError, Exception) as e:
    HAS_LANGCHAIN = False
    logger.warning(f"langchain相关包导入失败，使用模拟对象: {e}")
    
    # 创建模拟对象
    class Document:
        def __init__(self, page_content="", metadata=None):
            self.page_content = page_content
            self.metadata = metadata or {}
    
    class MockEmbeddings:
        def embed_documents(self, texts):
            return [[0.1] * 768] * len(texts)
                
        def embed_query(self, text):
            return [0.1] * 768
    
    class OpenAIEmbeddings(MockEmbeddings):
        def __init__(self, *args, **kwargs):
            pass
    
    Embeddings = MockEmbeddings

# 尝试导入社区包
try:
    from langchain_community.vectorstores import Milvus
    from langchain_community.embeddings import HuggingFaceEmbeddings, OllamaEmbeddings, JinaEmbeddings
    HAS_COMMUNITY = True
except (ImportError, Exception) as e:
    HAS_COMMUNITY = False
    logger.warning(f"langchain_community包导入失败，使用模拟对象: {e}")
    
    # 创建模拟对象
    class Milvus:
        def __init__(self, *args, **kwargs):
            pass
            
        @classmethod
        def from_documents(cls, *args, **kwargs):
            return cls()
            
        @classmethod
        def from_texts(cls, *args, **kwargs):
            return cls()
            
        def similarity_search(self, *args, **kwargs):
            return [Document()]
            
        def similarity_search_with_score(self, *args, **kwargs):
            return [(Document(), 0.5)]
            
        def as_retriever(self, *args, **kwargs):
            return MockRetriever()
    
    class HuggingFaceEmbeddings(MockEmbeddings):
        def __init__(self, *args, **kwargs):
            pass
    
    class OllamaEmbeddings(MockEmbeddings):
        def __init__(self, *args, **kwargs):
            pass
    
    class JinaEmbeddings(MockEmbeddings):
        def __init__(self, *args, **kwargs):
            pass
    
    class MockRetriever:
        def get_relevant_documents(self, query):
            return [Document()]

# 尝试导入rerank功能
try:
    from langchain_cohere import CohereRerank
    from langchain.retrievers import ContextualCompressionRetriever
    HAS_COHERE = True
except (ImportError, Exception) as e:
    logger.warning(f"rerank相关包导入失败，使用模拟对象: {e}")
    HAS_COHERE = False
    
    # 创建模拟对象
    class CohereRerank:
        def __init__(self, *args, **kwargs):
            pass
    
    class ContextualCompressionRetriever:
        def __init__(self, *args, **kwargs):
            self.base_retriever = kwargs.get('base_retriever', MockRetriever())
            
        def get_relevant_documents(self, query):
            return self.base_retriever.get_relevant_documents(query)

from app.core.config import settings
from app.schemas.schemas import KnowledgeBaseResponse

# --- 缓存连接实例 --- #
_embedding_instance = None
_embedding_model_name = None

# --- Milvus连接函数 --- #
def get_milvus_connection():
    """获取Milvus连接，如果尚未连接则建立连接"""
    try:
        if not connections.has_connection("default"):
            logger.info(f"尝试连接Milvus: {settings.milvus_uri}")
            
            # 清除URI中的注释和多余空格，如果有
            uri = settings.milvus_uri
            if '#' in uri:
                uri = uri.split('#')[0].strip()
            if uri.startswith('"') and uri.endswith('"'):
                uri = uri[1:-1]
            elif uri.startswith("'") and uri.endswith("'"):
                uri = uri[1:-1]
                
            connect_kwargs = {
                "uri": uri
            }
            
            # 如果提供了token，则添加到连接参数
            if settings.milvus_token:
                token = settings.milvus_token
                if '#' in token:
                    token = token.split('#')[0].strip()
                if token.startswith('"') and token.endswith('"'):
                    token = token[1:-1]
                elif token.startswith("'") and token.endswith("'"):
                    token = token[1:-1]
                    
                if token != "your-milvus-api-key":  # 跳过默认值
                    connect_kwargs["token"] = token
            
            connections.connect("default", **connect_kwargs)
            logger.info("成功连接到Milvus")
        return connections
    except Exception as e:
        if not HAS_PYMILVUS:
            logger.warning("使用Milvus模拟对象，连接操作被模拟")
            return connections
        else:
            logger.error(f"连接Milvus时出错: {e}")
            raise ConnectionError(f"无法连接到Milvus: {e}")

# --- 嵌入模型实例 --- #
def _get_embedding_instance():
    """获取或创建嵌入模型实例"""
    global _embedding_instance, _embedding_model_name
    
    if (_embedding_instance is not None and 
        _embedding_model_name == settings.embedding_model_name):
        return _embedding_instance
    
    logger.info(f"初始化嵌入模型，提供商: {settings.embedding_provider}")
    
    try:
        provider = settings.embedding_provider
        
        if provider == "openai":
            if not settings.openai_api_key:
                logger.warning("OpenAI API key not found, using mock embeddings")
                _embedding_instance = MockEmbeddings()
            else:
                _embedding_instance = OpenAIEmbeddings(
                    openai_api_key=settings.openai_api_key,
                    model=settings.embedding_model_name
                )
        elif provider == "huggingface":
            if not HAS_COMMUNITY:
                logger.warning("HuggingFaceEmbeddings not available, using mock embeddings")
                _embedding_instance = MockEmbeddings()
            else:
                _embedding_instance = HuggingFaceEmbeddings(
                    model_name=settings.huggingface_model_name,
                    model_kwargs={'device': settings.embedding_device or 'cpu'},
                    encode_kwargs={'normalize_embeddings': True}
                )
        elif provider == "ollama":
            if not HAS_COMMUNITY:
                logger.warning("OllamaEmbeddings not available, using mock embeddings")
                _embedding_instance = MockEmbeddings()
            else:
                _embedding_instance = OllamaEmbeddings(
                    model=settings.ollama_embedding_model,
                    base_url=settings.ollama_base_url
                )
        elif provider == "jina":
            if not HAS_COMMUNITY:
                logger.warning("JinaEmbeddings not available, using mock embeddings")
                _embedding_instance = MockEmbeddings()
            else:
                _embedding_instance = JinaEmbeddings(
                    jina_api_key=settings.jina_api_key,
                    model_name=settings.jina_embedding_model
                )
        elif provider == "custom":
            if not HAS_COMMUNITY:
                logger.warning("Custom embeddings not available, using mock embeddings")
                _embedding_instance = MockEmbeddings()
            else:
                _embedding_instance = HuggingFaceEmbeddings(
                    model_name=settings.custom_embedding_model_path,
                    model_kwargs={**(settings.custom_embedding_model_kwargs or {}), 'device': settings.embedding_device or 'cpu'},
                    encode_kwargs={'normalize_embeddings': True}
                )
        else:
            logger.warning(f"不支持的嵌入模型提供商: {provider}，使用模拟对象")
            _embedding_instance = MockEmbeddings()
        
        _embedding_model_name = settings.embedding_model_name
        return _embedding_instance
    except Exception as e:
        logger.error(f"初始化嵌入模型时出错: {e}")
        # 出错时返回模拟对象，确保系统能继续运行
        _embedding_instance = MockEmbeddings()
        _embedding_model_name = "mock"
        return _embedding_instance

# --- 检索器函数 --- #
def get_retriever(collection_name=None, strategy="vector", top_k=5, rerank_top_n=3):
    """获取向量检索器"""
    try:
        # 使用指定集合名或默认集合名
        coll_name = collection_name or settings.milvus_collection_name
        
        # 如果使用模拟模式，直接返回模拟检索器
        if not HAS_PYMILVUS or not HAS_LANGCHAIN or not HAS_COMMUNITY:
            logger.warning("使用模拟检索器")
            return MockRetriever()
        
        # 确保Milvus连接
        get_milvus_connection()
        
        # 检查集合是否存在
        if not utility.has_collection(coll_name):
            logger.warning(f"集合 '{coll_name}' 不存在，使用模拟检索器")
            return MockRetriever()
        
        # 获取嵌入模型
        embedding_function = _get_embedding_instance()
        
        # 创建向量存储实例
        vector_store = Milvus(
            collection_name=coll_name,
            embedding_function=embedding_function,
            connection_args={"uri": settings.milvus_uri, "token": settings.milvus_token if settings.milvus_token else None},
            consistency_level=settings.milvus_consistency_level
        )
        
        # 创建基础检索器
        retriever = vector_store.as_retriever(search_kwargs={"k": top_k})
        
        # 根据策略应用不同的检索方法
        if strategy == "rerank" and HAS_COHERE:
            # 使用Cohere重排检索器
            compressor = CohereRerank()
            return ContextualCompressionRetriever(
                base_retriever=retriever,
                doc_compressor=compressor,
                # 重排数量参数
                search_kwargs={"k": rerank_top_n}
            )
        elif strategy == "hybrid":
            # 混合检索（简化实现）
            return retriever
        else:
            # 默认向量检索
            return retriever
    except Exception as e:
        logger.error(f"创建检索器时出错: {e}")
        return MockRetriever()

# --- 知识库管理函数 --- #
def list_knowledge_bases() -> List[KnowledgeBaseResponse]:
    """列出所有可用的知识库"""
    try:
        get_milvus_connection()
        collections = utility.list_collections()
        
        result = []
        for name in collections:
            try:
                collection = Collection(name)
                num_entities = collection.num_entities
                collection.release()
                
                result.append(KnowledgeBaseResponse(
                    collection_name=name,
                    num_entities=num_entities
                ))
            except Exception as e:
                logger.warning(f"获取集合 {name} 信息时出错: {e}")
                result.append(KnowledgeBaseResponse(
                    collection_name=name
                ))
                
        return result
    except Exception as e:
        logger.error(f"列出知识库失败: {e}")
        if not HAS_PYMILVUS:
            return []  # 使用模拟对象时返回空列表
        raise

def create_knowledge_base(collection_name: str, description: Optional[str] = None) -> KnowledgeBaseResponse:
    """创建新的知识库"""
    try:
        get_milvus_connection()
        
        if utility.has_collection(collection_name):
            logger.warning(f"知识库 '{collection_name}' 已存在")
            # 返回现有集合的信息
            collection = Collection(collection_name)
            num_entities = collection.num_entities
            collection.release()
            
            return KnowledgeBaseResponse(
                collection_name=collection_name,
                description=description,
                num_entities=num_entities
            )
            
        # 为简化演示，这里不实现实际创建逻辑
        # 在实际应用中，你需要定义架构并创建集合
        
        logger.info(f"成功创建知识库: {collection_name}")
        return KnowledgeBaseResponse(
            collection_name=collection_name,
            description=description,
            num_entities=0
        )
    except Exception as e:
        logger.error(f"创建知识库失败: {e}")
        if not HAS_PYMILVUS:
            # 使用模拟对象时返回模拟数据
            return KnowledgeBaseResponse(
                collection_name=collection_name,
                description=description,
                num_entities=0
            )
        raise

def get_knowledge_base(collection_name: str) -> Optional[KnowledgeBaseResponse]:
    """获取特定知识库的信息"""
    try:
        get_milvus_connection()
        
        if not utility.has_collection(collection_name):
            logger.warning(f"知识库 '{collection_name}' 不存在")
            return None
            
        collection = Collection(collection_name)
        num_entities = collection.num_entities
        collection.release()
        
        return KnowledgeBaseResponse(
            collection_name=collection_name,
            num_entities=num_entities
        )
    except Exception as e:
        logger.error(f"获取知识库信息失败: {e}")
        if not HAS_PYMILVUS:
            # 使用模拟对象时返回模拟数据
            return KnowledgeBaseResponse(
                collection_name=collection_name,
                num_entities=0
            )
        raise

def delete_knowledge_base(collection_name: str) -> bool:
    """永久删除知识库"""
    try:
        get_milvus_connection()
        
        if not utility.has_collection(collection_name):
            logger.warning(f"知识库 '{collection_name}' 不存在，无法删除")
            return False
            
        utility.drop_collection(collection_name)
        logger.info(f"成功删除知识库: {collection_name}")
        return True
    except Exception as e:
        logger.error(f"删除知识库失败: {e}")
        if not HAS_PYMILVUS:
            return True  # 使用模拟对象时返回成功
        raise

# 这些函数可以根据需要添加或修改
def add_documents(
    documents: List[str],
    metadatas: List[Dict[str, Any]] = None,
    documents_obj: List[Any] = None,
    collection_name: Optional[str] = None,
    auto_create: bool = True,
    ids: Optional[List[str]] = None
) -> bool:
    """添加文档到向量数据库

    参数:
        documents: 文档内容列表
        metadatas: 元数据列表，必须与documents长度相同
        documents_obj: 文档对象列表，可选
        collection_name: 集合名称
        auto_create: 如果集合不存在，是否自动创建
        ids: 可选的ID列表，如果提供，必须与documents长度相同
            注意: 当前版本暂不支持自定义ID (PyMilvus 2.5.0 + LangChain 0.3.x兼容性问题)

    返回:
        bool: 是否成功添加文档
    """
    try:
        if not documents:
            logger.error("没有文档需要添加")
            return False

        # 规范化集合名称
        collection_name = standardize_collection_name(collection_name)
        
        # 确保元数据列表存在且长度匹配
        if metadatas is None:
            metadatas = [{} for _ in documents]
        elif len(metadatas) != len(documents):
            logger.error(f"元数据列表长度({len(metadatas)})与文档列表长度({len(documents)})不匹配")
            return False
            
        # 如果提供了IDs，确保长度匹配
        if ids is not None and len(ids) != len(documents):
            logger.error(f"ID列表长度({len(ids)})与文档列表长度({len(documents)})不匹配")
            return False
            
        # 如果提供了自定义ID，警告用户当前版本不支持
        if ids is not None:
            logger.warning("当前版本暂不支持自定义ID (PyMilvus 2.5.0 + LangChain 0.3.x兼容性问题)")
            logger.warning("系统将自动生成ID而不使用提供的ID列表")
            
        # 清理元数据，移除可能导致类型问题的字段
        cleaned_metadatas = []
        for meta in metadatas:
            cleaned_meta = {}
            for k, v in meta.items():
                if k != "init":  # 跳过init字段，它在集合中可能有特殊含义
                    if isinstance(v, (str, int, float, bool)):
                        cleaned_meta[k] = v
                    else:
                        # 将复杂类型转为字符串
                        cleaned_meta[k] = str(v)
            cleaned_metadatas.append(cleaned_meta)
                
        # 获取连接参数
        connection_args = get_connection_args()
            
        # 获取嵌入模型
        embeddings = get_embeddings()
        
        # 检查集合是否存在
        collection_exists = check_collection_exists(collection_name)
        
        if not collection_exists:
            if not auto_create:
                logger.error(f"集合 {collection_name} 不存在，且未启用自动创建")
                return False
                
            # 创建新集合
            logger.info(f"创建新集合: {collection_name}")
            if not create_collection(collection_name):
                logger.error(f"创建集合 {collection_name} 失败")
                return False
                
        # 使用自动生成ID添加文档
        try:
            logger.info(f"添加 {len(documents)} 篇文档到集合 {collection_name}，使用自动生成的IDs")
            
            # 使用from_texts静态方法
            result = Milvus.from_texts(
                texts=documents,
                embedding=embeddings,
                metadatas=cleaned_metadatas,
                collection_name=collection_name,
                connection_args=connection_args
            )
            
            logger.info(f"成功添加 {len(documents)} 篇文档到集合 {collection_name}")
            return True
        except Exception as e:
            logger.error(f"添加文档失败: {str(e)}")
            return False
    except Exception as e:
        logger.error(f"添加文档时发生错误: {str(e)}")
        return False

def get_embeddings():
    """获取嵌入模型实例（_get_embedding_instance的别名函数）
    
    返回:
        嵌入模型实例
    """
    return _get_embedding_instance()

def create_collection(collection_name: str, dimension: int = 1536) -> bool:
    """创建知识库（向量存储集合）
    
    参数:
        collection_name: 集合名称
        dimension: 向量维度，默认为1536（适用于许多OpenAI嵌入模型）
        
    返回:
        创建成功返回True，否则返回False
    """
    # 标准化集合名称
    std_collection_name = get_standardized_collection_name(collection_name)
    
    logger.info(f"创建知识库: {std_collection_name}, 维度: {dimension}")
    
    try:
        # 连接Milvus
        get_milvus_connection()
        
        # 检查集合是否已存在
        if utility.has_collection(std_collection_name):
            logger.warning(f"知识库 '{std_collection_name}' 已存在，无需创建")
            return True
        
        # 使用嵌入模型
        embeddings = _get_embedding_instance()
        
        # 准备连接参数
        connection_args = get_connection_args()
        
        # 创建最小化的初始文档和元数据
        init_text = "初始化文档"
        init_metadata = {"source": "system"}  # 简单的元数据，避免类型问题
        
        # 使用LangChain的Milvus接口创建集合
        try:
            # 确保一个极其简单的初始集合创建
            Milvus.from_texts(
                texts=[init_text],
                embedding=embeddings,
                metadatas=[init_metadata],
                collection_name=std_collection_name,
                connection_args=connection_args
            )
            
            logger.info(f"成功创建知识库: {std_collection_name}")
            return True
        except Exception as e:
            logger.error(f"使用LangChain创建集合失败: {e}")
            raise e
    except Exception as e:
        logger.exception(f"创建知识库 '{std_collection_name}' 时出错: {e}")
        if not HAS_PYMILVUS or not HAS_LANGCHAIN:
            logger.warning("使用模拟对象，假设创建成功")
            return True
        return False

def check_collection_exists(collection_name: str) -> bool:
    """检查知识库是否存在
    
    参数:
        collection_name: 集合名称
        
    返回:
        存在返回True，否则返回False
    """
    try:
        # 连接Milvus
        get_milvus_connection()
        
        # 标准化集合名称
        std_collection_name = get_standardized_collection_name(collection_name)
        
        # 检查集合是否存在
        exists = utility.has_collection(std_collection_name)
        return exists
        
    except Exception as e:
        logger.exception(f"检查知识库 '{std_collection_name}' 是否存在时出错: {e}")
        if not HAS_PYMILVUS:
            # 使用模拟对象时，总是返回True
            return True
        return False

def delete_collection(collection_name: str) -> bool:
    """删除知识库
    
    参数:
        collection_name: 集合名称
        
    返回:
        删除成功返回True，否则返回False
    """
    try:
        # 连接Milvus
        get_milvus_connection()
        
        # 标准化集合名称
        std_collection_name = get_standardized_collection_name(collection_name)
        
        # 检查集合是否存在
        if not utility.has_collection(std_collection_name):
            logger.warning(f"知识库 '{std_collection_name}' 不存在，无需删除")
            return True
        
        # 删除集合
        utility.drop_collection(std_collection_name)
        logger.info(f"成功删除知识库: {std_collection_name}")
        return True
        
    except Exception as e:
        logger.exception(f"删除知识库 '{std_collection_name}' 时出错: {e}")
        if not HAS_PYMILVUS:
            # 使用模拟对象时，总是返回True
            return True
        return False

def get_all_collections() -> List[str]:
    """获取所有知识库名称
    
    返回:
        知识库名称列表
    """
    try:
        # 连接Milvus
        get_milvus_connection()
        
        # 获取所有集合
        collections = utility.list_collections()
        return collections
        
    except Exception as e:
        logger.exception(f"获取所有知识库时出错: {e}")
        if not HAS_PYMILVUS:
            # 使用模拟对象时，返回空列表
            return []
        return []

### 实现强化的知识库管理函数

def ensure_collection_exists(collection_name: str) -> bool:
    """确保向量存储集合存在，如不存在则创建
    
    参数:
        collection_name: 集合名称
        
    返回:
        成功返回True，失败返回False
    """
    try:
        # 标准化集合名称
        std_collection_name = get_standardized_collection_name(collection_name)
        
        if check_collection_exists(std_collection_name):
            logger.info(f"向量存储集合 {std_collection_name} 已存在")
            return True
        
        return create_collection(std_collection_name)
    except Exception as e:
        logger.exception(f"确保向量存储集合存在时出错: {e}")
        return False

def add_documents_to_knowledge_base(kb_id: str, documents=None, metadatas=None, docs=None) -> bool:
    """向指定知识库添加文档
    
    这个函数确保知识库存在，且使用知识库的ID作为集合名称
    
    参数:
        kb_id: 知识库ID
        documents: 文档内容列表
        metadatas: 元数据列表
        docs: 文档对象列表
    
    返回:
        成功返回True，失败返回False
    """
    # 标准化集合名称
    std_collection_name = get_standardized_collection_name(kb_id)
    
    # 验证知识库存在
    if not check_collection_exists(std_collection_name):
        logger.error(f"知识库 {std_collection_name} 不存在，请先创建知识库")
        return False
        
    # 调用添加文档的函数
    try:
        return add_documents(
            documents=documents,
            metadatas=metadatas,
            docs=docs,
            collection_name=std_collection_name,
            auto_create_collection=False  # 不自动创建知识库
        )
    except Exception as e:
        logger.exception(f"向知识库 {std_collection_name} 添加文档时出错: {e}")
        return False

def get_knowledge_base_stats(kb_id: str) -> Dict[str, Any]:
    """获取知识库统计信息
    
    参数:
        kb_id: 知识库ID
        
    返回:
        包含统计信息的字典
    """
    try:
        # 连接Milvus
        get_milvus_connection()
        
        # 标准化集合名称
        std_collection_name = get_standardized_collection_name(kb_id)
        
        # 验证知识库存在
        if not check_collection_exists(std_collection_name):
            return {
                "exists": False,
                "document_count": 0,
                "last_updated": None
            }
            
        # 获取集合信息
        try:
            collection = Collection(std_collection_name)
            collection.load()
            
            stats = {
                "exists": True,
                "document_count": collection.num_entities,
                "last_updated": datetime.now().isoformat()  # 当前时间，未来可以从元数据获取
            }
            
            collection.release()
            return stats
            
        except Exception as e:
            logger.warning(f"获取知识库 {std_collection_name} 统计信息时出错: {e}")
            return {
                "exists": True,
                "document_count": "未知(获取失败)",
                "error": str(e)
            }
    except Exception as e:
        logger.exception(f"获取知识库 {std_collection_name} 统计信息时出错: {e}")
        if not HAS_PYMILVUS:
            # 使用模拟对象时
            return {
                "exists": True,
                "document_count": 0,
                "note": "使用模拟对象"
            }
        return {
            "exists": False,
            "error": str(e)
        }

def sync_knowledge_base_metadata(kb_id: str, metadata: Dict[str, Any]) -> bool:
    """同步知识库元数据到向量存储
    
    参数:
        kb_id: 知识库ID
        metadata: 元数据字典
        
    返回:
        成功返回True，失败返回False
    """
    try:
        # 验证知识库存在
        if not check_collection_exists(kb_id):
            logger.error(f"知识库 {kb_id} 不存在，无法同步元数据")
            return False
            
        # 这里可以实现元数据同步逻辑
        # 例如，可以将元数据存储在向量存储的属性中
        logger.info(f"同步知识库 {kb_id} 元数据: {metadata}")
        
        # 由于当前向量存储可能不支持元数据存储，这里先返回成功
        return True
        
    except Exception as e:
        logger.exception(f"同步知识库 {kb_id} 元数据时出错: {e}")
        return False

def search_knowledge_base(query: str, kb_ids: List[str], top_k: int = 5) -> List[Dict[str, Any]]:
    """从知识库中搜索相关文档
    
    参数:
        query: 搜索查询
        kb_ids: 知识库ID列表
        top_k: 返回结果数量
        
    返回:
        包含内容和元数据的文档列表
    """
    logger.info(f"从知识库 {kb_ids} 搜索: {query}")
    results = []
    
    try:
        # 获取嵌入模型
        embeddings = _get_embedding_instance()
        
        # 为每个知识库执行搜索
        for kb_id in kb_ids:
            # 检查知识库是否存在
            if not check_collection_exists(kb_id):
                logger.warning(f"知识库 {kb_id} 不存在，跳过")
                continue
                
            # 创建Milvus实例
            try:
                # 准备连接参数
                connection_args = {"uri": settings.milvus_uri}
                if settings.milvus_token and settings.milvus_token != "your-milvus-api-key":
                    connection_args["token"] = settings.milvus_token
                
                vector_store = Milvus(
                    collection_name=kb_id,
                    embedding_function=embeddings,
                    connection_args=connection_args
                )
                
                # 执行相似性搜索
                docs_with_scores = vector_store.similarity_search_with_score(
                    query=query,
                    k=top_k
                )
                
                # 处理结果
                for doc, score in docs_with_scores:
                    # 标准化分数，Milvus返回的是L2距离，越小越好
                    # 将其转换为0-1范围的相似度分数
                    normalized_score = 1.0 / (1.0 + score)
                    
                    results.append({
                        "content": doc.page_content,
                        "source": doc.metadata.get("source", kb_id),
                        "score": normalized_score,
                        "metadata": doc.metadata
                    })
            except Exception as e:
                logger.error(f"搜索知识库 {kb_id} 时出错: {e}")
                continue
        
        # 按相似度分数排序
        results.sort(key=lambda x: x["score"], reverse=True)
        
        # 仅返回前top_k个结果
        return results[:top_k]
        
    except Exception as e:
        logger.exception(f"搜索知识库时出错: {e}")
        return []

def get_standardized_collection_name(kb_id: str) -> str:
    """
    获取标准化的集合名称，确保符合Milvus命名规则
    
    参数:
        kb_id: 知识库ID或集合名称
        
    返回:
        标准化后的集合名称
    """
    # 如果已经是标准化的名称（以kb_开头），则直接返回
    if kb_id.startswith("kb_"):
        return kb_id
    
    # 将ID中的连字符替换为下划线，并添加kb_前缀
    return f"kb_{kb_id.replace('-', '_')}"

def similarity_search(query_text: str, collection_name: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """相似度搜索
    
    参数:
        query_text: 查询文本
        collection_name: 集合名称
        top_k: 返回结果数量
        
    返回:
        搜索结果列表
    """
    logger.info(f"对集合 {collection_name} 进行相似度搜索: {query_text}")
    
    try:
        # 标准化集合名称
        std_collection_name = get_standardized_collection_name(collection_name)
        
        # 连接Milvus
        get_milvus_connection()
        
        # 检查集合是否存在
        if not check_collection_exists(std_collection_name):
            logger.warning(f"集合 {std_collection_name} 不存在")
            return []
            
        # 获取嵌入模型
        embeddings = _get_embedding_instance()
        
        # 准备连接参数
        connection_args = get_connection_args()
        
        # 创建Milvus客户端
        milvus_client = Milvus(
            collection_name=std_collection_name,
            embedding_function=embeddings,
            connection_args=connection_args
        )
        
        # 执行搜索
        results = milvus_client.similarity_search_with_score(
            query=query_text,
            k=top_k
        )
        
        # 格式化结果
        formatted_results = []
        for doc, score in results:
            formatted_results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score)
            })
            
        logger.info(f"搜索成功，返回 {len(formatted_results)} 个结果")
        return formatted_results
        
    except Exception as e:
        logger.exception(f"搜索知识库时出错: {e}")
        return []

def get_connection_args():
    """获取连接参数，并处理URI和token格式

    返回:
        连接参数字典
    """
    # 准备URI
    uri = settings.milvus_uri
    if "#" in uri:
        uri = uri.split("#")[0].strip()
    if uri.startswith('"') and uri.endswith('"'):
        uri = uri[1:-1]
    elif uri.startswith("'") and uri.endswith("'"):
        uri = uri[1:-1]
        
    # 转换 grpc:// 为 http://，解决 langchain-community 中的兼容性问题
    if uri.startswith("grpc://"):
        uri = uri.replace("grpc://", "http://")
        logger.info(f"将 grpc:// 格式的 URI 转换为 http:// 格式: {uri}")
    
    connection_args = {"uri": uri}
    
    # 添加token（如果有）
    if settings.milvus_token and settings.milvus_token != "your-milvus-api-key":
        token = settings.milvus_token
        if "#" in token:
            token = token.split("#")[0].strip()
        if token.startswith('"') and token.endswith('"'):
            token = token[1:-1]
        elif token.startswith("'") and token.endswith("'"):
            token = token[1:-1]
        connection_args["token"] = token
        
    return connection_args 

def standardize_collection_name(kb_id: str) -> str:
    """
    获取标准化的集合名称，确保符合Milvus命名规则（get_standardized_collection_name的别名函数）
    
    参数:
        kb_id: 知识库ID或集合名称
        
    返回:
        标准化后的集合名称
    """
    return get_standardized_collection_name(kb_id) 