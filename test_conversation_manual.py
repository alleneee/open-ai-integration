#!/usr/bin/env python
"""
手动测试对话和会话管理功能
"""
import sys
import os
import requests
import json
import uuid
from pprint import pprint

# API 基础URL
BASE_URL = "http://127.0.0.1:8001"  # 修改为你的实际服务器地址

def create_test_conversation():
    """创建测试对话"""
    url = f"{BASE_URL}/api/v1/conversations/"
    data = {
        "title": f"测试对话 {uuid.uuid4().hex[:8]}",
        "metadata": {"source": "manual_test"}
    }
    response = requests.post(url, json=data)
    if response.status_code == 201:
        print("创建对话成功!")
        return response.json()
    else:
        print(f"创建对话失败: {response.status_code} - {response.text}")
        return None

def list_conversations():
    """获取对话列表"""
    url = f"{BASE_URL}/api/v1/conversations/"
    response = requests.get(url)
    if response.status_code == 200:
        conversations = response.json()
        print(f"获取到 {len(conversations)} 个对话:")
        for i, conv in enumerate(conversations):
            print(f"{i+1}. ID: {conv['id']}, 标题: {conv['title']}")
        return conversations
    else:
        print(f"获取对话列表失败: {response.status_code} - {response.text}")
        return []

def get_conversation_detail(conversation_id):
    """获取对话详情"""
    url = f"{BASE_URL}/api/v1/conversations/{conversation_id}"
    response = requests.get(url)
    if response.status_code == 200:
        print("获取对话详情成功!")
        return response.json()
    else:
        print(f"获取对话详情失败: {response.status_code} - {response.text}")
        return None

def add_message(conversation_id, message_content):
    """向对话添加消息"""
    url = f"{BASE_URL}/api/v1/conversations/{conversation_id}/messages"
    data = {
        "role": "user",
        "content": message_content,
        "metadata": {"source": "manual_test"}
    }
    response = requests.post(url, json=data)
    if response.status_code == 200:
        print("添加消息成功!")
        return response.json()
    else:
        print(f"添加消息失败: {response.status_code} - {response.text}")
        return None

def generate_message(conversation_id, message_content):
    """生成对话消息"""
    url = f"{BASE_URL}/api/v1/conversations/generate"
    data = {
        "conversation_id": conversation_id,
        "message": message_content,
        "stream": False,
        "llm_config": {
            "temperature": 0.7,
            "max_tokens": 1000
        }
    }
    response = requests.post(url, json=data)
    if response.status_code == 200:
        print("生成消息成功!")
        return response.json()
    else:
        print(f"生成消息失败: {response.status_code} - {response.text}")
        return None

def update_conversation(conversation_id, new_title=None, new_state=None):
    """更新对话信息"""
    url = f"{BASE_URL}/api/v1/conversations/{conversation_id}"
    data = {}
    if new_title:
        data["title"] = new_title
    if new_state:
        data["state"] = new_state
    
    response = requests.put(url, json=data)
    if response.status_code == 200:
        print("更新对话成功!")
        return response.json()
    else:
        print(f"更新对话失败: {response.status_code} - {response.text}")
        return None

def delete_conversation(conversation_id):
    """删除对话"""
    url = f"{BASE_URL}/api/v1/conversations/{conversation_id}"
    response = requests.delete(url)
    if response.status_code == 200:
        print("删除对话成功!")
        return True
    else:
        print(f"删除对话失败: {response.status_code} - {response.text}")
        return False

def test_conversation_flow():
    """测试完整对话流程"""
    print("\n----- 开始测试对话流程 -----\n")
    
    # 创建新对话
    print("\n1. 创建新对话")
    conversation = create_test_conversation()
    if not conversation:
        print("测试结束: 无法创建对话")
        return
    
    conversation_id = conversation["id"]
    print(f"创建的对话ID: {conversation_id}")
    
    # 列出对话
    print("\n2. 列出所有对话")
    list_conversations()
    
    # 向对话添加消息
    print("\n3. 添加用户消息")
    message = add_message(conversation_id, "这是一条测试消息")
    if not message:
        print("测试结束: 无法添加消息")
        return
    
    # 获取对话详情
    print("\n4. 获取对话详情")
    conv_detail = get_conversation_detail(conversation_id)
    if not conv_detail:
        print("测试结束: 无法获取对话详情")
        return
    
    print("对话消息列表:")
    for msg in conv_detail["messages"]:
        print(f"- 角色: {msg['role']}, 内容: {msg['content']}")
    
    # 生成回复
    print("\n5. 生成对话回复")
    response = generate_message(conversation_id, "请向我介绍一下你自己")
    if not response:
        print("测试结束: 无法生成回复")
        return
    
    # 打印响应的完整结构，以便了解它包含什么字段
    print("响应数据结构:")
    print(response)
    
    # 处理不同的响应结构
    if "content" in response:
        print(f"生成的回复: {response['content']}")
    elif "message" in response and "content" in response["message"]:
        print(f"生成的回复: {response['message']['content']}")
    elif "response" in response:
        print(f"生成的回复: {response['response']}")
    elif "message" in response:
        print(f"生成的回复: {response['message']}")
    else:
        print("响应中未找到内容字段，请检查响应格式")
    
    # 更新对话标题
    print("\n6. 更新对话标题")
    updated_conv = update_conversation(conversation_id, new_title="已更新的对话标题")
    if not updated_conv:
        print("测试结束: 无法更新对话")
        return
    
    print(f"更新后的标题: {updated_conv['title']}")
    
    # 最后查看对话详情
    print("\n7. 再次获取对话详情")
    final_detail = get_conversation_detail(conversation_id)
    if final_detail:
        print("最终对话详情:")
        print(f"- 标题: {final_detail['title']}")
        print(f"- 消息数: {len(final_detail['messages'])}")
        print("最近的消息:")
        for msg in final_detail["messages"][-2:]:
            print(f"- 角色: {msg['role']}, 内容: {msg['content']}")
    
    # 删除对话
    print("\n8. 删除对话")
    if delete_conversation(conversation_id):
        print(f"已成功删除对话 {conversation_id}")
    else:
        print(f"无法删除对话 {conversation_id}")
    
    print("\n----- 对话流程测试完成 -----\n")

if __name__ == "__main__":
    test_conversation_flow() 