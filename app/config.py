import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from typing import Optional, Literal, Dict, Any, List
from pydantic import AnyUrl, field_validator, model_validator, Field
import json
import logging

# Load .env file at the application start
load_dotenv()

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    project_name: str = "Enterprise RAG System"
    project_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"

    # Milvus
    milvus_uri: str = "grpc://localhost:19530"
    milvus_token: Optional[str] = None
    milvus_collection_name: str = "rag_documents"
    milvus_consistency_level: str = "Bounded"
    milvus_text_max_length: int = 65535
    milvus_index_params: Optional[Dict[str, Any]] = Field(default_factory=dict) # Store as dict

    # Embeddings
    embedding_provider: Literal["openai", "huggingface", "qwen", "ollama", "jina", "custom"] = "openai"
    embedding_device: str = "cpu"
    openai_api_key: Optional[str] = None # Make sure this is set if provider is openai
    embedding_model_name: str = "text-embedding-ada-002"
    huggingface_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Qwen
    qwen_embedding_model_name: str = "text-embedding-v2"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_embedding_model: str = "llama2"

    # Jina
    jina_api_key: Optional[str] = None
    jina_embedding_model: str = "jina-embeddings-v2-base-en"

    # Custom
    custom_embedding_model_path: Optional[str] = None
    custom_embedding_model_kwargs: Dict[str, Any] = {}

    # LLMs
    default_llm_provider: Literal["openai", "deepseek", "qwen"] = "openai"
    openai_model_name: str = "gpt-3.5-turbo"
    # Add other provider keys and model names as needed
    deepseek_api_key: Optional[str] = None
    deepseek_model_name: str = "deepseek-chat" # Example model
    dashscope_api_key: Optional[str] = None # For Qwen
    qwen_model_name: str = "qwen-turbo" # Example model

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Langchain specific (optional, Langchain might try to auto-detect or use its own defaults)
    # langchain_project: Optional[str] = None

    # --- Celery Settings ---
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    upload_temp_dir: str = "/tmp/rag_uploads" # Example temporary directory

    # --- Validators --- 
    @field_validator('milvus_index_params', 'custom_embedding_model_kwargs', mode='before')
    def parse_json_string(cls, value):
        if isinstance(value, str):
            if not value.strip(): # Handle empty string
                return {}
            try:
                return json.loads(value)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON string for setting: {e}. Input: '{value}'")
                raise ValueError(f"Invalid JSON string provided: {e}")
        return value # Assume it's already a dict or None/default

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        extra = 'ignore' # Ignore extra fields from .env

settings = Settings() 