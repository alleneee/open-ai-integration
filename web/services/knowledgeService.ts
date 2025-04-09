import { API_BASE_URL } from '@/config' // 使用别名路径
import type { KnowledgeBase } from '@/types/conversation' // 假设的类型定义

const getAuthHeaders = (): HeadersInit => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    return {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` })
    };
}

// 获取知识库列表
export const fetchKnowledgeBases = async (): Promise<KnowledgeBase[]> => {
    const response = await fetch(`${API_BASE_URL}/api/v1/knowledge-bases`, {
        headers: getAuthHeaders()
    })

    if (!response.ok)
        throw new Error('获取知识库列表失败')

    return response.json()
}

// 获取知识库详情 (如果需要)
export const fetchKnowledgeBase = async (id: string): Promise<KnowledgeBase> => {
    const response = await fetch(`${API_BASE_URL}/api/v1/knowledge-bases/${id}`, {
        headers: getAuthHeaders()
    })

    if (!response.ok)
        throw new Error('获取知识库详情失败')

    return response.json()
}

// 搜索知识库 (如果需要)
interface SearchOptions {
    limit?: number;
    scoreThreshold?: number;
}

export const searchKnowledgeBase = async (
    query: string,
    knowledgeBaseIds: string[],
    options: SearchOptions = {}
): Promise<any[]> => { // 明确返回类型，例如 Document[]
    const { limit = 5, scoreThreshold = 0.5 } = options

    const response = await fetch(`${API_BASE_URL}/api/v1/knowledge-bases/search`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
            query,
            knowledge_base_ids: knowledgeBaseIds,
            top_k: limit,
            score_threshold: scoreThreshold
        })
    })

    if (!response.ok)
        throw new Error('搜索知识库失败')

    return response.json()
} 