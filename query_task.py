#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查询本地任务参数的临时脚本
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models.Task import Task
from app.models.TaskData import TaskData
from app.models.Workflow import Workflow
import json

def query_task_details(task_id):
    """查询任务的详细信息"""
    app = create_app()
    
    with app.app_context():
        # 查询任务基本信息
        task = Task.query.get(task_id)
        if not task:
            print(f"❌ 任务 {task_id} 不存在")
            return None
            
        # 查询工作流信息
        workflow = Workflow.query.get(task.workflow_id)
        
        # 查询任务数据
        task_data = TaskData.query.filter_by(task_id=task_id).all()
        
        print(f"=== 任务信息 ===")
        print(f"任务ID: {task.task_id}")
        print(f"工作流ID: {task.workflow_id}")
        print(f"工作流名称: {workflow.name if workflow else 'Unknown'}")
        print(f"状态: {task.status}")
        print(f"Plus模式: {getattr(task, 'is_plus', False)}")
        print(f"RunningHub任务ID: {task.runninghub_task_id}")
        print(f"创建时间: {task.created_at}")
        
        # 显示工作流的节点信息
        if workflow:
            from app.models.Node import Node
            nodes = Node.query.filter_by(workflow_id=task.workflow_id).all()
            print(f"工作流节点数量: {len(nodes)}")
            for node in nodes:
                print(f"  - 节点{node.node_id}: {node.node_type}")
        print()
        
        print(f"=== 任务参数 ({len(task_data)} 个) ===")
        node_info_list = []
        for i, data in enumerate(task_data, 1):
            print(f"{i}. 节点ID: {data.node_id}")
            print(f"   字段名: {data.field_name}")
            print(f"   字段值: {data.field_value[:100]}{'...' if len(str(data.field_value)) > 100 else ''}")
            print(f"   文件URL: {data.file_url or 'None'}")
            print()
            
            # 构建API格式的参数
            node_info = {
                "nodeId": data.node_id,
                "fieldName": data.field_name,
                "fieldValue": data.field_value
            }
            node_info_list.append(node_info)
        
        return {
            'task': task,
            'workflow': workflow,
            'task_data': task_data,
            'node_info_list': node_info_list
        }

if __name__ == "__main__":
    task_id = "867e4df5-705d-4493-b59b-716c3f102208"
    result = query_task_details(task_id)
    
    if result:
        print("=== API格式参数 ===")
        print(json.dumps(result['node_info_list'], indent=2, ensure_ascii=False))