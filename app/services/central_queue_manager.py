"""集中式队列管理器
负责统一管理所有任务队列的处理请求，避免并发冲突
"""

import threading
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, Any
from flask import current_app
from app import db
from app.models.Task import Task
from app.models.TaskLog import TaskLog
from app.services.runninghub import RunningHubService
import logging

logger = logging.getLogger(__name__)

class TriggerSource(Enum):
    """触发源枚举"""
    USER_START = "user_start"
    TASK_COMPLETE = "task_complete"
    TASK_STOP = "task_stop"
    TIMEOUT_CHECK = "timeout_check"
    STATUS_MONITOR = "status_monitor"
    PENDING_CHECK = "pending_check"
    BACKGROUND = "background"

class CentralQueueManager:
    """集中式队列管理器
    
    统一管理所有任务队列处理请求，确保同时只有一个队列处理操作在执行
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """单例模式"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        """初始化管理器"""
        if self._initialized:
            return
            
        self._processing_lock = threading.RLock()  # 可重入锁
        self._processing = False
        self._last_process_time = 0
        self._min_interval = 1  # 最小处理间隔（秒）
        self._request_count = 0
        self._success_count = 0
        self._skip_count = 0
        
        # 远程状态缓存（简单TTL，无指数退避）
        self._status_cache_value = None
        self._status_cache_time = 0
        
        self.runninghub_service = RunningHubService()
        self._initialized = True
        
        logger.info("Central Queue Manager initialized")
    
    def request_queue_processing(self, trigger_source: TriggerSource, reason: str, 
                               task_id: Optional[str] = None, force: bool = False) -> bool:
        """统一的队列处理请求入口
        
        Args:
            trigger_source: 触发源
            reason: 触发原因
            task_id: 相关任务ID（可选）
            force: 是否强制处理，忽略间隔限制
            
        Returns:
            bool: 是否成功处理了队列
        """
        self._request_count += 1
        
        with self._processing_lock:
            # 检查是否正在处理
            if self._processing:
                logger.debug(f"Queue already processing, ignoring request from {trigger_source.value}: {reason}")
                self._skip_count += 1
                return False
            
            # 检查处理间隔（除非强制处理）
            if not force:
                current_time = time.time()
                if current_time - self._last_process_time < self._min_interval:
                    logger.debug(f"Too frequent request from {trigger_source.value}, skipping: {reason}")
                    self._skip_count += 1
                    return False
            
            # 开始处理
            self._processing = True
            self._last_process_time = time.time()
            
            try:
                logger.info(f"Processing queue request from {trigger_source.value}: {reason}" + 
                          (f" (task: {task_id})" if task_id else ""))
                
                success = self._process_queue_internal(trigger_source, reason, task_id)
                
                if success:
                    self._success_count += 1
                    logger.info(f"Queue processing completed successfully from {trigger_source.value}")
                else:
                    logger.debug(f"Queue processing completed with no action from {trigger_source.value}")
                
                return success
                
            except Exception as e:
                logger.error(f"Error in queue processing from {trigger_source.value}: {e}", exc_info=True)
                return False
            finally:
                self._processing = False
    
    def _process_queue_internal(self, trigger_source: TriggerSource, reason: str, 
                              task_id: Optional[str] = None) -> bool:
        """内部队列处理逻辑
        
        Returns:
            bool: 是否成功启动了新任务
        """
        try:
            # 在任何远程状态查询前，先确认是否存在待启动任务
            if not self._has_pending_tasks():
                logger.debug("No pending tasks in queue, skipping remote status check")
                return False
            
            # 1. 检查是否有可用的执行槽位
            if not self._can_start_task():
                # 使用缓存的远程状态进行日志输出，避免不必要的远程调用
                current_tasks = self._get_current_tasks_cached()
                if current_tasks is not None:
                    max_concurrent = current_app.config.get('MAX_CONCURRENT_TASKS', 1)
                    logger.debug(f"RunningHub status: {current_tasks}/{max_concurrent} tasks, waiting for completion")
                else:
                    logger.debug("No available slots for new tasks (using local fallback or unknown remote status)")
                return False
            
            # 2. 获取下一个待执行的任务
            next_task = self._get_next_pending_task()
            if not next_task:
                logger.debug("No pending tasks in queue")
                return False
            
            logger.info(f"Processing task {next_task.task_id} from queue (triggered by {trigger_source.value})")
            
            # 3. 在提交前再次检查RunningHub状态，避免并发问题
            if not self._can_start_task():
                logger.debug(f"RunningHub status changed, cannot start task {next_task.task_id}")
                return False
            
            # 4. 提交任务到RunningHub
            return self._submit_task_to_runninghub(next_task, trigger_source)
            
        except Exception as e:
            logger.error(f"Error in internal queue processing: {e}", exc_info=True)
            return False
    
    def _has_pending_tasks(self) -> bool:
        """是否存在待启动任务（本地短路）"""
        try:
            return Task.query.filter_by(status='PENDING').count() > 0
        except Exception as e:
            logger.error(f"Error checking pending tasks: {e}")
            # 出错时不阻塞调度，返回True以继续后续逻辑
            return True
    
    def _get_current_tasks_cached(self, force_refresh: bool = False) -> Optional[int]:
        """带TTL的远程任务数获取（简单缓存）"""
        try:
            ttl = 30
            try:
                ttl = current_app.config.get('RUNNINGHUB_STATUS_TTL', 30)
            except Exception:
                pass
            now = time.time()
            if (not force_refresh) and self._status_cache_value is not None and (now - self._status_cache_time) < ttl:
                return self._status_cache_value
            
            current_tasks = self.runninghub_service.check_account_status()
            if current_tasks is not None:
                self._status_cache_value = current_tasks
                self._status_cache_time = now
                return current_tasks
            # 不缓存None，以便下次有机会重新请求
            return None
        except Exception as e:
            logger.error(f"Error getting cached RunningHub status: {e}")
            return None
    
    def _can_start_task(self) -> bool:
        """检查是否可以启动新任务"""
        try:
            # 本地待启动任务短路：无待启动任务则不需查询远程状态
            if not self._has_pending_tasks():
                logger.debug("No pending tasks, skip remote status check")
                return False
            
            # 先尝试使用缓存的远程状态
            current_tasks = self._get_current_tasks_cached()
            
            if current_tasks is not None:
                # 成功获取RunningHub状态
                max_concurrent = current_app.config.get('MAX_CONCURRENT_TASKS', 1)
                can_start = current_tasks < max_concurrent
                logger.debug(f"RunningHub status: {current_tasks}/{max_concurrent} tasks, can_start: {can_start}")
                # 重置连接失败计数器
                if not hasattr(self, '_runninghub_fail_count'):
                    self._runninghub_fail_count = 0
                self._runninghub_fail_count = 0
                return can_start
            else:
                # 无法获取RunningHub状态，使用本地数据库作为备选
                if not hasattr(self, '_runninghub_fail_count'):
                    self._runninghub_fail_count = 0
                self._runninghub_fail_count += 1
                
                if self._runninghub_fail_count == 1 or self._runninghub_fail_count % 10 == 0:
                    logger.warning(f"Cannot get RunningHub status (attempt {self._runninghub_fail_count}), using local database as fallback")
                
                running_count = Task.query.filter(Task.status.in_(['QUEUED', 'RUNNING'])).count()
                max_concurrent = current_app.config.get('MAX_CONCURRENT_TASKS', 1)
                can_start = running_count < max_concurrent
                logger.debug(f"Local database status: {running_count}/{max_concurrent} tasks, can_start: {can_start}")
                return can_start
                
        except Exception as e:
            logger.error(f"Error checking if can start task: {e}")
            # 出错时允许启动，避免系统卡死
            return True
    
    def _get_next_pending_task(self) -> Optional[Task]:
        """获取下一个待处理的任务"""
        try:
            return Task.query.filter_by(status='PENDING').order_by(Task.created_at.asc()).first()
        except Exception as e:
            logger.error(f"Error getting next pending task: {e}")
            return None
    
    def _submit_task_to_runninghub(self, task: Task, trigger_source: TriggerSource) -> bool:
        """提交任务到RunningHub
        
        Args:
            task: 要提交的任务
            trigger_source: 触发源
            
        Returns:
            bool: 是否成功提交
        """
        try:
            # 记录开始提交任务的日志
            start_log = TaskLog(
                task_id=task.task_id,
                message=f"🚀 开始提交任务到RunningHub (触发源: {trigger_source.value})..."
            )
            db.session.add(start_log)
            db.session.commit()
            
            # 调用原有的提交逻辑
            from app.services.task_queue_service import TaskQueueService
            queue_service = TaskQueueService()
            success, runninghub_task_id, error_msg = queue_service.submit_task_to_runninghub(task)
            
            if success:
                # 更新任务状态
                task.status = 'QUEUED'
                task.runninghub_task_id = runninghub_task_id
                task.started_at = datetime.utcnow()
                db.session.commit()
                
                logger.info(f"Task {task.task_id} submitted to RunningHub with ID: {runninghub_task_id}")
                
                # 记录成功提交的日志
                success_log = TaskLog(
                    task_id=task.task_id,
                    message=f"✅ 任务已成功提交到RunningHub (ID: {runninghub_task_id}, 触发源: {trigger_source.value})"
                )
                db.session.add(success_log)
                db.session.commit()
                
                return True
            else:
                # 处理提交失败的情况
                if error_msg and 'TASK_QUEUE_MAXED' in error_msg:
                    # 队列满时，任务保持PENDING状态
                    logger.info(f"RunningHub queue is full, task {task.task_id} remains in PENDING status")
                    
                    # 记录队列满的日志（避免重复记录）
                    existing_queue_log = TaskLog.query.filter_by(
                        task_id=task.task_id
                    ).filter(
                        TaskLog.message.like('%队列已满%')
                    ).first()
                    
                    if not existing_queue_log:
                        queue_log = TaskLog(
                            task_id=task.task_id,
                            message=f"⏳ RunningHub队列已满，等待空闲槽位... (触发源: {trigger_source.value})"
                        )
                        db.session.add(queue_log)
                        db.session.commit()
                else:
                    # 其他错误，标记任务失败
                    task.status = 'FAILED'
                    if hasattr(task, 'completed_at'):
                        task.completed_at = datetime.utcnow()
                    db.session.commit()
                    
                    error_log = TaskLog(
                        task_id=task.task_id,
                        message=f"❌ 任务提交失败: {error_msg or '未知错误'} (触发源: {trigger_source.value})"
                    )
                    db.session.add(error_log)
                    db.session.commit()
                    
                    logger.error(f"Failed to submit task {task.task_id}: {error_msg}")
                
                return False
                
        except Exception as e:
            logger.error(f"Error submitting task {task.task_id} to RunningHub: {e}", exc_info=True)
            
            # 记录异常日志
            try:
                error_log = TaskLog(
                    task_id=task.task_id,
                    message=f"❌ 任务提交异常: {str(e)} (触发源: {trigger_source.value})"
                )
                db.session.add(error_log)
                db.session.commit()
            except:
                pass  # 避免日志记录失败影响主流程
            
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取管理器统计信息"""
        with self._processing_lock:
            return {
                'request_count': self._request_count,
                'success_count': self._success_count,
                'skip_count': self._skip_count,
                'is_processing': self._processing,
                'last_process_time': self._last_process_time,
                'success_rate': self._success_count / max(self._request_count, 1) * 100
            }
    
    def reset_statistics(self):
        """重置统计信息"""
        with self._processing_lock:
            self._request_count = 0
            self._success_count = 0
            self._skip_count = 0
            logger.info("Central Queue Manager statistics reset")

# 全局中央队列管理器实例
central_queue_manager = CentralQueueManager()