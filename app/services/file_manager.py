import os
import requests
import hashlib
from datetime import datetime
from urllib.parse import urlparse, unquote
from PIL import Image
import io
from flask import current_app
from app.models import TaskOutput, Task
from app import db
import re
import subprocess
import tempfile

class FileManager:
    def __init__(self):
        # 在远程模式下，不需要本地目录
        self.remote_only_mode = current_app.config.get('REMOTE_ONLY_MODE', False)
        if not self.remote_only_mode:
            self.base_dir = current_app.config.get('OUTPUT_FILES_DIR', 'outputs')
            self.static_url_prefix = '/static/outputs'
            # 确保目录存在
            os.makedirs(os.path.join(self.base_dir, 'images'), exist_ok=True)
            os.makedirs(os.path.join(self.base_dir, 'images', 'thumbnails'), exist_ok=True)
            os.makedirs(os.path.join(self.base_dir, 'videos'), exist_ok=True)
            os.makedirs(os.path.join(self.base_dir, 'documents'), exist_ok=True)
    
    def get_remote_task_outputs(self, task_id):
        """获取任务的远程输出文件列表（纯远程模式）"""
        # 先尝试获取本地记录（仅获取远程URL信息）
        local_outputs = TaskOutput.query.filter_by(task_id=task_id).all()
        if local_outputs:
            result = []
            for output in local_outputs:
                result.append({
                    'name': output.name or f"output_{output.id}.{output.file_type}",
                    'url': output.file_url,  # 直接使用远程URL
                    'id': output.id,
                    'node_id': output.node_id,
                    'file_url': output.file_url,
                    'file_type': output.file_type,
                    'file_size': output.file_size,
                    'source': 'remote',
                    'is_local': False,
                    'created_at': output.created_at.isoformat() if output.created_at else None
                })
            return result
        
        # 如果没有本地记录，从RunningHub获取
        from app.models.Task import Task
        task = Task.query.get(task_id)
        if not task or not task.runninghub_task_id:
            return []
        
        try:
            from app.services.runninghub import RunningHubService
            runninghub_service = RunningHubService()
            remote_outputs = runninghub_service.get_task_outputs(task.runninghub_task_id)
            
            # 补充前端需要的字段（纯远程文件信息）
            result = []
            for i, output in enumerate(remote_outputs):
                file_url = output.get('url', '')
                file_name = output.get('name', f'output_{i}.file')
                file_size = output.get('size', 0)
                
                # 从URL推断文件类型
                file_extension = 'png'
                if file_name and '.' in file_name:
                    file_extension = file_name.split('.')[-1].lower()
                elif file_url:
                    parsed_url = urlparse(file_url)
                    path = unquote(parsed_url.path)
                    if '.' in path:
                        file_extension = path.split('.')[-1].lower()
                
                result.append({
                    'name': file_name,
                    'url': file_url,
                    'id': f'remote_{i}',
                    'node_id': f'node_{i}',
                    'file_url': file_url,
                    'file_type': file_extension,
                    'file_size': file_size,
                    'source': 'remote',
                    'is_local': False,
                    'created_at': datetime.now().isoformat()
                })
            
            return result
            
        except Exception as e:
            current_app.logger.error(f"Error getting remote outputs for task {task_id}: {e}")
            return []

    def download_and_save_outputs(self, task_id, outputs):
        """下载并保存任务输出文件"""
        # 在远程模式下，跳过本地文件下载
        if self.remote_only_mode:
            current_app.logger.info(f"Skipping file download for task {task_id} - remote only mode enabled")
            return []
        
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
                
                # 生成原始文件名（用于生成自定义文件名）
                original_filename = f"node_{node_id}_output_{i}.{file_type}"
                
                # 生成自定义文件名（传递索引确保唯一性）
                custom_filename = self._generate_custom_filename(task_id, original_filename, i)
                
                # 生成本地文件路径（使用自定义文件名）
                local_path = self._generate_local_path_with_custom_name(task_id, custom_filename, file_type)
                
                # 保存原始文件
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                
                # 生成缩略图（仅图片）
                thumbnail_path = None
                if file_type.lower() in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp']:
                    thumbnail_path = self._generate_thumbnail_with_custom_name(local_path, task_id, custom_filename)
                elif file_type.lower() in ['mp4', 'avi', 'mov', 'wmv', 'flv', 'webm']:
                    thumbnail_path = self._generate_video_thumbnail_with_custom_name(local_path, task_id, custom_filename)
        
                # 保存到数据库（使用自定义文件名）
                task_output = TaskOutput(
                    task_id=task_id,
                    node_id=node_id,
                    name=custom_filename,  # 使用自定义文件名
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
        # 在远程模式下，不生成本地路径
        if self.remote_only_mode:
            return ""
            
        now = datetime.now()
        date_str = now.strftime('%m%d')  # 格式如：0913
        
        # 根据文件类型选择目录
        if file_type.lower() in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp']:
            base_dir = os.path.join(self.base_dir, 'images', date_str)
        elif file_type.lower() in ['mp4', 'avi', 'mov', 'wmv', 'flv']:
            base_dir = os.path.join(self.base_dir, 'videos', date_str)
        else:
            base_dir = os.path.join(self.base_dir, 'documents', date_str)
        
        filename = f"task_{task_id}_node_{node_id}_output_{index}.{file_type}"
        return os.path.join(base_dir, filename)
    
    def _generate_local_path_with_custom_name(self, task_id, custom_filename, file_type):
        """使用自定义文件名生成本地文件路径"""
        # 在远程模式下，不生成本地路径
        if self.remote_only_mode:
            return ""
            
        now = datetime.now()
        date_str = now.strftime('%m%d')  # 格式如：0913
        
        # 根据文件类型选择目录
        if file_type.lower() in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp']:
            base_dir = os.path.join(self.base_dir, 'images', date_str)
        elif file_type.lower() in ['mp4', 'avi', 'mov', 'wmv', 'flv']:
            base_dir = os.path.join(self.base_dir, 'videos', date_str)
        else:
            base_dir = os.path.join(self.base_dir, 'documents', date_str)
        
        return os.path.join(base_dir, custom_filename)
    
    def _generate_thumbnail(self, image_path, task_id, index, node_id, size=(270, 480)):
        """生成缩略图"""
        try:
            now = datetime.now()
            date_str = now.strftime('%m%d')  # 格式如：0913
            
            thumbnail_dir = os.path.join(self.base_dir, 'images', 'thumbnails', date_str)
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
                
                # 计算缩放比例以适应目标尺寸
                img_ratio = img.width / img.height
                target_ratio = size[0] / size[1]
                
                if img_ratio > target_ratio:
                    # 图片更宽，以高度为准
                    new_height = size[1]
                    new_width = int(new_height * img_ratio)
                else:
                    # 图片更高，以宽度为准
                    new_width = size[0]
                    new_height = int(new_width / img_ratio)
                
                # 缩放图片
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # 创建目标尺寸的画布并居中放置图片
                canvas = Image.new('RGB', size, (255, 255, 255))
                x = (size[0] - new_width) // 2
                y = (size[1] - new_height) // 2
                canvas.paste(img, (x, y))
                
                # 保存缩略图
                canvas.save(thumbnail_path, 'JPEG', quality=85)
                
            return thumbnail_path
            
        except Exception as e:
            current_app.logger.error(f"Failed to generate thumbnail for {image_path}: {str(e)}")
            return None
    
    def _generate_thumbnail_with_custom_name(self, image_path, task_id, custom_filename, size=(270, 480)):
        """使用自定义文件名生成缩略图"""
        try:
            now = datetime.now()
            date_str = now.strftime('%m%d')  # 格式如：0913
            
            thumbnail_dir = os.path.join(self.base_dir, 'images', 'thumbnails', date_str)
            os.makedirs(thumbnail_dir, exist_ok=True)
            
            # 从自定义文件名生成缩略图文件名
            name_without_ext = os.path.splitext(custom_filename)[0]
            thumbnail_filename = f"{name_without_ext}_thumb.jpg"
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
                
                # 计算缩放比例以适应目标尺寸
                img_ratio = img.width / img.height
                target_ratio = size[0] / size[1]
                
                if img_ratio > target_ratio:
                    # 图片更宽，以高度为准
                    new_height = size[1]
                    new_width = int(new_height * img_ratio)
                else:
                    # 图片更高，以宽度为准
                    new_width = size[0]
                    new_height = int(new_width / img_ratio)
                
                # 缩放图片
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # 创建目标尺寸的画布并居中放置图片
                canvas = Image.new('RGB', size, (255, 255, 255))
                x = (size[0] - new_width) // 2
                y = (size[1] - new_height) // 2
                canvas.paste(img, (x, y))
                
                # 保存缩略图
                canvas.save(thumbnail_path, 'JPEG', quality=85)
                
            return thumbnail_path
            
        except Exception as e:
            current_app.logger.error(f"Failed to generate thumbnail for {image_path}: {str(e)}")
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
        current_app.logger.debug(f"Querying outputs for task_id: {task_id}")
        outputs = TaskOutput.query.filter_by(task_id=task_id).all()
        current_app.logger.debug(f"Query returned {len(outputs)} outputs")
        
        result = []
        for output in outputs:
            # 使用数据库中存储的自定义文件名，如果没有则生成默认文件名
            if hasattr(output, 'name') and output.name:
                filename = output.name
            else:
                # 为历史数据生成自定义文件名
                original_filename = f"node_{output.node_id}_output.{output.file_type}"
                filename = self._generate_custom_filename(task_id, original_filename)
            
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
    
    def get_task_outputs_with_fallback(self, task_id, auto_download=True):
        """获取任务输出文件列表，远程模式下直接调用get_remote_task_outputs"""
        if self.remote_only_mode:
            return self.get_remote_task_outputs(task_id)
        
        # 传统模式保持不变（向后兼容）
        # 先尝试获取本地记录
        local_outputs = self.get_task_outputs(task_id)
        if local_outputs:
            # 为本地文件添加source标识
            for output in local_outputs:
                output['source'] = 'local'
                output['is_local'] = True
            return local_outputs
        
        # 如果没有本地记录，从RunningHub获取
        from app.models.Task import Task
        task = Task.query.get(task_id)
        if not task or not task.runninghub_task_id:
            return []
        
        try:
            from app.services.runninghub import RunningHubService
            runninghub_service = RunningHubService()
            remote_outputs = runninghub_service.get_task_outputs(task.runninghub_task_id)
            
            # 补充前端需要的字段（用于显示远程文件）
            result = []
            for i, output in enumerate(remote_outputs):
                file_url = output.get('url', '')
                file_name = output.get('name', f'output_{i}.file')
                file_size = output.get('size', 0)
                
                # 从URL推断文件类型
                file_extension = 'png'
                if file_name and '.' in file_name:
                    file_extension = file_name.split('.')[-1].lower()
                elif file_url:
                    parsed_url = urlparse(file_url)
                    path = unquote(parsed_url.path)
                    if '.' in path:
                        file_extension = path.split('.')[-1].lower()
                
                result.append({
                    'name': file_name,
                    'url': file_url,
                    'id': f'remote_{i}',
                    'node_id': f'node_{i}',
                    'file_url': file_url,
                    'local_path': None,
                    'thumbnail_path': None,
                    'file_type': file_extension,
                    'file_size': file_size,
                    'static_url': None,
                    'thumbnail_url': None,
                    'source': 'remote',
                    'is_local': False,
                    'created_at': datetime.now().isoformat()
                })
            
            return result
            
        except Exception as e:
            current_app.logger.error(f"Error getting remote outputs for task {task_id}: {e}")
            return []
    
    def _generate_custom_filename(self, task_id, original_filename, index=0):
        """根据任务描述和日期生成自定义文件名，包含毫秒时间戳和序号避免重复"""
        try:
            # 获取任务信息
            task = Task.query.filter_by(task_id=task_id).first()
            
            # 获取任务描述前20个字符
            if task and task.task_description:
                # 清理描述中的特殊字符，只保留中文、英文、数字
                clean_desc = re.sub(r'[^\w\u4e00-\u9fff]', '', task.task_description)
                desc_prefix = clean_desc[:20] if clean_desc else 'task'
            else:
                desc_prefix = 'task'
            
            # 获取当前日期和毫秒时间戳
            now = datetime.now()
            date_str = now.strftime('%Y%m%d')
            timestamp_ms = now.strftime('%H%M%S%f')[:-3]  # 精确到毫秒
            
            # 获取原文件扩展名
            file_ext = os.path.splitext(original_filename)[1] or '.png'
            
            # 生成新文件名：描述_日期_时间戳_序号.扩展名
            new_filename = f"{desc_prefix}_{date_str}_{timestamp_ms}_{index:02d}{file_ext}"
            
            return new_filename
        except Exception as e:
            current_app.logger.error(f"Error generating custom filename: {e}")
            return original_filename
    
    def save_output_file(self, task_id, file_name, file_url, file_type='file'):
        """保存单个输出文件"""
        # 在远程模式下，跳过本地文件保存
        if self.remote_only_mode:
            current_app.logger.info(f"Skipping file save for task {task_id} - remote only mode enabled")
            return None
            
        try:
            if not file_url or not file_name:
                return None
            
            # 下载文件
            response = requests.get(file_url, timeout=30)
            if response.status_code != 200:
                current_app.logger.error(f"Failed to download {file_url}: {response.status_code}")
                return None
            
            # 生成自定义文件名
            custom_filename = self._generate_custom_filename(task_id, file_name)
            file_ext = os.path.splitext(custom_filename)[1]
            
            # 生成本地文件路径（使用日期分类，与download_and_save_outputs保持一致）
            now = datetime.now()
            year_month = now.strftime('%Y/%m')
            
            if file_type in ['image', 'png', 'jpg', 'jpeg', 'gif']:
                local_dir = os.path.join(self.base_dir, 'images', year_month)
            elif file_type in ['video', 'mp4', 'avi', 'mov']:
                local_dir = os.path.join(self.base_dir, 'videos', year_month)
            else:
                local_dir = os.path.join(self.base_dir, 'documents', year_month)
            
            os.makedirs(local_dir, exist_ok=True)
            
            # 使用自定义文件名
            base_name = os.path.splitext(custom_filename)[0]
            local_path = os.path.join(local_dir, custom_filename)
            
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
            if file_type.lower() in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp']:
                thumbnail_path = self._generate_thumbnail_with_custom_name(local_path, task_id, custom_filename)
            elif file_type.lower() in ['mp4', 'avi', 'mov', 'wmv', 'flv', 'webm']:
                thumbnail_path = self._generate_video_thumbnail_with_custom_name(local_path, task_id, custom_filename)
        
            # 保存到数据库
            file_size = len(response.content)
            static_url = self._get_static_url(local_path)
            thumbnail_url = self._get_static_url(thumbnail_path) if thumbnail_path else None
            
            # 检查是否已存在相同的输出记录
            display_name = os.path.basename(local_path)
            existing_output = TaskOutput.query.filter_by(
                task_id=task_id,
                name=display_name
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
                    name=display_name,
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
                
                # 生成缩略图路径（使用日期分类，与其他方法保持一致）
                now = datetime.now()
                date_str = now.strftime('%m%d')  # 格式如：0913
                thumbnail_dir = os.path.join(self.base_dir, 'images', 'thumbnails', date_str)
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
    
    def _extract_video_frame(self, video_path, time_sec=0.5):
        """使用ffmpeg从视频中抽取一帧，返回临时jpg路径；失败返回None"""
        try:
            fd, temp_path = tempfile.mkstemp(suffix='.jpg')
            os.close(fd)
            cmd = [
                'ffmpeg', '-y', '-ss', str(time_sec), '-i', video_path,
                '-frames:v', '1', '-q:v', '4', temp_path
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return temp_path if os.path.exists(temp_path) else None
        except Exception as e:
            current_app.logger.warning(f"ffmpeg extract frame failed for {video_path}: {e}")
            return None

    def _generate_video_thumbnail(self, video_path, task_id, index, node_id, size=(270, 480)):
        """为视频生成9:16缩略图（默认第0.5秒帧），返回缩略图路径或None"""
        frame_path = self._extract_video_frame(video_path)
        if not frame_path:
            return None
        try:
            thumb_path = self._generate_thumbnail(frame_path, task_id, index, node_id, size=size)
            try:
                os.remove(frame_path)
            except Exception:
                pass
            return thumb_path
        except Exception as e:
            current_app.logger.warning(f"Generate video thumbnail failed: {e}")
            try:
                os.remove(frame_path)
            except Exception:
                pass
            return None

    def _generate_video_thumbnail_with_custom_name(self, video_path, task_id, custom_filename, size=(270, 480)):
        """自定义文件名版本的视频缩略图生成，返回缩略图路径或None"""
        frame_path = self._extract_video_frame(video_path)
        if not frame_path:
            return None
        try:
            thumb_path = self._generate_thumbnail_with_custom_name(frame_path, task_id, custom_filename, size=size)
            try:
                os.remove(frame_path)
            except Exception:
                pass
            return thumb_path
        except Exception as e:
            current_app.logger.warning(f"Generate video thumbnail (custom) failed: {e}")
            try:
                os.remove(frame_path)
            except Exception:
                pass
            return None

    def cleanup_old_files(self, days=30):
        """清理旧文件"""
        # TODO: 实现文件清理逻辑
        pass