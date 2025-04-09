'use client'

import React, { useState, useCallback, useRef, useEffect } from 'react'
import ReactFlow, {
    Background,
    Controls,
    MiniMap,
    Panel,
    ReactFlowProvider,
    useEdgesState,
    useNodesState,
    useReactFlow,
    ConnectionLineType,
    Connection,
    MarkerType,
    Edge,
    Node,
    addEdge,
    BackgroundVariant,
    NodeChange,
    SelectionMode,
    NodeDragHandler,
    NodeMouseHandler,
    OnSelectionChangeParams,
    OnConnectStartParams,
    useStoreApi,
    ControlButton,
    XYPosition,
    Handle,
    Position
} from 'reactflow'
import 'reactflow/dist/style.css'
import './style.css'
import { BlockEnum, NodeRunningStatus } from '../../types'
import CustomEdge from './CustomEdge'
import CustomConnectionLine from './CustomConnectionLine'
import NodeSelector from './NodeSelector'
import NodeContextMenu from './NodeContextMenu'
import PanelContextMenu from './PanelContextMenu'
import NodeEditor from './NodeEditor'

// 自定义节点组件 - 调整样式使其更像Dify
const CustomNode = ({ data, selected }: { data: any, selected?: boolean }) => (
    <div
        className={`px-3 py-2.5 rounded-lg shadow-sm transition-all duration-200 
        ${selected ? 'shadow-md ring-2 ring-indigo-500/50' : 'shadow-md hover:shadow-lg'} 
        border bg-white`}
        style={{
            minWidth: '180px',
            borderLeft: `4px solid ${data.color || '#ccc'}`
        }}
    >
        {/* 源连接点(输出) - 底部中心 */}
        {data.type !== BlockEnum.Output && (
            <Handle
                type="source"
                position={Position.Bottom}
                className="w-3 h-3 bg-blue-500 border-2 border-white"
                id="source"
                style={{ bottom: '-6px' }}
                isConnectable={true}
            />
        )}

        {/* 目标连接点(输入) - 顶部中心 */}
        {data.type !== BlockEnum.Input && data.type !== BlockEnum.Start && (
            <Handle
                type="target"
                position={Position.Top}
                className="w-3 h-3 bg-gray-300 border-2 border-white"
                id="target"
                style={{ top: '-6px' }}
                isConnectable={true}
            />
        )}

        <div className="flex items-center mb-1.5">
            <div className="w-7 h-7 flex items-center justify-center rounded-md text-lg mr-2"
                style={{ backgroundColor: `${data.color}20` }}>
                <span className="text-base" style={{ color: data.color }}>{data.icon}</span>
            </div>
            <div className="font-medium text-gray-800 text-sm">{data.label}</div>
            {data.status && (
                <div className="ml-auto">
                    <span className={`w-2 h-2 rounded-full inline-block ${data.status === 'running' ? 'bg-blue-500 animate-pulse' :
                        data.status === 'succeeded' ? 'bg-green-500' :
                            data.status === 'failed' ? 'bg-red-500' : 'bg-gray-300'
                        }`}></span>
                </div>
            )}
        </div>
        {data.description && (
            <div className="text-xs text-gray-500 pl-9 line-clamp-2">{data.description}</div>
        )}
        {data.model && (
            <div className="text-xs text-gray-500 pl-9 mt-1.5 flex items-center">
                <span className="inline-block w-2 h-2 rounded-full bg-purple-400 mr-1.5"></span>
                {data.model}
            </div>
        )}
        {data.toolType && (
            <div className="text-xs text-gray-500 pl-9 mt-1.5 flex items-center">
                <span className="inline-block w-2 h-2 rounded-full bg-green-400 mr-1.5"></span>
                {data.toolType === 'api' ? 'API调用' :
                    data.toolType === 'code' ? '代码执行' :
                        data.toolType === 'search' ? '网络搜索' : data.toolType}
            </div>
        )}
    </div>
)

// 必须在 CustomNode 定义之后
const nodeTypes = {
    llm: CustomNode,
    tool: CustomNode,
    condition: CustomNode,
    input: CustomNode,
    output: CustomNode,
    knowledge: CustomNode,
}

const edgeTypes = {
    custom: CustomEdge,
}

export const NODE_COLORS = {
    [BlockEnum.LLM]: '#8B5CF6', // 紫色
    [BlockEnum.Tool]: '#10B981', // 绿色
    [BlockEnum.Condition]: '#F59E0B', // 橙色 
    [BlockEnum.Input]: '#3B82F6', // 蓝色
    [BlockEnum.Output]: '#EC4899', // 粉色
    [BlockEnum.Knowledge]: '#6366F1', // 靛蓝色
    [BlockEnum.Start]: '#3B82F6', // 蓝色
}

export const NODE_ICONS = {
    [BlockEnum.LLM]: '🤖',
    [BlockEnum.Tool]: '🔧',
    [BlockEnum.Condition]: '🔀',
    [BlockEnum.Input]: '📥',
    [BlockEnum.Output]: '📤',
    [BlockEnum.Knowledge]: '📚',
    [BlockEnum.Start]: '📥',
}

type WorkflowCanvasProps = {
    initialNodes: Node[];
    initialEdges: Edge[];
    readOnly?: boolean;
    onSave?: (nodes: Node[], edges: Edge[]) => void;
}

const WorkflowCanvas: React.FC<WorkflowCanvasProps> = ({
    initialNodes,
    initialEdges,
    readOnly = false,
    onSave,
}) => {
    const reactFlowWrapper = useRef<HTMLDivElement>(null)
    const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
    const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)
    const [selectedNode, setSelectedNode] = useState<Node | null>(null)
    const [nodeContextMenu, setNodeContextMenu] = useState<{ id: string; x: number; y: number } | null>(null)
    const [panelContextMenu, setPanelContextMenu] = useState<{ x: number; y: number } | null>(null)
    const [reactFlowInstance, setReactFlowInstance] = useState<any>(null)
    const store = useStoreApi()

    const handleSave = useCallback(() => {
        if (onSave) {
            onSave(nodes, edges)
        }
    }, [nodes, edges, onSave])

    // 处理节点选择
    const onNodeClick: NodeMouseHandler = useCallback((event, node) => {
        event.stopPropagation()
        setSelectedNode(node)
        setNodeContextMenu(null)
        setPanelContextMenu(null)
    }, [])

    // 节点右键菜单
    const onNodeContextMenu: NodeMouseHandler = useCallback((event, node) => {
        event.preventDefault()
        setSelectedNode(node)
        setNodeContextMenu({
            id: node.id,
            x: event.clientX,
            y: event.clientY,
        })
        setPanelContextMenu(null)
    }, [])

    // 画布右键菜单
    const onPaneContextMenu = useCallback((event: React.MouseEvent) => {
        event.preventDefault()
        setNodeContextMenu(null)
        setPanelContextMenu({
            x: event.clientX,
            y: event.clientY,
        })
    }, [])

    // 添加节点
    const onAddNode = useCallback((nodeType: BlockEnum, position?: { x: number, y: number }) => {
        if (!reactFlowInstance) return;

        const reactFlowBounds = reactFlowWrapper.current?.getBoundingClientRect()
        const { project, getNodes, getViewport } = reactFlowInstance

        // 计算最佳位置，避免重叠
        let positionToUse: XYPosition

        if (position && panelContextMenu && reactFlowBounds) {
            // 从右键菜单添加，转换鼠标坐标为画布坐标
            positionToUse = project({
                x: panelContextMenu.x - reactFlowBounds.left,
                y: panelContextMenu.y - reactFlowBounds.top
            });
        } else {
            // 从侧边工具栏添加或默认情况
            const existingNodes = getNodes();
            const viewport = getViewport();

            if (existingNodes.length === 0) {
                // 第一个节点放在视口中心偏上位置
                const centerX = (viewport.width || 800) / 2 / viewport.zoom - viewport.x / viewport.zoom;
                const centerY = (viewport.height || 600) / 3 / viewport.zoom - viewport.y / viewport.zoom;
                positionToUse = { x: centerX, y: centerY };
            } else {
                // 根据现有节点布局计算新位置
                const lastNode = existingNodes[existingNodes.length - 1];

                // 找到最下方的节点
                let lowestY = 0;
                let lowestX = 0;

                existingNodes.forEach((node: Node) => {
                    if (node.position.y > lowestY) {
                        lowestY = node.position.y;
                        lowestX = node.position.x;
                    }
                });

                // 在最下方节点下方添加新节点，保持水平对齐
                positionToUse = {
                    x: lowestX,
                    y: lowestY + 120 // 垂直间隔
                };
            }
        }

        const newNodeId = `node_${Date.now()}`

        const newNode: Node = {
            id: newNodeId,
            position: positionToUse,
            data: {
                label: `${nodeType}节点`,
                nodeType: nodeType,
                icon: NODE_ICONS[nodeType],
                color: NODE_COLORS[nodeType],
                type: nodeType,
                title: `${nodeType}节点`,
                desc: ''
            },
            type: nodeType === BlockEnum.Input ? 'input' :
                nodeType === BlockEnum.Output ? 'output' : undefined // 让React Flow处理默认节点类型
        }

        setNodes((nds) => [...nds, newNode])
        setSelectedNode(newNode)
        setPanelContextMenu(null)
    }, [reactFlowInstance, panelContextMenu, setNodes])

    // 连接节点
    const onConnect = useCallback((params: Connection) => {
        setEdges((eds) => addEdge({
            ...params,
            type: 'custom',
            animated: true,
            style: { strokeWidth: 2 },
            markerEnd: {
                type: MarkerType.ArrowClosed,
                width: 20,
                height: 20
            },
            data: {
                sourceType: nodes.find(node => node.id === params.source)?.data?.type,
                targetType: nodes.find(node => node.id === params.target)?.data?.type
            }
        }, eds))
    }, [nodes, setEdges])

    // 删除节点
    const onDeleteNode = useCallback((nodeId: string) => {
        setNodes((nds) => nds.filter((node) => node.id !== nodeId))
        setEdges((eds) => eds.filter((edge) => edge.source !== nodeId && edge.target !== nodeId))
        setNodeContextMenu(null)
        if (selectedNode?.id === nodeId) {
            setSelectedNode(null)
        }
    }, [selectedNode, setNodes, setEdges])

    // 更新节点属性
    const updateNodeData = useCallback((id: string, newData: any) => {
        setNodes(nds => nds.map(node => {
            if (node.id === id) {
                return {
                    ...node,
                    data: { ...node.data, ...newData }
                }
            }
            return node
        }))
    }, [setNodes])

    // 处理画布点击，清除选择
    const onPaneClick = useCallback(() => {
        setSelectedNode(null)
        setNodeContextMenu(null)
        setPanelContextMenu(null)
    }, [])

    // 添加键盘快捷键处理
    useEffect(() => {
        const handleKeyDown = (event: KeyboardEvent) => {
            // 删除选中的节点 (Delete 或 Backspace)
            if ((event.key === 'Delete' || event.key === 'Backspace') && selectedNode) {
                onDeleteNode(selectedNode.id)
            }

            // 保存 (Ctrl+S 或 Cmd+S)
            if ((event.key === 's' || event.key === 'S') && (event.ctrlKey || event.metaKey)) {
                event.preventDefault()
                handleSave()
            }
        }

        document.addEventListener('keydown', handleKeyDown)
        return () => {
            document.removeEventListener('keydown', handleKeyDown)
        }
    }, [selectedNode, onDeleteNode, handleSave])

    // 处理外部点击关闭菜单
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (nodeContextMenu || panelContextMenu) {
                const isContextMenu = (event.target as Element).closest('.context-menu')
                if (!isContextMenu) {
                    setNodeContextMenu(null)
                    setPanelContextMenu(null)
                }
            }
        }

        document.addEventListener('click', handleClickOutside)
        return () => {
            document.removeEventListener('click', handleClickOutside)
        }
    }, [nodeContextMenu, panelContextMenu])

    // 监听窗口大小变化
    useEffect(() => {
        const handleResize = () => {
            if (reactFlowInstance) {
                reactFlowInstance.fitView({ padding: 0.2, includeHiddenNodes: false });
            }
        };

        window.addEventListener('resize', handleResize);

        // 初始化时执行一次
        setTimeout(handleResize, 200);

        return () => {
            window.removeEventListener('resize', handleResize);
        };
    }, [reactFlowInstance]);

    return (
        <div
            className="w-full h-full relative workflow-canvas" // 添加类名
            ref={reactFlowWrapper}
            style={{ height: 'calc(100vh - 160px)' }} // 改为响应式高度
        >
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onConnect={onConnect}
                onInit={setReactFlowInstance}
                onNodeClick={onNodeClick}
                onNodeContextMenu={onNodeContextMenu}
                onPaneClick={onPaneClick}
                onPaneContextMenu={onPaneContextMenu}
                nodeTypes={nodeTypes}
                edgeTypes={edgeTypes}
                connectionLineComponent={CustomConnectionLine}
                defaultViewport={{ x: 0, y: 0, zoom: 1 }}
                connectionLineType={ConnectionLineType.SmoothStep}
                fitView
                fitViewOptions={{ padding: 0.2, includeHiddenNodes: false }}
                attributionPosition="bottom-left"
                minZoom={0.25}
                maxZoom={2}
                nodesDraggable={!readOnly}
                nodesConnectable={true}
                elementsSelectable={!readOnly}
                selectionMode={SelectionMode.Partial}
                proOptions={{ hideAttribution: true }}
                defaultEdgeOptions={{
                    type: 'custom',
                    animated: true,
                    style: { strokeWidth: 2 }
                }}
            >
                <Background
                    variant={BackgroundVariant.Dots}
                    gap={14}
                    size={1}
                    className="bg-gray-50" // Dify背景色偏灰白
                    color="#e0e0e0" // 网点颜色
                />
                <Controls showInteractive={false} className="custom-controls"> {/* 自定义类名 */}
                    {/* 添加自定义按钮，模拟Dify的布局和功能 */}
                    <ControlButton onClick={() => { }} title="指针">👆</ControlButton>
                    <ControlButton onClick={() => { }} title="拖拽">🖐️</ControlButton>
                </Controls>
                <MiniMap
                    nodeStrokeWidth={3}
                    nodeColor={(n) => n.data.color || '#ccc'}
                    nodeClassName={(n) => 'minimap-node'}
                    zoomable
                    pannable
                    className="custom-minimap" // 自定义类名
                />

                {/* ... 底部按钮，类似Dify的放大缩小、撤销重做等，可以添加到Controls或Panel */}
                <Panel position="bottom-center">
                    <ZoomControls />
                </Panel>

                {!readOnly && (
                    <Panel position="top-right">
                        <div className="flex space-x-2">
                            <button
                                onClick={handleSave}
                                className="px-4 py-1.5 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 shadow-sm text-sm font-medium"
                            >
                                发布
                            </button>
                            {/* 添加预览、日志、功能等按钮 */}
                            <button className="px-3 py-1.5 border border-gray-300 bg-white text-gray-700 rounded-md hover:bg-gray-50 shadow-sm text-sm">预览</button>
                            <button className="px-3 py-1.5 border border-gray-300 bg-white text-gray-700 rounded-md hover:bg-gray-50 shadow-sm text-sm">日志</button>
                            <button className="px-3 py-1.5 border border-gray-300 bg-white text-gray-700 rounded-md hover:bg-gray-50 shadow-sm text-sm">功能</button>
                        </div>
                    </Panel>
                )}

                {!readOnly && (
                    <Panel position="top-left" className="pt-12"> {/* 调整位置避免遮挡 */}
                        <NodeSelector onAddNode={onAddNode} />
                    </Panel>
                )}
            </ReactFlow>

            {/* 节点右键菜单 */}
            {nodeContextMenu && (
                <NodeContextMenu
                    nodeId={nodeContextMenu.id}
                    position={{ x: nodeContextMenu.x, y: nodeContextMenu.y }}
                    onDelete={onDeleteNode}
                    onClose={() => setNodeContextMenu(null)}
                />
            )}

            {/* 画布右键菜单 */}
            {panelContextMenu && (
                <PanelContextMenu
                    position={{ x: panelContextMenu.x, y: panelContextMenu.y }}
                    onAddNode={onAddNode}
                    onClose={() => setPanelContextMenu(null)}
                />
            )}

            {/* 节点编辑器 */}
            {selectedNode && !readOnly && (
                <div className="absolute top-0 right-0 w-1/4 h-full bg-white border-l border-gray-200 overflow-y-auto shadow-lg z-10">
                    <NodeEditor
                        node={selectedNode}
                        onUpdate={updateNodeData}
                        onClose={() => setSelectedNode(null)}
                    />
                </div>
            )}
        </div>
    )
}

// 包装导出组件
const WorkflowCanvasProvider: React.FC<WorkflowCanvasProps> = (props) => {
    return (
        <ReactFlowProvider>
            <WorkflowCanvas {...props} />
        </ReactFlowProvider>
    )
}

// 底部缩放控制面板
const ZoomControls = () => {
    const { zoomIn, zoomOut, fitView } = useReactFlow()
    const store = useStoreApi()

    const handleFitView = () => {
        fitView({ padding: 0.2, includeHiddenNodes: false, duration: 800 })
    }

    return (
        <div className="zoom-controls">
            <button
                onClick={() => zoomOut({ duration: 300 })}
                title="缩小"
                className="text-gray-600 hover:text-gray-900"
            >
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                    <path fillRule="evenodd" d="M3 10a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" />
                </svg>
            </button>
            <span className="zoom-value">
                {Math.round(store.getState().transform[2] * 100)}%
            </span>
            <button
                onClick={() => zoomIn({ duration: 300 })}
                title="放大"
                className="text-gray-600 hover:text-gray-900"
            >
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                    <path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" />
                </svg>
            </button>
            <div className="border-l h-4 mx-1"></div>
            <button
                onClick={handleFitView}
                title="适应视图"
                className="text-gray-600 hover:text-gray-900"
            >
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                    <path fillRule="evenodd" d="M4.25 5.5a.75.75 0 00-.75.75v8.5c0 .414.336.75.75.75h8.5a.75.75 0 00.75-.75v-4a.75.75 0 011.5 0v4A2.25 2.25 0 0112.75 17h-8.5A2.25 2.25 0 012 14.75v-8.5A2.25 2.25 0 014.25 4h5a.75.75 0 010 1.5h-5z" clipRule="evenodd" />
                    <path fillRule="evenodd" d="M6.194 12.753a.75.75 0 001.06.053L16.5 4.44v2.81a.75.75 0 001.5 0v-4.5a.75.75 0 00-.75-.75h-4.5a.75.75 0 000 1.5h2.553l-9.056 8.194a.75.75 0 00-.053 1.06z" clipRule="evenodd" />
                </svg>
            </button>
        </div>
    )
}

export default WorkflowCanvasProvider 