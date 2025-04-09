'use client'

import React from 'react'

interface NodeContextMenuProps {
    nodeId: string
    position: { x: number; y: number }
    onDelete: (nodeId: string) => void
    onClose: () => void
}

const NodeContextMenu: React.FC<NodeContextMenuProps> = ({
    nodeId,
    position,
    onDelete,
    onClose,
}) => {
    return (
        <div
            className="absolute bg-white shadow-lg border border-gray-200 rounded-md py-1 z-50 context-menu"
            style={{
                left: position.x,
                top: position.y,
                minWidth: '160px',
            }}
        >
            <div className="px-4 py-2 text-sm font-medium text-gray-700 border-b border-gray-100">
                节点操作
            </div>

            <button
                className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center"
                onClick={() => onDelete(nodeId)}
            >
                <svg
                    className="h-4 w-4 mr-2 text-red-500"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                删除节点
            </button>

            <button
                className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center"
                onClick={onClose}
            >
                <svg
                    className="h-4 w-4 mr-2 text-gray-500"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M6 18L18 6M6 6l12 12" />
                </svg>
                取消
            </button>
        </div>
    )
}

export default NodeContextMenu 