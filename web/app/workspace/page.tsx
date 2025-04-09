'use client'

import React from 'react'
import WorkspaceLayout from '@/components/Layout/WorkspaceLayout'
import Link from 'next/link'

// 应用类型
const appTypes = [
    {
        id: 'assistant',
        name: '聊天助手',
        description: '创建可与用户对话的AI助手',
        icon: (
            <svg className="h-8 w-8 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 10.5h8m-4-4.5v8m.5 5a8.5 8.5 0 110-17 8.5 8.5 0 010 17z" />
            </svg>
        )
    },
    {
        id: 'agent',
        name: 'AI代理',
        description: '创建能主动执行任务的AI代理',
        icon: (
            <svg className="h-8 w-8 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" />
            </svg>
        )
    },
    {
        id: 'workflow',
        name: '工作流',
        description: '创建自定义的AI工作流',
        icon: (
            <svg className="h-8 w-8 text-purple-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
            </svg>
        )
    },
    {
        id: 'chatflow',
        name: '对话流',
        description: '创建引导式的对话流程',
        icon: (
            <svg className="h-8 w-8 text-pink-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 20.25c4.97 0 9-3.694 9-8.25s-4.03-8.25-9-8.25S3 7.444 3 12c0 2.104.859 4.023 2.273 5.48.432.447.74 1.04.586 1.641a4.483 4.483 0 01-.923 1.785A5.969 5.969 0 006 21c1.282 0 2.47-.402 3.445-1.087.81.22 1.668.337 2.555.337z" />
            </svg>
        )
    }
]

export default function WorkspacePage() {
    return (
        <WorkspaceLayout>
            <div className="mb-6">
                <h1 className="text-2xl font-bold text-gray-900">应用中心</h1>
                <p className="mt-1 text-sm text-gray-500">
                    管理和创建AI应用
                </p>
            </div>

            <div className="bg-white rounded-lg shadow overflow-hidden">
                <div className="p-4 border-b border-gray-200">
                    <h2 className="text-lg font-medium">创建新应用</h2>
                </div>

                <div className="p-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                        {appTypes.map((type) => (
                            <Link
                                key={type.id}
                                href={`/workspace/create/${type.id}`}
                                className="block p-6 border border-gray-200 rounded-lg hover:border-blue-400 hover:shadow-md transition"
                            >
                                <div className="flex flex-col items-center text-center">
                                    <div className="mb-3">
                                        {type.icon}
                                    </div>
                                    <h3 className="text-lg font-medium text-gray-900 mb-1">{type.name}</h3>
                                    <p className="text-sm text-gray-500">{type.description}</p>
                                </div>
                            </Link>
                        ))}
                    </div>
                </div>
            </div>

            <div className="mt-8 bg-white rounded-lg shadow overflow-hidden">
                <div className="p-4 border-b border-gray-200 flex justify-between items-center">
                    <h2 className="text-lg font-medium">我的应用</h2>
                    <div className="flex space-x-2">
                        <select className="px-3 py-1 border border-gray-300 rounded-md text-sm">
                            <option value="all">所有类型</option>
                            <option value="assistant">聊天助手</option>
                            <option value="agent">AI代理</option>
                            <option value="workflow">工作流</option>
                            <option value="chatflow">对话流</option>
                        </select>
                        <input
                            type="text"
                            placeholder="搜索应用..."
                            className="px-3 py-1 border border-gray-300 rounded-md text-sm w-40"
                        />
                    </div>
                </div>

                <div className="p-8 text-center text-gray-500">
                    <p>暂无应用</p>
                    <p className="mt-1 text-sm">选择上方的应用类型开始创建</p>
                </div>
            </div>
        </WorkspaceLayout>
    )
} 