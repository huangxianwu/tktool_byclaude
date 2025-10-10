#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移修复脚本
解决 sqlite3.OperationalError: no such column: workflows.pinned 错误

使用方法:
    python fix_database_migration.py
    
或者使用参数:
    python fix_database_migration.py --backup-only  # 仅备份数据库
    python fix_database_migration.py --check-only   # 仅检查数据库状态
    python fix_database_migration.py --force        # 强制执行修复
"""

import os
import sys
import sqlite3
import shutil
import argparse
from datetime import datetime
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def get_database_path():
    """获取数据库文件路径"""
    # 检查多个可能的数据库位置
    possible_paths = [
        project_root / "instance" / "database.db",
        project_root / "database.db",
        project_root / "app.db",
        project_root / "instance" / "app.db"
    ]
    
    for path in possible_paths:
        if path.exists():
            return str(path)
    
    # 如果没有找到现有数据库，返回默认路径
    instance_dir = project_root / "instance"
    instance_dir.mkdir(exist_ok=True)
    return str(instance_dir / "database.db")

def backup_database(db_path):
    """备份数据库文件"""
    if not os.path.exists(db_path):
        print(f"警告: 数据库文件不存在: {db_path}")
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = project_root / "backups"
    backup_dir.mkdir(exist_ok=True)
    
    backup_path = backup_dir / f"database_backup_{timestamp}.db"
    
    try:
        shutil.copy2(db_path, backup_path)
        print(f"✓ 数据库已备份到: {backup_path}")
        return str(backup_path)
    except Exception as e:
        print(f"✗ 备份失败: {e}")
        return None

def check_database_schema(db_path):
    """检查数据库模式，确认是否缺少 pinned 字段"""
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return False, []
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查 workflows 表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='workflows'
        """)
        
        if not cursor.fetchone():
            print("✗ workflows 表不存在")
            conn.close()
            return False, []
        
        # 获取 workflows 表的列信息
        cursor.execute("PRAGMA table_info(workflows)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print(f"当前 workflows 表的列: {column_names}")
        
        # 检查是否缺少 pinned 相关字段
        missing_columns = []
        if 'pinned' not in column_names:
            missing_columns.append('pinned')
        if 'pinned_at' not in column_names:
            missing_columns.append('pinned_at')
        
        conn.close()
        
        if missing_columns:
            print(f"✗ 缺少字段: {missing_columns}")
            return False, missing_columns
        else:
            print("✓ 数据库模式正确，包含所有必需字段")
            return True, []
            
    except Exception as e:
        print(f"✗ 检查数据库模式时出错: {e}")
        return False, []

def add_missing_columns(db_path, missing_columns):
    """手动添加缺失的列"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        for column in missing_columns:
            if column == 'pinned':
                print("添加 pinned 字段...")
                cursor.execute("""
                    ALTER TABLE workflows 
                    ADD COLUMN pinned BOOLEAN NOT NULL DEFAULT 0
                """)
            elif column == 'pinned_at':
                print("添加 pinned_at 字段...")
                cursor.execute("""
                    ALTER TABLE workflows 
                    ADD COLUMN pinned_at DATETIME
                """)
        
        conn.commit()
        conn.close()
        print("✓ 成功添加缺失的字段")
        return True
        
    except Exception as e:
        print(f"✗ 添加字段时出错: {e}")
        return False

def run_flask_migrate():
    """运行 Flask-Migrate 升级"""
    try:
        # 尝试导入 Flask 应用和迁移
        from flask import Flask
        from flask_migrate import Migrate, upgrade
        from app import create_app, db
        
        print("正在运行 Flask-Migrate 升级...")
        
        app = create_app()
        migrate = Migrate(app, db)
        
        with app.app_context():
            upgrade()
        
        print("✓ Flask-Migrate 升级完成")
        return True
        
    except ImportError as e:
        print(f"✗ 无法导入 Flask 模块: {e}")
        print("请确保已安装所有依赖: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"✗ Flask-Migrate 升级失败: {e}")
        return False

def verify_fix(db_path):
    """验证修复是否成功"""
    print("\n验证修复结果...")
    is_valid, missing = check_database_schema(db_path)
    
    if is_valid:
        print("✓ 数据库修复成功！")
        
        # 测试查询
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM workflows WHERE pinned = 0")
            count = cursor.fetchone()[0]
            print(f"✓ 测试查询成功，找到 {count} 个未置顶的工作流")
            conn.close()
            return True
        except Exception as e:
            print(f"✗ 测试查询失败: {e}")
            return False
    else:
        print(f"✗ 修复失败，仍然缺少字段: {missing}")
        return False

def main():
    parser = argparse.ArgumentParser(description='数据库迁移修复脚本')
    parser.add_argument('--backup-only', action='store_true', help='仅备份数据库')
    parser.add_argument('--check-only', action='store_true', help='仅检查数据库状态')
    parser.add_argument('--force', action='store_true', help='强制执行修复')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("数据库迁移修复脚本")
    print("=" * 60)
    
    # 获取数据库路径
    db_path = get_database_path()
    print(f"数据库路径: {db_path}")
    
    # 检查数据库状态
    is_valid, missing_columns = check_database_schema(db_path)
    
    if args.check_only:
        print("\n仅检查模式，不执行修复")
        return 0 if is_valid else 1
    
    if is_valid and not args.force:
        print("\n数据库模式正确，无需修复")
        return 0
    
    # 备份数据库
    if os.path.exists(db_path):
        backup_path = backup_database(db_path)
        if not backup_path and not args.force:
            print("备份失败，中止操作")
            return 1
    
    if args.backup_only:
        print("\n仅备份模式，修复完成")
        return 0
    
    # 执行修复
    print("\n开始修复数据库...")
    
    # 方法1: 尝试 Flask-Migrate
    if run_flask_migrate():
        if verify_fix(db_path):
            return 0
    
    # 方法2: 手动添加字段
    if missing_columns:
        print("\nFlask-Migrate 失败，尝试手动添加字段...")
        if add_missing_columns(db_path, missing_columns):
            if verify_fix(db_path):
                return 0
    
    print("\n✗ 所有修复方法都失败了")
    print("请手动执行以下 SQL 命令:")
    print("ALTER TABLE workflows ADD COLUMN pinned BOOLEAN NOT NULL DEFAULT 0;")
    print("ALTER TABLE workflows ADD COLUMN pinned_at DATETIME;")
    
    return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n操作被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 发生未预期的错误: {e}")
        sys.exit(1)