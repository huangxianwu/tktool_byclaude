#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据补偿脚本 - 修复缺失的TaskOutput记录
"""

import os
import sys
from datetime import datetime, timedelta
from collections import defaultdict

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Task, TaskOutput
from app.services.runninghub import RunningHubService
from app.utils.timezone_helper import now_utc, format_local_time

class DataCompensationService:
    """数据补偿服务"""
    
    def __init__(self):
        self.runninghub_service = RunningHubService()
        self.compensation_stats = {
            'total_missing': 0,
            'successfully_compensated': 0,
            'failed_compensation': 0,
            'already_exists': 0,
            'no_outputs_available': 0
        }
    
    def find_missing_task_outputs(self, start_date=None, end_date=None):
        """查找缺失TaskOutput记录的SUCCESS任务
        
        Args:
            start_date: 开始日期 (datetime)
            end_date: 结束日期 (datetime)
            
        Returns:
            缺失TaskOutput的任务列表
        """
        query = Task.query.filter_by(status='SUCCESS')
        
        if start_date:
            query = query.filter(Task.created_at >= start_date)
        if end_date:
            query = query.filter(Task.created_at <= end_date)
        
        success_tasks = query.all()
        missing_tasks = []
        
        for task in success_tasks:
            output_count = TaskOutput.query.filter_by(task_id=task.task_id).count()
            if output_count == 0:
                missing_tasks.append(task)
        
        return missing_tasks
    
    def compensate_single_task(self, task: Task, dry_run=False):
        """补偿单个任务的TaskOutput记录
        
        Args:
            task: 任务对象
            dry_run: 是否为试运行模式
            
        Returns:
            (success: bool, message: str, outputs_count: int)
        """
        try:
            print(f"🔄 处理任务 {task.task_id} (RunningHub ID: {task.runninghub_task_id})")
            
            # 检查是否已有TaskOutput记录
            existing_count = TaskOutput.query.filter_by(task_id=task.task_id).count()
            if existing_count > 0:
                self.compensation_stats['already_exists'] += 1
                return True, f"任务已有{existing_count}个TaskOutput记录", existing_count
            
            # 检查是否有RunningHub任务ID
            if not task.runninghub_task_id:
                self.compensation_stats['failed_compensation'] += 1
                return False, "缺少RunningHub任务ID", 0
            
            # 从RunningHub获取输出结果
            try:
                outputs = self.runninghub_service.get_outputs(task.runninghub_task_id, task.task_id)
            except Exception as e:
                self.compensation_stats['failed_compensation'] += 1
                return False, f"获取RunningHub输出失败: {str(e)}", 0
            
            if not outputs:
                self.compensation_stats['no_outputs_available'] += 1
                return False, "RunningHub中无可用输出", 0
            
            if dry_run:
                return True, f"试运行: 将创建{len(outputs)}个TaskOutput记录", len(outputs)
            
            # 创建TaskOutput记录（Remote-only模式：仅远程链接）
            created_count = 0
            skipped_count = 0
            creation_time = now_utc()
            
            for i, output in enumerate(outputs):
                try:
                    # 验证output数据
                    if not isinstance(output, dict):
                        print(f"  ⚠️ 跳过无效的output[{i}]: {output}")
                        continue
                    
                    file_url = output.get('fileUrl', '').strip()
                    node_id = output.get('nodeId', f'node_{i}').strip()
                    file_type = output.get('fileType', 'png').strip()
                    file_size = output.get('fileSize', 0)
                    
                    if not file_url:
                        print(f"  ⚠️ 跳过空fileUrl的output[{i}]")
                        continue
                    
                    if not node_id:
                        node_id = f'node_{i}'
                    
                    # 生成文件名
                    if '/' in file_url:
                        file_name = file_url.split('/')[-1]
                        if not file_name or file_name.startswith('.'):
                            file_name = f'compensated_{i}_{creation_time.strftime("%Y%m%d_%H%M%S")}.{file_type}'
                    else:
                        file_name = f'compensated_{i}_{creation_time.strftime("%Y%m%d_%H%M%S")}.{file_type}'
                    
                    # 创建新的TaskOutput记录（Remote-only模式：仅远程链接）
                    task_output = TaskOutput(
                        task_id=task.task_id,
                        node_id=node_id,
                        name=file_name,
                        file_url=file_url,
                        local_path=None,  # Remote-only模式：不保存本地路径
                        thumbnail_path=None,  # Remote-only模式：不保存缩略图路径
                        file_type=file_type,
                        file_size=file_size if isinstance(file_size, int) and file_size > 0 else 0,
                        created_at=creation_time  # 使用补偿时间
                    )
                    
                    # 使用数据库唯一约束实现幂等写入
                    try:
                        db.session.add(task_output)
                        db.session.flush()  # 立即检查约束冲突
                        created_count += 1
                        print(f"  ✅ 创建远程索引记录: {node_id} - {file_name}")
                        
                    except Exception as ie:
                        # 唯一约束冲突或其他错误，回滚当前记录
                        db.session.rollback()
                        skipped_count += 1
                        print(f"  ℹ️ 远程索引记录已存在或创建失败（幂等跳过）: {node_id} - {file_name}")
                        continue
                    
                except Exception as output_error:
                    print(f"  ⚠️ 处理单个输出记录失败[{i}]: {str(output_error)}")
                    continue
            
            # 提交数据库事务
            if created_count > 0 or skipped_count > 0:
                db.session.commit()
                self.compensation_stats['successfully_compensated'] += 1
                return True, f"远程索引库补偿完成：新建{created_count}个，跳过{skipped_count}个", created_count
            else:
                db.session.rollback()
                self.compensation_stats['failed_compensation'] += 1
                return False, "没有创建任何远程索引记录", 0
                
        except Exception as e:
            # 回滚数据库事务
            try:
                db.session.rollback()
            except:
                pass
            
            self.compensation_stats['failed_compensation'] += 1
            return False, f"补偿失败: {str(e)}", 0
    
    def compensate_batch(self, tasks, dry_run=False, batch_size=10):
        """批量补偿TaskOutput记录
        
        Args:
            tasks: 任务列表
            dry_run: 是否为试运行模式
            batch_size: 批处理大小
            
        Returns:
            补偿结果统计
        """
        total_tasks = len(tasks)
        print(f"📊 开始批量补偿，共{total_tasks}个任务")
        
        if dry_run:
            print("🔍 试运行模式 - 不会实际修改数据")
        
        # 重置统计
        self.compensation_stats = {
            'total_missing': total_tasks,
            'successfully_compensated': 0,
            'failed_compensation': 0,
            'already_exists': 0,
            'no_outputs_available': 0
        }
        
        # 分批处理
        for i in range(0, total_tasks, batch_size):
            batch = tasks[i:i + batch_size]
            print(f"\n📦 处理批次 {i//batch_size + 1}/{(total_tasks + batch_size - 1)//batch_size}")
            
            for j, task in enumerate(batch):
                try:
                    success, message, outputs_count = self.compensate_single_task(task, dry_run)
                    
                    status_icon = "✅" if success else "❌"
                    print(f"  {status_icon} 任务 {task.task_id}: {message}")
                    
                    # 每处理10个任务显示一次进度
                    if (i + j + 1) % 10 == 0:
                        progress = (i + j + 1) / total_tasks * 100
                        print(f"    📈 进度: {progress:.1f}% ({i + j + 1}/{total_tasks})")
                        
                except Exception as e:
                    print(f"  ❌ 任务 {task.task_id} 处理异常: {str(e)}")
                    self.compensation_stats['failed_compensation'] += 1
        
        return self.compensation_stats
    
    def print_compensation_report(self, stats):
        """打印补偿报告"""
        print("\n" + "=" * 80)
        print("数据补偿报告")
        print("=" * 80)
        
        print(f"📊 总体统计:")
        print(f"  待补偿任务总数: {stats['total_missing']}")
        print(f"  成功补偿任务数: {stats['successfully_compensated']}")
        print(f"  补偿失败任务数: {stats['failed_compensation']}")
        print(f"  已存在记录任务数: {stats['already_exists']}")
        print(f"  无可用输出任务数: {stats['no_outputs_available']}")
        
        if stats['total_missing'] > 0:
            success_rate = (stats['successfully_compensated'] / stats['total_missing']) * 100
            print(f"  补偿成功率: {success_rate:.1f}%")
        
        print(f"\n💡 建议:")
        if stats['failed_compensation'] > 0:
            print(f"  - 有{stats['failed_compensation']}个任务补偿失败，建议检查RunningHub连接和任务状态")
        if stats['no_outputs_available'] > 0:
            print(f"  - 有{stats['no_outputs_available']}个任务在RunningHub中无可用输出，可能需要重新执行")
        if stats['successfully_compensated'] > 0:
            print(f"  - 成功补偿了{stats['successfully_compensated']}个任务的输出记录")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='数据补偿脚本 - 修复缺失的TaskOutput记录')
    parser.add_argument('--start-date', type=str, help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--dry-run', action='store_true', help='试运行模式，不实际修改数据')
    parser.add_argument('--batch-size', type=int, default=10, help='批处理大小 (默认: 10)')
    parser.add_argument('--task-id', type=str, help='指定单个任务ID进行补偿')
    
    args = parser.parse_args()
    
    app = create_app()
    
    with app.app_context():
        service = DataCompensationService()
        
        if args.task_id:
            # 补偿单个任务
            task = Task.query.filter_by(task_id=args.task_id).first()
            if not task:
                print(f"❌ 未找到任务ID: {args.task_id}")
                return
            
            if task.status != 'SUCCESS':
                print(f"⚠️ 任务状态不是SUCCESS: {task.status}")
                return
            
            success, message, outputs_count = service.compensate_single_task(task, args.dry_run)
            status_icon = "✅" if success else "❌"
            print(f"{status_icon} 任务 {task.task_id}: {message}")
            
        else:
            # 批量补偿
            # 解析日期参数
            start_date = None
            end_date = None
            
            if args.start_date:
                try:
                    start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
                except ValueError:
                    print(f"❌ 无效的开始日期格式: {args.start_date}")
                    return
            
            if args.end_date:
                try:
                    end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
                    end_date = end_date.replace(hour=23, minute=59, second=59)
                except ValueError:
                    print(f"❌ 无效的结束日期格式: {args.end_date}")
                    return
            
            # 查找缺失TaskOutput的任务
            missing_tasks = service.find_missing_task_outputs(start_date, end_date)
            
            if not missing_tasks:
                print("✅ 没有发现缺失TaskOutput记录的SUCCESS任务")
                return
            
            print(f"🔍 发现{len(missing_tasks)}个缺失TaskOutput记录的SUCCESS任务")
            
            if args.start_date or args.end_date:
                date_range = f"{args.start_date or '开始'} 到 {args.end_date or '结束'}"
                print(f"📅 时间范围: {date_range}")
            
            # 执行批量补偿
            stats = service.compensate_batch(missing_tasks, args.dry_run, args.batch_size)
            
            # 打印报告
            service.print_compensation_report(stats)

if __name__ == '__main__':
    main()