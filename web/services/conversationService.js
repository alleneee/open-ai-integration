import { API_BASE_URL, STREAM_TIMEOUT } from '../config'

// 发送消息并处理流式响应
export const sendMessage = async (conversationId, message, callbacks) => {
    const { onData, onCompleted, onError } = callbacks

    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/conversations/generate/stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({
                conversation_id: conversationId,
                message,
                stream: true
            })
        })

        if (!response.ok)
            throw new Error('请求失败')

        const reader = response.body.getReader()
        const decoder = new TextDecoder('utf-8')
        let buffer = ''

        // 处理流式响应
        const read = async () => {
            const { done, value } = await reader.read()

            if (done) {
                onCompleted()
                return
            }

            buffer += decoder.decode(value, { stream: true })
            const lines = buffer.split('\n\n')

            lines.forEach(line => {
                if (line.startsWith('data: ')) {
                    try {
                        const jsonData = JSON.parse(line.substring(6))

                        if (jsonData.type === 'chunk') {
                            onData(jsonData.content, false, {
                                conversationId: jsonData.conversation_id,
                                messageId: jsonData.message_id
                            })
                        }
                        else if (jsonData.type === 'done') {
                            // 处理完成事件
                        }
                        else if (jsonData.type === 'error') {
                            onError(jsonData.error)
                        }
                    } catch (e) {
                        // 处理JSON解析错误
                    }
                }
            })

            buffer = lines[lines.length - 1]
            read()
        }

        read()
    } catch (error) {
        onError(error.message)
    }
}

// 发送RAG知识库增强消息
export const sendRagMessage = async (conversationId, message, knowledgeBaseIds, callbacks) => {
    const { onData, onCompleted, onError } = callbacks

    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/conversations/rag/stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({
                conversation_id: conversationId,
                message,
                knowledge_base_ids: knowledgeBaseIds,
                stream: true
            })
        })

        if (!response.ok)
            throw new Error('请求失败')

        const reader = response.body.getReader()
        const decoder = new TextDecoder('utf-8')
        let buffer = ''

        // 处理流式响应
        const read = async () => {
            const { done, value } = await reader.read()

            if (done) {
                onCompleted()
                return
            }

            buffer += decoder.decode(value, { stream: true })
            const lines = buffer.split('\n\n')

            lines.forEach(line => {
                if (line.startsWith('data: ')) {
                    try {
                        const jsonData = JSON.parse(line.substring(6))

                        if (jsonData.type === 'chunk') {
                            onData(jsonData.content, false, {
                                conversationId: jsonData.conversation_id,
                                messageId: jsonData.message_id,
                                sources: jsonData.sources
                            })
                        }
                        else if (jsonData.type === 'done') {
                            // 处理完成事件，包含引用源
                            callbacks.onSources?.(jsonData.sources)
                        }
                        else if (jsonData.type === 'error') {
                            onError(jsonData.error)
                        }
                    } catch (e) {
                        // 处理JSON解析错误
                    }
                }
            })

            buffer = lines[lines.length - 1]
            read()
        }

        read()
    } catch (error) {
        onError(error.message)
    }
}

// 获取对话列表
export const fetchConversations = async (page = 0, limit = 20) => {
    const response = await fetch(`${API_BASE_URL}/api/v1/conversations?skip=${page}&limit=${limit}`, {
        headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
    })

    if (!response.ok)
        throw new Error('获取对话列表失败')

    return response.json()
}

// 获取对话详情
export const fetchConversation = async (conversationId) => {
    const response = await fetch(`${API_BASE_URL}/api/v1/conversations/${conversationId}`, {
        headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
    })

    if (!response.ok)
        throw new Error('获取对话详情失败')

    return response.json()
}

// 创建新对话
export const createConversation = async (data) => {
    const response = await fetch(`${API_BASE_URL}/api/v1/conversations`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(data)
    })

    if (!response.ok)
        throw new Error('创建对话失败')

    return response.json()
}

// 删除对话
export const deleteConversation = async (conversationId) => {
    const response = await fetch(`${API_BASE_URL}/api/v1/conversations/${conversationId}`, {
        method: 'DELETE',
        headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
    })

    if (!response.ok)
        throw new Error('删除对话失败')

    return response.json()
}

// 更新对话
export const updateConversation = async (conversationId, data) => {
    const response = await fetch(`${API_BASE_URL}/api/v1/conversations/${conversationId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(data)
    })

    if (!response.ok)
        throw new Error('更新对话失败')

    return response.json()
} 