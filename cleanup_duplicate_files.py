#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理重复的文件记录，只保留最新的文件
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import TaskOutput
from datetime import datetime

def cleanup_duplicate_files(task_id):
    """清理指定任务的重复文件记录"""
    app = create_app()
    with app.app_context():
        print(f"开始清理任务 {task_id} 的重复文件...")
        
        # 获取所有该任务的输出文件，按创建时间排序
        outputs = TaskOutput.query.filter_by(task_id=task_id).order_by(TaskOutput.created_at.desc()).all()
        
        print(f"找到 {len(outputs)} 个文件记录")
        
        if len(outputs) <= 3:
            print("文件数量正常，无需清理")
            return
        
        # 保留最新的3个文件
        keep_outputs = outputs[:3]
        delete_outputs = outputs[3:]
        
        print(f"将保留最新的 {len(keep_outputs)} 个文件:")
        for output in keep_outputs:
            print(f"  - ID: {output.id}, Name: {output.name}, Path: {output.local_path}")
        
        print(f"将删除 {len(delete_outputs)} 个旧文件:")
        for output in delete_outputs:
            print(f"  - ID: {output.id}, Name: {output.name}, Path: {output.local_path}")
            
            # 删除本地文件
            if output.local_path and os.path.exists(output.local_path):
                try:
                    os.remove(output.local_path)
                    print(f"    ✅ 已删除本地文件: {output.local_path}")
                except Exception as e:
                    print(f"    ❌ 删除本地文件失败: {e}")
            
            # 删除缩略图
            if output.thumbnail_path and os.path.exists(output.thumbnail_path):
                try:
                    os.remove(output.thumbnail_path)
                    print(f"    ✅ 已删除缩略图: {output.thumbnail_path}")
                except Exception as e:
                    print(f"    ❌ 删除缩略图失败: {e}")
            
            # 删除数据库记录
            db.session.delete(output)
        
        # 提交更改
        db.session.commit()
        print(f"✅ 清理完成，已删除 {len(delete_outputs)} 个重复文件记录")
        
        # 验证结果
        remaining_outputs = TaskOutput.query.filter_by(task_id=task_id).all()
        print(f"\n验证结果: 剩余 {len(remaining_outputs)} 个文件记录")
        for output in remaining_outputs:
            file_exists = os.path.exists(output.local_path) if output.local_path else False
            print(f"  - Name: {output.name}, 文件存在: {file_exists}")

if __name__ == '__main__':
    task_id = 'f1e0daea-84ee-422d-9cae-c0da4908c3bc'
    cleanup_duplicate_files(task_id)