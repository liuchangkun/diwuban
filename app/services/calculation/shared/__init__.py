"""
共享层模块

提供全局单例服务：
- Scheduler: 任务调度器
- DataWriter: 数据写入器
- ParameterManager: 参数管理器
- SharedServices: 服务管理器
"""

from app.services.calculation.shared.scheduler import Scheduler, Task, TaskResult
from app.services.calculation.shared.data_writer import DataWriter, WriteRecord
from app.services.calculation.shared.parameter_manager import ParameterManager
from app.services.calculation.shared.shared_services import SharedServices

__all__ = [
    'Scheduler',
    'Task',
    'TaskResult',
    'DataWriter',
    'WriteRecord',
    'ParameterManager',
    'SharedServices',
]

