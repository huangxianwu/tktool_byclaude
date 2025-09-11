"""
任务状态监控服务
负责监控RunningHub任务状态并更新本地数据库
"""
from datetime import datetime
from flask import current_app
from app import db
from app.models.Task import Task
from app.services.runninghub import RunningHubService
import logging
import threading
import time

logger = logging.getLogger(__name__)

class TaskStatusService:
    def __init__(self):
        self.runninghub_service = RunningHubService()
        self.is_monitoring = False
        self.monitor_thread = None
    
    def update_task_status(self, task_id):
        """更新单个任务的状态"""
        task = Task.query.get(task_id)
        if not task or not task.runninghub_task_id:
            return False
        
        try:
            # 从RunningHub获取任务状态
            status_info = self.runninghub_service.get_task_status(task.runninghub_task_id)
            
            if status_info:
                old_status = task.status
                new_status = self.map_runninghub_status(status_info.get('status', ''))
                
                # 更新任务状态
                if new_status and new_status != old_status:
                    task.status = new_status
                    
                    # 如果任务完成，记录完成时间
                    if new_status in ['SUCCESS', 'FAILED']:
                        task.completed_at = datetime.utcnow()
                    
                    db.session.commit()
                    logger.info(f"Task {task_id} status updated from {old_status} to {new_status}")
                    
                    # 如果任务完成，尝试启动队列中的下一个任务
                    if new_status in ['SUCCESS', 'FAILED']:
                        from app.services.task_queue_service import TaskQueueService
                        queue_service = TaskQueueService()
                        queue_service.process_queue()
                
                return True
            
        except Exception as e:
            logger.error(f"Error updating task status for {task_id}: {e}")
        
        return False
    
    def map_runninghub_status(self, runninghub_status):
        """将RunningHub状态映射到本地状态"""
        status_mapping = {
            'queue': 'QUEUED',
            'queued': 'QUEUED',
            'running': 'RUNNING',
            'success': 'SUCCESS',
            'failed': 'FAILED',
            'error': 'FAILED',
            'cancelled': 'STOPPED',
            'canceled': 'STOPPED'
        }
        
        return status_mapping.get(runninghub_status.lower(), None)
    
    def update_all_running_tasks(self):
        """更新所有正在运行的任务状态"""
        running_tasks = Task.query.filter(
            Task.status.in_(['QUEUED', 'RUNNING']),
            Task.runninghub_task_id.isnot(None)
        ).all()
        
        updated_count = 0
        for task in running_tasks:
            if self.update_task_status(task.task_id):
                updated_count += 1
        
        logger.debug(f"Updated {updated_count} running tasks")
        return updated_count
    
    def get_task_details(self, task_id):
        """获取任务详细信息"""
        task = Task.query.get(task_id)
        if not task:
            return None
        
        result = task.to_dict()
        
        # 添加工作流信息
        if hasattr(task, 'workflow') and task.workflow:
            result['workflow_name'] = task.workflow.name
            result['node_count'] = len(task.workflow.nodes)
        
        # 添加任务数据
        result['data'] = [data.to_dict() for data in task.data]
        
        # 如果有RunningHub任务ID，获取详细状态
        if task.runninghub_task_id:
            try:
                runninghub_info = self.runninghub_service.get_task_status(task.runninghub_task_id)
                if runninghub_info:
                    result['runninghub_info'] = runninghub_info
            except Exception as e:
                logger.warning(f"Failed to get RunningHub info for task {task_id}: {e}")
        
        return result
    
    def start_monitoring(self):
        """启动状态监控"""
        if self.is_monitoring:
            logger.warning("Task monitoring is already running")
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Task status monitoring started")
    
    def stop_monitoring(self):
        """停止状态监控"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Task status monitoring stopped")
    
    def _monitor_loop(self):
        """监控循环"""
        while self.is_monitoring:
            try:
                # 更新所有运行中的任务状态
                self.update_all_running_tasks()
                
                # 检查超时任务
                from app.services.task_queue_service import TaskQueueService
                queue_service = TaskQueueService()
                timeout_count = queue_service.check_timeout_tasks()
                
                if timeout_count > 0:
                    logger.warning(f"Found {timeout_count} timeout tasks")
                
                # 等待下一次检查
                time.sleep(current_app.config.get('STATUS_CHECK_INTERVAL', 10))
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)  # 出错时短暂等待
    
    def get_task_progress(self, task_id):
        """获取任务进度信息"""
        task = Task.query.get(task_id)
        if not task or not task.runninghub_task_id:
            return None
        
        try:
            progress_info = self.runninghub_service.get_task_progress(task.runninghub_task_id)
            return progress_info
        except Exception as e:
            logger.error(f"Error getting task progress for {task_id}: {e}")
            return None
    
    def get_task_outputs(self, task_id):
        """获取任务输出文件"""
        task = Task.query.get(task_id)
        if not task or not task.runninghub_task_id:
            return []
        
        try:
            outputs = self.runninghub_service.get_task_outputs(task.runninghub_task_id)
            return outputs or []
        except Exception as e:
            logger.error(f"Error getting task outputs for {task_id}: {e}")
            return []
    
    def download_task_output(self, task_id, output_name):
        """下载任务输出文件"""
        task = Task.query.get(task_id)
        if not task or not task.runninghub_task_id:
            return None
        
        try:
            file_data = self.runninghub_service.download_output_file(task.runninghub_task_id, output_name)
            return file_data
        except Exception as e:
            logger.error(f"Error downloading task output {output_name} for {task_id}: {e}")
            return None