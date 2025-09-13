#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新数据库中的文件路径，从任务ID路径改为日期路径
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import TaskOutput
from datetime import datetime

def update_paths_for_task(task_id):
    """更新指定任务的文件路径"""
    app = create_app()
    with app.app_context():
        outputs = TaskOutput.query.filter_by(task_id=task_id).all()
        
        print(f"找到 {len(outputs)} 个文件记录需要更新")
        
        updated_count = 0
        for output in outputs:
            old_path = output.local_path
            old_file_url = output.file_url
            
            # 检查是否是任务ID路径格式
            if task_id in old_path:
                # 提取文件名
                filename = os.path.basename(old_path)
                
                # 生成新的日期路径
                year_month = '2025/09'  # 根据文件创建时间
                new_local_path = f"static/outputs/videos/{year_month}/{filename}"
                
                # 检查新路径的文件是否存在
                if os.path.exists(new_local_path):
                    print(f"更新文件 {output.id}:")
                    print(f"  旧路径: {old_path}")
                    print(f"  新路径: {new_local_path}")
                    print(f"  文件URL保持不变: {old_file_url}")
                    
                    # 更新数据库记录（只更新local_path，file_url保持不变）
                    output.local_path = new_local_path
                    updated_count += 1
                else:
                    print(f"⚠️  文件不存在，跳过更新: {new_local_path}")
            else:
                print(f"跳过已经是正确格式的路径: {old_path}")
        
        if updated_count > 0:
            try:
                db.session.commit()
                print(f"\n✅ 成功更新 {updated_count} 个文件记录")
            except Exception as e:
                db.session.rollback()
                print(f"❌ 更新失败: {e}")
        else:
            print("\n没有需要更新的记录")

if __name__ == '__main__':
    task_id = 'f1e0daea-84ee-422d-9cae-c0da4908c3bc'
    print(f"开始更新任务 {task_id} 的文件路径...")
    update_paths_for_task(task_id)
    print("更新完成！")