#!/usr/bin/env python3
"""
项目废弃文件分析脚本
分析TK Tool项目中可能已经废弃的文件和代码
"""

import os
import re
import json
import ast
from pathlib import Path
from collections import defaultdict
from datetime import datetime

class DeprecatedFileAnalyzer:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.analysis_result = {
            'deprecated_files': [],
            'suspicious_files': [],
            'temp_files': [],
            'unused_imports': [],
            'dead_code': [],
            'analysis_date': datetime.now().isoformat()
        }
        
        # 定义可能废弃的文件模式
        self.deprecated_patterns = [
            r'.*\.bak$',
            r'.*\.backup$',
            r'.*\.old$',
            r'.*\.tmp$',
            r'.*\.temp$',
            r'.*_old\.',
            r'.*_backup\.',
            r'.*_deprecated\.',
            r'.*\.orig$',
            r'.*~$',
            r'.*\.swp$',
            r'.*\.swo$',
            r'.*\.DS_Store$',
            r'.*Thumbs\.db$',
            r'.*\.pyc$',
            r'.*__pycache__.*',
            r'.*\.log$',
            r'.*\.cache$'
        ]
        
        # 临时文件目录
        self.temp_directories = ['temp', 'tmp', 'cache', 'logs', 'backups']
        
        # 可能废弃的关键词
        self.deprecated_keywords = [
            'deprecated', 'obsolete', 'unused', 'old', 'legacy', 
            'todo', 'fixme', 'hack', 'temp', 'test', 'debug'
        ]

    def scan_files(self):
        """扫描所有文件"""
        print("开始扫描项目文件...")
        
        for root, dirs, files in os.walk(self.project_root):
            # 跳过隐藏目录和特定目录
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__']]
            
            for file in files:
                file_path = Path(root) / file
                relative_path = file_path.relative_to(self.project_root)
                
                # 检查是否为废弃文件模式
                if self.is_deprecated_pattern(file):
                    self.analysis_result['deprecated_files'].append({
                        'path': str(relative_path),
                        'reason': 'matches deprecated pattern',
                        'size': file_path.stat().st_size if file_path.exists() else 0
                    })
                
                # 检查临时文件目录
                if any(temp_dir in str(relative_path) for temp_dir in self.temp_directories):
                    self.analysis_result['temp_files'].append({
                        'path': str(relative_path),
                        'reason': 'in temporary directory',
                        'size': file_path.stat().st_size if file_path.exists() else 0
                    })
                
                # 分析Python文件
                if file.endswith('.py'):
                    self.analyze_python_file(file_path, relative_path)
                
                # 分析其他文件
                self.analyze_general_file(file_path, relative_path)

    def is_deprecated_pattern(self, filename):
        """检查文件名是否匹配废弃模式"""
        for pattern in self.deprecated_patterns:
            if re.match(pattern, filename, re.IGNORECASE):
                return True
        return False

    def analyze_python_file(self, file_path, relative_path):
        """分析Python文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查废弃关键词
            for keyword in self.deprecated_keywords:
                if keyword.lower() in content.lower():
                    self.analysis_result['suspicious_files'].append({
                        'path': str(relative_path),
                        'reason': f'contains keyword: {keyword}',
                        'type': 'python'
                    })
                    break
            
            # 检查是否有TODO/FIXME注释
            todo_pattern = r'#.*(?:TODO|FIXME|XXX|HACK).*'
            todos = re.findall(todo_pattern, content, re.IGNORECASE)
            if todos:
                self.analysis_result['suspicious_files'].append({
                    'path': str(relative_path),
                    'reason': f'contains {len(todos)} TODO/FIXME comments',
                    'type': 'python',
                    'details': todos[:3]  # 只保留前3个
                })
            
            # 简单的AST分析
            try:
                tree = ast.parse(content)
                self.analyze_ast(tree, relative_path)
            except SyntaxError:
                pass
                
        except Exception as e:
            print(f"分析文件 {file_path} 时出错: {e}")

    def analyze_ast(self, tree, relative_path):
        """分析AST查找可能的死代码"""
        # 查找未使用的函数定义
        function_defs = []
        class_defs = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name.startswith('_') and not node.name.startswith('__'):
                    function_defs.append(node.name)
            elif isinstance(node, ast.ClassDef):
                if node.name.startswith('_'):
                    class_defs.append(node.name)
        
        if function_defs or class_defs:
            self.analysis_result['dead_code'].append({
                'path': str(relative_path),
                'private_functions': function_defs,
                'private_classes': class_defs,
                'reason': 'contains private methods/classes that might be unused'
            })

    def analyze_general_file(self, file_path, relative_path):
        """分析一般文件"""
        try:
            # 检查文件大小
            file_size = file_path.stat().st_size
            
            # 检查空文件
            if file_size == 0:
                self.analysis_result['suspicious_files'].append({
                    'path': str(relative_path),
                    'reason': 'empty file',
                    'size': 0
                })
            
            # 检查非常大的文件（可能是日志或临时文件）
            if file_size > 10 * 1024 * 1024:  # 10MB
                self.analysis_result['suspicious_files'].append({
                    'path': str(relative_path),
                    'reason': f'very large file ({file_size / 1024 / 1024:.1f}MB)',
                    'size': file_size
                })
            
        except Exception as e:
            print(f"分析文件 {file_path} 时出错: {e}")

    def analyze_imports(self):
        """分析Python文件的导入关系"""
        print("分析导入关系...")
        
        python_files = []
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)
        
        # 简单的导入分析
        all_imports = set()
        defined_modules = set()
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 提取导入
                import_pattern = r'(?:from\s+(\S+)\s+import|import\s+(\S+))'
                imports = re.findall(import_pattern, content)
                for imp in imports:
                    module = imp[0] if imp[0] else imp[1]
                    if module.startswith('.') or 'app.' in module:
                        all_imports.add(module)
                
                # 记录定义的模块
                relative_path = py_file.relative_to(self.project_root)
                module_name = str(relative_path).replace('/', '.').replace('.py', '')
                defined_modules.add(module_name)
                
            except Exception as e:
                print(f"分析导入 {py_file} 时出错: {e}")

    def generate_report(self):
        """生成分析报告"""
        report = {
            'summary': {
                'total_deprecated_files': len(self.analysis_result['deprecated_files']),
                'total_suspicious_files': len(self.analysis_result['suspicious_files']),
                'total_temp_files': len(self.analysis_result['temp_files']),
                'total_dead_code_files': len(self.analysis_result['dead_code'])
            },
            'details': self.analysis_result
        }
        
        return report

    def save_report(self, output_file):
        """保存分析报告"""
        report = self.generate_report()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"分析报告已保存到: {output_file}")
        return report

def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    analyzer = DeprecatedFileAnalyzer(project_root)
    
    print("开始项目废弃文件分析...")
    analyzer.scan_files()
    analyzer.analyze_imports()
    
    # 保存报告
    report_file = os.path.join(project_root, 'deprecated_files_analysis.json')
    report = analyzer.save_report(report_file)
    
    # 打印摘要
    print("\n=== 分析摘要 ===")
    print(f"废弃文件: {report['summary']['total_deprecated_files']}")
    print(f"可疑文件: {report['summary']['total_suspicious_files']}")
    print(f"临时文件: {report['summary']['total_temp_files']}")
    print(f"可能的死代码文件: {report['summary']['total_dead_code_files']}")
    
    return report

if __name__ == "__main__":
    main()