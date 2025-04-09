'use client'

import React from 'react'
import { useParams } from 'next/navigation'
import WorkflowDetail from '@/components/Workflow/WorkflowDetail'
import WorkspaceLayout from '@/components/Layout/WorkspaceLayout'
import Link from 'next/link'

export default function WorkflowDetailPage() {
    const params = useParams()
    const workflowId = Array.isArray(params.id) ? params.id[0] : params.id

    return (
        <WorkspaceLayout>
            <div className="mb-6 flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">工作流详情</h1>
                    <p className="mt-1 text-sm text-gray-500">
                        管理工作流配置和节点
                    </p>
                </div>
                <Link
                    href="/workspace"
                    className="px-4 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50 transition"
                >
                    返回工作室
                </Link>
            </div>

            <WorkflowDetail workflowId={workflowId} />
        </WorkspaceLayout>
    )
} 