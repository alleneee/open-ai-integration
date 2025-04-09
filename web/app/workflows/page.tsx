'use client'

import React from 'react'
import WorkflowList from '@/components/Workflow/WorkflowList'
import WorkspaceLayout from '@/components/Layout/WorkspaceLayout'

export default function WorkflowsPage() {
    return (
        <WorkspaceLayout>
            <div className="mb-6">
                <h1 className="text-2xl font-bold text-gray-900">工作流</h1>
                <p className="mt-1 text-sm text-gray-500">
                    管理和创建AI工作流，自定义处理流程和任务编排
                </p>
            </div>

            <WorkflowList />
        </WorkspaceLayout>
    )
} 