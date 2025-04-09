'use client'

import React from 'react'
import type { KnowledgeBase } from '@/types/conversation' // 假设的类型定义

interface KnowledgeBaseSelectorProps {
    knowledgeBases: KnowledgeBase[];
    selectedKBs: string[];
    onSelectionChange: (selectedIds: string[]) => void;
}

const KnowledgeBaseSelector: React.FC<KnowledgeBaseSelectorProps> = ({ knowledgeBases, selectedKBs, onSelectionChange }) => {
    const handleToggleKB = (kbId: string) => {
        if (selectedKBs.includes(kbId)) {
            onSelectionChange(selectedKBs.filter(id => id !== kbId))
        } else {
            onSelectionChange([...selectedKBs, kbId])
        }
    }

    if (!knowledgeBases || knowledgeBases.length === 0) {
        return null
    }

    return (
        <div className="border-b p-3 bg-gray-50">
            <div className="text-sm font-medium mb-2 text-gray-700">选择知识库进行 RAG：</div>
            <div className="flex flex-wrap gap-2">
                {knowledgeBases.map(kb => (
                    <button
                        key={kb.id}
                        onClick={() => handleToggleKB(kb.id)}
                        className={`px-3 py-1 rounded-full text-sm transition-colors duration-150 ${selectedKBs.includes(kb.id)
                            ? 'bg-blue-500 text-white hover:bg-blue-600'
                            : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                            }`}
                    >
                        {kb.name}
                    </button>
                ))}
            </div>
        </div>
    )
}

export default KnowledgeBaseSelector 