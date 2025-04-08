# 企业级 RAG API

本项目提供了一个企业级检索增强生成 (RAG) 系统的 API, 基于以下技术栈构建:

* **API 框架:** FastAPI
* **流程编排:** Langchain (~0.3)
* **向量数据库:** Milvus
* **LLM 支持:** 可插拔 (OpenAI, DeepSeek, Qwen - 带有占位符)
* **文档解析:** 支持 PDF, DOCX, TXT, MD
* **后台任务:** Celery
* **会话存储:** Redis

## 项目结构

```
├── .env                  # 环境变量 (API 密钥, Milvus URI 等) - 不要提交到 Git
├── .gitignore
├── pyproject.toml        # Poetry 依赖管理
├── README.md
└── app
    ├── __init__.py
    ├── main.py           # FastAPI 应用初始化, 中间件
    ├── api/
    │   └── v1/
    │       └── endpoints/
    │           ├── upload.py      # 文档上传和处理的端点
    │           ├── query.py       # RAG 查询的端点
    │           └── knowledgebase.py # 知识库管理端点
    ├── core/
    │   ├── config.py     # 配置加载 (Pydantic BaseSettings)
    │   └── dependencies.py  # 共享依赖项 (例如 get_vector_store)
    ├── schemas/
    │   └── schemas.py    # API 请求/响应的 Pydantic 模型
    ├── services/
    │   ├── llm.py        # LLM 提供商交互逻辑
    │   ├── parser.py     # 文档解析逻辑
    │   ├── rag.py        # 核心 RAG 流水线逻辑
    │   ├── vector_store.py  # Milvus 交互逻辑
    │   └── conversation.py # 会话历史管理 (Redis)
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
    * 您选择的 LLM 提供商的 API 密钥 (OpenAI, DeepSeek, Qwen/Dashscope)

2. **克隆仓库:**

    ```bash
    git clone <your-repo-url>
    cd <your-repo-directory>
    ```

3. **创建并配置环境文件:**
    * 复制 `.env.example` 文件 (如果存在) 或根据之前生成的 `.env` 创建: `cp .env.example .env`
    * 编辑 `.env` 文件, 填入您的 Milvus 连接信息, Redis URL (包括 Celery 和会话), LLM API 密钥, 以及期望的模型名称。

4. **安装依赖:**

    ```bash
    poetry install
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

* **`POST /api/v1/documents/upload`**: 上传文档 (PDF, DOCX, TXT, MD)。返回 `202 Accepted` 并在后台处理文件。
* **`POST /api/v1/rag/query`**: 向 RAG 系统发送查询。需要在 JSON 请求体中包含 `session_id` (用于跟踪对话历史) 和 `query`。例如: `{"session_id": "user123_abc", "query": "你的问题是什么?", "top_k": 5}`。返回答案和来源文档。
* **`GET /api/v1/knowledge-bases`**: 获取所有知识库列表。
* **`POST /api/v1/knowledge-bases`**: 创建新的知识库。
* **`GET /api/v1/knowledge-bases/{collection_name}`**: 获取特定知识库的详细信息。
* **`DELETE /api/v1/knowledge-bases/{collection_name}`**: 删除指定的知识库。
* **`GET /`**: 根路径端点 (通常仅用于确认服务运行)。
* **`GET /health`**: 健康检查端点。

## 重要说明

* **Langchain 版本:** 此代码概念上基于 Langchain 0.3，但可能使用了更新的 Langchain 组件。对于新项目，请参考最新的 Langchain 文档。
* **LLM 集成:** 为 DeepSeek 和 Qwen 提供了占位符。您需要在 `app/services/llm.py` 中实现实际的 API 调用。
* **会话管理:** 对话历史现在通过 Redis 进行管理。客户端在调用 `/api/v1/rag/query` 时需要提供唯一的 `session_id`。
* **错误处理:** 包含了基本的错误处理。请为生产用途进行增强。
* **安全性:** 为生产环境实现适当的身份验证、授权、输入验证加固和安全的配置管理。
* **可扩展性:** 考虑部署策略 (Docker, Kubernetes), 异步任务扩展, 以及数据库连接池调优。
* **Milvus Schema/Index:** Langchain Milvus 包装器通常会处理集合创建。对于生产环境, 建议显式定义 Milvus schema 和索引。
