'use client'

import React, { useState, useEffect } from 'react'
import { fetchKnowledgeBases, deleteKnowledgeBase } from '@/services/knowledgeBaseService'
import type { KnowledgeBase } from '@/types/knowledgeBase'
import Link from 'next/link'

const KnowledgeBaseList: React.FC = () => {
    const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([])
    const [loading, setLoading] = useState(true)

    const loadKnowledgeBases = async () => {
        try {
            setLoading(true)
            const data = await fetchKnowledgeBases()
            setKnowledgeBases(data)
        } catch (error) {
            console.error('加载知识库列表失败:', error)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        loadKnowledgeBases()
    }, [])

    const handleDelete = async (id: string, e: React.MouseEvent) => {
        e.preventDefault()
        e.stopPropagation()

        if (!window.confirm('确定要删除此知识库吗？此操作不可撤销。')) {
            return
        }

        try {
            await deleteKnowledgeBase(id)
            // 重新加载列表
            loadKnowledgeBases()
        } catch (error) {
            console.error('删除知识库失败:', error)
        }
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

    return (
        <div className="bg-white rounded-lg shadow">
            <div className="p-4 border-b flex justify-between items-center">
                <h2 className="text-lg font-medium">知识库</h2>
                <Link
                    href="/knowledge/create"
                    className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition"
                >
                    创建知识库
                </Link>
            </div>

            {loading ? (
                <div className="p-8 text-center">
                    <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
                    <p className="mt-2 text-gray-500">加载中...</p>
                </div>
            ) : (
                <div className="divide-y">
                    {knowledgeBases.length === 0 ? (
                        <div className="p-8 text-center text-gray-500">
                            <p>您还没有创建知识库</p>
                            <Link
                                href="/knowledge/create"
                                className="inline-block mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition"
                            >
                                创建知识库
                            </Link>
                        </div>
                    ) : (
                        knowledgeBases.map(kb => (
                            <Link
                                key={kb.id}
                                href={`/knowledge/${kb.id}`}
                                className="block p-4 hover:bg-gray-50 transition"
                            >
                                <div className="flex items-center justify-between">
                                    <div>
                                        <h3 className="font-medium text-blue-600">{kb.name}</h3>
                                        <p className="text-sm text-gray-500 mt-1">{kb.description || '无描述'}</p>
                                        <div className="flex items-center gap-3 mt-2">
                                            <span className="text-xs text-gray-500">
                                                创建于: {formatDate(kb.created_at)}
                                            </span>
                                            <span className="text-xs text-gray-500">
                                                文档数: {kb.document_count || 0}
                                            </span>
                                            <span className={`text-xs px-2 py-0.5 rounded-full ${kb.status === 'ready' ? 'bg-green-100 text-green-800' :
                                                kb.status === 'processing' ? 'bg-yellow-100 text-yellow-800' :
                                                    'bg-red-100 text-red-800'
                                                }`}>
                                                {kb.status === 'ready' ? '就绪' :
                                                    kb.status === 'processing' ? '处理中' : '错误'}
                                            </span>
                                        </div>
                                    </div>
                                    <div className="flex items-center space-x-2">
                                        <button
                                            onClick={(e) => handleDelete(kb.id, e)}
                                            className="px-3 py-1 text-sm text-red-600 hover:bg-red-50 rounded"
                                        >
                                            删除
                                        </button>
                                    </div>
                                </div>
                            </Link>
                        ))
                    )}
                </div>
            )}
        </div>
    )
}

export default KnowledgeBaseList 