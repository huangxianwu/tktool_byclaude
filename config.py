import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{os.path.abspath("instance/app.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # RunningHub API Configuration
    RUNNINGHUB_BASE_URL = 'https://www.runninghub.cn/task/openapi'
    RUNNINGHUB_API_KEY = 'd4b17e6ea9474695965f3f3c9dd53c1d'
    
    # File upload settings
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'avi', 'mov', 'mkv', 'mp3', 'wav', 'zip'}
    
    # Output files settings
    OUTPUT_FILES_DIR = 'static/outputs'
    
    # Task Management Configuration
    MAX_CONCURRENT_TASKS = 1  # 最大并发任务数
    TASK_TIMEOUT_MINUTES = 600  # 任务超时时间(分钟)
    STATUS_CHECK_INTERVAL = 10  # 状态检查间隔（秒）