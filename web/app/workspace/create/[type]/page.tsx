'use client'

import React, { useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import WorkspaceLayout from '@/components/Layout/WorkspaceLayout'
import Link from 'next/link'

// 应用类型配置
const APP_TYPES = {
    assistant: {
        name: '聊天助手',
        description: '创建可与用户对话的AI助手',
        icon: (
            <svg className="h-12 w-12 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 10.5h8m-4-4.5v8m.5 5a8.5 8.5 0 110-17 8.5 8.5 0 010 17z" />
            </svg>
        ),
        fields: ['名称', '描述', '系统提示词', '模型', '温度']
    },
    agent: {
        name: 'AI代理',
        description: '创建能主动执行任务的AI代理',
        icon: (
            <svg className="h-12 w-12 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" />
            </svg>
        ),
        fields: ['名称', '描述', '系统提示词', '工具', '模型', '温度']
    },
    workflow: {
        name: '工作流',
        description: '创建自定义的AI工作流',
        icon: (
            <svg className="h-12 w-12 text-purple-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
            </svg>
        ),
        fields: ['名称', '描述', '节点配置', '模型', '温度']
    },
    chatflow: {
        name: '对话流',
        description: '创建引导式的对话流程',
        icon: (
            <svg className="h-12 w-12 text-pink-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 20.25c4.97 0 9-3.694 9-8.25s-4.03-8.25-9-8.25S3 7.444 3 12c0 2.104.859 4.023 2.273 5.48.432.447.74 1.04.586 1.641a4.483 4.483 0 01-.923 1.785A5.969 5.969 0 006 21c1.282 0 2.47-.402 3.445-1.087.81.22 1.668.337 2.555.337z" />
            </svg>
        ),
        fields: ['名称', '描述', '欢迎消息', '节点配置', '模型', '温度']
    }
};

// 工作流节点类型
const WORKFLOW_NODE_TYPES = [
    { id: 'llm', name: 'LLM节点', description: '处理自然语言请求', icon: '🤖' },
    { id: 'tool', name: '工具节点', description: '执行特定功能或API调用', icon: '🔧' },
    { id: 'condition', name: '条件节点', description: '根据条件决定流程走向', icon: '🔀' },
    { id: 'input', name: '输入节点', description: '接收用户输入', icon: '📥' },
    { id: 'output', name: '输出节点', description: '返回结果给用户', icon: '📤' },
    { id: 'knowledge', name: '知识库节点', description: '查询知识库中的信息', icon: '��' }
];

// LLM模型列表
const MODELS = [
    { id: 'gpt-4', name: 'GPT-4', description: 'OpenAI最强大的模型' },
    { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', description: 'OpenAI性能与成本平衡的模型' },
    { id: 'claude-3-opus', name: 'Claude 3 Opus', description: 'Anthropic最强大的模型' },
    { id: 'claude-3-sonnet', name: 'Claude 3 Sonnet', description: 'Anthropic平衡模型' },
    { id: 'local-model', name: '本地模型', description: '使用本地部署的模型' }
];

export default function CreateAppPage() {
    const router = useRouter();
    const params = useParams();
    const appType = typeof params.type === 'string' ? params.type : '';

    const [loading, setLoading] = useState(false);
    const [formData, setFormData] = useState({
        name: '',
        description: '',
        systemPrompt: '',
        welcomeMessage: '',
        model: MODELS[0].id,
        temperature: 0.7,
        initialNodeType: 'llm',  // 初始节点类型
        maxTokens: 2048,         // 最大token数
        agentEnabled: false,     // 是否启用代理能力
        enableStreaming: true    // 是否启用流式响应
    });

    // 检查应用类型是否有效
    if (!APP_TYPES[appType as keyof typeof APP_TYPES]) {
        return (
            <WorkspaceLayout>
                <div className="p-8 text-center">
                    <div className="text-red-500 text-xl mb-4">未知的应用类型: {appType}</div>
                    <Link
                        href="/workspace"
                        className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition"
                    >
                        返回工作室
                    </Link>
                </div>
            </WorkspaceLayout>
        );
    }

    const appTypeInfo = APP_TYPES[appType as keyof typeof APP_TYPES];

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleChangeBool = (e: React.ChangeEvent<HTMLInputElement>) => {
        const { name, checked } = e.target;
        setFormData(prev => ({ ...prev, [name]: checked }));
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!formData.name.trim()) {
            alert(`请输入${appTypeInfo.name}名称`);
            return;
        }

        try {
            setLoading(true);
            // TODO: 实际创建应用的API调用
            console.log('创建应用:', { type: appType, ...formData });

            // 模拟API调用延迟
            await new Promise(resolve => setTimeout(resolve, 1000));

            // 成功后跳转到工作室
            alert('应用创建成功（模拟）');
            router.push('/workspace');
        } catch (error) {
            console.error('创建应用失败:', error);
            alert('创建应用失败，请重试');
        } finally {
            setLoading(false);
        }
    };

    return (
        <WorkspaceLayout>
            <div className="mb-6 flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">创建{appTypeInfo.name}</h1>
                    <p className="mt-1 text-sm text-gray-500">
                        {appTypeInfo.description}
                    </p>
                </div>
                <Link
                    href="/workspace"
                    className="px-4 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50 transition"
                >
                    返回工作室
                </Link>
            </div>

            <div className="bg-white rounded-lg shadow overflow-hidden">
                <div className="p-4 border-b border-gray-200 flex items-center">
                    <div className="mr-3">
                        {appTypeInfo.icon}
                    </div>
                    <div>
                        <h2 className="text-lg font-medium">{appTypeInfo.name}配置</h2>
                        <p className="text-sm text-gray-500">设置应用的基本信息和参数</p>
                    </div>
                </div>

                <form onSubmit={handleSubmit} className="p-6 space-y-6">
                    <div>
                        <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
                            应用名称 <span className="text-red-500">*</span>
                        </label>
                        <input
                            type="text"
                            id="name"
                            name="name"
                            value={formData.name}
                            onChange={handleChange}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            placeholder={`输入${appTypeInfo.name}名称`}
                            required
                        />
                    </div>

                    <div>
                        <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
                            应用描述
                        </label>
                        <textarea
                            id="description"
                            name="description"
                            value={formData.description}
                            onChange={handleChange}
                            rows={3}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            placeholder="描述这个应用的用途和特点"
                        />
                    </div>

                    {/* 根据不同应用类型显示不同的配置字段 */}
                    {appType === 'assistant' || appType === 'agent' ? (
                        <div>
                            <label htmlFor="systemPrompt" className="block text-sm font-medium text-gray-700 mb-1">
                                系统提示词
                            </label>
                            <textarea
                                id="systemPrompt"
                                name="systemPrompt"
                                value={formData.systemPrompt}
                                onChange={handleChange}
                                rows={4}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                placeholder="设置模型的行为和角色定位"
                            />
                            <p className="mt-1 text-xs text-gray-500">
                                系统提示词用于定义AI的行为、能力和限制，不会直接展示给最终用户
                            </p>
                        </div>
                    ) : null}

                    {appType === 'chatflow' && (
                        <div>
                            <label htmlFor="welcomeMessage" className="block text-sm font-medium text-gray-700 mb-1">
                                欢迎消息
                            </label>
                            <textarea
                                id="welcomeMessage"
                                name="welcomeMessage"
                                value={formData.welcomeMessage}
                                onChange={handleChange}
                                rows={3}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                placeholder="用户进入对话时显示的第一条消息"
                            />
                        </div>
                    )}

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                            <label htmlFor="model" className="block text-sm font-medium text-gray-700 mb-1">
                                模型
                            </label>
                            <select
                                id="model"
                                name="model"
                                value={formData.model}
                                onChange={handleChange}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            >
                                {MODELS.map(model => (
                                    <option key={model.id} value={model.id}>
                                        {model.name} - {model.description}
                                    </option>
                                ))}
                            </select>
                        </div>

                        <div>
                            <label htmlFor="temperature" className="block text-sm font-medium text-gray-700 mb-1">
                                温度 ({formData.temperature})
                            </label>
                            <input
                                type="range"
                                id="temperature"
                                name="temperature"
                                min="0"
                                max="1"
                                step="0.1"
                                value={formData.temperature}
                                onChange={handleChange}
                                className="w-full"
                            />
                            <div className="flex justify-between text-xs text-gray-500 mt-1">
                                <span>精确</span>
                                <span>平衡</span>
                                <span>创意</span>
                            </div>
                        </div>
                    </div>

                    {appType === 'agent' && (
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                可用工具
                            </label>
                            <div className="border border-gray-300 rounded-md p-4 bg-gray-50">
                                <p className="text-sm text-gray-500">
                                    在此版本中，工具配置尚未实现。实际应用中，这里会列出可用的工具列表供选择。
                                </p>
                            </div>
                        </div>
                    )}

                    {appType === 'workflow' && (
                        <>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    初始节点类型
                                </label>
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                    {WORKFLOW_NODE_TYPES.map(nodeType => (
                                        <div
                                            key={nodeType.id}
                                            className={`p-4 border rounded-md cursor-pointer transition ${formData.initialNodeType === nodeType.id
                                                ? 'border-purple-500 bg-purple-50'
                                                : 'border-gray-200 hover:border-purple-300 hover:bg-gray-50'
                                                }`}
                                            onClick={() => setFormData(prev => ({ ...prev, initialNodeType: nodeType.id }))}
                                        >
                                            <div className="flex items-center">
                                                <span className="text-2xl mr-3">{nodeType.icon}</span>
                                                <div>
                                                    <h3 className="font-medium">{nodeType.name}</h3>
                                                    <p className="text-xs text-gray-500">{nodeType.description}</p>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div>
                                    <label htmlFor="maxTokens" className="block text-sm font-medium text-gray-700 mb-1">
                                        最大Token数 ({formData.maxTokens})
                                    </label>
                                    <input
                                        type="range"
                                        id="maxTokens"
                                        name="maxTokens"
                                        min="256"
                                        max="8192"
                                        step="256"
                                        value={formData.maxTokens}
                                        onChange={handleChange}
                                        className="w-full"
                                    />
                                    <div className="flex justify-between text-xs text-gray-500 mt-1">
                                        <span>较短</span>
                                        <span>适中</span>
                                        <span>较长</span>
                                    </div>
                                </div>
                            </div>

                            <div className="space-y-3 border border-gray-200 rounded-md p-4">
                                <h3 className="font-medium">高级配置</h3>
                                <div className="flex items-center">
                                    <input
                                        type="checkbox"
                                        id="agentEnabled"
                                        name="agentEnabled"
                                        checked={formData.agentEnabled}
                                        onChange={handleChangeBool}
                                        className="h-4 w-4 text-purple-500 focus:ring-purple-400 border-gray-300 rounded"
                                    />
                                    <label htmlFor="agentEnabled" className="ml-2 block text-sm text-gray-700">
                                        启用代理能力（允许工作流节点自主执行和调用工具）
                                    </label>
                                </div>
                                <div className="flex items-center">
                                    <input
                                        type="checkbox"
                                        id="enableStreaming"
                                        name="enableStreaming"
                                        checked={formData.enableStreaming}
                                        onChange={handleChangeBool}
                                        className="h-4 w-4 text-purple-500 focus:ring-purple-400 border-gray-300 rounded"
                                    />
                                    <label htmlFor="enableStreaming" className="ml-2 block text-sm text-gray-700">
                                        启用流式响应（实时生成内容）
                                    </label>
                                </div>
                            </div>

                            <div className="border border-gray-300 rounded-md p-4 bg-gray-50">
                                <div className="flex items-center mb-2">
                                    <svg className="h-5 w-5 text-purple-500 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                    <span className="font-medium">工作流编辑器</span>
                                </div>
                                <p className="text-sm text-gray-500">
                                    工作流节点编辑器将在创建后的详情页面中提供。您可以创建并连接不同类型的节点，自定义工作流程。
                                </p>
                            </div>
                        </>
                    )}

                    <div className="flex justify-end pt-4 border-t">
                        <button
                            type="button"
                            onClick={() => router.push('/workspace')}
                            className="px-4 py-2 text-gray-700 border border-gray-300 rounded-md mr-2 hover:bg-gray-50"
                        >
                            取消
                        </button>
                        <button
                            type="submit"
                            disabled={loading}
                            className={`px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 ${loading ? 'opacity-70 cursor-not-allowed' : ''
                                }`}
                        >
                            {loading ? (
                                <>
                                    <span className="inline-block animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full mr-2"></span>
                                    创建中...
                                </>
                            ) : '创建应用'}
                        </button>
                    </div>
                </form>
            </div>
        </WorkspaceLayout>
    );
} 