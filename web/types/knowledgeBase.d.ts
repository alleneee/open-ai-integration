/**
 * 知识库相关类型定义
 */

export interface KnowledgeBase {
    id: string;
    name: string;
    description?: string;
    created_at: string;
    updated_at: string;
    document_count: number;
    status: 'ready' | 'processing' | 'error';
    embedding_model?: string;
    retrieval_type?: string;
    created_by: string;
}

export interface KnowledgeBaseCreate {
    name: string;
    description?: string;
    embedding_model?: string;
    retrieval_type?: string;
}

export interface KnowledgeBaseUpdate {
    name?: string;
    description?: string;
    embedding_model?: string;
    retrieval_type?: string;
}

export interface Document {
    id: string;
    name: string;
    knowledge_base_id: string;
    status: 'pending' | 'processing' | 'completed' | 'error';
    error_message?: string;
    created_at: string;
    updated_at: string;
    size_bytes: number;
    mime_type: string;
    tokens: number;
    chunks: number;
    words: number;
    pages?: number;
    segment_count?: number;
    segment_status?: 'completed' | 'processing' | 'error';
}

export interface DocumentUpload {
    file: File;
    metadata?: Record<string, any>;
}

export interface UploadResponse {
    document_id: string;
    name: string;
    status: 'pending' | 'processing' | 'completed' | 'error';
}

export interface Segment {
    id: string;
    document_id: string;
    content: string;
    vector_id?: string;
    position: number;
    created_at: string;
    tokens: number;
    keywords?: string[];
    metadata?: Record<string, any>;
}

export interface ChunkingConfig {
    chunk_size?: number;
    chunk_overlap?: number;
    separator?: string;
}

export interface SearchParams {
    query: string;
    top_k?: number;
    score_threshold?: number;
}

export interface SearchResult {
    segment: Segment;
    score: number;
    document: {
        id: string;
        name: string;
    };
} 