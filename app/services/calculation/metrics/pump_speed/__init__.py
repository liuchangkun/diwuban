"""
pump_speed 指标计算模块

包含完整的计算流水线：
- Pipeline: 流水线编排器
- DataLoader: 数据加载器
- DataFilter: 数据过滤器
- MethodSelector: 方法选择器
- Calculator: 计算执行器
- Validator: 结果验证器
"""

from .pipeline import PumpSpeedPipeline
from .data_loader import DataLoader
from .data_filter import DataFilter
from .method_selector import MethodSelector
from .calculator import Calculator
from .validator import Validator
from app.services.calculation.shared.scheduler import Task, TaskResult

__all__ = ['PumpSpeedPipeline', 'DataLoader', 'DataFilter', 'MethodSelector', 'Calculator', 'Validator', 'calculate_pump_speed']


# 全局流水线实例（延迟初始化）
_pipeline_instance = None


def calculate_pump_speed(task: Task) -> TaskResult:
    """
    pump_speed 计算函数（适配 Scheduler 接口）

    Args:
        task: 任务对象（包含 station_id, device_id, start_time, end_time, task_id）

    Returns:
        TaskResult: 任务结果
    """
    global _pipeline_instance

    # 延迟初始化流水线（确保 SharedServices 已初始化）
    if _pipeline_instance is None:
        _pipeline_instance = PumpSpeedPipeline()

    # 执行流水线
    try:
        result = _pipeline_instance.execute(
            station_id=task.station_id,
            device_id=task.device_id,
            start_time=task.start_time,
            end_time=task.end_time,
            task_id=task.task_id
        )

        # 转换为 TaskResult
        return TaskResult(
            task_id=task.task_id,
            device_id=task.device_id,
            metric_key=task.metric_key,
            success=True,
            results_count=result.get('results_count', 0),
            error_message=None
        )

    except Exception as e:
        import traceback
        return TaskResult(
            task_id=task.task_id,
            device_id=task.device_id,
            metric_key=task.metric_key,
            success=False,
            results_count=0,
            error_message=f"{str(e)}\n{traceback.format_exc()}"
        )

