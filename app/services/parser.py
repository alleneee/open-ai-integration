import io
from typing import List
from fastapi import UploadFile, HTTPException, status
from langchain.docstore.document import Document # 如果使用 0.3 版本, 确认导入路径是否正确
from langchain.text_splitter import RecursiveCharacterTextSplitter

# 导入特定的加载器 - 确保这些与 Langchain 0.3 兼容
# 查阅 Langchain 0.3 文档以获取正确的加载器类和导入路径。
# 这些可能位于 langchain.document_loaders 或类似位置。
from langchain.document_loaders import PyPDFLoader, UnstructuredMarkdownLoader, TextLoader
# 对于 DOCX, UnstructuredFileLoader 比较常用, 或者可能需要直接使用 python-docx
# from langchain.document_loaders import UnstructuredFileLoader # 示例
import docx # 直接使用 python-docx 作为替代方案

# 允许的内容类型及其对应的文件扩展名
ALLOWED_CONTENT_TYPES = {
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "text/markdown": ".md",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx"
}

# 文本分割参数
CHUNK_SIZE = 1000 # 块大小
CHUNK_OVERLAP = 150 # 块重叠大小

def _load_pdf(file_content: bytes, filename: str) -> List[Document]:
    """加载 PDF 文件内容。"""
    # PyPDFLoader 通常需要文件路径。我们需要将字节保存到临时文件中。
    # 或者, 检查 Langchain 0.3 的 PyPDFLoader 是否能直接处理字节。
    # 如果需要路径, 这是常用的模式:
    import tempfile
    import os
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpfile:
            tmpfile.write(file_content)
            tmp_path = tmpfile.name
        loader = PyPDFLoader(tmp_path)
        # Langchain 0.3 的加载器可能直接返回 Document, 或需要调用 .load() 方法。
        # 根据具体版本的 API 进行调整。
        docs = loader.load() # 或者可能是 `loader.load_and_split()` (如果可用)
        for doc in docs:
            doc.metadata["source"] = filename # 将原始文件名添加到元数据
        return docs
    except Exception as e:
        # 记录错误详情
        print(f"加载 PDF {filename} 时出错: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"解析 PDF 失败: {e}")
    finally:
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.remove(tmp_path) # 清理临时文件

def _load_markdown(file_content: bytes, filename: str) -> List[Document]:
    """加载 Markdown 文件内容。"""
    # 与 PDF 类似, 加载器通常需要文件路径。
    import tempfile
    import os
    try:
        content = file_content.decode('utf-8') # 假设 Markdown 文件使用 UTF-8 编码
        # UnstructuredMarkdownLoader 可能接受内容或需要路径
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".md", encoding='utf-8') as tmpfile:
            tmpfile.write(content)
            tmp_path = tmpfile.name
        loader = UnstructuredMarkdownLoader(tmp_path)
        docs = loader.load()
        for doc in docs:
            doc.metadata["source"] = filename
        return docs
    except Exception as e:
        print(f"加载 Markdown {filename} 时出错: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"解析 Markdown 失败: {e}")
    finally:
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.remove(tmp_path)

def _load_text(file_content: bytes, filename: str) -> List[Document]:
    """加载纯文本文件内容。"""
    # TextLoader 可能也需要路径, 或者有时可以处理原始文本。
    import tempfile
    import os
    try:
        content = file_content.decode('utf-8') # 假设文本文件使用 UTF-8 编码
        # 如果 TextLoader 需要路径:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".txt", encoding='utf-8') as tmpfile:
            tmpfile.write(content)
            tmp_path = tmpfile.name
        loader = TextLoader(tmp_path, encoding='utf-8')
        docs = loader.load()
        for doc in docs:
            doc.metadata["source"] = filename
        return docs
        # 如果它可以处理内容 (备选方案):
        # text_splitter = RecursiveCharacterTextSplitter(...) # 定义你的分割器
        # texts = text_splitter.split_text(content)
        # return [Document(page_content=t, metadata={"source": filename}) for t in texts]
    except Exception as e:
        print(f"加载文本文件 {filename} 时出错: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"解析文本文件失败: {e}")
    finally:
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.remove(tmp_path)

def _load_docx(file_content: bytes, filename: str) -> List[Document]:
    """加载 DOCX 文件内容。"""
    # 直接使用 python-docx, 因为 Langchain 的加载器可能对 docx 不太可靠或复杂
    try:
        doc_stream = io.BytesIO(file_content)
        document = docx.Document(doc_stream)
        full_text = "\n".join([para.text for para in document.paragraphs if para.text])

        # 将提取的文本包装在 Langchain Document 对象中
        # 如果需要, 稍后进行分割
        return [Document(page_content=full_text, metadata={"source": filename})]
    except Exception as e:
        print(f"加载 DOCX {filename} 时出错: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"解析 DOCX 文件失败: {e}")

async def parse_and_split_document(file: UploadFile) -> List[Document]:
    """根据上传文件的内容类型解析文件并将其分割成块。"""
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

    raw_docs: List[Document] = []
    try:
        if content_type == "application/pdf":
            raw_docs = _load_pdf(file_content, filename)
        elif content_type == "text/markdown":
            raw_docs = _load_markdown(file_content, filename)
        elif content_type == "text/plain":
            raw_docs = _load_text(file_content, filename)
        elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            raw_docs = _load_docx(file_content, filename)
        else:
            # 理论上此情况应已被初始检查捕获, 作为安全措施:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="未处理的内容类型 (尽管已通过初始检查)。")

    except HTTPException as http_exc: # 重新引发来自加载器的 HTTP 异常
        raise http_exc
    except Exception as e: # 捕获加载过程中的意外错误
        print(f"解析 {filename} ({content_type}) 时发生意外错误: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"处理文件时发生意外错误: {e}")

    if not raw_docs:
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="文档已加载但未产生任何内容。")

    # 将文档分割成更小的块
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        add_start_index=True, # 添加关于块位置的元数据
    )

    # 需要根据加载器返回文档的方式处理分割 (有些可能已经分割)
    all_splits = []
    for doc in raw_docs:
        # 确保 page_content 是字符串
        if isinstance(doc.page_content, str):
            splits = text_splitter.split_documents([doc]) # 作为列表传递
            all_splits.extend(splits)
        else:
            # 处理 page_content 可能不是字符串的情况 (较少见)
            print(f"警告: 在 {filename} 中跳过非字符串内容的文档块")
            continue

    if not all_splits:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="文档内容无法分割成可处理的块。")

    # 根据需要清理或添加更多元数据
    for split in all_splits:
        split.metadata.pop('start_index', None) # 分割后通常不需要
        # 确保文件名存在
        if 'source' not in split.metadata:
             split.metadata['source'] = filename


    print(f"成功将 '{filename}' 解析并分割成 {len(all_splits)} 个块。")
    return all_splits 