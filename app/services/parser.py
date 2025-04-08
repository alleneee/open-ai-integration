import io
import tempfile
import logging
import os
from typing import List, Optional, Dict, Any, Union, Tuple
from fastapi import UploadFile, HTTPException, status
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 导入特定的加载器 - 确保这些与 Langchain 0.3 兼容
from langchain_community.document_loaders import PyPDFLoader, UnstructuredMarkdownLoader, TextLoader
import docx # 直接使用 python-docx 作为替代方案

# 日志配置
logger = logging.getLogger(__name__)

# 允许的内容类型及其对应的文件扩展名
ALLOWED_CONTENT_TYPES = {
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "text/markdown": ".md",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx"
}

# 文本分割参数 - 移动到配置中，这里作为默认值
DEFAULT_CHUNK_SIZE = 1000  # 块大小
DEFAULT_CHUNK_OVERLAP = 150  # 块重叠大小

class FileParsingError(Exception):
    """文档解析错误的自定义异常"""
    def __init__(self, message: str, file_type: str = None, original_error: Exception = None):
        self.message = message
        self.file_type = file_type
        self.original_error = original_error
        super().__init__(self.message)

def _get_splitter(chunk_size: int = DEFAULT_CHUNK_SIZE, 
                 chunk_overlap: int = DEFAULT_CHUNK_OVERLAP) -> RecursiveCharacterTextSplitter:
    """获取文本分割器实例"""
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        add_start_index=True,
    )

def _load_pdf(file_content: bytes, filename: str) -> List[Document]:
    """加载 PDF 文件内容。"""
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpfile:
            tmpfile.write(file_content)
            tmp_path = tmpfile.name
            
        logger.debug(f"使用临时文件 {tmp_path} 加载 PDF")
        loader = PyPDFLoader(tmp_path)
        docs = loader.load()
        
        for doc in docs:
            doc.metadata["source"] = filename
            doc.metadata["file_type"] = "pdf"
            
        logger.info(f"成功从 {filename} 加载了 {len(docs)} 页 PDF 内容")
        return docs
        
    except Exception as e:
        logger.error(f"加载 PDF {filename} 时出错: {e}", exc_info=True)
        raise FileParsingError(f"解析 PDF 失败: {e}", file_type="pdf", original_error=e)
        
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
                logger.debug(f"已清理临时 PDF 文件 {tmp_path}")
            except OSError as remove_err:
                logger.warning(f"清理临时 PDF 文件 {tmp_path} 失败: {remove_err}")

def _load_markdown(file_content: bytes, filename: str) -> List[Document]:
    """加载 Markdown 文件内容。"""
    tmp_path = None
    try:
        content = file_content.decode('utf-8')
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".md", encoding='utf-8') as tmpfile:
            tmpfile.write(content)
            tmp_path = tmpfile.name
            
        logger.debug(f"使用临时文件 {tmp_path} 加载 Markdown")
        loader = UnstructuredMarkdownLoader(tmp_path)
        docs = loader.load()
        
        for doc in docs:
            doc.metadata["source"] = filename
            doc.metadata["file_type"] = "markdown"
            
        logger.info(f"成功从 {filename} 加载了 Markdown 内容，共 {len(docs)} 个文档")
        return docs
        
    except Exception as e:
        logger.error(f"加载 Markdown {filename} 时出错: {e}", exc_info=True)
        raise FileParsingError(f"解析 Markdown 失败: {e}", file_type="markdown", original_error=e)
        
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
                logger.debug(f"已清理临时 Markdown 文件 {tmp_path}")
            except OSError as remove_err:
                logger.warning(f"清理临时 Markdown 文件 {tmp_path} 失败: {remove_err}")

def _load_text(file_content: bytes, filename: str) -> List[Document]:
    """加载纯文本文件内容。"""
    tmp_path = None
    try:
        content = file_content.decode('utf-8')
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".txt", encoding='utf-8') as tmpfile:
            tmpfile.write(content)
            tmp_path = tmpfile.name
            
        logger.debug(f"使用临时文件 {tmp_path} 加载文本")
        loader = TextLoader(tmp_path, encoding='utf-8')
        docs = loader.load()
        
        for doc in docs:
            doc.metadata["source"] = filename
            doc.metadata["file_type"] = "text"
            
        logger.info(f"成功从 {filename} 加载了文本内容，共 {len(docs)} 个文档")
        return docs
        
    except Exception as e:
        logger.error(f"加载文本 {filename} 时出错: {e}", exc_info=True)
        raise FileParsingError(f"解析文本失败: {e}", file_type="text", original_error=e)
        
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
                logger.debug(f"已清理临时文本文件 {tmp_path}")
            except OSError as remove_err:
                logger.warning(f"清理临时文本文件 {tmp_path} 失败: {remove_err}")

def _load_docx(file_path: str, filename: str) -> List[Document]:
    """加载 DOCX 文件内容。"""
    try:
        logger.debug(f"从路径 {file_path} 加载 DOCX")
        # 使用 python-docx 直接读取内容
        doc = docx.Document(file_path)
        full_text = []
        
        # 提取段落文本
        for para in doc.paragraphs:
            if para.text.strip():  # 跳过空段落
                full_text.append(para.text)
                
        # 创建 Langchain Document
        document = Document(
            page_content="\n\n".join(full_text),
            metadata={"source": filename, "file_type": "docx"}
        )
        
        logger.info(f"成功从 {filename} 加载了 DOCX 内容，共 {len(full_text)} 个段落")
        return [document]
        
    except Exception as e:
        logger.error(f"加载 DOCX {filename} 时出错: {e}", exc_info=True)
        raise FileParsingError(f"解析 DOCX 失败: {e}", file_type="docx", original_error=e)

def parse_file_from_path_and_split(file_path: str, original_filename: str,
                                   chunk_size: int = DEFAULT_CHUNK_SIZE,
                                   chunk_overlap: int = DEFAULT_CHUNK_OVERLAP) -> List[Document]:
    """
    从文件路径同步加载、解析和分割文档。
    
    Args:
        file_path: 文件的本地路径
        original_filename: 原始文件名
        chunk_size: 文本块大小
        chunk_overlap: 文本块重叠大小
        
    Returns:
        分割后的文档列表
    
    Raises:
        FileParsingError: 解析过程中出现错误
    """
    logger.info(f"从路径 {file_path} 解析文件 {original_filename}")
    
    # 确定文件类型
    file_extension = os.path.splitext(original_filename)[1].lower()
    if not file_extension:
        # 尝试从文件路径获取扩展名
        file_extension = os.path.splitext(file_path)[1].lower()
        
    # 将扩展名映射到内容类型
    content_type_map = {
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    
    content_type = content_type_map.get(file_extension)
    if not content_type:
        raise FileParsingError(f"不支持的文件扩展名: {file_extension}")
    
    # 读取文件内容
    try:
        with open(file_path, 'rb') as file:
            file_content = file.read()
    except Exception as e:
        logger.error(f"读取文件 {file_path} 时出错: {e}", exc_info=True)
        raise FileParsingError(f"读取文件失败: {e}")
        
    # 解析文件
    raw_docs = []
    try:
        if content_type == "application/pdf":
            raw_docs = _load_pdf(file_content, original_filename)
        elif content_type == "text/markdown":
            raw_docs = _load_markdown(file_content, original_filename)
        elif content_type == "text/plain":
            raw_docs = _load_text(file_content, original_filename)
        elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            raw_docs = _load_docx(file_path, original_filename)
    except FileParsingError:
        # 让自定义异常传递上去
        raise
    except Exception as e:
        logger.error(f"解析文件 {original_filename} 时出错: {e}", exc_info=True)
        raise FileParsingError(f"解析文件失败: {e}")
    
    if not raw_docs:
        logger.warning(f"文件 {original_filename} 解析后没有内容")
        raise FileParsingError("文档解析后没有内容")
        
    # 分割文档
    text_splitter = _get_splitter(chunk_size, chunk_overlap)
    
    all_splits = []
    for doc in raw_docs:
        try:
            splits = text_splitter.split_documents([doc])
            # 完善分块的元数据
            for i, split in enumerate(splits):
                # 确保元数据中有源文件信息
                if "source" not in split.metadata:
                    split.metadata["source"] = original_filename
                # 添加分块索引
                split.metadata["chunk_index"] = i
                # 移除不需要的元数据
                split.metadata.pop('start_index', None)
                
            all_splits.extend(splits)
        except Exception as e:
            logger.error(f"分割文档 {original_filename} 时出错: {e}", exc_info=True)
            raise FileParsingError(f"文档分割失败: {e}")
            
    if not all_splits:
        logger.warning(f"文件 {original_filename} 分割后没有内容")
        raise FileParsingError("文档分割后没有内容")
        
    logger.info(f"成功将文件 {original_filename} 解析并分割成 {len(all_splits)} 个块")
    return all_splits

async def parse_uploaded_file_and_split(file: UploadFile, 
                                       chunk_size: int = DEFAULT_CHUNK_SIZE,
                                       chunk_overlap: int = DEFAULT_CHUNK_OVERLAP) -> Tuple[List[Document], str]:
    """
    解析上传的文件并将其分割成文本块
    
    Args:
        file: FastAPI 上传文件对象
        chunk_size: 文本块大小
        chunk_overlap: 文本块重叠大小
        
    Returns:
        元组: (文档分块列表, 临时文件路径)
        
    Raises:
        HTTPException: 文件类型不支持或解析出错
    """
    content_type = file.content_type
    filename = file.filename

    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型: {content_type}。允许的类型: {list(ALLOWED_CONTENT_TYPES.keys())}"
        )

    file_content = await file.read()
    if not file_content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件为空")
    
    # 创建临时文件
    temp_file_path = None
    try:
        suffix = ALLOWED_CONTENT_TYPES[content_type]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmpfile:
            tmpfile.write(file_content)
            temp_file_path = tmpfile.name
        
        logger.info(f"上传文件 {filename} 已保存到临时路径 {temp_file_path}")
        
        # 解析和分割文档
        all_splits = parse_file_from_path_and_split(
            temp_file_path, 
            filename,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        return all_splits, temp_file_path
        
    except FileParsingError as e:
        # 清理临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except OSError:
                pass
                
        logger.error(f"解析上传文件 {filename} 时出错: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"解析文件失败: {e.message}"
        )
        
    except Exception as e:
        # 清理临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except OSError:
                pass
                
        logger.exception(f"处理上传文件 {filename} 时出错: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理文件时出错: {str(e)}"
        )