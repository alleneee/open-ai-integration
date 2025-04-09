/**
 * 工作流相关类型定义
 */

export enum BlockEnum {
    Start = 'start',
    LLM = 'llm',
    Tool = 'tool',
    Condition = 'condition',
    Knowledge = 'knowledge',
    Output = 'output',
    Input = 'input'
}

export enum NodeRunningStatus {
    NotStart = 'not-start',
    Waiting = 'waiting',
    Running = 'running',
    Succeeded = 'succeeded',
    Failed = 'failed'
}

export interface Workflow {
    id: string;
    name: string;
    description?: string;
    createdAt?: string;
    updatedAt?: string;
    nodes: WorkflowNode[];
    edges: WorkflowEdge[];
    model: string;
    temperature: number;
    max_tokens: number;
    agent_enabled: boolean;
    enable_streaming: boolean;
    status: 'ready' | 'processing' | 'error';
    created_by: string;
}

export interface WorkflowNode {
    id: string;
    type: string;
    position: {
        x: number;
        y: number;
    };
    data: {
        label: string;
        desc?: string;
        type: BlockEnum;
        icon?: string;
        model?: string;
        prompt?: string;
        toolType?: string;
        condition?: string;
        knowledgeBase?: string;
        [key: string]: any;
    };
}

export interface WorkflowEdge {
    id: string;
    source: string;
    target: string;
    label?: string;
    type?: string;
} 