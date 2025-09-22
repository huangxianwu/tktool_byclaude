import threading
import time
import json
from datetime import datetime
from app import db, create_app
from app.models import Task, TaskData
from app.services.runninghub import RunningHubService

class TaskQueueManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_manager()
            return cls._instance
    
    def _init_manager(self):
        self.runninghub_service = RunningHubService()
        self.running_tasks = {}
        self.stop_event = threading.Event()
        
        # 启动任务监控线程
        self.monitor_thread = threading.Thread(target=self._monitor_tasks, daemon=True)
        self.monitor_thread.start()
    
    def start_task(self, task_id):
        """开始执行任务"""
        with self._lock:
            if task_id in self.running_tasks:
                return False
            
            # 启动任务执行线程
            thread = threading.Thread(target=self._execute_task, args=(task_id,), daemon=True)
            self.running_tasks[task_id] = thread
            thread.start()
            return True
    
    def _execute_task(self, task_id):
        """执行任务的主要逻辑"""
        # 创建应用实例用于数据库操作
        app = create_app()
        
        with app.app_context():
            try:
                # 获取任务数据
                task = Task.query.get(task_id)
                if not task:
                    return
                
                # 更新任务状态为运行中
                task.status = 'RUNNING'
                db.session.commit()
                
                # 获取任务输入数据
                task_data = TaskData.query.filter_by(task_id=task_id).all()
                
                # 构建nodeInfoList
                node_info_list = []
                for data in task_data:
                    node_info = {
                        "nodeId": data.node_id,
                        "fieldName": data.field_name,
                        "fieldValue": data.field_value
                    }
                    node_info_list.append(node_info)
                
                # 调用RunningHub执行任务
                runninghub_task_id = self.runninghub_service.run_task(node_info_list, task_id, task.workflow_id)
                
                # 保存RunningHub任务ID
                task.runninghub_task_id = runninghub_task_id
                db.session.commit()
                
                # 轮询任务状态
                self._poll_task_status(task_id, runninghub_task_id)
                
                # 获取任务结果
                outputs = self.runninghub_service.get_outputs(runninghub_task_id, task_id)
                
                if outputs:
                    # 保存结果文件URL到TaskData
                    for output in outputs:
                        # 根据nodeId找到对应的TaskData记录
                        task_data = TaskData.query.filter_by(
                            task_id=task_id, 
                            node_id=output['nodeId']
                        ).first()
                        
                        if task_data:
                            task_data.file_url = output['fileUrl']
                    
                    # 创建TaskOutput记录（远程模式下也需要创建记录用于前端显示）
                    task_output_success = False
                    created_outputs_count = 0
                    
                    try:
                        from app.models.TaskOutput import TaskOutput
                        from datetime import datetime
                        
                        # 验证outputs数据完整性
                        if not outputs or not isinstance(outputs, list):
                            raise ValueError(f"Invalid outputs data: {outputs}")
                        
                        # 记录开始创建TaskOutput的时间
                        from app.utils.timezone_helper import now_utc
                        creation_start_time = now_utc()
                        self.runninghub_service._log(task_id, f"🔄 开始创建TaskOutput记录，共{len(outputs)}个输出文件")
                        
                        for i, output in enumerate(outputs):
                            try:
                                # 验证单个output数据
                                if not isinstance(output, dict):
                                    self.runninghub_service._log(task_id, f"⚠️ 跳过无效的output[{i}]: {output}")
                                    continue
                                
                                file_url = output.get('fileUrl', '').strip()
                                node_id = output.get('nodeId', f'node_{i}').strip()
                                file_type = output.get('fileType', 'png').strip()
                                
                                # 验证必要字段
                                if not file_url:
                                    self.runninghub_service._log(task_id, f"⚠️ 跳过空fileUrl的output[{i}]")
                                    continue
                                
                                if not node_id:
                                    node_id = f'node_{i}'
                                
                                # 从URL中提取文件名，增强文件名处理逻辑
                                if '/' in file_url:
                                    file_name = file_url.split('/')[-1]
                                    # 如果文件名为空或只有扩展名，生成默认名称
                                    if not file_name or file_name.startswith('.'):
                                        file_name = f'output_{i}_{creation_start_time.strftime("%Y%m%d_%H%M%S")}.{file_type}'
                                else:
                                    file_name = f'output_{i}_{creation_start_time.strftime("%Y%m%d_%H%M%S")}.{file_type}'
                                
                                # 检查是否已存在相同的TaskOutput记录（增强去重逻辑）
                                existing_output = TaskOutput.query.filter_by(
                                    task_id=task_id,
                                    node_id=node_id,
                                    file_url=file_url
                                ).first()
                                
                                if existing_output:
                                    self.runninghub_service._log(task_id, f"ℹ️ TaskOutput记录已存在: {node_id} - {file_name}")
                                    created_outputs_count += 1  # 已存在的也算作成功
                                    continue
                                
                                # 创建新的TaskOutput记录
                                task_output = TaskOutput(
                                    task_id=task_id,
                                    node_id=node_id,
                                    name=file_name,
                                    file_url=file_url,
                                    local_path='',  # 远程模式下本地路径为空
                                    thumbnail_path='',  # 远程模式下缩略图路径为空
                                    file_type=file_type,
                                    file_size=0,  # 远程模式下文件大小暂时为0
                                    created_at=creation_start_time  # 使用统一的创建时间
                                )
                                db.session.add(task_output)
                                created_outputs_count += 1
                                
                                self.runninghub_service._log(task_id, f"✅ 创建TaskOutput记录: {node_id} - {file_name}")
                                
                            except Exception as output_error:
                                self.runninghub_service._log(task_id, f"⚠️ 创建单个TaskOutput记录失败[{i}]: {str(output_error)}")
                                # 继续处理下一个output，不中断整个流程
                                continue
                        
                        # 提交数据库事务
                        if created_outputs_count > 0:
                            db.session.commit()
                            task_output_success = True
                            creation_end_time = now_utc()
                            duration = (creation_end_time - creation_start_time).total_seconds()
                            self.runninghub_service._log(task_id, f"✅ 成功创建{created_outputs_count}个TaskOutput记录，耗时{duration:.2f}秒")
                        else:
                            db.session.rollback()
                            self.runninghub_service._log(task_id, f"⚠️ 没有创建任何TaskOutput记录")
                            
                    except Exception as e:
                        # 回滚数据库事务
                        try:
                            db.session.rollback()
                        except:
                            pass
                        
                        error_msg = f"创建TaskOutput记录失败: {str(e)}"
                        self.runninghub_service._log(task_id, f"❌ {error_msg}")
                        
                        # 记录详细的错误信息用于调试
                        import traceback
                        self.runninghub_service._log(task_id, f"🔍 错误详情: {traceback.format_exc()}")
                        
                        # 即使TaskOutput创建失败，也不应该影响任务状态更新
                        # 但需要记录这个问题以便后续修复
                        task_output_success = False
                    
                    # 禁用自动下载文件到本地的逻辑（远程模式下不需要）
                    # try:
                    #     from app.services.file_manager import FileManager
                    #     file_manager = FileManager()
                    #     saved_files = file_manager.download_and_save_outputs(task_id, outputs)
                    #     self.runninghub_service._log(task_id, f"✅ 已下载并保存{len(saved_files)}个输出文件到本地")
                    # except Exception as e:
                    #     self.runninghub_service._log(task_id, f"⚠️ 文件下载失败: {str(e)}")
                    
                    self.runninghub_service._log(task_id, f"✅ 任务完成，输出文件已保存到远程服务器")
                    
                    # 更新任务状态为成功
                    task.status = 'SUCCESS'
                    db.session.commit()
                else:
                    # 任务失败
                    task.status = 'FAILED'
                    db.session.commit()
                    
            except Exception as e:
                # 记录异常并更新任务状态
                task = Task.query.get(task_id)
                if task:
                    task.status = 'FAILED'
                    db.session.commit()
                
                # 记录异常日志
                self.runninghub_service._log(task_id, f"❌ 任务执行异常: {str(e)}")
            finally:
                # 清理运行中的任务
                with self._lock:
                    if task_id in self.running_tasks:
                        del self.running_tasks[task_id]
    
    def _poll_task_status(self, task_id, runninghub_task_id):
        """轮询任务状态"""
        max_attempts = 300  # 最多轮询300次（50分钟）
        attempt = 0
        
        while attempt < max_attempts and not self.stop_event.is_set():
            status = self.runninghub_service.get_status(runninghub_task_id, task_id)
            
            if status in ['SUCCESS', 'FAILED']:
                break
            
            # 每10秒轮询一次
            time.sleep(10)
            attempt += 1
    
    def _monitor_tasks(self):
        """监控待处理任务"""
        # 创建应用实例用于数据库操作
        app = create_app()
        
        while not self.stop_event.is_set():
            with app.app_context():
                try:
                    # 注释掉自动执行逻辑，任务应该手动触发执行
                    # 查找待处理的PENDING状态任务
                    # pending_tasks = Task.query.filter_by(status='PENDING').all()
                    # 
                    # for task in pending_tasks:
                    #     self.start_task(task.task_id)
                    
                    # 每5秒检查一次
                    time.sleep(5)
                    
                except Exception as e:
                    current_app.logger.error(f"Task monitor error: {e}")
                    time.sleep(10)
    
    def stop_all_tasks(self):
        """停止所有任务"""
        self.stop_event.set()
        
        # 等待所有线程结束
        for thread in self.running_tasks.values():
            thread.join(timeout=5)
        
        self.running_tasks.clear()
        self.stop_event.clear()
    
    def get_running_tasks(self):
        """获取当前运行中的任务"""
        with self._lock:
            return list(self.running_tasks.keys())