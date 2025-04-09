'use client'

import React, { useState, useEffect } from 'react'
import { LexicalComposer } from '@lexical/react/LexicalComposer'
import { PlainTextPlugin } from '@lexical/react/LexicalPlainTextPlugin'
import { ContentEditable } from '@lexical/react/LexicalContentEditable'
import { HistoryPlugin } from '@lexical/react/LexicalHistoryPlugin'
import { OnChangePlugin } from '@lexical/react/LexicalOnChangePlugin'
import { useLexicalComposerContext } from '@lexical/react/LexicalComposerContext'
import { $getRoot, $createParagraphNode, $createTextNode, EditorState } from 'lexical'
import LexicalErrorBoundary from '@lexical/react/LexicalErrorBoundary'

interface LexicalInputProps {
    onSend: (content: string) => void;
    disabled?: boolean;
}

const LexicalInput: React.FC<LexicalInputProps> = ({ onSend, disabled = false }) => {
    const [text, setText] = useState('')

    const initialConfig = {
        namespace: 'ChatEditor',
        theme: {
            paragraph: 'mb-1',
            root: 'outline-none',
            text: {
                base: 'text-gray-800',
                bold: 'font-bold',
                italic: 'italic',
                underline: 'underline',
                strikethrough: 'line-through',
                underlineStrikethrough: 'underline line-through',
            },
        },
        onError: (error: Error) => {
            console.error('Lexical editor error:', error)
        },
    }

    const onChange = (editorState: EditorState) => {
        editorState.read(() => {
            const root = $getRoot()
            const textContent = root.getTextContent()
            setText(textContent)
        })
    }

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault()
        if (text.trim() && !disabled) {
            onSend(text.trim())
            setText('')
            // 重置编辑器内容
            const element = document.querySelector('.lexical-content-editable')
            if (element && element.querySelector('p')) {
                element.querySelector('p')!.textContent = ''
            }
        }
    }

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSubmit(e)
        }
    }

    return (
        <form onSubmit={handleSubmit} className="border-t p-2">
            <div className={`border rounded-lg overflow-hidden ${disabled ? 'opacity-70' : ''}`}>
                <LexicalComposer initialConfig={initialConfig}>
                    <div className="relative min-h-[60px] max-h-[200px] overflow-auto">
                        <PlainTextPlugin
                            contentEditable={
                                <ContentEditable
                                    className="lexical-content-editable p-3 outline-none"
                                    onKeyDown={handleKeyDown}
                                />
                            }
                            placeholder={
                                <div className="absolute top-3 left-3 text-gray-400 pointer-events-none">
                                    输入消息...
                                </div>
                            }
                            ErrorBoundary={LexicalErrorBoundary}
                        />
                        <OnChangePlugin onChange={onChange} />
                        <HistoryPlugin />
                    </div>
                </LexicalComposer>
                <div className="flex justify-end bg-gray-50 p-2">
                    <button
                        type="submit"
                        className="bg-blue-500 text-white px-4 py-1 rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
                        disabled={!text.trim() || disabled}
                    >
                        发送
                    </button>
                </div>
            </div>
        </form>
    )
}

export default LexicalInput 