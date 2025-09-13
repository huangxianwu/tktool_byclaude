from app import db
from datetime import datetime

class TaskOutput(db.Model):
    __tablename__ = 'task_outputs'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(36), db.ForeignKey('tasks.task_id'), nullable=False)
    node_id = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(255), nullable=False)  # 文件名
    file_url = db.Column(db.Text, nullable=False)  # 原始RunningHub URL
    local_path = db.Column(db.Text, nullable=False)  # 本地存储路径
    thumbnail_path = db.Column(db.Text, nullable=True)  # 缩略图路径
    file_type = db.Column(db.String(10), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)  # 文件大小（字节）
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关联到任务 - 关系在Task模型中定义
    
    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'node_id': self.node_id,
            'name': self.name,
            'file_url': self.file_url,
            'local_path': self.local_path,
            'thumbnail_path': self.thumbnail_path,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }