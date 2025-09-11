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
    tasks = task_controller.get_tasks_with_workflow_info()
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
    task = Task(task_id=task_id, workflow_id=data['workflow_id'], status='READY', is_plus=is_plus)
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
            if node and node.node_type in ['image', 'video'] and field_value:
                try:
                    # 检查是否为base64编码的文件数据
                    if isinstance(field_value, str) and (
                        field_value.startswith('data:') or 
                        len(field_value) > 1000  # 假设超过1000字符可能是文件数据
                    ):
                        # 解析文件数据 
                        if field_value.startswith('data:'):
                            # base64 data URL格式: data:image/png;base64,iVBORw0KGgoAAAA...
                            header, encoded = field_value.split(',', 1)
                            file_data = base64.b64decode(encoded)
                            
                            # 从header中提取文件类型
                            if 'image/' in header:
                                filename = f"upload_{task_id}.png"
                            elif 'video/' in header:
                                filename = f"upload_{task_id}.mp4"
                            else:
                                filename = f"upload_{task_id}.bin"
                        else:
                            # 纯base64数据
                            file_data = base64.b64decode(field_value)
                            filename = f"upload_{task_id}_{node_data['node_id']}.{node.node_type}"
                        
                        # 上传文件到RunningHub
                        file_name = runninghub_service.upload_file(file_data, filename, task_id)
                        
                        # 用返回的fileName替换原始field_value
                        field_value = file_name
                        
                except Exception as e:
                    # 文件上传失败，记录错误但继续处理
                    print(f"File upload failed for node {node_data['node_id']}: {e}")
                    # 可以选择返回错误或使用原始值
                    # return jsonify({'error': f'File upload failed: {str(e)}'}), 500
            
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