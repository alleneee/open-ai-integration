'use client'

import React, { useState, useRef, useEffect } from 'react'
// import ConversationInput from './ConversationInput' // 旧的输入框
import LexicalInput from './LexicalInput' // 新的 Lexical 输入框
import MessageList from './MessageList' // 调整路径
import KnowledgeBaseSelector from './KnowledgeBaseSelector' // 调整路径
import { sendMessage, sendRagMessage } from '@/services/conversationService' // 使用别名路径
import { fetchKnowledgeBases } from '@/services/knowledgeService' // 使用别名路径
import { TEXT_GENERATION_TIMEOUT_MS } from '@/config' // 使用别名路径
import type { ConversationDetail, Message, KnowledgeBase } from '@/types/conversation' // 假设的类型定义

interface ChatProps {
    conversation: ConversationDetail | null;
}

const Chat: React.FC<ChatProps> = ({ conversation }) => {
    const [messages, setMessages] = useState<Message[]>([])
    const [isResponding, setIsResponding] = useState(false)
    const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([])
    const [selectedKBs, setSelectedKBs] = useState<string[]>([])
    const abortControllerRef = useRef<AbortController | null>(null)

    useEffect(() => {
        // 加载知识库列表
        const loadKnowledgeBases = async () => {
            try {
                const data = await fetchKnowledgeBases()
                setKnowledgeBases(data)
            } catch (error) {
                console.error('加载知识库列表失败:', error)
                // 添加用户反馈
            }
        }

        loadKnowledgeBases()
    }, [])

    useEffect(() => {
        // 加载对话历史
        if (conversation?.messages) {
            setMessages(conversation.messages)
        } else {
            setMessages([])
        }
        // 取消之前的请求（如果存在）
        abortControllerRef.current?.abort()
        setIsResponding(false)
    }, [conversation])

    // 处理发送消息
    const handleSend = async (content: string) => {
        if (isResponding) {
            console.log('等待上一条消息响应完成')
            return
        }

        setIsResponding(true)
        // 创建新的 AbortController
        abortControllerRef.current = new AbortController();
        const signal = abortControllerRef.current.signal;

        // 添加用户消息到界面
        const userMessage: Message = { role: 'user', content, id: Date.now().toString() }
        setMessages(prev => [...prev, userMessage])

        // 设置超时 (Next.js 环境下建议用 signal 来处理超时/取消)
        // const timeoutId = setTimeout(() => {...}, TEXT_GENERATION_TIMEOUT_MS);

        // 调用流式API
        try {
            let assistantContent = ''
            let sources: any[] = [] // 明确类型

            const callbacks = {
                onData: (chunk: string, _: boolean, info: { sources?: any[] }) => {
                    if (signal.aborted) return;
                    assistantContent += chunk
                    if (info.sources) {
                        sources = info.sources
                    }
                    setMessages(prev => {
                        const newMessages = [...prev]
                        const assistantMsgIndex = newMessages.findIndex(m => m.role === 'assistant' && m.isTemp)
                        if (assistantMsgIndex !== -1) {
                            newMessages[assistantMsgIndex] = {
                                ...newMessages[assistantMsgIndex],
                                content: assistantContent,
                                sources
                            }
                            return newMessages
                        } else {
                            return [...prev, {
                                role: 'assistant',
                                content: assistantContent,
                                id: `assistant-${Date.now()}`,
                                isTemp: true,
                                sources
                            }]
                        }
                    })
                },
                onCompleted: () => {
                    if (signal.aborted) return;
                    setMessages(prev => prev.map(m =>
                        m.isTemp ? { ...m, isTemp: false } : m
                    ))
                    setIsResponding(false)
                    abortControllerRef.current = null;
                },
                onError: (error: string) => {
                    if (signal.aborted) return;
                    console.error('消息生成错误:', error)
                    setMessages(prev => {
                        const lastMsg = prev[prev.length - 1]
                        if (lastMsg?.role === 'assistant' && lastMsg.isTemp) {
                            return [...prev.slice(0, -1), {
                                ...lastMsg,
                                content: lastMsg.content + `\n\n[生成错误: ${error}]`,
                                isTemp: false,
                                error: true
                            }]
                        }
                        return [...prev, {
                            role: 'assistant',
                            content: `生成错误: ${error}`,
                            id: `assistant-${Date.now()}`,
                            error: true
                        }]
                    })
                    setIsResponding(false)
                    abortControllerRef.current = null;
                },
                // 传递 AbortSignal
                signal: signal
            };

            // 使用RAG API还是普通对话API
            if (selectedKBs.length > 0) {
                await sendRagMessage(
                    conversation?.id,
                    content,
                    selectedKBs,
                    callbacks
                );
            } else {
                await sendMessage(
                    conversation?.id,
                    content,
                    callbacks
                );
            }
        } catch (error: any) {
            if (error.name !== 'AbortError' && !signal.aborted) {
                console.error('发送消息错误:', error)
                setMessages(prev => [...prev, {
                    role: 'assistant',
                    content: `发送消息错误: ${error.message}`,
                    id: `assistant-${Date.now()}`,
                    error: true
                }])
                setIsResponding(false)
                abortControllerRef.current = null;
            }
        }
    }

    return (
        <div className="flex flex-col h-full">
            <KnowledgeBaseSelector
                knowledgeBases={knowledgeBases}
                selectedKBs={selectedKBs}
                onSelectionChange={setSelectedKBs}
            />
            <div className="flex-1 overflow-y-auto"> {/* 将滚动移到这里 */}
                <MessageList messages={messages} />
            </div>
            <LexicalInput
                onSend={handleSend}
                disabled={isResponding}
            />
        </div>
    )
}

export default Chat 