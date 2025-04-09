/**
 * 知识库相关类型定义
 */

export interface KnowledgeBase {
    id: string;
    name: string;
    description?: string;
    documentCount: number;
    createdAt?: string;
    updatedAt?: string;
} 