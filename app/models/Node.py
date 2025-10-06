from app import db

class Node(db.Model):
    __tablename__ = 'nodes'
    
    id = db.Column(db.Integer, primary_key=True)
    workflow_id = db.Column(db.String(50), db.ForeignKey('workflows.workflow_id'), nullable=False)
    node_id = db.Column(db.String(50), nullable=False)
    node_name = db.Column(db.String(100), nullable=False)
    node_type = db.Column(db.String(50), nullable=False)  # 'image', 'video', 'file', 'text', 'number', 'audio'
    
    def to_dict(self):
        return {
            'id': self.id,
            'node_id': self.node_id,
            'node_name': self.node_name,
            'node_type': self.node_type
        }