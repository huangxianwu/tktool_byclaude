#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据监控调度器
定期执行数据一致性检查并发送告警
"""

import os
import sys
import time
import json
import logging
import schedule
from datetime import datetime
from typing import Dict, List

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.services.data_monitor import data_monitor_service, DataConsistencyAlert
from app.utils.timezone_helper import now_utc, format_local_time

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/monitoring.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class MonitoringScheduler:
    """监控调度器"""
    
    def __init__(self, app=None):
        self.app = app or create_app()
        self.alert_history = []
        self.last_monitoring_time = None
        
    def run_monitoring_check(self):
        """执行监控检查"""
        try:
            with self.app.app_context():
                logger.info("开始执行数据一致性监控检查...")
                
                # 执行完整监控
                monitoring_result = data_monitor_service.run_full_monitoring()
                
                # 记录监控时间
                self.last_monitoring_time = now_utc()
                
                # 处理告警
                if monitoring_result['total_alerts'] > 0:
                    self._handle_alerts(monitoring_result)
                else:
                    logger.info("监控检查完成 - 未发现问题")
                
                # 保存监控结果
                self._save_monitoring_result(monitoring_result)
                
                logger.info(f"监控检查完成，发现 {monitoring_result['total_alerts']} 个问题")
                
        except Exception as e:
            logger.error(f"监控检查执行失败: {e}")
            self._handle_monitoring_error(e)
    
    def _handle_alerts(self, monitoring_result: Dict):
        """处理告警"""
        alerts = monitoring_result.get('alerts', [])
        
        # 按严重程度分组处理
        critical_alerts = [a for a in alerts if a['severity'] == DataConsistencyAlert.SEVERITY_CRITICAL]
        high_alerts = [a for a in alerts if a['severity'] == DataConsistencyAlert.SEVERITY_HIGH]
        medium_alerts = [a for a in alerts if a['severity'] == DataConsistencyAlert.SEVERITY_MEDIUM]
        low_alerts = [a for a in alerts if a['severity'] == DataConsistencyAlert.SEVERITY_LOW]
        
        # 立即处理严重告警
        if critical_alerts:
            self._send_critical_alert_notification(critical_alerts)
        
        # 记录所有告警
        for alert in alerts:
            logger.warning(f"数据一致性告警 [{alert['severity'].upper()}]: {alert['message']}")
            if alert.get('task_ids'):
                logger.warning(f"  涉及任务: {', '.join(alert['task_ids'][:5])}{'...' if len(alert['task_ids']) > 5 else ''}")
        
        # 保存告警历史
        self.alert_history.extend(alerts)
        
        # 保持告警历史在合理范围内
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-500:]
    
    def _send_critical_alert_notification(self, critical_alerts: List[Dict]):
        """发送严重告警通知"""
        try:
            # 这里可以集成邮件、短信、钉钉等通知方式
            # 目前先记录到日志和文件
            
            alert_summary = {
                'timestamp': now_utc().isoformat(),
                'timestamp_local': format_local_time(now_utc()),
                'alert_count': len(critical_alerts),
                'alerts': critical_alerts
            }
            
            # 保存到紧急告警文件
            os.makedirs('logs/alerts', exist_ok=True)
            alert_file = f"logs/alerts/critical_alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(alert_file, 'w', encoding='utf-8') as f:
                json.dump(alert_summary, f, ensure_ascii=False, indent=2)
            
            logger.critical(f"严重数据一致性问题！已保存详细信息到: {alert_file}")
            
            # TODO: 集成实际的通知系统
            # self._send_email_notification(critical_alerts)
            # self._send_dingtalk_notification(critical_alerts)
            
        except Exception as e:
            logger.error(f"发送严重告警通知失败: {e}")
    
    def _save_monitoring_result(self, monitoring_result: Dict):
        """保存监控结果"""
        try:
            # 创建监控结果目录
            os.makedirs('logs/monitoring_results', exist_ok=True)
            
            # 按日期组织文件
            date_str = datetime.now().strftime('%Y%m%d')
            result_file = f"logs/monitoring_results/monitoring_{date_str}.jsonl"
            
            # 追加写入监控结果
            with open(result_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(monitoring_result, ensure_ascii=False) + '\n')
            
        except Exception as e:
            logger.error(f"保存监控结果失败: {e}")
    
    def _handle_monitoring_error(self, error: Exception):
        """处理监控错误"""
        error_info = {
            'timestamp': now_utc().isoformat(),
            'timestamp_local': format_local_time(now_utc()),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'error_details': {
                'last_successful_monitoring': self.last_monitoring_time.isoformat() if self.last_monitoring_time else None
            }
        }
        
        # 保存错误信息
        os.makedirs('logs/errors', exist_ok=True)
        error_file = f"logs/errors/monitoring_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(error_file, 'w', encoding='utf-8') as f:
            json.dump(error_info, f, ensure_ascii=False, indent=2)
        
        logger.error(f"监控系统错误，详细信息已保存到: {error_file}")
    
    def get_monitoring_status(self) -> Dict:
        """获取监控状态"""
        return {
            'last_monitoring_time': self.last_monitoring_time.isoformat() if self.last_monitoring_time else None,
            'last_monitoring_time_local': format_local_time(self.last_monitoring_time) if self.last_monitoring_time else None,
            'alert_history_count': len(self.alert_history),
            'recent_alerts': self.alert_history[-10:] if self.alert_history else [],
            'status': 'running' if self.last_monitoring_time else 'not_started'
        }
    
    def start_scheduler(self):
        """启动调度器"""
        logger.info("启动数据监控调度器...")
        
        # 配置调度任务
        # 每15分钟执行一次快速检查
        schedule.every(15).minutes.do(self._quick_monitoring_check)
        
        # 每小时执行一次完整检查
        schedule.every().hour.do(self.run_monitoring_check)
        
        # 每天凌晨2点执行深度检查
        schedule.every().day.at("02:00").do(self._deep_monitoring_check)
        
        # 立即执行一次检查
        self.run_monitoring_check()
        
        logger.info("监控调度器已启动，等待执行...")
        
        # 运行调度器
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次调度
            except KeyboardInterrupt:
                logger.info("收到停止信号，正在关闭监控调度器...")
                break
            except Exception as e:
                logger.error(f"调度器运行错误: {e}")
                time.sleep(60)  # 出错后等待1分钟再继续
    
    def _quick_monitoring_check(self):
        """快速监控检查（仅检查关键指标）"""
        try:
            with self.app.app_context():
                logger.info("执行快速监控检查...")
                
                # 只检查最近的缺失TaskOutput
                alerts = data_monitor_service.check_missing_task_outputs(1)  # 检查过去1小时
                
                if alerts:
                    self._handle_alerts({'alerts': [alert.to_dict() for alert in alerts], 'total_alerts': len(alerts)})
                
        except Exception as e:
            logger.error(f"快速监控检查失败: {e}")
    
    def _deep_monitoring_check(self):
        """深度监控检查（包含趋势分析）"""
        try:
            with self.app.app_context():
                logger.info("执行深度监控检查...")
                
                # 执行更全面的检查
                all_alerts = []
                all_alerts.extend(data_monitor_service.check_missing_task_outputs(72))  # 检查过去3天
                all_alerts.extend(data_monitor_service.check_data_integrity_trends(14))  # 检查过去2周趋势
                all_alerts.extend(data_monitor_service.check_database_performance())
                
                if all_alerts:
                    monitoring_result = {
                        'alerts': [alert.to_dict() for alert in all_alerts],
                        'total_alerts': len(all_alerts),
                        'check_type': 'deep_monitoring'
                    }
                    self._handle_alerts(monitoring_result)
                    self._save_monitoring_result(monitoring_result)
                
                logger.info(f"深度监控检查完成，发现 {len(all_alerts)} 个问题")
                
        except Exception as e:
            logger.error(f"深度监控检查失败: {e}")

def main():
    """主函数"""
    # 确保日志目录存在
    os.makedirs('logs', exist_ok=True)
    
    # 创建并启动监控调度器
    scheduler = MonitoringScheduler()
    
    try:
        scheduler.start_scheduler()
    except Exception as e:
        logger.error(f"监控调度器启动失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()