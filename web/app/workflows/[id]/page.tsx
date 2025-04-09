'use client'

import React, { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { Edge, Node } from 'reactflow'
import WorkspaceLayout from '../../../components/Layout/WorkspaceLayout'
import WorkflowCanvasProvider from '../../../components/Workflow/WorkflowCanvas'
import { fetchWorkflow, saveWorkflowNodes } from '../../../services/workflowService'
import { BlockEnum } from '../../../types'

export default function WorkflowEditPage() {
    const params = useParams()
    const workflowId = params.id as string
    const [loading, setLoading] = useState(true)
    const [workflow, setWorkflow] = useState<{
        name: string;
        description?: string;
        nodes: Node[];
        edges: Edge[];
    } | null>(null)

    useEffect(() => {
        const loadWorkflow = async () => {
            try {
                setLoading(true)
                const data = await fetchWorkflow(workflowId)
                setWorkflow({
                    name: data.name,
                    description: data.description,
                    nodes: data.nodes as Node[],
                    edges: data.edges as Edge[]
                })
            } catch (error) {
                console.error('加载工作流失败:', error)
            } finally {
                setLoading(false)
            }
        }

        if (workflowId) {
            loadWorkflow()
        }
    }, [workflowId])

    const handleSave = async (nodes: Node[], edges: Edge[]) => {
        try {
            await saveWorkflowNodes(workflowId, nodes, edges)
            alert('工作流保存成功')
        } catch (error) {
            console.error('保存工作流失败:', error)
            alert('工作流保存失败')
        }
    }

    if (loading) {
        return (
            <WorkspaceLayout>
                <div className="flex items-center justify-center h-96">
                    <div className="text-center">
                        <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-indigo-600 border-r-transparent"></div>
                        <p className="mt-2 text-gray-600">正在加载工作流...</p>
                    </div>
                </div>
            </WorkspaceLayout>
        )
    }

    if (!workflow) {
        return (
            <WorkspaceLayout>
                <div className="flex items-center justify-center h-96">
                    <div className="text-center">
                        <div className="text-red-500 text-2xl mb-2">❌</div>
                        <h2 className="text-xl font-bold text-gray-800">未找到工作流</h2>
                        <p className="mt-1 text-gray-600">请检查工作流ID是否正确</p>
                    </div>
                </div>
            </WorkspaceLayout>
        )
    }

    return (
        <WorkspaceLayout>
            <div className="mb-6">
                <h1 className="text-2xl font-bold text-gray-900">{workflow.name}</h1>
                {workflow.description && (
                    <p className="mt-1 text-sm text-gray-500">{workflow.description}</p>
                )}
            </div>

            <div className="bg-white rounded-lg border border-gray-200 h-[calc(100vh-200px)] overflow-hidden">
                <WorkflowCanvasProvider
                    initialNodes={workflow.nodes}
                    initialEdges={workflow.edges}
                    onSave={handleSave}
                />
            </div>
        </WorkspaceLayout>
    )
} 