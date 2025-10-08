"""
任务队列管理服务
负责管理任务的排队、调度和并发控制
"""
from datetime import datetime, timedelta
from flask import current_app
from app import db
from app.models.Task import Task
from app.services.runninghub import RunningHubService
from app.services.central_queue_manager import central_queue_manager, TriggerSource
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
        # 只在字段存在时才设置started_at，但不设置timeout_at（将在RUNNING状态时设置）
        if hasattr(task, 'started_at'):
            task.started_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Task {task_id} status changed to PENDING")
        
        # 尝试立即处理队列
        central_queue_manager.request_queue_processing(
            trigger_source=TriggerSource.USER_START,
            reason=f"User started task {task_id}",
            task_id=task_id
        )
        
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
        central_queue_manager.request_queue_processing(
            trigger_source=TriggerSource.TASK_STOP,
            reason=f"Task {task_id} stopped",
            task_id=task_id
        )
        
        return True, "任务已停止"
    
    def process_queue(self):
        """处理任务队列 - 已弃用，请使用CentralQueueManager
        
        此方法已被CentralQueueManager替代，保留仅为兼容性。
        新代码应使用: central_queue_manager.request_queue_processing()
        """
        logger.warning("process_queue() is deprecated, use CentralQueueManager instead")
        # 委托给中央管理器处理
        central_queue_manager.request_queue_processing(
            trigger_source=TriggerSource.USER_START,  # 默认触发源
            reason="Legacy process_queue call"
        )
    
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
            
            # 记录完整的API调用参数
            import json
            api_params = {
                "workflow_id": task.workflow_id,
                "is_plus": is_plus,
                "nodeInfoList": []
            }
            
            for data in task.data:
                node_info = {
                    "nodeId": data.node_id,
                    "fieldName": data.field_name,
                    "fieldValue": data.field_value
                }
                api_params["nodeInfoList"].append(node_info)
            
            # 记录完整参数到日志
            params_log = TaskLog(
                task_id=task.task_id,
                message=f"📤 API调用完整参数: {json.dumps(api_params, ensure_ascii=False, indent=2)}"
            )
            db.session.add(params_log)
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
            
            # 查找长时间未更新的任务（基于started_at字段，使用配置的超时时间）
            timeout_minutes = current_app.config.get('TASK_TIMEOUT_MINUTES', 600)
            timeout_threshold = now - timedelta(minutes=timeout_minutes)
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
            central_queue_manager.request_queue_processing(
                trigger_source=TriggerSource.TIMEOUT_CHECK,
                reason=f"Processed {timeout_count} timeout tasks"
            )
        
        return timeout_count

# 全局任务队列服务实例
task_queue_service = TaskQueueService()