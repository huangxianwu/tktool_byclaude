from flask import Blueprint, request, jsonify, send_file
from app.services.file_manager import FileManager
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
            download_name=f"output_{output.node_id}.{output.file_type}"
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
                    filename = f"node_{output.node_id}.{output.file_type}"
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