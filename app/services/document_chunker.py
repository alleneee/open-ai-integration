"""
文档分块服务
负责文档分块处理，支持多种分块策略
"""
import os
import json
import logging
import hashlib
import pickle
from typing import List, Dict, Any, Optional, Tuple
import mimetypes
from pathlib import Path
from functools import lru_cache

# Langchain core and common text splitters
from langchain.text_splitter import (
    RecursiveCharacterTextSplitter,
    MarkdownTextSplitter,
    TokenTextSplitter,
    CharacterTextSplitter,
    PythonCodeTextSplitter,
)
# Import specific code splitter from its new location
# Try importing from the 'code' submodule
# Remove the problematic import
# from langchain_text_splitters.code import JavascriptTextSplitter

from langchain.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader,
    CSVLoader,
    UnstructuredMarkdownLoader,
    UnstructuredHTMLLoader,
    UnstructuredPowerPointLoader
)

from app.core.config import settings

logger = logging.getLogger(__name__)


class DocumentChunker:
    """文档分块服务"""
    
    _code_file_extensions = {
        '.py': PythonCodeTextSplitter(),
        # Removed JavascriptTextSplitter entries
        # '.js': JavascriptTextSplitter(),
        # '.ts': JavascriptTextSplitter(),
        # '.jsx': JavascriptTextSplitter(),
        # '.tsx': JavascriptTextSplitter()
    }
    
    _document_loaders = {
        'application/pdf': PyPDFLoader,
        'text/plain': TextLoader,
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': Docx2txtLoader,
        'text/csv': CSVLoader,
        'text/markdown': UnstructuredMarkdownLoader,
        'text/html': UnstructuredHTMLLoader,
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': UnstructuredPowerPointLoader
    }
    
    @staticmethod
    async def chunk_document_async(
        document_path: str, 
        chunking_strategy: str = "paragraph",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        custom_separators: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        异步分块文档
        
        Args:
            document_path: 文档路径
            chunking_strategy: 分块策略，支持 paragraph, token, character, markdown, sentence, adaptive
            chunk_size: 分块大小
            chunk_overlap: 分块重叠大小
            custom_separators: 自定义分隔符列表
            
        Returns:
            分块后的文档块列表
        """
        return DocumentChunker.chunk_document(
            document_path=document_path,
            chunking_strategy=chunking_strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            custom_separators=custom_separators
        )
    
    @staticmethod
    def chunk_document(
        document_path: str, 
        chunking_strategy: str = "paragraph",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        custom_separators: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        分块文档
        
        Args:
            document_path: 文档路径
            chunking_strategy: 分块策略，支持 paragraph, token, character, markdown, sentence, adaptive
            chunk_size: 分块大小
            chunk_overlap: 分块重叠大小
            custom_separators: 自定义分隔符列表
            
        Returns:
            分块后的文档块列表
        """
        if not os.path.exists(document_path):
            logger.error(f"文档不存在: {document_path}")
            return []
        
        # 尝试从缓存获取结果
        cache_key = DocumentChunker._get_cache_key(
            document_path, chunking_strategy, chunk_size, chunk_overlap
        )
        cached_result = DocumentChunker._get_from_cache(cache_key)
        if cached_result:
            logger.info(f"从缓存加载分块结果: {document_path}, 共 {len(cached_result)} 个块")
            return cached_result
        
        # 自适应分块策略
        if chunking_strategy == "adaptive" or (
            chunking_strategy == "auto" and settings.ADAPTIVE_CHUNKING
        ):
            return DocumentChunker._adaptive_chunk_document(
                document_path=document_path,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
        
        # 根据文件类型和分块策略选择加载器和分割器
        document_loader = DocumentChunker._get_document_loader(document_path)
        text_splitter = DocumentChunker._get_text_splitter(
            document_path=document_path, 
            chunking_strategy=chunking_strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            custom_separators=custom_separators
        )
        
        if not document_loader or not text_splitter:
            logger.error(f"不支持的文件类型或分块策略: {document_path}, {chunking_strategy}")
            return []
        
        try:
            # 加载文档
            docs = document_loader(document_path).load()
            
            # 分割文档
            chunks = text_splitter.split_documents(docs)
            
            # 转换为标准格式
            result = []
            for i, chunk in enumerate(chunks):
                result.append({
                    "content": chunk.page_content,
                    "meta_data": {
                        "source": document_path,
                        **chunk.metadata
                    },
                    "chunk_index": i
                })
            
            # 缓存结果
            DocumentChunker._save_to_cache(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.error(f"文档分块失败: {str(e)}")
            return []
    
    @staticmethod
    def _adaptive_chunk_document(
        document_path: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> List[Dict[str, Any]]:
        """
        自适应分块文档，根据文件类型和内容自动选择最佳分块策略
        
        Args:
            document_path: 文档路径
            chunk_size: 分块大小
            chunk_overlap: 分块重叠大小
            
        Returns:
            分块后的文档块列表
        """
        file_extension = Path(document_path).suffix.lower()
        file_type = mimetypes.guess_type(document_path)[0]
        
        # 根据文件类型选择合适的分块策略
        if file_extension in ['.md', '.markdown']:
            chunking_strategy = "markdown"
        elif file_extension in DocumentChunker._code_file_extensions:
            chunking_strategy = "code"
        elif file_type == "application/pdf":
            # PDF通常按页面分块更好
            chunking_strategy = "recursive"
            chunk_size = max(chunk_size, 1500)  # PDF页面通常较大
        elif file_extension in ['.docx']:
            # Word文档适合段落分块
            chunking_strategy = "paragraph"
        elif file_extension in ['.csv', '.xlsx', '.xls']:
            # 表格文档按行分块
            chunking_strategy = "character"
            chunk_overlap = min(chunk_overlap, 50)  # 表格不需要太大的重叠
        elif file_extension in ['.txt', '.log']:
            # 检查是否是结构化日志
            if DocumentChunker._is_structured_content(document_path):
                chunking_strategy = "character"
                chunk_overlap = min(chunk_overlap, 50)
            else:
                chunking_strategy = "paragraph"
        else:
            # 默认使用递归字符分割器
            chunking_strategy = "recursive"
        
        logger.info(f"自适应分块策略: {file_extension} -> {chunking_strategy}")
        
        return DocumentChunker.chunk_document(
            document_path=document_path,
            chunking_strategy=chunking_strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
    
    @staticmethod
    def _is_structured_content(file_path: str, sample_lines: int = 10) -> bool:
        """
        检查文件内容是否是结构化内容（如JSON或CSV）
        
        Args:
            file_path: 文件路径
            sample_lines: 采样的行数
            
        Returns:
            是否是结构化内容
        """
        try:
            # 读取文件前几行
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [f.readline().strip() for _ in range(sample_lines)]
            
            # 检查是否包含JSON结构
            for line in lines:
                if line.startswith('{') and line.endswith('}'):
                    try:
                        json.loads(line)
                        return True
                    except:
                        pass
            
            # 检查CSV结构（包含多个逗号）
            comma_counts = [line.count(',') for line in lines if line]
            if comma_counts and min(comma_counts) > 3:
                return True
                
            return False
        except:
            return False
    
    @staticmethod
    def _get_document_loader(document_path: str):
        """获取对应的文档加载器"""
        file_type = mimetypes.guess_type(document_path)[0]
        file_extension = Path(document_path).suffix.lower()
        
        # 根据文件类型选择加载器
        if file_type in DocumentChunker._document_loaders:
            return DocumentChunker._document_loaders[file_type]
        
        # 根据扩展名再次尝试
        if file_extension == '.txt':
            return TextLoader
        elif file_extension == '.pdf':
            return PyPDFLoader
        elif file_extension in ['.docx']:
            return Docx2txtLoader
        elif file_extension == '.csv':
            return CSVLoader
        elif file_extension in ['.md', '.markdown']:
            return UnstructuredMarkdownLoader
        elif file_extension in ['.html', '.htm']:
            return UnstructuredHTMLLoader
        elif file_extension in ['.ppt', '.pptx']:
            return UnstructuredPowerPointLoader
        
        # 默认使用文本加载器
        return TextLoader
    
    @staticmethod
    def _get_text_splitter(
        document_path: str,
        chunking_strategy: str,
        chunk_size: int,
        chunk_overlap: int,
        custom_separators: Optional[List[str]] = None
    ):
        """获取对应的文本分割器"""
        file_extension = Path(document_path).suffix.lower()
        
        # 如果提供了自定义分隔符，优先使用
        if custom_separators:
            return RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=custom_separators
            )
        
        # 根据分块策略选择分割器
        if chunking_strategy == "paragraph":
            return RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["\n\n", "\n", ". ", " ", ""]
            )
        elif chunking_strategy == "token":
            return TokenTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
        elif chunking_strategy == "character":
            return CharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
        elif chunking_strategy == "markdown":
            return MarkdownTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
        elif chunking_strategy == "recursive":
            return RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
        elif chunking_strategy == "sentence":
            return RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=[". ", "! ", "? ", "\n", " ", ""]
            )
        elif chunking_strategy == "code" and file_extension in DocumentChunker._code_file_extensions:
            # 使用特定的代码分割器
            splitter = DocumentChunker._code_file_extensions[file_extension]
            splitter.chunk_size = chunk_size
            splitter.chunk_overlap = chunk_overlap
            return splitter
        elif chunking_strategy == "newline":
            # 使用换行符分块
            return RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["\n\n", "\n", ""]
            )
        elif chunking_strategy == "double_newline":
            # 仅使用双换行符分块（段落级别）
            return RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["\n\n", ""]
            )
        elif chunking_strategy == "custom":
            # 仅在未提供自定义分隔符时使用默认分隔符
            return RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["\n\n", "\n", ". ", ", ", " ", ""]
            )
        elif chunking_strategy == "chinese":
            # 针对中文内容的分块策略
            return RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
            )
        
        # 默认使用递归字符分割器
        return RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

    @staticmethod
    def _get_cache_key(
        document_path: str,
        chunking_strategy: str,
        chunk_size: int,
        chunk_overlap: int
    ) -> str:
        """
        生成缓存键
        
        Args:
            document_path: 文档路径
            chunking_strategy: 分块策略
            chunk_size: 分块大小
            chunk_overlap: 分块重叠大小
            
        Returns:
            缓存键
        """
        # 获取文件修改时间和大小
        try:
            mtime = os.path.getmtime(document_path)
            size = os.path.getsize(document_path)
        except (FileNotFoundError, PermissionError):
            return ""
        
        # 创建缓存键
        key_data = f"{document_path}:{mtime}:{size}:{chunking_strategy}:{chunk_size}:{chunk_overlap}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    @staticmethod
    def _get_cache_dir() -> str:
        """
        获取缓存目录
        
        Returns:
            缓存目录路径
        """
        cache_dir = os.path.join(settings.TEMP_DIR, "chunk_cache")
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir
    
    @staticmethod
    def _get_from_cache(cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """
        从缓存获取结果
        
        Args:
            cache_key: 缓存键
            
        Returns:
            缓存的分块结果，如果没有缓存则返回None
        """
        if not cache_key:
            return None
            
        cache_path = os.path.join(DocumentChunker._get_cache_dir(), f"{cache_key}.pkl")
        
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "rb") as f:
                    return pickle.load(f)
            except Exception as e:
                logger.error(f"读取缓存失败: {str(e)}")
                
        return None
    
    @staticmethod
    def _save_to_cache(cache_key: str, result: List[Dict[str, Any]]) -> bool:
        """
        保存结果到缓存
        
        Args:
            cache_key: 缓存键
            result: 分块结果
            
        Returns:
            保存成功返回True，否则返回False
        """
        if not cache_key or not result:
            return False
            
        cache_path = os.path.join(DocumentChunker._get_cache_dir(), f"{cache_key}.pkl")
        
        try:
            with open(cache_path, "wb") as f:
                pickle.dump(result, f)
            return True
        except Exception as e:
            logger.error(f"保存缓存失败: {str(e)}")
            return False
    
    @staticmethod
    def clear_cache(document_path: Optional[str] = None) -> int:
        """
        清除缓存
        
        Args:
            document_path: 文档路径，如果提供则只清除该文档的缓存
            
        Returns:
            清除的缓存文件数量
        """
        cache_dir = DocumentChunker._get_cache_dir()
        count = 0
        
        if document_path:
            # 只清除指定文档的缓存
            for file in os.listdir(cache_dir):
                if file.endswith(".pkl"):
                    cache_path = os.path.join(cache_dir, file)
                    try:
                        with open(cache_path, "rb") as f:
                            data = pickle.load(f)
                            
                        # 检查每个块的元数据中是否包含该文档路径
                        if data and isinstance(data, list) and data[0].get("meta_data", {}).get("source") == document_path:
                            os.remove(cache_path)
                            count += 1
                    except:
                        pass
        else:
            # 清除所有缓存
            for file in os.listdir(cache_dir):
                if file.endswith(".pkl"):
                    os.remove(os.path.join(cache_dir, file))
                    count += 1
                    
        return count


# 创建文档分块服务单例
document_chunker = DocumentChunker()
