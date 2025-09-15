#!/usr/bin/env python3
from app import create_app
from app.models import Task

app = create_app()
with app.app_context():
    tasks = Task.query.limit(5).all()
    print('Available task IDs:')
    for task in tasks:
        desc = task.task_description[:50] if task.task_description else 'No description'
        print(f'- {task.task_id}: {desc}')
    
    if not tasks:
        print('No tasks found in database')