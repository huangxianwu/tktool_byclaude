from flask import Blueprint, request, jsonify
from app import db
from app.models import Workflow, Node, Task
import uuid

bp = Blueprint('workflows', __name__, url_prefix='/api/workflows')

@bp.route('', methods=['GET'])
def get_workflows():
    """获取所有工作流模板"""
    status_filter = request.args.get('status')
    
    if status_filter and status_filter in ['active', 'inactive']:
        workflows = Workflow.query.filter_by(status=status_filter).all()
    else:
        workflows = Workflow.query.all()
    
    # 为每个工作流添加关联任务数量统计
    result = []
    for wf in workflows:
        wf_dict = wf.to_dict()
        # 统计该工作流的所有任务数量（不论状态）
        task_count = Task.query.filter_by(workflow_id=wf.workflow_id).count()
        wf_dict['task_count'] = task_count
        result.append(wf_dict)
    
    return jsonify(result)

@bp.route('', methods=['POST'])
def create_workflow():
    """创建工作流模板"""
    data = request.get_json()
    
    if not data or 'name' not in data:
        return jsonify({'error': 'Missing workflow name'}), 400
    
    # 使用用户提供的ID或生成唯一ID
    workflow_id = data.get('workflow_id', str(uuid.uuid4()))
    
    # 检查ID是否已存在
    existing_workflow = Workflow.query.get(workflow_id)
    if existing_workflow:
        return jsonify({'error': 'Workflow ID already exists'}), 400
    
    workflow = Workflow(workflow_id=workflow_id, name=data['name'])
    db.session.add(workflow)
    
    # 添加节点
    if 'nodes' in data:
        for node_data in data['nodes']:
            # 处理节点ID：如果为空或未提供，则自动生成
            node_id = node_data.get('node_id')
            if not node_id or not node_id.strip():
                node_id = str(uuid.uuid4())
            
            node = Node(
                workflow_id=workflow_id,
                node_id=node_id,
                node_name=node_data['node_name'],
                node_type=node_data['node_type']
            )
            db.session.add(node)
    
    db.session.commit()
    
    return jsonify(workflow.to_dict()), 201

@bp.route('/<workflow_id>', methods=['GET'])
def get_workflow(workflow_id):
    """获取特定工作流模板"""
    workflow = Workflow.query.get_or_404(workflow_id)
    return jsonify(workflow.to_dict())

@bp.route('/<workflow_id>', methods=['PUT'])
def update_workflow(workflow_id):
    """更新工作流模板"""
    workflow = Workflow.query.get_or_404(workflow_id)
    data = request.get_json()
    
    if 'name' in data:
        workflow.name = data['name']
    
    if 'status' in data:
        workflow.status = data['status']
    
    # 更新节点
    if 'nodes' in data:
        # 删除现有节点
        Node.query.filter_by(workflow_id=workflow_id).delete()
        
        # 添加新节点
        for node_data in data['nodes']:
            # 处理节点ID：如果为空或未提供，则自动生成
            node_id = node_data.get('node_id')
            if not node_id or not node_id.strip():
                node_id = str(uuid.uuid4())
            
            node = Node(
                workflow_id=workflow_id,
                node_id=node_id,
                node_name=node_data['node_name'],
                node_type=node_data['node_type']
            )
            db.session.add(node)
    
    db.session.commit()
    
    return jsonify(workflow.to_dict())

@bp.route('/<workflow_id>', methods=['DELETE'])
def delete_workflow(workflow_id):
    """删除工作流模板"""
    workflow = Workflow.query.get_or_404(workflow_id)
    db.session.delete(workflow)
    db.session.commit()
    
    return jsonify({'message': 'Workflow deleted'})

@bp.route('/<workflow_id>/toggle-status', methods=['PATCH'])
def toggle_workflow_status(workflow_id):
    """切换工作流状态"""
    workflow = Workflow.query.get_or_404(workflow_id)
    
    # 切换状态
    workflow.status = 'inactive' if workflow.status == 'active' else 'active'
    db.session.commit()
    
    return jsonify({
        'message': f'Workflow status changed to {workflow.status}',
        'workflow': workflow.to_dict()
    })