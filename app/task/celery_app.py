# app/task/celery_app.py

import os
import logging

# 尝试导入Celery，如果未安装则创建模拟对象
try:
    from celery import Celery
    from kombu import Queue
    HAS_CELERY = True
except ImportError:
    HAS_CELERY = False
    
    # 创建模拟对象以通过基本导入测试
    class MockTask:
        def __init__(self, *args, **kwargs):
            self.id = "mock-task-id"
            
    class MockCelery:
        def __init__(self, name, **kwargs):
            self.name = name
            self.conf = type('obj', (object,), {'update': lambda **kw: None})
            
        def autodiscover_tasks(self, packages):
            return self
            
        def task(self, *args, **kwargs):
            def decorator(func):
                def wrapped(*args, **kwargs):
                    return MockTask()
                wrapped.apply_async = lambda *a, **kw: MockTask()
                return wrapped
            return decorator

    class MockQueue:
        def __init__(self, name, **kwargs):
            self.name = name
    
    Celery = MockCelery
    Queue = MockQueue
    
    logging.warning("Celery未安装，使用模拟对象进行基本导入测试")

from app.core.config import settings

logger = logging.getLogger(__name__)

# 确保上传目录存在
try:
    os.makedirs(settings.upload_temp_dir, exist_ok=True)
    logger.info(f"临时上传目录: {settings.upload_temp_dir}")
except Exception as e:
    logger.error(f"无法创建临时上传目录 {settings.upload_temp_dir}: {e}")

# 创建Celery实例
celery_app = Celery(
    "rag_app",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend
)

# 仅在实际的Celery可用时配置
if HAS_CELERY:
    celery_app.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_queues=(
            Queue('default'),
            Queue('document_processing'),
        ),
        task_default_queue='default',
        task_default_exchange='default',
        task_default_routing_key='default',
    )
    logger.info(f"Celery应用已配置: broker={settings.celery_broker_url}")
else:
    logger.warning("使用Celery模拟对象，无法配置实际任务队列")

# No need to call autodiscover_tasks() here if 'include' is used.
# The worker will automatically discover tasks in the modules listed in 'include'. 