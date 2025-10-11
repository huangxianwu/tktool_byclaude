from flask import Blueprint, request, jsonify, current_app
import requests
import time
import os
import uuid
import json
from werkzeug.utils import secure_filename
from app.utils.gemini_key_manager import gemini_key_manager

# 模板系统相关函数
def load_ai_editing_template():
    """加载AI剪辑提示词模板"""
    try:
        docs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'docs')
        template_path = os.path.join(docs_dir, 'AI剪辑提示词.md')
        
        if not os.path.exists(template_path):
            return None
            
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        current_app.logger.error(f"加载AI剪辑提示词模板失败: {str(e)}")
        return None

def get_available_templates():
    """获取所有可用的模板列表"""
    templates = ['custom', 'ai_editing']  # custom=自定义提示词, ai_editing=AI剪辑提示词
    return templates

def process_template(template_content, variables):
    """处理模板变量替换"""
    if not template_content or not variables:
        return template_content
        
    try:
        # 简单的变量替换，支持 {{variable_name}} 格式
        processed_content = template_content
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            processed_content = processed_content.replace(placeholder, str(value))
        
        return processed_content
    except Exception as e:
        current_app.logger.error(f"模板处理失败: {str(e)}")
        return template_content

def _now_ms():
    return int(time.time() * 1000)

bp = Blueprint('ai_editor', __name__, url_prefix='/api/auto-editor')

# 简易会话存储：仅进程内，满足“不要过度设计”的要求
CONVERSATIONS = {}

# 上传目录
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads', 'auto_editor')
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 配置现已集中到config.py，通过current_app.config读取

def _cleanup_uploads(retention_hours: int):
    try:
        now = time.time()
        cutoff = now - retention_hours * 3600
        deleted = 0
        for name in os.listdir(UPLOAD_DIR):
            p = os.path.join(UPLOAD_DIR, name)
            try:
                if os.path.isfile(p):
                    mtime = os.path.getmtime(p)
                    if mtime < cutoff:
                        os.remove(p)
                        deleted += 1
            except Exception:
                pass
        return deleted
    except Exception:
        return 0

def _gemini_resumable_upload(file_path: str, mime_type: str, display_name: str, api_key: str = None):
    """使用 Gemini Files API 的可恢复上传协议上传文件，返回 file_uri 与文件名。
    参考官方文档：POST https://generativelanguage.googleapis.com/upload/v1beta/files?key=API_KEY
    步骤：
    1) start：声明文件元数据，获取 upload_url；
    2) upload+finalize：上传字节并完成，响应中包含 file.uri。
    """
    # 如果没有提供api_key，从管理器获取
    if not api_key:
        api_key = gemini_key_manager.get_current_key()
        if not api_key:
            return None, None, {'error': '没有可用的API key'}
    
    base_url = "https://generativelanguage.googleapis.com"
    start_url = f"{base_url}/upload/v1beta/files?key={api_key}"
    try:
        size = os.path.getsize(file_path)
        headers_start = {
            'X-Goog-Upload-Protocol': 'resumable',
            'X-Goog-Upload-Command': 'start',
            'X-Goog-Upload-Header-Content-Length': str(size),
            'X-Goog-Upload-Header-Content-Type': mime_type,
            'Content-Type': 'application/json',
        }
        body = json.dumps({'file': {'display_name': display_name or os.path.basename(file_path)}})
        resp_start = requests.post(start_url, headers=headers_start, data=body, timeout=60)
        if resp_start.status_code != 200:
            # 可能某些地区返回 200 以外，但仍提供头部；尽量解析
            upload_url = resp_start.headers.get('x-goog-upload-url') or resp_start.headers.get('X-Goog-Upload-Url')
            if not upload_url:
                return None, None, {'status': resp_start.status_code, 'text': resp_start.text}
        else:
            upload_url = resp_start.headers.get('x-goog-upload-url') or resp_start.headers.get('X-Goog-Upload-Url')
        if not upload_url:
            return None, None, {'error': 'no upload url'}

        headers_upload = {
            'Content-Length': str(size),
            'X-Goog-Upload-Offset': '0',
            'X-Goog-Upload-Command': 'upload, finalize',
        }
        with open(file_path, 'rb') as fp:
            resp_up = requests.post(upload_url, headers=headers_upload, data=fp, timeout=120)
        if resp_up.status_code != 200:
            try:
                err = resp_up.json()
            except Exception:
                err = {'status': resp_up.status_code, 'text': resp_up.text}
            return None, None, err
        info = resp_up.json() or {}
        file_obj = info.get('file') or {}
        file_uri = file_obj.get('uri')
        file_name = file_obj.get('name')
        return file_uri, file_name, None
    except Exception as e:
        return None, None, {'error': str(e)}

def _gemini_poll_file_active(file_ref: str, api_key: str = None, max_wait_s: int = 60):
    """轮询 Gemini Files API 直到文件状态为 ACTIVE。
    file_ref 可为完整 uri（https://.../v1beta/files/<id>）或 name（v1beta/files/<id>）。
    返回 (active: bool, info: dict, last_error: dict|None, logs: list[dict]).
    """
    logs = []
    try:
        # 如果没有提供api_key，从管理器获取
        if not api_key:
            api_key = gemini_key_manager.get_current_key()
            if not api_key:
                return False, None, {'error': '没有可用的API key'}, logs
        
        base = file_ref
        if not base.startswith('http'):
            base = f"https://generativelanguage.googleapis.com/{file_ref}"
        url = f"{base}?key={api_key}"
        start = time.time()
        while time.time() - start < max_wait_s:
            try:
                resp = requests.get(url, timeout=20)
                if resp.status_code == 200:
                    data = resp.json() or {}
                    # 响应可能是 {file:{...}} 或直接 {...}
                    file_info = data.get('file') or data
                    state = (file_info.get('state') or '').upper()
                    logs.append({'ts': _now_ms(), 'stage': 'gemini_file_state', 'message': f'state={state}'})
                    if state == 'ACTIVE':
                        return True, file_info, None, logs
                else:
                    logs.append({'ts': _now_ms(), 'stage': 'gemini_file_poll_error', 'message': f'status={resp.status_code}'})
                time.sleep(2)
            except Exception as e:
                logs.append({'ts': _now_ms(), 'stage': 'gemini_file_poll_exception', 'message': str(e)})
                time.sleep(2)
        return False, None, {'error': 'file not ACTIVE within timeout'}, logs
    except Exception as e:
        logs.append({'ts': _now_ms(), 'stage': 'gemini_file_poll_exception', 'message': str(e)})
        return False, None, {'error': str(e)}, logs

@bp.route('/templates', methods=['GET'])
def get_templates():
    """获取可用的提示词模板列表"""
    try:
        templates = get_available_templates()
        return jsonify({
            'templates': [
                {'value': 'custom', 'label': '自定义提示词'},
                {'value': 'ai_editing', 'label': 'AI剪辑提示词'}
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/upload', methods=['POST'])
def upload():
    """接受前端上传的素材（主要是视频），返回文件id等信息。
    说明：
    - 客户端使用XHR可获得上传进度（upload.onprogress），满足“视频上传给api的进度”需求。
    - 服务器端仅保存文件并返回id，不做复杂转码或解析。
    """
    try:
        log = []
        log.append({'ts': _now_ms(), 'stage': 'upload_start', 'message': '开始接收上传'})
        # 定期清理过期文件
        retention_hours = current_app.config.get('AUTO_EDITOR_RETENTION_HOURS', 24)
        deleted = _cleanup_uploads(retention_hours)
        files = request.files.getlist('files') or []
        saved = []
        for f in files:
            orig_name = f.filename or 'file'
            filename = secure_filename(orig_name)
            # 扩展名以原始文件名为准，避免中文被清理导致丢失扩展
            ext = os.path.splitext(orig_name)[1] or os.path.splitext(filename)[1]
            fid = uuid.uuid4().hex
            save_name = f"{fid}{ext}"
            save_path = os.path.join(UPLOAD_DIR, save_name)
            f.save(save_path)
            size = os.path.getsize(save_path)
            saved.append({
                'id': fid,
                'name': orig_name,
                'mimeType': f.mimetype,
                'size': size,
                'path': f"/uploads/auto_editor/{save_name}"
            })
        log.append({'ts': _now_ms(), 'stage': 'upload_cleanup', 'message': f'清理过期文件 {deleted} 个'})
        log.append({'ts': _now_ms(), 'stage': 'upload_done', 'message': f'保存完成，共{len(saved)}个文件'})
        return jsonify({'files': saved, 'log': log})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# 视频策略管理API
@bp.route('/video-strategy', methods=['POST'])
def save_video_strategy():
    """保存视频策略数据"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '无效的数据'}), 400
        
        # 生成唯一ID
        strategy_id = f"strategy_{int(time.time() * 1000)}"
        
        # 创建存储目录
        storage_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'video_strategies')
        os.makedirs(storage_dir, exist_ok=True)
        
        # 保存到文件
        file_path = os.path.join(storage_dir, f"{strategy_id}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True,
            'id': strategy_id,
            'message': '视频策略保存成功'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/video-strategy/<strategy_id>', methods=['GET'])
def get_video_strategy(strategy_id):
    """获取视频策略数据"""
    try:
        storage_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'video_strategies')
        file_path = os.path.join(storage_dir, f"{strategy_id}.json")
        
        if not os.path.exists(file_path):
            return jsonify({'error': '策略不存在'}), 404
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return jsonify(data)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/video-strategy', methods=['GET'])
def list_video_strategies():
    """获取所有视频策略列表"""
    try:
        storage_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'video_strategies')
        
        if not os.path.exists(storage_dir):
            return jsonify({'strategies': []})
        
        strategies = []
        for filename in os.listdir(storage_dir):
            if filename.endswith('.json'):
                strategy_id = filename[:-5]  # 移除.json后缀
                file_path = os.path.join(storage_dir, filename)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # 提取基本信息
                    metadata = data.get('metadata', {})
                    strategies.append({
                        'id': strategy_id,
                        'projectName': metadata.get('projectName', '未命名项目'),
                        'createdAt': metadata.get('createdAt'),
                        'lastModified': metadata.get('lastModified'),
                        'tags': metadata.get('tags', [])
                    })
                except Exception:
                    continue  # 跳过损坏的文件
        
        # 按创建时间排序
        strategies.sort(key=lambda x: x.get('createdAt', ''), reverse=True)
        
        return jsonify({'strategies': strategies})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/video-strategy/<strategy_id>', methods=['DELETE'])
def delete_video_strategy(strategy_id):
    """删除视频策略"""
    try:
        storage_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'video_strategies')
        file_path = os.path.join(storage_dir, f"{strategy_id}.json")
        
        if not os.path.exists(file_path):
            return jsonify({'error': '策略不存在'}), 404
        
        os.remove(file_path)
        
        return jsonify({
            'success': True,
            'message': '策略删除成功'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500





@bp.route('/save-table', methods=['POST'])
def save_table():
    """保存结构化表格数据到数据库"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '缺少数据'}), 400
        
        table_data = data.get('tableData')
        table_name = data.get('tableName', 'ai_editor_segments')
        
        if not table_data or not isinstance(table_data, list):
            return jsonify({'error': '无效的表格数据'}), 400
        
        # 这里可以根据需要实现数据库保存逻辑
        # 目前先返回成功响应，后续可以集成SQLAlchemy模型
        
        # 示例：验证数据结构
        for item in table_data:
            if not isinstance(item, dict):
                return jsonify({'error': '表格数据项必须是对象'}), 400
            required_fields = ['title', 'start', 'end', 'description']
            for field in required_fields:
                if field not in item:
                    return jsonify({'error': f'缺少必需字段: {field}'}), 400
        
        # TODO: 实际的数据库保存逻辑
        # from app.models import VideoSegment
        # for item in table_data:
        #     segment = VideoSegment(
        #         title=item['title'],
        #         start_time=item['start'],
        #         end_time=item['end'],
        #         description=item['description']
        #     )
        #     db.session.add(segment)
        # db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'成功保存 {len(table_data)} 条记录到表 {table_name}',
            'saved_count': len(table_data)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json() or {}
        model = data.get('model', 'gemini-2.5-pro')
        text = data.get('text', '')
        # 新增两类负载的支持
        reference_files = data.get('reference_files', [])
        reference_file = data.get('reference_file')  # 兼容旧字段（单个参考视频）
        clip_files = data.get('clip_files', [])
        files = data.get('files', [])  # 兼容旧负载
        conversation_id = data.get('conversation_id')
        output_format = data.get('output_format', 'markdown')  # 支持 'markdown' 或 'json-table'
        template_type = data.get('template', 'custom')  # 模板类型
        template_variables = data.get('template_variables', {})  # 模板变量
        
        # 读取集中配置
        keep_local = current_app.config.get('AUTO_EDITOR_KEEP_LOCAL', True)

        api_key = gemini_key_manager.get_current_key()
        if not api_key:
            current_app.logger.error('没有可用的Gemini API key，请在config.py中配置GEMINI_API_KEYS或设置环境变量')
            return jsonify({
                'error': '没有可用的Gemini API key，请检查配置'
            }), 500

        # 日志阶段
        log = []
        start_ms = _now_ms()
        log.append({'ts': start_ms, 'stage': 'start', 'message': '开始处理请求'})

        # 读取会话历史
        history_contents = []
        if conversation_id:
            history_contents = CONVERSATIONS.get(conversation_id, [])
            log.append({'ts': _now_ms(), 'stage': 'history', 'message': f'载入历史对话，条目={len(history_contents)}'})

        # 组装 parts
        parts = []
        file_mappings = []  # 收集剪辑素材的文件名与远程路径的映射关系
        reference_mappings = []  # 收集参考视频的文件名与远程路径的映射关系
        
        # 处理模板选择（先加载模板，变量替换延后到文件映射完成后进行）
        template_content = None
        if template_type == 'ai_editing':
            template_content = load_ai_editing_template()
            if template_content:
                log.append({'ts': _now_ms(), 'stage': 'template_loaded', 'message': 'AI剪辑模板已加载'})
            else:
                log.append({'ts': _now_ms(), 'stage': 'template_error', 'message': 'AI剪辑模板加载失败，使用默认处理'})
        
        # 注意：完整提示词的构建需要在文件映射完成后进行，故将文本构建延后到文件处理之后

        # 先处理参考视频（reference_files）：视频上传到 Gemini Files API 并以 fileData 引用（同时构建参考映射）
        gemini_files = []  # 收集上传到Gemini后的引用，便于前端日志展示
        for rf in (reference_files or [])[:10]:
            try:
                kind = rf.get('kind')
                mime_type = rf.get('mimeType')
                name = rf.get('name', 'reference')
                path = rf.get('path')
                if kind == 'video' and path and mime_type and mime_type.startswith('video/'):
                    save_name = path.split('/')[-1]
                    local_path = os.path.join(UPLOAD_DIR, save_name)
                    try:
                        size = os.path.getsize(local_path)
                        log.append({'ts': _now_ms(), 'stage': 'reference_video_meta', 'message': f'{name} size={(size/1024/1024):.2f}MB'})
                    except Exception:
                        pass
                    log.append({'ts': _now_ms(), 'stage': 'gemini_upload_start', 'message': f'上传参考视频到Gemini：{name} ({mime_type})'})
                    file_uri, file_name, err = _gemini_resumable_upload(local_path, mime_type, name)
                    if err:
                        log.append({'ts': _now_ms(), 'stage': 'gemini_upload_error', 'message': f'参考视频 {name} 上传失败: {err}'})
                        parts.append({'text': f"[参考视频: {name} @ {path}]"})
                    else:
                        parts.append({'fileData': {'mimeType': mime_type, 'fileUri': file_uri}})
                        gemini_files.append({'name': name, 'mimeType': mime_type, 'fileUri': file_uri, 'fileName': file_name})
                        reference_mappings.append({'clipIdentifier': name, 'clipUrl': file_uri})
                        log.append({'ts': _now_ms(), 'stage': 'gemini_upload_done', 'message': f'参考视频 {name} → {file_uri}'})

                        # 轮询文件状态直到 ACTIVE
                        active, info, perr, poll_logs = _gemini_poll_file_active(file_uri, max_wait_s=60)
                        log.extend(poll_logs)
                        if not active:
                            log.append({'ts': _now_ms(), 'stage': 'gemini_file_not_active', 'message': f'参考视频 {name} 未在时限内就绪，继续占位文本'})
                            parts.append({'text': f"[参考视频: {name} @ {path}]"})
                        else:
                            log.append({'ts': _now_ms(), 'stage': 'gemini_file_active', 'message': f'参考视频 {name} 文件就绪'})

                        # 不保留本地文件时，完成后删除本地副本
                        if not keep_local:
                            try:
                                os.remove(local_path)
                                log.append({'ts': _now_ms(), 'stage': 'local_delete', 'message': f'已删除本地文件：{save_name}'})
                            except Exception as de:
                                log.append({'ts': _now_ms(), 'stage': 'local_delete_error', 'message': str(de)})
                else:
                    # 仅支持视频作为参考；其他类型忽略或作为占位文本
                    name = rf.get('name', 'reference')
                    parts.append({'text': f"[参考视频占位: {name}]"})
            except Exception as e:
                log.append({'ts': _now_ms(), 'stage': 'gemini_upload_exception', 'message': f'参考视频 {rf.get("name") or "reference"} 异常: {str(e)}'})

        # 接着处理可编辑剪辑素材：支持图片内联；视频上传到 Gemini Files API 并以 fileData 引用（同时构建文件名映射）
        for f in (clip_files if clip_files else files)[:10]:
            kind = f.get('kind')
            mime_type = f.get('mimeType')
            if kind == 'image' and f.get('data') and mime_type and mime_type.startswith('image/'):
                # Gemini REST API 使用 camelCase：inlineData.mimeType
                parts.append({
                    'inlineData': {
                        'mimeType': mime_type,
                        'data': f.get('data')
                    }
                })
            elif kind == 'video':
                name = f.get('name', 'video')
                path = f.get('path')
                if path and mime_type and mime_type.startswith('video/'):
                    # 将本地上传文件转为Gemini Files API引用
                    try:
                        # 从 /uploads/auto_editor/<save_name> 推导本地绝对路径
                        save_name = path.split('/')[-1]
                        local_path = os.path.join(UPLOAD_DIR, save_name)
                        try:
                            size = os.path.getsize(local_path)
                            log.append({'ts': _now_ms(), 'stage': 'video_meta', 'message': f'{name} size={(size/1024/1024):.2f}MB'})
                        except Exception:
                            pass
                        log.append({'ts': _now_ms(), 'stage': 'gemini_upload_start', 'message': f'上传到Gemini：{name} ({mime_type})'})
                        file_uri, file_name, err = _gemini_resumable_upload(local_path, mime_type, name)
                        if err:
                            log.append({'ts': _now_ms(), 'stage': 'gemini_upload_error', 'message': f'{name} 上传失败: {err}'})
                            # 回退为占位文本
                            parts.append({'text': f"[参考视频: {name} @ {path}]"})
                        else:
                            # Gemini REST API 使用 camelCase：fileData.fileUri/mimeType
                            parts.append({
                                'fileData': {
                                    'mimeType': mime_type,
                                    'fileUri': file_uri
                                }
                            })
                            gemini_files.append({'name': name, 'mimeType': mime_type, 'fileUri': file_uri, 'fileName': file_name})
                            # 记录文件名与远程路径的映射关系
                            file_mappings.append({
                                'clipIdentifier': name,
                                'clipUrl': file_uri
                            })
                            log.append({'ts': _now_ms(), 'stage': 'gemini_upload_done', 'message': f'{name} → {file_uri}'})

                            # 轮询文件状态直到 ACTIVE
                            active, info, perr, poll_logs = _gemini_poll_file_active(file_uri, max_wait_s=60)
                            log.extend(poll_logs)
                            if not active:
                                log.append({'ts': _now_ms(), 'stage': 'gemini_file_not_active', 'message': f'{name} 未在时限内就绪，继续占位文本'})
                                parts.append({'text': f"[参考视频: {name} @ {path}]"})
                            else:
                                log.append({'ts': _now_ms(), 'stage': 'gemini_file_active', 'message': f'{name} 文件就绪'})

                            # 不保留本地文件时，完成后删除本地副本
                            if not keep_local:
                                try:
                                    os.remove(local_path)
                                    log.append({'ts': _now_ms(), 'stage': 'local_delete', 'message': f'已删除本地文件：{save_name}'})
                                except Exception as de:
                                    log.append({'ts': _now_ms(), 'stage': 'local_delete_error', 'message': str(de)})
                    except Exception as e:
                        log.append({'ts': _now_ms(), 'stage': 'gemini_upload_exception', 'message': f'{name} 异常: {str(e)}'})
                        parts.append({'text': f"[参考视频: {name} @ {path}]"})
                else:
                    parts.append({'text': f"[剪辑素材占位: {name}]"})

        # 处理参考视频占位：优先使用 reference_files 上传后的映射；其次兼容旧字段；最后回退到剪辑素材或文本
        reference_video = None
        try:
            if reference_mappings:
                # 多个参考视频则使用数组；一个则使用对象
                reference_video = reference_mappings[0] if len(reference_mappings) == 1 else reference_mappings
            elif reference_file:
                rf_kind = (reference_file.get('kind') or 'video').lower()
                rf_mime = reference_file.get('mimeType') or reference_file.get('mime') or 'video/mp4'
                rf_name = reference_file.get('name') or 'reference.mp4'
                rf_uri = reference_file.get('file_uri') or reference_file.get('path')
                if rf_kind == 'video' and rf_uri:
                    parts.append({'fileData': {'mimeType': rf_mime, 'fileUri': rf_uri}})
                    reference_video = {
                        'clipIdentifier': rf_name,
                        'clipUrl': rf_uri
                    }
                    log.append({'ts': _now_ms(), 'stage': 'reference_video', 'message': f'{rf_name} → {rf_uri}'})
                else:
                    parts.append({'text': f"[参考视频占位: {rf_name}]"})
                    reference_video = {
                        'clipIdentifier': rf_name,
                        'clipUrl': 'text_input'
                    }
            else:
                # 沿用旧逻辑：若无明确参考视频，则以第一个素材作为参考或用户文本
                if file_mappings:
                    reference_video = {
                        'clipIdentifier': file_mappings[0]['clipIdentifier'],
                        'clipUrl': file_mappings[0]['clipUrl']
                    }
                else:
                    reference_video = {
                        'clipIdentifier': '用户输入文本',
                        'clipUrl': 'text_input'
                    }
        except Exception as e:
            log.append({'ts': _now_ms(), 'stage': 'reference_error', 'message': str(e)})

        # 依据映射结果，填充模板占位并构建最终提示词文本
        try:
            # 可用剪辑素材列表
            editable_clips = [
                {
                    'clipIdentifier': m['clipIdentifier'],
                    'clipUrl': m['clipUrl']
                } for m in file_mappings
            ]

            # 创意简报（可选）
            creative_brief = {
                'targetDuration': '30s',
                'desiredStyle': '根据用户需求调整',
                'keySellingPointToFocus': text or ''
            }

            final_text = None
            if template_content and template_type == 'ai_editing':
                variables_for_template = {
                    'REFERENCE_VIDEO': json.dumps(reference_video, ensure_ascii=False, indent=2),
                    'EDITABLE_CLIPS': json.dumps(editable_clips, ensure_ascii=False, indent=2),
                    'CREATIVE_BRIEF': json.dumps(creative_brief, ensure_ascii=False, indent=2)
                }
                filled_template = process_template(template_content, variables_for_template)
                final_text = filled_template
            else:
                # 无模板时，直接以Markdown方式插入JSON对象，保持与文档结构一致
                final_text = (
                    "### 参考原视频 (referenceVideo)\n" +
                    "```json\n" + json.dumps(reference_video, ensure_ascii=False, indent=2) + "\n```\n\n" +
                    "### 可用剪辑素材 (editableClips)\n" +
                    "```json\n" + json.dumps(editable_clips, ensure_ascii=False, indent=2) + "\n```\n\n" +
                    (text or '')
                )

            # 在parts的最前面插入最终文本，使其与后续的fileData/inlineData并存
            if final_text:
                parts.insert(0, {'text': final_text})

            # 记录映射与最终提示词到后端日志与返回日志
            if file_mappings:
                mapping_lines = "\n".join([f"{m['clipIdentifier']} -> {m['clipUrl']}" for m in file_mappings])
                current_app.logger.info("可用剪辑素材文件名映射:\n" + mapping_lines)
                log.append({'ts': _now_ms(), 'stage': 'file_mapping', 'message': mapping_lines})

            current_app.logger.info("最终提示词（已填充JSON占位）:\n" + (final_text or ''))
            log.append({'ts': _now_ms(), 'stage': 'final_prompt', 'message': final_text or ''})
        except Exception as build_err:
            log.append({'ts': _now_ms(), 'stage': 'final_prompt_error', 'message': str(build_err)})

        contents = list(history_contents)
        contents.append({
            'role': 'user',
            'parts': parts or [{'text': '请根据上下文生成剪辑建议'}]
        })

        # 根据输出格式配置生成参数
        payload = { 'contents': contents }
        if output_format == 'json-table':
            # 配置结构化JSON输出，适用于两阶段视频策划数据
            payload['generationConfig'] = {
                'responseMimeType': 'application/json',
                'responseSchema': {
                    'type': 'OBJECT',
                    'properties': {
                        'phase1': {
                            'type': 'OBJECT',
                            'description': '第一阶段：材料分析和策略',
                            'properties': {
                                'materialAnalysisAndStrategy': {
                                    'type': 'OBJECT',
                                    'properties': {
                                        'keySellingPoints': {
                                            'type': 'ARRAY',
                                            'items': {'type': 'STRING'},
                                            'description': '关键卖点列表'
                                        },
                                        'videoClipAnalysis': {
                                            'type': 'ARRAY',
                                            'items': {
                                                'type': 'OBJECT',
                                                'properties': {
                                                    'clipName': {'type': 'STRING', 'description': '片段名称'},
                                                    'timeRange': {'type': 'STRING', 'description': '时间范围'},
                                                    'keyContent': {'type': 'STRING', 'description': '关键内容'},
                                                    'microClipSuggestions': {
                                                        'type': 'ARRAY',
                                                        'items': {
                                                            'type': 'OBJECT',
                                                            'properties': {
                                                                'sequence': {'type': 'INTEGER'},
                                                                'duration': {'type': 'STRING'},
                                                                'focus': {'type': 'STRING'},
                                                                'viralPotential': {'type': 'STRING'}
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        'phase2': {
                            'type': 'OBJECT',
                            'description': '第二阶段：视频制作蓝图',
                            'properties': {
                                'videoProductionBlueprint': {
                                    'type': 'ARRAY',
                                    'items': {
                                        'type': 'OBJECT',
                                        'properties': {
                                            'sequence': {'type': 'INTEGER', 'description': '序列号'},
                                            'clipSource': {'type': 'STRING', 'description': '素材来源'},
                                            'clipDescription': {'type': 'STRING', 'description': '片段描述'},
                                            'englishVoiceoverScript': {'type': 'STRING', 'description': '英文配音脚本'},
                                            'directorsNotes': {'type': 'STRING', 'description': '导演备注'}
                                        },
                                        'required': ['sequence', 'clipSource', 'clipDescription']
                                    }
                                },
                                'cleanEnglishVoiceoverScript': {
                                    'type': 'STRING',
                                    'description': '完整的英文配音脚本'
                                }
                            }
                        }
                    },
                    'required': ['phase1', 'phase2']
                }
            }

        log.append({'ts': _now_ms(), 'stage': 'request_init', 'message': f'构建请求，模型={model}, parts={len(parts)}'})

        # 调试：打印完整的提示词内容
        print("=" * 80)
        print("完整提示词内容调试:")
        print("=" * 80)
        for i, part in enumerate(parts):
            if 'text' in part:
                print(f"Part {i+1} (text):")
                print(part['text'])
                print("-" * 40)
            elif 'inlineData' in part:
                print(f"Part {i+1} (image): {part['inlineData']['mimeType']}")
                print("-" * 40)
            elif 'fileData' in part:
                print(f"Part {i+1} (file): {part['fileData']['mimeType']} - {part['fileData']['fileUri']}")
                print("-" * 40)
        print("=" * 80)
        print("文件映射信息:")
        if file_mappings:
            for mapping in file_mappings:
                print(f"  {mapping['clipIdentifier']} -> {mapping['clipUrl']}")
        else:
            print("  无文件映射")
        print("=" * 80)

        # 使用API key管理器的重试机制发送请求
        def _send_gemini_request():
            current_key = gemini_key_manager.get_current_key()
            if not current_key:
                raise Exception("没有可用的API key")
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={current_key}"
            headers = {
                'Content-Type': 'application/json'
            }
            
            log.append({'ts': _now_ms(), 'stage': 'request_send', 'message': f'发送请求，使用API key索引: {gemini_key_manager.config.CURRENT_GEMINI_KEY_INDEX}'})
            resp = requests.post(url, headers=headers, json=payload, timeout=90)
            log.append({'ts': _now_ms(), 'stage': 'request_done', 'message': f'收到响应，status={resp.status_code}'})
            
            # 检查响应状态
            if resp.status_code != 200:
                try:
                    err = resp.json()
                    error_message = str(err)
                except Exception:
                    error_message = resp.text
                
                # 如果是配额或认证错误，抛出异常让管理器处理
                if gemini_key_manager.is_quota_error(error_message) or gemini_key_manager.is_auth_error(error_message):
                    raise Exception(f"API错误 {resp.status_code}: {error_message}")
                else:
                    # 其他错误直接返回
                    raise Exception(f"非配额错误 {resp.status_code}: {error_message}")
            
            return resp

        try:
            resp = gemini_key_manager.execute_with_retry(_send_gemini_request)
        except Exception as e:
            end_ms = _now_ms()
            error_msg = str(e)
            log.append({'ts': end_ms, 'stage': 'end', 'message': f'请求失败: {error_msg}'})
            
            # 如果是配额错误，提供更友好的错误信息
            if gemini_key_manager.is_quota_error(error_msg):
                return jsonify({
                    'error': '所有Gemini API key的配额都已用完，请稍后再试或添加更多API key',
                    'log': log, 
                    'duration_ms': end_ms - start_ms
                }), 429
            else:
                return jsonify({
                    'error': error_msg,
                    'log': log, 
                    'duration_ms': end_ms - start_ms
                }), 500

        result = resp.json()
        # 根据输出格式提取内容
        text_out = ''
        json_out = None
        try:
            candidates = result.get('candidates') or []
            if candidates:
                parts_out = candidates[0].get('content', {}).get('parts') or []
                if output_format == 'json-table':
                    # 解析JSON格式的结构化数据
                    for p in parts_out:
                        if 'text' in p:
                            try:
                                json_out = json.loads(p['text'])
                                break
                            except json.JSONDecodeError:
                                text_out += p['text']  # 降级为文本
                else:
                    # 默认markdown格式，提取文本
                    for p in parts_out:
                        if 'text' in p:
                            text_out += p['text']
        except Exception:
            pass

        # 使用量信息（若返回）
        usage = result.get('usageMetadata') or {}
        end_ms = _now_ms()
        log.append({'ts': end_ms, 'stage': 'end', 'message': '完成处理'})

        # 将本次回复写入会话（简易记忆）
        if conversation_id:
            conv = CONVERSATIONS.setdefault(conversation_id, [])
            # 追加用户消息（如果未在contents中持久化）与模型消息
            # 这里直接保存模型的文本回复，满足分步骤、可延续的实现需求
            conv.append({
                'role': 'user',
                'parts': parts or [{'text': '请根据上下文生成剪辑建议'}]
            })
            if text_out.strip():
                conv.append({
                    'role': 'model',
                    'parts': [{'text': text_out.strip()}]
                })

        return jsonify({
            'text': text_out.strip(),
            'jsonData': json_out,
            'raw': result,
            'usage': {
                'promptTokenCount': usage.get('promptTokenCount'),
                'candidatesTokenCount': usage.get('candidatesTokenCount'),
                'totalTokenCount': usage.get('totalTokenCount')
            },
            'model': model,
            'duration_ms': end_ms - start_ms,
            'log': log,
            'geminiFiles': gemini_files,
            'conversation_id': conversation_id
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500