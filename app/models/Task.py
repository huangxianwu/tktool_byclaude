from app import db
from datetime import datetime

class Task(db.Model):
    __tablename__ = 'tasks'
    
    task_id = db.Column(db.String(50), primary_key=True)
    workflow_id = db.Column(db.String(50), db.ForeignKey('workflows.workflow_id'), nullable=False)
    status = db.Column(db.String(20), default='PENDING')  # PENDING, RUNNING, SUCCESS, FAILED
    runninghub_task_id = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    data = db.relationship('TaskData', backref='task', lazy=True, cascade='all, delete-orphan')
    logs = db.relationship('TaskLog', backref='task', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'task_id': self.task_id,
            'workflow_id': self.workflow_id,
            'status': self.status,
            'runninghub_task_id': self.runninghub_task_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }