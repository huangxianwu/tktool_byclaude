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
        """检查是否可以启动新任务 - 基于RunningHub实际任务数量"""
        try:
            # 检查RunningHub中的实际任务数量
            current_tasks = self.runninghub_service.check_account_status()
            if current_tasks is None:
                # 无法获取状态时，检查本地数据库作为备选
                running_count = Task.query.filter(Task.status.in_(['QUEUED', 'RUNNING'])).count()
                max_concurrent = current_app.config.get('MAX_CONCURRENT_TASKS', 1)
                return running_count < max_concurrent
            
            # 如果RunningHub没有任务在执行，可以启动新任务
            return current_tasks == 0
        except Exception as e:
            logger.error(f"Error checking if can start task: {e}")
            return True  # 如果出错，允许启动
    
    def get_next_pending_task(self):
        """获取下一个待执行的任务（按创建时间升序，FIFO原则）"""
        try:
            task = Task.query.filter_by(status='PENDING').order_by(Task.created_at.asc()).first()
            return task
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
        if task.status not in ['READY', 'FAILED', 'STOPPED', 'CANCELLED']:
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
            # 获取RunningHub当前任务数量用于日志
            current_tasks = self.runninghub_service.check_account_status()
            if current_tasks is not None and current_tasks > 0:
                logger.debug(f"RunningHub has {current_tasks} running tasks, waiting for completion")
            else:
                logger.debug("No available slots for new tasks")
            return
        
        # 获取下一个待执行的任务
        next_task = self.get_next_pending_task()
        if not next_task:
            logger.debug("No pending tasks in queue")
            return
        
        logger.info(f"Processing task {next_task.task_id} from queue")
        
        try:
            # 记录开始提交任务的日志
            from app.models.TaskLog import TaskLog
            start_log = TaskLog(
                task_id=next_task.task_id,
                message="🚀 开始提交任务到RunningHub..."
            )
            db.session.add(start_log)
            db.session.commit()
            
            # 提交任务到RunningHub
            success, runninghub_task_id, error_msg = self.submit_task_to_runninghub(next_task)
            
            if success:
                # 更新任务状态
                next_task.status = 'QUEUED'
                next_task.runninghub_task_id = runninghub_task_id
                next_task.started_at = datetime.utcnow()
                db.session.commit()
                
                logger.info(f"Task {next_task.task_id} submitted to RunningHub with ID: {runninghub_task_id}")
                
                # 记录成功提交的日志
                success_log = TaskLog(
                    task_id=next_task.task_id,
                    message=f"✅ 任务已成功提交到RunningHub (ID: {runninghub_task_id})"
                )
                db.session.add(success_log)
                db.session.commit()
            else:
                # 检查是否是队列满的错误
                if error_msg and 'TASK_QUEUE_MAXED' in error_msg:
                    # 队列满时，任务保持PENDING状态，等待下次处理
                    logger.info(f"RunningHub queue is full, task {next_task.task_id} remains in PENDING status")
                    
                    # 记录队列满的日志（避免重复记录）
                    from app.models.TaskLog import TaskLog
                    existing_queue_log = TaskLog.query.filter_by(
                        task_id=next_task.task_id
                    ).filter(
                        TaskLog.message.like('%队列已满%')
                    ).first()
                    
                    if not existing_queue_log:
                        queue_log = TaskLog(
                            task_id=next_task.task_id,
                            message=f"⏳ RunningHub队列已满，等待空闲槽位..."
                        )
                        db.session.add(queue_log)
                        db.session.commit()
                    return  # 不标记为失败，保持PENDING状态
                else:
                    # 其他错误，标记为失败
                    next_task.status = 'FAILED'
                    next_task.completed_at = datetime.utcnow()
                    
                    # 记录失败日志
                    from app.models.TaskLog import TaskLog
                    error_log = TaskLog(
                        task_id=next_task.task_id,
                        message=f"❌ 任务提交失败: {error_msg or 'Unknown error'}"
                    )
                    db.session.add(error_log)
                    db.session.commit()
                    
                    logger.error(f"Failed to submit task {next_task.task_id} to RunningHub: {error_msg}")
        
        except Exception as e:
            logger.error(f"Error processing queue: {e}")
            # 标记任务为失败
            next_task.status = 'FAILED'
            next_task.completed_at = datetime.utcnow()
            
            # 记录异常日志
            from app.models.TaskLog import TaskLog
            exception_log = TaskLog(
                task_id=next_task.task_id,
                message=f"❌ 队列处理异常: {str(e)}"
            )
            db.session.add(exception_log)
            db.session.commit()
    
    def submit_task_to_runninghub(self, task):
        """提交任务到RunningHub"""
        from app.models.TaskLog import TaskLog
        from app import db
        
        # 记录任务提交开始
        start_log = TaskLog(
            task_id=task.task_id,
            message=f"🚀 开始提交任务到RunningHub (工作流ID: {task.workflow_id})"
        )
        db.session.add(start_log)
        db.session.commit()
        
        try:
            # 获取任务数据
            data_log = TaskLog(
                task_id=task.task_id,
                message=f"📋 准备任务数据，共 {len(task.data)} 个节点参数"
            )
            db.session.add(data_log)
            db.session.commit()
            
            task_data = []
            for data in task.data:
                task_data.append({
                    'node_id': data.node_id,
                    'field_name': data.field_name,
                    'field_value': data.field_value
                })
            
            # 调用RunningHub API创建任务，传递is_plus参数
            is_plus = getattr(task, 'is_plus', False)  # 处理兼容性
            api_log = TaskLog(
                task_id=task.task_id,
                message=f"🔗 调用RunningHub API创建任务 (Plus模式: {is_plus})"
            )
            db.session.add(api_log)
            db.session.commit()
            
            result = self.runninghub_service.create_task(task.workflow_id, task_data, is_plus)
            
            if result and 'taskId' in result:
                success_log = TaskLog(
                    task_id=task.task_id,
                    message=f"✅ 任务成功提交到RunningHub，远程任务ID: {result['taskId']}"
                )
                db.session.add(success_log)
                db.session.commit()
                return True, result['taskId'], None
            else:
                error_msg = "Invalid response from RunningHub"
                error_log = TaskLog(
                    task_id=task.task_id,
                    message=f"❌ RunningHub返回无效响应: {result}"
                )
                db.session.add(error_log)
                db.session.commit()
                logger.error(f"{error_msg}: {result}")
                return False, None, error_msg
                
        except Exception as e:
            error_msg = str(e)
            exception_log = TaskLog(
                task_id=task.task_id,
                message=f"❌ 提交任务到RunningHub时发生异常: {error_msg}"
            )
            db.session.add(exception_log)
            db.session.commit()
            logger.error(f"Error submitting task to RunningHub: {error_msg}")
            return False, None, error_msg
    
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
    
    def check_timeout_tasks_without_queue_processing(self):
        """检查并处理超时任务，但不自动触发队列处理"""
        try:
            now = datetime.utcnow()
            
            # 查找超时的任务（基于timeout_at字段）
            timeout_tasks = Task.query.filter(
                Task.timeout_at < now,
                Task.status.in_(['PENDING', 'QUEUED', 'RUNNING'])
            ).all()
            
            # 查找长时间未更新的任务（基于started_at字段，超过30分钟）
            timeout_threshold = now - timedelta(minutes=30)
            stale_tasks = Task.query.filter(
                Task.started_at < timeout_threshold,
                Task.status.in_(['QUEUED', 'RUNNING']),
                Task.started_at.isnot(None)  # 确保有started_at时间
            ).all()
            
            all_timeout_tasks = timeout_tasks + stale_tasks
            
            for task in all_timeout_tasks:
                logger.warning(f"Task {task.task_id} timed out (status: {task.status}, started: {task.started_at})")
                
                # 如果任务在RunningHub中运行，尝试取消
                if task.runninghub_task_id and task.status in ['QUEUED', 'RUNNING']:
                    try:
                        self.runninghub_service.cancel_task(task.runninghub_task_id)
                        logger.info(f"Cancelled task {task.runninghub_task_id} on RunningHub")
                    except Exception as e:
                        logger.error(f"Failed to cancel task on RunningHub: {e}")
                
                # 更新任务状态
                task.status = 'FAILED'
                task.completed_at = now
                
                # 记录超时日志
                from app.models.TaskLog import TaskLog
                timeout_log = TaskLog(
                    task_id=task.task_id,
                    message=f"❌ 任务超时失败 - 执行时间超过30分钟"
                )
                db.session.add(timeout_log)
            
            if all_timeout_tasks:
                db.session.commit()
                logger.info(f"Marked {len(all_timeout_tasks)} tasks as failed due to timeout")
            
            return len(all_timeout_tasks)
            
        except Exception as e:
            logger.error(f"Error checking timeout tasks: {e}")
            db.session.rollback()
            return 0
    
    def check_timeout_tasks(self):
        """检查并处理超时任务（保持原有接口兼容性）"""
        timeout_count = self.check_timeout_tasks_without_queue_processing()
        
        # 如果有超时任务，处理队列
        if timeout_count > 0:
            self.process_queue()
        
        return timeout_count

# 全局任务队列服务实例
task_queue_service = TaskQueueService()