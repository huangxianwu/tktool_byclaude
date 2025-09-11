from app import db

class TaskData(db.Model):
    __tablename__ = 'task_data'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(50), db.ForeignKey('tasks.task_id'), nullable=False)
    node_id = db.Column(db.String(50), nullable=False)
    field_name = db.Column(db.String(100), nullable=False)
    field_value = db.Column(db.Text)
    file_url = db.Column(db.Text)
    
    def to_dict(self):
        return {
            'id': self.id,
            'node_id': self.node_id,
            'field_name': self.field_name,
            'field_value': self.field_value,
            'file_url': self.file_url
        }