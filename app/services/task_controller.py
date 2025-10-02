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
import json

logger = logging.getLogger(__name__)

class TaskController:
    def __init__(self):
        self.queue_service = TaskQueueService()
        self.status_service = TaskStatusService()
    
    def get_tasks_with_workflow_info(self, status=None, workflow_id=None, start_date=None, end_date=None, search=None, sort_by='created_at', sort_order='desc'):
        """获取任务列表及工作流信息（支持筛选）"""
        try:
            from datetime import datetime
            from sqlalchemy import or_, and_
            
            # 构建查询条件
            query = Task.query
            
            # 状态筛选
            if status:
                query = query.filter(Task.status == status.upper())
            
            # 工作流筛选
            if workflow_id:
                query = query.filter(Task.workflow_id == workflow_id)
            
            # 时间范围筛选
            if start_date:
                try:
                    # 支持日期格式 YYYY-MM-DD
                    if len(start_date) == 10:  # YYYY-MM-DD format
                        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                    else:
                        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                    query = query.filter(Task.created_at >= start_dt)
                except (ValueError, TypeError):
                    pass
            
            if end_date:
                try:
                    # 支持日期格式 YYYY-MM-DD，设置为当天结束时间
                    if len(end_date) == 10:  # YYYY-MM-DD format
                        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                        # 设置为当天的23:59:59
                        end_dt = end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
                    else:
                        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    query = query.filter(Task.created_at <= end_dt)
                except (ValueError, TypeError):
                    pass
            
            # 任务描述搜索
            if search:
                query = query.filter(or_(
                    Task.task_description.ilike(f'%{search}%'),
                    Task.task_id.ilike(f'%{search}%')
                ))
            
            # 排序
            if sort_by == 'created_at':
                if sort_order == 'desc':
                    query = query.order_by(Task.created_at.desc())
                else:
                    query = query.order_by(Task.created_at.asc())
            elif sort_by == 'status':
                if sort_order == 'desc':
                    query = query.order_by(Task.status.desc())
                else:
                    query = query.order_by(Task.status.asc())
            elif sort_by == 'task_id':
                if sort_order == 'desc':
                    query = query.order_by(Task.task_id.desc())
                else:
                    query = query.order_by(Task.task_id.asc())
            elif sort_by == 'workflow_id':
                if sort_order == 'desc':
                    query = query.order_by(Task.workflow_id.desc())
                else:
                    query = query.order_by(Task.workflow_id.asc())
            else:
                # 默认按创建时间降序排序
                query = query.order_by(Task.created_at.desc())
            
            tasks = query.all()
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
    
    def download_task_files(self, task_id):
        """下载任务的所有输出文件到本地"""
        # 检查是否为远程模式
        remote_only_mode = current_app.config.get('REMOTE_ONLY_MODE', False)
        if remote_only_mode:
            return {'success': False, 'error': 'File download is disabled in remote-only mode'}
        
        from app.services.file_manager import FileManager
        from app.services.runninghub import RunningHubService
        from app.models.Task import Task
        
        # 检查任务是否存在
        task = Task.query.get(task_id)
        if not task:
            return {'success': False, 'error': '任务不存在'}
        
        if not task.runninghub_task_id:
            return {'success': False, 'error': '任务没有远程ID，无法下载文件'}
        
        try:
            # 从RunningHub获取输出文件
            runninghub_service = RunningHubService()
            outputs = runninghub_service.get_outputs(task.runninghub_task_id, task_id)
            
            if not outputs:
                return {'success': False, 'error': '未找到输出文件'}
            
            # 下载并保存文件
            file_manager = FileManager()
            saved_files = file_manager.download_and_save_outputs(task_id, outputs)
            
            return {
                'success': True,
                'message': f'成功下载 {len(saved_files)} 个文件',
                'files': saved_files,
                'total_count': len(saved_files)
            }
            
        except Exception as e:
            logger.error(f"下载任务文件失败 {task_id}: {e}")
            return {'success': False, 'error': f'下载失败: {str(e)}'}
    
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
            logs = TaskLog.query.filter_by(task_id=task_id).order_by(TaskLog.timestamp.asc()).all()
            return [
                {
                    'id': log.id,
                    'message': log.message,
                    'timestamp': log.timestamp.isoformat() if log.timestamp else None
                } for log in logs
            ]
        except Exception as e:
            logger.error(f"Error fetching task logs for {task_id}: {e}")
            return []
    
    def get_task_logs_history(self, task_id):
        """获取任务历史日志"""
        return self.get_task_logs(task_id)
    
    def diagnose_and_retry(self, task_id: str):
        """
        诊断任务失败原因（包括APIKEY_INVALID_NODE_INFO等），必要时自动修复字段并重试提交到RunningHub。
        返回字典，包括诊断结论、是否修复、重试结果等。
        """
        from app import db
        from app.models.Task import Task
        from app.models.TaskLog import TaskLog
        from app.models.TaskData import TaskData
        from app.models.Node import Node
        from app.services.error_handler import ErrorHandler, RetryHandler, ErrorCode

        task = Task.query.get(task_id)
        if not task:
            return {'success': False, 'error': '任务不存在'}

        # 记录诊断开始
        start_log = TaskLog(task_id=task_id, message="🩺 开始诊断任务失败原因并尝试修复")
        db.session.add(start_log)
        db.session.commit()

        # 提取最近的错误日志
        logs = TaskLog.query.filter_by(task_id=task_id).order_by(TaskLog.timestamp.desc()).limit(50).all()
        last_error_msg = None
        for log in logs:
            msg_upper = (log.message or '').upper()
            if '❌' in log.message or 'ERROR' in msg_upper or 'FAILED' in msg_upper:
                last_error_msg = log.message
                break

        diagnose = {}
        error_code = None
        if last_error_msg:
            error_code, _ = ErrorHandler.parse_error_from_message(last_error_msg)
            diagnose['last_error'] = last_error_msg
            diagnose['error_code'] = error_code.value if error_code else None
        else:
            diagnose['last_error'] = None

        # 当检测到节点信息错误时，尝试修复字段名
        fixed_summary = None
        if error_code == ErrorCode.RUNNINGHUB_INVALID_NODE_INFO or (last_error_msg and 'APIKEY_INVALID_NODE_INFO' in last_error_msg.upper()):
            fixed_summary = self._fix_task_data_field_names(task)
            fix_log = TaskLog(task_id=task_id, message=f"🛠️ 自动修复字段名: {json.dumps(fixed_summary, ensure_ascii=False)}")
            db.session.add(fix_log)
            db.session.commit()

        # 决定是否进行重试
        should_retry = True
        if error_code and not RetryHandler.is_retryable(error_code):
            # 节点信息错误在修复后仍允许重试
            if error_code != ErrorCode.RUNNINGHUB_INVALID_NODE_INFO and not fixed_summary:
                should_retry = False

        retry_result = None
        if should_retry:
            queue_service = TaskQueueService()
            try:
                success, runninghub_task_id, error_msg = queue_service.submit_task_to_runninghub(task)
                retry_result = {
                    'success': success,
                    'runninghub_task_id': runninghub_task_id,
                    'error_msg': error_msg
                }
                # 写入日志
                if success:
                    db.session.add(TaskLog(task_id=task_id, message=f"🔁 重试提交成功 → 远程ID: {runninghub_task_id}"))
                    # 更新任务状态由queue_service处理，这里补充一次保障
                    task.status = 'QUEUED'
                    task.runninghub_task_id = runninghub_task_id
                    db.session.commit()
                else:
                    db.session.add(TaskLog(task_id=task_id, message=f"🔁 重试提交失败: {error_msg}"))
                    db.session.commit()
            except Exception as e:
                retry_result = {'success': False, 'error': str(e)}
                db.session.add(TaskLog(task_id=task_id, message=f"🔁 重试提交异常: {str(e)}"))
                db.session.commit()
        else:
            db.session.add(TaskLog(task_id=task_id, message="⛔ 当前错误类型不可重试，已结束诊断"))
            db.session.commit()

        return {
            'success': True,
            'diagnose': diagnose,
            'fixed': fixed_summary is not None,
            'fixed_summary': fixed_summary,
            'retry_result': retry_result
        }

    def _fix_task_data_field_names(self, task):
        """
        根据工作流中的节点类型，修正TaskData的field_name，使其符合RunningHub标准：
        - image → field_name: 'image'
        - video → field_name: 'file'，并确保存在 'video-preview'（为空）
        - text  → field_name: 'text'
        - number→ field_name: 'number'
        - audio → field_name: 'audio'
        返回修改摘要。
        """
        from app import db
        from app.models.TaskData import TaskData
        from app.models.Node import Node

        # 构建节点类型映射
        nodes = Node.query.filter_by(workflow_id=task.workflow_id).all()
        node_type_map = {n.node_id: n.node_type for n in nodes}

        standard_fields = {
            'image': ['image'],
            'video': ['file', 'video-preview'],
            'text': ['text'],
            'number': ['number'],
            'audio': ['audio']
        }

        changes = []
        # 修正现有字段名
        for d in task.data:
            node_type = node_type_map.get(d.node_id)
            if not node_type:
                continue
            allowed = standard_fields.get(node_type, [])
            if allowed and d.field_name not in allowed:
                old = d.field_name
                d.field_name = allowed[0]
                changes.append({'node_id': d.node_id, 'from': old, 'to': d.field_name})
        db.session.commit()

        # 为video节点补充video-preview
        for node_id, node_type in node_type_map.items():
            if node_type == 'video':
                has_preview = any((d.node_id == node_id and d.field_name == 'video-preview') for d in task.data)
                if not has_preview:
                    db.session.add(TaskData(task_id=task.task_id, node_id=node_id, field_name='video-preview', field_value=''))
                    changes.append({'node_id': node_id, 'added': 'video-preview'})
        db.session.commit()

        return {'changes': changes, 'total_changes': len(changes)}

    def refresh_task_files(self, task_id):
        """刷新任务输出文件"""
        try:
            from app.services.runninghub import RunningHubService
            from app.services.file_manager import FileManager
            
            # 检查任务是否存在
            task = Task.query.get(task_id)
            if not task:
                raise Exception(f"任务 {task_id} 不存在")
            
            # 初始化服务
            runninghub_service = RunningHubService()
            file_manager = FileManager()
            
            # 从RunningHub获取最新的输出文件
            try:
                if not task.runninghub_task_id:
                    raise Exception(f"任务 {task_id} 没有关联的RunningHub任务ID")
                    
                outputs = runninghub_service.get_task_outputs(task.runninghub_task_id)
                if not outputs:
                    logger.info(f"任务 {task_id} 在RunningHub中没有输出文件")
                    return 0
                
                updated_count = 0
                
                # 处理每个输出文件
                for output in outputs:
                    try:
                        # 保存文件到本地
                        saved_output = file_manager.save_output_file(
                            task_id=task_id,
                            file_name=output.get('name', ''),
                            file_url=output.get('url', ''),
                            file_type=output.get('type', 'file')
                        )
                        
                        if saved_output:
                            updated_count += 1
                            logger.info(f"成功保存文件: {output.get('name')}")
                        
                    except Exception as file_error:
                        logger.error(f"保存文件失败 {output.get('name')}: {file_error}")
                        continue
                
                logger.info(f"任务 {task_id} 文件刷新完成，更新了 {updated_count} 个文件")
                return updated_count
                
            except Exception as hub_error:
                logger.error(f"从RunningHub获取输出文件失败: {hub_error}")
                raise Exception(f"无法从RunningHub获取输出文件: {str(hub_error)}")
                
        except Exception as e:
            logger.error(f"刷新任务文件失败 {task_id}: {e}")
            raise e