// types/conversation.d.ts

export interface Message {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    createdAt?: string; // 或 Date 类型
    sources?: any[]; // 引用源，类型可以更具体
    isTemp?: boolean; // 临时消息，用于流式更新
    error?: boolean; // 标记错误消息
}

export interface Conversation {
    id: string;
    title: string;
    createdAt?: string;
    updatedAt?: string;
    // 可以添加其他元数据
}

export interface ConversationDetail extends Conversation {
    messages: Message[];
    // 可以包含其他详情，如LLM配置等
}

export interface ConversationCreate {
    title: string;
    metadata?: Record<string, any>;
}

export interface KnowledgeBase {
    id: string;
    name: string;
    description?: string;
    // 其他知识库相关字段
} 