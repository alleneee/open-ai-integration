'use client'

import React from 'react'
import KnowledgeBaseList from '@/components/KnowledgeBase/KnowledgeBaseList'
import WorkspaceLayout from '@/components/Layout/WorkspaceLayout'

export default function KnowledgeBasePage() {
    return (
        <WorkspaceLayout>
            <div className="mb-6">
                <h1 className="text-2xl font-bold text-gray-900">知识库</h1>
                <p className="mt-1 text-sm text-gray-500">
                    管理您的知识库，上传文档并用于增强AI回复
                </p>
            </div>

            <KnowledgeBaseList />
        </WorkspaceLayout>
    )
} 