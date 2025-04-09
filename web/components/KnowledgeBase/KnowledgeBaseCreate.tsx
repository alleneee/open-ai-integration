'use client'

import React, { useState } from 'react'
import { createKnowledgeBase } from '@/services/knowledgeBaseService'
import { useRouter } from 'next/navigation'

const EMBEDDING_MODELS = [
    { id: 'openai', name: 'OpenAI Embeddings', description: 'OpenAI文本嵌入模型' },
    { id: 'bge-base', name: 'BGE Base', description: '北京通用嵌入模型(Base)' },
    { id: 'bge-large', name: 'BGE Large', description: '北京通用嵌入模型(Large)' },
    { id: 'jina', name: 'Jina Embeddings', description: 'Jina Embeddings模型' }
]

const RETRIEVAL_TYPES = [
    { id: 'semantic', name: '语义检索', description: '基于语义相似度检索' },
    { id: 'keyword', name: '关键词检索', description: '基于关键词匹配检索' },
    { id: 'hybrid', name: '混合检索', description: '结合语义和关键词检索' }
]

const KnowledgeBaseCreate: React.FC = () => {
    const router = useRouter()
    const [loading, setLoading] = useState(false)
    const [formData, setFormData] = useState({
        name: '',
        description: '',
        embedding_model: EMBEDDING_MODELS[0].id,
        retrieval_type: RETRIEVAL_TYPES[0].id
    })

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
        const { name, value } = e.target
        setFormData(prev => ({ ...prev, [name]: value }))
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()

        if (!formData.name.trim()) {
            alert('请输入知识库名称')
            return
        }

        try {
            setLoading(true)
            const result = await createKnowledgeBase(formData)
            router.push(`/knowledge/${result.id}`)
        } catch (error) {
            console.error('创建知识库失败:', error)
            alert('创建知识库失败，请重试')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="bg-white rounded-lg shadow">
            <div className="p-4 border-b">
                <h2 className="text-lg font-medium">创建知识库</h2>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-6">
                <div>
                    <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
                        知识库名称 <span className="text-red-500">*</span>
                    </label>
                    <input
                        type="text"
                        id="name"
                        name="name"
                        required
                        value={formData.name}
                        onChange={handleChange}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="输入知识库名称"
                    />
                </div>

                <div>
                    <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
                        知识库描述
                    </label>
                    <textarea
                        id="description"
                        name="description"
                        value={formData.description}
                        onChange={handleChange}
                        rows={3}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="输入知识库描述（可选）"
                    />
                </div>

                <div>
                    <label htmlFor="embedding_model" className="block text-sm font-medium text-gray-700 mb-1">
                        嵌入模型
                    </label>
                    <select
                        id="embedding_model"
                        name="embedding_model"
                        value={formData.embedding_model}
                        onChange={handleChange}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                        {EMBEDDING_MODELS.map(model => (
                            <option key={model.id} value={model.id}>
                                {model.name} - {model.description}
                            </option>
                        ))}
                    </select>
                    <p className="mt-1 text-xs text-gray-500">
                        嵌入模型用于将文本转换为向量，用于语义检索
                    </p>
                </div>

                <div>
                    <label htmlFor="retrieval_type" className="block text-sm font-medium text-gray-700 mb-1">
                        检索类型
                    </label>
                    <select
                        id="retrieval_type"
                        name="retrieval_type"
                        value={formData.retrieval_type}
                        onChange={handleChange}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                        {RETRIEVAL_TYPES.map(type => (
                            <option key={type.id} value={type.id}>
                                {type.name} - {type.description}
                            </option>
                        ))}
                    </select>
                    <p className="mt-1 text-xs text-gray-500">
                        检索类型决定了系统如何搜索知识库中的内容
                    </p>
                </div>

                <div className="flex justify-end pt-4 border-t">
                    <button
                        type="button"
                        onClick={() => router.push('/knowledge')}
                        className="px-4 py-2 text-gray-700 border border-gray-300 rounded-md mr-2 hover:bg-gray-50"
                    >
                        取消
                    </button>
                    <button
                        type="submit"
                        disabled={loading}
                        className={`px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 ${loading ? 'opacity-70 cursor-not-allowed' : ''
                            }`}
                    >
                        {loading ? (
                            <>
                                <span className="inline-block animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full mr-2"></span>
                                创建中...
                            </>
                        ) : '创建知识库'}
                    </button>
                </div>
            </form>
        </div>
    )
}

export default KnowledgeBaseCreate 