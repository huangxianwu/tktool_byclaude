"""故障恢复服务
负责系统重启后的任务状态同步和数据完整性恢复
"""
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from flask import current_app
from app import db
from app.models.Task import Task
from app.models.TaskLog import TaskLog
from app.models.TaskOutput import TaskOutput
from app.services.runninghub import RunningHubService
from app.services.file_manager import FileManager

logger = logging.getLogger(__name__)

class RecoveryService:
    """故障恢复服务 - 处理系统重启后的任务状态同步"""
    
    def __init__(self):
        self.runninghub_service = RunningHubService()
        self.file_manager = FileManager()
        self.recovery_stats = {
            'total_tasks': 0,
            'synced_tasks': 0,
            'failed_tasks': 0,
            'completed_tasks': 0,
            'running_tasks': 0,
            'missing_tasks': 0,
            'start_time': None,
            'end_time': None
        }
    
    def perform_recovery(self, delay_seconds: int = 3) -> Dict[str, Any]:
        """执行故障恢复
        
        Args:
            delay_seconds: 延迟启动秒数，确保所有服务就绪
            
        Returns:
            恢复统计信息
        """
        logger.info(f"Starting system recovery in {delay_seconds} seconds...")
        time.sleep(delay_seconds)
        
        self.recovery_stats['start_time'] = datetime.utcnow()
        
        try:
            # 1. 识别需要同步的任务
            tasks_to_sync = self._identify_tasks_to_sync()
            self.recovery_stats['total_tasks'] = len(tasks_to_sync)
            
            if not tasks_to_sync:
                logger.info("No tasks need recovery")
                self.recovery_stats['end_time'] = datetime.utcnow()
                return self.recovery_stats
            
            logger.info(f"Found {len(tasks_to_sync)} tasks that need recovery")
            
            # 2. 批量查询任务状态
            status_results = self._batch_query_task_status(tasks_to_sync)
            
            # 3. 同步任务状态
            self._sync_task_status(tasks_to_sync, status_results)
            
            # 4. 恢复数据完整性
            self._restore_data_integrity(tasks_to_sync, status_results)
            
            # 5. 重建并发控制
            self._rebuild_concurrency_control()
            
            self.recovery_stats['end_time'] = datetime.utcnow()
            duration = (self.recovery_stats['end_time'] - self.recovery_stats['start_time']).total_seconds()
            
            logger.info(f"Recovery completed in {duration:.2f} seconds")
            logger.info(f"Recovery stats: {self.recovery_stats}")
            
            return self.recovery_stats
            
        except Exception as e:
            logger.error(f"Recovery failed: {e}")
            self.recovery_stats['end_time'] = datetime.utcnow()
            raise
    
    def _identify_tasks_to_sync(self) -> List[Task]:
        """识别需要同步的任务"""
        try:
            # 查找所有未完成且有runninghub_task_id的任务
            tasks = Task.query.filter(
                Task.status.in_(['PENDING', 'QUEUED', 'RUNNING']),
                Task.runninghub_task_id.isnot(None),
                Task.runninghub_task_id != ''
            ).all()
            
            logger.info(f"Found {len(tasks)} tasks with incomplete status")
            
            # 记录需要同步的任务
            for task in tasks:
                logger.info(f"Task {task.task_id} (RunningHub: {task.runninghub_task_id}) - Status: {task.status}")
            
            return tasks
            
        except Exception as e:
            logger.error(f"Failed to identify tasks to sync: {e}")
            return []
    
    def _batch_query_task_status(self, tasks: List[Task]) -> Dict[str, Dict[str, Any]]:
        """批量查询任务状态"""
        status_results = {}
        
        logger.info(f"Querying status for {len(tasks)} tasks...")
        
        for task in tasks:
            try:
                # 查询远程任务状态
                status_info = self.runninghub_service.get_task_status(task.runninghub_task_id)
                
                if status_info and 'status' in status_info:
                    remote_status = status_info['status'].upper()
                    status_results[task.task_id] = {
                        'exists': True,
                        'status': remote_status,
                        'runninghub_task_id': task.runninghub_task_id
                    }
                    logger.info(f"Task {task.task_id}: Remote status = {remote_status}")
                else:
                    # 任务不存在或查询失败
                    status_results[task.task_id] = {
                        'exists': False,
                        'status': None,
                        'runninghub_task_id': task.runninghub_task_id
                    }
                    logger.warning(f"Task {task.task_id}: Not found on RunningHub")
                
                # 避免请求过于频繁
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Failed to query status for task {task.task_id}: {e}")
                status_results[task.task_id] = {
                    'exists': False,
                    'status': None,
                    'error': str(e),
                    'runninghub_task_id': task.runninghub_task_id
                }
        
        return status_results
    
    def _sync_task_status(self, tasks: List[Task], status_results: Dict[str, Dict[str, Any]]):
        """同步任务状态"""
        for task in tasks:
            try:
                result = status_results.get(task.task_id, {})
                
                if result.get('exists', False):
                    # 远程任务存在，同步状态
                    remote_status = result['status']
                    self._sync_existing_task(task, remote_status)
                else:
                    # 远程任务不存在，处理丢失任务
                    self._handle_missing_task(task)
                    
            except Exception as e:
                logger.error(f"Failed to sync task {task.task_id}: {e}")
                self.recovery_stats['failed_tasks'] += 1
    
    def _sync_existing_task(self, task: Task, remote_status: str):
        """同步存在的任务"""
        old_status = task.status
        
        # 映射RunningHub状态到本地状态
        status_mapping = {
            'QUEUE': 'QUEUED',
            'QUEUED': 'QUEUED', 
            'RUNNING': 'RUNNING',
            'SUCCESS': 'SUCCESS',
            'FAILED': 'FAILED'
        }
        
        new_status = status_mapping.get(remote_status, remote_status)
        
        if old_status != new_status:
            # 更新任务状态
            task.status = new_status
            
            # 设置完成时间
            if new_status in ['SUCCESS', 'FAILED'] and not task.completed_at:
                task.completed_at = datetime.utcnow()
            
            # 重新设置超时时间（对于运行中的任务）
            if new_status == 'RUNNING':
                timeout_minutes = current_app.config.get('TASK_TIMEOUT_MINUTES', 600)
                task.timeout_at = datetime.utcnow() + timedelta(minutes=timeout_minutes)
            
            db.session.commit()
            
            # 记录恢复日志
            recovery_log = TaskLog(
                task_id=task.task_id,
                message=f"🔄 系统恢复：状态已同步 {old_status} → {new_status}"
            )
            db.session.add(recovery_log)
            db.session.commit()
            
            logger.info(f"Task {task.task_id} status synced: {old_status} → {new_status}")
            
            # 更新统计
            if new_status in ['SUCCESS', 'FAILED']:
                self.recovery_stats['completed_tasks'] += 1
            elif new_status in ['QUEUED', 'RUNNING']:
                self.recovery_stats['running_tasks'] += 1
        
        self.recovery_stats['synced_tasks'] += 1
    
    def _handle_missing_task(self, task: Task):
        """处理丢失的任务"""
        # 检查任务启动时间
        if task.started_at:
            time_since_start = datetime.utcnow() - task.started_at
            
            # 如果超过2小时，标记为失败
            if time_since_start > timedelta(hours=2):
                old_status = task.status
                task.status = 'FAILED'
                task.completed_at = datetime.utcnow()
                
                db.session.commit()
                
                # 记录失败日志
                failure_log = TaskLog(
                    task_id=task.task_id,
                    message=f"❌ 系统恢复：任务在RunningHub上不存在，已标记为失败 (运行时间: {time_since_start})"
                )
                db.session.add(failure_log)
                db.session.commit()
                
                logger.warning(f"Task {task.task_id} marked as FAILED (missing on RunningHub, runtime: {time_since_start})")
                self.recovery_stats['completed_tasks'] += 1
            else:
                # 时间较短，重置为READY状态
                old_status = task.status
                task.status = 'READY'
                task.runninghub_task_id = None
                task.started_at = None
                
                db.session.commit()
                
                # 记录重置日志
                reset_log = TaskLog(
                    task_id=task.task_id,
                    message=f"🔄 系统恢复：任务重置为READY状态，可重新执行"
                )
                db.session.add(reset_log)
                db.session.commit()
                
                logger.info(f"Task {task.task_id} reset to READY (missing on RunningHub, runtime: {time_since_start})")
        else:
            # 没有启动时间，直接重置为READY
            task.status = 'READY'
            task.runninghub_task_id = None
            
            db.session.commit()
            
            reset_log = TaskLog(
                task_id=task.task_id,
                message=f"🔄 系统恢复：任务重置为READY状态"
            )
            db.session.add(reset_log)
            db.session.commit()
            
            logger.info(f"Task {task.task_id} reset to READY (no start time)")
        
        self.recovery_stats['missing_tasks'] += 1
    
    def _restore_data_integrity(self, tasks: List[Task], status_results: Dict[str, Dict[str, Any]]):
        """恢复数据完整性"""
        logger.info("Starting data integrity restoration...")
        
        for task in tasks:
            try:
                result = status_results.get(task.task_id, {})
                
                # 只处理已完成的任务
                if result.get('exists', False) and task.status == 'SUCCESS':
                    self._restore_task_outputs(task)
                    
            except Exception as e:
                logger.error(f"Failed to restore data integrity for task {task.task_id}: {e}")
    
    def _restore_task_outputs(self, task: Task):
        """恢复任务输出文件"""
        try:
            # 获取远程输出列表
            remote_outputs = self.runninghub_service.get_task_outputs(task.runninghub_task_id)
            
            if not remote_outputs:
                return
            
            # 检查本地输出记录
            local_outputs = TaskOutput.query.filter_by(task_id=task.task_id).all()
            local_output_names = {output.name for output in local_outputs}
            
            # 下载缺失的输出文件
            for remote_output in remote_outputs:
                output_name = remote_output['name']
                
                if output_name not in local_output_names:
                    logger.info(f"Downloading missing output: {output_name} for task {task.task_id}")
                    
                    # 下载文件
                    file_content = self.runninghub_service.download_output_file(
                        task.runninghub_task_id, output_name
                    )
                    
                    if file_content:
                        # 保存文件
                        file_path = self.file_manager.save_output_file(
                            task.task_id, output_name, file_content
                        )
                        
                        # 创建输出记录
                        task_output = TaskOutput(
                            task_id=task.task_id,
                            name=output_name,
                            file_path=file_path,
                            file_type=remote_output.get('type', ''),
                            node_id=remote_output.get('node_id', '')
                        )
                        db.session.add(task_output)
                        
                        logger.info(f"Restored output file: {output_name}")
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Failed to restore outputs for task {task.task_id}: {e}")
    
    def _rebuild_concurrency_control(self):
        """重建并发控制"""
        try:
            # 统计当前运行中的任务数量
            running_count = Task.query.filter(
                Task.status.in_(['QUEUED', 'RUNNING'])
            ).count()
            
            logger.info(f"Current running tasks: {running_count}")
            
            # 这里可以重置并发控制相关的状态
            # 具体实现取决于并发控制的机制
            
        except Exception as e:
            logger.error(f"Failed to rebuild concurrency control: {e}")
    
    def get_recovery_stats(self) -> Dict[str, Any]:
        """获取恢复统计信息"""
        return self.recovery_stats.copy()
    
    def manual_sync_task(self, task_id: str) -> bool:
        """手动同步单个任务"""
        try:
            task = Task.query.filter_by(task_id=task_id).first()
            if not task or not task.runninghub_task_id:
                return False
            
            # 查询远程状态
            status_info = self.runninghub_service.get_task_status(task.runninghub_task_id)
            
            if status_info and 'status' in status_info:
                remote_status = status_info['status'].upper()
                self._sync_existing_task(task, remote_status)
                
                # 如果任务已完成，恢复输出文件
                if task.status == 'SUCCESS':
                    self._restore_task_outputs(task)
                
                return True
            else:
                self._handle_missing_task(task)
                return True
                
        except Exception as e:
            logger.error(f"Failed to manually sync task {task_id}: {e}")
            return False

# 全局恢复服务实例
recovery_service = RecoveryService()