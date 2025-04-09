'use client'

import React, { useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Message } from '@/types/conversation'

interface MessageListProps {
    messages: Message[];
}

const MessageList: React.FC<MessageListProps> = ({ messages }) => {
    const messagesEndRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    if (!messages || messages.length === 0) {
        return (
            <div className="flex-1 flex items-center justify-center p-4 text-gray-500">
                开始新的对话吧！
            </div>
        )
    }

    return (
        <div className="flex-1 overflow-y-auto p-4">
            {messages.map((message, index) => (
                <div
                    key={message.id || `msg-${index}`}
                    className={`mb-4 flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                    <div
                        className={`inline-block p-3 rounded-lg max-w-[80%] break-words ${message.role === 'user'
                            ? 'bg-blue-500 text-white'
                            : 'bg-gray-200 text-gray-800'
                            } ${message.error ? 'border border-red-500' : ''} ${message.isTemp ? 'opacity-80' : ''}`}
                    >
                        {message.role === 'assistant' ? (
                            <ReactMarkdown
                                className="prose prose-sm max-w-none dark:prose-invert"
                                remarkPlugins={[remarkGfm]}
                            >
                                {message.content || '思考中...'}
                            </ReactMarkdown>
                        ) : (
                            <div>{message.content}</div>
                        )}

                        {message.role === 'assistant' && message.sources && message.sources.length > 0 && (
                            <div className="mt-2 pt-2 border-t border-gray-300 text-xs text-gray-600">
                                <div className="font-semibold mb-1">引用来源：</div>
                                <ul className="list-disc pl-4 space-y-1">
                                    {message.sources.map((source: any, idx: number) => (
                                        <li key={idx} className="truncate">
                                            {source.source || `来源 ${idx + 1}`}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>
                </div>
            ))}
            <div ref={messagesEndRef} />
        </div>
    )
}

export default MessageList 