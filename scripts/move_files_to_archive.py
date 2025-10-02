#!/usr/bin/env python3
"""
文件归档脚本
将识别的废弃文件移动到归档目录，便于人工确认后删除
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime

class FileArchiver:
    def __init__(self, project_root, cleanup_plan_file):
        self.project_root = Path(project_root)
        self.cleanup_plan_file = cleanup_plan_file
        self.archive_root = self.project_root / 'archive_for_cleanup'
        self.moved_files = {
            'definitely_remove': [],
            'probably_remove': [],
            'review_required': []
        }
        
        # 确保归档目录存在
        self.archive_root.mkdir(exist_ok=True)
        (self.archive_root / 'definitely_remove').mkdir(exist_ok=True)
        (self.archive_root / 'probably_remove').mkdir(exist_ok=True)
        (self.archive_root / 'review_required').mkdir(exist_ok=True)
    
    def load_cleanup_plan(self):
        """加载清理计划"""
        with open(self.cleanup_plan_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def move_files(self, category, files_list, dry_run=False):
        """移动文件到指定类别的归档目录"""
        archive_dir = self.archive_root / category
        
        for file_info in files_list:
            source_path = self.project_root / file_info['path']
            
            if not source_path.exists():
                print(f"文件不存在，跳过: {file_info['path']}")
                continue
            
            # 创建目标路径，保持目录结构
            relative_path = Path(file_info['path'])
            target_path = archive_dir / relative_path
            
            # 确保目标目录存在
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            if dry_run:
                print(f"[DRY RUN] 将移动: {source_path} -> {target_path}")
            else:
                try:
                    shutil.move(str(source_path), str(target_path))
                    print(f"已移动: {file_info['path']} -> {category}/")
                    self.moved_files[category].append({
                        'original_path': file_info['path'],
                        'archive_path': str(target_path.relative_to(self.project_root)),
                        'reason': file_info['reason'],
                        'size': file_info['size'],
                        'moved_at': datetime.now().isoformat()
                    })
                except Exception as e:
                    print(f"移动文件失败 {file_info['path']}: {e}")
    
    def archive_files(self, dry_run=False):
        """执行文件归档"""
        cleanup_plan = self.load_cleanup_plan()
        
        print(f"开始文件归档 {'(预览模式)' if dry_run else ''}...")
        
        # 移动确定删除的文件
        print(f"\n=== 移动确定删除的文件 ({len(cleanup_plan['cleanup_candidates']['definitely_remove'])} 个) ===")
        self.move_files('definitely_remove', cleanup_plan['cleanup_candidates']['definitely_remove'], dry_run)
        
        # 移动建议删除的文件
        print(f"\n=== 移动建议删除的文件 ({len(cleanup_plan['cleanup_candidates']['probably_remove'])} 个) ===")
        self.move_files('probably_remove', cleanup_plan['cleanup_candidates']['probably_remove'], dry_run)
        
        # 移动需要审核的文件
        print(f"\n=== 移动需要审核的文件 ({len(cleanup_plan['cleanup_candidates']['review_required'])} 个) ===")
        self.move_files('review_required', cleanup_plan['cleanup_candidates']['review_required'], dry_run)
        
        if not dry_run:
            # 保存移动记录
            self.save_move_record()
    
    def save_move_record(self):
        """保存移动记录"""
        record = {
            'archive_date': datetime.now().isoformat(),
            'moved_files': self.moved_files,
            'summary': {
                'definitely_remove_count': len(self.moved_files['definitely_remove']),
                'probably_remove_count': len(self.moved_files['probably_remove']),
                'review_required_count': len(self.moved_files['review_required'])
            }
        }
        
        record_file = self.archive_root / 'move_record.json'
        with open(record_file, 'w', encoding='utf-8') as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        
        print(f"\n移动记录已保存到: {record_file}")
    
    def create_readme(self):
        """创建归档目录说明文件"""
        readme_content = """# 文件归档目录

此目录包含从项目中识别出的可能废弃的文件，按照清理建议分类存放。

## 目录结构

### definitely_remove/
**确定可以删除的文件**
- 系统生成文件（.DS_Store, .sync-meta.json等）
- 空的数据库文件（实际数据库在instance/目录）
- 空的调试文件

### probably_remove/
**建议删除的文件**
- 临时目录中的大型视频文件
- 日志文件
- 备份文件
- 调试文件

### review_required/
**需要人工审核的文件**
- 临时目录中的图片和配置文件
- 大型媒体文件
- 可能包含重要数据的文件

## 操作建议

1. **definitely_remove/** 目录中的文件可以直接删除
2. **probably_remove/** 目录中的文件建议删除，但请先确认
3. **review_required/** 目录中的文件需要仔细审核后决定是否删除

## 恢复文件

如果需要恢复某个文件，可以将其从归档目录移回原位置。
原始路径信息保存在 `move_record.json` 文件中。

## 确认删除

确认所有文件都不需要后，可以删除整个 `archive_for_cleanup` 目录。
"""
        
        readme_file = self.archive_root / 'README.md'
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        print(f"归档说明文件已创建: {readme_file}")

def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cleanup_plan_file = os.path.join(project_root, 'cleanup_plan.json')
    
    if not os.path.exists(cleanup_plan_file):
        print(f"清理计划文件不存在: {cleanup_plan_file}")
        print("请先运行 identify_cleanup_files.py 生成清理计划")
        return
    
    archiver = FileArchiver(project_root, cleanup_plan_file)
    
    # 创建说明文件
    archiver.create_readme()
    
    # 询问是否预览
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--dry-run':
        print("=== 预览模式 ===")
        archiver.archive_files(dry_run=True)
    else:
        print("=== 执行文件归档 ===")
        archiver.archive_files(dry_run=False)
        
        print("\n=== 归档完成 ===")
        print("文件已移动到 archive_for_cleanup/ 目录")
        print("请检查归档的文件，确认无误后可以删除")

if __name__ == "__main__":
    main()