# app/celery_app.py

from celery import Celery
from kombu import Queue

from app.core.config import settings
import logging
import os

logger = logging.getLogger(__name__)

# Ensure temporary upload directory exists
try:
    os.makedirs(settings.upload_temp_dir, exist_ok=True)
    logger.info(f"确保上传临时目录存在: {settings.upload_temp_dir}")
except OSError as e:
    logger.error(f"创建上传临时目录失败 '{settings.upload_temp_dir}': {e}")
    # Depending on severity, you might want to raise an exception here

# Initialize Celery
celery_app = Celery(
    "worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks"] # Tells Celery where to find task definitions
)

# Optional Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC', # Or your preferred timezone
    enable_utc=True,
    # Define specific queues for better task management
    task_queues=(
        Queue('default'),
        Queue('document_processing'),
    ),
    task_default_queue='default',
    task_default_exchange='default',
    task_default_routing_key='default',
    # Example reliability settings (consider based on your needs)
    # task_acks_late=True,
    # worker_prefetch_multiplier=1,
    # task_reject_on_worker_lost=True,
)

logger.info(f"Celery 应用已配置: Broker='{settings.celery_broker_url}', Backend='{settings.celery_result_backend}'")

# No need to call autodiscover_tasks() here if 'include' is used.
# The worker will automatically discover tasks in the modules listed in 'include'. 