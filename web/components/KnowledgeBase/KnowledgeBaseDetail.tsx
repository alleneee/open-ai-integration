'use client'

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { fetchKnowledgeBase, updateKnowledgeBase, deleteKnowledgeBase } from '@/services/knowledgeBaseService'
import type { KnowledgeBase } from '@/types/knowledgeBase'
import DocumentUpload from './DocumentUpload'
import DocumentList from './DocumentList'

interface KnowledgeBaseDetailProps {
    knowledgeBaseId: string;
}

const KnowledgeBaseDetail: React.FC<KnowledgeBaseDetailProps> = ({ knowledgeBaseId }) => {
    const router = useRouter()
    const [knowledgeBase, setKnowledgeBase] = useState<KnowledgeBase | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [activeTab, setActiveTab] = useState<'documents' | 'settings'>('documents')
    const [refreshTrigger, setRefreshTrigger] = useState(0)
    const [isEditing, setIsEditing] = useState(false)
    const [form, setForm] = useState({
        name: '',
        description: ''
    })

    useEffect(() => {
        const loadKnowledgeBase = async () => {
            try {
                setLoading(true)
                setError(null)
                const data = await fetchKnowledgeBase(knowledgeBaseId)
                setKnowledgeBase(data)
                setForm({
                    name: data.name,
                    description: data.description || ''
                })
            } catch (error) {
                console.error('加载知识库详情失败:', error)
                setError('加载知识库详情失败，请刷新页面重试')
            } finally {
                setLoading(false)
            }
        }

        if (knowledgeBaseId) {
            loadKnowledgeBase()
        }
    }, [knowledgeBaseId])

    const handleDelete = async () => {
        if (!window.confirm('确定要删除此知识库吗？此操作不可撤销，将删除所有相关文档。')) {
            return
        }

        try {
            await deleteKnowledgeBase(knowledgeBaseId)
            router.push('/knowledge')
        } catch (error) {
            console.error('删除知识库失败:', error)
            alert('删除知识库失败，请重试')
        }
    }

    const handleUpdateForm = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        const { name, value } = e.target
        setForm(prev => ({ ...prev, [name]: value }))
    }

    const handleSaveSettings = async () => {
        try {
            const updatedKB = await updateKnowledgeBase(knowledgeBaseId, form)
            setKnowledgeBase(updatedKB)
            setIsEditing(false)
            alert('知识库设置已更新')
        } catch (error) {
            console.error('更新知识库失败:', error)
            alert('更新知识库设置失败，请重试')
        }
    }

    const handleUploadSuccess = () => {
        // 刷新文档列表
        setRefreshTrigger(prev => prev + 1)
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

    if (loading) {
        return (
            <div className="p-8 text-center">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
                <p className="mt-2 text-gray-500">加载中...</p>
            </div>
        )
    }

    if (error || !knowledgeBase) {
        return (
            <div className="p-8 text-center text-red-500">
                <p>{error || '加载知识库失败'}</p>
                <button
                    onClick={() => router.push('/knowledge')}
                    className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition"
                >
                    返回知识库列表
                </button>
            </div>
        )
    }

    return (
        <div className="space-y-6">
            <div className="bg-white rounded-lg shadow">
                <div className="p-6">
                    <div className="flex justify-between items-start">
                        <div>
                            <h1 className="text-2xl font-bold text-gray-900">{knowledgeBase.name}</h1>
                            {knowledgeBase.description && (
                                <p className="mt-1 text-gray-500">{knowledgeBase.description}</p>
                            )}
                            <div className="mt-3 flex items-center gap-4">
                                <span className="text-sm text-gray-500">
                                    创建于: {formatDate(knowledgeBase.created_at)}
                                </span>
                                <span className="text-sm text-gray-500">
                                    文档数: {knowledgeBase.document_count || 0}
                                </span>
                                <span className={`text-sm px-2 py-0.5 rounded-full ${knowledgeBase.status === 'ready' ? 'bg-green-100 text-green-800' :
                                    knowledgeBase.status === 'processing' ? 'bg-yellow-100 text-yellow-800' :
                                        'bg-red-100 text-red-800'
                                    }`}>
                                    {knowledgeBase.status === 'ready' ? '就绪' :
                                        knowledgeBase.status === 'processing' ? '处理中' : '错误'}
                                </span>
                            </div>
                        </div>
                        <button
                            onClick={handleDelete}
                            className="px-3 py-1 border border-red-300 text-red-600 rounded hover:bg-red-50 transition"
                        >
                            删除知识库
                        </button>
                    </div>
                </div>

                <div className="border-t border-gray-200">
                    <div className="flex">
                        <button
                            onClick={() => setActiveTab('documents')}
                            className={`px-4 py-2 text-sm font-medium ${activeTab === 'documents'
                                ? 'border-b-2 border-blue-500 text-blue-600'
                                : 'text-gray-500 hover:text-gray-700'
                                }`}
                        >
                            文档管理
                        </button>
                        <button
                            onClick={() => setActiveTab('settings')}
                            className={`px-4 py-2 text-sm font-medium ${activeTab === 'settings'
                                ? 'border-b-2 border-blue-500 text-blue-600'
                                : 'text-gray-500 hover:text-gray-700'
                                }`}
                        >
                            知识库设置
                        </button>
                    </div>
                </div>
            </div>

            {activeTab === 'documents' ? (
                <div className="space-y-6">
                    <div className="bg-white rounded-lg shadow p-6">
                        <h2 className="text-lg font-medium mb-4">上传文档</h2>
                        <DocumentUpload
                            knowledgeBaseId={knowledgeBaseId}
                            onUploadSuccess={handleUploadSuccess}
                        />
                    </div>

                    <DocumentList
                        knowledgeBaseId={knowledgeBaseId}
                        refreshTrigger={refreshTrigger}
                    />
                </div>
            ) : (
                <div className="bg-white rounded-lg shadow">
                    <div className="p-4 border-b flex justify-between items-center">
                        <h2 className="text-lg font-medium">知识库设置</h2>
                        {isEditing ? (
                            <div className="flex space-x-2">
                                <button
                                    onClick={() => {
                                        setIsEditing(false);
                                        setForm({
                                            name: knowledgeBase.name,
                                            description: knowledgeBase.description || ''
                                        });
                                    }}
                                    className="px-3 py-1 border border-gray-300 text-gray-700 rounded hover:bg-gray-50 transition"
                                >
                                    取消
                                </button>
                                <button
                                    onClick={handleSaveSettings}
                                    className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 transition"
                                >
                                    保存
                                </button>
                            </div>
                        ) : (
                            <button
                                onClick={() => setIsEditing(true)}
                                className="px-3 py-1 border border-blue-300 text-blue-600 rounded hover:bg-blue-50 transition"
                            >
                                编辑
                            </button>
                        )}
                    </div>

                    <div className="p-6 space-y-6">
                        <div>
                            <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
                                知识库名称 <span className="text-red-500">*</span>
                            </label>
                            {isEditing ? (
                                <input
                                    type="text"
                                    id="name"
                                    name="name"
                                    required
                                    value={form.name}
                                    onChange={handleUpdateForm}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    placeholder="输入知识库名称"
                                />
                            ) : (
                                <div className="px-3 py-2 border border-gray-200 rounded-md bg-gray-50">
                                    {knowledgeBase.name}
                                </div>
                            )}
                        </div>

                        <div>
                            <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
                                知识库描述
                            </label>
                            {isEditing ? (
                                <textarea
                                    id="description"
                                    name="description"
                                    value={form.description}
                                    onChange={handleUpdateForm}
                                    rows={3}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    placeholder="输入知识库描述（可选）"
                                />
                            ) : (
                                <div className="px-3 py-2 border border-gray-200 rounded-md bg-gray-50 min-h-[80px]">
                                    {knowledgeBase.description || '无描述'}
                                </div>
                            )}
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                嵌入模型
                            </label>
                            <div className="px-3 py-2 border border-gray-200 rounded-md bg-gray-50">
                                {knowledgeBase.embedding_model || '默认模型'}
                            </div>
                            <p className="mt-1 text-xs text-gray-500">
                                嵌入模型一旦选择就不能更改
                            </p>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                检索方式
                            </label>
                            <div className="px-3 py-2 border border-gray-200 rounded-md bg-gray-50">
                                {knowledgeBase.retrieval_type || '默认检索方式'}
                            </div>
                            <p className="mt-1 text-xs text-gray-500">
                                检索方式一旦选择就不能更改
                            </p>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

export default KnowledgeBaseDetail 