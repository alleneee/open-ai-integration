'use client'

import React, { useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css'; // 引入注释层样式
import 'react-pdf/dist/Page/TextLayer.css'; // 引入文本层样式

// 配置 pdfjs worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

interface PdfViewerProps {
    fileUrl: string; // PDF 文件 URL
}

const PdfViewer: React.FC<PdfViewerProps> = ({ fileUrl }) => {
    const [numPages, setNumPages] = useState<number | null>(null);
    const [pageNumber, setPageNumber] = useState<number>(1);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    function onDocumentLoadSuccess({ numPages }: { numPages: number }): void {
        setNumPages(numPages);
        setPageNumber(1); // 重置到第一页
        setLoading(false);
        setError(null);
    }

    function onDocumentLoadError(error: Error): void {
        console.error('Failed to load PDF:', error);
        setError('无法加载 PDF 文件。');
        setLoading(false);
    }

    function changePage(offset: number) {
        setPageNumber(prevPageNumber => Math.max(1, Math.min(prevPageNumber + offset, numPages || 1)));
    }

    function previousPage() {
        changePage(-1);
    }

    function nextPage() {
        changePage(1);
    }

    return (
        <div className="pdf-viewer border rounded">
            {loading && <div className="p-4 text-center">加载 PDF 中...</div>}
            {error && <div className="p-4 text-center text-red-500">{error}</div>}
            {!loading && !error && (
                <>
                    <div className="pdf-controls flex justify-between items-center p-2 bg-gray-100 border-b">
                        <button
                            type="button"
                            disabled={pageNumber <= 1}
                            onClick={previousPage}
                            className="px-3 py-1 bg-gray-300 rounded disabled:opacity-50"
                        >
                            上一页
                        </button>
                        <span>
                            第 {pageNumber || (numPages ? 1 : '--')} 页 / 共 {numPages || '--'} 页
                        </span>
                        <button
                            type="button"
                            disabled={!numPages || pageNumber >= numPages}
                            onClick={nextPage}
                            className="px-3 py-1 bg-gray-300 rounded disabled:opacity-50"
                        >
                            下一页
                        </button>
                    </div>
                    <div className="pdf-document-container overflow-auto" style={{ maxHeight: '70vh' }}> {/* 设置最大高度并允许滚动 */}
                        <Document
                            file={fileUrl}
                            onLoadSuccess={onDocumentLoadSuccess}
                            onLoadError={onDocumentLoadError}
                            options={{
                                cMapUrl: `https://unpkg.com/pdfjs-dist@${pdfjs.version}/cmaps/`,
                                cMapPacked: true,
                            }}
                        >
                            <Page pageNumber={pageNumber} />
                        </Document>
                    </div>
                </>
            )}
        </div>
    );
}

export default PdfViewer; 