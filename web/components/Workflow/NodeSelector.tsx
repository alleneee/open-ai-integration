'use client'

import React from 'react'
import { BlockEnum } from '../../types'
import { NODE_COLORS, NODE_ICONS } from './WorkflowCanvas'

interface NodeSelectorProps {
    onAddNode: (type: BlockEnum, position?: { x: number, y: number }) => void
}

const NodeSelector: React.FC<NodeSelectorProps> = ({ onAddNode }) => {
    const nodeTypes = [
        { type: BlockEnum.LLM, name: 'LLM节点', description: '处理自然语言请求' },
        { type: BlockEnum.Tool, name: '工具节点', description: '执行特定功能或API调用' },
        { type: BlockEnum.Condition, name: '条件节点', description: '根据条件决定流程走向' },
        { type: BlockEnum.Input, name: '输入节点', description: '接收用户输入' },
        { type: BlockEnum.Output, name: '输出节点', description: '返回结果给用户' },
        { type: BlockEnum.Knowledge, name: '知识库节点', description: '查询知识库中的信息' },
    ]

    return (
        <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-3 mb-2">
            <h3 className="font-medium mb-3 text-gray-700 flex items-center text-sm">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1.5 text-gray-500" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 3a1 1 0 00-1 1v4H5a1 1 0 100 2h4v4a1 1 0 102 0v-4h4a1 1 0 100-2h-4V4a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                添加节点
            </h3>
            <div className="grid grid-cols-2 gap-2">
                {nodeTypes.map(nodeType => (
                    <button
                        key={nodeType.type}
                        onClick={() => onAddNode(nodeType.type)}
                        className="px-3 py-2 border rounded-lg text-sm flex items-center hover:bg-gray-50 transition-colors duration-200 group"
                        style={{ borderColor: `${NODE_COLORS[nodeType.type]}50` }}
                        title={nodeType.description}
                    >
                        <div className="w-6 h-6 flex items-center justify-center rounded-md text-lg mr-2 transition-colors duration-200"
                            style={{
                                backgroundColor: `${NODE_COLORS[nodeType.type]}20`,
                                color: NODE_COLORS[nodeType.type]
                            }}>
                            {NODE_ICONS[nodeType.type]}
                        </div>
                        <span className="text-gray-700 group-hover:text-gray-900 transition-colors duration-200">{nodeType.name}</span>
                    </button>
                ))}
            </div>
        </div>
    )
}

export default NodeSelector 