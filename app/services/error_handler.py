import logging
from typing import Dict, Tuple, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class ErrorCode(Enum):
    """错误代码枚举"""
    # 系统错误
    SYSTEM_ERROR = "SYSTEM_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    
    # 任务相关错误
    TASK_NOT_FOUND = "TASK_NOT_FOUND"
    TASK_ALREADY_RUNNING = "TASK_ALREADY_RUNNING"
    TASK_QUEUE_MAXED = "TASK_QUEUE_MAXED"
    TASK_TIMEOUT = "TASK_TIMEOUT"
    TASK_CANCELLED = "TASK_CANCELLED"
    
    # RunningHub错误
    RUNNINGHUB_CONNECTION_ERROR = "RUNNINGHUB_CONNECTION_ERROR"
    RUNNINGHUB_AUTH_ERROR = "RUNNINGHUB_AUTH_ERROR"
    RUNNINGHUB_INVALID_WORKFLOW = "RUNNINGHUB_INVALID_WORKFLOW"
    RUNNINGHUB_INVALID_NODE_INFO = "RUNNINGHUB_INVALID_NODE_INFO"
    
    # 工作流错误
    WORKFLOW_NOT_FOUND = "WORKFLOW_NOT_FOUND"
    WORKFLOW_INVALID_CONFIG = "WORKFLOW_INVALID_CONFIG"
    
    # 文件错误
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_UPLOAD_ERROR = "FILE_UPLOAD_ERROR"
    FILE_DOWNLOAD_ERROR = "FILE_DOWNLOAD_ERROR"

class ErrorHandler:
    """错误处理器 - 提供统一的错误处理和用户友好的错误信息"""
    
    # 错误码到用户友好信息的映射
    ERROR_MESSAGES: Dict[ErrorCode, Dict[str, str]] = {
        ErrorCode.SYSTEM_ERROR: {
            'title': '系统错误',
            'message': '系统遇到内部错误，请稍后重试',
            'suggestion': '如果问题持续存在，请联系技术支持'
        },
        ErrorCode.DATABASE_ERROR: {
            'title': '数据库错误',
            'message': '数据库连接或操作失败',
            'suggestion': '请检查网络连接或稍后重试'
        },
        ErrorCode.NETWORK_ERROR: {
            'title': '网络错误',
            'message': '网络连接失败',
            'suggestion': '请检查网络连接状态'
        },
        ErrorCode.TASK_NOT_FOUND: {
            'title': '任务不存在',
            'message': '指定的任务不存在或已被删除',
            'suggestion': '请检查任务ID是否正确'
        },
        ErrorCode.TASK_ALREADY_RUNNING: {
            'title': '任务已在运行',
            'message': '该任务已经在执行中，无法重复启动',
            'suggestion': '请等待当前任务完成或先停止当前任务'
        },
        ErrorCode.TASK_QUEUE_MAXED: {
            'title': '队列已满',
            'message': '当前执行队列已满，任务已加入等待队列',
            'suggestion': '任务将在有空闲槽位时自动开始执行'
        },
        ErrorCode.TASK_TIMEOUT: {
            'title': '任务超时',
            'message': '任务执行时间超过限制',
            'suggestion': '请检查任务配置或联系技术支持'
        },
        ErrorCode.TASK_CANCELLED: {
            'title': '任务已取消',
            'message': '任务已被用户或系统取消',
            'suggestion': '如需重新执行，请创建新任务'
        },
        ErrorCode.RUNNINGHUB_CONNECTION_ERROR: {
            'title': 'RunningHub连接错误',
            'message': '无法连接到RunningHub服务',
            'suggestion': '请检查网络连接或稍后重试'
        },
        ErrorCode.RUNNINGHUB_AUTH_ERROR: {
            'title': 'RunningHub认证错误',
            'message': 'API密钥无效或权限不足',
            'suggestion': '请检查API密钥配置'
        },
        ErrorCode.RUNNINGHUB_INVALID_WORKFLOW: {
            'title': '工作流无效',
            'message': '指定的工作流不存在或配置错误',
            'suggestion': '请检查工作流ID和配置'
        },
        ErrorCode.RUNNINGHUB_INVALID_NODE_INFO: {
            'title': '节点信息无效',
            'message': '节点ID或参数配置错误',
            'suggestion': '请检查节点配置和参数格式'
        },
        ErrorCode.WORKFLOW_NOT_FOUND: {
            'title': '工作流不存在',
            'message': '指定的工作流不存在',
            'suggestion': '请检查工作流ID是否正确'
        },
        ErrorCode.WORKFLOW_INVALID_CONFIG: {
            'title': '工作流配置错误',
            'message': '工作流配置文件格式错误或缺少必要参数',
            'suggestion': '请检查工作流配置文件'
        },
        ErrorCode.FILE_NOT_FOUND: {
            'title': '文件不存在',
            'message': '指定的文件不存在或已被删除',
            'suggestion': '请检查文件路径是否正确'
        },
        ErrorCode.FILE_UPLOAD_ERROR: {
            'title': '文件上传失败',
            'message': '文件上传过程中发生错误',
            'suggestion': '请检查文件格式和大小限制'
        },
        ErrorCode.FILE_DOWNLOAD_ERROR: {
            'title': '文件下载失败',
            'message': '文件下载过程中发生错误',
            'suggestion': '请稍后重试或联系技术支持'
        }
    }
    
    @classmethod
    def get_error_info(cls, error_code: ErrorCode, details: Optional[str] = None) -> Dict[str, str]:
        """获取错误信息"""
        error_info = cls.ERROR_MESSAGES.get(error_code, {
            'title': '未知错误',
            'message': '发生了未知错误',
            'suggestion': '请联系技术支持'
        }).copy()
        
        if details:
            error_info['details'] = details
            
        return error_info
    
    @classmethod
    def parse_error_from_message(cls, error_message: str) -> Tuple[ErrorCode, Optional[str]]:
        """从错误消息中解析错误代码"""
        error_message_upper = error_message.upper()
        
        # 检查RunningHub相关错误
        if 'TASK_QUEUE_MAXED' in error_message_upper:
            return ErrorCode.TASK_QUEUE_MAXED, error_message
        elif 'APIKEY_INVALID_NODE_INFO' in error_message_upper:
            return ErrorCode.RUNNINGHUB_INVALID_NODE_INFO, error_message
        elif 'UNAUTHORIZED' in error_message_upper or 'AUTH' in error_message_upper:
            return ErrorCode.RUNNINGHUB_AUTH_ERROR, error_message
        elif 'CONNECTION' in error_message_upper or 'TIMEOUT' in error_message_upper:
            return ErrorCode.RUNNINGHUB_CONNECTION_ERROR, error_message
        
        # 检查任务相关错误
        elif 'TASK NOT FOUND' in error_message_upper:
            return ErrorCode.TASK_NOT_FOUND, error_message
        elif 'ALREADY RUNNING' in error_message_upper:
            return ErrorCode.TASK_ALREADY_RUNNING, error_message
        elif 'CANCELLED' in error_message_upper:
            return ErrorCode.TASK_CANCELLED, error_message
        
        # 检查文件相关错误
        elif 'FILE NOT FOUND' in error_message_upper:
            return ErrorCode.FILE_NOT_FOUND, error_message
        elif 'UPLOAD' in error_message_upper:
            return ErrorCode.FILE_UPLOAD_ERROR, error_message
        elif 'DOWNLOAD' in error_message_upper:
            return ErrorCode.FILE_DOWNLOAD_ERROR, error_message
        
        # 检查数据库错误
        elif 'DATABASE' in error_message_upper or 'SQL' in error_message_upper:
            return ErrorCode.DATABASE_ERROR, error_message
        
        # 默认为系统错误
        return ErrorCode.SYSTEM_ERROR, error_message
    
    @classmethod
    def format_error_response(cls, error_code: ErrorCode, details: Optional[str] = None) -> Dict[str, any]:
        """格式化错误响应"""
        error_info = cls.get_error_info(error_code, details)
        
        return {
            'success': False,
            'error': {
                'code': error_code.value,
                'title': error_info['title'],
                'message': error_info['message'],
                'suggestion': error_info['suggestion'],
                'details': error_info.get('details')
            }
        }
    
    @classmethod
    def handle_exception(cls, e: Exception, context: str = "") -> Dict[str, any]:
        """处理异常并返回格式化的错误响应"""
        error_message = str(e)
        error_code, details = cls.parse_error_from_message(error_message)
        
        # 记录错误日志
        logger.error(f"Error in {context}: {error_message}", exc_info=True)
        
        return cls.format_error_response(error_code, details)
    
    @classmethod
    def create_user_friendly_message(cls, error_code: ErrorCode, task_id: Optional[str] = None) -> str:
        """创建用户友好的错误消息（用于TaskLog）"""
        error_info = cls.get_error_info(error_code)
        
        if task_id:
            return f"❌ {error_info['title']} (任务: {task_id}) - {error_info['message']}"
        else:
            return f"❌ {error_info['title']} - {error_info['message']}"

class RetryHandler:
    """重试处理器"""
    
    # 可重试的错误代码
    RETRYABLE_ERRORS = {
        ErrorCode.NETWORK_ERROR,
        ErrorCode.RUNNINGHUB_CONNECTION_ERROR,
        ErrorCode.DATABASE_ERROR,
        ErrorCode.TASK_QUEUE_MAXED  # 队列满时可以重试
    }
    
    @classmethod
    def is_retryable(cls, error_code: ErrorCode) -> bool:
        """判断错误是否可重试"""
        return error_code in cls.RETRYABLE_ERRORS
    
    @classmethod
    def get_retry_delay(cls, attempt: int, max_delay: int = 300) -> int:
        """获取重试延迟时间（指数退避）"""
        delay = min(2 ** attempt, max_delay)
        return delay
    
    @classmethod
    def should_retry(cls, error_code: ErrorCode, attempt: int, max_attempts: int = 3) -> bool:
        """判断是否应该重试"""
        return cls.is_retryable(error_code) and attempt < max_attempts