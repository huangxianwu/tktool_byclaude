#!/usr/bin/env python3
"""
精确识别需要清理的文件
基于项目实际情况，识别真正需要清理的废弃文件
"""

import os
import json
from pathlib import Path
from datetime import datetime

class CleanupFileIdentifier:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.cleanup_candidates = {
            'definitely_remove': [],  # 确定可以删除
            'probably_remove': [],    # 可能可以删除
            'review_required': [],    # 需要人工审核
            'keep': []               # 建议保留
        }
    
    def analyze_project(self):
        """分析项目文件"""
        print("开始精确分析项目文件...")
        
        # 1. 系统生成的文件（确定删除）
        self.identify_system_files()
        
        # 2. 空数据库文件（确定删除）
        self.identify_empty_databases()
        
        # 3. 临时文件和测试文件
        self.identify_temp_and_test_files()
        
        # 4. 日志文件
        self.identify_log_files()
        
        # 5. 备份文件
        self.identify_backup_files()
        
        # 6. 大型媒体文件（在temp目录中）
        self.identify_large_media_files()
        
        # 7. 调试和开发文件
        self.identify_debug_files()
    
    def identify_system_files(self):
        """识别系统生成的文件"""
        system_files = [
            '.DS_Store',
            'Thumbs.db',
            '.sync-meta.json'
        ]
        
        for root, dirs, files in os.walk(self.project_root):
            for file in files:
                if file in system_files:
                    file_path = Path(root) / file
                    relative_path = file_path.relative_to(self.project_root)
                    self.cleanup_candidates['definitely_remove'].append({
                        'path': str(relative_path),
                        'reason': f'系统生成文件: {file}',
                        'category': 'system_file',
                        'size': file_path.stat().st_size if file_path.exists() else 0
                    })
    
    def identify_empty_databases(self):
        """识别空的数据库文件"""
        db_files = ['app.db', 'task_manager.db', 'tasks.db']
        
        for db_file in db_files:
            db_path = self.project_root / db_file
            if db_path.exists() and db_path.stat().st_size == 0:
                self.cleanup_candidates['definitely_remove'].append({
                    'path': db_file,
                    'reason': '空的数据库文件，实际数据库在instance/目录',
                    'category': 'empty_database',
                    'size': 0
                })
    
    def identify_temp_and_test_files(self):
        """识别临时文件和测试文件"""
        # temp目录下的所有文件
        temp_dir = self.project_root / 'temp'
        if temp_dir.exists():
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = Path(root) / file
                    relative_path = file_path.relative_to(self.project_root)
                    file_size = file_path.stat().st_size if file_path.exists() else 0
                    
                    # 大型视频文件
                    if file.endswith(('.mp4', '.avi', '.mov')) and file_size > 5 * 1024 * 1024:
                        self.cleanup_candidates['probably_remove'].append({
                            'path': str(relative_path),
                            'reason': f'临时目录中的大型视频文件 ({file_size / 1024 / 1024:.1f}MB)',
                            'category': 'large_media',
                            'size': file_size
                        })
                    # 图片文件
                    elif file.endswith(('.png', '.jpg', '.jpeg')):
                        self.cleanup_candidates['review_required'].append({
                            'path': str(relative_path),
                            'reason': '临时目录中的图片文件，可能是测试素材',
                            'category': 'temp_image',
                            'size': file_size
                        })
                    # JSON配置文件
                    elif file.endswith('.json'):
                        self.cleanup_candidates['review_required'].append({
                            'path': str(relative_path),
                            'reason': '临时目录中的JSON文件，可能是工作流配置',
                            'category': 'temp_config',
                            'size': file_size
                        })
                    # 其他文件
                    else:
                        self.cleanup_candidates['probably_remove'].append({
                            'path': str(relative_path),
                            'reason': '临时目录中的其他文件',
                            'category': 'temp_other',
                            'size': file_size
                        })
        
        # tests目录下的调试文件
        tests_dir = self.project_root / 'tests'
        if tests_dir.exists():
            for root, dirs, files in os.walk(tests_dir):
                for file in files:
                    if file.startswith('debug_'):
                        file_path = Path(root) / file
                        relative_path = file_path.relative_to(self.project_root)
                        self.cleanup_candidates['probably_remove'].append({
                            'path': str(relative_path),
                            'reason': '调试文件，可能是临时生成的',
                            'category': 'debug_file',
                            'size': file_path.stat().st_size if file_path.exists() else 0
                        })
    
    def identify_log_files(self):
        """识别日志文件"""
        log_files = []
        
        for root, dirs, files in os.walk(self.project_root):
            for file in files:
                if file.endswith('.log'):
                    file_path = Path(root) / file
                    relative_path = file_path.relative_to(self.project_root)
                    file_size = file_path.stat().st_size if file_path.exists() else 0
                    
                    self.cleanup_candidates['probably_remove'].append({
                        'path': str(relative_path),
                        'reason': f'日志文件 ({file_size / 1024:.1f}KB)',
                        'category': 'log_file',
                        'size': file_size
                    })
    
    def identify_backup_files(self):
        """识别备份文件"""
        backup_patterns = ['.backup', '.bak', '.old', '_backup', '_old']
        
        for root, dirs, files in os.walk(self.project_root):
            for file in files:
                for pattern in backup_patterns:
                    if pattern in file:
                        file_path = Path(root) / file
                        relative_path = file_path.relative_to(self.project_root)
                        self.cleanup_candidates['probably_remove'].append({
                            'path': str(relative_path),
                            'reason': f'备份文件 (包含 {pattern})',
                            'category': 'backup_file',
                            'size': file_path.stat().st_size if file_path.exists() else 0
                        })
                        break
    
    def identify_large_media_files(self):
        """识别大型媒体文件"""
        media_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv']
        
        # 排除正常的输出目录
        exclude_paths = ['static/outputs', 'static/outputs/videos', 'static/outputs/images']
        
        for root, dirs, files in os.walk(self.project_root):
            # 跳过正常的输出目录
            root_path = Path(root)
            relative_root = root_path.relative_to(self.project_root)
            
            if any(str(relative_root).startswith(exclude_path) for exclude_path in exclude_paths):
                continue
                
            for file in files:
                if any(file.lower().endswith(ext) for ext in media_extensions):
                    file_path = Path(root) / file
                    relative_path = file_path.relative_to(self.project_root)
                    file_size = file_path.stat().st_size if file_path.exists() else 0
                    
                    # 大于10MB的视频文件
                    if file_size > 10 * 1024 * 1024:
                        self.cleanup_candidates['review_required'].append({
                            'path': str(relative_path),
                            'reason': f'大型视频文件 ({file_size / 1024 / 1024:.1f}MB)',
                            'category': 'large_video',
                            'size': file_size
                        })
    
    def identify_debug_files(self):
        """识别调试文件"""
        # 空的JS文件
        debug_js = self.project_root / 'debug_source_display.js'
        if debug_js.exists() and debug_js.stat().st_size == 0:
            self.cleanup_candidates['definitely_remove'].append({
                'path': 'debug_source_display.js',
                'reason': '空的调试JS文件',
                'category': 'empty_debug',
                'size': 0
            })
    
    def generate_cleanup_plan(self):
        """生成清理计划"""
        total_size = 0
        total_files = 0
        
        for category in self.cleanup_candidates.values():
            for file_info in category:
                total_size += file_info['size']
                total_files += 1
        
        plan = {
            'summary': {
                'total_files': total_files,
                'total_size_mb': round(total_size / 1024 / 1024, 2),
                'definitely_remove_count': len(self.cleanup_candidates['definitely_remove']),
                'probably_remove_count': len(self.cleanup_candidates['probably_remove']),
                'review_required_count': len(self.cleanup_candidates['review_required']),
                'analysis_date': datetime.now().isoformat()
            },
            'cleanup_candidates': self.cleanup_candidates
        }
        
        return plan
    
    def save_cleanup_plan(self, output_file):
        """保存清理计划"""
        plan = self.generate_cleanup_plan()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)
        
        print(f"清理计划已保存到: {output_file}")
        return plan
    
    def print_summary(self, plan):
        """打印摘要"""
        print("\n=== 文件清理分析摘要 ===")
        print(f"总文件数: {plan['summary']['total_files']}")
        print(f"总大小: {plan['summary']['total_size_mb']} MB")
        print(f"确定删除: {plan['summary']['definitely_remove_count']} 个文件")
        print(f"建议删除: {plan['summary']['probably_remove_count']} 个文件")
        print(f"需要审核: {plan['summary']['review_required_count']} 个文件")
        
        print("\n=== 确定删除的文件 ===")
        for file_info in self.cleanup_candidates['definitely_remove']:
            print(f"  {file_info['path']} - {file_info['reason']}")
        
        print("\n=== 建议删除的文件（前10个）===")
        for file_info in self.cleanup_candidates['probably_remove'][:10]:
            size_str = f"({file_info['size'] / 1024:.1f}KB)" if file_info['size'] > 0 else ""
            print(f"  {file_info['path']} {size_str} - {file_info['reason']}")
        
        if len(self.cleanup_candidates['probably_remove']) > 10:
            print(f"  ... 还有 {len(self.cleanup_candidates['probably_remove']) - 10} 个文件")

def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    identifier = CleanupFileIdentifier(project_root)
    
    identifier.analyze_project()
    
    # 保存清理计划
    plan_file = os.path.join(project_root, 'cleanup_plan.json')
    plan = identifier.save_cleanup_plan(plan_file)
    
    # 打印摘要
    identifier.print_summary(plan)
    
    return plan

if __name__ == "__main__":
    main()