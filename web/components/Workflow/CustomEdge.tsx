'use client'

import React from 'react'
import { EdgeProps, getBezierPath } from 'reactflow'

export default function CustomEdge({
    id,
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    style = {},
    selected,
    data,
}: EdgeProps) {
    // 创建平滑的贝塞尔曲线
    const deltaY = Math.abs(targetY - sourceY);
    const [edgePath] = getBezierPath({
        sourceX,
        sourceY,
        sourcePosition,
        targetX,
        targetY,
        targetPosition,
        curvature: 0.3, // 控制曲线的弯曲程度
    });

    // 计算标签位置
    const labelX = (sourceX + targetX) / 2;
    const labelY = (sourceY + targetY) / 2 - 10;

    return (
        <g className={`custom-edge ${selected ? 'selected' : ''}`}>
            <path
                id={id}
                className="custom-edge-path"
                d={edgePath}
                style={{
                    ...style,
                    strokeWidth: selected ? 3 : 2,
                    stroke: selected ? '#6366F1' : '#94A3B8',
                    strokeDasharray: data?.dashed ? '5 5' : 'none',
                }}
            />
            {data?.label && (
                <foreignObject
                    width={100}
                    height={30}
                    x={labelX - 50}
                    y={labelY - 10}
                    className="edge-label-container"
                >
                    <div className="edge-label">
                        {data.label}
                    </div>
                </foreignObject>
            )}
        </g>
    )
} 