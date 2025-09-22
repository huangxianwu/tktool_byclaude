from flask import Blueprint, jsonify, request
from app.services.monitoring_service import monitoring_service
from app.services.status_monitor import status_monitor
from app.services.error_handler import ErrorHandler, ErrorCode
from app.services.data_monitor import data_monitor_service
from app.utils.timezone_helper import now_utc, format_local_time
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('monitoring', __name__, url_prefix='/api/monitoring')

@bp.route('/health', methods=['GET'])
def get_health_status():
    """获取系统健康状态"""
    try:
        monitoring_service.load_config()
        health_status = monitoring_service.check_system_health()
        return jsonify({
            'success': True,
            'data': health_status
        })
    except Exception as e:
        logger.error(f"Error getting health status: {e}")
        error_handler = ErrorHandler()
        error_info = error_handler.handle_error(e, ErrorCode.SYSTEM_ERROR)
        return jsonify({
            'success': False,
            'error': error_info
        }), 500

@bp.route('/data-consistency/check', methods=['POST'])
def trigger_data_consistency_check():
    """手动触发数据一致性检查"""
    try:
        # 获取请求参数
        data = request.get_json() or {}
        check_type = data.get('type', 'full')  # full, quick, deep
        hours_back = data.get('hours_back', 24)
        
        # 根据检查类型执行不同的监控
        if check_type == 'quick':
            # 快速检查 - 只检查缺失的TaskOutput
            alerts = data_monitor_service.check_missing_task_outputs(hours_back=1)
            alerts_data = [alert.to_dict() for alert in alerts]
            
        elif check_type == 'deep':
            # 深度检查 - 包含趋势分析
            alerts = []
            alerts.extend(data_monitor_service.check_missing_task_outputs(hours_back=72))
            alerts.extend(data_monitor_service.check_data_integrity_trends(days_back=14))
            alerts.extend(data_monitor_service.check_database_performance())
            alerts_data = [alert.to_dict() for alert in alerts]
            
        else:
            # 完整检查
            monitoring_result = data_monitor_service.run_full_monitoring()
            return jsonify({
                'success': True,
                'data': monitoring_result
            })
        
        # 处理单独的告警列表
        result = {
            'timestamp': now_utc().isoformat(),
            'timestamp_local': format_local_time(now_utc()),
            'check_type': check_type,
            'total_alerts': len(alerts_data),
            'alerts': alerts_data,
            'status': 'healthy' if not alerts_data else 'issues_detected'
        }
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.error(f"数据一致性检查失败: {e}")
        error_handler = ErrorHandler()
        error_info = error_handler.handle_error(e, ErrorCode.SYSTEM_ERROR)
        return jsonify({
            'success': False,
            'error': error_info
        }), 500

@bp.route('/data-consistency/metrics', methods=['GET'])
def get_data_consistency_metrics():
    """获取数据一致性指标"""
    try:
        from app.models import Task, TaskOutput
        
        # 计算基本指标
        end_time = now_utc()
        start_time = end_time - timedelta(hours=24)
        
        # 统计最近24小时的任务
        recent_tasks = Task.query.filter(
            Task.completed_at >= start_time,
            Task.completed_at <= end_time
        ).all()
        
        success_tasks = [t for t in recent_tasks if t.status == 'SUCCESS']
        
        # 统计有TaskOutput的SUCCESS任务
        tasks_with_outputs = 0
        total_outputs = 0
        
        for task in success_tasks:
            output_count = TaskOutput.query.filter_by(task_id=task.task_id).count()
            if output_count > 0:
                tasks_with_outputs += 1
                total_outputs += output_count
        
        # 计算指标
        total_success_tasks = len(success_tasks)
        completion_rate = (tasks_with_outputs / total_success_tasks * 100) if total_success_tasks > 0 else 0
        avg_outputs_per_task = (total_outputs / tasks_with_outputs) if tasks_with_outputs > 0 else 0
        
        metrics = {
            'timestamp': end_time.isoformat(),
            'timestamp_local': format_local_time(end_time),
            'time_range_hours': 24,
            'task_metrics': {
                'total_tasks': len(recent_tasks),
                'success_tasks': total_success_tasks,
                'tasks_with_outputs': tasks_with_outputs,
                'completion_rate': f"{completion_rate:.1f}%"
            },
            'output_metrics': {
                'total_outputs': total_outputs,
                'avg_outputs_per_task': f"{avg_outputs_per_task:.1f}"
            },
            'health_status': {
                'status': 'healthy' if completion_rate >= 95 else 'degraded' if completion_rate >= 80 else 'unhealthy',
                'completion_rate_threshold': {
                    'healthy': '>=95%',
                    'degraded': '80-95%',
                    'unhealthy': '<80%'
                }
            }
        }
        
        return jsonify({
            'success': True,
            'data': metrics
        })
        
    except Exception as e:
        logger.error(f"获取数据一致性指标失败: {e}")
        error_handler = ErrorHandler()
        error_info = error_handler.handle_error(e, ErrorCode.SYSTEM_ERROR)
        return jsonify({
            'success': False,
            'error': error_info
        }), 500

@bp.route('/alerts', methods=['GET'])
def get_alerts():
    """获取告警历史"""
    try:
        limit = request.args.get('limit', 100, type=int)
        alerts = monitoring_service.get_alert_history(limit)
        return jsonify({
            'success': True,
            'data': alerts
        })
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        error_handler = ErrorHandler()
        error_info = error_handler.handle_error(e, ErrorCode.SYSTEM_ERROR)
        return jsonify({
            'success': False,
            'error': error_info
        }), 500

@bp.route('/alerts', methods=['DELETE'])
def clear_alerts():
    """清空告警历史"""
    try:
        monitoring_service.clear_alert_history()
        return jsonify({
            'success': True,
            'message': 'Alert history cleared successfully'
        })
    except Exception as e:
        logger.error(f"Error clearing alerts: {e}")
        error_handler = ErrorHandler()
        error_info = error_handler.handle_error(e, ErrorCode.SYSTEM_ERROR)
        return jsonify({
            'success': False,
            'error': error_info
        }), 500

@bp.route('/status', methods=['GET'])
def get_system_status():
    """获取系统状态概览"""
    try:
        status = status_monitor.get_system_status()
        return jsonify({
            'success': True,
            'data': status
        })
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        error_handler = ErrorHandler()
        error_info = error_handler.handle_error(e, ErrorCode.SYSTEM_ERROR)
        return jsonify({
            'success': False,
            'error': error_info
        }), 500

@bp.route('/tasks/stats', methods=['GET'])
def get_task_stats():
    """获取任务统计信息"""
    try:
        stats = status_monitor.get_task_statistics()
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        logger.error(f"Error getting task stats: {e}")
        error_handler = ErrorHandler()
        error_info = error_handler.handle_error(e, ErrorCode.SYSTEM_ERROR)
        return jsonify({
            'success': False,
            'error': error_info
        }), 500

@bp.route('/config/thresholds', methods=['GET'])
def get_monitoring_thresholds():
    """获取监控阈值配置"""
    try:
        return jsonify({
            'success': True,
            'data': monitoring_service.thresholds
        })
    except Exception as e:
        logger.error(f"Error getting monitoring thresholds: {e}")
        error_handler = ErrorHandler()
        error_info = error_handler.handle_error(e, ErrorCode.SYSTEM_ERROR)
        return jsonify({
            'success': False,
            'error': error_info
        }), 500

@bp.route('/config/thresholds', methods=['PUT'])
def update_monitoring_thresholds():
    """更新监控阈值配置"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
            
        # 验证和更新阈值
        valid_keys = set(monitoring_service.thresholds.keys())
        provided_keys = set(data.keys())
        
        if not provided_keys.issubset(valid_keys):
            invalid_keys = provided_keys - valid_keys
            return jsonify({
                'success': False,
                'error': f'Invalid threshold keys: {list(invalid_keys)}'
            }), 400
            
        monitoring_service.thresholds.update(data)
        
        return jsonify({
            'success': True,
            'message': 'Monitoring thresholds updated successfully',
            'data': monitoring_service.thresholds
        })
        
    except Exception as e:
        logger.error(f"Error updating monitoring thresholds: {e}")
        error_handler = ErrorHandler()
        error_info = error_handler.handle_error(e, ErrorCode.SYSTEM_ERROR)
        return jsonify({
            'success': False,
            'error': error_info
        }), 500

@bp.route('/test-alert', methods=['POST'])
def send_test_alert():
    """发送测试告警"""
    try:
        data = request.get_json() or {}
        
        test_alert = {
            'level': data.get('level', 'INFO'),
            'title': data.get('title', 'Test Alert'),
            'message': data.get('message', 'This is a test alert from the monitoring system'),
            'details': data.get('details', {'test': True})
        }
        
        monitoring_service.send_alert(test_alert)
        
        return jsonify({
            'success': True,
            'message': 'Test alert sent successfully',
            'data': test_alert
        })
        
    except Exception as e:
        logger.error(f"Error sending test alert: {e}")
        error_handler = ErrorHandler()
        error_info = error_handler.handle_error(e, ErrorCode.SYSTEM_ERROR)
        return jsonify({
            'success': False,
            'error': error_info
        }), 500