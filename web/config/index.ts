// config/index.ts
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
export const DEFAULT_SYSTEM_PROMPT = '你是一个有用的AI助手。'
export const STREAM_TIMEOUT = 60000 // 60秒
export const TEXT_GENERATION_TIMEOUT_MS = 60000 // 60秒 