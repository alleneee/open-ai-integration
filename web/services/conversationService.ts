import { API_BASE_URL } from '@/config' // 使用别名路径
import type { Conversation, ConversationDetail, Message, ConversationCreate } from '@/types/conversation' // 假设的类型定义

interface Callbacks {
    onData: (chunk: string, isFirstMessage: boolean, info: { conversationId?: string, messageId?: string, sources?: any[] }) => void;
    onCompleted: () => void;
    onError: (error: string) => void;
    onSources?: (sources: any[]) => void; // 用于 RAG 完成时传递 sources
    signal?: AbortSignal; // 添加 signal
}

// 辅助函数处理流式响应
const handleStreamResponse = async (response: Response, callbacks: Callbacks) => {
    const { onData, onCompleted, onError, signal } = callbacks

    if (!response.body) {
        throw new Error('Response body is null');
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    // 监听 abort 事件
    signal?.addEventListener('abort', () => {
        reader.cancel()
        console.log('Stream reading aborted.');
    });

    try {
        while (true) {
            if (signal?.aborted) {
                throw new Error('Operation aborted');
            }

            const { done, value } = await reader.read()
            if (done) {
                break;
            }

            buffer += decoder.decode(value, { stream: true })
            const lines = buffer.split('\n\n')
            buffer = lines.pop() || '' // 保留不完整的行

            for (const line of lines) {
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
                            callbacks.onSources?.(jsonData.sources)
                        }
                        else if (jsonData.type === 'error') {
                            onError(jsonData.error)
                            return; // 出错时停止处理
                        }
                    } catch (e: any) {
                        console.error('Error parsing stream data:', e);
                        onError('Error parsing stream data');
                        return; // 解析错误时停止处理
                    }
                }
            }
        }
        onCompleted()
    } catch (error: any) {
        if (error.name !== 'AbortError') {
            console.error('Stream reading error:', error);
            onError(error.message || 'Stream reading failed');
        }
    } finally {
        reader.releaseLock();
    }
};

const getAuthHeaders = (): HeadersInit => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    return {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` })
    };
}

// 发送普通消息
export const sendMessage = async (
    conversationId: string | undefined,
    message: string,
    callbacks: Callbacks
): Promise<void> => {
    const { signal } = callbacks;
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/conversations/generate/stream`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                conversation_id: conversationId,
                message,
                stream: true
            }),
            signal: signal // 传递 signal
        })

        if (!response.ok)
            throw new Error(`请求失败: ${response.statusText}`);

        await handleStreamResponse(response, callbacks);

    } catch (error: any) {
        if (error.name !== 'AbortError') {
            console.error('SendMessage failed:', error);
            callbacks.onError(error.message || 'Failed to send message');
        }
    }
}

// 发送RAG知识库增强消息
export const sendRagMessage = async (
    conversationId: string | undefined,
    message: string,
    knowledgeBaseIds: string[],
    callbacks: Callbacks
): Promise<void> => {
    const { signal } = callbacks;
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/conversations/rag/stream`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                conversation_id: conversationId,
                message,
                knowledge_base_ids: knowledgeBaseIds,
                stream: true
            }),
            signal: signal // 传递 signal
        })

        if (!response.ok)
            throw new Error(`请求失败: ${response.statusText}`);

        await handleStreamResponse(response, callbacks);

    } catch (error: any) {
        if (error.name !== 'AbortError') {
            console.error('SendRagMessage failed:', error);
            callbacks.onError(error.message || 'Failed to send RAG message');
        }
    }
}

// 获取对话列表
export const fetchConversations = async (page: number = 0, limit: number = 20): Promise<Conversation[]> => {
    console.log(`正在获取对话列表，API_BASE_URL: ${API_BASE_URL}`);

    try {
        const url = `${API_BASE_URL}/api/v1/conversations?skip=${page}&limit=${limit}`;
        console.log(`请求URL: ${url}`);
        console.log(`请求头: ${JSON.stringify(getAuthHeaders())}`);

        const response = await fetch(url, {
            headers: getAuthHeaders()
        });

        console.log(`响应状态: ${response.status} ${response.statusText}`);

        if (!response.ok) {
            console.error(`获取对话列表失败: ${response.status} ${response.statusText}`);
            const errorText = await response.text();
            console.error(`错误详情: ${errorText}`);
            throw new Error('获取对话列表失败');
        }

        const data = await response.json();
        console.log(`获取到 ${data.length} 个对话`);
        return data;
    } catch (error) {
        console.error('获取对话列表出错:', error);
        throw error;
    }
}

// 获取对话详情
export const fetchConversation = async (conversationId: string): Promise<ConversationDetail> => {
    const response = await fetch(`${API_BASE_URL}/api/v1/conversations/${conversationId}`, {
        headers: getAuthHeaders()
    })

    if (!response.ok)
        throw new Error('获取对话详情失败')

    return response.json()
}

// 创建新对话
export const createConversation = async (data: ConversationCreate): Promise<Conversation> => {
    console.log(`正在创建对话，API_BASE_URL: ${API_BASE_URL}，数据:`, data);

    try {
        const url = `${API_BASE_URL}/api/v1/conversations`;
        console.log(`请求URL: ${url}`);
        console.log(`请求头: ${JSON.stringify(getAuthHeaders())}`);

        const response = await fetch(url, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(data)
        });

        console.log(`响应状态: ${response.status} ${response.statusText}`);

        if (!response.ok) {
            console.error(`创建对话失败: ${response.status} ${response.statusText}`);
            const errorText = await response.text();
            console.error(`错误详情: ${errorText}`);
            throw new Error('创建对话失败');
        }

        const result = await response.json();
        console.log('创建对话成功:', result);
        return result;
    } catch (error) {
        console.error('创建对话出错:', error);
        throw error;
    }
}

// 删除对话
export const deleteConversation = async (conversationId: string): Promise<{ message: string }> => {
    const response = await fetch(`${API_BASE_URL}/api/v1/conversations/${conversationId}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
    })

    if (!response.ok)
        throw new Error('删除对话失败')

    return response.json()
}

// 更新对话
export const updateConversation = async (conversationId: string, data: Partial<ConversationCreate>): Promise<Conversation> => {
    const response = await fetch(`${API_BASE_URL}/api/v1/conversations/${conversationId}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(data)
    })

    if (!response.ok)
        throw new Error('更新对话失败')

    return response.json()
} 