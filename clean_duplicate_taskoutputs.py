#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理 TaskOutput 表中的重复记录
为添加唯一约束 (task_id + node_id + file_url) 做准备
"""

import os
import sys
from collections import defaultdict

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.TaskOutput import TaskOutput

def clean_duplicate_taskoutputs():
    """清理重复的 TaskOutput 记录"""
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("清理 TaskOutput 重复记录")
        print("=" * 60)
        
        # 1. 查找所有记录
        all_outputs = TaskOutput.query.all()
        print(f"总记录数: {len(all_outputs)}")
        
        # 2. 按 (task_id, node_id, file_url) 分组
        groups = defaultdict(list)
        for output in all_outputs:
            key = (output.task_id, output.node_id, output.file_url)
            groups[key].append(output)
        
        # 3. 找出重复的组
        duplicate_groups = {k: v for k, v in groups.items() if len(v) > 1}
        print(f"发现 {len(duplicate_groups)} 个重复组，涉及 {sum(len(v) for v in duplicate_groups.values())} 条记录")
        
        if not duplicate_groups:
            print("没有发现重复记录，可以直接应用唯一约束。")
            return True
        
        # 4. 显示重复记录详情
        print("\n重复记录详情:")
        print("-" * 60)
        for i, (key, records) in enumerate(duplicate_groups.items(), 1):
            task_id, node_id, file_url = key
            print(f"\n{i}. 重复组: task_id={task_id}, node_id={node_id}")
            print(f"   file_url: {file_url[:80]}{'...' if len(file_url) > 80 else ''}")
            print(f"   重复记录数: {len(records)}")
            
            for j, record in enumerate(records):
                print(f"   [{j+1}] ID={record.id}, name='{record.name}', created_at={record.created_at}")
        
        # 5. 询问用户是否继续清理
        print(f"\n将保留每组中最早创建的记录，删除其余 {sum(len(v)-1 for v in duplicate_groups.values())} 条重复记录。")
        response = input("是否继续清理? (y/N): ")
        
        if response.lower() not in ['y', 'yes']:
            print("清理已取消。")
            return False
        
        # 6. 执行清理
        deleted_count = 0
        try:
            for key, records in duplicate_groups.items():
                # 按创建时间排序，保留最早的记录
                records.sort(key=lambda x: x.created_at or x.id)
                keep_record = records[0]
                delete_records = records[1:]
                
                print(f"\n处理组 {key[0][:8]}...{key[1]}")
                print(f"  保留: ID={keep_record.id}, created_at={keep_record.created_at}")
                
                for record in delete_records:
                    print(f"  删除: ID={record.id}, created_at={record.created_at}")
                    db.session.delete(record)
                    deleted_count += 1
            
            # 提交更改
            db.session.commit()
            print(f"\n✅ 清理完成！删除了 {deleted_count} 条重复记录。")
            
            # 验证清理结果
            remaining_outputs = TaskOutput.query.all()
            remaining_groups = defaultdict(list)
            for output in remaining_outputs:
                key = (output.task_id, output.node_id, output.file_url)
                remaining_groups[key].append(output)
            
            remaining_duplicates = {k: v for k, v in remaining_groups.items() if len(v) > 1}
            if remaining_duplicates:
                print(f"⚠️ 警告：仍有 {len(remaining_duplicates)} 个重复组未清理完成。")
                return False
            else:
                print("✅ 验证通过：所有重复记录已清理完成。")
                return True
                
        except Exception as e:
            db.session.rollback()
            print(f"❌ 清理失败: {str(e)}")
            return False

if __name__ == '__main__':
    print("此脚本将清理 TaskOutput 表中的重复记录")
    print("重复标准: 相同的 (task_id, node_id, file_url) 组合")
    print("清理策略: 保留每组中最早创建的记录")
    print("\n注意: 请确保应用程序已停止运行!")
    print("=" * 60)
    
    success = clean_duplicate_taskoutputs()
    if success:
        print("\n现在可以安全地应用唯一约束了。")
        print("请运行: flask db upgrade")
    else:
        print("\n清理未完成，请检查错误信息并重试。")