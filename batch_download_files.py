#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量下载所有成功任务的文件
"""

import requests
import time
from app import create_app, db
from app.models.Task import Task

def batch_download_all_success_tasks():
    """批量下载所有成功任务的文件"""
    app = create_app()
    
    with app.app_context():
        # 获取所有成功的任务
        success_tasks = Task.query.filter_by(status='SUCCESS').all()
        task_ids = [task.task_id for task in success_tasks]
        
        print(f"找到 {len(task_ids)} 个成功的任务")
        
        success_count = 0
        failed_count = 0
        
        for i, task_id in enumerate(task_ids, 1):
            print(f"\n[{i}/{len(task_ids)}] 处理任务: {task_id}")
            
            try:
                # 调用下载API
                response = requests.post(
                    f'http://localhost:5001/api/tasks/{task_id}/download-files',
                    headers={'Content-Type': 'application/json'},
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        file_count = result.get('total_count', 0)
                        print(f"✅ 成功下载 {file_count} 个文件")
                        success_count += 1
                    else:
                        print(f"❌ 下载失败: {result.get('error', '未知错误')}")
                        failed_count += 1
                else:
                    print(f"❌ HTTP错误: {response.status_code}")
                    failed_count += 1
                    
            except Exception as e:
                print(f"❌ 异常错误: {str(e)}")
                failed_count += 1
            
            # 添加延迟避免过载
            if i < len(task_ids):
                time.sleep(1)
        
        print(f"\n=== 批量下载完成 ===")
        print(f"成功: {success_count} 个任务")
        print(f"失败: {failed_count} 个任务")
        print(f"总计: {len(task_ids)} 个任务")

if __name__ == '__main__':
    batch_download_all_success_tasks()