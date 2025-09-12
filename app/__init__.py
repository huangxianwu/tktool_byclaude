import threading
import time
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_socketio import SocketIO
from config import Config

db = SQLAlchemy()
migrate = Migrate()
socketio = SocketIO(cors_allowed_origins="*")

def create_app(config_class=Config):
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.config.from_object(config_class)
    
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app)
    socketio.init_app(app)
    
    # 注册蓝图
    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)
    
    from app.api.tasks import bp as tasks_bp
    app.register_blueprint(tasks_bp)
    
    from app.api.monitoring import bp as monitoring_bp
    app.register_blueprint(monitoring_bp)
    
    from app.api.workflows import bp as workflows_bp
    app.register_blueprint(workflows_bp)
    
    from app.api.outputs import bp as outputs_bp
    app.register_blueprint(outputs_bp)
    
    from app.api.task_logs import bp as task_logs_bp
    app.register_blueprint(task_logs_bp)
    
    # 配置静态文件服务 - 为outputs目录提供静态文件访问
    from flask import send_from_directory
    import os
    
    @app.route('/static/outputs/<path:filename>')
    def serve_output_files(filename):
        outputs_dir = app.config.get('OUTPUT_FILES_DIR', 'outputs')
        return send_from_directory(outputs_dir, filename)
    
    # 在应用上下文中启动后台任务检查
    def start_background_tasks():
        with app.app_context():
            # 导入服务
            from app.services.task_queue_service import task_queue_service
            from app.services.monitoring_service import monitoring_service
            from app.services.status_monitor import status_monitor
            from app.services.task_status_service import TaskStatusService
            
            # 初始化状态监控服务
            from app.services.status_monitor import init_status_monitor
            status_monitor = init_status_monitor(socketio)
            
            # 启动任务状态监控服务
            task_status_service = TaskStatusService()
            task_status_service.app = app  # 传递应用实例
            task_status_service.start_monitoring()
            
            # 启动后台任务检查
            def background_task_checker():
                """后台任务检查器 - 定期检查超时任务和处理队列"""
                while True:
                    try:
                        with app.app_context():
                            # 检查超时任务
                            task_queue_service.check_timeout_tasks()
                            
                            # 处理队列
                            task_queue_service.process_queue()
                            
                            # 广播系统状态更新
                            status_monitor.broadcast_system_status()
                            
                            # 运行健康检查和告警（每5分钟运行一次）
                            current_time = time.time()
                            if not hasattr(background_task_checker, 'last_health_check'):
                                background_task_checker.last_health_check = 0
                                
                            if current_time - background_task_checker.last_health_check >= 300:  # 5分钟
                                monitoring_service.load_config()
                                health_status = monitoring_service.run_health_check_and_alert()
                                # 广播健康状态
                                status_monitor.broadcast_health_status(health_status)
                                background_task_checker.last_health_check = current_time
                            
                            # 等待30秒
                            time.sleep(30)
                            
                    except Exception as e:
                        print(f"Background task checker error: {e}")
                        # 出错时等待更长时间
                        time.sleep(60)
            
            # 启动后台线程
            background_thread = threading.Thread(target=background_task_checker, daemon=True)
            background_thread.start()
    
    # 延迟启动后台任务
    threading.Timer(2.0, start_background_tasks).start()
    
    return app

from app import models