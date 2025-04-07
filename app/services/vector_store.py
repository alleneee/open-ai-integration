from typing import List, Optional, Dict, Any
from pymilvus import connections, utility, Collection
from langchain.vectorstores import Milvus
from langchain.embeddings.base import Embeddings
from langchain.docstore.document import Document
from fastapi import HTTPException, status

from app.config import settings

# Choose and initialize embedding model based on config
# Note: Ensure API keys are correctly set in the environment/.env file

def get_embedding_model() -> Embeddings:
    """Initializes and returns the embedding model based on settings."""
    provider = settings.embedding_provider
    try:
        if provider == "openai":
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY must be set for OpenAI embeddings.")
            # Langchain 0.3 might use a different import path or class name
            from langchain.embeddings import OpenAIEmbeddings
            # Ensure compatibility with Pydantic v1 if OpenAIEmbeddings uses it internally
            # May need older openai SDK version specified in pyproject.toml
            embeddings = OpenAIEmbeddings(
                model=settings.embedding_model_name,
                openai_api_key=settings.openai_api_key
                # Potentially add chunk_size based on older API needs
            )
        elif provider == "huggingface":
            # Langchain 0.3 might use a different import path or class name
            from langchain.embeddings import HuggingFaceEmbeddings
            embeddings = HuggingFaceEmbeddings(
                model_name=settings.huggingface_model_name,
                model_kwargs={'device': 'cpu'} # Or 'cuda' if available
            )
        elif provider == "qwen":
            # Qwen 通过 Dashscope 的 embedding 功能
            if not settings.dashscope_api_key:
                raise ValueError("使用 Qwen embeddings 时必须设置 DASHSCOPE_API_KEY。")
            
            # 由于 Langchain 0.3 可能不直接支持 dashscope, 我们创建自定义包装器
            class QwenEmbeddings(Embeddings):
                """Qwen Embedding 包装器类 (通过 Dashscope)"""
                
                def __init__(self, api_key: str, model_name: str):
                    self.api_key = api_key
                    self.model_name = model_name
                    
                def _dashscope_embed(self, texts):
                    """调用 Dashscope API 获取嵌入向量"""
                    try:
                        import dashscope
                        from dashscope.embeddings.text_embedding import TextEmbedding
                        from http import HTTPStatus
                        
                        dashscope.api_key = self.api_key
                        resp = TextEmbedding.call(
                            model=self.model_name,
                            input=texts,
                            text_type="document" # 或根据需求使用 "query"
                        )
                        
                        if resp.status_code == HTTPStatus.OK:
                            # 提取并返回嵌入
                            embeddings = [item['embedding'] for item in resp.output['embeddings']]
                            return embeddings
                        else:
                            raise RuntimeError(f"Dashscope API 错误: {resp.code} - {resp.message}")
                    except ImportError:
                        raise ImportError("缺少 dashscope 包，请安装: pip install dashscope")
                
                def embed_documents(self, texts: List[str]) -> List[List[float]]:
                    """为文档生成嵌入向量"""
                    return self._dashscope_embed(texts)
                
                def embed_query(self, text: str) -> List[float]:
                    """为查询生成嵌入向量"""
                    result = self._dashscope_embed([text])
                    return result[0] if result else []
            
            embeddings = QwenEmbeddings(
                api_key=settings.dashscope_api_key,
                model_name=settings.qwen_embedding_model_name
            )
            
        elif provider == "ollama":
            # Ollama 本地嵌入模型
            class OllamaEmbeddings(Embeddings):
                """Ollama 本地 Embedding 包装器类"""
                
                def __init__(self, base_url: str, model: str):
                    self.base_url = base_url
                    self.model = model
                    
                def _ollama_embed(self, texts, is_query=False):
                    """调用 Ollama API 获取嵌入向量"""
                    try:
                        import requests
                        import json
                        
                        results = []
                        for text in texts:
                            response = requests.post(
                                f"{self.base_url}/api/embeddings",
                                json={"model": self.model, "prompt": text}
                            )
                            
                            if response.status_code == 200:
                                embedding = response.json().get("embedding", [])
                                results.append(embedding)
                            else:
                                raise RuntimeError(f"Ollama API 错误: {response.status_code} - {response.text}")
                        
                        return results
                    except ImportError:
                        raise ImportError("缺少 requests 包，请安装: pip install requests")
                
                def embed_documents(self, texts: List[str]) -> List[List[float]]:
                    """为文档生成嵌入向量"""
                    return self._ollama_embed(texts)
                
                def embed_query(self, text: str) -> List[float]:
                    """为查询生成嵌入向量"""
                    result = self._ollama_embed([text], is_query=True)
                    return result[0] if result else []
            
            embeddings = OllamaEmbeddings(
                base_url=settings.ollama_base_url,
                model=settings.ollama_embedding_model
            )
            
        elif provider == "jina":
            # Jina AI Embeddings
            if not settings.jina_api_key:
                raise ValueError("使用 Jina embeddings 时必须设置 JINA_API_KEY。")
                
            class JinaEmbeddings(Embeddings):
                """Jina AI Embedding 包装器类"""
                
                def __init__(self, api_key: str, model: str):
                    self.api_key = api_key
                    self.model = model
                    
                def _jina_embed(self, texts):
                    """调用 Jina AI API 获取嵌入向量"""
                    try:
                        import requests
                        import json
                        
                        headers = {
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json"
                        }
                        
                        response = requests.post(
                            "https://api.jina.ai/v1/embeddings",
                            headers=headers,
                            json={"input": texts, "model": self.model}
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            embeddings = [item["embedding"] for item in result["data"]]
                            return embeddings
                        else:
                            raise RuntimeError(f"Jina AI API 错误: {response.status_code} - {response.text}")
                    except ImportError:
                        raise ImportError("缺少 requests 包，请安装: pip install requests")
                
                def embed_documents(self, texts: List[str]) -> List[List[float]]:
                    """为文档生成嵌入向量"""
                    return self._jina_embed(texts)
                
                def embed_query(self, text: str) -> List[float]:
                    """为查询生成嵌入向量"""
                    result = self._jina_embed([text])
                    return result[0] if result else []
            
            embeddings = JinaEmbeddings(
                api_key=settings.jina_api_key,
                model=settings.jina_embedding_model
            )
            
        elif provider == "custom":
            # 支持自定义本地模型
            if not settings.custom_embedding_model_path:
                raise ValueError("使用自定义嵌入模型时必须设置 custom_embedding_model_path。")
                
            # 这里提供一个示例实现，具体实现可能需要根据模型类型调整
            from langchain.embeddings import HuggingFaceEmbeddings
                
            embeddings = HuggingFaceEmbeddings(
                model_name=settings.custom_embedding_model_path,
                model_kwargs=settings.custom_embedding_model_kwargs
            )
            
        else:
            raise NotImplementedError(f"Embedding provider '{provider}' not supported.")
        return embeddings
    except ImportError as e:
        raise RuntimeError(f"Failed to import embedding model dependencies for {provider}: {e}. Make sure required packages are installed.")
    except Exception as e:
        raise RuntimeError(f"Failed to initialize embedding model {provider}: {e}")

embedding_function = get_embedding_model()

def get_vector_store() -> Milvus:
    """Initializes and returns the Milvus vector store instance."""
    try:
        # Connect to Milvus
        # Langchain 0.3 Milvus constructor might handle connection, or it might need separate setup
        # Check Langchain 0.3 docs for Milvus connection parameters
        connections.connect(
            alias="default",
            uri=settings.milvus_uri,
            token=settings.milvus_token,
            # Add user/password if using legacy auth
        )
        print(f"Connected to Milvus at {settings.milvus_uri}")

        # Check if collection exists, create if not (Milvus client usage)
        if not utility.has_collection(settings.milvus_collection_name):
            print(f"Collection '{settings.milvus_collection_name}' not found. It will be created by Langchain Milvus wrapper if needed.")
            # Langchain's Milvus wrapper often creates the collection on first add
            # Defining schema explicitly here might be needed in some setups
            # vector_dim = len(embedding_function.embed_query("test")) # Get embedding dimension
            # schema = Milvus.prepare_schema(...) # Consult Langchain 0.3 + PyMilvus docs
            # collection = Collection(name=settings.milvus_collection_name, schema=schema, using='default')
            # print(f"Collection '{settings.milvus_collection_name}' created.")
            # Milvus.prepare_index(...) # Create index after collection creation
            # print(f"Index created for collection '{settings.milvus_collection_name}'.")

        vector_store = Milvus(
            embedding_function=embedding_function,
            collection_name=settings.milvus_collection_name,
            connection_args={
                "alias": "default",
                "uri": settings.milvus_uri,
                "token": settings.milvus_token,
                 # Add user/password if needed
            },
            # Langchain 0.3 might have different parameters like `index_params`, `search_params`
        )
        print(f"Milvus vector store initialized for collection '{settings.milvus_collection_name}'.")
        return vector_store

    except Exception as e:
        print(f"Error connecting to or initializing Milvus: {e}")
        # Depending on where this is called, might need to handle differently
        # For now, raise a general exception or specific HTTP exception if in request context
        raise RuntimeError(f"Failed to initialize Milvus vector store: {e}")

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
        # The `add_documents` method handles embedding and upserting
        # Langchain 0.3 might have slightly different method name or parameters
        ids = await vector_store.aadd_documents(documents) # Use async version if available
        # ids = vector_store.add_documents(documents) # Sync version
        print(f"Added {len(documents)} chunks to Milvus. IDs: {ids[:5]}... ({len(ids)} total)")

        # Optional: Force a flush if needed, depends on Milvus/Langchain version behavior
        # vector_store.collection.flush() # Accessing underlying PyMilvus collection
        # print("Milvus collection flushed.")

        return ids # Return the generated vector IDs
    except Exception as e:
        print(f"Error adding documents to Milvus: {e}")
        # Consider more specific error handling based on potential Milvus/network errors
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to add documents to vector store: {e}")

async def search_similar_documents(query: str, k: int, vector_store: Milvus) -> List[Document]:
    """Searches for documents similar to the query in the vector store."""
    if not vector_store:
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Vector store not initialized.")

    try:
        # Langchain 0.3 might have different method name or parameters
        # results_with_scores = vector_store.similarity_search_with_score(query, k=k)
        results_with_scores = await vector_store.asimilarity_search_with_score(query, k=k) # Async if available

        # Process results (already includes scores in Langchain)
        results = []
        for doc, score in results_with_scores:
            # Add score to metadata for easy access later if not already present
            doc.metadata['score'] = score
            results.append(doc)

        print(f"Found {len(results)} similar documents for query.")
        return results
    except Exception as e:
        print(f"Error searching documents in Milvus: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to search documents in vector store: {e}") 