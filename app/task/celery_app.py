"""
Celery配置 - 使用独立配置文件
"""
import os
import logging
from celery import Celery

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建Celery实例
app = Celery('rag_app')

# 直接从配置模块加载配置，跳过环境变量
logger.info("从celery_config.py加载配置...")
app.config_from_object('app.task.celery_config')

# 测试Redis连接
try:
    # 通过获取celery connection测试连接
    with app.connection_or_acquire() as conn:
        logger.info(f"Celery成功连接到broker: {app.conf.broker_url}")
        conn.ensure_connection(max_retries=3)
        logger.info("连接测试成功!")
except Exception as e:
    logger.error(f"连接测试失败: {e}")

# 注册任务
app.autodiscover_tasks(['app.task'])

# 供外部导入
celery_app = app

# 简单测试任务
@app.task(bind=True, name='app.task.celery_app.test_task')
def test_task(self):
    """测试任务"""
    logger.info(f"任务ID: {self.request.id} 正在执行")
    return {"status": "success", "message": "测试任务已完成"}