#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
时区处理工具类 - 统一时间处理逻辑
"""

import pytz
from datetime import datetime, timezone
from typing import Optional, Union

class TimezoneHelper:
    """时区处理助手类"""
    
    # 默认时区设置
    DEFAULT_TIMEZONE = 'Asia/Shanghai'  # 中国标准时间
    UTC_TIMEZONE = 'UTC'
    
    @classmethod
    def get_local_timezone(cls) -> pytz.BaseTzInfo:
        """获取本地时区对象"""
        return pytz.timezone(cls.DEFAULT_TIMEZONE)
    
    @classmethod
    def get_utc_timezone(cls) -> pytz.BaseTzInfo:
        """获取UTC时区对象"""
        return pytz.timezone(cls.UTC_TIMEZONE)
    
    @classmethod
    def now_local(cls) -> datetime:
        """获取当前本地时间（带时区信息）"""
        local_tz = cls.get_local_timezone()
        return datetime.now(local_tz)
    
    @classmethod
    def now_utc(cls) -> datetime:
        """获取当前UTC时间（带时区信息）"""
        return datetime.now(pytz.UTC)
    
    @classmethod
    def now_naive_local(cls) -> datetime:
        """获取当前本地时间（不带时区信息，用于数据库存储）"""
        local_tz = cls.get_local_timezone()
        return datetime.now(local_tz).replace(tzinfo=None)
    
    @classmethod
    def utc_to_local(cls, utc_dt: datetime) -> datetime:
        """将UTC时间转换为本地时间
        
        Args:
            utc_dt: UTC时间（可以是naive或aware）
            
        Returns:
            本地时间（aware）
        """
        if utc_dt is None:
            return None
            
        # 如果是naive datetime，假设它是UTC时间
        if utc_dt.tzinfo is None:
            utc_dt = pytz.UTC.localize(utc_dt)
        
        # 转换到本地时区
        local_tz = cls.get_local_timezone()
        return utc_dt.astimezone(local_tz)
    
    @classmethod
    def local_to_utc(cls, local_dt: datetime) -> datetime:
        """将本地时间转换为UTC时间
        
        Args:
            local_dt: 本地时间（可以是naive或aware）
            
        Returns:
            UTC时间（aware）
        """
        if local_dt is None:
            return None
            
        # 如果是naive datetime，假设它是本地时间
        if local_dt.tzinfo is None:
            local_tz = cls.get_local_timezone()
            local_dt = local_tz.localize(local_dt)
        
        # 转换到UTC时区
        return local_dt.astimezone(pytz.UTC)
    
    @classmethod
    def to_naive_utc(cls, dt: datetime) -> datetime:
        """将任意时间转换为naive UTC时间（用于数据库存储）
        
        Args:
            dt: 任意时间
            
        Returns:
            naive UTC时间
        """
        if dt is None:
            return None
            
        # 如果是naive datetime，假设它是本地时间
        if dt.tzinfo is None:
            local_tz = cls.get_local_timezone()
            dt = local_tz.localize(dt)
        
        # 转换到UTC并移除时区信息
        return dt.astimezone(pytz.UTC).replace(tzinfo=None)
    
    @classmethod
    def format_local_time(cls, dt: datetime, format_str: str = '%Y-%m-%d %H:%M:%S') -> str:
        """格式化为本地时间字符串
        
        Args:
            dt: 时间对象
            format_str: 格式字符串
            
        Returns:
            格式化的本地时间字符串
        """
        if dt is None:
            return ''
            
        # 转换为本地时间
        local_dt = cls.utc_to_local(dt)
        return local_dt.strftime(format_str)
    
    @classmethod
    def parse_datetime_string(cls, dt_str: str, format_str: str = '%Y-%m-%d %H:%M:%S', 
                            is_local: bool = True) -> datetime:
        """解析时间字符串
        
        Args:
            dt_str: 时间字符串
            format_str: 格式字符串
            is_local: 是否为本地时间
            
        Returns:
            datetime对象（naive UTC）
        """
        if not dt_str:
            return None
            
        try:
            dt = datetime.strptime(dt_str, format_str)
            
            if is_local:
                # 如果是本地时间，转换为UTC
                return cls.to_naive_utc(dt)
            else:
                # 如果已经是UTC时间，直接返回
                return dt
                
        except ValueError as e:
            raise ValueError(f"无法解析时间字符串 '{dt_str}': {e}")
    
    @classmethod
    def get_date_range_utc(cls, start_date_str: str, end_date_str: str) -> tuple:
        """获取日期范围的UTC时间
        
        Args:
            start_date_str: 开始日期字符串 (YYYY-MM-DD)
            end_date_str: 结束日期字符串 (YYYY-MM-DD)
            
        Returns:
            (start_datetime_utc, end_datetime_utc) 元组
        """
        local_tz = cls.get_local_timezone()
        
        # 解析开始日期（本地时间00:00:00）
        start_dt = None
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                start_dt_local = local_tz.localize(start_date)
                start_dt = start_dt_local.astimezone(pytz.UTC).replace(tzinfo=None)
            except ValueError:
                pass
        
        # 解析结束日期（本地时间23:59:59）
        end_dt = None
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                end_date = end_date.replace(hour=23, minute=59, second=59)
                end_dt_local = local_tz.localize(end_date)
                end_dt = end_dt_local.astimezone(pytz.UTC).replace(tzinfo=None)
            except ValueError:
                pass
        
        return start_dt, end_dt
    
    @classmethod
    def is_same_day_local(cls, dt1: datetime, dt2: datetime) -> bool:
        """判断两个时间是否为同一本地日期
        
        Args:
            dt1: 第一个时间
            dt2: 第二个时间
            
        Returns:
            是否为同一本地日期
        """
        if dt1 is None or dt2 is None:
            return False
            
        local_dt1 = cls.utc_to_local(dt1)
        local_dt2 = cls.utc_to_local(dt2)
        
        return local_dt1.date() == local_dt2.date()
    
    @classmethod
    def get_timezone_offset_hours(cls) -> int:
        """获取本地时区相对于UTC的偏移小时数"""
        local_tz = cls.get_local_timezone()
        now = datetime.now(local_tz)
        offset = now.utcoffset()
        return int(offset.total_seconds() / 3600)

# 便捷函数
def now_local() -> datetime:
    """获取当前本地时间（不带时区信息）"""
    return TimezoneHelper.now_naive_local()

def now_utc() -> datetime:
    """获取当前UTC时间（不带时区信息）"""
    return TimezoneHelper.now_utc().replace(tzinfo=None)

def format_local_time(dt: datetime, format_str: str = '%Y-%m-%d %H:%M:%S') -> str:
    """格式化为本地时间字符串"""
    return TimezoneHelper.format_local_time(dt, format_str)

def utc_to_local_str(dt: datetime, format_str: str = '%Y-%m-%d %H:%M:%S') -> str:
    """将UTC时间转换为本地时间字符串"""
    return TimezoneHelper.format_local_time(dt, format_str)