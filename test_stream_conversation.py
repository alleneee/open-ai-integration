#!/usr/bin/env python
"""
测试流式问答功能
"""
import sys
import os
import requests
import json
import uuid
from pprint import pprint
import time

# API 基础URL
BASE_URL = "http://127.0.0.1:8001"  # 修改为你的实际服务器地址

def create_test_conversation():
    """创建测试对话"""
    url = f"{BASE_URL}/api/v1/conversations/"
    data = {
        "title": f"流式测试对话 {uuid.uuid4().hex[:8]}",
        "metadata": {"source": "stream_test"}
    }
    response = requests.post(url, json=data)
    if response.status_code == 201:
        print("创建对话成功!")
        return response.json()
    else:
        print(f"创建对话失败: {response.status_code} - {response.text}")
        return None

def generate_message_stream(conversation_id, message_content):
    """流式生成对话消息"""
    url = f"{BASE_URL}/api/v1/conversations/generate/stream"
    data = {
        "conversation_id": conversation_id,
        "message": message_content,
        "stream": True,
        "llm_config": {
            "temperature": 0.7,
            "max_tokens": 1000
        }
    }
    print(f"发送流式请求: {message_content}")
    
    # 使用stream=True参数以流式方式接收响应
    response = requests.post(url, json=data, stream=True)
    
    if response.status_code != 200:
        print(f"流式生成消息失败: {response.status_code} - {response.text}")
        return
    
    print("\n--- 开始接收流式响应 ---")
    full_response = ""
    chunk_count = 0
    
    # 处理SSE事件流
    for line in response.iter_lines():
        if line:
            line = line.decode("utf-8")
            # SSE事件格式: "data: {json数据}\n\n"
            if line.startswith("data: "):
                chunk_count += 1
                data = line[6:]  # 去掉 "data: " 前缀
                
                # 检查是否是结束标记
                if data == "[DONE]":
                    print("\n--- 响应接收完成 ---")
                    break
                
                try:
                    chunk = json.loads(data)
                    if "content" in chunk:
                        content = chunk["content"]
                        full_response += content
                        print(f"块 {chunk_count}: {content}", end="", flush=True)
                    elif "error" in chunk:
                        print(f"\n错误: {chunk['error']}")
                except json.JSONDecodeError:
                    print(f"\n无法解析JSON: {data}")
    
    print(f"\n\n完整响应: {full_response}")
    return full_response

def generate_rag_message_stream(conversation_id, message_content, knowledge_base_ids):
    """流式生成RAG知识库增强回复"""
    url = f"{BASE_URL}/api/v1/conversations/rag/stream"
    data = {
        "conversation_id": conversation_id,
        "message": message_content,
        "knowledge_base_ids": knowledge_base_ids,
        "stream": True,
        "llm_config": {
            "temperature": 0.7,
            "max_tokens": 1500
        }
    }
    print(f"发送RAG流式请求: {message_content}")
    print(f"使用知识库IDs: {knowledge_base_ids}")
    
    # 使用stream=True参数以流式方式接收响应
    response = requests.post(url, json=data, stream=True)
    
    if response.status_code != 200:
        print(f"RAG流式生成消息失败: {response.status_code} - {response.text}")
        return
    
    print("\n--- 开始接收RAG流式响应 ---")
    full_response = ""
    chunk_count = 0
    
    # 处理SSE事件流
    for line in response.iter_lines():
        if line:
            line = line.decode("utf-8")
            # SSE事件格式: "data: {json数据}\n\n"
            if line.startswith("data: "):
                chunk_count += 1
                data = line[6:]  # 去掉 "data: " 前缀
                
                # 检查是否是结束标记
                if data == "[DONE]":
                    print("\n--- RAG响应接收完成 ---")
                    break
                
                try:
                    chunk = json.loads(data)
                    if "content" in chunk:
                        content = chunk["content"]
                        full_response += content
                        print(f"块 {chunk_count}: {content}", end="", flush=True)
                    elif "error" in chunk:
                        print(f"\n错误: {chunk['error']}")
                except json.JSONDecodeError:
                    print(f"\n无法解析JSON: {data}")
    
    print(f"\n\n完整RAG响应: {full_response}")
    return full_response

def test_stream_flow():
    """测试流式问答流程"""
    print("\n----- 开始测试流式问答功能 -----\n")
    
    # 创建新对话
    print("\n1. 创建新对话")
    conversation = create_test_conversation()
    if not conversation:
        print("测试结束: 无法创建对话")
        return
    
    conversation_id = conversation["id"]
    print(f"创建的对话ID: {conversation_id}")
    
    # 测试流式生成
    print("\n2. 测试流式对话生成")
    message = "请详细介绍一下北京的历史和文化，至少说5点重要特征"
    generate_message_stream(conversation_id, message)
    
    # 延迟一下，让服务器处理完成
    time.sleep(2)
    
    # 测试另一轮对话
    print("\n3. 测试多轮对话")
    message = "请继续说明北京的现代发展"
    generate_message_stream(conversation_id, message)
    
    # 如果有知识库，测试RAG流式问答
    try:
        print("\n4. 测试RAG流式问答 (可选，需要知识库)")
        # 获取可用知识库列表
        print("尝试获取知识库列表...")
        kb_url = f"{BASE_URL}/api/v1/knowledge-bases/"
        kb_response = requests.get(kb_url)
        if kb_response.status_code == 200:
            knowledge_bases = kb_response.json()
            if knowledge_bases and len(knowledge_bases) > 0:
                kb_ids = [kb["id"] for kb in knowledge_bases]
                print(f"找到 {len(kb_ids)} 个知识库")
                message = "请分析公司财务报表的关键指标"
                generate_rag_message_stream(conversation_id, message, kb_ids)
            else:
                print("没有找到可用的知识库，跳过RAG测试")
        else:
            print(f"获取知识库列表失败: {kb_response.status_code}, 跳过RAG测试")
    except Exception as e:
        print(f"RAG测试过程中出错: {str(e)}")
    
    print("\n----- 流式问答测试完成 -----\n")

def test_rag_stream_only():
    """单独测试RAG流式问答功能"""
    print("\n----- 开始测试RAG流式问答功能 -----\n")
    
    # 创建新对话
    print("\n1. 创建新对话")
    conversation = create_test_conversation()
    if not conversation:
        print("测试结束: 无法创建对话")
        return
    
    conversation_id = conversation["id"]
    print(f"创建的对话ID: {conversation_id}")
    
    # 获取可用知识库列表
    print("\n2. 获取知识库列表")
    kb_url = f"{BASE_URL}/api/v1/knowledge-bases/"
    kb_response = requests.get(kb_url)
    
    if kb_response.status_code != 200:
        print(f"获取知识库列表失败: {kb_response.status_code} - {kb_response.text}")
        print("测试结束: 无法获取知识库")
        return
    
    knowledge_bases = kb_response.json()
    if not knowledge_bases or len(knowledge_bases) == 0:
        print("没有找到可用的知识库")
        print("测试结束: 需要先创建知识库")
        return
    
    kb_ids = [kb["id"] for kb in knowledge_bases]
    print(f"找到 {len(kb_ids)} 个知识库: {kb_ids}")
    
    # 测试RAG流式问答
    print("\n3. 测试RAG流式问答")
    message = "请分析公司的产品线和市场策略"
    generate_rag_message_stream(conversation_id, message, kb_ids)
    
    print("\n----- RAG流式问答测试完成 -----\n")

if __name__ == "__main__":
    test_stream_flow()
    #test_rag_stream_only()  # 取消注释以单独测试RAG流式问答功能 