'use client'

import React from 'react'
import { useParams } from 'next/navigation'
import KnowledgeBaseDetail from '@/components/KnowledgeBase/KnowledgeBaseDetail'
import WorkspaceLayout from '@/components/Layout/WorkspaceLayout'
import Link from 'next/link'

export default function KnowledgeBaseDetailPage() {
    const params = useParams()
    const knowledgeBaseId = Array.isArray(params.id) ? params.id[0] : params.id

    return (
        <WorkspaceLayout>
            <div className="mb-6 flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">知识库详情</h1>
                    <p className="mt-1 text-sm text-gray-500">
                        管理知识库文档和设置
                    </p>
                </div>
                <Link
                    href="/knowledge"
                    className="px-4 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50 transition"
                >
                    返回列表
                </Link>
            </div>

            <KnowledgeBaseDetail knowledgeBaseId={knowledgeBaseId} />
        </WorkspaceLayout>
    )
} 