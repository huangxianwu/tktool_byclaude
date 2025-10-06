#!/usr/bin/env python3
"""
Windows环境数据库初始化脚本
用于在Windows环境中初始化SQLite数据库
"""

import os
import sys
import shutil
import sqlite3
from pathlib import Path
from flask import Flask
from flask_migrate import Migrate, init, migrate, upgrade

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def create_app():
    """创建Flask应用实例"""
    app = Flask(__name__)
    
    # 导入配置
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import Config
    app.config.from_object(Config)
    
    # 初始化数据库
    from app import db
    db.init_app(app)
    
    return app, db

def ensure_instance_directory():
    """确保instance目录存在"""
    instance_dir = Path("instance")
    if not instance_dir.exists():
        instance_dir.mkdir(parents=True, exist_ok=True)
        print(f"✓ 创建instance目录: {instance_dir.absolute()}")
    else:
        print(f"✓ instance目录已存在: {instance_dir.absolute()}")
    return instance_dir

def check_database_exists():
    """检查数据库文件是否存在"""
    db_path = Path("instance/app.db")
    if db_path.exists():
        size_mb = db_path.stat().st_size / (1024 * 1024)
        print(f"✓ 数据库文件已存在: {db_path.absolute()} ({size_mb:.2f} MB)")
        return True
    else:
        print(f"✗ 数据库文件不存在: {db_path.absolute()}")
        return False

def test_database_connection():
    """测试数据库连接"""
    try:
        db_path = Path("instance/app.db")
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if tables:
            print(f"✓ 数据库连接成功，发现 {len(tables)} 个表:")
            for table in tables[:5]:  # 只显示前5个表
                cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
                count = cursor.fetchone()[0]
                print(f"  - {table[0]}: {count} 条记录")
            if len(tables) > 5:
                print(f"  ... 还有 {len(tables) - 5} 个表")
        else:
            print("✗ 数据库为空，没有找到任何表")
            
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ 数据库连接失败: {e}")
        return False

def initialize_empty_database():
    """初始化空数据库"""
    try:
        print("\n开始初始化空数据库...")
        
        app, db = create_app()
        
        with app.app_context():
            # 检查是否已经初始化过migrations
            migrations_dir = Path("migrations")
            if not migrations_dir.exists():
                print("初始化数据库迁移...")
                migrate_obj = Migrate(app, db)
                init()
                print("✓ 数据库迁移初始化完成")
            
            # 创建所有表
            db.create_all()
            print("✓ 数据库表创建完成")
            
            # 运行迁移
            try:
                upgrade()
                print("✓ 数据库迁移完成")
            except Exception as e:
                print(f"⚠ 迁移警告: {e}")
                
        return True
        
    except Exception as e:
        print(f"✗ 数据库初始化失败: {e}")
        return False

def validate_database_integrity():
    """验证数据库完整性"""
    try:
        db_path = Path("instance/app.db")
        if not db_path.exists():
            return False, "数据库文件不存在"
            
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 检查数据库是否损坏
        cursor.execute("PRAGMA integrity_check;")
        result = cursor.fetchone()
        if result[0] != "ok":
            conn.close()
            return False, f"数据库完整性检查失败: {result[0]}"
        
        # 检查必要的表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [table[0] for table in cursor.fetchall()]
        
        required_tables = ['task', 'workflow', 'task_output']  # 核心表
        missing_tables = [table for table in required_tables if table not in tables]
        
        conn.close()
        
        if missing_tables:
            return False, f"缺少必要的表: {', '.join(missing_tables)}"
        
        return True, f"数据库完整性验证通过，包含 {len(tables)} 个表"
        
    except Exception as e:
        return False, f"数据库验证失败: {e}"

def backup_existing_database():
    """备份现有数据库"""
    try:
        db_path = Path("instance/app.db")
        if db_path.exists():
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = Path(f"instance/app_backup_{timestamp}.db")
            shutil.copy2(db_path, backup_path)
            print(f"✓ 数据库已备份到: {backup_path.absolute()}")
            return backup_path
    except Exception as e:
        print(f"⚠ 数据库备份失败: {e}")
    return None

def run_migrations():
    """运行数据库迁移"""
    try:
        print("\n开始运行数据库迁移...")
        app, db = create_app()
        
        with app.app_context():
            from flask_migrate import Migrate, upgrade
            migrate_obj = Migrate(app, db)
            upgrade()
            print("✓ 数据库迁移完成")
            
    except Exception as e:
        print(f"✗ 数据库迁移失败: {e}")
        return False
    return True

def main():
    """主函数"""
    print("=" * 60)
    print("Windows环境数据库初始化脚本")
    print("=" * 60)
    
    # 检查当前目录
    current_dir = Path.cwd()
    print(f"当前工作目录: {current_dir}")
    
    # 检查是否在正确的项目目录
    if not Path("config.py").exists():
        print("✗ 错误: 请在项目根目录运行此脚本")
        sys.exit(1)
    
    try:
        # 1. 确保instance目录存在
        ensure_instance_directory()
        
        # 2. 检查数据库是否存在
        db_exists = check_database_exists()
        
        if db_exists:
            print("\n验证数据库完整性...")
            is_valid, message = validate_database_integrity()
            print(f"验证结果: {message}")
            
            if is_valid:
                print("\n测试数据库连接...")
                if test_database_connection():
                    print("\n✓ 数据库已就绪，无需初始化")
                    
                    # 询问是否需要运行迁移
                    print("\n" + "=" * 50)
                    print("数据库迁移选项")
                    print("=" * 50)
                    print("数据库迁移可以更新表结构以支持新功能")
                    choice = input("是否需要运行数据库迁移? (y/N): ").lower()
                    
                    if choice in ['y', 'yes']:
                        # 先备份数据库
                        backup_existing_database()
                        run_migrations()
                    else:
                        print("跳过数据库迁移")
                else:
                    print("\n数据库文件存在但连接失败")
                    choice = input("是否备份现有数据库并重新初始化? (y/N): ").lower()
                    if choice in ['y', 'yes']:
                        backup_existing_database()
                        initialize_empty_database()
                    else:
                        print("保持现有数据库状态")
            else:
                print(f"\n⚠ 数据库验证失败: {message}")
                print("建议重新初始化数据库")
                choice = input("是否备份现有数据库并重新初始化? (y/N): ").lower()
                if choice in ['y', 'yes']:
                    backup_existing_database()
                    initialize_empty_database()
                else:
                    print("保持现有数据库状态")
        else:
            print("\n数据库文件不存在")
            print("请确保已将 app.db 文件复制到 instance/ 目录")
            print(f"目标路径: {Path('instance/app.db').absolute()}")
            
            choice = input("\n选择操作:\n1. 创建新的空数据库\n2. 等待手动复制数据库文件\n请输入选择 (1/2): ")
            
            if choice == "1":
                print("\n创建新的空数据库...")
                initialize_empty_database()
            else:
                print("\n请将您的 app.db 文件复制到以下路径:")
                print(f"  {Path('instance/app.db').absolute()}")
                print("复制完成后重新运行此脚本")
                return
                
        print("\n" + "=" * 60)
        print("✓ 数据库初始化完成")
        print(f"数据库路径: {Path('instance/app.db').absolute()}")
        
        # 最终验证
        print("\n最终验证...")
        is_valid, message = validate_database_integrity()
        print(f"最终验证结果: {message}")
        
        print("\n下一步:")
        print("1. 如果需要迁移现有数据，请运行: python scripts/migrate_database.py")
        print("2. 启动应用: python run.py")
        
    except Exception as e:
        print(f"\n✗ 数据库初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()