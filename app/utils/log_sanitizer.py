"""
日志脱敏工具类
用于对敏感数据进行脱敏处理和智能截断
"""
import json
import re
from typing import Any, Dict, List, Union


class LogSanitizer:
    """日志脱敏工具类"""
    
    # 敏感字段名称模式
    SENSITIVE_FIELDS = {
        'api_key', 'apikey', 'password', 'token', 'secret', 'auth',
        'field_value', 'fieldvalue', 'base64', 'data'
    }
    
    # base64数据模式
    BASE64_PATTERN = re.compile(r'^[A-Za-z0-9+/]*={0,2}$')
    
    # 长字符串截断阈值
    MAX_STRING_LENGTH = 100
    
    @classmethod
    def sanitize_dict(cls, data: Dict[str, Any], max_depth: int = 3) -> Dict[str, Any]:
        """
        对字典数据进行脱敏处理
        
        Args:
            data: 要处理的字典数据
            max_depth: 最大递归深度
            
        Returns:
            脱敏后的字典数据
        """
        if max_depth <= 0:
            return {"...": "max_depth_reached"}
            
        sanitized = {}
        
        for key, value in data.items():
            sanitized_key = key.lower()
            
            # 检查是否为敏感字段
            if any(sensitive in sanitized_key for sensitive in cls.SENSITIVE_FIELDS):
                sanitized[key] = cls._sanitize_sensitive_value(value)
            elif isinstance(value, dict):
                sanitized[key] = cls.sanitize_dict(value, max_depth - 1)
            elif isinstance(value, list):
                sanitized[key] = cls._sanitize_list(value, max_depth - 1)
            elif isinstance(value, str):
                sanitized[key] = cls._sanitize_string(value)
            else:
                sanitized[key] = value
                
        return sanitized
    
    @classmethod
    def sanitize_list(cls, data: List[Any], max_depth: int = 3) -> List[Any]:
        """
        对列表数据进行脱敏处理
        
        Args:
            data: 要处理的列表数据
            max_depth: 最大递归深度
            
        Returns:
            脱敏后的列表数据
        """
        return cls._sanitize_list(data, max_depth)
    
    @classmethod
    def _sanitize_list(cls, data: List[Any], max_depth: int) -> List[Any]:
        """内部列表脱敏方法"""
        if max_depth <= 0:
            return ["...max_depth_reached"]
            
        sanitized = []
        for item in data:
            if isinstance(item, dict):
                sanitized.append(cls.sanitize_dict(item, max_depth - 1))
            elif isinstance(item, list):
                sanitized.append(cls._sanitize_list(item, max_depth - 1))
            elif isinstance(item, str):
                sanitized.append(cls._sanitize_string(item))
            else:
                sanitized.append(item)
                
        return sanitized
    
    @classmethod
    def _sanitize_sensitive_value(cls, value: Any) -> str:
        """对敏感值进行脱敏处理"""
        if not isinstance(value, str):
            return str(value)
            
        # API Key类型的脱敏
        if len(value) > 20 and any(char.isalnum() for char in value):
            if len(value) > 12:
                return f"{value[:4]}...{value[-4:]}"
            else:
                return f"{value[:2]}...{value[-2:]}"
        
        # 长字符串脱敏（可能是base64数据）
        if len(value) > cls.MAX_STRING_LENGTH:
            return f"{value[:20]}...(长度:{len(value)}字符,已脱敏)"
            
        return value
    
    @classmethod
    def _sanitize_string(cls, value: str) -> str:
        """对普通字符串进行智能截断"""
        if len(value) <= cls.MAX_STRING_LENGTH:
            return value
            
        # 检查是否可能是base64数据
        if len(value) > 200 and cls._is_likely_base64(value):
            return f"{value[:30]}...(长度:{len(value)}字符,疑似base64数据,已截断)"
            
        # 普通长字符串截断
        return f"{value[:cls.MAX_STRING_LENGTH]}...(长度:{len(value)}字符,已截断)"
    
    @classmethod
    def _is_likely_base64(cls, value: str) -> bool:
        """检查字符串是否可能是base64数据"""
        # 检查长度和字符组成
        if len(value) < 50:
            return False
            
        # 检查是否符合base64字符集
        base64_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=')
        return all(c in base64_chars for c in value)
    
    @classmethod
    def sanitize_json_string(cls, json_str: str, max_depth: int = 3) -> str:
        """
        对JSON字符串进行脱敏处理
        
        Args:
            json_str: JSON字符串
            max_depth: 最大递归深度
            
        Returns:
            脱敏后的JSON字符串
        """
        try:
            data = json.loads(json_str)
            if isinstance(data, dict):
                sanitized_data = cls.sanitize_dict(data, max_depth)
            elif isinstance(data, list):
                sanitized_data = cls.sanitize_list(data, max_depth)
            else:
                return str(data)
                
            return json.dumps(sanitized_data, ensure_ascii=False, indent=2)
        except (json.JSONDecodeError, TypeError):
            # 如果不是有效的JSON，按普通字符串处理
            return cls._sanitize_string(json_str)
    
    @classmethod
    def create_safe_request_data(cls, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建安全的请求数据副本（专门用于API请求日志）
        
        Args:
            request_data: 原始请求数据
            
        Returns:
            安全的请求数据副本
        """
        safe_data = {}
        
        for key, value in request_data.items():
            if key.lower() in ['apikey', 'api_key']:
                # API Key脱敏
                if isinstance(value, str) and len(value) > 8:
                    safe_data[key] = f"{value[:8]}...{value[-4:]}"
                else:
                    safe_data[key] = "***"
            elif key.lower() in ['nodeinfolist', 'node_info_list']:
                # 节点信息列表特殊处理
                safe_data[key] = cls._sanitize_node_info_list(value)
            else:
                safe_data[key] = value
                
        return safe_data
    
    @classmethod
    def _sanitize_node_info_list(cls, node_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """对节点信息列表进行脱敏处理"""
        if not isinstance(node_list, list):
            return node_list
            
        sanitized_nodes = []
        for node in node_list:
            if not isinstance(node, dict):
                sanitized_nodes.append(node)
                continue
                
            safe_node = {
                "nodeId": node.get("nodeId", "N/A"),
                "fieldName": node.get("fieldName", "N/A")
            }
            
            field_value = node.get("fieldValue", "N/A")
            if isinstance(field_value, str) and len(field_value) > cls.MAX_STRING_LENGTH:
                safe_node["fieldValue"] = f"{field_value[:50]}...(长度:{len(field_value)}字符,已截断)"
            else:
                safe_node["fieldValue"] = field_value
                
            sanitized_nodes.append(safe_node)
            
        return sanitized_nodes