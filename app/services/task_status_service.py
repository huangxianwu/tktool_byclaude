"""
任务状态监控服务
负责监控RunningHub任务状态并更新本地数据库
"""
from datetime import datetime, timedelta
from flask import current_app
from app import db
from app.models.Task import Task
from app.models.TaskLog import TaskLog
from app.models.TaskOutput import TaskOutput
from app.services.runninghub import RunningHubService
from app.services.central_queue_manager import central_queue_manager, TriggerSource
from app.utils.timezone_helper import now_utc
import logging
import threading
import time

logger = logging.getLogger(__name__)

class TaskStatusService:
    def __init__(self):
        self.runninghub_service = RunningHubService()
        self.is_monitoring = False
        self.monitor_thread = None
        self.app = None
    
    def update_task_status(self, task_id):
        """更新单个任务的状态"""
        from app.models.TaskLog import TaskLog
        
        task = Task.query.get(task_id)
        if not task or not task.runninghub_task_id:
            return False
        
        # 记录状态检查开始
        check_log = TaskLog(
            task_id=task_id,
            message=f"🔍 检查任务状态 (远程ID: {task.runninghub_task_id})"
        )
        db.session.add(check_log)
        db.session.commit()
        
        try:
            # 从RunningHub获取任务状态
            api_log = TaskLog(
                task_id=task_id,
                message="📡 从RunningHub获取任务状态"
            )
            db.session.add(api_log)
            db.session.commit()
            
            status_info = self.runninghub_service.get_task_status(task.runninghub_task_id)
            
            if status_info:
                old_status = task.status
                new_status = self.map_runninghub_status(status_info.get('status', ''))
                
                status_log = TaskLog(
                    task_id=task_id,
                    message=f"📊 获取到状态信息: {status_info.get('status', 'unknown')} -> {new_status}"
                )
                db.session.add(status_log)
                db.session.commit()
                
                # 更新任务状态
                if new_status and new_status != old_status:
                    task.status = new_status
                    
                    # 如果任务状态变更为RUNNING，设置超时时间
                    if new_status == 'RUNNING' and hasattr(task, 'timeout_at'):
                        timeout_minutes = current_app.config.get('TASK_TIMEOUT_MINUTES', 600)
                        task.timeout_at = datetime.utcnow() + timedelta(minutes=timeout_minutes)
                    
                    # 如果任务完成，记录完成时间
                    if new_status in ['SUCCESS', 'FAILED']:
                        task.completed_at = datetime.utcnow()
                    
                    db.session.commit()
                    
                    update_log = TaskLog(
                        task_id=task_id,
                        message=f"🔄 任务状态已更新: {old_status} -> {new_status}"
                    )
                    db.session.add(update_log)
                    db.session.commit()
                    
                    logger.info(f"Task {task_id} status updated from {old_status} to {new_status}")
                    
                    # 如果任务完成，尝试启动队列中的下一个任务
                    if new_status in ['SUCCESS', 'FAILED']:
                        complete_log = TaskLog(
                            task_id=task_id,
                            message=f"🏁 任务已完成，触发队列处理"
                        )
                        db.session.add(complete_log)
                        db.session.commit()
                        
                        # 如果任务成功完成，自动获取并保存输出文件信息
                        if new_status == 'SUCCESS':
                            self._auto_fetch_task_outputs(task_id)
                        
                        # 任务完成后，通过中央管理器触发队列处理
                        central_queue_manager.request_queue_processing(
                            trigger_source=TriggerSource.TASK_COMPLETE,
                            reason=f"Task {task_id} completed with status {new_status}",
                            task_id=task_id
                        )
                else:
                    no_change_log = TaskLog(
                        task_id=task_id,
                        message=f"ℹ️ 状态无变化，保持: {old_status}"
                    )
                    db.session.add(no_change_log)
                    db.session.commit()
                
                return True
            else:
                error_log = TaskLog(
                    task_id=task_id,
                    message="❌ 未能获取到有效的状态信息"
                )
                db.session.add(error_log)
                db.session.commit()
            
        except Exception as e:
            exception_log = TaskLog(
                task_id=task_id,
                message=f"❌ 更新任务状态时发生异常: {str(e)}"
            )
            db.session.add(exception_log)
            db.session.commit()
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
        
        if not self.app:
            logger.error("Cannot start monitoring: app instance not set")
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
                if self.app:
                    with self.app.app_context():
                        # 更新所有运行中的任务状态
                        self.update_all_running_tasks()
                        
                        # 检查超时任务 - 但不自动触发队列处理
                        from app.services.task_queue_service import TaskQueueService
                        queue_service = TaskQueueService()
                        timeout_count = queue_service.check_timeout_tasks_without_queue_processing()
                        
                        if timeout_count > 0:
                            logger.warning(f"Found {timeout_count} timeout tasks, processing queue...")
                            # 只有在实际处理了超时任务时才通过中央管理器触发队列处理
                            central_queue_manager.request_queue_processing(
                                trigger_source=TriggerSource.STATUS_MONITOR,
                                reason=f"Found {timeout_count} timeout tasks"
                            )
                        
                        # 检查并处理PENDING状态的任务
                        self._process_pending_tasks(queue_service)
                        
                        # 等待下一次检查
                        time.sleep(self.app.config.get('STATUS_CHECK_INTERVAL', 10))
                else:
                    # 如果没有应用实例，使用默认间隔
                    time.sleep(10)
                
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
    
    def _process_pending_tasks(self, queue_service):
        """处理PENDING状态的任务 - 只有当RunningHub任务数为0时才处理队列"""
        try:
            # 查询所有PENDING状态的任务
            pending_tasks = Task.query.filter_by(status='PENDING').order_by(Task.created_at.asc()).all()
            
            if pending_tasks:
                # 检查RunningHub中是否有正在运行的任务
                current_tasks = self.runninghub_service.check_account_status()
                
                if current_tasks is None:
                    # 无法获取RunningHub状态时，使用本地数据库检查
                    running_count = Task.query.filter(Task.status.in_(['QUEUED', 'RUNNING'])).count()
                    can_process = running_count == 0
                else:
                    # 只有当RunningHub中没有任务时才处理队列
                    can_process = current_tasks == 0
                
                if can_process:
                    logger.info(f"Found {len(pending_tasks)} pending tasks and RunningHub is idle, processing queue...")
                    # 通过中央管理器触发队列处理
                    central_queue_manager.request_queue_processing(
                        trigger_source=TriggerSource.PENDING_CHECK,
                        reason="RunningHub is idle, processing pending tasks"
                    )
                else:
                    logger.debug(f"Found {len(pending_tasks)} pending tasks but RunningHub has {current_tasks} running tasks, waiting...")
        except Exception as e:
            logger.error(f"Error processing pending tasks: {e}")
    
    def get_task_outputs(self, task_id):
        """获取任务输出文件"""
        try:
            # 使用FileManager的fallback方法
            from app.services.file_manager import FileManager
            file_manager = FileManager()
            outputs = file_manager.get_task_outputs_with_fallback(task_id)
            return outputs
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
    
    def _auto_fetch_task_outputs(self, task_id):
        """任务完成时自动获取并保存输出文件信息到TaskOutput表"""
        try:
            task = Task.query.get(task_id)
            if not task or not task.runninghub_task_id:
                logger.warning(f"Task {task_id} not found or missing runninghub_task_id")
                return
            
            # 获取任务输出文件
            outputs = self.runninghub_service.get_outputs(task.runninghub_task_id, task_id)
            
            if not outputs:
                logger.info(f"No outputs found for task {task_id}")
                return
            
            # 创建TaskOutput记录
            from app.models.TaskOutput import TaskOutput
            from app.utils.timezone_helper import now_utc
            from sqlalchemy.exc import IntegrityError
            import os
            
            created_count = 0
            skipped_count = 0
            
            for output in outputs:
                try:
                    # 提取文件信息
                    node_id = output.get('nodeId', '')
                    file_url = output.get('fileUrl', '')
                    file_type = output.get('fileType', '')
                    file_size = output.get('fileSize', 0)
                    
                    if not file_url:
                        continue
                    
                    # 从URL中提取文件名
                    file_name = os.path.basename(file_url.split('?')[0])
                    
                    # 创建TaskOutput记录
                    task_output = TaskOutput(
                        task_id=task_id,
                        node_id=node_id,
                        name=file_name,
                        file_type=file_type,
                        file_size=file_size,
                        file_url=file_url,
                        thumbnail_path=None,
                        created_at=now_utc()
                    )
                    
                    db.session.add(task_output)
                    db.session.flush()  # 检查约束冲突
                    created_count += 1
                    
                    logger.info(f"Created TaskOutput record for task {task_id}, node {node_id}: {file_name}")
                    
                except IntegrityError:
                    # 记录已存在，跳过
                    db.session.rollback()
                    skipped_count += 1
                    logger.debug(f"TaskOutput record already exists for task {task_id}, node {node_id}")
                    continue
                except Exception as e:
                    logger.error(f"Error creating TaskOutput record for task {task_id}: {e}")
                    continue
            
            # 提交事务
            if created_count > 0:
                db.session.commit()
                
                # 记录成功日志
                success_log = TaskLog(
                    task_id=task_id,
                    message=f"✅ 自动获取输出文件完成：新建{created_count}个记录，跳过{skipped_count}个"
                )
                db.session.add(success_log)
                db.session.commit()
                
                logger.info(f"Auto-fetched outputs for task {task_id}: created {created_count}, skipped {skipped_count}")
            else:
                db.session.rollback()
                logger.info(f"No new TaskOutput records created for task {task_id}")
                
        except Exception as e:
            try:
                db.session.rollback()
            except:
                pass
            
            # 记录错误日志
            error_log = TaskLog(
                task_id=task_id,
                message=f"❌ 自动获取输出文件失败: {str(e)}"
            )
            db.session.add(error_log)
            db.session.commit()
            
            logger.error(f"Error auto-fetching outputs for task {task_id}: {e}")