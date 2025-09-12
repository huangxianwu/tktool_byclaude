#!/usr/bin/env python3
"""
查询数据库中指定工作流的完整数据
"""

import json
from app import create_app, db
from app.models import Workflow, Node

def query_workflow_data(workflow_ids):
    """查询指定工作流的完整数据"""
    app = create_app()
    
    with app.app_context():
        results = []
        
        for workflow_id in workflow_ids:
            print(f"\n🔍 查询工作流: {workflow_id}")
            
            # 查询工作流基本信息
            workflow = Workflow.query.filter_by(workflow_id=workflow_id).first()
            
            if not workflow:
                print(f"❌ 工作流 {workflow_id} 不存在")
                continue
                
            print(f"✅ 找到工作流: {workflow.name}")
            
            # 查询关联的节点
            nodes = Node.query.filter_by(workflow_id=workflow_id).all()
            print(f"📋 节点数量: {len(nodes)}")
            
            # 构建完整数据结构
            workflow_data = {
                'workflow_id': workflow.workflow_id,
                'name': workflow.name,
                'created_at': workflow.created_at.isoformat() if workflow.created_at else None,
                'nodes': []
            }
            
            for node in nodes:
                node_data = {
                    'node_id': node.node_id,
                    'node_name': node.node_name,
                    'node_type': node.node_type
                }
                workflow_data['nodes'].append(node_data)
                print(f"   🔸 节点: {node.node_id} -> {node.node_name} ({node.node_type})")
            
            results.append(workflow_data)
        
        return results

def main():
    """主函数"""
    # 要查询的工作流ID
    target_workflow_ids = [
        "1962342403615166465",
        "1956307610033160194"
    ]
    
    print("🔍 开始查询数据库中的工作流数据...")
    print("=" * 50)
    
    # 查询数据
    workflow_data = query_workflow_data(target_workflow_ids)
    
    if not workflow_data:
        print("\n❌ 没有找到任何工作流数据")
        return
    
    print("\n" + "=" * 50)
    print("📊 查询结果汇总:")
    print("=" * 50)
    
    for i, workflow in enumerate(workflow_data, 1):
        print(f"\n{i}. 工作流ID: {workflow['workflow_id']}")
        print(f"   名称: {workflow['name']}")
        print(f"   创建时间: {workflow['created_at']}")
        print(f"   节点数量: {len(workflow['nodes'])}")
        
        for j, node in enumerate(workflow['nodes'], 1):
            print(f"     {j}) {node['node_name']} ({node['node_type']}) - ID: {node['node_id']}")
    
    # 输出JSON格式的完整数据
    print("\n" + "=" * 50)
    print("📄 完整JSON数据:")
    print("=" * 50)
    print(json.dumps(workflow_data, indent=2, ensure_ascii=False))
    
    # 保存到文件
    output_file = 'workflow_data_export.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(workflow_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 数据已保存到: {output_file}")
    print("\n✅ 查询完成！请确认数据无误后，我将创建初始化脚本。")

if __name__ == "__main__":
    main()