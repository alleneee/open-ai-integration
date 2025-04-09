"""
Alembic环境配置
处理数据库模型与数据库迁移之间的集成
"""
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# 确保可以导入app包
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# 从应用程序导入配置和模型
from app.core.config import settings
from app.models.database import Base
from app.models.document import Document, Segment  # 文档相关模型
from app.models.user import User, Role, Permission, user_role  # 用户认证相关模型
from app.models.knowledge_base import KnowledgeBaseDB, knowledge_base_document  # 知识库相关模型

# 这是Alembic配置对象
config = context.config

# 设置日志
fileConfig(config.config_file_name)

# 从配置中获取元数据
target_metadata = Base.metadata

# 覆盖配置中的连接字符串
config.set_main_option("sqlalchemy.url", settings.DATABASE_URI)

def run_migrations_offline():
    """以"离线"模式运行迁移

    这不需要实际的数据库连接，适用于生成迁移脚本
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """以"在线"模式运行迁移

    在这种模式下，在执行迁移脚本时会维护连接
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            compare_type=True,  # 比较列类型
            compare_server_default=True,  # 比较默认值
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
