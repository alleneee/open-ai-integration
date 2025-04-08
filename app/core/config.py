import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from typing import Optional, Literal, Dict, Any, List, Union
from pydantic import AnyUrl, field_validator, model_validator, Field
import json
import logging

# Load .env file at the application start
load_dotenv()

logger = logging.getLogger(__name__)

# Log environment variables before initializing Settings
logger.debug(f"[Config Init] CELERY_BROKER_URL from env: {os.getenv('CELERY_BROKER_URL')}")
logger.debug(f"[Config Init] CELERY_RESULT_BACKEND from env: {os.getenv('CELERY_RESULT_BACKEND')}")

# 应急默认值，确保应用能启动
FALLBACK_VALUES = {
    "embedding_provider": "openai",
    "default_llm_provider": "openai",
    "milvus_text_max_length": 65535
}

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
    milvus_text_max_length: int = FALLBACK_VALUES["milvus_text_max_length"]
    milvus_index_params: Optional[Dict[str, Any]] = Field(default_factory=dict) # Store as dict

    # Embeddings
    embedding_provider: Literal["openai", "huggingface", "qwen", "ollama", "jina", "custom"] = FALLBACK_VALUES["embedding_provider"]
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
    cors_origins: Union[List[str], str] = "*"

    # Langchain specific (optional, Langchain might try to auto-detect or use its own defaults)
    # langchain_project: Optional[str] = None

    # --- Celery Settings ---
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    upload_temp_dir: str = "/tmp/rag_uploads" # Example temporary directory
    redis_url: str = "redis://localhost:6379/2" # Added Redis URL for conversation history

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
        
    @field_validator('milvus_text_max_length', mode='before')
    def validate_int_fields(cls, value):
        if isinstance(value, str):
            # 移除可能的注释
            clean_value = value.split('#')[0].strip()
            try:
                return int(clean_value)
            except ValueError:
                logger.error(f"无法将'{value}'解析为整数")
                return 65535  # 默认值
        return value
    
    @field_validator('embedding_provider', 'default_llm_provider', mode='before')
    def validate_literal_fields(cls, value):
        if isinstance(value, str):
            # 移除引号和注释
            clean_value = value.strip()
            # 特别处理带引号的情况
            if clean_value.startswith('"'):
                end_quote = clean_value.find('"', 1)
                if end_quote > 0:
                    clean_value = clean_value[1:end_quote]
            elif clean_value.startswith("'"):
                end_quote = clean_value.find("'", 1)
                if end_quote > 0:
                    clean_value = clean_value[1:end_quote]
            # 处理任何注释
            if '#' in clean_value:
                clean_value = clean_value.split('#')[0].strip()
            
            logger.debug(f"清理后的值: '{clean_value}'")
            
            # 特别处理default_llm_provider
            if clean_value not in ["openai", "deepseek", "qwen"]:
                logger.warning(f"default_llm_provider值'{clean_value}'无效，使用默认值'openai'")
                return "openai"
                
            return clean_value
        return value

    # --- 应急初始化 ---
    @model_validator(mode='after')
    def check_critical_settings(self) -> 'Settings':
        missing_values = []
        if self.embedding_provider == 'openai' and not self.openai_api_key:
            missing_values.append("OPENAI_API_KEY (当前embedding_provider='openai')")
        
        if self.default_llm_provider == 'openai' and not self.openai_api_key:
            missing_values.append("OPENAI_API_KEY (当前default_llm_provider='openai')")
        
        if missing_values:
            logger.warning(f"配置中缺少关键值: {', '.join(missing_values)}")
            logger.warning("应用可能无法正常运行，除非提供这些值")
            
        return self

    # --- 清理函数 --- 
    @model_validator(mode='before')
    @classmethod
    def clean_env_values(cls, values):
        # 遍历所有字符串值，清理注释和引号
        for key, value in list(values.items()):
            if isinstance(value, str) and '#' in value:
                # 移除注释部分
                cleaned_value = value.split('#')[0].strip()
                # 如果有引号，移除它们
                if cleaned_value.startswith('"') and cleaned_value.endswith('"'):
                    cleaned_value = cleaned_value[1:-1]
                elif cleaned_value.startswith("'") and cleaned_value.endswith("'"):
                    cleaned_value = cleaned_value[1:-1]
                
                values[key] = cleaned_value
                if key in ['milvus_uri', 'embedding_provider', 'default_llm_provider']:
                    logger.info(f"已清理环境变量 {key}: '{value}' -> '{cleaned_value}'")
                
        return values

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        extra = 'ignore' # Ignore extra fields from .env

try:
    logger.debug("[Config Init] Attempting to initialize Settings()...")
    settings = Settings()
    logger.debug(f"[Config Init] Settings initialized. Type: {type(settings)}")
    logger.debug(f"[Config Init] settings.celery_broker_url: {getattr(settings, 'celery_broker_url', 'NOT FOUND')}")
    logger.debug(f"[Config Init] settings.celery_result_backend: {getattr(settings, 'celery_result_backend', 'NOT FOUND')}")
    logger.info(f"配置加载成功: embedding_provider={settings.embedding_provider}, default_llm_provider={settings.default_llm_provider}")
except Exception as e:
    logger.critical(f"配置加载失败: {e}", exc_info=True) # Add exc_info=True
    # 回退到基本配置
    settings = Settings(
        embedding_provider=FALLBACK_VALUES["embedding_provider"],
        default_llm_provider=FALLBACK_VALUES["default_llm_provider"],
        milvus_text_max_length=FALLBACK_VALUES["milvus_text_max_length"]
    )
    logger.warning("已加载应急配置")
    logger.debug(f"[Config Init - Fallback] settings.celery_broker_url: {getattr(settings, 'celery_broker_url', 'NOT FOUND')}")
    logger.debug(f"[Config Init - Fallback] settings.celery_result_backend: {getattr(settings, 'celery_result_backend', 'NOT FOUND')}") 