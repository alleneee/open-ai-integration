'use client'

import React from 'react'
import { BlockEnum } from '../../types'
import { NODE_COLORS, NODE_ICONS } from './WorkflowCanvas'

interface PanelContextMenuProps {
    position: { x: number; y: number }
    onAddNode: (type: BlockEnum, position?: { x: number, y: number }) => void
    onClose: () => void
}

const PanelContextMenu: React.FC<PanelContextMenuProps> = ({
    position,
    onAddNode,
    onClose,
}) => {
    const nodeTypes = [
        { type: BlockEnum.LLM, name: 'LLM节点' },
        { type: BlockEnum.Tool, name: '工具节点' },
        { type: BlockEnum.Condition, name: '条件节点' },
        { type: BlockEnum.Input, name: '输入节点' },
        { type: BlockEnum.Output, name: '输出节点' },
        { type: BlockEnum.Knowledge, name: '知识库节点' },
    ]

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
                添加节点
            </div>

            {nodeTypes.map(nodeType => (
                <button
                    key={nodeType.type}
                    className="w-full text-left px-4 py-2 text-sm hover:bg-gray-100 flex items-center"
                    style={{ color: NODE_COLORS[nodeType.type] }}
                    onClick={() => {
                        onAddNode(nodeType.type, position)
                        onClose()
                    }}
                >
                    <span className="mr-2 text-lg">{NODE_ICONS[nodeType.type]}</span>
                    {nodeType.name}
                </button>
            ))}

            <div className="border-t border-gray-100 mt-1">
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
        </div>
    )
}

export default PanelContextMenu 