"""
测试所需的模拟对象和工具函数
"""
from unittest.mock import MagicMock
import io

# 模拟知识库服务对象
kb_service_mock = MagicMock()
kb_service_mock.create_knowledge_base.return_value = MagicMock()
kb_service_mock.get_knowledge_base.return_value = MagicMock()
kb_service_mock.get_knowledge_bases.return_value = ([], 0)
kb_service_mock.get_knowledge_base_with_documents.return_value = MagicMock()
kb_service_mock.update_knowledge_base.return_value = MagicMock()
kb_service_mock.delete_knowledge_base.return_value = True

# 模拟文档处理服务
document_processor_mock = MagicMock()
document_processor_mock.process_document.return_value = True

# 模拟向量存储服务函数
def mock_create_collection(*args, **kwargs):
    return True

def mock_check_collection_exists(*args, **kwargs):
    return True

def mock_get_knowledge_base_stats(*args, **kwargs):
    return {"vector_count": 0, "dimension": 1536}

def mock_get_retriever(*args, **kwargs):
    retriever_mock = MagicMock()
    retriever_mock.retrieve.return_value = []
    return retriever_mock

# 模拟文档解析函数
async def mock_parse_uploaded_file_and_split(*args, **kwargs):
    """模拟文档解析和分块函数"""
    return [{"content": "测试内容", "metadata": {}}], "/tmp/test.txt"

# 应用模拟的钩子函数
def apply_mocks():
    """应用所有模拟"""
    # 知识库模块模拟
    from app.api.v1.endpoints import knowledge_base
    knowledge_base.kb_service = kb_service_mock
    knowledge_base.create_collection = mock_create_collection
    knowledge_base.check_collection_exists = mock_check_collection_exists
    knowledge_base.get_knowledge_base_stats = mock_get_knowledge_base_stats
    
    # 文档处理模块模拟
    from app.api.v1.endpoints import documents
    documents.parse_uploaded_file_and_split = mock_parse_uploaded_file_and_split
    documents.document_indexing_task = MagicMock()
    documents.document_processor = document_processor_mock
    documents.get_retriever = mock_get_retriever
    
    # 其他可能需要的依赖
    try:
        from app.api.v1.endpoints import segments
        segments.update_segment = MagicMock()
    except ImportError:
        pass 