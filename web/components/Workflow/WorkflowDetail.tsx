'use client'

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { fetchWorkflow, updateWorkflow, deleteWorkflow, saveWorkflowNodes } from '@/services/workflowService'
import type { Workflow } from '@/types/workflow'
import WorkflowCanvas from './WorkflowCanvas'
import { Node, Edge, MarkerType } from 'reactflow'

interface WorkflowDetailProps {
    workflowId: string;
}

const WorkflowDetail: React.FC<WorkflowDetailProps> = ({ workflowId }) => {
    const router = useRouter()
    const [workflow, setWorkflow] = useState<Workflow | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [activeTab, setActiveTab] = useState<'editor' | 'settings'>('editor')
    const [isEditing, setIsEditing] = useState(false)
    const [form, setForm] = useState({
        name: '',
        description: '',
        model: '',
        temperature: 0.7,
        max_tokens: 2048,
        agent_enabled: false,
        enable_streaming: true
    })

    useEffect(() => {
        const loadWorkflow = async () => {
            try {
                setLoading(true)
                setError(null)
                const data = await fetchWorkflow(workflowId)
                setWorkflow(data)
                setForm({
                    name: data.name,
                    description: data.description || '',
                    model: data.model,
                    temperature: data.temperature,
                    max_tokens: data.max_tokens,
                    agent_enabled: data.agent_enabled,
                    enable_streaming: data.enable_streaming
                })
            } catch (error) {
                console.error('加载工作流详情失败:', error)
                setError('加载工作流详情失败，请刷新页面重试')
            } finally {
                setLoading(false)
            }
        }

        if (workflowId) {
            loadWorkflow()
        }
    }, [workflowId])

    const handleDelete = async () => {
        if (!window.confirm('确定要删除此工作流吗？此操作不可撤销。')) {
            return
        }

        try {
            await deleteWorkflow(workflowId)
            router.push('/workspace')
        } catch (error) {
            console.error('删除工作流失败:', error)
            alert('删除工作流失败，请重试')
        }
    }

    const handleSaveNodes = async (nodes: Node[], edges: Edge[]) => {
        try {
            await saveWorkflowNodes(workflowId, nodes, edges)
            // 更新本地状态
            if (workflow) {
                setWorkflow({
                    ...workflow,
                    nodes: nodes as any,
                    edges: edges as any,
                    updated_at: new Date().toISOString()
                })
            }
        } catch (error) {
            console.error('保存工作流节点失败:', error)
            alert('保存工作流节点失败，请重试')
        }
    }

    const handleUpdateForm = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
        const { name, value } = e.target
        setForm(prev => ({
            ...prev,
            [name]: value
        }))
    }

    const handleUpdateBoolForm = (e: React.ChangeEvent<HTMLInputElement>) => {
        const { name, checked } = e.target
        setForm(prev => ({
            ...prev,
            [name]: checked
        }))
    }

    const handleSaveSettings = async () => {
        try {
            const updatedWorkflow = await updateWorkflow(workflowId, {
                name: form.name,
                description: form.description,
                model: form.model,
                temperature: parseFloat(form.temperature.toString()),
                max_tokens: parseInt(form.max_tokens.toString()),
                agent_enabled: form.agent_enabled,
                enable_streaming: form.enable_streaming
            })
            setWorkflow(updatedWorkflow)
            setIsEditing(false)
        } catch (error) {
            console.error('更新工作流失败:', error)
            alert('更新工作流失败，请重试')
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

    if (loading) {
        return (
            <div className="flex justify-center items-center py-12">
                <div className="animate-spin h-10 w-10 border-4 border-blue-500 border-t-transparent rounded-full"></div>
            </div>
        )
    }

    if (error || !workflow) {
        return (
            <div className="p-6 text-center text-red-500">
                <div className="text-lg mb-2">出错了</div>
                <div>{error || '无法加载工作流详情'}</div>
            </div>
        )
    }

    // 转换节点和边数据格式以符合reactflow要求
    const initialNodes = workflow.nodes.map(node => ({
        id: node.id,
        type: node.type,
        position: node.position,
        data: node.data
    }))

    const initialEdges = workflow.edges.map(edge => {
        // 确保markerEnd使用正确的MarkerType类型
        const markerEnd = edge.markerEnd ? {
            type: MarkerType.ArrowClosed, // 使用枚举而不是字符串
            width: edge.markerEnd.width,
            height: edge.markerEnd.height
        } : undefined;

        return {
            id: edge.id,
            source: edge.source,
            target: edge.target,
            type: edge.type,
            animated: edge.animated,
            markerEnd,
            data: {
                sourceType: initialNodes.find(node => node.id === edge.source)?.data?.type,
                targetType: initialNodes.find(node => node.id === edge.target)?.data?.type,
            }
        };
    })

    return (
        <div className="space-y-6">
            <div className="bg-white rounded-lg shadow">
                <div className="p-6">
                    <div className="flex justify-between items-start">
                        <div>
                            <h1 className="text-2xl font-bold text-gray-900">{workflow.name}</h1>
                            {workflow.description && (
                                <p className="mt-1 text-gray-500">{workflow.description}</p>
                            )}
                            <div className="mt-3 flex items-center gap-4">
                                <span className="text-sm text-gray-500">
                                    创建于: {formatDate(workflow.created_at)}
                                </span>
                                <span className="text-sm text-gray-500">
                                    更新于: {formatDate(workflow.updated_at)}
                                </span>
                                <span className={`text-sm px-2.5 py-0.5 rounded-full ${workflow.status === 'ready' ? 'bg-green-100 text-green-800' :
                                    workflow.status === 'processing' ? 'bg-yellow-100 text-yellow-800' :
                                        'bg-red-100 text-red-800'
                                    }`}>
                                    {workflow.status === 'ready' ? '就绪' :
                                        workflow.status === 'processing' ? '处理中' : '错误'}
                                </span>
                            </div>
                        </div>
                        <div className="flex space-x-2">
                            {activeTab === 'settings' && !isEditing && (
                                <button
                                    onClick={() => setIsEditing(true)}
                                    className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 transition"
                                >
                                    编辑设置
                                </button>
                            )}
                            {activeTab === 'settings' && isEditing && (
                                <button
                                    onClick={handleSaveSettings}
                                    className="px-3 py-1 bg-green-500 text-white rounded hover:bg-green-600 transition"
                                >
                                    保存设置
                                </button>
                            )}
                            <button
                                onClick={handleDelete}
                                className="px-3 py-1 border border-red-300 text-red-600 rounded hover:bg-red-50 transition"
                            >
                                删除工作流
                            </button>
                        </div>
                    </div>
                </div>

                <div className="border-t border-gray-200">
                    <div className="flex">
                        <button
                            className={`px-6 py-3 text-sm font-medium ${activeTab === 'editor'
                                ? 'border-b-2 border-blue-500 text-blue-600'
                                : 'text-gray-500 hover:text-gray-700'
                                }`}
                            onClick={() => setActiveTab('editor')}
                        >
                            工作流编辑器
                        </button>
                        <button
                            className={`px-6 py-3 text-sm font-medium ${activeTab === 'settings'
                                ? 'border-b-2 border-blue-500 text-blue-600'
                                : 'text-gray-500 hover:text-gray-700'
                                }`}
                            onClick={() => setActiveTab('settings')}
                        >
                            工作流设置
                        </button>
                    </div>
                </div>
            </div>

            {activeTab === 'editor' && (
                <div className="bg-white rounded-lg shadow overflow-hidden">
                    <WorkflowCanvas
                        initialNodes={initialNodes}
                        initialEdges={initialEdges}
                        readOnly={false}
                        onSave={handleSaveNodes}
                    />
                </div>
            )}

            {activeTab === 'settings' && (
                <div className="bg-white rounded-lg shadow p-6 space-y-6">
                    <div>
                        <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
                            工作流名称
                        </label>
                        {isEditing ? (
                            <input
                                type="text"
                                id="name"
                                name="name"
                                value={form.name}
                                onChange={handleUpdateForm}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                placeholder="输入工作流名称"
                            />
                        ) : (
                            <div className="px-3 py-2 border border-gray-200 rounded-md bg-gray-50">
                                {workflow.name}
                            </div>
                        )}
                    </div>

                    <div>
                        <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
                            工作流描述
                        </label>
                        {isEditing ? (
                            <textarea
                                id="description"
                                name="description"
                                value={form.description}
                                onChange={handleUpdateForm}
                                rows={3}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                placeholder="输入工作流描述（可选）"
                            />
                        ) : (
                            <div className="px-3 py-2 border border-gray-200 rounded-md bg-gray-50 min-h-[80px]">
                                {workflow.description || '无描述'}
                            </div>
                        )}
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                            <label htmlFor="model" className="block text-sm font-medium text-gray-700 mb-1">
                                LLM模型
                            </label>
                            {isEditing ? (
                                <select
                                    id="model"
                                    name="model"
                                    value={form.model}
                                    onChange={handleUpdateForm}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                >
                                    <option value="gpt-4">GPT-4</option>
                                    <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                                    <option value="claude-3-opus">Claude 3 Opus</option>
                                    <option value="claude-3-sonnet">Claude 3 Sonnet</option>
                                    <option value="local-model">本地模型</option>
                                </select>
                            ) : (
                                <div className="px-3 py-2 border border-gray-200 rounded-md bg-gray-50">
                                    {workflow.model}
                                </div>
                            )}
                        </div>

                        <div>
                            <label htmlFor="temperature" className="block text-sm font-medium text-gray-700 mb-1">
                                温度 ({form.temperature})
                            </label>
                            {isEditing ? (
                                <div>
                                    <input
                                        type="range"
                                        id="temperature"
                                        name="temperature"
                                        min="0"
                                        max="1"
                                        step="0.1"
                                        value={form.temperature}
                                        onChange={handleUpdateForm}
                                        className="w-full"
                                    />
                                    <div className="flex justify-between text-xs text-gray-500 mt-1">
                                        <span>精确</span>
                                        <span>平衡</span>
                                        <span>创意</span>
                                    </div>
                                </div>
                            ) : (
                                <div className="px-3 py-2 border border-gray-200 rounded-md bg-gray-50">
                                    {workflow.temperature}
                                </div>
                            )}
                        </div>
                    </div>

                    <div>
                        <label htmlFor="max_tokens" className="block text-sm font-medium text-gray-700 mb-1">
                            最大Token数
                        </label>
                        {isEditing ? (
                            <input
                                type="number"
                                id="max_tokens"
                                name="max_tokens"
                                value={form.max_tokens}
                                onChange={handleUpdateForm}
                                min="256"
                                max="8192"
                                step="256"
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                        ) : (
                            <div className="px-3 py-2 border border-gray-200 rounded-md bg-gray-50">
                                {workflow.max_tokens}
                            </div>
                        )}
                    </div>

                    <div className="space-y-3">
                        <div className="flex items-center">
                            {isEditing ? (
                                <input
                                    type="checkbox"
                                    id="agent_enabled"
                                    name="agent_enabled"
                                    checked={form.agent_enabled}
                                    onChange={handleUpdateBoolForm}
                                    className="h-4 w-4 text-blue-500 focus:ring-blue-400 border-gray-300 rounded"
                                />
                            ) : (
                                <div className={`h-4 w-4 rounded ${workflow.agent_enabled ? 'bg-blue-500' : 'bg-gray-300'}`}></div>
                            )}
                            <label htmlFor="agent_enabled" className="ml-2 block text-sm text-gray-700">
                                启用代理能力（允许工作流节点自主执行和调用工具）
                            </label>
                        </div>

                        <div className="flex items-center">
                            {isEditing ? (
                                <input
                                    type="checkbox"
                                    id="enable_streaming"
                                    name="enable_streaming"
                                    checked={form.enable_streaming}
                                    onChange={handleUpdateBoolForm}
                                    className="h-4 w-4 text-blue-500 focus:ring-blue-400 border-gray-300 rounded"
                                />
                            ) : (
                                <div className={`h-4 w-4 rounded ${workflow.enable_streaming ? 'bg-blue-500' : 'bg-gray-300'}`}></div>
                            )}
                            <label htmlFor="enable_streaming" className="ml-2 block text-sm text-gray-700">
                                启用流式响应（实时生成内容）
                            </label>
                        </div>
                    </div>

                    <div className="border-t pt-4 mt-6">
                        <div className="text-sm text-gray-500">
                            <p>创建者: {workflow.created_by}</p>
                            <p>创建时间: {formatDate(workflow.created_at)}</p>
                            <p>最后更新: {formatDate(workflow.updated_at)}</p>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

export default WorkflowDetail 