"""
任务状态管理服务
负责管理和跟踪Celery任务状态
"""
import json
import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from fastapi import HTTPException, status, Depends

from app.models.task import TaskStatus, TaskState, TaskStatusCreate, TaskStatusUpdate
from app.models.database import get_db
import json

logger = logging.getLogger(__name__)


class TaskManager:
    """任务管理器"""
    
    def __init__(self, db: Session):
        """初始化任务管理器"""
        self.db = db
    
    def create_task(self, task_data: TaskStatusCreate) -> TaskStatus:
        """
        创建任务状态记录
        
        Args:
            task_data: 任务数据
            
        Returns:
            任务状态记录
        """
        try:
            task_status = TaskStatus(
                task_id=task_data.task_id,
                task_name=task_data.task_name,
                task_type=task_data.task_type,
                status=task_data.status.value,
                progress=task_data.progress,
                retries=task_data.retries,
                max_retries=task_data.max_retries,
                user_id=task_data.user_id,
                created_at=datetime.now()
            )
            
            # 如果有元数据，转为JSON字符串
            if task_data.task_metadata:
                task_status.task_metadata = json.dumps(task_data.task_metadata)
            
            self.db.add(task_status)
            self.db.commit()
            self.db.refresh(task_status)
            
            logger.info(f"创建任务状态记录: {task_status.id}, task_id: {task_status.task_id}")
            return task_status
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"创建任务状态记录失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"创建任务状态记录失败: {str(e)}"
            )
    
    def update_task(self, task_id: str, update_data: TaskStatusUpdate) -> TaskStatus:
        """
        更新任务状态
        
        Args:
            task_id: 任务ID
            update_data: 更新数据
            
        Returns:
            更新后的任务状态
        """
        task_status = self.db.query(TaskStatus).filter(TaskStatus.task_id == task_id).first()
        
        if not task_status:
            logger.warning(f"任务不存在: {task_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"任务不存在: {task_id}"
            )
        
        try:
            # 更新状态
            if update_data.status is not None:
                task_status.status = update_data.status.value
                
                # 如果状态变为运行中，且开始时间未设置，则设置开始时间
                if update_data.status == TaskState.RUNNING and not task_status.started_at:
                    task_status.started_at = datetime.now()
                
                # 如果状态变为完成或失败，且完成时间未设置，则设置完成时间
                if update_data.status in [TaskState.COMPLETED, TaskState.FAILED] and not task_status.completed_at:
                    task_status.completed_at = datetime.now()
            
            # 更新其他字段
            if update_data.progress is not None:
                task_status.progress = update_data.progress
                
            if update_data.result is not None:
                task_status.result = update_data.result
                
            if update_data.error is not None:
                task_status.error = update_data.error
                
            if update_data.retries is not None:
                task_status.retries = update_data.retries
                
            if update_data.started_at is not None:
                task_status.started_at = update_data.started_at
                
            if update_data.completed_at is not None:
                task_status.completed_at = update_data.completed_at
            
            # 更新元数据
            if update_data.task_metadata is not None:
                task_status.task_metadata = json.dumps(update_data.task_metadata)
            
            self.db.commit()
            self.db.refresh(task_status)
            
            logger.info(f"更新任务状态: {task_id}, 新状态: {task_status.status}")
            return task_status
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新任务状态失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"更新任务状态失败: {str(e)}"
            )
    
    def get_task(self, task_id: str) -> TaskStatus:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态
        """
        task_status = self.db.query(TaskStatus).filter(TaskStatus.task_id == task_id).first()
        
        if not task_status:
            logger.warning(f"任务不存在: {task_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"任务不存在: {task_id}"
            )
            
        return task_status
    
    def list_tasks(
        self, 
        task_type: Optional[str] = None,
        status: Optional[TaskState] = None,
        user_id: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[TaskStatus]:
        """
        列出任务
        
        Args:
            task_type: 任务类型
            status: 任务状态
            user_id: 用户ID
            from_date: 开始日期
            to_date: 结束日期
            limit: 限制数量
            offset: 偏移量
            
        Returns:
            任务列表
        """
        query = self.db.query(TaskStatus)
        
        # 应用过滤条件
        if task_type:
            query = query.filter(TaskStatus.task_type == task_type)
            
        if status:
            query = query.filter(TaskStatus.status == status.value)
            
        if user_id:
            query = query.filter(TaskStatus.user_id == user_id)
            
        if from_date:
            query = query.filter(TaskStatus.created_at >= from_date)
            
        if to_date:
            query = query.filter(TaskStatus.created_at <= to_date)
        
        # 应用排序、分页
        query = query.order_by(desc(TaskStatus.created_at)).offset(offset).limit(limit)
        
        return query.all()
    
    def count_tasks(
        self, 
        task_type: Optional[str] = None,
        status: Optional[TaskState] = None,
        user_id: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> int:
        """
        统计任务数量
        
        Args:
            task_type: 任务类型
            status: 任务状态
            user_id: 用户ID
            from_date: 开始日期
            to_date: 结束日期
            
        Returns:
            任务数量
        """
        query = self.db.query(TaskStatus)
        
        # 应用过滤条件
        if task_type:
            query = query.filter(TaskStatus.task_type == task_type)
            
        if status:
            query = query.filter(TaskStatus.status == status.value)
            
        if user_id:
            query = query.filter(TaskStatus.user_id == user_id)
            
        if from_date:
            query = query.filter(TaskStatus.created_at >= from_date)
            
        if to_date:
            query = query.filter(TaskStatus.created_at <= to_date)
        
        return query.count()
    
    def update_task_progress(self, task_id: str, progress: float) -> TaskStatus:
        """
        更新任务进度
        
        Args:
            task_id: 任务ID
            progress: 进度 (0-100)
            
        Returns:
            更新后的任务状态
        """
        return self.update_task(
            task_id=task_id,
            update_data=TaskStatusUpdate(progress=progress)
        )
    
    def mark_task_running(self, task_id: str) -> TaskStatus:
        """
        标记任务为运行中
        
        Args:
            task_id: 任务ID
            
        Returns:
            更新后的任务状态
        """
        return self.update_task(
            task_id=task_id,
            update_data=TaskStatusUpdate(
                status=TaskState.RUNNING,
                started_at=datetime.now()
            )
        )
    
    def mark_task_completed(
        self, 
        task_id: str,
        result: Optional[str] = None
    ) -> TaskStatus:
        """
        标记任务为已完成
        
        Args:
            task_id: 任务ID
            result: 结果
            
        Returns:
            更新后的任务状态
        """
        return self.update_task(
            task_id=task_id,
            update_data=TaskStatusUpdate(
                status=TaskState.COMPLETED,
                progress=100.0,
                result=result,
                completed_at=datetime.now()
            )
        )
    
    def mark_task_failed(
        self, 
        task_id: str,
        error: str
    ) -> TaskStatus:
        """
        标记任务为失败
        
        Args:
            task_id: 任务ID
            error: 错误信息
            
        Returns:
            更新后的任务状态
        """
        return self.update_task(
            task_id=task_id,
            update_data=TaskStatusUpdate(
                status=TaskState.FAILED,
                error=error,
                completed_at=datetime.now()
            )
        )
    
    def cancel_task(self, task_id: str) -> TaskStatus:
        """
        取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            更新后的任务状态
        """
        return self.update_task(
            task_id=task_id,
            update_data=TaskStatusUpdate(
                status=TaskState.CANCELLED,
                completed_at=datetime.now()
            )
        )
    
    def cleanup_old_tasks(self, days: int = 30) -> int:
        """
        清理旧任务
        
        Args:
            days: 保留天数
            
        Returns:
            删除的任务数量
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        try:
            # 获取要删除的任务数量
            count = self.db.query(TaskStatus).filter(
                TaskStatus.created_at < cutoff_date
            ).count()
            
            # 删除旧任务
            self.db.query(TaskStatus).filter(
                TaskStatus.created_at < cutoff_date
            ).delete(synchronize_session=False)
            
            self.db.commit()
            logger.info(f"清理了 {count} 个旧任务")
            
            return count
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"清理旧任务失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"清理旧任务失败: {str(e)}"
            )


# 创建依赖注入函数
def get_task_manager(db: Session = Depends(get_db)) -> TaskManager:
    """获取任务管理器实例"""
    return TaskManager(db=db)
