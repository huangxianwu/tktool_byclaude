#!/usr/bin/env python3
"""
TK工具项目结构重构脚本
自动整理项目目录，移动文件到标准化位置
"""

import os
import shutil
import json
from pathlib import Path
from datetime import datetime

class ProjectRestructurer:
    def __init__(self, project_root="."):
        self.project_root = Path(project_root).resolve()
        self.dry_run = True
        self.changes_log = []
        
    def log_change(self, action, source, target=None, reason=""):
        """记录变更操作"""
        change = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "source": str(source),
            "target": str(target) if target else None,
            "reason": reason
        }
        self.changes_log.append(change)
        
    def ensure_directory(self, path):
        """确保目录存在"""
        if not self.dry_run:
            path.mkdir(parents=True, exist_ok=True)
        print(f"📁 创建目录: {path}")
        
    def move_file(self, source, target, reason=""):
        """移动文件"""
        source_path = self.project_root / source
        target_path = self.project_root / target
        
        if not source_path.exists():
            print(f"⚠️  源文件不存在: {source}")
            return False
            
        self.log_change("move", source, target, reason)
        
        if self.dry_run:
            print(f"📄 [DRY-RUN] 移动: {source} → {target}")
        else:
            # 确保目标目录存在
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source_path), str(target_path))
            print(f"✅ 移动完成: {source} → {target}")
        return True
        
    def restructure_scripts(self):
        """整理工具脚本到scripts目录"""
        print("\n🔧 整理工具脚本...")
        self.ensure_directory(self.project_root / "scripts")
        
        script_patterns = [
            # 检查类脚本
            "check_*.py",
            # 清理类脚本  
            "clean_*.py",
            "cleanup_*.py",
            # 修复类脚本
            "fix_*.py",
            # 数据处理脚本
            "data_*.py",
            # 验证脚本
            "verify_*.py",
            # 测试脚本
            "test_*.py",
            # 其他工具脚本
            "batch_download_files.py",
            "reset_single_task.py",
            "update_database_paths.py",
            "migrate_file_names.py",
            "monitoring_scheduler.py",
            "query_workflows.py"
        ]
        
        for pattern in script_patterns:
            for file_path in self.project_root.glob(pattern):
                if file_path.is_file():
                    target = f"scripts/{file_path.name}"
                    self.move_file(file_path.name, target, "工具脚本标准化")
                    
    def restructure_docs(self):
        """整理文档到docs目录"""
        print("\n📚 整理文档...")
        
        # 创建文档目录结构
        doc_dirs = [
            "docs/api",
            "docs/deployment", 
            "docs/design",
            "docs/monitoring",
            "docs/architecture"
        ]
        
        for doc_dir in doc_dirs:
            self.ensure_directory(self.project_root / doc_dir)
            
        # 移动具体文档
        doc_moves = [
            ("test/doc/Deploy.md", "docs/deployment/Deploy.md", "部署文档标准化"),
            ("test/doc/UI_Design.md", "docs/design/UI_Design.md", "设计文档标准化"),
            ("README_monitoring.md", "docs/monitoring/README.md", "监控文档标准化"),
            ("PRD_taskmanager.md", "docs/architecture/PRD_taskmanager.md", "架构文档标准化")
        ]
        
        for source, target, reason in doc_moves:
            self.move_file(source, target, reason)
            
    def restructure_archive(self):
        """创建归档目录"""
        print("\n🗄️  创建归档目录...")
        
        archive_dirs = [
            "archive/deprecated",
            "archive/process"
        ]
        
        for archive_dir in archive_dirs:
            self.ensure_directory(self.project_root / archive_dir)
            
        # 移动归档文件
        archive_moves = [
            ("templates/task_create.html.backup", "archive/deprecated/task_create.html.backup", "备份文件归档"),
            ("test/临时debug.md", "archive/process/临时debug.md", "临时文档归档"),
            ("test/doc/临时debug.md", "archive/process/test_临时debug.md", "临时文档归档")
        ]
        
        for source, target, reason in archive_moves:
            if (self.project_root / source).exists():
                self.move_file(source, target, reason)
                
    def create_tests_dir(self):
        """标准化测试目录"""
        print("\n🧪 标准化测试目录...")
        
        # 如果test目录存在且不是标准的tests目录
        test_dir = self.project_root / "test"
        tests_dir = self.project_root / "tests"
        
        if test_dir.exists() and not tests_dir.exists():
            # 移动非文档文件到tests目录
            self.ensure_directory(tests_dir)
            
            for item in test_dir.iterdir():
                if item.is_file() and item.suffix == ".py":
                    target = f"tests/{item.name}"
                    self.move_file(f"test/{item.name}", target, "测试文件标准化")
                    
    def update_gitignore(self):
        """更新.gitignore文件"""
        print("\n📝 更新.gitignore...")
        
        gitignore_additions = [
            "# 归档目录",
            "archive/",
            "",
            "# 临时文件",
            "*.tmp",
            "*.temp",
            "",
            "# 输出目录", 
            "outputs/",
            "downloads/",
            "",
            "# 数据库备份",
            "*.db.backup",
            "instance/*.backup"
        ]
        
        gitignore_path = self.project_root / ".gitignore"
        
        if not self.dry_run:
            with open(gitignore_path, "a", encoding="utf-8") as f:
                f.write("\n".join(gitignore_additions))
                
        print("✅ .gitignore 更新完成")
        
    def generate_migration_report(self):
        """生成迁移报告"""
        report_path = self.project_root / "MIGRATION.md"
        
        report_content = f"""# 项目结构迁移报告

## 迁移时间
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 变更摘要
- 工具脚本移动到 `scripts/` 目录
- 文档整理到 `docs/` 目录  
- 创建 `archive/` 归档目录
- 标准化 `tests/` 测试目录

## 详细变更记录
"""
        
        for change in self.changes_log:
            report_content += f"\n### {change['action'].upper()}: {change['source']}"
            if change['target']:
                report_content += f" → {change['target']}"
            if change['reason']:
                report_content += f"\n**原因**: {change['reason']}"
            report_content += f"\n**时间**: {change['timestamp']}\n"
            
        if not self.dry_run:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report_content)
                
        print(f"📊 迁移报告: {report_path}")
        
    def run(self, dry_run=True):
        """执行重构"""
        self.dry_run = dry_run
        
        print(f"🚀 开始项目重构 {'(DRY-RUN模式)' if dry_run else '(执行模式)'}")
        print(f"📁 项目根目录: {self.project_root}")
        
        # 执行重构步骤
        self.restructure_scripts()
        self.restructure_docs()
        self.restructure_archive()
        self.create_tests_dir()
        self.update_gitignore()
        self.generate_migration_report()
        
        print(f"\n✅ 重构完成! 共处理 {len(self.changes_log)} 个变更")
        
        if dry_run:
            print("\n💡 这是预览模式，没有实际移动文件")
            print("   使用 --execute 参数执行实际重构")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="TK工具项目结构重构")
    parser.add_argument("--execute", action="store_true", help="执行实际重构(默认为dry-run)")
    parser.add_argument("--project-root", default=".", help="项目根目录路径")
    
    args = parser.parse_args()
    
    restructurer = ProjectRestructurer(args.project_root)
    restructurer.run(dry_run=not args.execute)

if __name__ == "__main__":
    main()