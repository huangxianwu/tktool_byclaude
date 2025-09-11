#!/usr/bin/env python3
"""
清理孤立任务脚本
删除不属于保留工作流的所有任务
"""

import requests
import json

# 要保留的工作流ID
KEEP_WORKFLOWS = ['1956307610033160194', '1962342403615166465']
BASE_URL = 'http://localhost:5002'

def get_all_tasks():
    """获取所有任务"""
    response = requests.get(f'{BASE_URL}/api/tasks')
    if response.status_code == 200:
        return response.json()
    else:
        print(f"获取任务失败: {response.status_code}")
        return []

def delete_task(task_id):
    """删除单个任务"""
    response = requests.delete(f'{BASE_URL}/api/tasks/{task_id}')
    return response.status_code == 200

def main():
    print("🧹 开始清理孤立任务...")
    print(f"保留的工作流: {KEEP_WORKFLOWS}")
    print()
    
    # 获取所有任务
    tasks = get_all_tasks()
    if not tasks:
        print("❌ 无法获取任务列表")
        return
    
    print(f"📊 找到 {len(tasks)} 个任务:")
    
    # 按工作流分组
    workflow_tasks = {}
    for task in tasks:
        workflow_id = task['workflow_id']
        if workflow_id not in workflow_tasks:
            workflow_tasks[workflow_id] = []
        workflow_tasks[workflow_id].append(task)
    
    for workflow_id, task_list in workflow_tasks.items():
        status = "🟢 保留" if workflow_id in KEEP_WORKFLOWS else "🔴 删除"
        print(f"   {status} 工作流 {workflow_id}: {len(task_list)} 个任务")
    
    print()
    
    # 识别要删除的任务
    tasks_to_delete = [task for task in tasks if task['workflow_id'] not in KEEP_WORKFLOWS]
    
    if not tasks_to_delete:
        print("✅ 没有需要删除的孤立任务")
        return
    
    print(f"🗑️ 将删除 {len(tasks_to_delete)} 个孤立任务:")
    
    deleted_count = 0
    for task in tasks_to_delete:
        task_id = task['task_id']
        workflow_id = task['workflow_id']
        
        if delete_task(task_id):
            print(f"   ✅ 删除任务: {task_id[:8]}... (工作流: {workflow_id})")
            deleted_count += 1
        else:
            print(f"   ❌ 删除失败: {task_id[:8]}... (工作流: {workflow_id})")
    
    print(f"\n📊 清理完成:")
    print(f"   删除任务: {deleted_count} 个")
    
    # 验证结果
    print(f"\n🔍 验证清理结果:")
    remaining_tasks = get_all_tasks()
    
    remaining_workflow_tasks = {}
    for task in remaining_tasks:
        workflow_id = task['workflow_id']
        if workflow_id not in remaining_workflow_tasks:
            remaining_workflow_tasks[workflow_id] = []
        remaining_workflow_tasks[workflow_id].append(task)
    
    print(f"   剩余任务: {len(remaining_tasks)} 个")
    for workflow_id, task_list in remaining_workflow_tasks.items():
        print(f"   - 工作流 {workflow_id}: {len(task_list)} 个任务")
    
    print("\n✅ 孤立任务清理完成！")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ 操作被用户中断")
    except Exception as e:
        print(f"\n❌ 执行出错: {e}")
        import traceback
        traceback.print_exc()