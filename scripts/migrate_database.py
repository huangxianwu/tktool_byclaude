#!/usr/bin/env python3
"""
数据库迁移脚本
用于将SQLite数据库从Mac环境迁移到Windows环境
"""

import os
import sys
import shutil
import sqlite3
import json
from pathlib import Path
from datetime import datetime

class DatabaseMigrator:
    def __init__(self):
        self.source_db = None
        self.target_db = Path("instance/app.db")
        self.backup_dir = Path("backups")
        
    def find_source_database(self):
        """查找源数据库文件"""
        possible_paths = [
            Path("instance/app.db"),
            Path("app.db"),
            Path("task_manager.db"),
            Path("tasks.db"),
            Path("instance/tktool.db")
        ]
        
        print("搜索可用的数据库文件...")
        available_dbs = []
        
        for db_path in possible_paths:
            if db_path.exists():
                size_mb = db_path.stat().st_size / (1024 * 1024)
                try:
                    conn = sqlite3.connect(str(db_path))
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                    tables = cursor.fetchall()
                    conn.close()
                    
                    available_dbs.append({
                        'path': db_path,
                        'size_mb': size_mb,
                        'tables': len(tables),
                        'table_names': [t[0] for t in tables]
                    })
                    
                    print(f"  ✓ {db_path} ({size_mb:.2f} MB, {len(tables)} 个表)")
                    
                except Exception as e:
                    print(f"  ✗ {db_path} (无法读取: {e})")
        
        if not available_dbs:
            print("✗ 没有找到可用的数据库文件")
            return None
            
        # 选择最大的数据库文件作为源
        source_db = max(available_dbs, key=lambda x: x['size_mb'])
        self.source_db = source_db['path']
        
        print(f"\n选择源数据库: {self.source_db} ({source_db['size_mb']:.2f} MB)")
        print(f"包含表: {', '.join(source_db['table_names'][:5])}")
        if len(source_db['table_names']) > 5:
            print(f"... 还有 {len(source_db['table_names']) - 5} 个表")
            
        return self.source_db
    
    def create_backup(self):
        """创建备份"""
        if not self.backup_dir.exists():
            self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 备份源数据库
        if self.source_db and self.source_db.exists():
            source_backup = self.backup_dir / f"source_db_{timestamp}.db"
            shutil.copy2(self.source_db, source_backup)
            print(f"✓ 源数据库备份: {source_backup}")
        
        # 备份目标数据库（如果存在）
        if self.target_db.exists():
            target_backup = self.backup_dir / f"target_db_{timestamp}.db"
            shutil.copy2(self.target_db, target_backup)
            print(f"✓ 目标数据库备份: {target_backup}")
            
        return timestamp
    
    def analyze_database_schema(self, db_path):
        """分析数据库结构"""
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # 获取所有表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            schema_info = {}
            for table in tables:
                # 获取表结构
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                
                # 获取记录数
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                
                schema_info[table] = {
                    'columns': columns,
                    'count': count
                }
            
            conn.close()
            return schema_info
            
        except Exception as e:
            print(f"✗ 分析数据库结构失败: {e}")
            return {}
    
    def migrate_database(self):
        """执行数据库迁移"""
        if not self.source_db:
            print("✗ 没有找到源数据库")
            return False
        
        try:
            print(f"\n开始迁移数据库...")
            print(f"源: {self.source_db}")
            print(f"目标: {self.target_db}")
            
            # 确保目标目录存在
            self.target_db.parent.mkdir(parents=True, exist_ok=True)
            
            # 直接复制数据库文件
            shutil.copy2(self.source_db, self.target_db)
            
            # 验证迁移结果
            if self.target_db.exists():
                size_mb = self.target_db.stat().st_size / (1024 * 1024)
                print(f"✓ 数据库迁移完成 ({size_mb:.2f} MB)")
                
                # 测试连接
                conn = sqlite3.connect(str(self.target_db))
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                conn.close()
                
                print(f"✓ 迁移验证成功，包含 {len(tables)} 个表")
                return True
            else:
                print("✗ 迁移失败，目标文件不存在")
                return False
                
        except Exception as e:
            print(f"✗ 数据库迁移失败: {e}")
            return False
    
    def export_database_info(self):
        """导出数据库信息"""
        if not self.target_db.exists():
            return
            
        try:
            schema_info = self.analyze_database_schema(self.target_db)
            
            info_file = Path("database_info.json")
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'migration_time': datetime.now().isoformat(),
                    'database_path': str(self.target_db),
                    'database_size_mb': self.target_db.stat().st_size / (1024 * 1024),
                    'schema_info': schema_info
                }, f, indent=2, ensure_ascii=False)
            
            print(f"✓ 数据库信息已导出: {info_file}")
            
        except Exception as e:
            print(f"⚠ 导出数据库信息失败: {e}")

def main():
    """主函数"""
    print("=" * 60)
    print("数据库迁移脚本")
    print("=" * 60)
    
    # 检查当前目录
    if not Path("config.py").exists():
        print("✗ 错误: 请在项目根目录运行此脚本")
        sys.exit(1)
    
    migrator = DatabaseMigrator()
    
    # 1. 查找源数据库
    if not migrator.find_source_database():
        print("\n请确保以下文件之一存在:")
        print("- instance/app.db (推荐)")
        print("- app.db")
        print("- task_manager.db")
        print("- tasks.db")
        sys.exit(1)
    
    # 2. 创建备份
    print(f"\n创建备份...")
    backup_timestamp = migrator.create_backup()
    
    # 3. 确认迁移
    print(f"\n准备迁移数据库:")
    print(f"源文件: {migrator.source_db}")
    print(f"目标文件: {migrator.target_db}")
    
    if migrator.target_db.exists():
        print(f"⚠ 警告: 目标数据库已存在，将被覆盖")
    
    response = input("\n确认执行迁移? (y/N): ")
    if response.lower() != 'y':
        print("迁移已取消")
        sys.exit(0)
    
    # 4. 检查源文件和目标文件是否相同
    if migrator.source_db.resolve() == migrator.target_db.resolve():
        print("\n⚠ 警告: 源文件和目标文件相同，无需迁移")
        print("✓ 数据库已在正确位置")
        
        # 导出信息
        migrator.export_database_info()
        
        print("\n" + "=" * 60)
        print("数据库检查完成!")
        print("=" * 60)
        print(f"\n数据库信息: database_info.json")
        print(f"\n下一步:")
        print(f"1. 运行: python run.py")
        print(f"2. 访问: http://localhost:5000")
        return
    
    # 5. 执行迁移
    if migrator.migrate_database():
        # 6. 导出信息
        migrator.export_database_info()
        
        print("\n" + "=" * 60)
        print("数据库迁移完成!")
        print("=" * 60)
        print(f"\n备份文件保存在: backups/ 目录")
        print(f"数据库信息: database_info.json")
        print(f"\n下一步:")
        print(f"1. 运行: python run.py")
        print(f"2. 访问: http://localhost:5000")
    else:
        print("\n✗ 数据库迁移失败")
        sys.exit(1)

if __name__ == "__main__":
    main()