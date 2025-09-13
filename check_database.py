#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查数据库中TaskOutput表的数据
"""

import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Task, TaskOutput

def check_database():
    """检查数据库中的数据"""
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("数据库检查报告")
        print("=" * 60)
        
        # 1. 检查Task表中的任务
        print("\n📋 Task表中的任务:")
        tasks = Task.query.all()
        print(f"总任务数: {len(tasks)}")
        
        for task in tasks:
            print(f"  - 任务ID: {task.task_id}")
            print(f"    RunningHub ID: {task.runninghub_task_id}")
            print(f"    描述: {task.task_description}")
            print(f"    状态: {task.status}")
            print()
        
        # 2. 检查TaskOutput表中的输出文件
        print("\n📁 TaskOutput表中的输出文件:")
        outputs = TaskOutput.query.all()
        print(f"总输出文件数: {len(outputs)}")
        
        for output in outputs:
            print(f"  - ID: {output.id}")
            print(f"    任务ID: {output.task_id}")
            print(f"    节点ID: {output.node_id}")
            print(f"    文件名(name): '{output.name}'")
            print(f"    文件类型: {output.file_type}")
            print(f"    本地路径: {output.local_path}")
            print(f"    文件URL: {output.file_url}")
            print(f"    创建时间: {output.created_at}")
            print()
        
        # 3. 特别检查任务1966677697546108929的数据
        print("\n🔍 特别检查任务1966677697546108929:")
        target_task = Task.query.filter_by(runninghub_task_id="1966677697546108929").first()
        if target_task:
            print(f"找到任务: {target_task.task_id} - {target_task.task_description}")
            
            target_outputs = TaskOutput.query.filter_by(task_id=target_task.task_id).all()
            print(f"该任务的输出文件数: {len(target_outputs)}")
            
            for i, output in enumerate(target_outputs, 1):
                print(f"  文件{i}:")
                print(f"    name字段: '{output.name}'")
                print(f"    local_path: {output.local_path}")
                print(f"    文件是否存在: {os.path.exists(output.local_path) if output.local_path else 'N/A'}")
                
                # 检查文件名是否符合新规则
                if output.name and "_20250913" in output.name:
                    print(f"    ✅ 文件名符合新规则")
                else:
                    print(f"    ❌ 文件名不符合新规则")
                print()
        else:
            print("❌ 未找到该任务")
        
        print("=" * 60)
        print("检查完成")
        print("=" * 60)

if __name__ == '__main__':
    check_database()