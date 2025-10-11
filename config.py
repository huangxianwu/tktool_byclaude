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

    # Gemini API Keys: 支持多个API key自动切换
    GEMINI_API_KEYS = [
        'AIzaSyBwr0MWRyPPOUBUkId8NvBCPhmDffRmhGA' ,  # 主要API key
        'AIzaSyC0qrM3XmiG0-YhEa1ikc-03e-i8HJ6_Rs',  # 备用API key 1
        'AIzaSyBoaTRAzi_ARaZckF60hhLurvLtQoWH5To'#,  # 备用API key 2
        # 可以继续添加更多备用key
    ]
    
    # 当前使用的API key索引
    CURRENT_GEMINI_KEY_INDEX = 0
    
    # 从环境变量读取API keys（如果设置了的话）
    _env_keys = []
    if os.environ.get('GEMINI_API_KEY'):
        _env_keys.append(os.environ.get('GEMINI_API_KEY'))
    if os.environ.get('GOOGLE_API_KEY'):
        _env_keys.append(os.environ.get('GOOGLE_API_KEY'))
    if os.environ.get('GEMINI_API_KEY_2'):
        _env_keys.append(os.environ.get('GEMINI_API_KEY_2'))
    if os.environ.get('GEMINI_API_KEY_3'):
        _env_keys.append(os.environ.get('GEMINI_API_KEY_3'))
    
    # 如果环境变量中有API keys，则使用环境变量的，否则使用上面配置的
    if _env_keys:
        GEMINI_API_KEYS = _env_keys
    
    # 获取当前API key的方法
    @classmethod
    def get_current_gemini_key(cls):
        """获取当前使用的Gemini API key"""
        if cls.GEMINI_API_KEYS and cls.CURRENT_GEMINI_KEY_INDEX < len(cls.GEMINI_API_KEYS):
            return cls.GEMINI_API_KEYS[cls.CURRENT_GEMINI_KEY_INDEX]
        return None
    
    @classmethod
    def switch_to_next_gemini_key(cls):
        """切换到下一个可用的Gemini API key"""
        if len(cls.GEMINI_API_KEYS) > 1:
            cls.CURRENT_GEMINI_KEY_INDEX = (cls.CURRENT_GEMINI_KEY_INDEX + 1) % len(cls.GEMINI_API_KEYS)
            print(f"已切换到备用Gemini API key (索引: {cls.CURRENT_GEMINI_KEY_INDEX})")
            return cls.get_current_gemini_key()
        return None
    
    @classmethod
    def get_all_gemini_keys(cls):
        """获取所有配置的Gemini API keys"""
        return cls.GEMINI_API_KEYS.copy()
    
    @classmethod
    def reset_gemini_key_index(cls):
        """重置API key索引到第一个"""
        cls.CURRENT_GEMINI_KEY_INDEX = 0
    
    # 保持向后兼容性
    @property
    def GEMINI_API_KEY(self):
        """向后兼容的API key属性"""
        return self.get_current_gemini_key()
    
    # Task Management Configuration
    MAX_CONCURRENT_TASKS = 1  # 最大并发任务数
    TASK_TIMEOUT_MINUTES = 600  # 任务超时时间(分钟)
    STATUS_CHECK_INTERVAL = 10  # 状态检查间隔（秒）
    
    # 远程模式配置
    REMOTE_ONLY_MODE = True  # 纯远程模式，禁用本地文件下载和存储
    
    # Auto Editor Configuration
    AUTO_EDITOR_KEEP_LOCAL = os.environ.get('AUTO_EDITOR_KEEP_LOCAL', 'true').lower() == 'true'
    AUTO_EDITOR_RETENTION_HOURS = int(os.environ.get('AUTO_EDITOR_RETENTION_HOURS', '24'))
    
    # 以下配置项已移除（远程模式下不需要）：
    # SHOW_REMOTE_FILES_ONLY = True  # 默认只显示远程文件
    # AUTO_DOWNLOAD_ON_SUCCESS = False  # 任务成功后是否自动下载文件到本地
    # ENABLE_LOCAL_FILE_STORAGE = False  # 禁用本地存储