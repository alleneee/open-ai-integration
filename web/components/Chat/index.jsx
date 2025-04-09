import React, { useState, useRef, useEffect } from 'react'
import ConversationInput from './ConversationInput'
import MessageList from './MessageList'
import KnowledgeBaseSelector from './KnowledgeBaseSelector'
import { sendMessage, sendRagMessage } from '../../services/conversationService'
import { fetchKnowledgeBases } from '../../services/knowledgeService'
import { TEXT_GENERATION_TIMEOUT_MS } from '../../config'

const Chat = ({ conversation }) => {
    const [messages, setMessages] = useState([])
    const [isResponding, setIsResponding] = useState(false)
    const [knowledgeBases, setKnowledgeBases] = useState([])
    const [selectedKBs, setSelectedKBs] = useState([])

    useEffect(() => {
        // 加载知识库列表
        const loadKnowledgeBases = async () => {
            try {
                const data = await fetchKnowledgeBases()
                setKnowledgeBases(data)
            } catch (error) {
                console.error('加载知识库列表失败:', error)
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
    }, [conversation])

    // 处理发送消息
    const handleSend = async (content) => {
        if (isResponding) {
            console.log('等待上一条消息响应完成')
            return
        }

        setIsResponding(true)

        // 添加用户消息到界面
        const userMessage = { role: 'user', content, id: Date.now().toString() }
        setMessages(prev => [...prev, userMessage])

        // 设置超时
        let isTimeout = false
        const timeoutId = setTimeout(() => {
            if (isResponding) {
                setIsResponding(false)
                isTimeout = true
                console.warn('请求超时')

                // 添加超时消息
                setMessages(prev => {
                    const lastMsg = prev[prev.length - 1]
                    if (lastMsg.role === 'assistant' && lastMsg.isTemp) {
                        return [...prev.slice(0, -1), {
                            ...lastMsg,
                            content: lastMsg.content + '\n\n[生成超时，请重试]',
                            isTemp: false,
                            error: true
                        }]
                    }
                    return [...prev, {
                        role: 'assistant',
                        content: '生成超时，请重试',
                        id: `assistant-${Date.now()}`,
                        error: true
                    }]
                })
            }
        }, TEXT_GENERATION_TIMEOUT_MS)

        // 调用流式API
        try {
            let assistantContent = ''
            let sources = []

            // 使用RAG API还是普通对话API
            const sendFn = selectedKBs.length > 0 ? sendRagMessage : sendMessage

            await sendFn(
                conversation?.id,
                content,
                selectedKBs,
                {
                    onData: (chunk, _, info) => {
                        if (isTimeout) return

                        assistantContent += chunk

                        // 记录引用源
                        if (info.sources) {
                            sources = info.sources
                        }

                        // 更新助手消息
                        setMessages(prev => {
                            const newMessages = [...prev]
                            const assistantMessage = newMessages.find(m => m.role === 'assistant' && m.isTemp)

                            if (assistantMessage) {
                                assistantMessage.content = assistantContent
                                assistantMessage.sources = sources
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
                        if (isTimeout) return

                        clearTimeout(timeoutId)

                        // 完成后更新消息状态
                        setMessages(prev => prev.map(m =>
                            m.isTemp ? { ...m, isTemp: false } : m
                        ))
                        setIsResponding(false)
                    },
                    onError: (error) => {
                        if (isTimeout) return

                        clearTimeout(timeoutId)
                        console.error('消息生成错误:', error)

                        // 添加错误消息
                        setMessages(prev => {
                            const lastMsg = prev[prev.length - 1]
                            if (lastMsg.role === 'assistant' && lastMsg.isTemp) {
                                return [...prev.slice(0, -1), {
                                    ...lastMsg,
                                    content: lastMsg.content + '\n\n[生成错误: ' + error + ']',
                                    isTemp: false,
                                    error: true
                                }]
                            }
                            return [...prev, {
                                role: 'assistant',
                                content: '生成错误: ' + error,
                                id: `assistant-${Date.now()}`,
                                error: true
                            }]
                        })

                        setIsResponding(false)
                    }
                }
            )
        } catch (error) {
            if (!isTimeout) {
                clearTimeout(timeoutId)
                console.error('发送消息错误:', error)

                // 添加错误消息
                setMessages(prev => [...prev, {
                    role: 'assistant',
                    content: '发送消息错误: ' + error.message,
                    id: `assistant-${Date.now()}`,
                    error: true
                }])

                setIsResponding(false)
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
            <MessageList messages={messages} />
            <ConversationInput
                onSend={handleSend}
                disabled={isResponding}
            />
        </div>
    )
}

export default Chat 