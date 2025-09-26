from flask import Blueprint, request, jsonify, send_file, current_app
from app.services.file_manager import FileManager
from app.services.recovery_service import RecoveryService
from app.models import TaskOutput
import os
from urllib.parse import urlparse

bp = Blueprint('outputs', __name__, url_prefix='/api')

@bp.route('/outputs', methods=['GET'])
def get_all_outputs():
    """获取所有输出结果 - 仅使用数据库查询，支持筛选排序分页"""
    try:
        from app.models import Task, Workflow
        from sqlalchemy import and_, or_, desc, asc
        from datetime import datetime, timedelta
        
        # 获取筛选参数
        workflow_id = request.args.get('workflow')
        file_type = request.args.get('type')
        time_range = request.args.get('timeRange')
        search = request.args.get('search', '').strip()
        sort_by = request.args.get('sort', 'created_at_desc')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('pageSize', 20))
        
        # 构建基础查询 - 联表查询 TaskOutput, Task, Workflow
        query = TaskOutput.query.join(Task, TaskOutput.task_id == Task.task_id)\
                                .join(Workflow, Task.workflow_id == Workflow.workflow_id)\
                                .filter(Task.status == 'SUCCESS')
        
        # 工作流筛选
        if workflow_id:
            query = query.filter(Task.workflow_id == workflow_id)
        
        # 文件类型筛选
        if file_type:
            query = query.filter(TaskOutput.file_type == file_type)
        
        # 时间范围筛选
        if time_range:
            now = datetime.now()
            if time_range == 'today':
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif time_range == 'week':
                start_date = now - timedelta(days=7)
            elif time_range == 'month':
                start_date = now - timedelta(days=30)
            else:
                start_date = None
            
            if start_date:
                query = query.filter(TaskOutput.created_at >= start_date)
        
        # 搜索筛选 - 支持任务描述、工作流名称、文件名搜索
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    TaskOutput.name.ilike(search_pattern),
                    Task.task_id.ilike(search_pattern),
                    Task.task_description.ilike(search_pattern),
                    Workflow.name.ilike(search_pattern)
                )
            )
        
        # 排序
        if sort_by == 'created_at_desc':
            query = query.order_by(desc(TaskOutput.created_at))
        elif sort_by == 'created_at_asc':
            query = query.order_by(asc(TaskOutput.created_at))
        elif sort_by == 'size_desc':
            query = query.order_by(desc(TaskOutput.file_size))
        elif sort_by == 'size_asc':
            query = query.order_by(asc(TaskOutput.file_size))
        else:
            query = query.order_by(desc(TaskOutput.created_at))
        
        # 分页查询
        total_count = query.count()
        outputs_query = query.offset((page - 1) * page_size).limit(page_size)
        
        # 构建返回结果
        outputs = []
        for output in outputs_query:
            task = output.task
            workflow = task.workflow
            
            output_item = {
                'id': f"{task.task_id}_{output.name}",
                'filename': output.name,
                'file_path': output.file_url,  # Remote-only 模式只使用 file_url
                'file_size': output.file_size or 0,
                'task_id': task.task_id,
                'task_description': task.task_description or '',
                'workflow_id': task.workflow_id,
                'workflow_name': workflow.name if workflow else '未知工作流',
                'created_at': output.created_at.isoformat() if output.created_at else task.created_at.isoformat(),
                'thumbnail_path': output.thumbnail_path or '',  # 使用缩略图路径
                'file_type': output.file_type or get_file_type_from_name(output.name)
            }
            outputs.append(output_item)
        
        return jsonify({
            'outputs': outputs,
            'total': total_count,
            'page': page,
            'pageSize': page_size,
            'totalPages': (total_count + page_size - 1) // page_size
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting all outputs: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/download/<path:file_path>', methods=['GET'])
def download_file(file_path):
    """通用文件下载接口"""
    try:
        import os
        from urllib.parse import unquote
        
        # 解码文件路径
        file_path = unquote(file_path)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return jsonify({'error': '文件不存在'}), 404
        
        # 获取文件名
        filename = os.path.basename(file_path)
        
        # 发送文件
        return send_file(file_path, as_attachment=True, download_name=filename)
        
    except Exception as e:
        current_app.logger.error(f"下载文件失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

def get_file_type_from_name(filename):
    """根据文件名获取文件类型"""
    if not filename:
        return 'other'
    
    ext = filename.split('.')[-1].lower() if '.' in filename else ''
    
    if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg']:
        return 'image'
    elif ext in ['mp4', 'avi', 'mov', 'wmv', 'flv', 'webm']:
        return 'video'
    elif ext in ['mp3', 'wav', 'flac', 'aac', 'ogg']:
        return 'audio'
    elif ext in ['txt', 'md', 'json', 'xml', 'csv']:
        return 'text'
    else:
        return 'other'

def apply_output_filters(outputs, file_type, time_range, search):
    """应用筛选条件"""
    filtered = outputs
    
    # 文件类型筛选
    if file_type:
        filtered = [o for o in filtered if o['file_type'] == file_type]
    
    # 时间范围筛选
    if time_range:
        from datetime import datetime, timedelta
        now = datetime.now()
        
        if time_range == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_range == 'week':
            start_date = now - timedelta(days=7)
        elif time_range == 'month':
            start_date = now - timedelta(days=30)
        else:
            start_date = None
        
        if start_date:
            filtered = [o for o in filtered if datetime.fromisoformat(o['created_at'].replace('Z', '+00:00')) >= start_date]
    
    # 搜索筛选 - 支持任务描述、工作流名称、文件名搜索
    if search:
        search_lower = search.lower()
        filtered = [o for o in filtered if 
                   search_lower in o['filename'].lower() or
                   search_lower in o['task_id'].lower() or
                   search_lower in o['workflow_name'].lower() or
                   search_lower in (o.get('task_description', '') or '').lower()]
    
    return filtered

def sort_outputs(outputs, sort_by):
    """排序输出结果"""
    if sort_by == 'created_at_desc':
        return sorted(outputs, key=lambda x: x['created_at'], reverse=True)
    elif sort_by == 'created_at_asc':
        return sorted(outputs, key=lambda x: x['created_at'])
    elif sort_by == 'size_desc':
        return sorted(outputs, key=lambda x: x['file_size'], reverse=True)
    elif sort_by == 'size_asc':
        return sorted(outputs, key=lambda x: x['file_size'])
    else:
        return outputs

# 保持原有的任务相关端点
bp_tasks = Blueprint('outputs_tasks', __name__, url_prefix='/api/tasks')

@bp_tasks.route('/<task_id>/outputs', methods=['GET'])
def get_task_outputs(task_id):
    """获取任务的输出文件列表 - 优先 TaskOutput，缺失时调用 RunningHub 并可选幂等回写"""
    try:
        # 首先查询 TaskOutput 表
        task_outputs = TaskOutput.query.filter_by(task_id=task_id).all()
        
        if task_outputs:
            # 如果有 TaskOutput 记录，直接返回
            outputs = []
            for output in task_outputs:
                output_item = {
                    'id': output.id,
                    'name': output.name,
                    'url': output.file_url,
                    'node_id': output.node_id,
                    'file_url': output.file_url,
                    'file_type': output.file_type,
                    'file_size': output.file_size,
                    'thumbnail_url': output.thumbnail_url,
                    'source': 'database',
                    'is_local': False,
                    'created_at': output.created_at.isoformat() if output.created_at else None
                }
                outputs.append(output_item)
            return jsonify(outputs)
        
        # 如果没有 TaskOutput 记录，回退到 RunningHub
        from app.models.Task import Task
        task = Task.query.get(task_id)
        if not task or not task.runninghub_task_id:
            return jsonify([])
        
        try:
            from app.services.runninghub import RunningHubService
            runninghub_service = RunningHubService()
            remote_outputs = runninghub_service.get_task_outputs(task.runninghub_task_id)
            
            if not remote_outputs:
                return jsonify([])
            
            # 检查是否开启回写功能
            backfill_enabled = current_app.config.get('BACKFILL_ON_FALLBACK', True)
            
            if backfill_enabled:
                # 幂等回写到 TaskOutput
                from app import db
                from datetime import datetime
                
                for i, output in enumerate(remote_outputs):
                    file_url = output.get('url', '')
                    file_name = output.get('name', f'output_{i}.file')
                    file_size = output.get('size', 0)
                    node_id = output.get('nodeId', f'node_{i}')
                    
                    if file_url:  # 只有有效的 file_url 才写入
                        try:
                            # 幂等检查：基于 task_id + node_id + file_url 的唯一约束
                            existing = TaskOutput.query.filter_by(
                                task_id=task_id,
                                node_id=node_id,
                                file_url=file_url
                            ).first()
                            
                            if not existing:
                                # 推断文件类型
                                file_type = get_file_type_from_name(file_name)
                                
                                task_output = TaskOutput(
                                    task_id=task_id,
                                    node_id=node_id,
                                    name=file_name,
                                    file_url=file_url,
                                    file_type=file_type,
                                    file_size=file_size,
                                    local_path=None,  # Remote-only 模式不保存本地路径
                                    thumbnail_path=None,  # Remote-only 模式不保存本地缩略图
                                    thumbnail_url=output.get('thumbnail_url'),  # 保存远程缩略图URL
                                    created_at=datetime.utcnow()
                                )
                                db.session.add(task_output)
                        except Exception as e:
                            current_app.logger.warning(f"Failed to backfill TaskOutput for {task_id}: {e}")
                            continue
                
                try:
                    db.session.commit()
                    current_app.logger.info(f"Successfully backfilled TaskOutput records for task {task_id}")
                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Failed to commit TaskOutput backfill for task {task_id}: {e}")
            
            # 格式化返回结果
            result = []
            for i, output in enumerate(remote_outputs):
                file_url = output.get('url', '')
                file_name = output.get('name', f'output_{i}.file')
                file_size = output.get('size', 0)
                node_id = output.get('nodeId', f'node_{i}')
                
                result.append({
                    'id': f"{task_id}_{node_id}",
                    'name': file_name,
                    'url': file_url,
                    'node_id': node_id,
                    'file_url': file_url,
                    'file_type': get_file_type_from_name(file_name),
                    'file_size': file_size,
                    'thumbnail_url': output.get('thumbnail_url', ''),
                    'source': 'runninghub',
                    'is_local': False,
                    'created_at': None
                })
            
            return jsonify(result)
            
        except Exception as e:
            current_app.logger.error(f"Failed to fetch outputs from RunningHub for task {task_id}: {e}")
            return jsonify({'error': f'Failed to fetch remote outputs: {str(e)}'}), 500
        
    except Exception as e:
        current_app.logger.error(f"Error getting task outputs for {task_id}: {e}")
        return jsonify({'error': str(e)}), 500

@bp_tasks.route('/<task_id>/generate-filename', methods=['POST'])
def generate_custom_filename(task_id):
    """为文件生成自定义文件名"""
    try:
        data = request.get_json()
        file_url = data.get('fileUrl')
        original_filename = data.get('originalFilename')
        index = data.get('index', 0)
        
        if not file_url:
            return jsonify({'error': 'fileUrl is required'}), 400
        
        # 如果没有提供原始文件名，从URL中提取
        if not original_filename:
            parsed_url = urlparse(file_url)
            original_filename = os.path.basename(parsed_url.path) or 'output.png'
        
        file_manager = FileManager()
        custom_filename = file_manager._generate_custom_filename(task_id, original_filename, index)
        
        return jsonify({
            'customFilename': custom_filename,
            'originalFilename': original_filename
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp_tasks.route('/<task_id>/outputs/<int:output_id>/download', methods=['GET'])
def download_output_file(task_id, output_id):
    """下载特定的输出文件"""
    try:
        # 检查是否为远程模式
        remote_only_mode = current_app.config.get('REMOTE_ONLY_MODE', False)
        if remote_only_mode:
            return jsonify({'error': 'File download is disabled in remote-only mode'}), 403
        
        output = TaskOutput.query.filter_by(id=output_id, task_id=task_id).first()
        if not output:
            return jsonify({'error': 'Output not found'}), 404
        
        if not os.path.exists(output.local_path):
            return jsonify({'error': 'File not found on disk'}), 404
        
        return send_file(
            output.local_path,
            as_attachment=True,
            download_name=output.name
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp_tasks.route('/<task_id>/outputs/download-all', methods=['GET'])
def download_all_outputs(task_id):
    """打包下载所有输出文件"""
    try:
        # 检查是否为远程模式
        remote_only_mode = current_app.config.get('REMOTE_ONLY_MODE', False)
        if remote_only_mode:
            return jsonify({'error': 'File download is disabled in remote-only mode'}), 403
        
        import zipfile
        import io
        from datetime import datetime
        
        outputs = TaskOutput.query.filter_by(task_id=task_id).all()
        if not outputs:
            return jsonify({'error': 'No outputs found'}), 404
        
        # 创建内存中的ZIP文件
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for output in outputs:
                if os.path.exists(output.local_path):
                    # 使用数据库中存储的文件名
                    filename = output.name
                    zip_file.write(output.local_path, filename)
        
        zip_buffer.seek(0)
        
        # 返回ZIP文件
        return send_file(
            io.BytesIO(zip_buffer.read()),
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"task_{task_id}_outputs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/batch-restore', methods=['POST'])
def batch_restore_files():
    """批量恢复输出文件 - 已禁用（远程模式）"""
    return jsonify({'error': 'File restore is disabled in remote-only mode'}), 403
    
    # 原有逻辑已禁用
    # try:
    #     data = request.get_json() or {}
    #     task_ids = data.get('task_ids')  # 可选，如果不提供则恢复所有SUCCESS任务
    #     
    #     recovery_service = RecoveryService()
    #     result = recovery_service.batch_restore_files(task_ids)
    #     
    #     return jsonify(result)
    #     
    # except Exception as e:
    #     return jsonify({'error': str(e)}), 500

@bp_tasks.route('/<task_id>/restore', methods=['POST'])
def restore_task_files(task_id):
    """恢复单个任务的输出文件 - 已禁用（远程模式）"""
    return jsonify({'error': 'File restore is disabled in remote-only mode'}), 403
    
    # 原有逻辑已禁用
    # try:
    #     recovery_service = RecoveryService()
    #     success = recovery_service.manual_sync_task(task_id)
    #     
    #     if success:
    #         return jsonify({'message': f'Task {task_id} files restored successfully'})
    #     else:
    #         return jsonify({'error': f'Failed to restore files for task {task_id}'}), 500
    #         
    # except Exception as e:
    #     return jsonify({'error': str(e)}), 500

@bp_tasks.route('/<task_id>/outputs/status', methods=['GET'])
def get_output_status(task_id):
    """获取任务输出文件状态（本地/远程）"""
    try:
        file_manager = FileManager()
        
        # 检查本地文件
        local_outputs = file_manager.get_task_outputs(task_id)
        
        # 获取远程文件信息（不自动下载）
        remote_outputs = file_manager.get_task_outputs_with_fallback(task_id, auto_download=False)
        
        status = {
            'task_id': task_id,
            'has_local_files': len(local_outputs) > 0,
            'local_files_count': len(local_outputs),
            'remote_files_count': len(remote_outputs),
            'files_status': []
        }
        
        # 详细文件状态
        for output in remote_outputs:
            file_status = {
                'name': output.get('name'),
                'source': output.get('source', 'unknown'),
                'is_local': output.get('is_local', False),
                'file_type': output.get('file_type'),
                'file_size': output.get('file_size')
            }
            status['files_status'].append(file_status)
        
        return jsonify(status)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500