import { API_BASE_URL } from '@/config'
import type {
    KnowledgeBase,
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    Document,
    UploadResponse,
    SearchParams,
    SearchResult
} from '@/types/knowledgeBase'

// 获取认证头
const getAuthHeaders = (): HeadersInit => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    return {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` })
    };
}

// 获取认证头（无Content-Type，用于文件上传）
const getAuthHeadersWithoutContentType = (): HeadersInit => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    return {
        ...(token && { 'Authorization': `Bearer ${token}` })
    };
}

// 获取知识库列表
export const fetchKnowledgeBases = async (page: number = 0, limit: number = 20): Promise<KnowledgeBase[]> => {
    console.log(`获取知识库列表，API_BASE_URL: ${API_BASE_URL}`);

    try {
        const url = `${API_BASE_URL}/api/v1/knowledge-bases?skip=${page}&limit=${limit}`;
        console.log(`请求URL: ${url}`);

        const response = await fetch(url, {
            headers: getAuthHeaders()
        });

        console.log(`响应状态: ${response.status} ${response.statusText}`);

        if (!response.ok) {
            console.error(`获取知识库列表失败: ${response.status} ${response.statusText}`);
            const errorText = await response.text();
            console.error(`错误详情: ${errorText}`);
            throw new Error('获取知识库列表失败');
        }

        const data = await response.json();
        console.log(`获取到 ${data.length} 个知识库`);
        return data;
    } catch (error) {
        console.error('获取知识库列表出错:', error);
        throw error;
    }
}

// 获取知识库详情
export const fetchKnowledgeBase = async (knowledgeBaseId: string): Promise<KnowledgeBase> => {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/knowledge-bases/${knowledgeBaseId}`, {
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error(`获取知识库详情失败: ${errorText}`);
            throw new Error('获取知识库详情失败');
        }

        return response.json();
    } catch (error) {
        console.error('获取知识库详情出错:', error);
        throw error;
    }
}

// 创建知识库
export const createKnowledgeBase = async (data: KnowledgeBaseCreate): Promise<KnowledgeBase> => {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/knowledge-bases`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error(`创建知识库失败: ${errorText}`);
            throw new Error('创建知识库失败');
        }

        return response.json();
    } catch (error) {
        console.error('创建知识库出错:', error);
        throw error;
    }
}

// 更新知识库
export const updateKnowledgeBase = async (knowledgeBaseId: string, data: KnowledgeBaseUpdate): Promise<KnowledgeBase> => {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/knowledge-bases/${knowledgeBaseId}`, {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error(`更新知识库失败: ${errorText}`);
            throw new Error('更新知识库失败');
        }

        return response.json();
    } catch (error) {
        console.error('更新知识库出错:', error);
        throw error;
    }
}

// 删除知识库
export const deleteKnowledgeBase = async (knowledgeBaseId: string): Promise<{ message: string }> => {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/knowledge-bases/${knowledgeBaseId}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error(`删除知识库失败: ${errorText}`);
            throw new Error('删除知识库失败');
        }

        return response.json();
    } catch (error) {
        console.error('删除知识库出错:', error);
        throw error;
    }
}

// 获取知识库的文档列表
export const fetchDocuments = async (knowledgeBaseId: string, page: number = 0, limit: number = 20): Promise<Document[]> => {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/knowledge-bases/${knowledgeBaseId}/documents?skip=${page}&limit=${limit}`, {
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error(`获取文档列表失败: ${errorText}`);
            throw new Error('获取文档列表失败');
        }

        return response.json();
    } catch (error) {
        console.error('获取文档列表出错:', error);
        throw error;
    }
}

// 上传文档
export const uploadDocument = async (knowledgeBaseId: string, file: File, metadata?: Record<string, any>): Promise<UploadResponse> => {
    try {
        const formData = new FormData();
        formData.append('file', file);

        if (metadata) {
            formData.append('metadata', JSON.stringify(metadata));
        }

        const response = await fetch(`${API_BASE_URL}/api/v1/knowledge-bases/${knowledgeBaseId}/documents`, {
            method: 'POST',
            headers: getAuthHeadersWithoutContentType(),
            body: formData
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error(`上传文档失败: ${errorText}`);
            throw new Error('上传文档失败');
        }

        return response.json();
    } catch (error) {
        console.error('上传文档出错:', error);
        throw error;
    }
}

// 删除文档
export const deleteDocument = async (knowledgeBaseId: string, documentId: string): Promise<{ message: string }> => {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/knowledge-bases/${knowledgeBaseId}/documents/${documentId}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error(`删除文档失败: ${errorText}`);
            throw new Error('删除文档失败');
        }

        return response.json();
    } catch (error) {
        console.error('删除文档出错:', error);
        throw error;
    }
}

// 搜索知识库
export const searchKnowledgeBase = async (knowledgeBaseId: string, params: SearchParams): Promise<SearchResult[]> => {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/knowledge-bases/${knowledgeBaseId}/search`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(params)
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error(`搜索知识库失败: ${errorText}`);
            throw new Error('搜索知识库失败');
        }

        return response.json();
    } catch (error) {
        console.error('搜索知识库出错:', error);
        throw error;
    }
} 