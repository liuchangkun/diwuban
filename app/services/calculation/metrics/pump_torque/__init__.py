"""
pump_torque 指标计算模块

职责：
- 计算泵扭矩（pump_torque）
- 支持2种计算方法（功率-转速法、水力功率法）
- 集成到调度器和数据写入系统
"""

from .pipeline import PumpTorquePipeline
from app.services.calculation.shared.scheduler import Task, TaskResult

__all__ = ['PumpTorquePipeline', 'calculate_pump_torque']


# 全局流水线实例（延迟初始化）
_pipeline_instance = None


def calculate_pump_torque(task: Task) -> TaskResult:
    """
    pump_torque 计算函数（适配 Scheduler 接口）

    Args:
        task: 任务对象（包含 station_id, device_id, start_time, end_time, task_id）

    Returns:
        TaskResult: 任务结果
    """
    global _pipeline_instance

    # 延迟初始化流水线（确保 SharedServices 已初始化）
    if _pipeline_instance is None:
        _pipeline_instance = PumpTorquePipeline()

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

