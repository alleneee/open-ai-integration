import React, { useState, useEffect } from 'react'
import ConversationList from './ConversationList'
import Chat from './Chat'
import { fetchConversation } from '../services/conversationService'

const ChatLayout = () => {
    const [currentConversation, setCurrentConversation] = useState(null)
    const [loading, setLoading] = useState(false)

    const handleSelectConversation = async (conversation) => {
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
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="flex h-screen">
            <ConversationList
                onSelect={handleSelectConversation}
                currentConversationId={currentConversation?.id}
            />

            <div className="flex-1 flex flex-col">
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