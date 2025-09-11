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
        outputs = TaskOutput.query.filter_by(task_id=task_id).all()
        
        result = []
        for output in outputs:
            result.append({
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
    
    def cleanup_old_files(self, days=30):
        """清理旧文件（可选功能）"""
        # TODO: 实现文件清理逻辑
        pass