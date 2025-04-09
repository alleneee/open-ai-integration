'use client'

import React, { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Edge, Node } from 'reactflow'
import WorkspaceLayout from '../../../components/Layout/WorkspaceLayout'
import WorkflowCanvasProvider from '../../../components/Workflow/WorkflowCanvas'
import { createWorkflow, saveWorkflowNodes } from '../../../services/workflowService'
import { BlockEnum } from '../../../types'

export default function CreateWorkflowPage() {
    const router = useRouter()
    const [name, setName] = useState('新工作流')
    const [description, setDescription] = useState('描述你的工作流程...')
    const [saving, setSaving] = useState(false)

    // 初始节点 - 简单的开始节点
    const initialNodes: Node[] = [
        {
            id: 'start-node',
            type: 'input',
            position: { x: 250, y: 5 },
            data: {
                label: '开始',
                type: BlockEnum.Start,
                icon: '📥',
                color: '#3B82F6'
            },
        }
    ]

    const initialEdges: Edge[] = []

    const handleSave = async (nodes: Node[], edges: Edge[]) => {
        try {
            setSaving(true)
            // 创建工作流
            const newWorkflow = await createWorkflow({
                name,
                description,
                model: 'gpt-3.5-turbo',
                temperature: 0.7,
                max_tokens: 2048,
                agent_enabled: false,
                enable_streaming: true
            })

            // 保存节点和边
            await saveWorkflowNodes(newWorkflow.id, nodes, edges)

            // 导航到新创建的工作流
            router.push(`/workflows/${newWorkflow.id}`)
        } catch (error) {
            console.error('创建工作流失败:', error)
            alert('工作流创建失败')
            setSaving(false)
        }
    }

    return (
        <WorkspaceLayout>
            <div className="mb-6 flex justify-between items-center">
                <div>
                    <input
                        type="text"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        className="text-2xl font-bold text-gray-900 border-0 border-b border-transparent focus:border-indigo-500 focus:ring-0 bg-transparent p-0"
                        placeholder="工作流名称"
                    />
                    <textarea
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                        className="mt-1 w-full text-sm text-gray-500 border-0 border-b border-transparent focus:border-indigo-500 focus:ring-0 bg-transparent p-0 resize-none"
                        placeholder="描述你的工作流程..."
                        rows={2}
                    />
                </div>
                <button
                    onClick={() => router.push('/workflows')}
                    className="px-3 py-1.5 border border-gray-300 bg-white text-gray-700 rounded-md hover:bg-gray-50 shadow-sm text-sm"
                >
                    取消
                </button>
            </div>

            <div className="bg-white rounded-lg border border-gray-200 h-[calc(100vh-250px)] overflow-hidden">
                <WorkflowCanvasProvider
                    initialNodes={initialNodes}
                    initialEdges={initialEdges}
                    onSave={handleSave}
                />
            </div>

            {saving && (
                <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-30 z-50">
                    <div className="bg-white p-6 rounded-lg shadow-xl">
                        <div className="flex items-center">
                            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-indigo-600 border-r-transparent mr-3"></div>
                            <p className="text-gray-800">正在创建工作流...</p>
                        </div>
                    </div>
                </div>
            )}
        </WorkspaceLayout>
    )
} 