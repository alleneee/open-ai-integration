# app/task/tasks.py

import os
import logging
import shutil
import traceback
from typing import List, Optional

# Updated import paths
from app.task.celery_app import celery_app  # 使用正确的导入路径

logger = logging.getLogger(__name__) # 将 logger 定义移到 try-except 之前

# 视情况模拟这些导入
try:
    from app.services.parser import parse_and_split_document # 修正导入的函数名
    from app.services.vector_store import add_documents # Services path unchanged
    HAS_SERVICES = True
except ImportError as e:
    HAS_SERVICES = False
    # 添加详细的 traceback 日志
    logger.error("导入服务模块失败! 将使用模拟函数。错误详情:", exc_info=True)
    # logging.warning("无法导入服务模块，使用模拟函数") # 旧的警告
    
    # 更新模拟函数名以匹配实际函数（虽然可能不会被调用了）
    def parse_and_split_document(*args, **kwargs):
        logging.info("[模拟] 解析文档")
        return [], []
        
    def add_documents(*args, **kwargs):
        logging.info("[模拟] 添加文档到向量库")
        return True

# Import settings if needed directly in task (currently not needed)
# from app.core.config import settings

# Define the task
@celery_app.task(
    bind=True, # Allows access to task instance via self
    name="app.tasks.process_document_batch", # Explicit name is good practice
    queue='document_processing', # Route this task to the specific queue
    # Optional: Add retry logic
    autoretry_for=(Exception,), # Retry for any exception (be cautious with this)
    retry_kwargs={'max_retries': 3, 'countdown': 15} # Example: 3 retries, 15s delay
)
def process_document_batch(
    self, # 'bind=True' provides access to the task instance
    temp_file_paths: List[str],
    original_filenames: List[str],
    collection_name: Optional[str] = None
):
    """
    Celery task to parse a batch of documents from temporary paths and add them to the vector store.

    Args:
        temp_file_paths: List of paths to the temporarily stored uploaded files.
        original_filenames: List of original filenames corresponding to the temp paths.
        collection_name: The target Milvus collection name.
    """
    task_id = self.request.id
    logger.info(f"[Task ID: {task_id}] 开始处理文档批次: {original_filenames}, 目标 Collection: {collection_name}")

    all_docs = []
    errors = []
    processed_files_count = 0

    # 1. Parse all documents in the batch
    for i, temp_path in enumerate(temp_file_paths):
        original_filename = original_filenames[i] if i < len(original_filenames) else "unknown"
        logger.info(f"[Task ID: {task_id}] 正在解析文档: {original_filename} (路径: {temp_path})")
        try:
            parsed_docs = parse_and_split_document([temp_path])
            if not parsed_docs:
                logger.warning(f"[Task ID: {task_id}] 文档 '{original_filename}' 解析后未产生任何块。")
            else:
                for doc in parsed_docs:
                    doc.metadata = {'source': original_filename, **(doc.metadata or {})}
                all_docs.extend(parsed_docs)
                logger.info(f"[Task ID: {task_id}] 文档 '{original_filename}' 解析成功，生成 {len(parsed_docs)} 个块。")
            processed_files_count += 1
        except Exception as e:
            error_msg = f"解析文档 '{original_filename}' (路径: {temp_path}) 时失败: {e}"
            logger.exception(f"[Task ID: {task_id}] {error_msg}")
            errors.append({"filename": original_filename, "error": str(e)})
        finally:
            # 2. Clean up the temporary file
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    logger.debug(f"[Task ID: {task_id}] 已删除临时文件: {temp_path}")
            except OSError as e:
                # Log error but don't let cleanup failure stop the task
                logger.error(f"[Task ID: {task_id}] 删除临时文件 {temp_path} 失败: {e}")

    # 3. Add parsed documents to vector store (if any were successful)
    if all_docs:
        try:
            logger.info(f"[Task ID: {task_id}] 正在将 {len(all_docs)} 个文档块添加到 Collection '{collection_name}'...")
            # Ensure the target collection exists before adding
            # add_documents itself calls get_vector_store_instance which handles creation
            add_documents(docs=all_docs, collection_name=collection_name)
            logger.info(f"[Task ID: {task_id}] 成功将 {len(all_docs)} 个文档块添加到 Collection '{collection_name}'。")
        except Exception as e:
            # This is a critical error for the batch, likely warrants retry/failure
            error_msg = f"将文档块添加到 Collection '{collection_name}' 时失败: {e}"
            logger.exception(f"[Task ID: {task_id}] {error_msg}")
            errors.append({"filename": "<batch_add>", "error": str(e)})
            # Re-raise to trigger Celery retry mechanism if configured
            raise self.retry(exc=e, countdown=15, max_retries=3) # Example explicit retry
            # Or just raise e if autoretry_for is set
            # raise e
    elif processed_files_count > 0 and not errors:
         logger.info(f"[Task ID: {task_id}] 所有文件处理完毕，但未生成任何可添加的文档块。")
    elif not all_docs and not errors and processed_files_count == 0:
         logger.warning(f"[Task ID: {task_id}] 未处理任何文件或生成任何块 (可能是空输入?)。")


    # 4. Return results
    if errors:
        final_status = "Completed with errors"
        logger.error(f"[Task ID: {task_id}] 文档批处理完成，但出现错误: {len(errors)} 个错误。", extra={"errors": errors})
    else:
        final_status = "Completed successfully"
        logger.info(f"[Task ID: {task_id}] 文档批处理 ({processed_files_count} 个文件) 成功完成。")

    return {
        "task_id": str(task_id),
        "status": final_status,
        "processed_files_count": processed_files_count,
        "total_chunks_generated": len(all_docs),
        "target_collection": collection_name,
        "errors": errors
    }

# --- Optional: Add other tasks here --- 