'use client'

import React, { useState, useEffect } from 'react'
import ConversationList from './ConversationList' // 调整路径
import Chat from './Chat' // 调整路径
import { fetchConversation } from '@/services/conversationService' // 使用别名路径
import type { Conversation, ConversationDetail } from '@/types/conversation' // 假设的类型定义

const ChatLayout = () => {
    const [currentConversation, setCurrentConversation] = useState<ConversationDetail | null>(null)
    const [loading, setLoading] = useState(false)

    const handleSelectConversation = async (conversation: Conversation | null) => {
        if (!conversation) {
            setCurrentConversation(null)
            return
        }

        try {
            setLoading(true)
            const conversationDetail = await fetchConversation(conversation.id)
            setCurrentConversation(conversationDetail)
        } catch (error) {
            console.error('获取对话详情失败:', error)
            // 添加用户反馈，例如使用Toast
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="flex h-full"> {/* 移除 h-screen，父级已控制高度 */}
            <ConversationList
                onSelect={handleSelectConversation}
                currentConversationId={currentConversation?.id}
            />

            <div className="flex-1 flex flex-col overflow-hidden"> {/* 添加 overflow-hidden */}
                {loading ? (
                    <div className="flex-1 flex items-center justify-center">
                        加载对话中...
                    </div>
                ) : currentConversation ? (
                    <Chat conversation={currentConversation} />
                ) : (
                    <div className="flex-1 flex items-center justify-center text-gray-500">
                        选择一个对话或创建新对话开始聊天
                    </div>
                )}
            </div>
        </div>
    )
}

export default ChatLayout 