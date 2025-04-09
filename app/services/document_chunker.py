"""
文档分块服务
负责文档分块处理，支持多种分块策略
"""
import os
import json
import logging
import hashlib
import pickle
import tiktoken
import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple, Callable, Collection, Union, Literal, Set
import mimetypes
from pathlib import Path
from functools import lru_cache

# Langchain core and common text splitters
from langchain_text_splitters import (
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

from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader,
    CSVLoader,
    UnstructuredMarkdownLoader,
    UnstructuredHTMLLoader,
    UnstructuredPowerPointLoader
)

from app.core.config import settings
from app.models.knowledge_base import ChunkingStrategy

logger = logging.getLogger(__name__)


# 定义文档分块基类
class TextSplitter(ABC):
    """文本分块基类"""
    
    def __init__(
        self,
        chunk_size: int = 4000,
        chunk_overlap: int = 200,
        length_function: Callable[[str], int] = len,
        keep_separator: bool = False
    ) -> None:
        """
        初始化文本分块器
        
        Args:
            chunk_size: 块大小
            chunk_overlap: 块重叠大小
            length_function: 计算文本长度的函数
            keep_separator: 是否保留分隔符
        """
        if chunk_overlap > chunk_size:
            raise ValueError(
                f"chunk_overlap({chunk_overlap})必须小于chunk_size({chunk_size})"
            )
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._length_function = length_function
        self._keep_separator = keep_separator
    
    @abstractmethod
    def split_text(self, text: str) -> List[str]:
        """
        分割文本
        
        Args:
            text: 要分割的文本
            
        Returns:
            分割后的文本块列表
        """
        pass
    
    def _join_docs(self, docs: List[str], separator: str) -> Optional[str]:
        """
        连接文档块
        
        Args:
            docs: 文档块列表
            separator: 分隔符
            
        Returns:
            连接后的文本
        """
        text = separator.join(docs)
        text = text.strip()
        if text == "":
            return None
        else:
            return text
    
    def _merge_splits(self, splits: List[str], separator: str) -> List[str]:
        """
        合并分割后的文本块
        
        Args:
            splits: 分割后的文本块
            separator: 分隔符
            
        Returns:
            合并后的文本块列表
        """
        # 计算每个分割的长度
        lengths = [self._length_function(text) for text in splits]
        separator_len = self._length_function(separator)
        
        docs = []
        current_doc = []
        current_length = 0
        
        for i, split in enumerate(splits):
            split_length = lengths[i]
            
            if current_length + split_length + (separator_len if current_doc else 0) > self._chunk_size:
                if current_doc:
                    doc = self._join_docs(current_doc, separator)
                    if doc is not None:
                        docs.append(doc)
                    
                    # 保留一部分重叠内容
                    overlap_chunks = []
                    overlap_length = 0
                    
                    for j in range(len(current_doc) - 1, -1, -1):
                        chunk = current_doc[j]
                        chunk_len = self._length_function(chunk)
                        
                        if overlap_length + chunk_len > self._chunk_overlap:
                            # 如果加上这个块后超过重叠大小，看是否需要保留
                            if overlap_length == 0:
                                # 如果还没有重叠，至少保留一个块
                                overlap_chunks.insert(0, chunk)
                            break
                        
                        overlap_chunks.insert(0, chunk)
                        overlap_length += chunk_len
                    
                    current_doc = overlap_chunks
                    current_length = overlap_length
                else:
                    current_doc = []
                    current_length = 0
            
            current_doc.append(split)
            current_length += split_length + (separator_len if len(current_doc) > 1 else 0)
        
        if current_doc:
            doc = self._join_docs(current_doc, separator)
            if doc is not None:
                docs.append(doc)
        
        return docs
    
    @classmethod
    def from_tiktoken_encoder(
        cls,
        encoding_name: str = "cl100k_base",
        model_name: Optional[str] = None,
        allowed_special: Union[Literal["all"], Set[str]] = set(),
        disallowed_special: Union[Literal["all"], Collection[str]] = "all",
        **kwargs
    ):
        """
        使用tiktoken编码器创建文本分块器
        
        Args:
            encoding_name: 编码器名称
            model_name: 模型名称
            allowed_special: 允许的特殊token
            disallowed_special: 不允许的特殊token
            **kwargs: 其他参数
            
        Returns:
            文本分块器实例
        """
        try:
            import tiktoken
        except ImportError:
            raise ImportError(
                "tiktoken包未安装，请使用 `pip install tiktoken` 安装"
            )
        
        if model_name is not None:
            enc = tiktoken.encoding_for_model(model_name)
        else:
            enc = tiktoken.get_encoding(encoding_name)
        
        def _token_length(text: str) -> int:
            return len(
                enc.encode(
                    text,
                    allowed_special=allowed_special,
                    disallowed_special=disallowed_special
                )
            )
        
        return cls(length_function=_token_length, **kwargs)


class RecursiveTextSplitter(TextSplitter):
    """递归文本分块器"""
    
    def __init__(
        self,
        separators: Optional[List[str]] = None,
        **kwargs
    ) -> None:
        """
        初始化递归文本分块器
        
        Args:
            separators: 分隔符列表，按优先级排序
            **kwargs: 其他参数
        """
        super().__init__(**kwargs)
        self._separators = separators or ["\n\n", "\n", " ", ""]
    
    def split_text(self, text: str) -> List[str]:
        """
        递归分割文本
        
        Args:
            text: 要分割的文本
            
        Returns:
            分割后的文本块列表
        """
        # 获取文本长度
        text_length = self._length_function(text)
        
        # 如果文本长度小于块大小，直接返回
        if text_length <= self._chunk_size:
            return [text]
        
        # 递归分割
        return self._split_text_recursive(text, self._separators)
    
    def _split_text_recursive(self, text: str, separators: List[str]) -> List[str]:
        """
        递归分割文本
        
        Args:
            text: 要分割的文本
            separators: 分隔符列表
            
        Returns:
            分割后的文本块列表
        """
        # 如果没有更多分隔符，返回文本
        if not separators:
            return [text]
        
        # 获取当前分隔符
        separator = separators[0]
        
        # 如果分隔符为空，将文本拆分为单个字符
        if separator == "":
            return [char for char in text]
        
        # 使用分隔符分割文本
        splits = text.split(separator)
        
        # 是否保留分隔符
        if self._keep_separator and separator != "":
            splits = [
                (f"{separator}{split}" if i > 0 else split)
                for i, split in enumerate(splits)
            ]
        
        # 获取分割后的文本
        final_chunks = []
        
        # 对于每个分割块
        for split in splits:
            # 如果分割块长度大于块大小，递归分割
            if self._length_function(split) > self._chunk_size:
                # 递归使用下一级分隔符分割
                recursive_chunks = self._split_text_recursive(split, separators[1:])
                final_chunks.extend(recursive_chunks)
            else:
                final_chunks.append(split)
        
        # 合并分割后的文本块
        return self._merge_splits(final_chunks, separator if self._keep_separator else "")


class FixedSizeTextSplitter(TextSplitter):
    """固定大小文本分块器"""
    
    def __init__(
        self,
        separator: str = " ",
        **kwargs
    ) -> None:
        """
        初始化固定大小文本分块器
        
        Args:
            separator: 分隔符
            **kwargs: 其他参数
        """
        super().__init__(**kwargs)
        self._separator = separator
    
    def split_text(self, text: str) -> List[str]:
        """
        分割文本为固定大小的块
        
        Args:
            text: 要分割的文本
            
        Returns:
            分割后的文本块列表
        """
        # 使用分隔符分割文本
        splits = text.split(self._separator)
        
        # 合并分割后的文本块
        return self._merge_splits(splits, self._separator)


class SemanticTextSplitter(TextSplitter):
    """语义文本分块器"""
    
    def __init__(
        self,
        embedding_function: Optional[Callable] = None,
        similarity_threshold: float = 0.7,
        **kwargs
    ) -> None:
        """
        初始化语义文本分块器
        
        Args:
            embedding_function: 嵌入函数
            similarity_threshold: 相似度阈值
            **kwargs: 其他参数
        """
        super().__init__(**kwargs)
        self._embedding_function = embedding_function
        self._similarity_threshold = similarity_threshold
    
    def split_text(self, text: str) -> List[str]:
        """
        基于语义分割文本
        
        Args:
            text: 要分割的文本
            
        Returns:
            分割后的文本块列表
        """
        # 如果没有提供嵌入函数，降级为RecursiveTextSplitter
        if self._embedding_function is None:
            logger.warning("没有提供嵌入函数，降级为RecursiveTextSplitter")
            return RecursiveTextSplitter(
                chunk_size=self._chunk_size,
                chunk_overlap=self._chunk_overlap,
                length_function=self._length_function,
                keep_separator=self._keep_separator
            ).split_text(text)
        
        # 先用段落分隔符进行初步分割
        initial_splits = text.split("\n\n")
        
        # 如果初步分割后的文本块数量小于2，降级为RecursiveTextSplitter
        if len(initial_splits) < 2:
            return RecursiveTextSplitter(
                chunk_size=self._chunk_size,
                chunk_overlap=self._chunk_overlap,
                length_function=self._length_function,
                keep_separator=self._keep_separator
            ).split_text(text)
        
        # 计算相似度并合并相似的块
        chunks = []
        current_chunk = initial_splits[0]
        current_embedding = self._embedding_function(current_chunk)
        
        for split in initial_splits[1:]:
            # 计算当前块的嵌入
            split_embedding = self._embedding_function(split)
            
            # 计算相似度
            similarity = self._calculate_similarity(current_embedding, split_embedding)
            
            # 如果相似度高于阈值且合并后不超过块大小，则合并
            combined_text = current_chunk + "\n\n" + split
            if (
                similarity > self._similarity_threshold
                and self._length_function(combined_text) <= self._chunk_size
            ):
                current_chunk = combined_text
                # 更新当前嵌入为合并后文本的嵌入
                current_embedding = self._embedding_function(current_chunk)
            else:
                # 否则，将当前块添加到结果中，并开始新的块
                chunks.append(current_chunk)
                current_chunk = split
                current_embedding = split_embedding
        
        # 添加最后一个块
        if current_chunk:
            chunks.append(current_chunk)
        
        # 检查是否有块超过了块大小
        final_chunks = []
        for chunk in chunks:
            if self._length_function(chunk) > self._chunk_size:
                # 如果块太大，使用RecursiveTextSplitter进一步分割
                sub_chunks = RecursiveTextSplitter(
                    chunk_size=self._chunk_size,
                    chunk_overlap=self._chunk_overlap,
                    length_function=self._length_function,
                    keep_separator=self._keep_separator
                ).split_text(chunk)
                final_chunks.extend(sub_chunks)
            else:
                final_chunks.append(chunk)
        
        return final_chunks
    
    def _calculate_similarity(self, embedding1, embedding2) -> float:
        """
        计算两个嵌入向量之间的余弦相似度
        
        Args:
            embedding1: 第一个嵌入向量
            embedding2: 第二个嵌入向量
            
        Returns:
            余弦相似度
        """
        import numpy as np
        
        # 转换为numpy数组
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # 计算余弦相似度
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))


class CustomSeparatorTextSplitter(TextSplitter):
    """自定义分隔符文本分块器"""
    
    def __init__(
        self,
        separators: List[str],
        **kwargs
    ) -> None:
        """
        初始化自定义分隔符文本分块器
        
        Args:
            separators: 分隔符列表
            **kwargs: 其他参数
        """
        super().__init__(**kwargs)
        self._separators = separators
    
    def split_text(self, text: str) -> List[str]:
        """
        使用自定义分隔符分割文本
        
        Args:
            text: 要分割的文本
            
        Returns:
            分割后的文本块列表
        """
        # 如果没有提供分隔符，降级为FixedSizeTextSplitter
        if not self._separators:
            logger.warning("没有提供分隔符，降级为FixedSizeTextSplitter")
            return FixedSizeTextSplitter(
                chunk_size=self._chunk_size,
                chunk_overlap=self._chunk_overlap,
                length_function=self._length_function,
                keep_separator=self._keep_separator
            ).split_text(text)
        
        # 创建正则表达式模式
        pattern = "|".join(map(re.escape, self._separators))
        
        # 使用正则表达式分割文本
        splits = re.split(f"({pattern})", text)
        
        # 如果需要保留分隔符，合并分隔符和文本
        if self._keep_separator:
            merged_splits = []
            for i in range(0, len(splits) - 1, 2):
                if i + 1 < len(splits):
                    merged_splits.append(splits[i] + splits[i+1])
                else:
                    merged_splits.append(splits[i])
            
            if len(splits) % 2 == 1:
                merged_splits.append(splits[-1])
            
            splits = merged_splits
        else:
            # 过滤掉分隔符
            splits = [s for i, s in enumerate(splits) if i % 2 == 0]
        
        # 合并分割后的文本块
        return self._merge_splits(splits, " ")


class DocumentChunker:
    """文档分块服务"""
    
    _code_file_extensions = {
        '.py': PythonCodeTextSplitter(),
        '.html': RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", "<", ">", "</", "/>", " ", ""],
            chunk_size=1000,
            chunk_overlap=200
        ),
        '.md': MarkdownTextSplitter(chunk_size=1000, chunk_overlap=200),
        '.xml': RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", "<", ">", "</", "/>", " ", ""],
            chunk_size=1000,
            chunk_overlap=200
        ),
        '.json': RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", "{", "}", "[", "]", ",", " ", ""],
            chunk_size=1000,
            chunk_overlap=200
        ),
        '.sql': RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", ";", " ", ""],
            chunk_size=1000,
            chunk_overlap=200
        )
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
        document_name: str = None,
        chunking_strategy: str = "fixed_size",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        custom_separators: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        异步分块文档
        
        Args:
            document_path: 文档路径
            document_name: 文档名称
            chunking_strategy: 分块策略，支持 fixed_size, recursive, semantic, custom
            chunk_size: 分块大小
            chunk_overlap: 分块重叠大小
            custom_separators: 自定义分隔符列表
            
        Returns:
            分块后的文档块列表
        """
        return DocumentChunker.chunk_document(
            document_path=document_path,
            document_name=document_name,
            chunking_strategy=chunking_strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            custom_separators=custom_separators
        )
    
    @staticmethod
    def chunk_document(
        document_path: str, 
        document_name: str = None,
        chunking_strategy: str = "fixed_size",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        custom_separators: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        分块文档
        
        Args:
            document_path: 文档路径
            document_name: 文档名称
            chunking_strategy: 分块策略，支持 fixed_size, recursive, semantic, custom
            chunk_size: 分块大小
            chunk_overlap: 分块重叠大小
            custom_separators: 自定义分隔符列表
            
        Returns:
            分块后的文档块列表
        """
        if not os.path.exists(document_path):
            logger.error(f"文档不存在: {document_path}")
            return []
        
        # 如果未提供文档名称，使用文件名
        if not document_name:
            document_name = os.path.basename(document_path)
        
        # 尝试从缓存获取结果
        cache_key = DocumentChunker._get_cache_key(
            document_path, chunking_strategy, chunk_size, chunk_overlap, custom_separators
        )
        cached_result = DocumentChunker._get_from_cache(cache_key)
        if cached_result:
            logger.info(f"从缓存加载分块结果: {document_path}, 共 {len(cached_result)} 个块")
            return cached_result
        
        # 获取文档内容
        content, meta_data = DocumentChunker._extract_content(document_path)
        if not content:
            logger.error(f"无法提取文档内容: {document_path}")
            return []
        
        # 记录额外的元数据
        if not meta_data:
            meta_data = {}
        
        meta_data.update({
            "source": document_path,
            "file_name": document_name
        })
        
        # 创建文本分块器
        text_splitter = DocumentChunker._create_text_splitter(
            chunking_strategy=chunking_strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            custom_separators=custom_separators,
            document_path=document_path
        )
        
        # 分块文本
        chunks = text_splitter.split_text(content)
        
        # 转换为标准格式
        result = []
        for i, chunk in enumerate(chunks):
            chunk_meta = meta_data.copy()
            chunk_meta["chunk_index"] = i
            
            # 计算token数量
            token_count = DocumentChunker._count_tokens(chunk)
            
            result.append({
                "content": chunk,
                "meta_data": chunk_meta,
                "chunk_index": i,
                "word_count": len(chunk.split()),
                "token_count": token_count
            })
        
        # 缓存结果
        DocumentChunker._save_to_cache(cache_key, result)
        
        return result
    
    @staticmethod
    def _create_text_splitter(
        chunking_strategy: str,
        chunk_size: int,
        chunk_overlap: int,
        custom_separators: Optional[List[str]],
        document_path: str
    ) -> TextSplitter:
        """
        创建文本分块器
        
        Args:
            chunking_strategy: 分块策略
            chunk_size: 分块大小
            chunk_overlap: 分块重叠大小
            custom_separators: 自定义分隔符列表
            document_path: 文档路径
            
        Returns:
            文本分块器
        """
        # 获取文件扩展名
        file_extension = Path(document_path).suffix.lower()
        
        # 如果是代码文件且有特定的分块器，使用特定的分块器
        if file_extension in DocumentChunker._code_file_extensions:
            # 代码文件使用特定的分块器
            return DocumentChunker._code_file_extensions[file_extension]
        
        # 创建基于策略的分块器
        if chunking_strategy == ChunkingStrategy.RECURSIVE or chunking_strategy == "recursive":
            return RecursiveTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
        elif chunking_strategy == ChunkingStrategy.FIXED_SIZE or chunking_strategy == "fixed_size":
            return FixedSizeTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
        elif chunking_strategy == ChunkingStrategy.SEMANTIC or chunking_strategy == "semantic":
            # 语义分块器需要嵌入函数，如果没有设置，将降级为递归分块器
            return SemanticTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
        elif chunking_strategy == ChunkingStrategy.CUSTOM or chunking_strategy == "custom":
            # 自定义分隔符分块器
            if not custom_separators:
                logger.warning("使用自定义分块策略但未提供分隔符，使用默认分隔符")
                custom_separators = ["\n\n", "\n", ".", " "]
            
            return CustomSeparatorTextSplitter(
                separators=custom_separators,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
        
        # 默认使用固定大小分块器
        logger.warning(f"未知的分块策略 {chunking_strategy}，使用固定大小分块器")
        return FixedSizeTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
    
    @staticmethod
    def _extract_content(document_path: str) -> Tuple[str, Dict[str, Any]]:
        """
        提取文档内容
        
        Args:
            document_path: 文档路径
            
        Returns:
            文档内容和元数据
        """
        file_extension = Path(document_path).suffix.lower()
        file_type = mimetypes.guess_type(document_path)[0]
        
        # 为常见的文件扩展名补充MIME类型
        if not file_type:
            extension_to_type = {
                '.txt': 'text/plain',
                '.md': 'text/markdown',
                '.pdf': 'application/pdf',
                '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                '.csv': 'text/csv',
                '.html': 'text/html',
                '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
            }
            file_type = extension_to_type.get(file_extension, 'text/plain')
        
        # 获取适合的加载器
        loader_class = DocumentChunker._document_loaders.get(file_type, TextLoader)
        
        try:
            # 加载文档
            loader = loader_class(document_path)
            docs = loader.load()
            
            # 合并文档内容
            content = "\n\n".join([doc.page_content for doc in docs])
            
            # 提取元数据
            meta_data = {}
            if docs:
                # 合并所有文档的元数据
                for doc in docs:
                    meta_data.update(doc.metadata)
            
            return content, meta_data
            
        except Exception as e:
            logger.error(f"提取文档内容失败: {str(e)}")
            
            # 尝试作为纯文本文件读取
            try:
                with open(document_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return content, {"source": document_path}
            except Exception as e2:
                logger.error(f"作为纯文本读取失败: {str(e2)}")
                return "", {}
    
    @staticmethod
    def _count_tokens(text: str, model_name: str = "gpt-3.5-turbo") -> int:
        """
        计算文本的token数量
        
        Args:
            text: 文本
            model_name: 模型名称
            
        Returns:
            token数量
        """
        try:
            encoding = tiktoken.encoding_for_model(model_name)
            tokens = len(encoding.encode(text))
            return tokens
        except Exception as e:
            logger.warning(f"计算token数量失败: {str(e)}")
            # 如果tiktoken失败，使用简单的估算方法（英文约1.3token/词，中文约1.5字符/token）
            # 检测文本中中文字符的比例
            chinese_char_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
            chinese_ratio = chinese_char_count / len(text) if text else 0
            
            if chinese_ratio > 0.5:
                # 主要是中文文本
                return len(text) // 2 + 1  # 中文大约2个字符一个token
            else:
                # 主要是英文文本
                return len(text.split()) + len(text) // 10  # 英文单词+额外符号
    
    @staticmethod
    def _get_cache_key(document_path: str, 
                      chunking_strategy: str, 
                      chunk_size: int, 
                      chunk_overlap: int,
                      custom_separators: Optional[List[str]] = None) -> str:
        """
        生成缓存键
        
        Args:
            document_path: 文档路径
            chunking_strategy: 分块策略
            chunk_size: 分块大小
            chunk_overlap: 分块重叠大小
            custom_separators: 自定义分隔符列表
            
        Returns:
            缓存键
        """
        # 获取文件最后修改时间
        mtime = os.path.getmtime(document_path)
        
        # 组合参数
        key = f"{document_path}:{mtime}:{chunking_strategy}:{chunk_size}:{chunk_overlap}"
        
        # 添加自定义分隔符到键中
        if custom_separators:
            key += f":{','.join(custom_separators)}"
        
        # 计算MD5哈希
        return hashlib.md5(key.encode()).hexdigest()
    
    @staticmethod
    def _get_from_cache(cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """
        从缓存获取结果
        
        Args:
            cache_key: 缓存键
            
        Returns:
            缓存的结果，未找到则返回None
        """
        cache_dir = os.path.join(settings.CACHE_DIR, "chunks")
        os.makedirs(cache_dir, exist_ok=True)
        
        cache_file = os.path.join(cache_dir, f"{cache_key}.pkl")
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                logger.warning(f"读取缓存失败: {str(e)}")
                return None
        
        return None
    
    @staticmethod
    def _save_to_cache(cache_key: str, data: List[Dict[str, Any]]) -> None:
        """
        保存结果到缓存
        
        Args:
            cache_key: 缓存键
            data: 要缓存的数据
        """
        cache_dir = os.path.join(settings.CACHE_DIR, "chunks")
        os.makedirs(cache_dir, exist_ok=True)
        
        cache_file = os.path.join(cache_dir, f"{cache_key}.pkl")
        
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            logger.warning(f"保存缓存失败: {str(e)}")
    
    @staticmethod
    def clear_cache(document_path: Optional[str] = None) -> None:
        """
        清除缓存
        
        Args:
            document_path: 文档路径，如果不提供则清除所有缓存
        """
        cache_dir = os.path.join(settings.CACHE_DIR, "chunks")
        
        if not os.path.exists(cache_dir):
            return
        
        if document_path:
            # 生成包含此文档路径的所有可能的缓存键的前缀
            file_hash = hashlib.md5(document_path.encode()).hexdigest()[:10]
            
            # 遍历缓存目录中的文件
            for cache_file in os.listdir(cache_dir):
                # 读取缓存文件内容检查是否包含文档路径
                cache_path = os.path.join(cache_dir, cache_file)
                try:
                    with open(cache_path, 'rb') as f:
                        cached_data = pickle.load(f)
                        
                    # 检查第一个块的meta_data中的source
                    if cached_data and cached_data[0].get('meta_data', {}).get('source') == document_path:
                        os.remove(cache_path)
                        logger.debug(f"已删除文档 {document_path} 的缓存文件 {cache_file}")
                except Exception:
                    # 如果读取失败，跳过此文件
                    continue
        else:
            # 清除所有缓存
            for cache_file in os.listdir(cache_dir):
                os.remove(os.path.join(cache_dir, cache_file))
            
            logger.debug("已清除所有分块缓存")

# 创建单例实例
document_chunker = DocumentChunker()
