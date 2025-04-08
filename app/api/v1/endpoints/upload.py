# app/api/v1/endpoints/upload.py

import os
import shutil
import uuid
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Form
from typing import List, Optional

# Updated import paths
from app.task.tasks import process_document_batch
from app.core.config import settings
from app.schemas.schemas import AsyncTaskResponse # Updated schema path

logger = logging.getLogger(__name__)

# REMOVED prefix from router definition
router = APIRouter()

# AsyncTaskResponse definition is now in schemas.py

@router.post(
    "", # 修正路径：移除冗余的 /upload
    response_model=AsyncTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="上传文档进行后台处理 (Upload documents for background processing)",
    description="上传一个或多个文档文件。文件将被保存并在后台进行解析和索引。返回一个任务 ID 用于追踪。",
)
async def upload_files(
    files: List[UploadFile] = File(..., description="要上传的文档文件列表 (PDF, DOCX, MD)"),
    collection_name: Optional[str] = Form(None, description="目标知识库名称 (如果省略则使用默认)")
):
    # ... (Implementation remains the same as the last version of app/routers/upload.py) ...
    if not files: 
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="没有提供文件。")
    
    temp_file_paths = []
    original_filenames = []
    task_id = None
    
    try:
        try: 
            os.makedirs(settings.upload_temp_dir, exist_ok=True)
        except OSError as e: 
            logger.error(f"无法创建或访问临时上传目录: {settings.upload_temp_dir} - {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="服务器无法存储上传文件。")
        
        for file in files:
            if not file.filename: 
                logger.warning("收到一个没有文件名的上传文件，已跳过。")
                continue
            
            allowed_extensions = {".pdf", ".docx", ".md"}
            _, ext = os.path.splitext(file.filename)
            
            if ext.lower() not in allowed_extensions: 
                logger.warning(f"收到不允许的文件类型 '{ext}' (来自文件 '{file.filename}')，已跳过。")
                continue
            
            original_filenames.append(file.filename)
            
            # Create a unique temporary filename suffix
            unique_suffix = uuid.uuid4().hex
            
            # Get original filename and extension
            raw_filename = file.filename or ""
            base_name, current_ext = os.path.splitext(raw_filename)
            
            # Sanitize the base name (remove extension first)
            safe_basename = "".join(c for c in base_name if c.isalnum() or c in ('_', '-')).strip() # Only sanitize the name part
            
            if not safe_basename:
                safe_basename = "uploaded_file"
                
            # Construct final temp filename safely
            # Ensure the extension starts with a dot if it's not empty
            safe_ext = ('.' + current_ext.lstrip('.')) if current_ext else ''
            temp_filename = f"{unique_suffix}_{safe_basename}{safe_ext}" 
            temp_file_path = os.path.join(settings.upload_temp_dir, temp_filename)

            logger.info(f"正在保存上传的文件 '{file.filename}' 到临时路径: {temp_file_path}")
            
            content_read = None # Initialize variable
            try:
                # 1. Read entire content into memory
                logger.debug(f"开始读取 '{file.filename}' 的完整内容...")
                content_read = await file.read()
                content_length = len(content_read) if content_read else 0
                logger.debug(f"'{file.filename}' 读取完成，大小: {content_length} 字节。")

                if not content_read:
                     logger.warning(f"文件 '{file.filename}' 读取后内容为空，跳过保存。")
                     continue # Skip to next file if content is empty

                # 2. Write content from memory to file
                logger.debug(f"开始将内存内容写入到: {temp_file_path}")
                with open(temp_file_path, "wb") as buffer:
                    buffer.write(content_read)
                logger.debug(f"内存内容已写入到: {temp_file_path}")
                
                # 3. Verify file size on disk
                if os.path.exists(temp_file_path):
                    disk_file_size = os.path.getsize(temp_file_path)
                    logger.debug(f"磁盘文件大小验证: {disk_file_size} 字节。")
                    if disk_file_size != content_length:
                         logger.error(f"严重错误：写入后的磁盘文件大小 ({disk_file_size}) 与读取的内存大小 ({content_length}) 不匹配！ 文件: {temp_file_path}")
                         # Optionally raise an error here or just log
                else:
                    logger.error(f"严重错误：文件写入后在磁盘上未找到！ 文件: {temp_file_path}")
                    # Optionally raise error

                temp_file_paths.append(temp_file_path)
            except Exception as e:
                logger.error(f"保存文件 '{file.filename}' 到 '{temp_file_path}' 时出错: {e}")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                                  detail=f"无法保存文件 {file.filename}: {e}")
        
        if not temp_file_paths: 
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                              detail="未提供有效或允许的文件类型。允许的类型: PDF, DOCX, MD。")
        
        target_collection = collection_name or settings.milvus_collection_name
        logger.info(f"准备将处理任务发送到 Celery: {len(temp_file_paths)} 个文件, 目标 Collection: {target_collection}")
        
        try:
            task = process_document_batch.apply_async(
                args=[temp_file_paths, original_filenames, target_collection], 
                queue='document_processing'
            )
            task_id = task.id
            logger.info(f"文档处理任务已成功入队，Task ID: {task_id}", 
                      extra={"task_id": task_id, "filenames": original_filenames, "collection": target_collection})
        except Exception as e:
            logger.error(f"发送任务到 Celery 失败: {e}")
            # Cleanup on failure to queue
            for path in temp_file_paths:
                if os.path.exists(path):
                    try: 
                        os.remove(path)
                    except OSError:
                        logger.error(f"无法清理临时文件 {path} 在 Celery 发送失败后。")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                              detail=f"无法安排文件处理任务: {e}")
        
        return AsyncTaskResponse(
            message="文件已接收并正在后台处理。", 
            task_id=task_id, 
            filenames=original_filenames, 
            collection_name=target_collection
        )
    except HTTPException as http_exc:
        # Cleanup on known HTTP errors during processing
        for path in temp_file_paths:
            if os.path.exists(path):
                try: 
                    os.remove(path)
                except OSError:
                    pass
        raise http_exc
    except Exception as e:
        logger.exception(f"处理上传请求时发生意外错误: {e}")
        # Cleanup on general errors
        for path in temp_file_paths:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                          detail=f"处理上传时发生内部错误。")

# Optional Task Status Endpoint (Keep commented out or move/enable as needed)
# from celery.result import AsyncResult
# from app.celery_app import celery_app
# from pydantic import BaseModel
# from typing import Any
# ... (TaskStatusResponse definition)
# @router.get("/tasks/{task_id}/status", ...)
# async def get_task_status(task_id: str): ... 