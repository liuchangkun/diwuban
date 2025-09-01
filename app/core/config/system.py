"""
系统配置模块（app.core.config.system）

本模块包含系统级别的通用配置类定义，包括：
- 目录配置
- 时区配置
- 通用系统配置
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SystemDirectoriesSettings:
    """
    系统目录配置
    
    用于配置系统级别的目录路径。
    
    属性：
        data: 数据文件目录
        logs: 日志文件目录
        configs: 配置文件目录
        temp: 临时文件目录
        backup: 备份文件目录
    """
    data: str = "data"
    logs: str = "logs"
    configs: str = "configs"
    temp: str = "temp"
    backup: str = "backup"


@dataclass(frozen=True)
class SystemTimezoneSettings:
    """
    系统时区配置
    
    用于配置系统级别的时区设置。
    
    属性：
        default: 默认时区
        storage: 数据库存储时区
        display: 显示时区
    """
    default: str = "Asia/Shanghai"
    storage: str = "UTC"
    display: str = "Asia/Shanghai"


@dataclass(frozen=True)
class SystemGeneralSettings:
    """
    系统通用配置
    
    用于配置系统级别的通用设置。
    
    属性：
        encoding: 默认文件编码
        locale: 系统语言环境
        max_workers: 系统级别默认最大工作线程数
    """
    encoding: str = "utf-8"
    locale: str = "zh_CN.UTF-8"
    max_workers: int = 4


@dataclass(frozen=True)
class SystemSettings:
    """
    系统完整配置
    
    集成所有系统级别配置，提供统一的配置访问接口。
    
    属性：
        directories: 目录配置
        timezone: 时区配置
        general: 通用配置
    """
    directories: SystemDirectoriesSettings = SystemDirectoriesSettings()
    timezone: SystemTimezoneSettings = SystemTimezoneSettings()
    general: SystemGeneralSettings = SystemGeneralSettings()