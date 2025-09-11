#!/usr/bin/env python3
"""
清理工作流和任务脚本
只保留指定的两个工作流：1956307610033160194 和 1962342403615166465
删除其他所有工作流及其相关任务
"""

import requests
import json

# 要保留的工作流ID
KEEP_WORKFLOWS = ['1956307610033160194', '1962342403615166465']
BASE_URL = 'http://localhost:5002'

def get_all_workflows():
    """获取所有工作流"""
    response = requests.get(f'{BASE_URL}/api/workflows')
    if response.status_code == 200:
        return response.json()
    else:
        print(f"获取工作流失败: {response.status_code}")
        return []

def get_tasks_for_workflow(workflow_id):
    """获取指定工作流的所有任务"""
    response = requests.get(f'{BASE_URL}/api/tasks')
    if response.status_code == 200:
        all_tasks = response.json()
        return [task for task in all_tasks if task['workflow_id'] == workflow_id]
    else:
        print(f"获取任务失败: {response.status_code}")
        return []

def delete_task(task_id):
    """删除单个任务"""
    response = requests.delete(f'{BASE_URL}/api/tasks/{task_id}')
    return response.status_code == 200

def delete_workflow(workflow_id):
    """删除工作流"""
    response = requests.delete(f'{BASE_URL}/api/workflows/{workflow_id}')
    return response.status_code == 200

def main():
    print("🧹 开始清理工作流和任务...")
    print(f"保留的工作流: {KEEP_WORKFLOWS}")
    print()
    
    # 获取所有工作流
    workflows = get_all_workflows()
    if not workflows:
        print("❌ 无法获取工作流列表")
        return
    
    print(f"📊 找到 {len(workflows)} 个工作流:")
    for wf in workflows:
        status = "🟢 保留" if wf['workflow_id'] in KEEP_WORKFLOWS else "🔴 删除"
        print(f"   {status} {wf['workflow_id']} - {wf['name']}")
    
    print()
    
    # 识别要删除的工作流
    workflows_to_delete = [wf for wf in workflows if wf['workflow_id'] not in KEEP_WORKFLOWS]
    
    if not workflows_to_delete:
        print("✅ 没有需要删除的工作流")
        return
    
    print(f"🗑️ 将删除 {len(workflows_to_delete)} 个工作流及其任务:")
    
    deleted_workflows = 0
    deleted_tasks = 0
    
    for workflow in workflows_to_delete:
        workflow_id = workflow['workflow_id']
        workflow_name = workflow['name']
        
        print(f"\n📋 处理工作流: {workflow_name} ({workflow_id})")
        
        # 获取该工作流的所有任务
        tasks = get_tasks_for_workflow(workflow_id)
        print(f"   找到 {len(tasks)} 个相关任务")
        
        # 删除所有相关任务
        for task in tasks:
            task_id = task['task_id']
            if delete_task(task_id):
                print(f"   ✅ 删除任务: {task_id}")
                deleted_tasks += 1
            else:
                print(f"   ❌ 删除任务失败: {task_id}")
        
        # 删除工作流
        if delete_workflow(workflow_id):
            print(f"   ✅ 删除工作流: {workflow_name}")
            deleted_workflows += 1
        else:
            print(f"   ❌ 删除工作流失败: {workflow_name}")
    
    print(f"\n📊 清理完成:")
    print(f"   删除工作流: {deleted_workflows} 个")
    print(f"   删除任务: {deleted_tasks} 个")
    
    # 验证结果
    print(f"\n🔍 验证清理结果:")
    remaining_workflows = get_all_workflows()
    print(f"   剩余工作流: {len(remaining_workflows)} 个")
    
    for wf in remaining_workflows:
        print(f"   - {wf['workflow_id']} - {wf['name']}")
    
    print("\n✅ 清理操作完成！")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ 操作被用户中断")
    except Exception as e:
        print(f"\n❌ 执行出错: {e}")
        import traceback
        traceback.print_exc()