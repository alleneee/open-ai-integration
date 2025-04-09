'use client'

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { fetchWorkflows, deleteWorkflow } from '../../services/workflowService'
import type { Workflow } from '../../types'

const WorkflowList: React.FC = () => {
    const router = useRouter()
    const [workflows, setWorkflows] = useState<Workflow[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [filter, setFilter] = useState('')

    useEffect(() => {
        const loadWorkflows = async () => {
            try {
                setLoading(true)
                setError(null)
                const data = await fetchWorkflows()
                setWorkflows(data)
            } catch (error) {
                console.error('加载工作流列表失败:', error)
                setError('加载工作流列表失败，请刷新页面重试')
            } finally {
                setLoading(false)
            }
        }

        loadWorkflows()
    }, [])

    const handleDelete = async (workflowId: string, event: React.MouseEvent) => {
        event.preventDefault()
        event.stopPropagation()

        if (!window.confirm('确定要删除此工作流吗？此操作不可撤销。')) {
            return
        }

        try {
            await deleteWorkflow(workflowId)
            setWorkflows(workflows.filter(workflow => workflow.id !== workflowId))
        } catch (error) {
            console.error('删除工作流失败:', error)
            alert('删除工作流失败，请重试')
        }
    }

    // 格式化日期
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

    // 过滤工作流
    const filteredWorkflows = filter
        ? workflows.filter(workflow =>
            workflow.name.toLowerCase().includes(filter.toLowerCase()) ||
            (workflow.description && workflow.description.toLowerCase().includes(filter.toLowerCase()))
        )
        : workflows

    if (loading) {
        return (
            <div className="flex justify-center items-center py-12">
                <div className="animate-spin h-10 w-10 border-4 border-blue-500 border-t-transparent rounded-full"></div>
            </div>
        )
    }

    if (error) {
        return (
            <div className="p-6 text-center text-red-500">
                <div className="text-lg mb-2">出错了</div>
                <div>{error}</div>
            </div>
        )
    }

    return (
        <div className="space-y-6">
            <div className="bg-white rounded-lg shadow">
                <div className="p-4 border-b border-gray-200 flex justify-between items-center">
                    <h2 className="text-lg font-medium">工作流列表</h2>
                    <div className="flex space-x-2">
                        <input
                            type="text"
                            placeholder="搜索工作流..."
                            value={filter}
                            onChange={(e) => setFilter(e.target.value)}
                            className="px-3 py-1 border border-gray-300 rounded-md text-sm w-48"
                        />
                        <Link
                            href="/workflows/create"
                            className="px-3 py-1 bg-purple-500 text-white rounded-md hover:bg-purple-600 transition text-sm"
                        >
                            创建工作流
                        </Link>
                    </div>
                </div>

                {filteredWorkflows.length === 0 ? (
                    <div className="p-8 text-center text-gray-500">
                        <p>{filter ? '没有匹配的工作流' : '暂无工作流'}</p>
                        <p className="mt-1 text-sm">点击"创建工作流"按钮开始创建</p>
                    </div>
                ) : (
                    <div className="divide-y divide-gray-200">
                        {filteredWorkflows.map(workflow => (
                            <Link
                                key={workflow.id}
                                href={`/workflows/${workflow.id}`}
                                className="block hover:bg-gray-50 transition"
                            >
                                <div className="p-6">
                                    <div className="flex justify-between items-start">
                                        <div>
                                            <h3 className="text-lg font-medium text-gray-900">{workflow.name}</h3>
                                            {workflow.description && (
                                                <p className="mt-1 text-sm text-gray-500">{workflow.description}</p>
                                            )}
                                            <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-gray-500">
                                                <span>
                                                    模型: {workflow.model}
                                                </span>
                                                <span>
                                                    温度: {workflow.temperature}
                                                </span>
                                                <span>
                                                    更新于: {formatDate(workflow.updatedAt || '')}
                                                </span>
                                                <span className={`px-2 py-0.5 rounded-full ${workflow.status === 'ready' ? 'bg-green-100 text-green-800' :
                                                    workflow.status === 'processing' ? 'bg-yellow-100 text-yellow-800' :
                                                        'bg-red-100 text-red-800'
                                                    }`}>
                                                    {workflow.status === 'ready' ? '就绪' :
                                                        workflow.status === 'processing' ? '处理中' : '错误'}
                                                </span>
                                            </div>
                                        </div>
                                        <div className="flex items-center space-x-2">
                                            <button
                                                onClick={(e) => handleDelete(workflow.id, e)}
                                                className="text-red-500 hover:text-red-700 transition"
                                                title="删除工作流"
                                            >
                                                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                                </svg>
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </Link>
                        ))}
                    </div>
                )}
            </div>
        </div>
    )
}

export default WorkflowList 