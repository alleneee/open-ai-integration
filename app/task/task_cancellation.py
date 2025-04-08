"""
Celery 任务取消功能
提供终止正在运行的Celery任务的功能
"""
import logging
from typing import Optional, Dict, Any, Tuple

from celery.result import AsyncResult
from celery.exceptions import TaskRevokedError

from app.task.celery_app import celery_app
from app.models.task import TaskState
from app.services.task_manager import TaskManager, get_task_manager
from app.models.database import SessionLocal

logger = logging.getLogger(__name__)


def get_db_session():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()


def cancel_celery_task(task_id: str, terminate: bool = False, signal: str = 'SIGTERM') -> Tuple[bool, str]:
    """
    取消Celery任务
    
    Args:
        task_id: 任务ID
        terminate: 是否强制终止（如果为True，会向任务进程发送信号）
        signal: 终止信号类型（默认为SIGTERM）
            
    Returns:
        成功与否及消息
    """
    try:
        # 获取任务实例
        task_result = AsyncResult(task_id, app=celery_app)
        
        # 检查任务状态
        current_state = task_result.state
        
        # 如果任务已经完成、失败或者已经被取消，则不需要取消
        if current_state in ['SUCCESS', 'FAILURE', 'REVOKED']:
            return False, f"任务已经处于终态 ({current_state})，无需取消"
        
        # 取消任务
        task_result.revoke(terminate=terminate, signal=signal)
        
        return True, f"任务 {task_id} 已成功取消"
        
    except TaskRevokedError:
        # 任务已经被取消
        return True, f"任务 {task_id} 已经被取消"
        
    except Exception as e:
        logger.error(f"取消任务 {task_id} 失败: {str(e)}")
        return False, f"取消任务失败: {str(e)}"


def cancel_task(task_id: str, user_id: Optional[str] = None, is_admin: bool = False) -> Dict[str, Any]:
    """
    取消任务并更新任务状态
    
    Args:
        task_id: 任务ID
        user_id: 用户ID
        is_admin: 是否管理员
            
    Returns:
        取消结果
    """
    # 获取数据库会话
    db = get_db_session()
    
    try:
        # 获取任务管理器
        task_manager = TaskManager(db)
        
        # 获取任务
        try:
            task = task_manager.get_task(task_id)
        except Exception as e:
            return {
                "success": False,
                "message": f"获取任务信息失败: {str(e)}"
            }
        
        # 检查权限
        if not is_admin and task.user_id != user_id:
            return {
                "success": False, 
                "message": "无权限取消此任务"
            }
        
        # 检查任务是否可以取消
        if task.status not in [TaskState.PENDING.value, TaskState.RUNNING.value, TaskState.RETRYING.value]:
            return {
                "success": False,
                "message": f"无法取消状态为 {task.status} 的任务"
            }
        
        # 取消Celery任务
        success, message = cancel_celery_task(task_id)
        
        # 无论Celery取消是否成功，都更新数据库中的任务状态
        task_manager.cancel_task(task_id)
        
        # 如果取消成功或者任务已经不在运行，则认为操作成功
        if success or task.status not in [TaskState.PENDING.value, TaskState.RUNNING.value]:
            return {
                "success": True,
                "message": f"任务已取消: {message}"
            }
        else:
            return {
                "success": False, 
                "message": f"取消Celery任务失败，但已更新数据库任务状态: {message}"
            }
        
    finally:
        db.close()


def cancel_child_tasks(parent_task_id: str) -> Dict[str, Any]:
    """
    取消父任务关联的所有子任务
    
    Args:
        parent_task_id: 父任务ID
            
    Returns:
        取消结果
    """
    # 获取数据库会话
    db = get_db_session()
    
    try:
        # 获取任务管理器
        task_manager = TaskManager(db)
        
        # 查询所有关联的子任务
        # 假设我们在任务元数据中存储了parent_id
        child_tasks = db.query(task_manager.__class__.model_class).filter(
            task_manager.__class__.model_class.metadata.like(f'%"parent_id": "{parent_task_id}"%')
        ).all()
        
        if not child_tasks:
            return {
                "success": True,
                "message": "没有找到子任务",
                "cancelled_count": 0
            }
        
        # 取消所有子任务
        cancelled_count = 0
        failed_tasks = []
        
        for task in child_tasks:
            try:
                success, _ = cancel_celery_task(task.task_id)
                
                # 更新任务状态为取消
                task_manager.cancel_task(task.task_id)
                
                if success:
                    cancelled_count += 1
                else:
                    failed_tasks.append(task.task_id)
                
            except Exception as e:
                logger.error(f"取消子任务 {task.task_id} 失败: {str(e)}")
                failed_tasks.append(task.task_id)
        
        # 返回结果
        return {
            "success": True,
            "message": f"已取消 {cancelled_count} 个子任务, {len(failed_tasks)} 个失败",
            "cancelled_count": cancelled_count,
            "failed_tasks": failed_tasks
        }
        
    except Exception as e:
        logger.error(f"取消子任务失败: {str(e)}")
        return {
            "success": False,
            "message": f"取消子任务失败: {str(e)}",
            "cancelled_count": 0
        }
        
    finally:
        db.close()
