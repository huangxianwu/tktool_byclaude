import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from flask import current_app
from flask_socketio import SocketIO, emit, join_room, leave_room
from app import db
from app.models.Task import Task
from app.models.TaskLog import TaskLog
from app.services.error_handler import ErrorHandler, ErrorCode

logger = logging.getLogger(__name__)

class StatusMonitor:
    """状态监控服务 - 提供实时状态推送和任务执行进度显示"""
    
    def __init__(self, socketio: Optional[SocketIO] = None):
        self.socketio = socketio
        self.connected_clients: Dict[str, Dict[str, Any]] = {}
        
    def set_socketio(self, socketio: SocketIO):
        """设置SocketIO实例"""
        self.socketio = socketio
        
    def register_client(self, client_id: str, user_info: Dict[str, Any] = None):
        """注册客户端"""
        self.connected_clients[client_id] = {
            'connected_at': datetime.utcnow(),
            'user_info': user_info or {},
            'subscribed_tasks': set()
        }
        logger.info(f"Client {client_id} registered")
        
    def unregister_client(self, client_id: str):
        """注销客户端"""
        if client_id in self.connected_clients:
            del self.connected_clients[client_id]
            logger.info(f"Client {client_id} unregistered")
            
    def subscribe_task(self, client_id: str, task_id: str):
        """订阅任务状态更新"""
        if client_id in self.connected_clients:
            self.connected_clients[client_id]['subscribed_tasks'].add(task_id)
            
            # 发送当前任务状态
            task_status = self.get_task_status(task_id)
            if task_status:
                self.emit_to_client(client_id, 'task_status_update', task_status)
                
    def unsubscribe_task(self, client_id: str, task_id: str):
        """取消订阅任务状态更新"""
        if client_id in self.connected_clients:
            self.connected_clients[client_id]['subscribed_tasks'].discard(task_id)
            
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态信息"""
        try:
            task = Task.query.filter_by(task_id=task_id).first()
            if not task:
                return None
                
            # 获取最新日志
            latest_logs = TaskLog.query.filter_by(task_id=task_id).order_by(
                TaskLog.created_at.desc()
            ).limit(5).all()
            
            # 计算进度
            progress = self.calculate_task_progress(task)
            
            return {
                'task_id': task.task_id,
                'status': task.status,
                'progress': progress,
                'created_at': task.created_at.isoformat() if task.created_at else None,
                'started_at': task.started_at.isoformat() if task.started_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'workflow_id': task.workflow_id,
                'runninghub_task_id': task.runninghub_task_id,
                'latest_logs': [{
                    'message': log.message,
                    'created_at': log.created_at.isoformat()
                } for log in latest_logs],
                'estimated_completion': self.estimate_completion_time(task)
            }
            
        except Exception as e:
            logger.error(f"Error getting task status for {task_id}: {e}")
            return None
            
    def calculate_task_progress(self, task: Task) -> Dict[str, Any]:
        """计算任务进度"""
        if task.status == 'PENDING':
            return {'percentage': 0, 'stage': '等待中', 'description': '任务已创建，等待执行'}
        elif task.status == 'QUEUED':
            return {'percentage': 10, 'stage': '排队中', 'description': '任务已提交到执行队列'}
        elif task.status == 'RUNNING':
            # 基于运行时间估算进度
            if task.started_at:
                elapsed = (datetime.utcnow() - task.started_at).total_seconds()
                # 假设平均任务执行时间为5分钟
                estimated_total = 300  # 5分钟
                percentage = min(90, 10 + (elapsed / estimated_total) * 80)
                return {'percentage': int(percentage), 'stage': '执行中', 'description': f'任务正在执行中，已运行{int(elapsed/60)}分钟'}
            return {'percentage': 20, 'stage': '执行中', 'description': '任务正在执行中'}
        elif task.status == 'SUCCESS':
            return {'percentage': 100, 'stage': '已完成', 'description': '任务执行成功'}
        elif task.status == 'FAILED':
            return {'percentage': 0, 'stage': '已失败', 'description': '任务执行失败'}
        elif task.status == 'CANCELLED':
            return {'percentage': 0, 'stage': '已取消', 'description': '任务已被取消'}
        else:
            return {'percentage': 0, 'stage': '未知', 'description': '任务状态未知'}
            
    def estimate_completion_time(self, task: Task) -> Optional[str]:
        """估算任务完成时间"""
        if task.status not in ['RUNNING', 'QUEUED']:
            return None
            
        if task.status == 'RUNNING' and task.started_at:
            elapsed = (datetime.utcnow() - task.started_at).total_seconds()
            # 基于历史数据估算剩余时间（这里使用简单的固定时间）
            estimated_remaining = max(0, 300 - elapsed)  # 假设总共5分钟
            if estimated_remaining > 0:
                completion_time = datetime.utcnow().timestamp() + estimated_remaining
                return datetime.fromtimestamp(completion_time).isoformat()
                
        return None
        
    def broadcast_task_update(self, task_id: str, update_type: str = 'status_change'):
        """广播任务状态更新"""
        if not self.socketio:
            return
            
        task_status = self.get_task_status(task_id)
        if not task_status:
            return
            
        # 找到订阅了该任务的客户端
        subscribed_clients = []
        for client_id, client_info in self.connected_clients.items():
            if task_id in client_info['subscribed_tasks']:
                subscribed_clients.append(client_id)
                
        # 发送更新给订阅的客户端
        for client_id in subscribed_clients:
            self.emit_to_client(client_id, 'task_status_update', {
                'type': update_type,
                'task': task_status
            })
            
        logger.debug(f"Broadcasted task update for {task_id} to {len(subscribed_clients)} clients")
        
    def broadcast_system_status(self):
        """广播系统状态"""
        if not self.socketio:
            return
            
        system_status = self.get_system_status()
        
        for client_id in self.connected_clients.keys():
            self.emit_to_client(client_id, 'system_status_update', system_status)
            
    def broadcast_health_status(self, health_data: Dict[str, Any]):
        """广播健康状态"""
        if not self.socketio:
            return
            
        for client_id in self.connected_clients.keys():
            self.emit_to_client(client_id, 'health_status_update', health_data)
            
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            # 统计各状态任务数量
            status_counts = db.session.query(
                Task.status,
                db.func.count(Task.task_id)
            ).group_by(Task.status).all()
            
            status_summary = {status: count for status, count in status_counts}
            
            # 获取队列信息
            pending_count = status_summary.get('PENDING', 0)
            running_count = status_summary.get('RUNNING', 0) + status_summary.get('QUEUED', 0)
            
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'queue_status': {
                    'pending': pending_count,
                    'running': running_count,
                    'total_capacity': 10  # 假设最大并发数为10
                },
                'task_statistics': status_summary,
                'connected_clients': len(self.connected_clients)
            }
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e)
            }
            
    def emit_to_client(self, client_id: str, event: str, data: Any):
        """向特定客户端发送消息"""
        if self.socketio:
            try:
                self.socketio.emit(event, data, room=client_id)
            except Exception as e:
                logger.error(f"Error emitting to client {client_id}: {e}")
                
    def emit_error(self, client_id: str, error_code: ErrorCode, details: str = None):
        """向客户端发送错误信息"""
        error_response = ErrorHandler.format_error_response(error_code, details)
        self.emit_to_client(client_id, 'error', error_response)
        
    def get_client_count(self) -> int:
        """获取连接的客户端数量"""
        return len(self.connected_clients)
        
    def get_subscribed_tasks(self, client_id: str) -> List[str]:
        """获取客户端订阅的任务列表"""
        if client_id in self.connected_clients:
            return list(self.connected_clients[client_id]['subscribed_tasks'])
        return []
        
    def cleanup_disconnected_clients(self):
        """清理断开连接的客户端"""
        # 这个方法应该由SocketIO的disconnect事件调用
        pass

# 全局状态监控实例
status_monitor = StatusMonitor()

def init_status_monitor(socketio: SocketIO):
    """初始化状态监控服务"""
    status_monitor.set_socketio(socketio)
    
    @socketio.on('connect')
    def handle_connect():
        client_id = request.sid
        status_monitor.register_client(client_id)
        emit('connected', {'client_id': client_id})
        
    @socketio.on('disconnect')
    def handle_disconnect():
        client_id = request.sid
        status_monitor.unregister_client(client_id)
        
    @socketio.on('subscribe_task')
    def handle_subscribe_task(data):
        client_id = request.sid
        task_id = data.get('task_id')
        if task_id:
            status_monitor.subscribe_task(client_id, task_id)
            
    @socketio.on('unsubscribe_task')
    def handle_unsubscribe_task(data):
        client_id = request.sid
        task_id = data.get('task_id')
        if task_id:
            status_monitor.unsubscribe_task(client_id, task_id)
            
    @socketio.on('get_system_status')
    def handle_get_system_status():
        client_id = request.sid
        system_status = status_monitor.get_system_status()
        status_monitor.emit_to_client(client_id, 'system_status', system_status)
        
    logger.info("Status monitor initialized with SocketIO")
    
    return status_monitor