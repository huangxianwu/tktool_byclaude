from flask import Blueprint, request, jsonify
from app import db
from app.models import Task, TaskData, Node
from app.services.runninghub import RunningHubService
from app.managers.TaskQueueManager import TaskQueueManager
import uuid
import base64

bp = Blueprint('tasks', __name__, url_prefix='/api/tasks')

@bp.route('', methods=['GET'])
def get_tasks():
    """获取所有任务"""
    tasks = Task.query.all()
    return jsonify([task.to_dict() for task in tasks])

@bp.route('', methods=['POST'])
def create_task():
    """创建新任务"""
    data = request.get_json()
    
    if not data or 'workflow_id' not in data:
        return jsonify({'error': 'Missing workflow_id'}), 400
    
    # 生成任务ID
    task_id = str(uuid.uuid4())
    
    # 创建任务
    task = Task(task_id=task_id, workflow_id=data['workflow_id'])
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
    """获取特定任务"""
    task = Task.query.get_or_404(task_id)
    
    # 获取任务数据
    task_data = TaskData.query.filter_by(task_id=task_id).all()
    
    result = task.to_dict()
    result['data'] = [td.to_dict() for td in task_data]
    
    return jsonify(result)

@bp.route('/<task_id>/run', methods=['POST'])
def run_task(task_id):
    """运行任务"""
    task = Task.query.get_or_404(task_id)
    
    # 检查任务状态
    if task.status not in ['PENDING', 'FAILED']:
        return jsonify({'error': 'Task is already running or completed'}), 400
    
    # 启动任务
    task_manager = TaskQueueManager()
    success = task_manager.start_task(task_id)
    
    if success:
        return jsonify({'message': 'Task started'})
    else:
        return jsonify({'error': 'Task is already running'}), 400

@bp.route('/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    """删除任务"""
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    
    return jsonify({'message': 'Task deleted'})

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