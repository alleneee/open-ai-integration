'use client'

import React, { useState, useEffect } from 'react'
import { fetchDocuments, deleteDocument } from '@/services/knowledgeBaseService'
import type { Document } from '@/types/knowledgeBase'

interface DocumentListProps {
    knowledgeBaseId: string;
    refreshTrigger?: number; // 用于触发刷新
}

const DocumentList: React.FC<DocumentListProps> = ({ knowledgeBaseId, refreshTrigger = 0 }) => {
    const [documents, setDocuments] = useState<Document[]>([])
    const [loading, setLoading] = useState(true)

    const loadDocuments = async () => {
        try {
            setLoading(true)
            const data = await fetchDocuments(knowledgeBaseId)
            setDocuments(data)
        } catch (error) {
            console.error('加载文档列表失败:', error)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        if (knowledgeBaseId) {
            loadDocuments()
        }
    }, [knowledgeBaseId, refreshTrigger])

    const handleDelete = async (documentId: string) => {
        if (!window.confirm('确定要删除此文档吗？此操作不可撤销。')) {
            return
        }

        try {
            await deleteDocument(knowledgeBaseId, documentId)
            // 重新加载列表
            loadDocuments()
        } catch (error) {
            console.error('删除文档失败:', error)
        }
    }

    const formatFileSize = (bytes: number) => {
        if (bytes < 1024) return bytes + ' B'
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
    }

    const formatDate = (dateString: string) => {
        const date = new Date(dateString)
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        })
    }

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'completed':
                return 'bg-green-100 text-green-800'
            case 'processing':
                return 'bg-yellow-100 text-yellow-800'
            case 'error':
                return 'bg-red-100 text-red-800'
            default:
                return 'bg-gray-100 text-gray-800'
        }
    }

    const getStatusText = (status: string) => {
        switch (status) {
            case 'completed':
                return '已完成'
            case 'processing':
                return '处理中'
            case 'error':
                return '错误'
            case 'pending':
                return '等待中'
            default:
                return status
        }
    }

    const getFileIcon = (mimeType: string) => {
        if (mimeType.includes('pdf')) {
            return (
                <svg className="w-6 h-6 text-red-500" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M7 11.5h10a.5.5 0 000-1H7a.5.5 0 000 1zm0 4h10a.5.5 0 000-1H7a.5.5 0 000 1zm0-8h10a.5.5 0 000-1H7a.5.5 0 000 1zM20.5 5v14c0 .827-.673 1.5-1.5 1.5h-14c-.827 0-1.5-.673-1.5-1.5v-14c0-.827.673-1.5 1.5-1.5h14c.827 0 1.5.673 1.5 1.5zm-1 0c0-.275-.225-.5-.5-.5h-14c-.275 0-.5.225-.5.5v14c0 .275.225.5.5.5h14c.275 0 .5-.225.5-.5v-14z" />
                </svg>
            )
        } else if (mimeType.includes('text')) {
            return (
                <svg className="w-6 h-6 text-blue-500" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M14 2.25H7c-1.1 0-2 .9-2 2v15.5c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2V8.25l-5-6zm3 17.5H7v-15h6v4.5h4v10.5zm-8-10h8v1h-8v-1zm0 2h8v1h-8v-1zm0 2h8v1h-8v-1z" />
                </svg>
            )
        } else if (mimeType.includes('word') || mimeType.includes('document')) {
            return (
                <svg className="w-6 h-6 text-blue-600" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zM6 20V4h7v5h5v11H6zm10-9H8v-2h8v2zm0 3H8v-2h8v2zm0 3H8v-2h8v2z" />
                </svg>
            )
        } else {
            return (
                <svg className="w-6 h-6 text-gray-500" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zM6 20V4h7v5h5v11H6z" />
                </svg>
            )
        }
    }

    return (
        <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="p-4 border-b">
                <h2 className="text-lg font-medium">文档列表</h2>
            </div>

            {loading ? (
                <div className="p-8 text-center">
                    <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
                    <p className="mt-2 text-gray-500">加载中...</p>
                </div>
            ) : (
                <div>
                    {documents.length === 0 ? (
                        <div className="p-8 text-center text-gray-500">
                            <p>此知识库暂无文档，请上传文档</p>
                        </div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            文档名
                                        </th>
                                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            大小
                                        </th>
                                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            状态
                                        </th>
                                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            上传时间
                                        </th>
                                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            处理信息
                                        </th>
                                        <th scope="col" className="relative px-6 py-3">
                                            <span className="sr-only">操作</span>
                                        </th>
                                    </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {documents.map((doc) => (
                                        <tr key={doc.id} className="hover:bg-gray-50">
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <div className="flex items-center">
                                                    <div className="flex-shrink-0">
                                                        {getFileIcon(doc.mime_type)}
                                                    </div>
                                                    <div className="ml-4">
                                                        <div className="text-sm font-medium text-gray-900" title={doc.name}>
                                                            {doc.name.length > 30 ? doc.name.substring(0, 30) + '...' : doc.name}
                                                        </div>
                                                    </div>
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <div className="text-sm text-gray-500">
                                                    {formatFileSize(doc.size_bytes)}
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(doc.status)}`}>
                                                    {getStatusText(doc.status)}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                {formatDate(doc.created_at)}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <div className="text-sm text-gray-500">
                                                    {doc.chunks && (
                                                        <span className="mr-2">{doc.chunks}个片段</span>
                                                    )}
                                                    {doc.tokens && (
                                                        <span className="mr-2">{doc.tokens}个词元</span>
                                                    )}
                                                    {doc.error_message && (
                                                        <span className="text-red-500" title={doc.error_message}>处理错误</span>
                                                    )}
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                                <button
                                                    onClick={() => handleDelete(doc.id)}
                                                    className="text-red-600 hover:text-red-900"
                                                >
                                                    删除
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}

export default DocumentList 