import { Workflow, WorkflowNode, WorkflowEdge, BlockEnum } from '../types'
import { Edge, Node } from 'reactflow'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000'

// 模拟Auth头部，实际项目中从localStorage或其他源获取
const getAuthHeaders = () => {
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${typeof window !== 'undefined' ? localStorage.getItem('token') || 'mock-token' : 'mock-token'}`
    }
}

// 获取工作流列表
export const fetchWorkflows = async (): Promise<Workflow[]> => {
    try {
        // 模拟API调用
        // const response = await fetch(`${API_BASE_URL}/api/v1/workflows`, {
        //     headers: getAuthHeaders()
        // });
        // 
        // if (!response.ok) {
        //     throw new Error('获取工作流列表失败');
        // }
        // 
        // return response.json();

        // 模拟数据
        await new Promise(resolve => setTimeout(resolve, 500));
        return [
            {
                id: '1',
                name: '知识库查询工作流',
                description: '使用知识库处理用户查询的工作流',
                createdAt: new Date(Date.now() - 86400000 * 2).toISOString(),
                updatedAt: new Date(Date.now() - 86400000).toISOString(),
                nodes: [],
                edges: [],
                model: 'gpt-3.5-turbo',
                temperature: 0.7,
                max_tokens: 2048,
                agent_enabled: false,
                enable_streaming: true,
                status: 'ready',
                created_by: 'user1'
            },
            {
                id: '2',
                name: '客服工作流',
                description: '处理客户服务请求的智能工作流',
                createdAt: new Date(Date.now() - 86400000 * 5).toISOString(),
                updatedAt: new Date(Date.now() - 86400000 * 3).toISOString(),
                nodes: [],
                edges: [],
                model: 'gpt-4',
                temperature: 0.5,
                max_tokens: 4096,
                agent_enabled: true,
                enable_streaming: true,
                status: 'ready',
                created_by: 'user1'
            }
        ];
    } catch (error) {
        console.error('获取工作流列表出错:', error);
        throw error;
    }
}

// 创建工作流
export const createWorkflow = async (workflowData: Partial<Workflow>): Promise<Workflow> => {
    try {
        // 模拟API调用
        // const response = await fetch(`${API_BASE_URL}/api/v1/workflows`, {
        //     method: 'POST',
        //     headers: getAuthHeaders(),
        //     body: JSON.stringify(workflowData)
        // });
        //
        // if (!response.ok) {
        //     throw new Error('创建工作流失败');
        // }
        //
        // return response.json();

        // 模拟创建
        await new Promise(resolve => setTimeout(resolve, 800));
        return {
            id: `wf_${Date.now()}`,
            name: workflowData.name || '新工作流',
            description: workflowData.description || '',
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            nodes: workflowData.nodes || [],
            edges: workflowData.edges || [],
            model: workflowData.model || 'gpt-3.5-turbo',
            temperature: workflowData.temperature || 0.7,
            max_tokens: workflowData.max_tokens || 2048,
            agent_enabled: workflowData.agent_enabled || false,
            enable_streaming: workflowData.enable_streaming || true,
            status: 'ready',
            created_by: 'user1'
        };
    } catch (error) {
        console.error('创建工作流出错:', error);
        throw error;
    }
}

// 获取工作流详情
export const fetchWorkflow = async (workflowId: string): Promise<Workflow> => {
    try {
        // 模拟API调用
        // const response = await fetch(`${API_BASE_URL}/api/v1/workflows/${workflowId}`, {
        //     headers: getAuthHeaders()
        // });
        //
        // if (!response.ok) {
        //     throw new Error('获取工作流详情失败');
        // }
        //
        // return response.json();

        // 模拟数据
        await new Promise(resolve => setTimeout(resolve, 600));

        // 示例节点数据
        const nodes: WorkflowNode[] = [
            {
                id: '1',
                type: 'input',
                position: { x: 250, y: 5 },
                data: {
                    label: '开始节点',
                    type: BlockEnum.Start,
                    icon: '📥',
                    color: '#3B82F6'
                },
            },
            {
                id: '2',
                type: 'default',
                position: { x: 250, y: 100 },
                data: {
                    label: 'LLM处理',
                    type: BlockEnum.LLM,
                    icon: '🤖',
                    color: '#8B5CF6',
                    prompt: '将用户输入转化为格式化响应',
                    model: 'gpt-3.5-turbo'
                },
            },
            {
                id: '3',
                type: 'output',
                position: { x: 250, y: 200 },
                data: {
                    label: '输出结果',
                    type: BlockEnum.Output,
                    icon: '📤',
                    color: '#EC4899'
                },
            },
        ];

        // 示例边数据
        const edges: WorkflowEdge[] = [
            {
                id: 'e1-2',
                source: '1',
                target: '2',
                type: 'smoothstep',
                label: '处理'
            },
            {
                id: 'e2-3',
                source: '2',
                target: '3',
                type: 'smoothstep',
                label: '输出'
            },
        ];

        return {
            id: workflowId,
            name: workflowId === '1' ? '知识库查询工作流' : '客服工作流',
            description: workflowId === '1'
                ? '使用知识库处理用户查询的工作流'
                : '处理客户服务请求的智能工作流',
            createdAt: new Date(Date.now() - 86400000 * 2).toISOString(),
            updatedAt: new Date(Date.now() - 86400000).toISOString(),
            nodes: nodes,
            edges: edges,
            model: workflowId === '1' ? 'gpt-3.5-turbo' : 'gpt-4',
            temperature: workflowId === '1' ? 0.7 : 0.5,
            max_tokens: workflowId === '1' ? 2048 : 4096,
            agent_enabled: workflowId === '2',
            enable_streaming: true,
            status: 'ready',
            created_by: 'user1'
        };
    } catch (error) {
        console.error('获取工作流详情出错:', error);
        throw error;
    }
}

// 更新工作流
export const updateWorkflow = async (workflowId: string, workflowData: Partial<Workflow>): Promise<Workflow> => {
    try {
        // 模拟API调用
        // const response = await fetch(`${API_BASE_URL}/api/v1/workflows/${workflowId}`, {
        //     method: 'PUT',
        //     headers: getAuthHeaders(),
        //     body: JSON.stringify(workflowData)
        // });
        //
        // if (!response.ok) {
        //     throw new Error('更新工作流失败');
        // }
        //
        // return response.json();

        // 模拟更新
        await new Promise(resolve => setTimeout(resolve, 700));
        return {
            ...await fetchWorkflow(workflowId),
            ...workflowData,
            updatedAt: new Date().toISOString()
        };
    } catch (error) {
        console.error('更新工作流出错:', error);
        throw error;
    }
}

// 保存工作流节点和边
export const saveWorkflowNodes = async (
    workflowId: string,
    nodes: Node[],
    edges: Edge[]
): Promise<{ success: boolean }> => {
    try {
        // 模拟API调用
        // const response = await fetch(`${API_BASE_URL}/api/v1/workflows/${workflowId}/nodes`, {
        //     method: 'PUT',
        //     headers: getAuthHeaders(),
        //     body: JSON.stringify({ nodes, edges })
        // });
        //
        // if (!response.ok) {
        //     throw new Error('保存工作流节点失败');
        // }
        //
        // return response.json();

        // 模拟保存
        await new Promise(resolve => setTimeout(resolve, 500));
        console.log('保存工作流节点:', workflowId, nodes, edges);

        return { success: true };
    } catch (error) {
        console.error('保存工作流节点出错:', error);
        throw error;
    }
}

// 删除工作流
export const deleteWorkflow = async (workflowId: string): Promise<{ success: boolean }> => {
    try {
        // 模拟API调用
        // const response = await fetch(`${API_BASE_URL}/api/v1/workflows/${workflowId}`, {
        //     method: 'DELETE',
        //     headers: getAuthHeaders()
        // });
        //
        // if (!response.ok) {
        //     throw new Error('删除工作流失败');
        // }
        //
        // return response.json();

        // 模拟删除
        await new Promise(resolve => setTimeout(resolve, 500));
        return { success: true };
    } catch (error) {
        console.error('删除工作流出错:', error);
        throw error;
    }
} 