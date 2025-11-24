"""
main_pipeline_inlet_pressure 指标计算模块

总管进口压力计算
"""

from .pipeline import MainPipelineInletPressurePipeline

__all__ = ['MainPipelineInletPressurePipeline', 'calculate_main_pipeline_inlet_pressure']


# 全局流水线实例（延迟初始化）
_pipeline_instance = None


def calculate_main_pipeline_inlet_pressure(task):
    """
    main_pipeline_inlet_pressure 计算函数（适配 Scheduler 接口）
    
    Args:
        task: 任务对象（包含 station_id, device_id, start_time, end_time, task_id）
    
    Returns:
        TaskResult: 任务结果
    """
    global _pipeline_instance
    
    # 延迟初始化流水线（确保 SharedServices 已初始化）
    if _pipeline_instance is None:
        _pipeline_instance = MainPipelineInletPressurePipeline()
    
    # 执行流水线
    try:
        from app.services.calculation.shared.scheduler import TaskResult
        
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
            results_count=result.get('written_count', 0),
            error_message=None
        )
    
    except Exception as e:
        import traceback
        from app.services.calculation.shared.scheduler import TaskResult
        
        return TaskResult(
            task_id=task.task_id,
            device_id=task.device_id,
            metric_key=task.metric_key,
            success=False,
            results_count=0,
            error_message=f"{str(e)}\n{traceback.format_exc()}"
        )

