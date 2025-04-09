'use client'

import React from 'react'
import { ConnectionLineComponentProps } from 'reactflow'

export default function CustomConnectionLine({
    fromX,
    fromY,
    toX,
    toY,
    connectionLineStyle,
}: ConnectionLineComponentProps) {
    // 创建平滑的贝塞尔曲线
    const deltaY = Math.abs(toY - fromY);
    const controlPoint1X = fromX;
    const controlPoint1Y = fromY + deltaY * 0.3;
    const controlPoint2X = toX;
    const controlPoint2Y = toY - deltaY * 0.3;

    // 构建SVG路径 - 使用平滑的贝塞尔曲线
    const path = `M ${fromX} ${fromY} C ${controlPoint1X} ${controlPoint1Y}, ${controlPoint2X} ${controlPoint2Y}, ${toX} ${toY}`;

    return (
        <g>
            <path
                className="custom-connection-line"
                d={path}
                style={{
                    ...connectionLineStyle,
                    strokeDasharray: '5 3',
                    strokeWidth: 2,
                    stroke: '#6366F1',
                    animation: 'flowing 0.5s linear infinite',
                }}
            />
        </g>
    )
} 