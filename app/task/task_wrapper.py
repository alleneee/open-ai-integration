"""
Celery 任务包装器
提供任务状态追踪功能
"""
import json
import logging
import functools
import traceback
from typing import Any, Callable, Dict, Optional, TypeVar, cast
from datetime import datetime

from celery import Task
from celery.signals import (
    task_prerun, task_postrun, task_failure, task_retry, task_success,
    task_revoked, worker_process_init
)

from app.models.task import TaskState, TaskStatusCreate, TaskStatusUpdate
from app.services.task_manager import TaskManager
from app.models.database import SessionLocal

logger = logging.getLogger(__name__)

# 类型变量
F = TypeVar('F', bound=Callable[..., Any])


def get_task_session():
    """获取任务数据库会话"""
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()


def track_task_status(task_type: str, task_name: Optional[str] = None):
    """
    跟踪任务状态的装饰器
    
    Args:
        task_type: 任务类型
        task_name: 任务名称，默认使用函数名
        
    Returns:
        装饰后的函数
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # 获取Celery任务实例和ID
            celery_task = self
            task_id = celery_task.request.id
            
            # 获取任务名称（默认使用函数名）
            nonlocal task_name
            if task_name is None:
                task_name = func.__name__
            
            # 获取任务参数 (exclude self from args for metadata)
            task_args = {
                "args": args,
                "kwargs": kwargs
            }
            
            # 获取用户ID (如果在kwargs中)
            user_id = kwargs.get('user_id', None)
            
            # 创建数据库会话
            db = get_task_session()
            task_manager = TaskManager(db)
            
            try:
                # 创建任务状态记录
                task_status_data = TaskStatusCreate(
                    task_id=task_id or "unknown",
                    task_name=task_name,
                    task_type=task_type,
                    status=TaskState.RUNNING,
                    progress=0.0,
                    task_metadata=task_args,
                    user_id=user_id
                )
                
                task_manager.create_task(task_status_data)
                
                # 执行原始函数 (pass args without self)
                try:
                    result = func(self, *args, **kwargs)
                    
                    # 标记任务为已完成
                    task_manager.mark_task_completed(
                        task_id=task_id,
                        result=str(result) if result is not None else None
                    )
                    
                    return result
                except Exception as e:
                    # 捕获异常并更新任务状态
                    error_msg = f"{str(e)}\n{traceback.format_exc()}"
                    logger.error(f"任务执行失败: {error_msg}")
                    
                    task_manager.mark_task_failed(
                        task_id=task_id,
                        error=error_msg
                    )
                    
                    # 重新抛出异常
                    raise
            finally:
                # 关闭数据库会话
                db.close()
                
        return cast(F, wrapper)
    
    return decorator


def update_task_progress(task_id: str, progress: float):
    """
    更新任务进度
    
    Args:
        task_id: 任务ID
        progress: 进度 (0-100)
    """
    db = get_task_session()
    try:
        task_manager = TaskManager(db)
        task_manager.update_task_progress(task_id, progress)
    finally:
        db.close()


# Celery信号处理器

@task_prerun.connect
def task_prerun_handler(task_id, task, *args, **kwargs):
    """任务开始前处理器"""
    logger.info(f"开始执行任务: {task_id}")


@task_success.connect
def task_success_handler(result, sender, **kwargs):
    """任务成功处理器"""
    task_id = sender.request.id
    logger.info(f"任务成功: {task_id}, 结果: {result}")


@task_failure.connect
def task_failure_handler(task_id, exception, traceback, einfo, **kwargs):
    """任务失败处理器"""
    logger.error(f"任务失败: {task_id}, 异常: {exception}")
    
    # 获取数据库会话
    db = get_task_session()
    try:
        task_manager = TaskManager(db)
        
        # 检查任务是否存在
        try:
            task = task_manager.get_task(task_id)
            # 更新任务状态为失败
            task_manager.mark_task_failed(
                task_id=task_id,
                error=f"{str(exception)}\n{einfo}"
            )
        except:
            # 如果任务不存在，则忽略
            pass
    finally:
        db.close()


@task_retry.connect
def task_retry_handler(request, reason, einfo, **kwargs):
    """任务重试处理器"""
    task_id = request.id
    logger.info(f"任务重试: {task_id}, 原因: {reason}")
    
    # 获取数据库会话
    db = get_task_session()
    try:
        task_manager = TaskManager(db)
        
        # 检查任务是否存在
        try:
            task = task_manager.get_task(task_id)
            # 更新任务状态为重试中
            task_manager.update_task(
                task_id=task_id,
                update_data=TaskStatusUpdate(
                    status=TaskState.RETRYING,
                    error=f"{str(reason)}\n{einfo}",
                    retries=task.retries + 1
                )
            )
        except:
            # 如果任务不存在，则忽略
            pass
    finally:
        db.close()


@task_postrun.connect
def task_postrun_handler(task_id, task, retval, state, **kwargs):
    """任务完成后处理器"""
    logger.info(f"任务执行完成: {task_id}, 状态: {state}")


@task_revoked.connect
def task_revoked_handler(request, terminated, signum, expired, **kwargs):
    """任务取消处理器"""
    task_id = request.id
    
    # 获取终止原因
    reason = "未知原因"
    if terminated:
        reason = f"被终止 (信号: {signum})"
    elif expired:
        reason = "任务超时"
    else:
        reason = "任务被取消"
    
    logger.info(f"任务被取消: {task_id}, 原因: {reason}")
    
    # 获取数据库会话
    db = get_task_session()
    try:
        task_manager = TaskManager(db)
        
        # 检查任务是否存在
        try:
            task = task_manager.get_task(task_id)
            # 更新任务状态为已取消
            task_manager.update_task(
                task_id=task_id,
                update_data=TaskStatusUpdate(
                    status=TaskState.CANCELLED,
                    error=f"任务被取消，原因: {reason}",
                    completed_at=datetime.now()
                )
            )
            logger.info(f"已更新任务 {task_id} 状态为已取消")
        except Exception as e:
            logger.error(f"更新任务 {task_id} 状态失败: {str(e)}")
    finally:
        db.close()
