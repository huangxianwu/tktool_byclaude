from app import db
from datetime import datetime

class Workflow(db.Model):
    __tablename__ = 'workflows'
    
    workflow_id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    nodes = db.relationship('Node', backref='workflow', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'workflow_id': self.workflow_id,
            'name': self.name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'nodes': [node.to_dict() for node in self.nodes]
        }