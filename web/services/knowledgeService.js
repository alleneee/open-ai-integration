import { API_BASE_URL } from '../config'

// 获取知识库列表
export const fetchKnowledgeBases = async () => {
    const response = await fetch(`${API_BASE_URL}/api/v1/knowledge-bases`, {
        headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
    })

    if (!response.ok)
        throw new Error('获取知识库列表失败')

    return response.json()
}

// 获取知识库详情
export const fetchKnowledgeBase = async (id) => {
    const response = await fetch(`${API_BASE_URL}/api/v1/knowledge-bases/${id}`, {
        headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
    })

    if (!response.ok)
        throw new Error('获取知识库详情失败')

    return response.json()
}

// 搜索知识库
export const searchKnowledgeBase = async (query, knowledgeBaseIds, options = {}) => {
    const { limit = 5, scoreThreshold = 0.5 } = options

    const response = await fetch(`${API_BASE_URL}/api/v1/knowledge-bases/search`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
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