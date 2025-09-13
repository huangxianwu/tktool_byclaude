#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
历史文件迁移脚本
用于将所有已存在的任务输出文件重命名为新的自定义格式（任务描述_日期）
"""

import os
import sys
import shutil
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import TaskOutput, Task
from app.services.file_manager import FileManager

def migrate_file_names():
    """迁移历史文件名"""
    app = create_app()
    
    with app.app_context():
        print("开始迁移历史文件名...")
        
        # 获取所有没有name字段或name字段为空的TaskOutput记录
        outputs = TaskOutput.query.filter(
            (TaskOutput.name == None) | (TaskOutput.name == '')
        ).all()
        
        print(f"找到 {len(outputs)} 个需要迁移的文件")
        
        file_manager = FileManager()
        success_count = 0
        error_count = 0
        
        for i, output in enumerate(outputs, 1):
            try:
                print(f"处理第 {i}/{len(outputs)} 个文件: task_id={output.task_id}, node_id={output.node_id}")
                
                # 生成原始文件名
                original_filename = f"node_{output.node_id}_output.{output.file_type}"
                
                # 生成新的自定义文件名
                custom_filename = file_manager._generate_custom_filename(output.task_id, original_filename)
                
                # 检查本地文件是否存在
                if output.local_path and os.path.exists(output.local_path):
                    # 生成新的文件路径
                    old_path = output.local_path
                    new_path = os.path.join(os.path.dirname(old_path), custom_filename)
                    
                    # 如果新路径与旧路径不同，则重命名文件
                    if old_path != new_path:
                        # 确保目标目录存在
                        os.makedirs(os.path.dirname(new_path), exist_ok=True)
                        
                        # 重命名文件
                        shutil.move(old_path, new_path)
                        print(f"  文件重命名: {os.path.basename(old_path)} -> {os.path.basename(new_path)}")
                        
                        # 更新数据库中的local_path
                        output.local_path = new_path
                    
                    # 处理缩略图文件
                    if output.thumbnail_path and os.path.exists(output.thumbnail_path):
                        old_thumb_path = output.thumbnail_path
                        name_without_ext = os.path.splitext(custom_filename)[0]
                        new_thumb_filename = f"{name_without_ext}_thumb.jpg"
                        new_thumb_path = os.path.join(os.path.dirname(old_thumb_path), new_thumb_filename)
                        
                        if old_thumb_path != new_thumb_path:
                            shutil.move(old_thumb_path, new_thumb_path)
                            print(f"  缩略图重命名: {os.path.basename(old_thumb_path)} -> {os.path.basename(new_thumb_path)}")
                            output.thumbnail_path = new_thumb_path
                
                # 更新数据库中的name字段
                output.name = custom_filename
                
                success_count += 1
                print(f"  ✓ 成功处理: {custom_filename}")
                
            except Exception as e:
                error_count += 1
                print(f"  ✗ 处理失败: {str(e)}")
                continue
        
        # 提交数据库更改
        try:
            db.session.commit()
            print(f"\n迁移完成!")
            print(f"成功处理: {success_count} 个文件")
            print(f"处理失败: {error_count} 个文件")
        except Exception as e:
            db.session.rollback()
            print(f"\n数据库提交失败: {str(e)}")
            return False
        
        return True

def backup_database():
    """备份数据库（可选）"""
    print("建议在运行迁移脚本前备份数据库!")
    response = input("是否继续执行迁移? (y/N): ")
    return response.lower() in ['y', 'yes']

if __name__ == '__main__':
    print("=" * 50)
    print("历史文件名迁移脚本")
    print("=" * 50)
    print("此脚本将:")
    print("1. 重命名所有历史文件为新的格式（任务描述_日期）")
    print("2. 更新数据库中的文件路径和名称")
    print("3. 处理缩略图文件")
    print("\n注意: 请确保应用程序已停止运行!")
    print("=" * 50)
    
    if backup_database():
        success = migrate_file_names()
        if success:
            print("\n迁移成功完成! 可以重新启动应用程序。")
        else:
            print("\n迁移失败! 请检查错误信息并重试。")
    else:
        print("\n迁移已取消。")