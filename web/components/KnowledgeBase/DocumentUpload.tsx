'use client'

import React, { useState, useRef } from 'react'
import { uploadDocument } from '@/services/knowledgeBaseService'

interface DocumentUploadProps {
    knowledgeBaseId: string;
    onUploadSuccess: () => void;
}

const DocumentUpload: React.FC<DocumentUploadProps> = ({ knowledgeBaseId, onUploadSuccess }) => {
    const [isDragging, setIsDragging] = useState(false)
    const [uploadingFiles, setUploadingFiles] = useState<File[]>([])
    const [progress, setProgress] = useState<Record<string, number>>({})
    const [errors, setErrors] = useState<Record<string, string>>({})
    const fileInputRef = useRef<HTMLInputElement>(null)

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault()
        setIsDragging(true)
    }

    const handleDragLeave = (e: React.DragEvent) => {
        e.preventDefault()
        setIsDragging(false)
    }

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault()
        setIsDragging(false)

        const files = Array.from(e.dataTransfer.files)
        processFiles(files)
    }

    const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            const files = Array.from(e.target.files)
            processFiles(files)
        }
    }

    const processFiles = async (files: File[]) => {
        // 过滤掉不支持的文件类型
        const supportedTypes = [
            'application/pdf',
            'text/plain',
            'text/markdown',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document', // .docx
            'application/msword', // .doc
            'text/csv',
            'application/json'
        ]

        const validFiles = files.filter(file => supportedTypes.includes(file.type))

        if (validFiles.length !== files.length) {
            alert('某些文件类型不支持，仅支持PDF、TXT、Markdown、Word、CSV和JSON格式')
        }

        if (validFiles.length === 0) return

        // 添加到上传队列
        setUploadingFiles(prev => [...prev, ...validFiles])

        // 初始化进度
        const initialProgress = { ...progress }
        validFiles.forEach(file => {
            initialProgress[file.name] = 0
        })
        setProgress(initialProgress)

        // 上传文件
        for (const file of validFiles) {
            try {
                await uploadSingleFile(file)
            } catch (error) {
                console.error(`上传文件 ${file.name} 失败:`, error)
                setErrors(prev => ({ ...prev, [file.name]: '上传失败' }))
            }
        }

        // 通知上层组件上传完成
        onUploadSuccess()
    }

    const uploadSingleFile = async (file: File) => {
        try {
            // 模拟上传进度
            const progressInterval = setInterval(() => {
                setProgress(prev => {
                    const currentProgress = prev[file.name] || 0
                    if (currentProgress < 90) {
                        return { ...prev, [file.name]: currentProgress + 10 }
                    }
                    return prev
                })
            }, 500)

            // 实际上传文件
            await uploadDocument(knowledgeBaseId, file)

            // 清除定时器并设置为100%
            clearInterval(progressInterval)
            setProgress(prev => ({ ...prev, [file.name]: 100 }))

            // 从上传列表中移除
            setTimeout(() => {
                setUploadingFiles(prev => prev.filter(f => f.name !== file.name))
            }, 1000)
        } catch (error) {
            throw error
        }
    }

    const formatFileSize = (bytes: number) => {
        if (bytes < 1024) return bytes + ' B'
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
    }

    return (
        <div className="w-full">
            <div
                className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition ${isDragging
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
                    }`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
            >
                <input
                    type="file"
                    ref={fileInputRef}
                    className="hidden"
                    multiple
                    onChange={handleFileInputChange}
                    accept=".pdf,.txt,.md,.docx,.doc,.csv,.json"
                />
                <svg
                    className="mx-auto h-12 w-12 text-gray-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    xmlns="http://www.w3.org/2000/svg"
                >
                    <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={1}
                        d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    />
                </svg>
                <h3 className="mt-2 text-sm font-medium text-gray-900">
                    {isDragging ? '松开鼠标上传文件' : '拖放文件到此处或点击选择文件'}
                </h3>
                <p className="mt-1 text-xs text-gray-500">
                    支持PDF、TXT、Markdown、Word、CSV和JSON格式
                </p>
            </div>

            {/* 上传进度列表 */}
            {uploadingFiles.length > 0 && (
                <div className="mt-4 space-y-3 max-h-60 overflow-y-auto">
                    <h4 className="text-sm font-medium">上传队列</h4>

                    {uploadingFiles.map((file) => (
                        <div key={file.name} className="bg-white border rounded-md p-3">
                            <div className="flex justify-between items-center mb-1">
                                <span className="text-sm font-medium truncate" title={file.name}>
                                    {file.name}
                                </span>
                                <span className="text-xs text-gray-500">
                                    {formatFileSize(file.size)}
                                </span>
                            </div>

                            <div className="relative pt-1">
                                <div className="flex mb-2 items-center justify-between">
                                    <div>
                                        {errors[file.name] ? (
                                            <span className="text-xs font-semibold inline-block text-red-600">
                                                {errors[file.name]}
                                            </span>
                                        ) : (
                                            <span className="text-xs font-semibold inline-block text-blue-600">
                                                {progress[file.name] || 0}%
                                            </span>
                                        )}
                                    </div>
                                </div>
                                <div className="overflow-hidden h-2 text-xs flex rounded bg-gray-200">
                                    <div
                                        style={{ width: `${progress[file.name] || 0}%` }}
                                        className={`shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center ${errors[file.name]
                                            ? 'bg-red-500'
                                            : progress[file.name] === 100
                                                ? 'bg-green-500'
                                                : 'bg-blue-500'
                                            }`}
                                    />
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}

export default DocumentUpload 