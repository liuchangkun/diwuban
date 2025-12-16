"""
共享服务管理器（SharedServices）

职责：
- 管理所有共享服务的生命周期
- 提供统一的服务访问接口
"""

from __future__ import annotations

from app.services.calculation.shared.scheduler import Scheduler
from app.services.calculation.shared.data_writer import DataWriter
from app.services.calculation.shared.parameter_manager import ParameterManager
from app.core.logging.setup import log_activity


class SharedServices:
    """
    共享服务管理器（单例）

    职责：
    - 管理所有共享服务的生命周期
    - 提供统一的服务访问接口
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化共享服务"""
        if hasattr(self, '_initialized'):
            return
        
        self.scheduler = Scheduler()
        self.data_writer = DataWriter()
        self.parameter_manager = ParameterManager()
        self.logger = log_activity
        self._initialized = True

    def shutdown_all(self):
        """关闭所有服务"""
        self.scheduler.shutdown()
        self.logger("[共享服务] 所有服务已关闭")

