'use client'

import React, { useCallback, useState, useRef } from 'react';
import ReactFlow, {
    addEdge,
    ConnectionLineType,
    useNodesState,
    useEdgesState,
    Controls,
    Background,
    MiniMap,
    Node,
    Edge,
    Position,
    BackgroundVariant,
    Panel,
    NodeChange,
    updateEdge,
    Connection,
    MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css'; // 引入 ReactFlow 样式

// 工作流节点类型
const NODE_TYPES = {
    llm: { name: 'LLM节点', icon: '🤖', color: '#8B5CF6' },
    tool: { name: '工具节点', icon: '🔧', color: '#10B981' },
    condition: { name: '条件节点', icon: '🔀', color: '#F59E0B' },
    input: { name: '输入节点', icon: '📥', color: '#3B82F6' },
    output: { name: '输出节点', icon: '📤', color: '#EC4899' },
    knowledge: { name: '知识库节点', icon: '📚', color: '#6366F1' }
};

// 示例节点数据
const initialNodes: Node[] = [
    {
        id: '1',
        type: 'input', // 内置节点类型
        data: {
            label: '开始节点',
            nodeType: 'input',
            icon: NODE_TYPES.input.icon,
            color: NODE_TYPES.input.color
        },
        position: { x: 250, y: 5 },
        sourcePosition: Position.Bottom,
    },
    {
        id: '2',
        data: {
            label: 'LLM处理',
            nodeType: 'llm',
            icon: NODE_TYPES.llm.icon,
            color: NODE_TYPES.llm.color,
            prompt: '将用户输入转化为格式化响应',
            model: 'gpt-3.5-turbo'
        },
        position: { x: 250, y: 100 },
        sourcePosition: Position.Bottom,
        targetPosition: Position.Top,
    },
    {
        id: '3',
        type: 'output', // 内置节点类型
        data: {
            label: '输出结果',
            nodeType: 'output',
            icon: NODE_TYPES.output.icon,
            color: NODE_TYPES.output.color
        },
        position: { x: 250, y: 200 },
        targetPosition: Position.Top,
    },
];

// 示例边数据
const initialEdges: Edge[] = [
    {
        id: 'e1-2',
        source: '1',
        target: '2',
        type: ConnectionLineType.SmoothStep,
        animated: true,
        markerEnd: {
            type: MarkerType.ArrowClosed,
            width: 20,
            height: 20
        }
    },
    {
        id: 'e2-3',
        source: '2',
        target: '3',
        type: ConnectionLineType.SmoothStep,
        animated: true,
        markerEnd: {
            type: MarkerType.ArrowClosed,
            width: 20,
            height: 20
        }
    },
];

// 自定义节点组件
const CustomNode = ({ data }: { data: any }) => (
    <div className={`px-4 py-2 rounded shadow-md`} style={{ backgroundColor: data.color, border: '1px solid #ccc', minWidth: '150px' }}>
        <div className="flex items-center">
            <span className="text-xl mr-2">{data.icon}</span>
            <div className="text-white font-medium">{data.label}</div>
        </div>
    </div>
);

interface WorkflowDisplayProps {
    readOnly?: boolean;
    onSave?: (nodes: Node[], edges: Edge[]) => void;
}

const WorkflowDisplay: React.FC<WorkflowDisplayProps> = ({ readOnly = false, onSave }) => {
    const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
    const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
    const [selectedNode, setSelectedNode] = useState<Node | null>(null);
    const edgeUpdateSuccessful = useRef(true);

    // 添加新节点
    const onAddNode = useCallback((nodeType: keyof typeof NODE_TYPES) => {
        const newNodeId = `node_${Date.now()}`;
        const typeInfo = NODE_TYPES[nodeType];
        const newNode: Node = {
            id: newNodeId,
            data: {
                label: `${typeInfo.name}`,
                nodeType: nodeType,
                icon: typeInfo.icon,
                color: typeInfo.color
            },
            position: { x: 250, y: nodes.length * 100 + 50 },
            sourcePosition: Position.Bottom,
            targetPosition: Position.Top,
        };

        setNodes((nds) => nds.concat(newNode));
    }, [nodes, setNodes]);

    // 处理节点选择
    const onNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
        setSelectedNode(node);
    }, []);

    // 连接节点
    const onConnect = useCallback(
        (params: Connection) => setEdges((eds) => addEdge(
            {
                ...params,
                type: ConnectionLineType.SmoothStep,
                animated: true,
                markerEnd: {
                    type: MarkerType.ArrowClosed,
                    width: 20,
                    height: 20
                }
            },
            eds
        )),
        [setEdges],
    );

    // 边更新
    const onEdgeUpdate = useCallback(
        (oldEdge: Edge, newConnection: Connection) => {
            edgeUpdateSuccessful.current = true;
            setEdges((els) => updateEdge(oldEdge, newConnection, els));
        },
        [setEdges]
    );

    // 更新节点属性
    const updateNodeData = useCallback((id: string, newData: any) => {
        setNodes(nds => nds.map(node => {
            if (node.id === id) {
                return {
                    ...node,
                    data: { ...node.data, ...newData }
                };
            }
            return node;
        }));
    }, [setNodes]);

    // 保存工作流
    const handleSave = useCallback(() => {
        if (onSave) {
            onSave(nodes, edges);
        }
        alert('工作流保存成功(模拟)');
    }, [nodes, edges, onSave]);

    // 节点属性面板
    const NodePropertiesPanel = () => {
        if (!selectedNode) return null;

        const nodeType = selectedNode.data.nodeType;

        return (
            <div className="bg-white border border-gray-200 rounded-md shadow-sm p-4 w-full max-w-md">
                <h3 className="font-medium text-lg mb-3 flex items-center">
                    <span className="mr-2">{selectedNode.data.icon}</span>
                    节点属性
                </h3>

                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">节点名称</label>
                        <input
                            type="text"
                            value={selectedNode.data.label || ''}
                            onChange={(e) => updateNodeData(selectedNode.id, { label: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                    </div>

                    {nodeType === 'llm' && (
                        <>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">模型</label>
                                <select
                                    value={selectedNode.data.model || 'gpt-3.5-turbo'}
                                    onChange={(e) => updateNodeData(selectedNode.id, { model: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                >
                                    <option value="gpt-4">GPT-4</option>
                                    <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                                    <option value="claude-3-opus">Claude 3 Opus</option>
                                    <option value="claude-3-sonnet">Claude 3 Sonnet</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">提示词</label>
                                <textarea
                                    rows={3}
                                    value={selectedNode.data.prompt || ''}
                                    onChange={(e) => updateNodeData(selectedNode.id, { prompt: e.target.value })}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    placeholder="输入节点的提示词..."
                                />
                            </div>
                        </>
                    )}

                    {nodeType === 'condition' && (
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">条件表达式</label>
                            <textarea
                                rows={3}
                                value={selectedNode.data.condition || ''}
                                onChange={(e) => updateNodeData(selectedNode.id, { condition: e.target.value })}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                placeholder="输入条件表达式，例如: result.score > 0.5"
                            />
                        </div>
                    )}

                    {nodeType === 'tool' && (
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">工具类型</label>
                            <select
                                value={selectedNode.data.toolType || 'api'}
                                onChange={(e) => updateNodeData(selectedNode.id, { toolType: e.target.value })}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            >
                                <option value="api">API调用</option>
                                <option value="code">代码执行</option>
                                <option value="search">网络搜索</option>
                            </select>
                        </div>
                    )}

                    {nodeType === 'knowledge' && (
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">知识库</label>
                            <select
                                value={selectedNode.data.knowledgeBase || ''}
                                onChange={(e) => updateNodeData(selectedNode.id, { knowledgeBase: e.target.value })}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            >
                                <option value="">选择知识库...</option>
                                <option value="kb1">产品文档知识库</option>
                                <option value="kb2">客户支持知识库</option>
                            </select>
                        </div>
                    )}
                </div>
            </div>
        );
    };

    return (
        <div className="w-full h-full flex">
            <div style={{ width: '75%', height: '700px', border: '1px solid #eee' }}>
                <ReactFlow
                    nodes={nodes}
                    edges={edges}
                    onNodesChange={onNodesChange}
                    onEdgesChange={onEdgesChange}
                    onConnect={onConnect}
                    onNodeClick={onNodeClick}
                    onEdgeUpdate={onEdgeUpdate}
                    connectionLineType={ConnectionLineType.SmoothStep}
                    fitView
                    attributionPosition="bottom-left"
                    nodesDraggable={!readOnly}
                    nodesConnectable={!readOnly}
                    elementsSelectable={!readOnly}
                >
                    <Controls />
                    <MiniMap />
                    <Background variant={'dots' as BackgroundVariant} gap={12} size={1} />

                    {!readOnly && (
                        <Panel position="top-right">
                            <button
                                onClick={handleSave}
                                className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 shadow-sm"
                            >
                                保存工作流
                            </button>
                        </Panel>
                    )}

                    {!readOnly && (
                        <Panel position="top-left">
                            <div className="bg-white border border-gray-200 rounded p-3 shadow-sm mb-2">
                                <h3 className="font-medium mb-2">节点类型</h3>
                                <div className="flex flex-wrap gap-2">
                                    {Object.entries(NODE_TYPES).map(([type, info]) => (
                                        <button
                                            key={type}
                                            onClick={() => onAddNode(type as keyof typeof NODE_TYPES)}
                                            className="px-3 py-1 border rounded-full text-sm flex items-center hover:bg-gray-50 transition"
                                            style={{ borderColor: info.color, color: info.color }}
                                        >
                                            <span className="mr-1">{info.icon}</span>
                                            {info.name}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </Panel>
                    )}
                </ReactFlow>
            </div>

            {!readOnly && selectedNode && (
                <div style={{ width: '25%', paddingLeft: '16px' }}>
                    <NodePropertiesPanel />
                </div>
            )}
        </div>
    );
};

export default WorkflowDisplay; 