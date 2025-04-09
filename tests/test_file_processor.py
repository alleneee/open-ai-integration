"""
文件处理服务的测试类
"""
import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock
import asyncio

from app.services.file_processor import (
    determine_file_type,
    get_file_processor,
    process_file
)
from app.services.document_processor import process_text

class TestFileProcessor:
    """文件处理服务测试类"""
    
    def test_determine_file_type(self):
        """测试文件类型识别功能"""
        # 测试文本文件类型
        assert determine_file_type("test.txt") == "text"
        assert determine_file_type("test.md") == "text"
        
        # 测试PDF文件类型
        assert determine_file_type("test.pdf") == "pdf"
        
        # 测试Word文件类型
        assert determine_file_type("test.docx") == "docx"
        assert determine_file_type("test.doc") == "doc"
        
        # 测试Excel文件类型
        assert determine_file_type("test.xlsx") == "xlsx"
        assert determine_file_type("test.xls") == "xls"
        
        # 测试PowerPoint文件类型
        assert determine_file_type("test.pptx") == "pptx"
        assert determine_file_type("test.ppt") == "ppt"
        
        # 测试CSV文件类型
        assert determine_file_type("test.csv") == "csv"
        
        # 测试未知文件类型
        assert determine_file_type("test.unknown") == "unknown"
    
    def test_get_file_processor(self):
        """测试获取文件处理器功能"""
        # 测试文本文件处理器
        text_processor = get_file_processor("text")
        assert text_processor is not None
        
        # 测试PDF文件处理器
        pdf_processor = get_file_processor("pdf")
        assert pdf_processor is not None
        
        # 测试未支持的文件类型处理器
        with pytest.raises(ValueError):
            get_file_processor("unknown")
    
    @patch("app.services.file_processor.process_text")
    def test_process_text_file(self, mock_process_text):
        """测试处理文本文件功能"""
        # 创建临时文本文件
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp.write(b"This is a test content.\nTest line 2.")
            tmp_path = tmp.name
        
        try:
            # 设置模拟处理结果
            mock_process_text.return_value = "This is a test content. Test line 2."
            
            # 处理文本文件
            result = process_file(tmp_path)
            
            # 验证结果
            assert result == "This is a test content. Test line 2."
            mock_process_text.assert_called_once()
        finally:
            # 清理临时文件
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    
    @patch("app.services.file_processor.extract_text_from_pdf")
    def test_process_pdf_file(self, mock_extract_pdf):
        """测试处理PDF文件功能"""
        # 设置模拟PDF提取结果
        mock_extract_pdf.return_value = "PDF extracted content"
        
        # 模拟PDF文件处理
        result = process_file("test.pdf")
        
        # 验证结果
        assert result == "PDF extracted content"
        mock_extract_pdf.assert_called_once_with("test.pdf")
    
    @patch("app.services.file_processor.extract_text_from_docx")
    def test_process_docx_file(self, mock_extract_docx):
        """测试处理DOCX文件功能"""
        # 设置模拟DOCX提取结果
        mock_extract_docx.return_value = "DOCX extracted content"
        
        # 模拟DOCX文件处理
        result = process_file("test.docx")
        
        # 验证结果
        assert result == "DOCX extracted content"
        mock_extract_docx.assert_called_once_with("test.docx")
    
    @patch("app.services.document_processor.split_text_into_chunks")
    def test_text_splitting(self, mock_split):
        """测试文本分块功能"""
        # 设置模拟分块结果
        mock_split.return_value = [
            {"content": "Chunk 1", "metadata": {}},
            {"content": "Chunk 2", "metadata": {}}
        ]
        
        # 模拟文本处理
        text = "Test content for splitting into chunks"
        result = process_text(text)
        
        # 验证结果
        mock_split.assert_called_once()
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["content"] == "Chunk 1"
        assert result[1]["content"] == "Chunk 2"
    
    @patch("app.services.file_processor.determine_file_type")
    def test_unsupported_file_type(self, mock_determine_type):
        """测试不支持的文件类型处理"""
        # 设置模拟文件类型
        mock_determine_type.return_value = "unknown"
        
        # 测试处理不支持的文件类型
        with pytest.raises(ValueError) as excinfo:
            process_file("test.unknown")
        
        assert "Unsupported file type" in str(excinfo.value) 