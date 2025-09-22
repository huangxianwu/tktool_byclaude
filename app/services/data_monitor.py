#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据一致性监控和告警服务
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from app import db
from app.models import Task, TaskOutput
from app.utils.timezone_helper import now_utc, format_local_time

logger = logging.getLogger(__name__)

class DataConsistencyAlert:
    """数据一致性告警"""
    
    SEVERITY_LOW = 'low'
    SEVERITY_MEDIUM = 'medium'
    SEVERITY_HIGH = 'high'
    SEVERITY_CRITICAL = 'critical'
    
    def __init__(self, alert_type: str, severity: str, message: str, 
                 details: Dict = None, task_ids: List[str] = None):
        self.alert_type = alert_type
        self.severity = severity
        self.message = message
        self.details = details or {}
        self.task_ids = task_ids or []
        self.created_at = now_utc()
    
    def to_dict(self):
        return {
            'alert_type': self.alert_type,
            'severity': self.severity,
            'message': self.message,
            'details': self.details,
            'task_ids': self.task_ids,
            'created_at': self.created_at.isoformat(),
            'created_at_local': format_local_time(self.created_at)
        }

class DataMonitorService:
    """数据监控服务"""
    
    def __init__(self):
        self.alerts = []
        self.monitoring_stats = {}
    
    def check_missing_task_outputs(self, hours_back: int = 24) -> List[DataConsistencyAlert]:
        """检查缺失的TaskOutput记录
        
        Args:
            hours_back: 检查过去多少小时的数据
            
        Returns:
            告警列表
        """
        alerts = []
        
        try:
            # 计算时间范围
            end_time = now_utc()
            start_time = end_time - timedelta(hours=hours_back)
            
            # 查找指定时间范围内的SUCCESS任务
            success_tasks = Task.query.filter(
                Task.status == 'SUCCESS',
                Task.completed_at >= start_time,
                Task.completed_at <= end_time
            ).all()
            
            missing_tasks = []
            for task in success_tasks:
                output_count = TaskOutput.query.filter_by(task_id=task.task_id).count()
                if output_count == 0:
                    missing_tasks.append(task)
            
            # 生成告警
            if missing_tasks:
                severity = self._calculate_severity_by_count(len(missing_tasks), len(success_tasks))
                
                alert = DataConsistencyAlert(
                    alert_type='missing_task_outputs',
                    severity=severity,
                    message=f'发现{len(missing_tasks)}个SUCCESS任务缺失TaskOutput记录',
                    details={
                        'time_range_hours': hours_back,
                        'total_success_tasks': len(success_tasks),
                        'missing_count': len(missing_tasks),
                        'missing_rate': f"{(len(missing_tasks)/len(success_tasks)*100):.1f}%" if success_tasks else "0%"
                    },
                    task_ids=[task.task_id for task in missing_tasks[:10]]  # 只记录前10个
                )
                alerts.append(alert)
                
                logger.warning(f"Data consistency alert: {alert.message}")
            
        except Exception as e:
            error_alert = DataConsistencyAlert(
                alert_type='monitoring_error',
                severity=DataConsistencyAlert.SEVERITY_HIGH,
                message=f'TaskOutput缺失检查失败: {str(e)}',
                details={'error': str(e)}
            )
            alerts.append(error_alert)
            logger.error(f"Error checking missing task outputs: {e}")
        
        return alerts
    
    def check_task_output_creation_delay(self, minutes_threshold: int = 30) -> List[DataConsistencyAlert]:
        """检查TaskOutput创建延迟
        
        Args:
            minutes_threshold: 延迟阈值（分钟）
            
        Returns:
            告警列表
        """
        alerts = []
        
        try:
            # 查找最近完成但TaskOutput创建延迟的任务
            threshold_time = now_utc() - timedelta(minutes=minutes_threshold)
            
            # 查找最近完成的SUCCESS任务
            recent_success_tasks = Task.query.filter(
                Task.status == 'SUCCESS',
                Task.completed_at >= threshold_time
            ).all()
            
            delayed_tasks = []
            for task in recent_success_tasks:
                # 检查是否有TaskOutput记录
                task_outputs = TaskOutput.query.filter_by(task_id=task.task_id).all()
                
                if not task_outputs:
                    # 如果没有TaskOutput记录，且任务完成时间超过阈值，则认为延迟
                    if task.completed_at and task.completed_at < threshold_time:
                        delayed_tasks.append(task)
                else:
                    # 如果有TaskOutput记录，检查创建时间是否延迟
                    for output in task_outputs:
                        if (output.created_at and task.completed_at and 
                            (output.created_at - task.completed_at).total_seconds() > minutes_threshold * 60):
                            delayed_tasks.append(task)
                            break
            
            if delayed_tasks:
                severity = self._calculate_severity_by_count(len(delayed_tasks), len(recent_success_tasks))
                
                alert = DataConsistencyAlert(
                    alert_type='task_output_creation_delay',
                    severity=severity,
                    message=f'发现{len(delayed_tasks)}个任务的TaskOutput创建延迟超过{minutes_threshold}分钟',
                    details={
                        'delay_threshold_minutes': minutes_threshold,
                        'total_recent_tasks': len(recent_success_tasks),
                        'delayed_count': len(delayed_tasks)
                    },
                    task_ids=[task.task_id for task in delayed_tasks[:10]]
                )
                alerts.append(alert)
                
                logger.warning(f"Task output creation delay alert: {alert.message}")
        
        except Exception as e:
            error_alert = DataConsistencyAlert(
                alert_type='monitoring_error',
                severity=DataConsistencyAlert.SEVERITY_HIGH,
                message=f'TaskOutput创建延迟检查失败: {str(e)}',
                details={'error': str(e)}
            )
            alerts.append(error_alert)
            logger.error(f"Error checking task output creation delay: {e}")
        
        return alerts
    
    def check_data_integrity_trends(self, days_back: int = 7) -> List[DataConsistencyAlert]:
        """检查数据完整性趋势
        
        Args:
            days_back: 检查过去多少天的数据
            
        Returns:
            告警列表
        """
        alerts = []
        
        try:
            # 按天统计数据完整性
            daily_stats = {}
            
            for i in range(days_back):
                date = (now_utc() - timedelta(days=i)).date()
                
                # 查找当天的SUCCESS任务
                day_start = datetime.combine(date, datetime.min.time())
                day_end = datetime.combine(date, datetime.max.time())
                
                success_tasks = Task.query.filter(
                    Task.status == 'SUCCESS',
                    Task.completed_at >= day_start,
                    Task.completed_at <= day_end
                ).all()
                
                # 统计有TaskOutput的任务
                tasks_with_outputs = 0
                for task in success_tasks:
                    output_count = TaskOutput.query.filter_by(task_id=task.task_id).count()
                    if output_count > 0:
                        tasks_with_outputs += 1
                
                completion_rate = (tasks_with_outputs / len(success_tasks) * 100) if success_tasks else 100
                
                daily_stats[date.isoformat()] = {
                    'total_success_tasks': len(success_tasks),
                    'tasks_with_outputs': tasks_with_outputs,
                    'completion_rate': completion_rate
                }
            
            # 分析趋势
            rates = [stats['completion_rate'] for stats in daily_stats.values() if stats['total_success_tasks'] > 0]
            
            if len(rates) >= 3:
                # 检查是否有显著下降趋势
                recent_avg = sum(rates[:3]) / 3  # 最近3天平均
                overall_avg = sum(rates) / len(rates)  # 总体平均
                
                if recent_avg < overall_avg - 20:  # 最近平均比总体平均低20%以上
                    alert = DataConsistencyAlert(
                        alert_type='data_integrity_trend_decline',
                        severity=DataConsistencyAlert.SEVERITY_MEDIUM,
                        message=f'数据完整性呈下降趋势，最近3天平均完整率{recent_avg:.1f}%，低于总体平均{overall_avg:.1f}%',
                        details={
                            'days_analyzed': days_back,
                            'recent_avg_rate': f"{recent_avg:.1f}%",
                            'overall_avg_rate': f"{overall_avg:.1f}%",
                            'daily_stats': daily_stats
                        }
                    )
                    alerts.append(alert)
                    
                    logger.warning(f"Data integrity trend decline alert: {alert.message}")
        
        except Exception as e:
            error_alert = DataConsistencyAlert(
                alert_type='monitoring_error',
                severity=DataConsistencyAlert.SEVERITY_HIGH,
                message=f'数据完整性趋势检查失败: {str(e)}',
                details={'error': str(e)}
            )
            alerts.append(error_alert)
            logger.error(f"Error checking data integrity trends: {e}")
        
        return alerts
    
    def check_database_performance(self) -> List[DataConsistencyAlert]:
        """检查数据库性能指标"""
        alerts = []
        
        try:
            # 检查TaskOutput表大小和性能
            total_outputs = TaskOutput.query.count()
            total_tasks = Task.query.count()
            
            # 检查是否有异常的数据量
            if total_outputs > total_tasks * 10:  # 如果TaskOutput数量是Task的10倍以上
                alert = DataConsistencyAlert(
                    alert_type='excessive_task_outputs',
                    severity=DataConsistencyAlert.SEVERITY_MEDIUM,
                    message=f'TaskOutput记录数量异常，共{total_outputs}条记录对应{total_tasks}个任务',
                    details={
                        'total_outputs': total_outputs,
                        'total_tasks': total_tasks,
                        'ratio': f"{(total_outputs/total_tasks):.1f}" if total_tasks > 0 else "N/A"
                    }
                )
                alerts.append(alert)
        
        except Exception as e:
            error_alert = DataConsistencyAlert(
                alert_type='monitoring_error',
                severity=DataConsistencyAlert.SEVERITY_HIGH,
                message=f'数据库性能检查失败: {str(e)}',
                details={'error': str(e)}
            )
            alerts.append(error_alert)
            logger.error(f"Error checking database performance: {e}")
        
        return alerts
    
    def run_full_monitoring(self) -> Dict:
        """运行完整的监控检查
        
        Returns:
            监控结果字典
        """
        all_alerts = []
        
        # 执行各项检查
        all_alerts.extend(self.check_missing_task_outputs(24))  # 检查过去24小时
        all_alerts.extend(self.check_task_output_creation_delay(30))  # 检查30分钟延迟
        all_alerts.extend(self.check_data_integrity_trends(7))  # 检查过去7天趋势
        all_alerts.extend(self.check_database_performance())
        
        # 按严重程度分类
        alerts_by_severity = defaultdict(list)
        for alert in all_alerts:
            alerts_by_severity[alert.severity].append(alert)
        
        # 生成监控报告
        monitoring_result = {
            'timestamp': now_utc().isoformat(),
            'timestamp_local': format_local_time(now_utc()),
            'total_alerts': len(all_alerts),
            'alerts_by_severity': {
                severity: len(alerts) for severity, alerts in alerts_by_severity.items()
            },
            'alerts': [alert.to_dict() for alert in all_alerts],
            'status': 'healthy' if not all_alerts else 'issues_detected'
        }
        
        # 记录监控结果
        if all_alerts:
            logger.warning(f"Data monitoring detected {len(all_alerts)} issues")
        else:
            logger.info("Data monitoring completed - no issues detected")
        
        return monitoring_result
    
    def _calculate_severity_by_count(self, issue_count: int, total_count: int) -> str:
        """根据问题数量计算严重程度"""
        if total_count == 0:
            return DataConsistencyAlert.SEVERITY_LOW
        
        rate = issue_count / total_count
        
        if rate >= 0.5:  # 50%以上
            return DataConsistencyAlert.SEVERITY_CRITICAL
        elif rate >= 0.2:  # 20%以上
            return DataConsistencyAlert.SEVERITY_HIGH
        elif rate >= 0.05:  # 5%以上
            return DataConsistencyAlert.SEVERITY_MEDIUM
        else:
            return DataConsistencyAlert.SEVERITY_LOW

# 全局监控服务实例
data_monitor_service = DataMonitorService()