import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from flask import current_app
from sqlalchemy import text
from app import db
from app.models.Task import Task
from app.models.TaskLog import TaskLog
from app.services.error_handler import ErrorHandler, ErrorCode

logger = logging.getLogger(__name__)

class AlertLevel:
    """告警级别"""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class MonitoringService:
    """监控告警服务 - 提供异常任务自动告警和系统健康状态检查"""
    
    def __init__(self):
        self.alert_history: List[Dict[str, Any]] = []
        self.max_alert_history = 1000
        
        # 告警阈值配置
        self.thresholds = {
            'max_pending_tasks': 50,  # 最大待处理任务数
            'max_failed_rate': 0.3,   # 最大失败率（30%）
            'max_queue_wait_time': 1800,  # 最大队列等待时间（30分钟）
            'max_execution_time': 3600,   # 最大执行时间（60分钟）
            'min_success_rate': 0.7,      # 最小成功率（70%）
        }
        

        
    def load_config(self):
        """从应用配置加载监控配置"""
        try:
            if current_app:
                config = current_app.config
                
                # 更新阈值配置
                threshold_config = config.get('MONITORING_THRESHOLDS', {})
                self.thresholds.update(threshold_config)
                
        except Exception as e:
            logger.error(f"Error loading monitoring config: {e}")
            
    def check_system_health(self) -> Dict[str, Any]:
        """检查系统健康状态"""
        health_status = {
            'timestamp': datetime.utcnow().isoformat(),
            'overall_status': 'HEALTHY',
            'checks': {},
            'alerts': []
        }
        
        try:
            # 检查数据库连接
            db_health = self._check_database_health()
            health_status['checks']['database'] = db_health
            
            # 检查任务队列状态
            queue_health = self._check_queue_health()
            health_status['checks']['queue'] = queue_health
            
            # 检查任务执行状态
            task_health = self._check_task_execution_health()
            health_status['checks']['task_execution'] = task_health
            
            # 检查系统资源
            resource_health = self._check_resource_health()
            health_status['checks']['resources'] = resource_health
            
            # 汇总健康状态
            all_checks = [db_health, queue_health, task_health, resource_health]
            if any(check['status'] == 'CRITICAL' for check in all_checks):
                health_status['overall_status'] = 'CRITICAL'
            elif any(check['status'] == 'WARNING' for check in all_checks):
                health_status['overall_status'] = 'WARNING'
                
            # 收集告警
            for check in all_checks:
                if check.get('alerts'):
                    health_status['alerts'].extend(check['alerts'])
                    
        except Exception as e:
            logger.error(f"Error checking system health: {e}")
            health_status['overall_status'] = 'ERROR'
            health_status['error'] = str(e)
            
        return health_status
        
    def _check_database_health(self) -> Dict[str, Any]:
        """检查数据库健康状态"""
        try:
            # 简单的数据库连接测试
            db.session.execute(text('SELECT 1'))
            
            return {
                'status': 'HEALTHY',
                'message': 'Database connection is healthy',
                'response_time': 0  # 可以添加响应时间测量
            }
            
        except Exception as e:
            return {
                'status': 'CRITICAL',
                'message': f'Database connection failed: {str(e)}',
                'alerts': [{
                    'level': AlertLevel.CRITICAL,
                    'message': f'Database connection failed: {str(e)}'
                }]
            }
            
    def _check_queue_health(self) -> Dict[str, Any]:
        """检查任务队列健康状态"""
        try:
            # 统计队列状态
            pending_count = Task.query.filter_by(status='PENDING').count()
            running_count = Task.query.filter(
                Task.status.in_(['QUEUED', 'RUNNING'])
            ).count()
            
            alerts = []
            status = 'HEALTHY'
            
            # 检查待处理任务数量
            if pending_count > self.thresholds['max_pending_tasks']:
                alerts.append({
                    'level': AlertLevel.WARNING,
                    'message': f'High number of pending tasks: {pending_count}'
                })
                status = 'WARNING'
                
            # 检查队列等待时间
            long_waiting_tasks = Task.query.filter(
                Task.status == 'PENDING',
                Task.created_at < datetime.utcnow() - timedelta(
                    seconds=self.thresholds['max_queue_wait_time']
                )
            ).count()
            
            if long_waiting_tasks > 0:
                alerts.append({
                    'level': AlertLevel.ERROR,
                    'message': f'{long_waiting_tasks} tasks waiting too long in queue'
                })
                status = 'ERROR'
                
            return {
                'status': status,
                'message': f'Queue status: {pending_count} pending, {running_count} running',
                'metrics': {
                    'pending_tasks': pending_count,
                    'running_tasks': running_count,
                    'long_waiting_tasks': long_waiting_tasks
                },
                'alerts': alerts
            }
            
        except Exception as e:
            return {
                'status': 'ERROR',
                'message': f'Error checking queue health: {str(e)}',
                'alerts': [{
                    'level': AlertLevel.ERROR,
                    'message': f'Queue health check failed: {str(e)}'
                }]
            }
            
    def _check_task_execution_health(self) -> Dict[str, Any]:
        """检查任务执行健康状态"""
        try:
            # 统计最近24小时的任务执行情况
            since = datetime.utcnow() - timedelta(hours=24)
            
            total_tasks = Task.query.filter(Task.created_at >= since).count()
            if total_tasks == 0:
                return {
                    'status': 'HEALTHY',
                    'message': 'No tasks in the last 24 hours',
                    'metrics': {'total_tasks': 0}
                }
                
            success_tasks = Task.query.filter(
                Task.created_at >= since,
                Task.status == 'SUCCESS'
            ).count()
            
            failed_tasks = Task.query.filter(
                Task.created_at >= since,
                Task.status == 'FAILED'
            ).count()
            
            success_rate = success_tasks / total_tasks if total_tasks > 0 else 0
            failure_rate = failed_tasks / total_tasks if total_tasks > 0 else 0
            
            alerts = []
            status = 'HEALTHY'
            
            # 检查失败率
            if failure_rate > self.thresholds['max_failed_rate']:
                alerts.append({
                    'level': AlertLevel.ERROR,
                    'message': f'High failure rate: {failure_rate:.2%}'
                })
                status = 'ERROR'
                
            # 检查成功率
            if success_rate < self.thresholds['min_success_rate']:
                alerts.append({
                    'level': AlertLevel.WARNING,
                    'message': f'Low success rate: {success_rate:.2%}'
                })
                if status == 'HEALTHY':
                    status = 'WARNING'
                    
            # 检查长时间运行的任务
            long_running_tasks = Task.query.filter(
                Task.status.in_(['QUEUED', 'RUNNING']),
                Task.started_at < datetime.utcnow() - timedelta(
                    seconds=self.thresholds['max_execution_time']
                )
            ).count()
            
            if long_running_tasks > 0:
                alerts.append({
                    'level': AlertLevel.WARNING,
                    'message': f'{long_running_tasks} tasks running too long'
                })
                if status == 'HEALTHY':
                    status = 'WARNING'
                    
            return {
                'status': status,
                'message': f'Task execution: {success_rate:.2%} success rate',
                'metrics': {
                    'total_tasks': total_tasks,
                    'success_tasks': success_tasks,
                    'failed_tasks': failed_tasks,
                    'success_rate': success_rate,
                    'failure_rate': failure_rate,
                    'long_running_tasks': long_running_tasks
                },
                'alerts': alerts
            }
            
        except Exception as e:
            return {
                'status': 'ERROR',
                'message': f'Error checking task execution health: {str(e)}',
                'alerts': [{
                    'level': AlertLevel.ERROR,
                    'message': f'Task execution health check failed: {str(e)}'
                }]
            }
            
    def _check_resource_health(self) -> Dict[str, Any]:
        """检查系统资源健康状态"""
        try:
            import psutil
            
            # 获取系统资源使用情况
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            alerts = []
            status = 'HEALTHY'
            
            # 检查CPU使用率
            if cpu_percent > 90:
                alerts.append({
                    'level': AlertLevel.ERROR,
                    'message': f'High CPU usage: {cpu_percent:.1f}%'
                })
                status = 'ERROR'
            elif cpu_percent > 80:
                alerts.append({
                    'level': AlertLevel.WARNING,
                    'message': f'High CPU usage: {cpu_percent:.1f}%'
                })
                if status == 'HEALTHY':
                    status = 'WARNING'
                    
            # 检查内存使用率
            if memory.percent > 90:
                alerts.append({
                    'level': AlertLevel.ERROR,
                    'message': f'High memory usage: {memory.percent:.1f}%'
                })
                status = 'ERROR'
            elif memory.percent > 80:
                alerts.append({
                    'level': AlertLevel.WARNING,
                    'message': f'High memory usage: {memory.percent:.1f}%'
                })
                if status == 'HEALTHY':
                    status = 'WARNING'
                    
            # 检查磁盘使用率
            if disk.percent > 95:
                alerts.append({
                    'level': AlertLevel.CRITICAL,
                    'message': f'Critical disk usage: {disk.percent:.1f}%'
                })
                status = 'CRITICAL'
            elif disk.percent > 85:
                alerts.append({
                    'level': AlertLevel.WARNING,
                    'message': f'High disk usage: {disk.percent:.1f}%'
                })
                if status == 'HEALTHY':
                    status = 'WARNING'
                    
            return {
                'status': status,
                'message': f'Resources: CPU {cpu_percent:.1f}%, Memory {memory.percent:.1f}%, Disk {disk.percent:.1f}%',
                'metrics': {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'disk_percent': disk.percent,
                    'memory_available': memory.available,
                    'disk_free': disk.free
                },
                'alerts': alerts
            }
            
        except ImportError:
            return {
                'status': 'WARNING',
                'message': 'psutil not available, cannot check system resources',
                'alerts': [{
                    'level': AlertLevel.WARNING,
                    'message': 'System resource monitoring unavailable'
                }]
            }
        except Exception as e:
            return {
                'status': 'ERROR',
                'message': f'Error checking resource health: {str(e)}',
                'alerts': [{
                    'level': AlertLevel.ERROR,
                    'message': f'Resource health check failed: {str(e)}'
                }]
            }
            
    def send_alert(self, alert: Dict[str, Any]):
        """发送告警"""
        try:
            # 记录告警历史
            alert['timestamp'] = datetime.utcnow().isoformat()
            alert['id'] = len(self.alert_history) + 1
            
            self.alert_history.append(alert)
            
            # 保持告警历史大小
            if len(self.alert_history) > self.max_alert_history:
                self.alert_history = self.alert_history[-self.max_alert_history:]
                

                
            # 记录日志
            log_level = {
                AlertLevel.INFO: logger.info,
                AlertLevel.WARNING: logger.warning,
                AlertLevel.ERROR: logger.error,
                AlertLevel.CRITICAL: logger.critical
            }.get(alert.get('level', AlertLevel.INFO), logger.info)
            
            log_level(f"Alert: {alert.get('message', 'Unknown alert')}")
            
        except Exception as e:
            logger.error(f"Error sending alert: {e}")

            
    def get_alert_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取告警历史"""
        return self.alert_history[-limit:]
        
    def clear_alert_history(self):
        """清空告警历史"""
        self.alert_history.clear()
        
    def run_health_check_and_alert(self):
        """运行健康检查并发送告警"""
        try:
            health_status = self.check_system_health()
            
            # 发送告警
            for alert in health_status.get('alerts', []):
                self.send_alert({
                    'level': alert['level'],
                    'title': 'System Health Alert',
                    'message': alert['message'],
                    'details': health_status
                })
                
            return health_status
            
        except Exception as e:
            logger.error(f"Error running health check: {e}")
            self.send_alert({
                'level': AlertLevel.ERROR,
                'title': 'Health Check Failed',
                'message': f'Health check failed: {str(e)}',
                'details': {'error': str(e)}
            })
            
# 全局监控服务实例
monitoring_service = MonitoringService()