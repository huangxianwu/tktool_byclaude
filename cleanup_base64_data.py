#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
历史数据清理脚本 - 清理数据库中的base64数据
"""

import os
import sys
import re
import base64
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import TaskData, Task


class Base64DataCleaner:
    """Base64数据清理器"""
    
    def __init__(self):
        self.app = create_app()
        self.cleaned_count = 0
        self.error_count = 0
        self.total_count = 0
        
    def is_base64_data(self, value):
        """检查字符串是否为base64数据"""
        if not isinstance(value, str) or len(value) < 100:
            return False
            
        # 检查是否为data URL格式
        if value.startswith('data:'):
            return True
            
        # 检查是否为纯base64数据
        try:
            # base64数据通常很长且只包含特定字符
            if len(value) > 500:
                # 检查字符组成
                base64_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=')
                if all(c in base64_chars for c in value):
                    # 尝试解码验证
                    if value.startswith('data:'):
                        _, encoded = value.split(',', 1)
                        base64.b64decode(encoded)
                    else:
                        base64.b64decode(value)
                    return True
        except Exception:
            pass
            
        return False
    
    def analyze_data(self):
        """分析数据库中的base64数据"""
        print("🔍 分析数据库中的TaskData记录...")
        print("=" * 60)
        
        with self.app.app_context():
            # 获取所有TaskData记录
            all_task_data = TaskData.query.all()
            print(f"📊 总TaskData记录数: {len(all_task_data)}")
            
            base64_records = []
            
            for task_data in all_task_data:
                if self.is_base64_data(task_data.field_value):
                    base64_records.append(task_data)
                    
            print(f"🔍 发现包含base64数据的记录: {len(base64_records)}")
            
            if base64_records:
                print("\n📋 详细信息:")
                for i, record in enumerate(base64_records[:10], 1):  # 只显示前10条
                    task = Task.query.filter_by(task_id=record.task_id).first()
                    task_desc = task.task_description if task else "未知任务"
                    
                    print(f"  {i}. 任务ID: {record.task_id}")
                    print(f"     任务描述: {task_desc}")
                    print(f"     节点ID: {record.node_id}")
                    print(f"     字段名: {record.field_name}")
                    print(f"     数据长度: {len(record.field_value)} 字符")
                    print(f"     数据预览: {record.field_value[:50]}...")
                    print()
                    
                if len(base64_records) > 10:
                    print(f"  ... 还有 {len(base64_records) - 10} 条记录")
                    
            return base64_records
    
    def clean_base64_data(self, dry_run=True):
        """清理base64数据"""
        print(f"🧹 开始清理base64数据 ({'预览模式' if dry_run else '执行模式'})...")
        print("=" * 60)
        
        with self.app.app_context():
            base64_records = []
            all_task_data = TaskData.query.all()
            
            # 找出所有包含base64数据的记录
            for task_data in all_task_data:
                if self.is_base64_data(task_data.field_value):
                    base64_records.append(task_data)
                    
            self.total_count = len(base64_records)
            
            if not base64_records:
                print("✅ 没有发现需要清理的base64数据")
                return
                
            print(f"📊 找到 {len(base64_records)} 条包含base64数据的记录")
            
            if dry_run:
                print("\n🔍 预览模式 - 将要执行的操作:")
                for i, record in enumerate(base64_records, 1):
                    task = Task.query.filter_by(task_id=record.task_id).first()
                    task_desc = task.task_description if task else "未知任务"
                    
                    print(f"  {i}. 任务: {task_desc}")
                    print(f"     记录ID: {record.id}")
                    print(f"     节点ID: {record.node_id}")
                    print(f"     字段名: {record.field_name}")
                    print(f"     操作: 将删除包含base64数据的记录")
                    print()
                    
                print(f"\n⚠️  预览完成，共 {len(base64_records)} 条记录将被删除")
                print("💡 使用 --execute 参数执行实际清理")
                return
                
            # 执行清理
            print(f"\n🗑️  开始删除 {len(base64_records)} 条记录...")
            
            for i, record in enumerate(base64_records, 1):
                try:
                    task = Task.query.filter_by(task_id=record.task_id).first()
                    task_desc = task.task_description if task else "未知任务"
                    
                    print(f"  [{i}/{len(base64_records)}] 删除记录: {task_desc} - 节点{record.node_id}")
                    
                    db.session.delete(record)
                    self.cleaned_count += 1
                    
                except Exception as e:
                    print(f"  ❌ 删除失败: {e}")
                    self.error_count += 1
                    
            # 提交更改
            try:
                db.session.commit()
                print(f"\n✅ 清理完成!")
                print(f"   成功删除: {self.cleaned_count} 条记录")
                print(f"   删除失败: {self.error_count} 条记录")
                
            except Exception as e:
                db.session.rollback()
                print(f"\n❌ 数据库提交失败: {e}")
                
    def verify_cleanup(self):
        """验证清理结果"""
        print("\n🔍 验证清理结果...")
        print("=" * 60)
        
        with self.app.app_context():
            remaining_base64 = []
            all_task_data = TaskData.query.all()
            
            for task_data in all_task_data:
                if self.is_base64_data(task_data.field_value):
                    remaining_base64.append(task_data)
                    
            if remaining_base64:
                print(f"⚠️  仍有 {len(remaining_base64)} 条记录包含base64数据")
                for record in remaining_base64[:5]:  # 显示前5条
                    print(f"   - 记录ID: {record.id}, 任务ID: {record.task_id}")
            else:
                print("✅ 验证通过，没有发现残留的base64数据")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='清理数据库中的base64数据')
    parser.add_argument('--analyze', action='store_true', help='分析数据库中的base64数据')
    parser.add_argument('--clean', action='store_true', help='清理base64数据（预览模式）')
    parser.add_argument('--execute', action='store_true', help='执行实际清理')
    parser.add_argument('--verify', action='store_true', help='验证清理结果')
    
    args = parser.parse_args()
    
    cleaner = Base64DataCleaner()
    
    try:
        if args.analyze:
            cleaner.analyze_data()
        elif args.clean:
            cleaner.clean_base64_data(dry_run=not args.execute)
        elif args.verify:
            cleaner.verify_cleanup()
        else:
            print("📋 Base64数据清理工具")
            print("=" * 60)
            print("使用方法:")
            print("  python cleanup_base64_data.py --analyze     # 分析数据")
            print("  python cleanup_base64_data.py --clean       # 预览清理")
            print("  python cleanup_base64_data.py --clean --execute  # 执行清理")
            print("  python cleanup_base64_data.py --verify      # 验证结果")
            print()
            
            # 默认执行分析
            cleaner.analyze_data()
            
    except KeyboardInterrupt:
        print("\n⏹️ 操作被用户中断")
    except Exception as e:
        print(f"\n❌ 执行出错: {e}")


if __name__ == '__main__':
    main()