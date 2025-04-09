import React, { useEffect, useState } from 'react'
import { fetchConversations, deleteConversation, createConversation } from '../../services/conversationService'

const ConversationList = ({ onSelect, currentConversationId }) => {
    const [conversations, setConversations] = useState([])
    const [loading, setLoading] = useState(true)

    const loadConversations = async () => {
        try {
            setLoading(true)
            const data = await fetchConversations()
            setConversations(data)
        } catch (error) {
            console.error('加载对话列表失败:', error)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        loadConversations()
    }, [])

    const handleNew = async () => {
        try {
            const newConversation = await createConversation({ title: '新对话' })
            setConversations([newConversation, ...conversations])
            onSelect(newConversation)
        } catch (error) {
            console.error('创建对话失败:', error)
        }
    }

    const handleDelete = async (id, e) => {
        e.stopPropagation()

        try {
            await deleteConversation(id)
            setConversations(conversations.filter(conv => conv.id !== id))

            if (currentConversationId === id)
                onSelect(null)
        } catch (error) {
            console.error('删除对话失败:', error)
        }
    }

    return (
        <div className="w-64 h-full border-r bg-gray-50">
            <div className="p-4">
                <button
                    className="w-full bg-blue-500 text-white p-2 rounded"
                    onClick={handleNew}
                >
                    新建对话
                </button>
            </div>

            {loading ? (
                <div className="p-4 text-center">加载中...</div>
            ) : (
                <div className="overflow-y-auto">
                    {conversations.length === 0 ? (
                        <div className="p-4 text-center text-gray-500">没有对话记录</div>
                    ) : (
                        conversations.map(conversation => (
                            <div
                                key={conversation.id}
                                onClick={() => onSelect(conversation)}
                                className={`p-3 border-b cursor-pointer hover:bg-gray-100 flex justify-between items-center ${currentConversationId === conversation.id ? 'bg-blue-100' : ''
                                    }`}
                            >
                                <div className="truncate">{conversation.title}</div>
                                <button
                                    className="text-red-500 text-sm"
                                    onClick={(e) => handleDelete(conversation.id, e)}
                                >
                                    删除
                                </button>
                            </div>
                        ))
                    )}
                </div>
            )}
        </div>
    )
}

export default ConversationList 