'use client'

import React, { ReactNode, useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

interface WorkspaceLayoutProps {
    children: ReactNode;
}

const WorkspaceLayout: React.FC<WorkspaceLayoutProps> = ({ children }) => {
    const pathname = usePathname()
    const [isMenuOpen, setIsMenuOpen] = useState(false)

    const isActive = (path: string) => {
        if (path === '/workspace' && pathname === '/workspace') {
            return true
        }
        if (path !== '/workspace' && pathname?.startsWith(path)) {
            return true
        }
        return false
    }

    const navItems = [
        { path: '/workspace', label: '应用', icon: 'M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5' },
        { path: '/knowledge', label: '知识库', icon: 'M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25' },
        { path: '/workflows', label: '工作流', icon: 'M9.348 14.651a3.75 3.75 0 010-5.303m5.304 0a3.75 3.75 0 010 5.303m-7.425 2.122a6.75 6.75 0 010-9.546m9.546 0a6.75 6.75 0 010 9.546M5.106 18.894c-3.808-3.808-3.808-9.98 0-13.789m13.788 0c3.808 3.808 3.808 9.981 0 13.79M12 12h.008v.007H12V12zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z' },
        { path: '/tools', label: '工具', icon: 'M21.75 6.75a2.25 2.25 0 00-2.25-2.25H4.5a2.25 2.25 0 00-2.25 2.25v10.5a2.25 2.25 0 002.25 2.25h15a2.25 2.25 0 002.25-2.25V6.75zM6 21v-2.25m0 0V15m12 6v-2.25m0 0V15' },
    ]

    return (
        <div className="flex min-h-screen bg-gray-100">
            {/* 侧边栏 - 大屏幕 */}
            <div className="hidden md:flex md:w-64 md:flex-col md:fixed md:inset-y-0">
                <div className="flex-1 flex flex-col min-h-0 border-r border-gray-200 bg-white">
                    <div className="flex-1 flex flex-col pt-5 pb-4 overflow-y-auto">
                        <div className="flex items-center flex-shrink-0 px-4">
                            <h1 className="text-xl font-bold text-blue-600">AI 助手平台</h1>
                        </div>
                        <nav className="mt-5 flex-1 px-2 space-y-1">
                            {navItems.map((item) => (
                                <Link
                                    key={item.path}
                                    href={item.path}
                                    className={`group flex items-center px-2 py-2 text-sm font-medium rounded-md ${isActive(item.path)
                                        ? 'bg-blue-50 text-blue-600'
                                        : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                                        }`}
                                >
                                    <svg
                                        className={`mr-3 h-5 w-5 ${isActive(item.path) ? 'text-blue-500' : 'text-gray-400 group-hover:text-gray-500'
                                            }`}
                                        xmlns="http://www.w3.org/2000/svg"
                                        fill="none"
                                        viewBox="0 0 24 24"
                                        stroke="currentColor"
                                        aria-hidden="true"
                                    >
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={item.icon} />
                                    </svg>
                                    {item.label}
                                </Link>
                            ))}
                        </nav>
                    </div>
                    <div className="flex-shrink-0 flex border-t border-gray-200 p-4">
                        <div className="flex-shrink-0 w-full group block">
                            <div className="flex items-center">
                                <div className="ml-3">
                                    <p className="text-sm font-medium text-gray-700 group-hover:text-gray-900">
                                        用户设置
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* 移动菜单按钮 */}
            <div className="md:hidden fixed top-0 inset-x-0 z-10 flex items-center bg-white border-b border-gray-200 h-16 px-4">
                <button
                    type="button"
                    className="text-gray-500 focus:outline-none"
                    onClick={() => setIsMenuOpen(!isMenuOpen)}
                >
                    <svg
                        className="h-6 w-6"
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        aria-hidden="true"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M4 6h16M4 12h16M4 18h16"
                        />
                    </svg>
                </button>
                <h1 className="ml-4 text-lg font-bold text-blue-600">AI 助手平台</h1>
            </div>

            {/* 移动菜单 */}
            {isMenuOpen && (
                <div className="md:hidden fixed inset-0 z-20 bg-black bg-opacity-50" onClick={() => setIsMenuOpen(false)}>
                    <div className="fixed inset-y-0 left-0 w-64 bg-white shadow-lg" onClick={(e) => e.stopPropagation()}>
                        <div className="flex-1 flex flex-col min-h-0">
                            <div className="flex-1 flex flex-col pt-5 pb-4 overflow-y-auto">
                                <div className="flex items-center justify-between flex-shrink-0 px-4">
                                    <h1 className="text-xl font-bold text-blue-600">AI 助手平台</h1>
                                    <button
                                        type="button"
                                        className="ml-1 flex items-center justify-center h-8 w-8 rounded-full focus:outline-none"
                                        onClick={() => setIsMenuOpen(false)}
                                    >
                                        <svg
                                            className="h-6 w-6 text-gray-500"
                                            xmlns="http://www.w3.org/2000/svg"
                                            fill="none"
                                            viewBox="0 0 24 24"
                                            stroke="currentColor"
                                            aria-hidden="true"
                                        >
                                            <path
                                                strokeLinecap="round"
                                                strokeLinejoin="round"
                                                strokeWidth={2}
                                                d="M6 18L18 6M6 6l12 12"
                                            />
                                        </svg>
                                    </button>
                                </div>
                                <nav className="mt-5 flex-1 px-2 space-y-1">
                                    {navItems.map((item) => (
                                        <Link
                                            key={item.path}
                                            href={item.path}
                                            className={`group flex items-center px-2 py-2 text-sm font-medium rounded-md ${isActive(item.path)
                                                ? 'bg-blue-50 text-blue-600'
                                                : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                                                }`}
                                            onClick={() => setIsMenuOpen(false)}
                                        >
                                            <svg
                                                className={`mr-3 h-5 w-5 ${isActive(item.path) ? 'text-blue-500' : 'text-gray-400 group-hover:text-gray-500'
                                                    }`}
                                                xmlns="http://www.w3.org/2000/svg"
                                                fill="none"
                                                viewBox="0 0 24 24"
                                                stroke="currentColor"
                                                aria-hidden="true"
                                            >
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={item.icon} />
                                            </svg>
                                            {item.label}
                                        </Link>
                                    ))}
                                </nav>
                            </div>
                            <div className="flex-shrink-0 flex border-t border-gray-200 p-4">
                                <div className="flex-shrink-0 w-full group block">
                                    <div className="flex items-center">
                                        <div className="ml-3">
                                            <p className="text-sm font-medium text-gray-700 group-hover:text-gray-900">
                                                用户设置
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* 主内容区域 */}
            <div className="md:pl-64 flex flex-col flex-1">
                <main className="flex-1">
                    <div className="py-6">
                        <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8">
                            {children}
                        </div>
                    </div>
                </main>
            </div>
        </div>
    )
}

export default WorkspaceLayout 