import React, { useEffect, useRef } from 'react'

const MessageList = ({ messages }) => {
    const messagesEndRef = useRef(null)

    // 自动滚动到底部
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
            {messages.map(message => (
                <div
                    key={message.id}
                    className={`mb-4 ${message.role === 'user' ? 'text-right' : 'text-left'}`}
                >
                    <div
                        className={`inline-block p-3 rounded-lg max-w-[80%] ${message.role === 'user'
                                ? 'bg-blue-500 text-white'
                                : 'bg-gray-200 text-gray-800'
                            }`}
                    >
                        {message.role === 'assistant' ? (
                            <div>{message.content || '思考中...'}</div>
                        ) : (
                            <div>{message.content}</div>
                        )}

                        {/* 显示引用源 */}
                        {message.role === 'assistant' && message.sources && message.sources.length > 0 && (
                            <div className="mt-2 pt-2 border-t border-gray-300 text-xs">
                                <div className="font-semibold">引用来源：</div>
                                <ul className="list-disc pl-4">
                                    {message.sources.map((source, index) => (
                                        <li key={index} className="truncate">
                                            {source.source}
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