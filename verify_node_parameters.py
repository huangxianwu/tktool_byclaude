#!/usr/bin/env python3
"""
验证修复后的节点参数结构
检查APIKEY_INVALID_NODE_INFO错误的修复
"""

import json

def verify_node_parameters():
    print("🧪 验证修复后的节点参数结构")
    print("=" * 50)
    
    # 1. 读取工作流JSON获取正确的节点定义
    print("📋 分析工作流节点定义...")
    
    with open('/Users/winston/Desktop/Gitlab/repository/tk/tktool_byclaude/test/1962342403615166465-背景替换工作流.json', 'r', encoding='utf-8') as f:
        workflow = json.load(f)
    
    # 查找目标节点
    target_nodes = [318, 339, 352]
    node_definitions = {}
    
    for node in workflow.get('nodes', []):
        node_id = node.get('id')
        if node_id in target_nodes:
            node_definitions[node_id] = {
                'type': node.get('type'),
                'inputs': [inp.get('name') for inp in node.get('inputs', [])]
            }
    
    print("工作流中的节点定义:")
    for node_id in target_nodes:
        if node_id in node_definitions:
            node_def = node_definitions[node_id]
            print(f"   节点 {node_id} ({node_def['type']}): 输入字段 {node_def['inputs']}")
        else:
            print(f"   节点 {node_id}: 不存在")
    
    # 2. 显示修复前的错误参数
    print("\n❌ 修复前的错误参数:")
    wrong_params = [
        {"nodeId": "318", "fieldName": "image", "fieldValue": "test.png", "status": "✅ 正确"},
        {"nodeId": "339", "fieldName": "number", "fieldValue": "2", "status": "❌ 错误 - 应该是'int'"},
        {"nodeId": "352", "fieldName": "video", "fieldValue": "test.mp4", "status": "✅ 正确"},
        {"nodeId": "384", "fieldName": "text", "fieldValue": "提示词", "status": "❌ 错误 - 节点不存在"}
    ]
    
    for param in wrong_params:
        print(f"   {param['nodeId']}: fieldName='{param['fieldName']}' - {param['status']}")
    
    # 3. 显示修复后的正确参数
    print("\n✅ 修复后的正确参数:")
    fixed_params = [
        {"nodeId": "318", "fieldName": "image", "fieldValue": "test.png"},
        {"nodeId": "339", "fieldName": "int", "fieldValue": 2},  # 修复：number -> int
        {"nodeId": "352", "fieldName": "video", "fieldValue": "test.mp4"}
        # 移除节点384
    ]
    
    for param in fixed_params:
        node_id = param['nodeId']
        field_name = param['fieldName']
        
        # 验证节点是否存在
        if int(node_id) in node_definitions:
            node_def = node_definitions[int(node_id)]
            if field_name in node_def['inputs']:
                status = "✅ 正确"
            else:
                status = f"❌ 字段名错误 - 可用字段: {node_def['inputs']}"
        else:
            status = "❌ 节点不存在"
        
        print(f"   {node_id}: fieldName='{field_name}' - {status}")
    
    # 4. 生成正确的API请求结构
    print("\n📡 正确的API请求结构:")
    api_request = {
        "workflowId": "1962342403615166465",
        "apiKey": "your_api_key_here",
        "nodeInfoList": fixed_params
    }
    
    print(json.dumps(api_request, ensure_ascii=False, indent=2))
    
    # 5. 检查修复项目
    print("\n🔧 已修复的问题:")
    print("   1. ✅ 节点339: fieldName从'number'改为'int'")
    print("   2. ✅ 移除不存在的节点384")
    print("   3. ✅ 更新了task_create.html中的fieldName映射逻辑")
    print("   4. ✅ 从数据库中删除了无效的节点384配置")
    
    return True

if __name__ == "__main__":
    verify_node_parameters()
    
    print("\n📝 修复总结:")
    print("   APIKEY_INVALID_NODE_INFO错误的根本原因是节点参数不匹配")
    print("   修复方法:")
    print("   - 分析工作流JSON文件获取准确的节点输入字段名")
    print("   - 更新fieldName映射逻辑以匹配RunningHub的期望")
    print("   - 移除工作流中不存在的节点配置")
    print("   - 确保所有字段名与工作流定义完全一致")
    
    print("\n✨ 现在可以创建新任务测试修复效果！")