'use client'

import React, { useState, useEffect } from 'react'
import { Node } from 'reactflow'
import { BlockEnum } from '../../types' // 使用从types目录导入

// 移除临时的 BlockEnum
// enum BlockEnum { ... }

interface NodeEditorProps {
    node: Node
    onUpdate: (id: string, data: any) => void
    onClose: () => void
}

const NodeEditor: React.FC<NodeEditorProps> = ({ node, onUpdate, onClose }) => {
    const [formData, setFormData] = useState<{
        label: string
        desc: string
        [key: string]: any
    }>({
        label: node.data.label || '',
        desc: node.data.desc || '',
        ...node.data,
    })

    useEffect(() => {
        setFormData({
            label: node.data.label || '',
            desc: node.data.desc || '',
            ...node.data,
        })
    }, [node])

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
        const { name, value } = e.target
        setFormData(prev => ({ ...prev, [name]: value }))
    }

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault()
        onUpdate(node.id, formData)
    }

    return (
        <div className="h-full flex flex-col">
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
                <div className="flex items-center">
                    <div className="w-8 h-8 flex items-center justify-center rounded-md mr-3"
                        style={{ backgroundColor: `${node.data.color}20`, color: node.data.color }}>
                        <span className="text-lg">{node.data.icon}</span>
                    </div>
                    <h3 className="text-lg font-medium text-gray-800">编辑节点</h3>
                </div>
                <button
                    onClick={onClose}
                    className="text-gray-500 hover:text-gray-700 focus:outline-none"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4">
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">节点名称</label>
                        <input
                            name="label"
                            value={formData.label || ''}
                            onChange={handleChange}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
                        <textarea
                            name="desc"
                            value={formData.desc || ''}
                            onChange={handleChange}
                            rows={3}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                        />
                    </div>

                    {/* LLM节点特定设置 */}
                    {node.data.type === BlockEnum.LLM && (
                        <>
                            <div className="bg-gray-50 p-3 rounded-lg border border-gray-200">
                                <h4 className="text-sm font-medium text-gray-800 mb-2 flex items-center">
                                    <span className="w-5 h-5 flex items-center justify-center rounded-md mr-2 text-xs"
                                        style={{ backgroundColor: `${node.data.color}20`, color: node.data.color }}>
                                        🤖
                                    </span>
                                    LLM设置
                                </h4>
                                <div className="space-y-3">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">模型</label>
                                        <select
                                            name="model"
                                            value={formData.model || 'gpt-3.5-turbo'}
                                            onChange={handleChange}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                                        >
                                            <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                                            <option value="gpt-4">GPT-4</option>
                                            <option value="gpt-4-turbo">GPT-4 Turbo</option>
                                            <option value="claude-3">Claude 3</option>
                                        </select>
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">提示词</label>
                                        <textarea
                                            name="prompt"
                                            value={formData.prompt || ''}
                                            onChange={handleChange}
                                            rows={5}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 font-mono text-sm"
                                            placeholder="输入提示词..."
                                        />
                                        <p className="mt-1 text-xs text-gray-500">
                                            提示词将指导模型如何处理输入并生成输出
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </>
                    )}

                    {/* 工具节点特定设置 */}
                    {node.data.type === BlockEnum.Tool && (
                        <div className="bg-gray-50 p-3 rounded-lg border border-gray-200">
                            <h4 className="text-sm font-medium text-gray-800 mb-2 flex items-center">
                                <span className="w-5 h-5 flex items-center justify-center rounded-md mr-2 text-xs"
                                    style={{ backgroundColor: `${node.data.color}20`, color: node.data.color }}>
                                    🔧
                                </span>
                                工具设置
                            </h4>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">工具类型</label>
                                <select
                                    name="toolType"
                                    value={formData.toolType || 'api'}
                                    onChange={handleChange}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                                >
                                    <option value="api">API调用</option>
                                    <option value="code">代码执行</option>
                                    <option value="search">网络搜索</option>
                                </select>
                            </div>
                        </div>
                    )}

                    {/* 条件节点特定设置 */}
                    {node.data.type === BlockEnum.Condition && (
                        <div className="bg-gray-50 p-3 rounded-lg border border-gray-200">
                            <h4 className="text-sm font-medium text-gray-800 mb-2 flex items-center">
                                <span className="w-5 h-5 flex items-center justify-center rounded-md mr-2 text-xs"
                                    style={{ backgroundColor: `${node.data.color}20`, color: node.data.color }}>
                                    🔀
                                </span>
                                条件设置
                            </h4>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">条件表达式</label>
                                <textarea
                                    name="condition"
                                    value={formData.condition || ''}
                                    onChange={handleChange}
                                    rows={3}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 font-mono text-sm"
                                    placeholder="输入条件表达式，例如: result.score > 0.5"
                                />
                                <p className="mt-1 text-xs text-gray-500">
                                    使用JavaScript条件表达式来定义分支路径
                                </p>
                            </div>
                        </div>
                    )}

                    {/* 知识库节点特定设置 */}
                    {node.data.type === BlockEnum.Knowledge && (
                        <div className="bg-gray-50 p-3 rounded-lg border border-gray-200">
                            <h4 className="text-sm font-medium text-gray-800 mb-2 flex items-center">
                                <span className="w-5 h-5 flex items-center justify-center rounded-md mr-2 text-xs"
                                    style={{ backgroundColor: `${node.data.color}20`, color: node.data.color }}>
                                    📚
                                </span>
                                知识库设置
                            </h4>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">选择知识库</label>
                                <select
                                    name="knowledgeBase"
                                    value={formData.knowledgeBase || ''}
                                    onChange={handleChange}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                                >
                                    <option value="">选择知识库...</option>
                                    <option value="kb1">产品文档知识库</option>
                                    <option value="kb2">客户支持知识库</option>
                                </select>
                            </div>
                        </div>
                    )}
                </form>
            </div>

            <div className="border-t border-gray-200 p-4 flex justify-end space-x-3">
                <button
                    type="button"
                    onClick={onClose}
                    className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-md shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                >
                    取消
                </button>
                <button
                    type="button"
                    onClick={handleSubmit}
                    className="px-4 py-2 bg-indigo-600 text-white rounded-md shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                >
                    保存
                </button>
            </div>
        </div>
    )
}

export default NodeEditor 