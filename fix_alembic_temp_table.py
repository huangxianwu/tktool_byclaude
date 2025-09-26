#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复 Alembic 临时表问题
清理遗留的临时表，重新应用迁移
"""

import os
import sys
import sqlite3

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from config import Config

def fix_alembic_temp_table():
    """修复 Alembic 临时表问题"""
    print("=" * 60)
    print("修复 Alembic 临时表问题")
    print("=" * 60)
    
    # 获取数据库文件路径
    config = Config()
    db_path = config.SQLALCHEMY_DATABASE_URI.replace('sqlite:///', '')
    
    print(f"数据库路径: {db_path}")
    
    if not os.path.exists(db_path):
        print("数据库文件不存在！")
        return False
    
    try:
        # 直接连接 SQLite 数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 查看所有表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"当前数据库中的表: {[table[0] for table in tables]}")
        
        # 查找并删除临时表
        temp_tables = [table[0] for table in tables if table[0].startswith('_alembic_tmp_')]
        
        if temp_tables:
            print(f"发现临时表: {temp_tables}")
            for temp_table in temp_tables:
                print(f"删除临时表: {temp_table}")
                cursor.execute(f"DROP TABLE IF EXISTS {temp_table};")
            
            conn.commit()
            print("✅ 临时表清理完成")
        else:
            print("没有发现临时表")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ 修复失败: {str(e)}")
        return False

def reset_migration_state():
    """重置迁移状态"""
    print("\n" + "=" * 60)
    print("重置迁移状态")
    print("=" * 60)
    
    app = create_app()
    
    with app.app_context():
        try:
            # 查看当前迁移状态
            result = db.engine.execute("SELECT version_num FROM alembic_version;")
            current_version = result.fetchone()
            if current_version:
                print(f"当前迁移版本: {current_version[0]}")
            else:
                print("没有找到迁移版本信息")
            
            return True
            
        except Exception as e:
            print(f"查看迁移状态失败: {str(e)}")
            return False

if __name__ == '__main__':
    print("此脚本将修复 Alembic 临时表问题")
    print("1. 清理遗留的临时表")
    print("2. 重置迁移状态")
    print("\n注意: 请确保应用程序已停止运行!")
    print("=" * 60)
    
    # 修复临时表问题
    if fix_alembic_temp_table():
        print("\n✅ 临时表问题已修复")
        
        # 重置迁移状态
        if reset_migration_state():
            print("\n现在可以重新运行迁移:")
            print("flask db upgrade")
        else:
            print("\n迁移状态检查失败，请手动检查")
    else:
        print("\n❌ 修复失败，请检查错误信息")