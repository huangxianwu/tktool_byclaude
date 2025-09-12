from flask import Blueprint, jsonify, request
from app.services.monitoring_service import monitoring_service
from app.services.status_monitor import status_monitor
from app.services.error_handler import ErrorHandler, ErrorCode
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