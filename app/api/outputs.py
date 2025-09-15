from flask import Blueprint, request, jsonify, send_file
from app.services.file_manager import FileManager
from app.services.recovery_service import RecoveryService
from app.models import TaskOutput
import os

bp = Blueprint('outputs', __name__, url_prefix='/api/tasks')

@bp.route('/<task_id>/outputs', methods=['GET'])
def get_task_outputs(task_id):
    """获取任务的输出文件列表"""
    try:
        file_manager = FileManager()
        outputs = file_manager.get_task_outputs_with_fallback(task_id)
        return jsonify(outputs)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/<task_id>/outputs/<int:output_id>/download', methods=['GET'])
def download_output_file(task_id, output_id):
    """下载特定的输出文件"""
    try:
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

@bp.route('/<task_id>/outputs/download-all', methods=['GET'])
def download_all_outputs(task_id):
    """打包下载所有输出文件"""
    try:
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
    """批量恢复输出文件"""
    try:
        data = request.get_json() or {}
        task_ids = data.get('task_ids')  # 可选，如果不提供则恢复所有SUCCESS任务
        
        recovery_service = RecoveryService()
        result = recovery_service.batch_restore_files(task_ids)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/<task_id>/restore', methods=['POST'])
def restore_task_files(task_id):
    """恢复单个任务的输出文件"""
    try:
        recovery_service = RecoveryService()
        success = recovery_service.manual_sync_task(task_id)
        
        if success:
            return jsonify({'message': f'Task {task_id} files restored successfully'})
        else:
            return jsonify({'error': f'Failed to restore files for task {task_id}'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/<task_id>/outputs/status', methods=['GET'])
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