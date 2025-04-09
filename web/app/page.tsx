'use client' // 由于使用了useState等hook，需要标记为客户端组件

import Link from 'next/link'

export default function HomePage() {
    return (
        <div className="app-container h-screen flex flex-col">
            <header className="bg-blue-600 text-white p-4">
                <div className="max-w-7xl mx-auto flex justify-between items-center">
                    <h1 className="text-xl font-bold">AI 聊天助手</h1>
                    <div className="space-x-4">
                        <Link href="/workspace" className="px-3 py-1 border border-white rounded-md hover:bg-blue-500 transition">
                            工作室
                        </Link>
                        <Link href="/knowledge" className="px-3 py-1 border border-white rounded-md hover:bg-blue-500 transition">
                            知识库
                        </Link>
                    </div>
                </div>
            </header>
            <main className="flex-1 flex items-center justify-center bg-gray-50">
                <div className="text-center p-8 bg-white rounded-lg shadow-md max-w-2xl mx-auto">
                    <h2 className="text-3xl font-bold text-gray-800 mb-4">欢迎使用AI助手平台</h2>
                    <p className="text-lg text-gray-600 mb-8">
                        一站式AI应用开发和知识库管理平台
                    </p>
                    <div className="flex flex-col sm:flex-row justify-center gap-4">
                        <Link
                            href="/workspace"
                            className="px-6 py-3 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 transition"
                        >
                            进入工作室
                        </Link>
                        <Link
                            href="/knowledge"
                            className="px-6 py-3 bg-white text-blue-600 font-medium rounded-md border border-blue-600 hover:bg-blue-50 transition"
                        >
                            管理知识库
                        </Link>
                    </div>
                </div>
            </main>
            <footer className="bg-gray-800 text-white p-4 text-center text-sm">
                <p>&copy; {new Date().getFullYear()} AI助手平台. 保留所有权利。</p>
            </footer>
        </div>
    );
} 