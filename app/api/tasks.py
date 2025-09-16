from flask import Blueprint, request, jsonify
from app import db
from app.models import Task, TaskData, Node
from app.services.runninghub import RunningHubService
from app.services.task_controller import TaskController
import uuid
import base64

bp = Blueprint('tasks', __name__, url_prefix='/api/tasks')
task_controller = TaskController()

@bp.route('', methods=['GET'])
def get_tasks():
    """获取所有任务（包含工作流信息）"""
    # 获取筛选参数
    status = request.args.get('status')
    workflow_id = request.args.get('workflow_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    search = request.args.get('search')
    sort_by = request.args.get('sort_by', 'created_at')
    sort_order = request.args.get('sort_order', 'desc')
    
    tasks = task_controller.get_tasks_with_workflow_info(
        status=status,
        workflow_id=workflow_id,
        start_date=start_date,
        end_date=end_date,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order
    )
    return jsonify(tasks)

@bp.route('', methods=['POST'])
def create_task():
    """创建新任务"""
    data = request.get_json()
    
    if not data or 'workflow_id' not in data:
        return jsonify({'error': 'Missing workflow_id'}), 400
    
    # 生成任务ID
    task_id = str(uuid.uuid4())
    
    # 创建任务（默认状态为READY）
    is_plus = data.get('is_plus', False)  # 获取是否Plus实例标志
    task_description = data.get('task_description', '')  # 获取任务描述
    task = Task(task_id=task_id, workflow_id=data['workflow_id'], status='READY', is_plus=is_plus, task_description=task_description)
    db.session.add(task)
    
    # 处理任务数据并集成文件上传
    if 'data' in data:
        runninghub_service = RunningHubService()
        
        for node_data in data['data']:
            field_value = node_data['field_value']
            
            # 获取节点类型信息
            node = Node.query.filter_by(
                workflow_id=data['workflow_id'], 
                node_id=node_data['node_id']
            ).first()
            
            # 如果是文件类型字段且包含文件数据，则预上传
            if node and node.node_type in ['image', 'video', 'audio'] and field_value:
                # 检查是否为base64编码的文件数据
                is_base64_data = isinstance(field_value, str) and (
                    field_value.startswith('data:') or 
                    len(field_value) > 1000  # 假设超过1000字符可能是文件数据
                )
                
                if is_base64_data:
                    try:
                        # 解析文件数据 
                        if field_value.startswith('data:'):
                            # base64 data URL格式: data:image/png;base64,iVBORw0KGgoAAAA...
                            header, encoded = field_value.split(',', 1)
                            file_data = base64.b64decode(encoded)
                            
                            # 从header中提取文件类型和生成合适的文件名
                            if 'image/' in header:
                                # 提取具体的图片格式
                                if 'image/jpeg' in header or 'image/jpg' in header:
                                    filename = f"upload_{task_id}.jpg"
                                elif 'image/png' in header:
                                    filename = f"upload_{task_id}.png"
                                elif 'image/gif' in header:
                                    filename = f"upload_{task_id}.gif"
                                elif 'image/webp' in header:
                                    filename = f"upload_{task_id}.webp"
                                else:
                                    filename = f"upload_{task_id}.png"  # 默认png
                            elif 'video/' in header:
                                # 提取具体的视频格式
                                if 'video/mp4' in header:
                                    filename = f"upload_{task_id}.mp4"
                                elif 'video/avi' in header:
                                    filename = f"upload_{task_id}.avi"
                                elif 'video/mov' in header:
                                    filename = f"upload_{task_id}.mov"
                                elif 'video/webm' in header:
                                    filename = f"upload_{task_id}.webm"
                                else:
                                    filename = f"upload_{task_id}.mp4"  # 默认mp4
                            elif 'audio/' in header:
                                # 提取具体的音频格式
                                if 'audio/mp3' in header or 'audio/mpeg' in header:
                                    filename = f"upload_{task_id}.mp3"
                                elif 'audio/wav' in header:
                                    filename = f"upload_{task_id}.wav"
                                elif 'audio/ogg' in header:
                                    filename = f"upload_{task_id}.ogg"
                                elif 'audio/aac' in header:
                                    filename = f"upload_{task_id}.aac"
                                elif 'audio/flac' in header:
                                    filename = f"upload_{task_id}.flac"
                                elif 'audio/m4a' in header:
                                    filename = f"upload_{task_id}.m4a"
                                else:
                                    filename = f"upload_{task_id}.mp3"  # 默认mp3
                            else:
                                filename = f"upload_{task_id}.bin"
                        else:
                            # 纯base64数据，根据节点类型生成文件名
                            file_data = base64.b64decode(field_value)
                            if node.node_type == 'image':
                                filename = f"upload_{task_id}_{node_data['node_id']}.png"
                            elif node.node_type == 'video':
                                filename = f"upload_{task_id}_{node_data['node_id']}.mp4"
                            elif node.node_type == 'audio':
                                filename = f"upload_{task_id}_{node_data['node_id']}.mp3"
                            else:
                                filename = f"upload_{task_id}_{node_data['node_id']}.bin"
                        
                        # 根据文件类型选择合适的上传服务
                        if node.node_type == 'audio':
                            file_name = runninghub_service.upload_audio_file(file_data, filename, task_id)
                        else:
                            file_name = runninghub_service.upload_file(file_data, filename, task_id)
                        
                        # 用返回的fileName替换原始field_value
                        field_value = file_name
                        
                    except Exception as e:
                        # 文件上传失败，记录错误并返回错误响应
                        # 绝对不能将base64数据存储到数据库中
                        from flask import current_app
                        current_app.logger.error(f"File upload failed for node {node_data['node_id']} (type: {node.node_type}): {e}")
                        return jsonify({'error': f'File upload failed for node {node_data["node_id"]}: {str(e)}'}), 500
            
            # 创建任务数据记录
            task_data = TaskData(
                task_id=task_id,
                node_id=node_data['node_id'],
                field_name=node_data['field_name'],
                field_value=field_value  # 使用处理后的值（可能是fileName）
            )
            db.session.add(task_data)
    
    db.session.commit()
    
    return jsonify(task.to_dict()), 201

@bp.route('/<task_id>', methods=['GET'])
def get_task(task_id):
    """获取特定任务详细信息"""
    task_details = task_controller.get_task_details(task_id)
    if not task_details:
        return jsonify({'error': 'Task not found'}), 404
    
    return jsonify(task_details)

@bp.route('/<task_id>/start', methods=['POST'])
def start_task(task_id):
    """启动任务"""
    success, message = task_controller.start_single_task(task_id)
    
    if success:
        return jsonify({'message': message})
    else:
        return jsonify({'error': message}), 400

@bp.route('/<task_id>/stop', methods=['POST'])
def stop_task(task_id):
    """停止任务"""
    success, message = task_controller.stop_single_task(task_id)
    
    if success:
        return jsonify({'message': message})
    else:
        return jsonify({'error': message}), 400

@bp.route('/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    """删除任务"""
    success, message = task_controller.delete_single_task(task_id)
    
    if success:
        return jsonify({'message': message})
    else:
        return jsonify({'error': message}), 400

@bp.route('/upload', methods=['POST'])
def upload_file():
    """文件上传接口"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # 获取任务ID（如果有）
    task_id = request.headers.get('X-Task-ID')
    
    try:
        # 调用RunningHub服务上传文件
        runninghub_service = RunningHubService()
        file_data = file.read()
        file_name = runninghub_service.upload_file(file_data, file.filename, task_id)
        
        return jsonify({
            'fileName': file_name,
            'originalName': file.filename,
            'message': 'File uploaded successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/upload/audio', methods=['POST'])
def upload_audio_file():
    """音频文件上传接口"""
    if 'file' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No audio file selected'}), 400
    
    # 获取任务ID（如果有）
    task_id = request.headers.get('X-Task-ID')
    
    try:
        # 调用RunningHub服务上传音频文件
        runninghub_service = RunningHubService()
        file_data = file.read()
        file_name = runninghub_service.upload_audio_file(file_data, file.filename, task_id)
        
        return jsonify({
            'fileName': file_name,
            'originalName': file.filename,
            'fileType': 'audio',
            'message': 'Audio file uploaded successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 批量操作接口
@bp.route('/batch/start', methods=['POST'])
def batch_start_tasks():
    """批量启动任务"""
    data = request.get_json()
    if not data or 'task_ids' not in data:
        return jsonify({'error': 'Missing task_ids'}), 400
    
    task_ids = data['task_ids']
    if not isinstance(task_ids, list) or not task_ids:
        return jsonify({'error': 'task_ids must be a non-empty list'}), 400
    
    success, message = task_controller.batch_start_tasks(task_ids)
    
    if success:
        return jsonify({'message': message})
    else:
        return jsonify({'error': message}), 400

@bp.route('/batch/stop', methods=['POST'])
def batch_stop_tasks():
    """批量停止任务"""
    data = request.get_json()
    if not data or 'task_ids' not in data:
        return jsonify({'error': 'Missing task_ids'}), 400
    
    task_ids = data['task_ids']
    if not isinstance(task_ids, list) or not task_ids:
        return jsonify({'error': 'task_ids must be a non-empty list'}), 400
    
    success, message = task_controller.batch_stop_tasks(task_ids)
    
    if success:
        return jsonify({'message': message})
    else:
        return jsonify({'error': message}), 400

@bp.route('/batch/delete', methods=['DELETE'])
def batch_delete_tasks():
    """批量删除任务"""
    data = request.get_json()
    if not data or 'task_ids' not in data:
        return jsonify({'error': 'Missing task_ids'}), 400
    
    task_ids = data['task_ids']
    if not isinstance(task_ids, list) or not task_ids:
        return jsonify({'error': 'task_ids must be a non-empty list'}), 400
    
    success, message = task_controller.batch_delete_tasks(task_ids)
    
    if success:
        return jsonify({'message': message})
    else:
        return jsonify({'error': message}), 400

# 状态和统计接口
@bp.route('/queue/status', methods=['GET'])
def get_queue_status():
    """获取队列状态"""
    status = task_controller.get_queue_status()
    return jsonify(status)

@bp.route('/statistics', methods=['GET'])
def get_task_statistics():
    """获取任务统计信息"""
    stats = task_controller.get_task_statistics()
    return jsonify(stats)

@bp.route('/<task_id>/progress', methods=['GET'])
def get_task_progress(task_id):
    """获取任务进度"""
    progress = task_controller.get_task_progress(task_id)
    if progress is not None:
        return jsonify(progress)
    else:
        return jsonify({'error': 'Progress not available'}), 404

@bp.route('/<task_id>/outputs', methods=['GET'])
def get_task_outputs(task_id):
    """获取任务输出文件列表"""
    outputs = task_controller.get_task_outputs(task_id)
    return jsonify(outputs)

@bp.route('/<task_id>/outputs/<output_name>', methods=['GET'])
def download_task_output(task_id, output_name):
    """下载任务输出文件"""
    file_data = task_controller.download_task_output(task_id, output_name)
    if file_data:
        from flask import make_response
        response = make_response(file_data)
        response.headers['Content-Disposition'] = f'attachment; filename={output_name}'
        return response
    else:
        return jsonify({'error': 'File not found'}), 404

@bp.route('/<task_id>/logs', methods=['GET'])
def get_task_logs(task_id):
    """获取任务执行日志"""
    logs = task_controller.get_task_logs(task_id)
    return jsonify(logs)

@bp.route('/<task_id>/logs/history', methods=['GET'])
def get_task_logs_history(task_id):
    """获取任务历史日志"""
    logs = task_controller.get_task_logs_history(task_id)
    return jsonify(logs)

@bp.route('/<task_id>/download-files', methods=['POST'])
def download_task_files(task_id):
    """下载任务输出文件到本地 - 已禁用（远程模式）"""
    return jsonify({'error': 'File download is disabled in remote-only mode'}), 403
    
    # 原有逻辑已禁用
    # try:
    #     # 检查是否为远程模式
    #     from flask import current_app
    #     remote_only_mode = current_app.config.get('REMOTE_ONLY_MODE', False)
    #     if remote_only_mode:
    #         return jsonify({'error': 'File download is disabled in remote-only mode'}), 403
    #     
    #     result = task_controller.download_task_files(task_id)
    #     return jsonify(result)
    # except Exception as e:
    #     return jsonify({'error': str(e)}), 500

@bp.route('/<task_id>/refresh-files', methods=['POST'])
def refresh_task_files(task_id):
    """刷新任务输出文件"""
    try:
        updated_count = task_controller.refresh_task_files(task_id)
        return jsonify({
            'success': True,
            'updated_count': updated_count,
            'message': f'成功更新 {updated_count} 个文件'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/<task_id>/sync', methods=['POST'])
def sync_task_status(task_id):
    """手动同步单个任务状态"""
    try:
        from app.services.recovery_service import recovery_service
        
        success = recovery_service.manual_sync_task(task_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Task status synced successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to sync task status - task not found or no remote ID'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/recovery/stats', methods=['GET'])
def get_recovery_stats():
    """获取系统恢复统计信息"""
    try:
        from app.services.recovery_service import recovery_service
        
        stats = recovery_service.get_recovery_stats()
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/recovery/trigger', methods=['POST'])
def trigger_recovery():
    """手动触发系统恢复"""
    try:
        from app.services.recovery_service import recovery_service
        from flask import current_app
        
        with current_app.app_context():
            recovery_stats = recovery_service.perform_recovery(delay_seconds=0)
            
        return jsonify({
            'success': True,
            'message': 'Recovery completed successfully',
            'stats': recovery_stats
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/<task_id>/update-status', methods=['POST'])
def update_task_status(task_id):
    """根据远程任务ID更新任务状态"""
    try:
        data = request.get_json()
        remote_task_id = data.get('remote_task_id')
        
        if not remote_task_id:
            return jsonify({'error': '缺少远程任务ID'}), 400
        
        # 获取本地任务
        task = Task.query.filter_by(task_id=task_id).first()
        if not task:
            return jsonify({'error': '任务不存在'}), 404
        
        # 记录原始状态
        old_status = task.status
        
        # 查询远程任务状态
        from app.services.runninghub import RunningHubService
        runninghub_service = RunningHubService()
        
        try:
            # get_task_status返回字符串状态
            remote_status = runninghub_service.get_status(remote_task_id, task_id)
            
            if not remote_status:
                return jsonify({'error': '无法获取远程任务状态'}), 500
            
            # 映射远程状态到本地状态
            status_mapping = {
                'PENDING': 'PENDING',
                'RUNNING': 'RUNNING', 
                'SUCCESS': 'SUCCESS',
                'FAILED': 'FAILED',
                'CANCELLED': 'FAILED',
                'queue': 'PENDING',
                'running': 'RUNNING',
                'success': 'SUCCESS',
                'failed': 'FAILED',
                'cancelled': 'FAILED'
            }
            
            new_status = status_mapping.get(remote_status, 'UNKNOWN')
            
            # 更新本地任务状态
            task.status = new_status
            db.session.commit()
            
            return jsonify({
                'success': True,
                'old_status': old_status,
                'new_status': new_status,
                'remote_status': remote_status
            })
            
        except Exception as e:
            return jsonify({'error': f'查询远程任务状态失败: {str(e)}'}), 500
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500