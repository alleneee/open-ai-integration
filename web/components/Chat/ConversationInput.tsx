'use client'

import React, { useState } from 'react'

interface ConversationInputProps {
    onSend: (message: string) => void;
    disabled?: boolean;
}

const ConversationInput: React.FC<ConversationInputProps> = ({ onSend, disabled }) => {
    const [message, setMessage] = useState('')

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault()
        const trimmedMessage = message.trim()
        if (!trimmedMessage || disabled) return

        onSend(trimmedMessage)
        setMessage('')
    }

    return (
        <form onSubmit={handleSubmit} className="border-t p-4">
            <div className="flex items-center">
                <input
                    type="text"
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    placeholder="输入消息..."
                    disabled={disabled}
                    className="flex-1 border rounded-l-lg p-2 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                />
                <button
                    type="submit"
                    disabled={disabled || !message.trim()}
                    className="bg-blue-500 text-white p-2 rounded-r-lg hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 disabled:bg-blue-300 disabled:cursor-not-allowed"
                >
                    发送
                </button>
            </div>
        </form>
    )
}

export default ConversationInput 