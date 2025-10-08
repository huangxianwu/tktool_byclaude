from flask import Blueprint, request, jsonify
from app import db
from app.models import Workflow, Node, Task
import uuid

bp = Blueprint('workflows', __name__, url_prefix='/api/workflows')

@bp.route('', methods=['GET'])
def get_workflows():
    """获取所有工作流模板"""
    status_filter = request.args.get('status')
    workflow_id_filter = request.args.get('workflow_id')
    
    # 构建查询条件
    query = Workflow.query
    
    # 工作流ID精准匹配（优先级最高）
    if workflow_id_filter and workflow_id_filter.strip():
        query = query.filter_by(workflow_id=workflow_id_filter.strip())
    
    # 状态筛选
    if status_filter and status_filter in ['active', 'inactive']:
        query = query.filter_by(status=status_filter)
    
    # 排序：置顶优先，且按置顶时间倒序，其次创建时间倒序
    query = query.order_by(Workflow.pinned.desc(), Workflow.pinned_at.desc(), Workflow.created_at.desc())
    workflows = query.all()
    
    # 为每个工作流添加关联任务数量统计
    result = []
    for wf in workflows:
        wf_dict = wf.to_dict()
        # 统计该工作流的所有任务数量（不论状态）
        task_count = Task.query.filter_by(workflow_id=wf.workflow_id).count()
        wf_dict['task_count'] = task_count
        result.append(wf_dict)
    
    return jsonify(result)

@bp.route('/<workflow_id>/pin', methods=['PATCH'])
def pin_workflow(workflow_id):
    """置顶或取消置顶工作流模板"""
    from datetime import datetime
    workflow = Workflow.query.get_or_404(workflow_id)
    data = request.get_json(silent=True) or {}
    pin = data.get('pin', True)
    workflow.pinned = bool(pin)
    workflow.pinned_at = datetime.utcnow() if workflow.pinned else None
    db.session.commit()
    return jsonify({
        'message': 'Workflow pinned' if workflow.pinned else 'Workflow unpinned',
        'workflow': workflow.to_dict()
    })

@bp.route('', methods=['POST'])
def create_workflow():
    """创建工作流模板"""
    try:
        data = request.get_json()
        print(f"DEBUG: Received data: {data}")
        
        if not data or 'name' not in data:
            print("DEBUG: Missing workflow name")
            return jsonify({'error': 'Missing workflow name'}), 400
        
        # 使用用户提供的ID或生成唯一ID
        workflow_id = data.get('workflow_id', str(uuid.uuid4()))
        
        # 检查ID是否已存在
        existing_workflow = Workflow.query.get(workflow_id)
        if existing_workflow:
            print(f"DEBUG: Workflow ID already exists: {workflow_id}")
            return jsonify({'error': 'Workflow ID already exists'}), 400
        
        workflow = Workflow(
            workflow_id=workflow_id, 
            name=data['name'],
            description=data.get('description', '')  # 支持描述字段
        )
        db.session.add(workflow)
        
        # 添加节点
        if 'nodes' in data:
            for node_data in data['nodes']:
                print(f"DEBUG: Processing node: {node_data}")
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
        print("DEBUG: Workflow created successfully")
        
        return jsonify(workflow.to_dict()), 201
        
    except Exception as e:
        print(f"DEBUG: Error creating workflow: {str(e)}")
        db.session.rollback()
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

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
    
    if 'description' in data:
        workflow.description = data['description']
    
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