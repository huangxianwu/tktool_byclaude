#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库同步脚本
功能：在部署过程中同步数据库文件
支持：本地备份、远程同步、增量更新
"""

import os
import sys
import json
import shutil
import sqlite3
import hashlib
import argparse
from datetime import datetime
from pathlib import Path
import subprocess

class DatabaseSyncer:
    def __init__(self, config_path=None):
        self.script_dir = Path(__file__).parent
        self.project_root = self.script_dir.parent
        self.config_path = config_path or self.script_dir / "deploy_config.json"
        self.load_config()
        
    def load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.db_config = config.get('database_sync', {})
                self.enabled = self.db_config.get('enabled', False)
                self.sync_method = self.db_config.get('sync_method', 'manual')
                self.backup_count = self.db_config.get('backup_count', 5)
        except FileNotFoundError:
            print(f"配置文件不存在: {self.config_path}")
            self.enabled = False
            self.sync_method = 'manual'
            self.backup_count = 5
        except json.JSONDecodeError as e:
            print(f"配置文件格式错误: {e}")
            sys.exit(1)
    
    def log(self, message):
        """日志输出"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {message}")
        
        # 写入日志文件
        log_file = self.script_dir / "deploy_sync.log"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {message}\n")
    
    def get_db_path(self):
        """获取数据库文件路径"""
        db_path = self.project_root / "instance" / "app.db"
        return db_path
    
    def get_backup_dir(self):
        """获取备份目录"""
        backup_dir = self.project_root / "backups" / "database"
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir
    
    def calculate_file_hash(self, file_path):
        """计算文件MD5哈希"""
        if not file_path.exists():
            return None
            
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def backup_database(self, source_path=None):
        """备份数据库"""
        if source_path is None:
            source_path = self.get_db_path()
        
        if not source_path.exists():
            self.log(f"数据库文件不存在: {source_path}")
            return None
        
        backup_dir = self.get_backup_dir()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = backup_dir / f"app_{timestamp}.db"
        
        try:
            shutil.copy2(source_path, backup_file)
            self.log(f"数据库备份成功: {backup_file}")
            
            # 清理旧备份
            self.cleanup_old_backups()
            
            return backup_file
        except Exception as e:
            self.log(f"数据库备份失败: {e}")
            return None
    
    def cleanup_old_backups(self):
        """清理旧备份文件"""
        backup_dir = self.get_backup_dir()
        backup_files = sorted(backup_dir.glob("app_*.db"), key=os.path.getmtime, reverse=True)
        
        if len(backup_files) > self.backup_count:
            for old_backup in backup_files[self.backup_count:]:
                try:
                    old_backup.unlink()
                    self.log(f"删除旧备份: {old_backup}")
                except Exception as e:
                    self.log(f"删除备份失败: {e}")
    
    def verify_database(self, db_path):
        """验证数据库完整性"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 执行完整性检查
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            
            conn.close()
            
            if result[0] == "ok":
                self.log(f"数据库完整性检查通过: {db_path}")
                return True
            else:
                self.log(f"数据库完整性检查失败: {result[0]}")
                return False
                
        except Exception as e:
            self.log(f"数据库验证失败: {e}")
            return False
    
    def get_database_info(self, db_path):
        """获取数据库信息"""
        if not db_path.exists():
            return None
            
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 获取表信息
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            # 获取记录数统计
            table_counts = {}
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                table_counts[table] = count
            
            conn.close()
            
            return {
                'file_size': db_path.stat().st_size,
                'modified_time': datetime.fromtimestamp(db_path.stat().st_mtime),
                'tables': tables,
                'table_counts': table_counts,
                'hash': self.calculate_file_hash(db_path)
            }
            
        except Exception as e:
            self.log(f"获取数据库信息失败: {e}")
            return None
    
    def compare_databases(self, db1_path, db2_path):
        """比较两个数据库"""
        info1 = self.get_database_info(db1_path)
        info2 = self.get_database_info(db2_path)
        
        if not info1 or not info2:
            return False
        
        # 比较哈希值
        if info1['hash'] == info2['hash']:
            self.log("数据库文件完全相同")
            return True
        
        # 比较表结构和数据
        self.log("数据库差异分析:")
        self.log(f"文件大小: {info1['file_size']} vs {info2['file_size']}")
        self.log(f"修改时间: {info1['modified_time']} vs {info2['modified_time']}")
        
        # 比较表数量
        for table in set(info1['table_counts'].keys()) | set(info2['table_counts'].keys()):
            count1 = info1['table_counts'].get(table, 0)
            count2 = info2['table_counts'].get(table, 0)
            if count1 != count2:
                self.log(f"表 {table}: {count1} vs {count2} 条记录")
        
        return False
    
    def sync_to_remote(self, remote_path, method='copy'):
        """同步到远程位置"""
        local_db = self.get_db_path()
        
        if not local_db.exists():
            self.log("本地数据库不存在，无法同步")
            return False
        
        # 备份本地数据库
        backup_file = self.backup_database()
        if not backup_file:
            self.log("本地备份失败，取消同步")
            return False
        
        try:
            remote_path = Path(remote_path)
            
            if method == 'copy':
                # 直接复制
                remote_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(local_db, remote_path)
                self.log(f"数据库同步成功: {remote_path}")
                
            elif method == 'rsync':
                # 使用rsync（如果可用）
                cmd = ['rsync', '-av', str(local_db), str(remote_path)]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    self.log(f"rsync同步成功: {remote_path}")
                else:
                    self.log(f"rsync同步失败: {result.stderr}")
                    return False
            
            # 验证同步结果
            if remote_path.exists():
                if self.verify_database(remote_path):
                    self.log("远程数据库验证通过")
                    return True
                else:
                    self.log("远程数据库验证失败")
                    return False
            else:
                self.log("远程数据库文件不存在")
                return False
                
        except Exception as e:
            self.log(f"数据库同步失败: {e}")
            return False
    
    def sync_from_remote(self, remote_path):
        """从远程同步"""
        remote_path = Path(remote_path)
        local_db = self.get_db_path()
        
        if not remote_path.exists():
            self.log(f"远程数据库不存在: {remote_path}")
            return False
        
        # 验证远程数据库
        if not self.verify_database(remote_path):
            self.log("远程数据库验证失败，取消同步")
            return False
        
        # 备份本地数据库
        if local_db.exists():
            backup_file = self.backup_database()
            if not backup_file:
                self.log("本地备份失败，取消同步")
                return False
        
        try:
            # 复制远程数据库到本地
            local_db.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(remote_path, local_db)
            
            # 验证本地数据库
            if self.verify_database(local_db):
                self.log(f"数据库同步成功: {local_db}")
                return True
            else:
                self.log("本地数据库验证失败")
                return False
                
        except Exception as e:
            self.log(f"数据库同步失败: {e}")
            return False
    
    def show_status(self):
        """显示同步状态"""
        self.log("数据库同步状态:")
        self.log(f"同步功能: {'启用' if self.enabled else '禁用'}")
        self.log(f"同步方式: {self.sync_method}")
        self.log(f"备份保留: {self.backup_count} 个")
        
        db_path = self.get_db_path()
        if db_path.exists():
            info = self.get_database_info(db_path)
            if info:
                self.log(f"数据库大小: {info['file_size']} 字节")
                self.log(f"修改时间: {info['modified_time']}")
                self.log(f"表数量: {len(info['tables'])}")
                self.log(f"文件哈希: {info['hash'][:8]}...")
        else:
            self.log("数据库文件不存在")
        
        # 显示备份信息
        backup_dir = self.get_backup_dir()
        backup_files = list(backup_dir.glob("app_*.db"))
        self.log(f"备份文件: {len(backup_files)} 个")

def main():
    parser = argparse.ArgumentParser(description='数据库同步工具')
    parser.add_argument('action', choices=['backup', 'sync-to', 'sync-from', 'status', 'compare'],
                       help='执行的操作')
    parser.add_argument('--remote', help='远程数据库路径')
    parser.add_argument('--config', help='配置文件路径')
    parser.add_argument('--method', choices=['copy', 'rsync'], default='copy',
                       help='同步方法')
    
    args = parser.parse_args()
    
    syncer = DatabaseSyncer(args.config)
    
    if args.action == 'backup':
        syncer.backup_database()
        
    elif args.action == 'sync-to':
        if not args.remote:
            print("错误: 需要指定 --remote 参数")
            sys.exit(1)
        syncer.sync_to_remote(args.remote, args.method)
        
    elif args.action == 'sync-from':
        if not args.remote:
            print("错误: 需要指定 --remote 参数")
            sys.exit(1)
        syncer.sync_from_remote(args.remote)
        
    elif args.action == 'status':
        syncer.show_status()
        
    elif args.action == 'compare':
        if not args.remote:
            print("错误: 需要指定 --remote 参数")
            sys.exit(1)
        local_db = syncer.get_db_path()
        syncer.compare_databases(local_db, Path(args.remote))

if __name__ == '__main__':
    main()