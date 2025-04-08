# app/task/celery_app.py
"""
Celery configuration - absolute minimal version
"""
import os
import logging
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 导入 Celery
from celery import Celery
from kombu import Queue

# # 确保上传目录存在 (Temporarily commented out for debugging)
# upload_dir = os.getenv('UPLOAD_TEMP_DIR', './tmp_uploads')
# try:
#     os.makedirs(upload_dir, exist_ok=True)
#     logger.info(f"创建上传目录: {upload_dir}")
# except Exception as e:
#     logger.error(f"无法创建上传目录 {upload_dir}: {e}")

# ******************************************
# 绝对明确的 Redis URL 设置 - 无环境变量依赖
# ******************************************
BROKER_URL = 'redis://localhost:6379/0'
BACKEND_URL = 'redis://localhost:6379/1'

logger.info(f"【硬编码】broker={BROKER_URL} backend={BACKEND_URL}")

# 创建 Celery 应用
celery_app = Celery('rag_app')

# *** 使用 update() 配置核心设置 ***
celery_app.conf.update(
    broker_url=BROKER_URL,
    result_backend=BACKEND_URL,
    broker_read_url=BROKER_URL,
    broker_transport_options={},
    result_backend_transport_options={},
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    task_default_queue='default',
    task_queues=(
        Queue('default'),
        Queue('document_processing'),
    )
)

# *** Forcefully set transport type ***
celery_app.conf.transport = 'redis'

# 强制打印配置以进行调试
logger.info(f"【最终配置】broker_url={celery_app.conf.broker_url}")
logger.info(f"【最终配置】result_backend={celery_app.conf.result_backend}")
logger.info(f"【最终配置】broker_read_url={celery_app.conf.broker_read_url}")
logger.info(f"【最终配置】transport={celery_app.conf.transport}")
logger.info(f"【最终配置】broker_connection_retry_on_startup={celery_app.conf.broker_connection_retry_on_startup}")

# 自动发现任务 (放在配置之后)
celery_app.autodiscover_tasks(['app.task']) # Re-enabled
logger.info("Celery任务自动发现已启用") # Re-enabled

# Minimal task defined directly in this file for testing isolation - REMOVING
# @celery_app.task
# def minimal_test_task(x, y):
#     logger.info(f"Minimal test task running: {x} + {y}")
#     return x + y
# 
# logger.info("Minimal test task defined.") 