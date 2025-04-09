"""
Celery专用配置文件
完全独立于环境变量，使用硬编码值
"""

# Redis连接设置
broker_url = 'redis://localhost:6379/0' 
result_backend = 'redis://localhost:6379/1'

# 任务设置
task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'

# 连接设置
broker_connection_retry = True
broker_connection_retry_on_startup = True
broker_connection_max_retries = 10

# 结果设置
task_ignore_result = False
task_track_started = True
