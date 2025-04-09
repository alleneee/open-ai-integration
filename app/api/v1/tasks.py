"""
任务状态管理API路由
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from celery.result import AsyncResult

from app.task.celery_app import celery_app
from app.api.deps import get_current_user, get_current_user_optional, get_db
from app.models.user import User
from app.models.task import TaskStatusResponse, TaskStatusCreate, TaskStatusUpdate, TaskState, TaskStatusFilterParams
from app.services.task_manager import get_task_manager, TaskManager
from app.task.task_cancellation import cancel_task, cancel_child_tasks

router = APIRouter(prefix="/tasks", tags=["Tasks"])


def is_admin(user: Optional[User]) -> bool:
    """
    检查用户是否是管理员
    
    Args:
        user: 用户对象，可以为 None
        
    Returns:
        如果用户是管理员则返回 True，否则返回 False
    """
    if user is None:
        return False
    return user.is_superuser


@router.get(
    "/", 
    response_model=List[TaskStatusResponse],
    summary="获取任务列表",
    description="获取任务列表，支持分页和筛选"
)
async def list_tasks(
    task_type: Optional[str] = Query(None, description="任务类型"),
    status: Optional[TaskState] = Query(None, description="任务状态"),
    user_id: Optional[str] = Query(None, description="用户ID"),
    from_date: Optional[datetime] = Query(None, description="开始日期"),
    to_date: Optional[datetime] = Query(None, description="结束日期"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(get_current_user),
    task_manager: TaskManager = Depends(get_task_manager)
):
    """
    获取任务列表，支持分页和筛选
    
    如果不是管理员，只能查看自己的任务
    """
    # 非管理员只能查看自己的任务
    if not is_admin(current_user):
        user_id = current_user.id
    
    tasks = task_manager.list_tasks(
        task_type=task_type,
        status=status,
        user_id=user_id,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset
    )
    
    # 转换元数据为JSON
    for task in tasks:
        if task.task_metadata:
            try:
                import json
                task.task_metadata = json.loads(task.task_metadata)
            except:
                task.task_metadata = {}
    
    return tasks


@router.get(
    "/count",
    response_model=Dict[str, int],
    summary="获取任务数量",
    description="获取符合条件的任务数量"
)
async def count_tasks(
    task_type: Optional[str] = Query(None, description="任务类型"),
    status: Optional[TaskState] = Query(None, description="任务状态"),
    user_id: Optional[str] = Query(None, description="用户ID"),
    from_date: Optional[datetime] = Query(None, description="开始日期"),
    to_date: Optional[datetime] = Query(None, description="结束日期"),
    current_user: User = Depends(get_current_user),
    task_manager: TaskManager = Depends(get_task_manager)
):
    """
    获取符合条件的任务数量
    
    如果不是管理员，只能查看自己的任务数量
    """
    # 非管理员只能查看自己的任务
    if not is_admin(current_user):
        user_id = current_user.id
    
    count = task_manager.count_tasks(
        task_type=task_type,
        status=status,
        user_id=user_id,
        from_date=from_date,
        to_date=to_date
    )
    
    return {"count": count}


@router.get(
    "/{task_id}",
    response_model=TaskStatusResponse,
    summary="获取任务详情",
    description="获取指定任务ID的详细信息"
)
async def get_task(
    task_id: str = Path(..., description="任务ID"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    task_manager: TaskManager = Depends(get_task_manager)
):
    """
    获取指定任务ID的详细信息
    
    如果用户已登录且不是管理员，只能查看自己的任务
    """
    task = task_manager.get_task(task_id)
    
    # 如果用户已登录且不是管理员，验证权限
    if current_user and not is_admin(current_user) and task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您无权查看此任务"
        )
    
    # 转换元数据为JSON
    if task.task_metadata:
        try:
            import json
            task.task_metadata = json.loads(task.task_metadata)
        except:
            task.task_metadata = {}
    
    return task


@router.delete(
    "/{task_id}",
    response_model=Dict[str, Any],
    summary="取消任务",
    description="取消指定的任务"
)
async def cancel_task_endpoint(
    task_id: str = Path(..., description="任务ID"),
    force: bool = Query(False, description="是否强制取消，针对已经开始运行的任务"),
    recursive: bool = Query(False, description="是否级联取消子任务"),
    current_user: User = Depends(get_current_user),
    task_manager: TaskManager = Depends(get_task_manager)
):
    """
    取消指定的任务
    
    Args:
        task_id: 任务ID
        force: 是否强制取消，针对已经开始运行的任务
        recursive: 是否级联取消子任务
        
    如果不是管理员，只能取消自己的任务
    任务必须处于等待中、运行中或重试中状态才能取消
    """
    task = task_manager.get_task(task_id)
    
    # 非管理员只能取消自己的任务
    if not is_admin(current_user) and task.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您无权取消此任务"
        )
    
    # 检查任务是否可以取消
    if task.status not in [
        TaskState.PENDING.value, 
        TaskState.RUNNING.value, 
        TaskState.RETRYING.value
    ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无法取消状态为 {task.status} 的任务"
        )
    
    # 取消任务
    result = cancel_task(
        task_id=task_id, 
        user_id=current_user.id, 
        is_admin=is_admin(current_user)
    )
    
    # 如果需要级联取消子任务
    if recursive and result.get("success", False):
        child_result = cancel_child_tasks(task_id)
        result["child_tasks"] = child_result
    
    if not result.get("success", False):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("message", "取消任务失败")
        )
    
    return result


@router.post(
    "/cancel-batch",
    response_model=Dict[str, Any],
    summary="批量取消任务",
    description="批量取消多个任务"
)
async def cancel_task_batch(
    task_ids: List[str],
    force: bool = Query(False, description="是否强制取消，针对已经开始运行的任务"),
    current_user: User = Depends(get_current_user),
    task_manager: TaskManager = Depends(get_task_manager)
):
    """
    批量取消任务
    
    Args:
        task_ids: 任务ID列表
        force: 是否强制取消
        
    如果不是管理员，只能取消自己的任务
    """
    is_user_admin = is_admin(current_user)
    
    results = {
        "total": len(task_ids),
        "success": 0,
        "failed": 0,
        "failed_tasks": []
    }
    
    for task_id in task_ids:
        try:
            # 获取任务信息
            try:
                task = task_manager.get_task(task_id)
            except Exception as e:
                results["failed"] += 1
                results["failed_tasks"].append({
                    "task_id": task_id,
                    "error": f"获取任务信息失败: {str(e)}"
                })
                continue
            
            # 检查权限
            if not is_user_admin and task.user_id != current_user.id:
                results["failed"] += 1
                results["failed_tasks"].append({
                    "task_id": task_id,
                    "error": "无权限取消此任务"
                })
                continue
            
            # 检查任务状态
            if task.status not in [
                TaskState.PENDING.value, 
                TaskState.RUNNING.value, 
                TaskState.RETRYING.value
            ]:
                results["failed"] += 1
                results["failed_tasks"].append({
                    "task_id": task_id,
                    "error": f"无法取消状态为 {task.status} 的任务"
                })
                continue
            
            # 取消任务
            cancel_result = cancel_task(
                task_id=task_id, 
                user_id=current_user.id, 
                is_admin=is_user_admin
            )
            
            if cancel_result.get("success", False):
                results["success"] += 1
            else:
                results["failed"] += 1
                results["failed_tasks"].append({
                    "task_id": task_id,
                    "error": cancel_result.get("message", "取消任务失败")
                })
                
        except Exception as e:
            results["failed"] += 1
            results["failed_tasks"].append({
                "task_id": task_id,
                "error": f"处理异常: {str(e)}"
            })
    
    return results


@router.delete(
    "/cleanup/{days}",
    response_model=Dict[str, Any],
    summary="清理旧任务",
    description="清理指定天数前的旧任务"
)
async def cleanup_old_tasks(
    days: int = Path(..., ge=1, le=365, description="保留天数"),
    current_user: User = Depends(get_current_user),
    task_manager: TaskManager = Depends(get_task_manager)
):
    """
    清理指定天数前的旧任务
    
    仅管理员可以执行此操作
    """
    # 仅管理员可以清理旧任务
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅管理员可以清理旧任务"
        )
    
    count = task_manager.cleanup_old_tasks(days)
    
    return {
        "message": f"成功清理了 {count} 个旧任务",
        "deleted_count": count
    }
