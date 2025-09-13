from app import db
from datetime import datetime

class Task(db.Model):
    __tablename__ = 'tasks'
    
    task_id = db.Column(db.String(50), primary_key=True)
    workflow_id = db.Column(db.String(50), db.ForeignKey('workflows.workflow_id'), nullable=False)
    status = db.Column(db.String(20), default='READY')  # READY, PENDING, QUEUED, RUNNING, SUCCESS, FAILED, STOPPED
    runninghub_task_id = db.Column(db.String(50))
    task_description = db.Column(db.Text)  # 任务描述
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    timeout_at = db.Column(db.DateTime)  # 超时时间
    started_at = db.Column(db.DateTime)  # 开始执行时间
    completed_at = db.Column(db.DateTime)  # 完成时间
    is_plus = db.Column(db.Boolean, default=False)  # 是否使用Plus实例
    
    # 关系定义
    workflow = db.relationship('Workflow', backref='tasks', lazy=True)
    data = db.relationship('TaskData', backref='task', lazy=True, cascade='all, delete-orphan')
    logs = db.relationship('TaskLog', backref='task', lazy=True, cascade='all, delete-orphan')
    outputs = db.relationship('TaskOutput', backref='task', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'task_id': self.task_id,
            'workflow_id': self.workflow_id,
            'status': self.status,
            'runninghub_task_id': self.runninghub_task_id,
            'task_description': self.task_description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'timeout_at': self.timeout_at.isoformat() if self.timeout_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'is_plus': self.is_plus
        }