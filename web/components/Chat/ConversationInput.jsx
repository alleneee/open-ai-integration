import React, { useState } from 'react'

const ConversationInput = ({ onSend, disabled }) => {
    const [message, setMessage] = useState('')

    const handleSubmit = (e) => {
        e.preventDefault()
        if (!message.trim() || disabled) return

        onSend(message)
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
                    className="flex-1 border rounded-l-lg p-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <button
                    type="submit"
                    disabled={disabled || !message.trim()}
                    className="bg-blue-500 text-white p-2 rounded-r-lg disabled:bg-blue-300"
                >
                    发送
                </button>
            </div>
        </form>
    )
}

export default ConversationInput 