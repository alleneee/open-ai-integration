import os
import shutil
import uuid
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Form
from typing import List, Optional

# Import the Celery task we defined
from app.tasks import process_document_batch
# Import settings to get the temp directory
from app.config import settings
# Import a response model for task submission
from pydantic import BaseModel, Field # Ensure Field is imported

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1", # Add prefix for versioning
    tags=["Document Upload"]
)

# Define a response model for task submission acknowledgment
class AsyncTaskResponse(BaseModel):
    message: str = Field(..., description="指示任务已接收的消息")
    task_id: str = Field(..., description="后台处理任务的唯一 ID")
    filenames: List[str] = Field(..., description="已接收并安排处理的文件名列表")
    collection_name: Optional[str] = Field(None, description="文件将被添加到的目标知识库名称")

@router.post(
    "/upload",
    response_model=AsyncTaskResponse,
    status_code=status.HTTP_202_ACCEPTED, # Return 202 Accepted for async tasks
    summary="上传文档进行后台处理 (Upload documents for background processing)",
    description="上传一个或多个文档文件。文件将被保存并在后台进行解析和索引。返回一个任务 ID 用于追踪。",
)
async def upload_files(
    files: List[UploadFile] = File(..., description="要上传的文档文件列表 (PDF, DOCX, MD)"),
    collection_name: Optional[str] = Form(None, description="目标知识库名称 (如果省略则使用默认)")
):
    """
    接收上传的文件，保存到临时位置，并将处理任务发送到 Celery 队列。
    """
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="没有提供文件。")

    temp_file_paths = []
    original_filenames = []
    task_id = None

    try:
        # Ensure the temporary directory exists
        try:
             os.makedirs(settings.upload_temp_dir, exist_ok=True)
        except OSError as e:
             logger.error(f"无法创建或访问临时上传目录: {settings.upload_temp_dir} - {e}")
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器无法存储上传文件。")

        for file in files:
            if not file.filename:
                logger.warning("收到一个没有文件名的上传文件，已跳过。")
                continue

            # Basic check for allowed extensions
            allowed_extensions = {".pdf", ".docx", ".md"}
            _, ext = os.path.splitext(file.filename)
            if ext.lower() not in allowed_extensions:
                logger.warning(f"收到不允许的文件类型 '{ext}' (来自文件 '{file.filename}')，已跳过。")
                continue # Skip disallowed file types

            original_filenames.append(file.filename)
            # Create a unique temporary filename
            unique_suffix = uuid.uuid4().hex
            safe_filename = "".join(c for c in file.filename if c.isalnum() or c in ('_', '.', '-')).strip()
            if not safe_filename: safe_filename = "uploaded_file"
            temp_filename = f"{unique_suffix}_{safe_filename}{ext}"
            temp_file_path = os.path.join(settings.upload_temp_dir, temp_filename)

            logger.info(f"正在保存上传的文件 '{file.filename}' 到临时路径: {temp_file_path}")

            try:
                # Save the uploaded file content
                with open(temp_file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                temp_file_paths.append(temp_file_path)
                logger.debug(f"文件 '{file.filename}' 已保存到 '{temp_file_path}'")
            except Exception as e:
                 logger.error(f"保存文件 '{file.filename}' 到 '{temp_file_path}' 时出错: {e}")
                 raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"无法保存文件 {file.filename}: {e}")
            finally:
                 await file.close() # Use await for async file close

        # If no valid files were processed
        if not temp_file_paths:
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="未提供有效或允许的文件类型。允许的类型: PDF, DOCX, MD。")

        # Send the batch processing task to Celery
        target_collection = collection_name or settings.milvus_collection_name
        logger.info(f"准备将处理任务发送到 Celery: {len(temp_file_paths)} 个文件, 目标 Collection: {target_collection}")
        try:
            task = process_document_batch.apply_async(
                args=[temp_file_paths, original_filenames, target_collection],
                queue='document_processing',
            )
            task_id = task.id
            logger.info(f"文档处理任务已成功入队，Task ID: {task_id}", extra={"task_id": task_id, "filenames": original_filenames, "collection": target_collection})
        except Exception as e:
             logger.error(f"发送任务到 Celery 失败: {e}")
             # Clean up the temp files if task couldn't be queued
             for path in temp_file_paths:
                 if os.path.exists(path):
                     try: os.remove(path)
                     except OSError: logger.error(f"无法清理临时文件 {path} 在 Celery 发送失败后。")
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"无法安排文件处理任务: {e}")

        return AsyncTaskResponse(
            message="文件已接收并正在后台处理。",
            task_id=task_id,
            filenames=original_filenames,
            collection_name=target_collection
        )

    except HTTPException as http_exc:
         # Clean up temp files if created before the error
         for path in temp_file_paths:
              if os.path.exists(path):
                  try: os.remove(path)
                  except OSError: pass
         raise http_exc
    except Exception as e:
        logger.exception(f"处理上传请求时发生意外错误: {e}")
        # Clean up temp files
        for path in temp_file_paths:
             if os.path.exists(path):
                 try: os.remove(path)
                 except OSError: pass
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"处理上传时发生内部错误。")

# --- Optional: Add an endpoint to check task status ---
# from celery.result import AsyncResult
# from app.celery_app import celery_app # Import celery instance
# from pydantic import BaseModel
# from typing import Any # Import Any for result type

# class TaskStatusResponse(BaseModel):
#     task_id: str
#     status: str
#     result: Optional[Any] = None
#     error_info: Optional[str] = None

# @router.get("/tasks/{task_id}/status", response_model=TaskStatusResponse, summary="获取后台任务状态 (Get background task status)")
# async def get_task_status(task_id: str):
#     """根据任务 ID 检查后台处理任务的状态和结果。"""
#     try:
#         task_result = AsyncResult(task_id, app=celery_app)
#         response = {
#             "task_id": task_id,
#             "status": task_result.status, # PENDING, STARTED, SUCCESS, FAILURE, RETRY, REVOKED
#             "result": task_result.result if task_result.ready() else None,
#             "error_info": None,
#         }
#         if task_result.failed():
#             if isinstance(task_result.info, Exception):
#                  response["error_info"] = f"{type(task_result.info).__name__}: {str(task_result.info)}"
#             else:
#                  response["error_info"] = str(task_result.info)
#         elif task_result.status == 'PENDING':
#              pass
#         logger.debug(f"查询任务状态 Task ID: {task_id}, Status: {task_result.status}")
#         return response
#     except Exception as e:
#          logger.error(f"查询任务状态 Task ID: {task_id} 时出错: {e}")
#          raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"无法获取任务状态: {e}") 