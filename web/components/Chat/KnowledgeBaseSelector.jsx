import React from 'react'

const KnowledgeBaseSelector = ({ knowledgeBases, selectedKBs, onSelectionChange }) => {
    const handleToggleKB = (kbId) => {
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
        <div className="border-b p-3">
            <div className="text-sm font-medium mb-2">选择知识库：</div>
            <div className="flex flex-wrap gap-2">
                {knowledgeBases.map(kb => (
                    <button
                        key={kb.id}
                        onClick={() => handleToggleKB(kb.id)}
                        className={`px-3 py-1 rounded-full text-sm ${selectedKBs.includes(kb.id)
                                ? 'bg-blue-500 text-white'
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