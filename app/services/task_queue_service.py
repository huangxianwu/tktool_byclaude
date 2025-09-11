"""
任务队列管理服务
负责管理任务的排队、调度和并发控制
"""
from datetime import datetime, timedelta
from flask import current_app
from app import db
from app.models.Task import Task
from app.services.runninghub import RunningHubService
import logging

logger = logging.getLogger(__name__)

class TaskQueueService:
    def __init__(self):
        self.runninghub_service = RunningHubService()
    
    def get_queue_status(self):
        """获取队列状态"""
        try:
            pending_count = Task.query.filter_by(status='PENDING').count()
            running_count = Task.query.filter(Task.status.in_(['QUEUED', 'RUNNING'])).count()
            
            return {
                'pending_tasks': pending_count,
                'running_tasks': running_count,
                'max_concurrent': current_app.config.get('MAX_CONCURRENT_TASKS', 1)
            }
        except Exception as e:
            logger.error(f"Error getting queue status: {e}")
            return {
                'pending_tasks': 0,
                'running_tasks': 0,
                'max_concurrent': current_app.config.get('MAX_CONCURRENT_TASKS', 1)
            }
    
    def can_start_task(self):
        """检查是否可以启动新任务"""
        try:
            running_count = Task.query.filter(Task.status.in_(['QUEUED', 'RUNNING'])).count()
            max_concurrent = current_app.config.get('MAX_CONCURRENT_TASKS', 1)
            return running_count < max_concurrent
        except Exception as e:
            logger.error(f"Error checking if can start task: {e}")
            return True  # 如果出错，允许启动
    
    def get_next_pending_task(self):
        """获取下一个待执行的任务（按创建时间排序）"""
        try:
            return Task.query.filter_by(status='PENDING').order_by(Task.created_at.asc()).first()
        except Exception as e:
            logger.error(f"Error getting next pending task: {e}")
            return None
    
    def start_task(self, task_id):
        """启动单个任务"""
        task = Task.query.get(task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return False, "任务不存在"
        
        # 检查任务状态
        if task.status not in ['READY', 'FAILED', 'STOPPED']:
            logger.warning(f"Task {task_id} cannot be started, current status: {task.status}")
            return False, f"任务状态 {task.status} 不允许启动"
        
        # 更新任务状态为PENDING
        task.status = 'PENDING'
        # 只在字段存在时才设置
        if hasattr(task, 'started_at'):
            task.started_at = datetime.utcnow()
        if hasattr(task, 'timeout_at'):
            timeout_minutes = current_app.config.get('TASK_TIMEOUT_MINUTES', 30)
            task.timeout_at = datetime.utcnow() + timedelta(minutes=timeout_minutes)
        db.session.commit()
        
        logger.info(f"Task {task_id} status changed to PENDING")
        
        # 尝试立即处理队列
        self.process_queue()
        
        return True, "任务已加入队列"
    
    def stop_task(self, task_id):
        """停止单个任务"""
        task = Task.query.get(task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return False, "任务不存在"
        
        # 检查任务状态
        if task.status not in ['PENDING', 'QUEUED', 'RUNNING']:
            logger.warning(f"Task {task_id} cannot be stopped, current status: {task.status}")
            return False, f"任务状态 {task.status} 不允许停止"
        
        # 如果任务已经在RunningHub中运行，需要调用API停止
        if task.status in ['QUEUED', 'RUNNING'] and task.runninghub_task_id:
            try:
                # 调用RunningHub API停止任务
                success = self.runninghub_service.cancel_task(task.runninghub_task_id)
                if not success:
                    logger.warning(f"Failed to cancel task {task.runninghub_task_id} on RunningHub")
            except Exception as e:
                logger.error(f"Error canceling task on RunningHub: {e}")
        
        # 更新任务状态
        task.status = 'STOPPED'
        if hasattr(task, 'completed_at'):
            task.completed_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Task {task_id} stopped")
        
        # 处理队列，启动下一个任务
        self.process_queue()
        
        return True, "任务已停止"
    
    def process_queue(self):
        """处理任务队列，启动下一个可执行的任务"""
        # 检查是否有可用的执行槽位
        if not self.can_start_task():
            logger.debug("No available slots for new tasks")
            return
        
        # 获取下一个待执行的任务
        next_task = self.get_next_pending_task()
        if not next_task:
            logger.debug("No pending tasks in queue")
            return
        
        try:
            # 提交任务到RunningHub
            success, runninghub_task_id = self.submit_task_to_runninghub(next_task)
            
            if success:
                # 更新任务状态
                next_task.status = 'QUEUED'
                next_task.runninghub_task_id = runninghub_task_id
                db.session.commit()
                
                logger.info(f"Task {next_task.task_id} submitted to RunningHub with ID: {runninghub_task_id}")
            else:
                # 提交失败，标记为失败
                next_task.status = 'FAILED'
                if hasattr(next_task, 'completed_at'):
                    next_task.completed_at = datetime.utcnow()
                db.session.commit()
                
                logger.error(f"Failed to submit task {next_task.task_id} to RunningHub")
        
        except Exception as e:
            logger.error(f"Error processing queue: {e}")
            # 标记任务为失败
            next_task.status = 'FAILED'
            if hasattr(next_task, 'completed_at'):
                next_task.completed_at = datetime.utcnow()
            db.session.commit()
    
    def submit_task_to_runninghub(self, task):
        """提交任务到RunningHub"""
        try:
            # 获取任务数据
            task_data = []
            for data in task.data:
                task_data.append({
                    'node_id': data.node_id,
                    'field_name': data.field_name,
                    'field_value': data.field_value
                })
            
            # 调用RunningHub API创建任务，传递is_plus参数
            is_plus = getattr(task, 'is_plus', False)  # 处理兼容性
            result = self.runninghub_service.create_task(task.workflow_id, task_data, is_plus)
            
            if result and 'taskId' in result:
                return True, result['taskId']
            else:
                logger.error(f"Invalid response from RunningHub: {result}")
                return False, None
                
        except Exception as e:
            logger.error(f"Error submitting task to RunningHub: {e}")
            return False, None
    
    def batch_start_tasks(self, task_ids):
        """批量启动任务"""
        results = []
        
        for task_id in task_ids:
            success, message = self.start_task(task_id)
            results.append({
                'task_id': task_id,
                'success': success,
                'message': message
            })
        
        return results
    
    def batch_stop_tasks(self, task_ids):
        """批量停止任务"""
        results = []
        
        for task_id in task_ids:
            success, message = self.stop_task(task_id)
            results.append({
                'task_id': task_id,
                'success': success,
                'message': message
            })
        
        return results
    
    def check_timeout_tasks(self):
        """检查超时的任务"""
        try:
            timeout_threshold = datetime.utcnow()
            # 只有在timeout_at字段存在的情况下才检查超时
            timeout_tasks = []
            if hasattr(Task, 'timeout_at'):
                timeout_tasks = Task.query.filter(
                    Task.timeout_at < timeout_threshold,
                    Task.status.in_(['QUEUED', 'RUNNING'])
                ).all()
            
            for task in timeout_tasks:
                logger.warning(f"Task {task.task_id} timed out")
                task.status = 'FAILED'
                if hasattr(task, 'completed_at'):
                    task.completed_at = datetime.utcnow()
            
            if timeout_tasks:
                db.session.commit()
                # 处理队列，启动下一个任务
                self.process_queue()
            
            return len(timeout_tasks)
        except Exception as e:
            logger.error(f"Error checking timeout tasks: {e}")
            return 0