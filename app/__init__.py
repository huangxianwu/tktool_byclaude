from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

db = SQLAlchemy()

def create_app():
    app = Flask(__name__, 
               template_folder='../templates',
               static_folder='../static')
    app.config.from_object(Config)
    
    db.init_app(app)
    
    with app.app_context():
        from . import models
        db.create_all()
        
        from .api import workflows, tasks, task_logs, outputs
        app.register_blueprint(workflows.bp)
        app.register_blueprint(tasks.bp)
        app.register_blueprint(task_logs.bp)
        app.register_blueprint(outputs.bp)
    
    # Import and register main routes
    from .routes import bp as main_bp
    app.register_blueprint(main_bp)
    
    return app