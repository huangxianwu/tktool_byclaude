from flask import Blueprint, Response, request, jsonify
from app import db
from app.models import TaskLog
import json
import time

bp = Blueprint('task_logs', __name__, url_prefix='/api/tasks')

@bp.route('/<task_id>/logs', methods=['GET'])
def get_task_logs(task_id):
    """获取任务日志（SSE流）"""
    from app import create_app
    
    # 创建应用实例用于数据库查询
    app = create_app()
    
    def generate():
        with app.app_context():
            # 获取现有日志
            logs = TaskLog.query.filter_by(task_id=task_id).order_by(TaskLog.timestamp.asc()).all()
            last_id = logs[-1].id if logs else 0
            
            # 发送现有日志
            for log in logs:
                yield f"data: {json.dumps(log.to_dict())}\n\n"
        
        while True:
            with app.app_context():
                # 查询新日志
                new_logs = TaskLog.query.filter(
                    TaskLog.task_id == task_id,
                    TaskLog.id > last_id
                ).order_by(TaskLog.timestamp.asc()).all()
                
                for log in new_logs:
                    yield f"data: {json.dumps(log.to_dict())}\n\n"
                    last_id = log.id
            
            # 每秒检查一次
            time.sleep(1)
    
    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*'
        }
    )

@bp.route('/<task_id>/logs/history', methods=['GET'])
def get_task_logs_history(task_id):
    """获取任务历史日志"""
    logs = TaskLog.query.filter_by(task_id=task_id).order_by(TaskLog.timestamp.asc()).all()
    return jsonify([log.to_dict() for log in logs])