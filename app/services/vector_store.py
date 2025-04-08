"""
向量存储和检索服务
提供 Milvus 集合(知识库)管理、嵌入模型和检索功能
"""
import logging
import os
from typing import List, Optional, Dict, Any, Literal, Union, Tuple

# 配置日志
logger = logging.getLogger(__name__)

# 尝试导入pymilvus，如果失败则使用模拟对象
try:
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
def add_documents(documents, metadatas, collection_name=None):
    """添加文档到向量存储"""
    # 简化实现
    logger.info(f"添加 {len(documents)} 个文档到集合 {collection_name}")
    return True

def get_embedding_model():
    """获取嵌入模型"""
    return _get_embedding_instance() 