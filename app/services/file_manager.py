import os
import requests
import hashlib
from datetime import datetime
from urllib.parse import urlparse, unquote
from PIL import Image
import io
from flask import current_app
from app.models import TaskOutput
from app import db

class FileManager:
    def __init__(self):
        self.base_dir = current_app.config.get('OUTPUT_FILES_DIR', 'outputs')
        self.static_url_prefix = '/static/outputs'
        
        # 确保目录存在
        os.makedirs(os.path.join(self.base_dir, 'images'), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, 'images', 'thumbnails'), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, 'videos'), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, 'documents'), exist_ok=True)
    
    def download_and_save_outputs(self, task_id, outputs):
        """下载并保存任务输出文件"""
        saved_files = []
        
        for i, output in enumerate(outputs):
            try:
                file_url = output.get('fileUrl')
                file_type = output.get('fileType', 'png')
                node_id = output.get('nodeId', '')
                
                if not file_url:
                    continue
                
                # 下载文件
                response = requests.get(file_url, timeout=30)
                if response.status_code != 200:
                    current_app.logger.error(f"Failed to download {file_url}: {response.status_code}")
                    continue
                
                # 生成本地文件路径
                local_path = self._generate_local_path(task_id, file_type, i, node_id)
                
                # 保存原始文件
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                
                # 生成缩略图（仅图片）
                thumbnail_path = None
                if file_type.lower() in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp']:
                    thumbnail_path = self._generate_thumbnail(local_path, task_id, i, node_id)
                
                # 保存到数据库
                task_output = TaskOutput(
                    task_id=task_id,
                    node_id=node_id,
                    file_url=file_url,
                    local_path=local_path,
                    thumbnail_path=thumbnail_path,
                    file_type=file_type,
                    file_size=len(response.content)
                )
                db.session.add(task_output)
                
                saved_files.append({
                    'original_url': file_url,
                    'local_path': local_path,
                    'thumbnail_path': thumbnail_path,
                    'file_type': file_type,
                    'node_id': node_id,
                    'static_url': self._get_static_url(local_path),
                    'thumbnail_url': self._get_static_url(thumbnail_path) if thumbnail_path else None
                })
                
            except Exception as e:
                current_app.logger.error(f"Error processing output {i}: {str(e)}")
                continue
        
        db.session.commit()
        return saved_files
    
    def _generate_local_path(self, task_id, file_type, index, node_id):
        """生成本地文件路径"""
        now = datetime.now()
        year_month = now.strftime('%Y/%m')
        
        # 根据文件类型选择目录
        if file_type.lower() in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp']:
            base_dir = os.path.join(self.base_dir, 'images', year_month)
        elif file_type.lower() in ['mp4', 'avi', 'mov', 'wmv', 'flv']:
            base_dir = os.path.join(self.base_dir, 'videos', year_month)
        else:
            base_dir = os.path.join(self.base_dir, 'documents', year_month)
        
        filename = f"task_{task_id}_node_{node_id}_output_{index}.{file_type}"
        return os.path.join(base_dir, filename)
    
    def _generate_thumbnail(self, image_path, task_id, index, node_id, size=(270, 480)):
        """生成缩略图"""
        try:
            now = datetime.now()
            year_month = now.strftime('%Y/%m')
            
            thumbnail_dir = os.path.join(self.base_dir, 'images', 'thumbnails', year_month)
            os.makedirs(thumbnail_dir, exist_ok=True)
            
            thumbnail_filename = f"task_{task_id}_node_{node_id}_output_{index}_thumb.jpg"
            thumbnail_path = os.path.join(thumbnail_dir, thumbnail_filename)
            
            # 使用PIL生成9:16比例的缩略图
            with Image.open(image_path) as img:
                # 转换为RGB（处理RGBA和其他格式）
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # 计算9:16比例的智能裁剪
                target_width, target_height = size  # (270, 480)
                target_ratio = target_width / target_height  # 9:16 = 0.5625
                
                original_width, original_height = img.size
                original_ratio = original_width / original_height
                
                if original_ratio > target_ratio:
                    # 原图更宽，需要裁剪宽度
                    new_width = int(original_height * target_ratio)
                    left = (original_width - new_width) // 2
                    crop_box = (left, 0, left + new_width, original_height)
                else:
                    # 原图更高，需要裁剪高度
                    new_height = int(original_width / target_ratio)
                    top = (original_height - new_height) // 2
                    crop_box = (0, top, original_width, top + new_height)
                
                # 裁剪并调整大小
                cropped_img = img.crop(crop_box)
                thumbnail = cropped_img.resize(size, Image.Resampling.LANCZOS)
                thumbnail.save(thumbnail_path, 'JPEG', quality=85)
                
            return thumbnail_path
            
        except Exception as e:
            current_app.logger.error(f"Error generating thumbnail: {str(e)}")
            return None
    
    def _get_static_url(self, local_path):
        """将本地路径转换为静态文件URL"""
        if not local_path:
            return None
        
        # 将绝对路径转换为相对于outputs目录的路径
        relative_path = os.path.relpath(local_path, self.base_dir)
        return f"{self.static_url_prefix}/{relative_path}".replace('\\', '/')
    
    def get_task_outputs(self, task_id):
        """获取任务的输出文件列表"""
        print(f"DEBUG FileManager: Querying outputs for task_id: {task_id}")
        outputs = TaskOutput.query.filter_by(task_id=task_id).all()
        print(f"DEBUG FileManager: Query returned {len(outputs)} outputs")
        
        result = []
        for output in outputs:
            # 生成文件名
            filename = f"node_{output.node_id}_output.{output.file_type}"
            
            # 优先使用本地文件URL，如果本地文件不存在则使用原始URL
            local_url = self._get_static_url(output.local_path)
            file_url = local_url if local_url and os.path.exists(output.local_path) else output.file_url
            
            result.append({
                'name': filename,
                'url': file_url,
                'id': output.id,
                'node_id': output.node_id,
                'file_url': output.file_url,
                'local_path': output.local_path,
                'thumbnail_path': output.thumbnail_path,
                'file_type': output.file_type,
                'file_size': output.file_size,
                'static_url': self._get_static_url(output.local_path),
                'thumbnail_url': self._get_static_url(output.thumbnail_path),
                'created_at': output.created_at.isoformat() if output.created_at else None
            })
        
        return result
    
    def get_task_outputs_with_fallback(self, task_id):
        """获取任务输出文件列表，如果没有本地记录则从RunningHub获取并补充字段"""
        # 先尝试获取本地记录
        local_outputs = self.get_task_outputs(task_id)
        if local_outputs:
            return local_outputs
        
        # 如果没有本地记录，从RunningHub获取并补充必要字段
        from app.models.Task import Task
        task = Task.query.get(task_id)
        if not task or not task.runninghub_task_id:
            return []
        
        try:
            from app.services.runninghub import RunningHubService
            runninghub_service = RunningHubService()
            remote_outputs = runninghub_service.get_task_outputs(task.runninghub_task_id)
            
            # 补充前端需要的字段
            result = []
            for i, output in enumerate(remote_outputs):
                # 从URL推断文件类型
                file_url = output.get('url', '')
                file_name = output.get('name', 'output.file')
                file_extension = file_name.split('.')[-1].lower() if '.' in file_name else 'unknown'
                
                result.append({
                    'name': file_name,
                    'url': file_url,
                    'id': None,
                    'node_id': f'node_{i}',
                    'file_url': file_url,
                    'local_path': None,
                    'thumbnail_path': None,
                    'file_type': file_extension,
                    'file_size': None,
                    'static_url': file_url,  # 直接使用远程URL
                    'thumbnail_url': file_url if file_extension.lower() in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'] else None,
                    'created_at': None
                })
            
            return result
            
        except Exception as e:
            current_app.logger.error(f"Error getting remote outputs for task {task_id}: {e}")
            return []
    
    def save_output_file(self, task_id, file_name, file_url, file_type='file'):
        """保存单个输出文件"""
        try:
            if not file_url or not file_name:
                return None
            
            # 下载文件
            response = requests.get(file_url, timeout=30)
            if response.status_code != 200:
                current_app.logger.error(f"Failed to download {file_url}: {response.status_code}")
                return None
            
            # 确定文件扩展名
            file_ext = os.path.splitext(file_name)[1] or '.png'
            
            # 生成本地文件路径
            if file_type in ['image', 'png', 'jpg', 'jpeg', 'gif']:
                local_dir = os.path.join(self.base_dir, 'images', task_id)
            elif file_type in ['video', 'mp4', 'avi', 'mov']:
                local_dir = os.path.join(self.base_dir, 'videos', task_id)
            else:
                local_dir = os.path.join(self.base_dir, 'documents', task_id)
            
            os.makedirs(local_dir, exist_ok=True)
            
            # 生成唯一文件名
            base_name = os.path.splitext(file_name)[0]
            local_path = os.path.join(local_dir, f"{base_name}{file_ext}")
            
            # 如果文件已存在，添加序号
            counter = 1
            while os.path.exists(local_path):
                local_path = os.path.join(local_dir, f"{base_name}_{counter}{file_ext}")
                counter += 1
            
            # 保存文件
            with open(local_path, 'wb') as f:
                f.write(response.content)
            
            # 生成缩略图（仅图片）
            thumbnail_path = None
            if file_type in ['image', 'png', 'jpg', 'jpeg', 'gif']:
                try:
                    thumbnail_path = self._generate_thumbnail_for_file(local_path, task_id)
                except Exception as thumb_error:
                    current_app.logger.warning(f"Failed to generate thumbnail for {local_path}: {thumb_error}")
            
            # 保存到数据库
            file_size = len(response.content)
            static_url = self._get_static_url(local_path)
            thumbnail_url = self._get_static_url(thumbnail_path) if thumbnail_path else None
            
            # 检查是否已存在相同的输出记录
            existing_output = TaskOutput.query.filter_by(
                task_id=task_id,
                name=os.path.basename(local_path)
            ).first()
            
            if existing_output:
                # 更新现有记录
                existing_output.file_url = file_url
                existing_output.local_path = local_path
                existing_output.file_type = file_type
                existing_output.file_size = file_size
                existing_output.thumbnail_path = thumbnail_path
                existing_output.created_at = datetime.now()
                task_output = existing_output
            else:
                # 创建新记录
                task_output = TaskOutput(
                    task_id=task_id,
                    node_id='',  # 默认空值，可以后续更新
                    name=os.path.basename(local_path),
                    file_url=file_url,
                    local_path=local_path,
                    thumbnail_path=thumbnail_path,
                    file_type=file_type,
                    file_size=file_size
                )
                db.session.add(task_output)
            
            db.session.commit()
            
            current_app.logger.info(f"Successfully saved file: {local_path}")
            return task_output
            
        except Exception as e:
            current_app.logger.error(f"Error saving output file {file_name}: {e}")
            db.session.rollback()
            return None
    
    def _generate_thumbnail_for_file(self, image_path, task_id, size=(270, 480)):
        """为单个文件生成缩略图"""
        try:
            with Image.open(image_path) as img:
                # 转换为RGB模式（处理RGBA等格式）
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # 创建缩略图
                img.thumbnail(size, Image.Resampling.LANCZOS)
                
                # 生成缩略图路径
                thumbnail_dir = os.path.join(self.base_dir, 'images', 'thumbnails', task_id)
                os.makedirs(thumbnail_dir, exist_ok=True)
                
                filename = os.path.basename(image_path)
                name, ext = os.path.splitext(filename)
                thumbnail_path = os.path.join(thumbnail_dir, f"{name}_thumb.jpg")
                
                # 保存缩略图
                img.save(thumbnail_path, 'JPEG', quality=85, optimize=True)
                
                return thumbnail_path
                
        except Exception as e:
            current_app.logger.error(f"Error generating thumbnail for {image_path}: {e}")
            return None
    
    def cleanup_old_files(self, days=30):
        """清理旧文件"""
        # TODO: 实现文件清理逻辑
        pass