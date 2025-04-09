'use client'

import React from 'react'
import KnowledgeBaseCreate from '@/components/KnowledgeBase/KnowledgeBaseCreate'
import WorkspaceLayout from '@/components/Layout/WorkspaceLayout'
import Link from 'next/link'

export default function CreateKnowledgeBasePage() {
    return (
        <WorkspaceLayout>
            <div className="mb-6 flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">创建知识库</h1>
                    <p className="mt-1 text-sm text-gray-500">
                        创建新的知识库并上传文档
                    </p>
                </div>
                <Link
                    href="/knowledge"
                    className="px-4 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50 transition"
                >
                    返回列表
                </Link>
            </div>

            <KnowledgeBaseCreate />
        </WorkspaceLayout>
    )
} 