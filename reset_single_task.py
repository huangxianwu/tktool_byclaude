#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重置特定任务的文件 - 删除现有文件并重新下载
"""

import os
import sys
import shutil

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Task, TaskOutput
from app.services.file_manager import FileManager
from app.services.runninghub import RunningHubService

def reset_task_files(task_id):
    """重置指定任务的文件"""
    app = create_app()
    
    with app.app_context():
        print(f"开始重置任务 {task_id} 的文件...")
        
        # 1. 获取任务信息
        task = Task.query.get(task_id)
        if not task:
            print(f"❌ 任务 {task_id} 不存在")
            return
        
        print(f"📋 任务描述: {task.task_description}")
        print(f"🔗 RunningHub ID: {task.runninghub_task_id}")
        
        # 2. 删除现有的TaskOutput记录和文件
        existing_outputs = TaskOutput.query.filter_by(task_id=task_id).all()
        deleted_files = 0
        
        for output in existing_outputs:
            # 删除本地文件
            if output.local_path and os.path.exists(output.local_path):
                try:
                    os.remove(output.local_path)
                    deleted_files += 1
                    print(f"🗑️  删除文件: {output.local_path}")
                except Exception as e:
                    print(f"⚠️  删除文件失败: {output.local_path} - {e}")
            
            # 删除缩略图
            if output.thumbnail_path and os.path.exists(output.thumbnail_path):
                try:
                    os.remove(output.thumbnail_path)
                    print(f"🗑️  删除缩略图: {output.thumbnail_path}")
                except Exception as e:
                    print(f"⚠️  删除缩略图失败: {output.thumbnail_path} - {e}")
        
        # 删除数据库记录
        TaskOutput.query.filter_by(task_id=task_id).delete()
        db.session.commit()
        print(f"🗑️  删除了 {len(existing_outputs)} 个数据库记录")
        
        # 3. 重新从RunningHub获取并下载文件
        print("\n📥 重新下载文件...")
        
        runninghub_service = RunningHubService()
        file_manager = FileManager()
        
        # 获取远程输出列表
        remote_outputs = runninghub_service.get_outputs(task.runninghub_task_id, task_id)
        
        if not remote_outputs:
            print("❌ 未找到远程输出文件")
            return
        
        print(f"📁 找到 {len(remote_outputs)} 个远程文件")
        
        # 下载并保存文件
        downloaded_files = file_manager.download_and_save_outputs(task_id, remote_outputs)
        
        print(f"\n✅ 重置完成!")
        print(f"   - 删除了 {deleted_files} 个现有文件")
        print(f"   - 删除了 {len(existing_outputs)} 个数据库记录")
        print(f"   - 重新下载了 {len(downloaded_files)} 个文件")
        
        # 4. 验证新文件
        print("\n🔍 验证新文件:")
        new_outputs = TaskOutput.query.filter_by(task_id=task_id).all()
        for output in new_outputs:
            exists = "✅" if os.path.exists(output.local_path) else "❌"
            print(f"   {exists} {output.name} -> {output.local_path}")

if __name__ == '__main__':
    # 重置任务f1e0daea-84ee-422d-9cae-c0da4908c3bc (RunningHub ID: 1966677697546108929)
    reset_task_files('f1e0daea-84ee-422d-9cae-c0da4908c3bc')
    print("\n🔄 系统恢复完成，无错误。")