#!/usr/bin/env python3
"""
TK工具文档同步脚本
自动同步已完成功能到PRD、README、CHANGELOG等文档
"""

import os
import re
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

class DocumentSyncer:
    def __init__(self, project_root="."):
        self.project_root = Path(project_root).resolve()
        self.dry_run = True
        self.completed_tasks = []
        
    def get_git_commits(self, since_date="2024-01-01"):
        """获取指定日期以来的Git提交"""
        try:
            # 修改命令，直接获取所有提交然后过滤
            cmd = f'git log --oneline --since="{since_date}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"⚠️  获取Git提交失败: {result.stderr}")
                return []
                
            commits = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = line.split(' ', 1)
                    if len(parts) >= 2:
                        message = parts[1]
                        # 过滤包含feat, fix, refactor的提交
                        if any(keyword in message.lower() for keyword in ['feat:', 'fix:', 'refactor:']):
                            commits.append({
                                'hash': parts[0],
                                'message': message,
                                "type": self.extract_commit_type(message)
                            })
                        
            return commits
            
        except Exception as e:
            print(f"⚠️  获取Git提交异常: {e}")
            return []
            
    def extract_commit_type(self, message):
        """提取提交类型"""
        if message.startswith("feat"):
            return "feat"
        elif message.startswith("fix"):
            return "fix"
        elif message.startswith("refactor"):
            return "refactor"
        else:
            return "other"
            
    def analyze_code_changes(self):
        """分析代码变更"""
        changes = {
            "models": [],
            "api_endpoints": [],
            "services": [],
            "ui_components": []
        }
        
        # 分析模型变更
        models_dir = self.project_root / "app" / "models"
        if models_dir.exists():
            for model_file in models_dir.glob("*.py"):
                if model_file.name != "__init__.py":
                    changes["models"].append(model_file.stem)
                    
        # 分析API端点
        api_dir = self.project_root / "app" / "api"
        if api_dir.exists():
            for api_file in api_dir.glob("*.py"):
                if api_file.name != "__init__.py":
                    changes["api_endpoints"].append(api_file.stem)
                    
        # 分析服务
        services_dir = self.project_root / "app" / "services"
        if services_dir.exists():
            for service_file in services_dir.glob("*.py"):
                if service_file.name != "__init__.py":
                    changes["services"].append(service_file.stem)
                    
        return changes
        
    def collect_completed_tasks(self):
        """收集已完成任务"""
        print("📊 收集已完成任务...")
        
        # 获取Git提交
        commits = self.get_git_commits()
        
        # 分析代码变更
        code_changes = self.analyze_code_changes()
        
        # 生成任务列表
        tasks = []
        
        for commit in commits[:10]:  # 最近10个提交
            task = {
                "id": f"TASK-{datetime.now().strftime('%Y%m%d')}-{len(tasks)+1:03d}",
                "title": commit["message"][:50] + ("..." if len(commit["message"]) > 50 else ""),
                "summary": commit["message"],
                "commit_hash": commit["hash"],
                "type": commit["type"],
                "timestamp": datetime.now().isoformat(),
                "breaking": "BREAKING" in commit["message"].upper(),
                "impacts": self.analyze_impacts(commit["message"])
            }
            tasks.append(task)
            
        self.completed_tasks = tasks
        print(f"✅ 收集到 {len(tasks)} 个已完成任务")
        return tasks
        
    def analyze_impacts(self, commit_message):
        """分析提交影响"""
        impacts = []
        
        if "模型" in commit_message or "model" in commit_message.lower():
            impacts.append("数据库模型变更")
        if "API" in commit_message or "api" in commit_message.lower():
            impacts.append("API接口变更")
        if "UI" in commit_message or "界面" in commit_message:
            impacts.append("用户界面变更")
        if "配置" in commit_message or "config" in commit_message.lower():
            impacts.append("配置文件变更")
            
        return impacts
        
    def update_prd(self):
        """更新PRD文档"""
        print("📝 更新PRD文档...")
        
        prd_path = self.project_root / "PRD.md"
        if not prd_path.exists():
            print("⚠️  PRD.md 文件不存在")
            return False
            
        # 读取现有PRD内容
        with open(prd_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # 生成变更记录
        change_entries = []
        for task in self.completed_tasks:
            entry = f"- **{task['id']}** ({task['timestamp'][:10]}): {task['summary']}"
            if task['impacts']:
                entry += f" - 影响: {', '.join(task['impacts'])}"
            change_entries.append(entry)
            
        # 插入变更记录
        change_section = "\n## 最新变更记录\n\n" + "\n".join(change_entries) + "\n"
        
        # 查找插入位置
        if "## 变更记录" in content:
            content = re.sub(r"## 变更记录.*?(?=\n##|\n$)", 
                           change_section, content, flags=re.DOTALL)
        else:
            # 在文档开头插入
            content = change_section + "\n" + content
            
        if not self.dry_run:
            with open(prd_path, "w", encoding="utf-8") as f:
                f.write(content)
                
        print("✅ PRD文档更新完成")
        return True
        
    def update_readme(self):
        """更新README文档"""
        print("📝 更新README文档...")
        
        readme_path = self.project_root / "README.md"
        if not readme_path.exists():
            print("⚠️  README.md 文件不存在")
            return False
            
        # 读取现有README内容
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # 更新核心功能部分
        core_features = [
            "- 🎯 **任务管理**: 支持工作流创建、任务执行和状态监控",
            "- 📁 **文件处理**: 支持多媒体文件上传、处理和输出管理", 
            "- 🔄 **队列管理**: 智能任务队列和并发控制",
            "- 📊 **实时监控**: 任务状态实时更新和日志流",
            "- 🎨 **用户界面**: 现代化Web界面，支持拖拽和实时预览",
            "- 🔌 **API集成**: 与RunningHub平台深度集成"
        ]
        
        features_section = "\n## 核心功能\n\n" + "\n".join(core_features) + "\n"
        
        # 更新功能部分
        if "## 核心功能" in content:
            content = re.sub(r"## 核心功能.*?(?=\n##|\n$)", 
                           features_section, content, flags=re.DOTALL)
        else:
            # 在适当位置插入
            content = content.replace("# TK工具", "# TK工具\n" + features_section)
            
        if not self.dry_run:
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(content)
                
        print("✅ README文档更新完成")
        return True
        
    def generate_changelog(self):
        """生成CHANGELOG"""
        print("📝 生成CHANGELOG...")
        
        changelog_path = self.project_root / "CHANGELOG.md"
        
        # 生成版本号
        version = self.determine_version()
        
        # 生成CHANGELOG内容
        changelog_content = f"""# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [{version}] - {datetime.now().strftime('%Y-%m-%d')}

"""
        
        # 按类型分组任务
        features = [t for t in self.completed_tasks if t['type'] == 'feat']
        fixes = [t for t in self.completed_tasks if t['type'] == 'fix']
        refactors = [t for t in self.completed_tasks if t['type'] == 'refactor']
        
        if features:
            changelog_content += "### Added\n"
            for task in features:
                changelog_content += f"- {task['summary']}\n"
            changelog_content += "\n"
            
        if fixes:
            changelog_content += "### Fixed\n"
            for task in fixes:
                changelog_content += f"- {task['summary']}\n"
            changelog_content += "\n"
            
        if refactors:
            changelog_content += "### Changed\n"
            for task in refactors:
                changelog_content += f"- {task['summary']}\n"
            changelog_content += "\n"
            
        # 如果文件已存在，合并内容
        if changelog_path.exists():
            with open(changelog_path, "r", encoding="utf-8") as f:
                existing_content = f.read()
                
            # 在现有内容前插入新版本
            if "## [" in existing_content:
                parts = existing_content.split("## [", 1)
                changelog_content += "## [" + parts[1]
            else:
                changelog_content += existing_content
                
        if not self.dry_run:
            with open(changelog_path, "w", encoding="utf-8") as f:
                f.write(changelog_content)
                
        print(f"✅ CHANGELOG生成完成 (版本: {version})")
        return True
        
    def determine_version(self):
        """确定版本号"""
        # 简单的版本策略
        has_breaking = any(t['breaking'] for t in self.completed_tasks)
        has_features = any(t['type'] == 'feat' for t in self.completed_tasks)
        has_fixes = any(t['type'] == 'fix' for t in self.completed_tasks)
        
        if has_breaking:
            return "1.0.0"  # Major
        elif has_features:
            return "0.2.0"  # Minor
        elif has_fixes:
            return "0.1.1"  # Patch
        else:
            return "0.1.0"  # Initial
            
    def create_sync_metadata(self):
        """创建同步元数据"""
        metadata = {
            "last_sync": datetime.now().isoformat(),
            "synced_commits": [t['commit_hash'] for t in self.completed_tasks],
            "version": self.determine_version(),
            "task_count": len(self.completed_tasks)
        }
        
        metadata_path = self.project_root / ".sync-meta.json"
        
        if not self.dry_run:
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
                
        print("✅ 同步元数据创建完成")
        
    def run(self, dry_run=True):
        """执行文档同步"""
        self.dry_run = dry_run
        
        print(f"🚀 开始文档同步 {'(DRY-RUN模式)' if dry_run else '(执行模式)'}")
        print(f"📁 项目根目录: {self.project_root}")
        
        # 收集已完成任务
        self.collect_completed_tasks()
        
        if not self.completed_tasks:
            print("ℹ️  没有发现需要同步的任务")
            return
            
        # 执行文档更新
        self.update_prd()
        self.update_readme()
        self.generate_changelog()
        self.create_sync_metadata()
        
        print(f"\n✅ 文档同步完成! 处理了 {len(self.completed_tasks)} 个任务")
        
        if dry_run:
            print("\n💡 这是预览模式，没有实际修改文件")
            print("   使用 --dry-run=false 参数执行实际同步")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="TK工具文档同步")
    parser.add_argument("--dry-run", default="true", help="是否为预览模式 (true/false)")
    parser.add_argument("--project-root", default=".", help="项目根目录路径")
    parser.add_argument("--since", default="2024-01-01", help="同步起始日期")
    
    args = parser.parse_args()
    
    syncer = DocumentSyncer(args.project_root)
    syncer.run(dry_run=args.dry_run.lower() == "true")

if __name__ == "__main__":
    main()