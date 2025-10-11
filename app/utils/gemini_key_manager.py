"""
Gemini API Key 管理器
处理多个API key的自动切换逻辑
"""

import time
import logging
from typing import Optional, List, Callable, Any
from config import Config

logger = logging.getLogger(__name__)

class GeminiKeyManager:
    """Gemini API Key 管理器"""
    
    def __init__(self):
        self.config = Config
        self.failed_keys = set()  # 记录失败的key
        self.last_switch_time = 0  # 上次切换时间
        self.min_switch_interval = 60  # 最小切换间隔（秒）
    
    def get_current_key(self) -> Optional[str]:
        """获取当前可用的API key"""
        return self.config.get_current_gemini_key()
    
    def is_quota_error(self, error_message: str) -> bool:
        """判断是否为配额错误"""
        quota_indicators = [
            'quota exceeded',
            'rate limit',
            'too many requests',
            'quota_exceeded',
            'rate_limit_exceeded',
            'insufficient quota',
            'billing',
            'payment required',
            '429',  # HTTP状态码
            'RESOURCE_EXHAUSTED'
        ]
        
        error_lower = error_message.lower()
        return any(indicator in error_lower for indicator in quota_indicators)
    
    def is_auth_error(self, error_message: str) -> bool:
        """判断是否为认证错误"""
        auth_indicators = [
            'invalid api key',
            'authentication failed',
            'unauthorized',
            'invalid_api_key',
            'api key not valid',
            '401',  # HTTP状态码
            'UNAUTHENTICATED'
        ]
        
        error_lower = error_message.lower()
        return any(indicator in error_lower for indicator in auth_indicators)
    
    def should_switch_key(self, error_message: str) -> bool:
        """判断是否应该切换API key"""
        current_time = time.time()
        
        # 检查是否为需要切换的错误类型
        if not (self.is_quota_error(error_message) or self.is_auth_error(error_message)):
            return False
        
        # 检查切换间隔
        if current_time - self.last_switch_time < self.min_switch_interval:
            logger.warning(f"切换间隔过短，跳过切换。距离上次切换: {current_time - self.last_switch_time:.1f}秒")
            return False
        
        return True
    
    def switch_to_next_key(self) -> Optional[str]:
        """切换到下一个可用的API key"""
        current_key = self.get_current_key()
        if current_key:
            self.failed_keys.add(current_key)
        
        # 尝试切换到下一个key
        next_key = self.config.switch_to_next_gemini_key()
        self.last_switch_time = time.time()
        
        if next_key:
            logger.info(f"已切换到新的Gemini API key")
            return next_key
        else:
            logger.error("没有可用的备用API key")
            return None
    
    def reset_failed_keys(self):
        """重置失败的key记录（可能配额已恢复）"""
        self.failed_keys.clear()
        self.config.reset_gemini_key_index()
        logger.info("已重置失败的API key记录")
    
    def get_available_keys_count(self) -> int:
        """获取可用的API key数量"""
        all_keys = self.config.get_all_gemini_keys()
        return len([key for key in all_keys if key not in self.failed_keys])
    
    def execute_with_retry(self, func: Callable, *args, max_retries: int = None, **kwargs) -> Any:
        """
        使用重试机制执行函数，自动切换API key
        
        Args:
            func: 要执行的函数
            *args: 函数参数
            max_retries: 最大重试次数（默认为API key数量）
            **kwargs: 函数关键字参数
        
        Returns:
            函数执行结果
        
        Raises:
            Exception: 所有API key都失败后抛出最后一个异常
        """
        if max_retries is None:
            max_retries = len(self.config.get_all_gemini_keys())
        
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                current_key = self.get_current_key()
                if not current_key:
                    raise Exception("没有可用的Gemini API key")
                
                # 执行函数
                result = func(*args, **kwargs)
                
                # 如果成功，重置失败计数器（可能配额已恢复）
                if attempt > 0:
                    logger.info("API调用成功，可能配额已恢复")
                
                return result
                
            except Exception as e:
                last_exception = e
                error_message = str(e)
                
                logger.warning(f"API调用失败 (尝试 {attempt + 1}/{max_retries}): {error_message}")
                
                # 判断是否应该切换key
                if self.should_switch_key(error_message):
                    next_key = self.switch_to_next_key()
                    if not next_key:
                        logger.error("没有更多可用的API key")
                        break
                else:
                    # 如果不是配额/认证错误，直接抛出异常
                    logger.error(f"非配额/认证错误，停止重试: {error_message}")
                    break
        
        # 所有重试都失败了
        if last_exception:
            logger.error(f"所有API key都已失败，最后错误: {str(last_exception)}")
            raise last_exception
        else:
            raise Exception("未知错误：没有可用的API key")
    
    def get_status(self) -> dict:
        """获取管理器状态"""
        all_keys = self.config.get_all_gemini_keys()
        current_key = self.get_current_key()
        
        return {
            'total_keys': len(all_keys),
            'failed_keys': len(self.failed_keys),
            'available_keys': len(all_keys) - len(self.failed_keys),
            'current_key_index': self.config.CURRENT_GEMINI_KEY_INDEX,
            'current_key_masked': f"{current_key[:10]}...{current_key[-4:]}" if current_key else None,
            'last_switch_time': self.last_switch_time,
            'failed_keys_masked': [f"{key[:10]}...{key[-4:]}" for key in self.failed_keys] if self.failed_keys else []
        }

# 全局实例
gemini_key_manager = GeminiKeyManager()