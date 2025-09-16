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
    
    # 远程模式配置
    REMOTE_ONLY_MODE = True  # 纯远程模式，禁用本地文件下载和存储
    
    # 以下配置项已移除（远程模式下不需要）：
    # SHOW_REMOTE_FILES_ONLY = True  # 默认只显示远程文件
    # AUTO_DOWNLOAD_ON_SUCCESS = False  # 任务成功后是否自动下载文件到本地
    # ENABLE_LOCAL_FILE_STORAGE = False  # 禁用本地存储