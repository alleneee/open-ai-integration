# 企业级 RAG API

本项目提供了一个企业级检索增强生成 (RAG) 系统的 API, 基于以下技术栈构建:

* **API 框架:** FastAPI
* **流程编排:** Langchain (~0.3)
* **向量数据库:** Milvus
* **LLM 支持:** 可插拔 (OpenAI, DeepSeek, Qwen - 带有占位符)
* **文档解析:** 支持 PDF, DOCX, TXT, MD
* **后台任务:** Celery
* **会话存储:** Redis
* **用户认证:** JWT (JSON Web Token)
* **数据库迁移:** Alembic

## 项目结构

```bash
├── .env                  # 环境变量 (API 密钥, Milvus URI 等) - 不要提交到 Git
├── .gitignore
├── pyproject.toml        # Poetry 依赖管理
├── README.md
├── alembic.ini           # Alembic 配置文件
├── migrations/           # 数据库迁移脚本
└── app
    ├── __init__.py
    ├── main.py           # FastAPI 应用初始化, 中间件
    ├── api/
    │   ├── api.py        # API 路由注册
    │   ├── deps.py       # API 依赖项 (如认证)
    │   ├── v1/
    │   │   ├── auth.py   # 认证相关路由
    │   │   └── endpoints/
    │   │       ├── upload.py      # 文档上传和处理的端点
    │   │       ├── query.py       # RAG 查询的端点
    │   │       └── knowledge_bases.py # 知识库管理端点
    ├── core/
    │   ├── config.py     # 配置加载 (Pydantic BaseSettings)
    │   ├── security.py   # 安全相关功能 (如密码哈希, JWT)
    │   ├── limiter.py    # 速率限制功能
    │   ├── pagination.py # 分页功能
    │   └── dependencies.py  # 共享依赖项 (例如 get_vector_store)
    ├── models/
    │   ├── database.py   # 数据库连接和基础类
    │   ├── user.py       # 用户, 角色和权限模型
    │   ├── document.py   # 文档和段落模型
    │   └── knowledge_base.py # 知识库模型
    ├── schemas/
    │   ├── schemas.py    # API 请求/响应的 Pydantic 模型
    │   └── user.py       # 用户相关的Pydantic模型
    ├── services/
    │   ├── auth.py       # 认证服务
    │   ├── llm.py        # LLM 提供商交互逻辑
    │   ├── parser.py     # 文档解析逻辑
    │   ├── rag.py        # 核心 RAG 流水线逻辑
    │   ├── vector_store.py  # Milvus 交互逻辑
    │   ├── conversation.py  # 会话历史管理 (Redis)
    │   ├── document_chunker.py # 文档分块服务
    │   ├── document_processor.py # 文档处理服务
    │   └── knowledge_base.py # 知识库服务
    └── task/
        ├── celery_app.py  # Celery 配置
        └── tasks.py       # 异步任务定义
```

## 安装与设置

1. **环境要求:**
    * Python 3.10+
    * Poetry (`pip install poetry`)
    * 运行中的 Milvus 实例 (推荐 v2.3+)
    * 运行中的 Redis 服务器 (用于 Celery 任务队列和会话存储)
    * MySQL 数据库 (用于用户管理和文档元数据存储)
    * 您选择的 LLM 提供商的 API 密钥 (OpenAI, DeepSeek, Qwen/Dashscope)

2. **克隆仓库:**

    ```bash
    git clone <your-repo-url>
    cd <your-repo-directory>
    ```

3. **创建并配置环境文件:**
    * 复制 `.env.example` 文件 (如果存在) 或根据之前生成的 `.env` 创建: `cp .env.example .env`
    * 编辑 `.env` 文件, 填入您的 Milvus 连接信息, Redis URL (包括 Celery 和会话), MySQL 数据库连接信息, LLM API 密钥, JWT 密钥, 以及期望的模型名称。

4. **安装依赖:**

    ```bash
    poetry install
    ```

5. **运行数据库迁移:**

    ```bash
    # 检查迁移状态
    alembic current
    
    # 应用所有迁移
    alembic upgrade head
    ```

## 运行应用程序

1. **启动 FastAPI 应用:**

    ```bash
    poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ```

    * `--reload` 选项启用自动重新加载, 适用于开发环境。生产环境中请移除此选项。
    * API 将在 `http://localhost:8000` (或您配置的主机和端口) 可用。
    * 交互式 API 文档 (Swagger UI) 地址: `http://localhost:8000/docs`。
    * 备选 API 文档 (ReDoc) 地址: `http://localhost:8000/redoc`。

2. **启动 Celery 工作进程:**

    ```bash
    poetry run celery -A app.task.celery_app worker --loglevel=info
    ```

## API 端点

### 认证相关

* **`POST /api/v1/auth/register`**: 用户注册。需要提供用户名、邮箱和密码。
* **`POST /api/v1/auth/login`**: 用户登录。登录成功后返回访问令牌和刷新令牌。
* **`POST /api/v1/auth/token/refresh`**: 刷新访问令牌。
* **`GET /api/v1/auth/me`**: 获取当前登录用户信息。
* **`GET /api/v1/auth/users`**: 获取用户列表 (需要管理员权限)。
* **`GET /api/v1/auth/users/{user_id}`**: 获取特定用户信息 (需要管理员权限或为用户本人)。

### RAG 相关

* **`POST /api/v1/documents/upload`**: 上传文档 (PDF, DOCX, TXT, MD)。返回 `202 Accepted` 并在后台处理文件。需要认证。
* **`POST /api/v1/rag/query`**: 向 RAG 系统发送查询。需要在 JSON 请求体中包含 `session_id` (用于跟踪对话历史) 和 `query`。例如: `{"session_id": "user123_abc", "query": "你的问题是什么?", "top_k": 5}`。返回答案和来源文档。需要认证。
* **`GET /api/v1/knowledge-bases`**: 获取所有知识库列表。需要认证。
* **`POST /api/v1/knowledge-bases`**: 创建新的知识库。需要认证。
* **`GET /api/v1/knowledge-bases/{kb_id}`**: 获取特定知识库的详细信息。需要认证。
* **`DELETE /api/v1/knowledge-bases/{kb_id}`**: 删除指定的知识库。需要管理员权限。
* **`PUT /api/v1/knowledge-bases/{kb_id}/chunking-config`**: 更新知识库的分块配置。需要管理员权限。
* **`GET /api/v1/knowledge-bases/{kb_id}/chunking-strategies`**: 获取所有可用的分块策略。需要认证。
* **`GET /api/v1/knowledge-bases/{kb_id}/chunking-status`**: 获取知识库文档分块状态。需要认证。
* **`POST /api/v1/knowledge-bases/{kb_id}/rechunk-all`**: 重新处理知识库中的所有文档。需要管理员权限。
* **`POST /api/v1/knowledge-bases/{kb_id}/rebuild-index`**: 重建知识库的向量索引。需要管理员权限。
* **`DELETE /api/v1/knowledge-bases/chunking-cache`**: 清除分块缓存。需要管理员权限。
* **`GET /`**: 根路径端点 (通常仅用于确认服务运行)。
* **`GET /health`**: 健康检查端点。

## 文档分块管理系统

本系统实现了高级文档分块管理功能，支持多种分块策略和性能优化：

### 分块策略

系统支持多种文档分块策略，可根据不同文档类型和需求选择最合适的策略：

* **段落分块 (paragraph)**: 使用段落作为分隔单位，以`\n\n`等作为主要分隔符
* **Token分块 (token)**: 按Token数量进行分块，适合大多数文本
* **字符分块 (character)**: 按字符数进行简单分块
* **Markdown分块 (markdown)**: 针对Markdown文档优化的分块方式
* **句子分块 (sentence)**: 按句子进行分块，使用标点符号作为分隔
* **换行分块 (newline)**: 使用换行符`\n`作为主要分隔符
* **双换行分块 (double_newline)**: 仅使用双换行符`\n\n`作为分隔符
* **中文分块 (chinese)**: 针对中文文档优化，使用中文标点符号作为分隔符
* **代码分块 (code)**: 针对程序代码优化的分块方式
* **自定义分块 (custom)**: 使用自定义分隔符列表进行分块

### 自定义分隔符

系统支持自定义分隔符，允许用户根据特定文档需求定义精确的分块规则：

* 可通过API指定自定义分隔符列表
* 分隔符按优先级顺序应用
* 支持多种字符序列作为分隔符，如`\n\n`、`\t`、特殊标点等

### 缓存机制

为提高性能，系统实现了多层缓存机制：

* **分块结果缓存**: 基于文档哈希值缓存分块结果，避免重复处理
* **向量缓存**: 缓存文档向量，加速查询
* **分块配置缓存**: 缓存知识库分块配置，减少数据库访问

### 批量处理与异步执行

系统支持大规模文档批量处理：

* 使用后台任务处理长时间运行的分块操作
* 批量重新处理文档，支持增量更新
* 索引重建功能，允许在更改配置后快速更新向量存储

### 性能优化

* 自适应线程池：根据服务器资源调整处理线程
* 批处理暂停：防止服务器过载
* 事务管理：确保数据一致性
* 错误恢复：支持从错误中恢复并继续处理

### 配置与监控

* 全局配置参数：可在`app/core/config.py`中设置默认分块参数
* 分块状态监控：实时跟踪文档处理进度
* 错误日志记录：详细记录处理过程中的错误信息

## 使用示例

### 更新知识库分块配置

```bash
curl -X PUT "http://localhost:8000/api/v1/knowledge-bases/{kb_id}/chunking-config" \
  -H "Authorization: Bearer {your_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "chunk_size": 1000,
    "chunk_overlap": 200,
    "chunking_strategy": "paragraph",
    "rechunk_documents": true,
    "custom_separators": ["\\n\\n", "\\n", ". "]
  }'
```

### 获取可用分块策略

```bash
curl -X GET "http://localhost:8000/api/v1/knowledge-bases/{kb_id}/chunking-strategies" \
  -H "Authorization: Bearer {your_token}"
```

### 重建知识库索引

```bash
curl -X POST "http://localhost:8000/api/v1/knowledge-bases/{kb_id}/rebuild-index" \
  -H "Authorization: Bearer {your_token}"
```

## 重要说明

* Langchain 版本: 此代码概念上基于 Langchain 0.3，但可能使用了更新的 Langchain 组件。对于新项目，请参考最新的 Langchain 文档。
* LLM 集成: 为 DeepSeek 和 Qwen 提供了占位符。您需要在 `app/services/llm.py` 中实现实际的 API 调用。
* 会话管理: 对话历史现在通过 Redis 进行管理。客户端在调用 `/api/v1/rag/query` 时需要提供唯一的 `session_id`。
* 错误处理: 包含了基本的错误处理。请为生产用途进行增强。
* 安全性:
  * 生产环境中请更换 `SECRET_KEY` 为安全的随机值。
  * 考虑实现 HTTPS 和额外的安全措施。
  * 默认使用 bcrypt 算法进行密码哈希。
* 可扩展性: 考虑部署策略 (Docker, Kubernetes), 异步任务扩展, 以及数据库连接池调优。
* Milvus Schema/Index: Langchain Milvus 包装器通常会处理集合创建。对于生产环境, 建议显式定义 Milvus schema 和索引。
* 数据库迁移: 使用 Alembic 管理数据库模式变更，确保数据库结构与代码同步。
