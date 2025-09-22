#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据完整性检查脚本 - 分析9月15日前后的数据差异
"""

import os
import sys
from datetime import datetime, timedelta
from collections import defaultdict

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Task, TaskOutput

def analyze_data_integrity():
    """分析数据完整性，重点关注9月15日前后的差异"""
    app = create_app()
    
    with app.app_context():
        print("=" * 80)
        print("数据完整性分析报告")
        print("=" * 80)
        
        # 定义关键时间点
        sep_15_2024 = datetime(2024, 9, 15)
        sep_10_2024 = datetime(2024, 9, 10)
        sep_20_2024 = datetime(2024, 9, 20)
        
        # 1. 分析Task表中的任务分布
        print("\n📊 任务时间分布分析:")
        print("-" * 50)
        
        # 按日期统计任务数量
        all_tasks = Task.query.all()
        task_by_date = defaultdict(int)
        success_tasks_by_date = defaultdict(int)
        tasks_with_outputs_by_date = defaultdict(int)
        
        for task in all_tasks:
            if task.created_at:
                date_key = task.created_at.date()
                task_by_date[date_key] += 1
                
                if task.status == 'SUCCESS':
                    success_tasks_by_date[date_key] += 1
                    
                    # 检查是否有对应的TaskOutput记录
                    output_count = TaskOutput.query.filter_by(task_id=task.task_id).count()
                    if output_count > 0:
                        tasks_with_outputs_by_date[date_key] += 1
        
        # 显示9月10日到20日的统计
        print(f"{'日期':<12} {'总任务':<8} {'成功任务':<8} {'有输出任务':<10} {'输出完整率':<10}")
        print("-" * 60)
        
        for i in range(11):  # 9月10日到20日
            date = sep_10_2024.date() + timedelta(days=i)
            total = task_by_date.get(date, 0)
            success = success_tasks_by_date.get(date, 0)
            with_outputs = tasks_with_outputs_by_date.get(date, 0)
            
            if success > 0:
                completion_rate = f"{(with_outputs/success)*100:.1f}%"
            else:
                completion_rate = "N/A"
            
            marker = " ⚠️" if date >= sep_15_2024.date() and success > with_outputs else ""
            print(f"{date:<12} {total:<8} {success:<8} {with_outputs:<10} {completion_rate:<10}{marker}")
        
        # 2. 分析缺失TaskOutput的SUCCESS任务
        print("\n🔍 缺失TaskOutput记录的SUCCESS任务:")
        print("-" * 50)
        
        success_tasks = Task.query.filter_by(status='SUCCESS').all()
        missing_outputs = []
        
        for task in success_tasks:
            output_count = TaskOutput.query.filter_by(task_id=task.task_id).count()
            if output_count == 0:
                missing_outputs.append(task)
        
        print(f"总SUCCESS任务数: {len(success_tasks)}")
        print(f"缺失TaskOutput的任务数: {len(missing_outputs)}")
        
        # 按日期分组显示缺失的任务
        missing_by_date = defaultdict(list)
        for task in missing_outputs:
            if task.created_at:
                date_key = task.created_at.date()
                missing_by_date[date_key].append(task)
        
        print("\n缺失TaskOutput的任务详情:")
        for date in sorted(missing_by_date.keys()):
            tasks = missing_by_date[date]
            print(f"\n📅 {date} ({len(tasks)}个任务):")
            for task in tasks[:5]:  # 只显示前5个
                print(f"  - 任务ID: {task.task_id}")
                print(f"    RunningHub ID: {task.runninghub_task_id}")
                print(f"    描述: {task.task_description or 'N/A'}")
                print(f"    创建时间: {task.created_at}")
                print(f"    完成时间: {task.completed_at}")
            if len(tasks) > 5:
                print(f"  ... 还有 {len(tasks) - 5} 个任务")
        
        # 3. 分析9月15日前后的差异
        print(f"\n📈 9月15日前后对比分析:")
        print("-" * 50)
        
        before_sep15_tasks = Task.query.filter(
            Task.created_at < sep_15_2024,
            Task.status == 'SUCCESS'
        ).all()
        
        after_sep15_tasks = Task.query.filter(
            Task.created_at >= sep_15_2024,
            Task.status == 'SUCCESS'
        ).all()
        
        before_with_outputs = 0
        after_with_outputs = 0
        
        for task in before_sep15_tasks:
            if TaskOutput.query.filter_by(task_id=task.task_id).count() > 0:
                before_with_outputs += 1
        
        for task in after_sep15_tasks:
            if TaskOutput.query.filter_by(task_id=task.task_id).count() > 0:
                after_with_outputs += 1
        
        print(f"9月15日前:")
        print(f"  SUCCESS任务数: {len(before_sep15_tasks)}")
        print(f"  有TaskOutput的任务数: {before_with_outputs}")
        print(f"  完整率: {(before_with_outputs/len(before_sep15_tasks)*100) if before_sep15_tasks else 0:.1f}%")
        
        print(f"\n9月15日后:")
        print(f"  SUCCESS任务数: {len(after_sep15_tasks)}")
        print(f"  有TaskOutput的任务数: {after_with_outputs}")
        print(f"  完整率: {(after_with_outputs/len(after_sep15_tasks)*100) if after_sep15_tasks else 0:.1f}%")
        
        # 4. 检查TaskOutput表的时间分布
        print(f"\n📁 TaskOutput记录时间分布:")
        print("-" * 50)
        
        all_outputs = TaskOutput.query.all()
        outputs_by_date = defaultdict(int)
        
        for output in all_outputs:
            if output.created_at:
                date_key = output.created_at.date()
                outputs_by_date[date_key] += 1
        
        print(f"总TaskOutput记录数: {len(all_outputs)}")
        print("\n按日期分布:")
        for date in sorted(outputs_by_date.keys()):
            count = outputs_by_date[date]
            marker = " ⚠️" if date >= sep_15_2024.date() and count == 0 else ""
            print(f"  {date}: {count}个记录{marker}")
        
        # 5. 生成修复建议
        print(f"\n💡 修复建议:")
        print("-" * 50)
        
        if missing_outputs:
            print(f"1. 发现 {len(missing_outputs)} 个SUCCESS任务缺失TaskOutput记录")
            print("   建议: 运行数据补偿脚本修复这些记录")
            
            # 统计9月15日后的缺失数量
            after_sep15_missing = [t for t in missing_outputs if t.created_at and t.created_at >= sep_15_2024]
            if after_sep15_missing:
                print(f"   其中9月15日后缺失: {len(after_sep15_missing)} 个")
        
        if len(after_sep15_tasks) > 0 and after_with_outputs < len(after_sep15_tasks):
            print("2. 9月15日后的TaskOutput完整率较低")
            print("   建议: 检查TaskQueueManager的异常处理逻辑")
        
        print("3. 建议实施预防措施:")
        print("   - 增强TaskOutput创建的异常处理")
        print("   - 添加数据一致性监控")
        print("   - 实现失败重试机制")
        
        return {
            'total_tasks': len(all_tasks),
            'success_tasks': len(success_tasks),
            'missing_outputs': len(missing_outputs),
            'before_sep15_success': len(before_sep15_tasks),
            'before_sep15_with_outputs': before_with_outputs,
            'after_sep15_success': len(after_sep15_tasks),
            'after_sep15_with_outputs': after_with_outputs,
            'missing_tasks': missing_outputs
        }

if __name__ == '__main__':
    print("开始数据完整性检查...")
    result = analyze_data_integrity()
    print(f"\n✅ 检查完成!")
    print(f"发现 {result['missing_outputs']} 个需要修复的任务记录")