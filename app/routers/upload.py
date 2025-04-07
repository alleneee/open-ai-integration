from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status, BackgroundTasks
from langchain.vectorstores import Milvus
from typing import List

from app.services.parser import parse_and_split_document
from app.services.vector_store import add_documents_to_vector_store
from app.core.dependencies import get_cached_vector_store
from app.models.schemas import UploadResponse, GenericErrorResponse

router = APIRouter()

async def process_and_index_file(file: UploadFile, vector_store: Milvus):
    """用于解析、分割和索引上传文件的后台任务。"""
    filename = file.filename
    try:
        print(f"后台任务已开始处理: {filename}")
        # 1. 解析和分割
        # 注意: parse_and_split_document 已经是异步的
        document_chunks = await parse_and_split_document(file)
        if not document_chunks:
            print(f"未为 {filename} 生成任何块。跳过索引。")
            # 可以选择记录此事件或通知管理员
            return

        # 2. 添加到向量存储
        # 注意: add_documents_to_vector_store 是异步的
        await add_documents_to_vector_store(document_chunks, vector_store)
        print(f"已在后台成功处理和索引 {filename}。")

    except HTTPException as http_exc:
        # 记录解析/索引阶段的错误
        print(f"后台处理 {filename} 时发生 HTTP 错误: {http_exc.status_code} - {http_exc.detail}")
        # 可以考虑添加到失败队列或进行通知
    except Exception as e:
        print(f"后台处理 {filename} 时发生意外错误: {e}")
        # 可以考虑添加到失败队列或进行通知

@router.post(
    "/upload",
    response_model=UploadResponse,
    summary="上传文档以进行处理和索引",
    description="接受 PDF, DOCX, TXT 或 MD 文件, 解析它们, 分割成块, 生成嵌入, 并将它们存储在向量数据库中。",
    status_code=status.HTTP_202_ACCEPTED, # 表示处理已开始
    responses={
        400: {"model": GenericErrorResponse, "description": "错误的请求 (例如, 无效的文件类型, 空文件)"},
        500: {"model": GenericErrorResponse, "description": "处理期间发生内部服务器错误"},
        503: {"model": GenericErrorResponse, "description": "向量数据库服务不可用"}
    }
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="文档文件 (PDF, DOCX, TXT, MD)"),
    vector_store: Milvus = Depends(get_cached_vector_store) # 注入向量存储依赖
):
    """
    处理文档上传, 启动后台处理。
    使用 FastAPI 的 BackgroundTasks 异步执行解析和索引。
    """
    # 添加处理任务以在后台运行
    # 直接传递文件对象 - BackgroundTasks 会正确处理 awaitable
    # 确保在任务开始前解析 vector_store 依赖项
    background_tasks.add_task(process_and_index_file, file, vector_store)

    # 立即向客户端返回响应
    return UploadResponse(
        filename=file.filename,
        message="文件上传已接受并排队等待处理。"
    )

# 如果需要, 可以考虑添加一个端点来检查处理状态 