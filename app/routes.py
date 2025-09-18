from flask import Blueprint, render_template, send_from_directory, current_app
from app.models import Workflow
import os

# Create a blueprint for the main routes
bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    return render_template('workflows.html')

@bp.route('/workflows')
def workflows():
    return render_template('workflows.html')

@bp.route('/tasks/create/<workflow_id>')
def task_create(workflow_id):
    return render_template('task_create.html')

@bp.route('/tasks')
def tasks():
    return render_template('task_management.html')

@bp.route('/outputs')
def outputs():
    """输出结果页面"""
    return render_template('outputs.html')

@bp.route('/queue')  
def queue():
    """任务队列管理页面"""
    return render_template('task_management.html')

@bp.route('/tasks/<task_id>')
def task_detail(task_id):
    return render_template('task_detail.html')

@bp.route('/task_detail/<task_id>')
def task_detail_page(task_id):
    return render_template('task_detail.html')

@bp.route('/workflows/edit/<workflow_id>')
def edit_workflow(workflow_id):
    workflow = Workflow.query.get_or_404(workflow_id)
    return render_template('edit_workflow.html', workflow=workflow.to_dict())

@bp.route('/file-test')
def file_test():
    """文件显示测试页面"""
    return render_template('file_test.html')

@bp.route('/static/outputs/<path:filename>')
def serve_output_file(filename):
    """服务输出文件的静态路由"""
    try:
        output_dir = current_app.config.get('OUTPUT_FILES_DIR', 'outputs')
        # 使用绝对路径
        if not os.path.isabs(output_dir):
            output_dir = os.path.abspath(output_dir)
        return send_from_directory(output_dir, filename)
    except Exception as e:
        return f"File not found: {str(e)}", 404