# 企业级 RAG API

本项目提供了一个企业级检索增强生成 (RAG) 系统的 API, 基于以下技术栈构建:

* **API 框架:** FastAPI
* **流程编排:** Langchain (~0.0.354 / 针对 0.3 版本概念)
* **向量数据库:** Milvus
* **LLM 支持:** 可插拔 (OpenAI, DeepSeek, Qwen - 带有占位符)
* **文档解析:** 支持 PDF, DOCX, TXT, MD

## 项目结构

├── .env # 环境变量 (API 密钥, Milvus URI 等) - 不要提交到 Git
├── .gitignore
├── pyproject.toml # Poetry 依赖管理
├── README.md
└── app
├── init.py
├── main.py # FastAPI 应用初始化, 中间件
├── config.py # 配置加载 (Pydantic BaseSettings)
├── models/
│ └── schemas.py # API 请求/响应的 Pydantic 模型
├── routers/
│ ├── upload.py # 文档上传和处理的端点
│ └── query.py # RAG 查询的端点
├── services/
│ ├── llm.py # LLM 提供商交互逻辑
│ ├── parser.py # 文档解析逻辑
│ ├── rag.py # 核心 RAG 流水线逻辑
│ └── vector_store.py # Milvus 交互逻辑
└── core/
└── dependencies.py # 共享依赖项 (例如 get_vector_store)


## 安装与设置

1. **环境要求:**
    * Python 3.10+ (Langchain 0.3 可能与更新的 Python 版本存在兼容性问题)
    * Poetry (`pip install poetry`)
    * 运行中的 Milvus 实例 (推荐 v2.3+)
    * 您选择的 LLM 提供商的 API 密钥 (OpenAI, DeepSeek, Qwen/Dashscope)。

2. **克隆仓库:**

    ```bash
    git clone <your-repo-url>
    cd <your-repo-directory>
    ```

3. **创建并配置环境文件:**
    * 复制 `.env.example` 文件 (如果存在) 或根据之前生成的 `.env` 创建: `cp .env.example .env`
    * 编辑 `.env` 文件, 填入您的 Milvus 连接信息 (URI, TOKEN - 如果需要), LLM API 密钥, 以及期望的模型名称。

4. **安装依赖:**

    ```bash
    poetry install
    ```

    * **注意:** Langchain 0.3 及其依赖项可能较旧。如果遇到安装问题, 您可能需要调整 `pyproject.toml` 中的版本或解决冲突。
    * **注意:** 确保您已安装 `pymilvus` 所需的系统库 (如果需要)。

## 运行应用程序

使用 Uvicorn 运行 FastAPI 应用:

```bash
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

* `--reload` 选项启用自动重新加载, 适用于开发环境。生产环境中请移除此选项。
* API 将在 `http://localhost:8000` (或您配置的主机和端口) 可用。
* 交互式 API 文档 (Swagger UI) 地址: `http://localhost:8000/docs`。
* 备选 API 文档 (ReDoc) 地址: `http://localhost:8000/redoc`。

## API 端点

* **`POST /api/v1/documents/upload`**: 上传文档 (PDF, DOCX, TXT, MD)。返回 `202 Accepted` 并在后台处理文件。
* **`POST /api/v1/rag/query`**: 向 RAG 系统发送查询。需要一个 JSON 请求体, 例如 `{\"query\": \"你的问题是什么?\", \"top_k\": 5, \"llm_provider\": \"openai\"}`。返回答案和来源文档。
* **`GET /`**: 根路径端点 (通常仅用于确认服务运行)。
* **`GET /health`**: 健康检查端点。

## 重要说明

* **Langchain 版本:** 此代码针对 Langchain 0.3 的概念 (使用 `RetrievalQA`)。Langchain 已有显著发展; 对于新项目, 强烈建议升级。
* **LLM 集成:** 为 DeepSeek 和 Qwen 提供了占位符。您需要在 `app/services/llm.py` 中的占位符类 (`DeepSeekLLMPlaceholder`, `QwenLLMPlaceholder`) 中, 使用它们各自的 Python SDK 实现实际的 API 调用, 并遵循 Langchain 0.3 版本的 `BaseLLM` 接口规范。
* **错误处理:** 包含了基本的错误处理。请为生产用途进行增强 (例如, 详细日志记录, 更具体的异常类型)。
* **安全性:** 为生产环境实现适当的身份验证、授权、输入验证加固和安全的配置管理。
* **可扩展性:** 考虑部署策略 (例如, 使用 Docker 进行容器化, Kubernetes), 异步任务扩展 (对于高负载情况, 考虑使用 Celery 等代替 `BackgroundTasks`), 以及数据库连接池调优以提高可扩展性。
* **Milvus Schema/Index:** Langchain Milvus 包装器通常会处理集合创建。对于生产环境, 建议显式定义您的 Milvus schema 和索引参数以获得最佳性能和控制。



## 安装与设置

1.  **环境要求:**
    *   Python 3.10+ (Langchain 0.3 可能与更新的 Python 版本存在兼容性问题)
    *   Poetry (`pip install poetry`)
    *   运行中的 Milvus 实例 (推荐 v2.3+)
    *   您选择的 LLM 提供商的 API 密钥 (OpenAI, DeepSeek, Qwen/Dashscope)。

2.  **克隆仓库:**
    ```bash
    git clone <your-repo-url>
    cd <your-repo-directory>
    ```

3.  **创建并配置环境文件:**
    *   复制 `.env.example` 文件 (如果存在) 或根据之前生成的 `.env` 创建: `cp .env.example .env`
    *   编辑 `.env` 文件, 填入您的 Milvus 连接信息 (URI, TOKEN - 如果需要), LLM API 密钥, 以及期望的模型名称。

4.  **安装依赖:**
    ```bash
    poetry install
    ```
    *   **注意:** Langchain 0.3 及其依赖项可能较旧。如果遇到安装问题, 您可能需要调整 `pyproject.toml` 中的版本或解决冲突。
    *   **注意:** 确保您已安装 `pymilvus` 所需的系统库 (如果需要)。

## 运行应用程序

使用 Uvicorn 运行 FastAPI 应用:

```bash
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

*   `--reload` 选项启用自动重新加载, 适用于开发环境。生产环境中请移除此选项。
*   API 将在 `http://localhost:8000` (或您配置的主机和端口) 可用。
*   交互式 API 文档 (Swagger UI) 地址: `http://localhost:8000/docs`。
*   备选 API 文档 (ReDoc) 地址: `http://localhost:8000/redoc`。

## API 端点

*   **`POST /api/v1/documents/upload`**: 上传文档 (PDF, DOCX, TXT, MD)。返回 `202 Accepted` 并在后台处理文件。
*   **`POST /api/v1/rag/query`**: 向 RAG 系统发送查询。需要一个 JSON 请求体, 例如 `{\"query\": \"你的问题是什么?\", \"top_k\": 5, \"llm_provider\": \"openai\"}`。返回答案和来源文档。
*   **`GET /`**: 根路径端点 (通常仅用于确认服务运行)。
*   **`GET /health`**: 健康检查端点。

## 重要说明

*   **Langchain 版本:** 此代码针对 Langchain 0.3 的概念 (使用 `RetrievalQA`)。Langchain 已有显著发展; 对于新项目, 强烈建议升级。
*   **LLM 集成:** 为 DeepSeek 和 Qwen 提供了占位符。您需要在 `app/services/llm.py` 中的占位符类 (`DeepSeekLLMPlaceholder`, `QwenLLMPlaceholder`) 中, 使用它们各自的 Python SDK 实现实际的 API 调用, 并遵循 Langchain 0.3 版本的 `BaseLLM` 接口规范。
*   **错误处理:** 包含了基本的错误处理。请为生产用途进行增强 (例如, 详细日志记录, 更具体的异常类型)。
*   **安全性:** 为生产环境实现适当的身份验证、授权、输入验证加固和安全的配置管理。
*   **可扩展性:** 考虑部署策略 (例如, 使用 Docker 进行容器化, Kubernetes), 异步任务扩展 (对于高负载情况, 考虑使用 Celery 等代替 `BackgroundTasks`), 以及数据库连接池调优以提高可扩展性。
*   **Milvus Schema/Index:** Langchain Milvus 包装器通常会处理集合创建。对于生产环境, 建议显式定义您的 Milvus schema 和索引参数以获得最佳性能和控制。