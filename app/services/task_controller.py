"""
任务控制器
统一管理任务的生命周期和操作
"""
from flask import current_app
from app import db
from app.models.Task import Task
from app.services.task_queue_service import TaskQueueService
from app.services.task_status_service import TaskStatusService
import logging

logger = logging.getLogger(__name__)

class TaskController:
    def __init__(self):
        self.queue_service = TaskQueueService()
        self.status_service = TaskStatusService()
    
    def get_tasks_with_workflow_info(self):
        """获取任务列表及工作流信息"""
        try:
            # 先查询所有任务
            tasks = Task.query.all()
            result = []
            
            for task in tasks:
                task_dict = task.to_dict()
                # 处理is_plus字段兼容性
                if not hasattr(task, 'is_plus'):
                    task_dict['is_plus'] = False
                # 尝试添加工作流信息
                try:
                    if hasattr(task, 'workflow') and task.workflow:
                        task_dict['workflow_name'] = task.workflow.name
                        task_dict['node_count'] = len(task.workflow.nodes)
                    else:
                        # 手动查询工作流信息
                        from app.models.Workflow import Workflow
                        workflow = Workflow.query.get(task.workflow_id)
                        if workflow:
                            task_dict['workflow_name'] = workflow.name
                            task_dict['node_count'] = len(workflow.nodes)
                        else:
                            task_dict['workflow_name'] = 'Unknown'
                            task_dict['node_count'] = 0
                except Exception as e:
                    # 如果工作流信息获取失败，使用默认值
                    task_dict['workflow_name'] = 'Unknown'
                    task_dict['node_count'] = 0
                
                result.append(task_dict)
            
            return result
        except Exception as e:
            # 如果查询失败，返回空列表
            logger.error(f"Error fetching tasks: {e}")
            return []
    
    def start_single_task(self, task_id):
        """启动单个任务"""
        logger.info(f"Starting task: {task_id}")
        return self.queue_service.start_task(task_id)
    
    def stop_single_task(self, task_id):
        """停止单个任务"""
        logger.info(f"Stopping task: {task_id}")
        return self.queue_service.stop_task(task_id)
    
    def delete_single_task(self, task_id):
        """删除单个任务"""
        logger.info(f"Deleting task: {task_id}")
        
        task = Task.query.get(task_id)
        if not task:
            return False, "任务不存在"
        
        try:
            # 如果任务正在运行，先停止它
            if task.status in ['PENDING', 'QUEUED', 'RUNNING']:
                self.queue_service.stop_task(task_id)
            
            # 删除任务
            db.session.delete(task)
            db.session.commit()
            
            logger.info(f"Task {task_id} deleted successfully")
            return True, "任务删除成功"
            
        except Exception as e:
            logger.error(f"Error deleting task {task_id}: {e}")
            db.session.rollback()
            return False, f"删除任务失败: {str(e)}"
    
    def batch_start_tasks(self, task_ids):
        """批量启动任务"""
        logger.info(f"Batch starting tasks: {task_ids}")
        
        # 验证所有任务都可以启动
        invalid_tasks = []
        for task_id in task_ids:
            task = Task.query.get(task_id)
            if not task:
                invalid_tasks.append(f"{task_id}: 任务不存在")
            elif task.status not in ['READY', 'FAILED', 'STOPPED']:
                invalid_tasks.append(f"{task_id}: 状态 {task.status} 不允许启动")
        
        if invalid_tasks:
            return False, f"以下任务无法启动: {'; '.join(invalid_tasks)}"
        
        # 执行批量启动
        results = self.queue_service.batch_start_tasks(task_ids)
        
        # 统计结果
        success_count = sum(1 for r in results if r['success'])
        total_count = len(results)
        
        if success_count == total_count:
            return True, f"成功启动 {success_count} 个任务"
        else:
            failed_tasks = [r['task_id'] for r in results if not r['success']]
            return False, f"启动了 {success_count}/{total_count} 个任务，失败的任务: {', '.join(failed_tasks)}"
    
    def batch_stop_tasks(self, task_ids):
        """批量停止任务"""
        logger.info(f"Batch stopping tasks: {task_ids}")
        
        # 验证所有任务都可以停止
        invalid_tasks = []
        for task_id in task_ids:
            task = Task.query.get(task_id)
            if not task:
                invalid_tasks.append(f"{task_id}: 任务不存在")
            elif task.status not in ['PENDING', 'QUEUED', 'RUNNING']:
                invalid_tasks.append(f"{task_id}: 状态 {task.status} 不允许停止")
        
        if invalid_tasks:
            return False, f"以下任务无法停止: {'; '.join(invalid_tasks)}"
        
        # 执行批量停止
        results = self.queue_service.batch_stop_tasks(task_ids)
        
        # 统计结果
        success_count = sum(1 for r in results if r['success'])
        total_count = len(results)
        
        if success_count == total_count:
            return True, f"成功停止 {success_count} 个任务"
        else:
            failed_tasks = [r['task_id'] for r in results if not r['success']]
            return False, f"停止了 {success_count}/{total_count} 个任务，失败的任务: {', '.join(failed_tasks)}"
    
    def batch_delete_tasks(self, task_ids):
        """批量删除任务"""
        logger.info(f"Batch deleting tasks: {task_ids}")
        
        success_count = 0
        failed_tasks = []
        
        for task_id in task_ids:
            success, message = self.delete_single_task(task_id)
            if success:
                success_count += 1
            else:
                failed_tasks.append(f"{task_id}: {message}")
        
        total_count = len(task_ids)
        
        if success_count == total_count:
            return True, f"成功删除 {success_count} 个任务"
        else:
            return False, f"删除了 {success_count}/{total_count} 个任务，失败的任务: {'; '.join(failed_tasks)}"
    
    def get_task_details(self, task_id):
        """获取任务详细信息"""
        return self.status_service.get_task_details(task_id)
    
    def get_queue_status(self):
        """获取队列状态"""
        return self.queue_service.get_queue_status()
    
    def update_task_status(self, task_id):
        """手动更新任务状态"""
        return self.status_service.update_task_status(task_id)
    
    def get_task_progress(self, task_id):
        """获取任务进度"""
        return self.status_service.get_task_progress(task_id)
    
    def get_task_outputs(self, task_id):
        """获取任务输出"""
        return self.status_service.get_task_outputs(task_id)
    
    def download_task_output(self, task_id, output_name):
        """下载任务输出文件"""
        return self.status_service.download_task_output(task_id, output_name)
    
    def validate_batch_operation(self, task_ids, operation):
        """验证批量操作的有效性"""
        if not task_ids:
            return False, "未选择任务"
        
        tasks = Task.query.filter(Task.task_id.in_(task_ids)).all()
        
        if len(tasks) != len(task_ids):
            found_ids = [t.task_id for t in tasks]
            missing_ids = [tid for tid in task_ids if tid not in found_ids]
            return False, f"以下任务不存在: {', '.join(missing_ids)}"
        
        # 根据操作类型验证任务状态
        if operation == 'start':
            invalid_tasks = [t.task_id for t in tasks if t.status not in ['READY', 'FAILED', 'STOPPED']]
            if invalid_tasks:
                return False, f"以下任务状态不允许启动: {', '.join(invalid_tasks)}"
        
        elif operation == 'stop':
            invalid_tasks = [t.task_id for t in tasks if t.status not in ['PENDING', 'QUEUED', 'RUNNING']]
            if invalid_tasks:
                return False, f"以下任务状态不允许停止: {', '.join(invalid_tasks)}"
        
        # delete操作允许任何状态
        
        return True, "验证通过"
    
    def get_task_statistics(self):
        """获取任务统计信息"""
        stats = {}
        
        # 按状态统计任务数量
        for status in ['READY', 'PENDING', 'QUEUED', 'RUNNING', 'SUCCESS', 'FAILED', 'STOPPED']:
            count = Task.query.filter_by(status=status).count()
            stats[status.lower()] = count
        
        # 总任务数
        stats['total'] = Task.query.count()
        
        # 队列状态
        queue_status = self.get_queue_status()
        stats.update(queue_status)
        
        return stats
    
    def get_task_logs(self, task_id):
        """获取任务执行日志"""
        try:
            from app.models.TaskLog import TaskLog
            logs = TaskLog.query.filter_by(task_id=task_id).order_by(TaskLog.timestamp.desc()).all()
            return [
                {
                    'id': log.id,
                    'message': log.message,
                    'created_at': log.timestamp.isoformat() if log.timestamp else None
                } for log in logs
            ]
        except Exception as e:
            logger.error(f"Error fetching task logs for {task_id}: {e}")
            return []