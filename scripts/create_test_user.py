#!/usr/bin/env python
"""
创建测试用户脚本
用于添加测试用户以验证系统功能
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from app.core.security import get_password_hash
from app.models.user import User
from app.models.database import SessionLocal
import uuid
from datetime import datetime

def create_test_user(username, password, email, is_superuser=False):
    """创建测试用户"""
    db = SessionLocal()
    try:
        # 检查用户是否已存在
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            print(f"用户 '{username}' 已存在.")
            return existing_user

        # 创建新用户
        user = User(
            id=str(uuid.uuid4()),
            username=username,
            email=email,
            hashed_password=get_password_hash(password),
            full_name=f"Test {username.title()}",
            is_active=True,
            is_superuser=is_superuser,
            created_at=datetime.utcnow(),
            tenant_id="default"
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"已创建用户: {username} (ID: {user.id})")
        return user
    finally:
        db.close()

if __name__ == "__main__":
    # 创建管理员用户
    admin = create_test_user(
        username="admin",
        password="adminpassword",
        email="admin@example.com",
        is_superuser=True
    )
    
    # 创建普通用户
    user = create_test_user(
        username="testuser",
        password="userpassword",
        email="user@example.com"
    )
    
    print("所有测试用户已创建完成！") 