"""
任务调度器（Scheduler）

职责：
- 定义指标计算顺序（METRIC_ORDER）
- 任务创建和分片
- 并行执行管理（指标间串行，设备间并行）
- 进度跟踪
- 错误处理和重试
"""

from __future__ import annotations

import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Callable, Dict, List, Optional, Tuple

from app.adapters.db import get_connection
from app.services.calculation.shared.adaptive_chunk import AdaptiveChunkManager


@dataclass
class Task:
    """任务定义"""

    task_id: str
    metric_key: str
    station_id: int
    device_id: int
    start_time: datetime
    end_time: datetime
    priority: int = 0


@dataclass
class TaskResult:
    """任务结果"""

    task_id: str
    device_id: int
    metric_key: str
    success: bool
    results_count: int
    error_message: Optional[str] = None
    duration_seconds: float = 0.0


class Scheduler:
    """
    任务调度器（单例）

    职责：
    - 定义指标计算顺序（METRIC_ORDER）
    - 任务创建和分片
    - 并行执行管理（指标间串行，设备间并行）
    - 进度跟踪
    """

    # 指标计算顺序（按依赖关系排序）
    # 规则：先计算基础指标，再计算依赖它们的指标
    # 注意：pump_outlet_pressure 是 pump_head 的中间结果，不是独立任务，不应出现在此列表中
    METRIC_ORDER = [
        "pump_flow_rate",  # 1. 水泵流量（基础指标）
        "pump_inlet_pressure",  # 2. 水泵入口压力（基础指标）
        "main_pipeline_inlet_pressure",  # 3. 总管进口压力（基础指标，仅依赖pool_liquid_level）
        "pump_head",  # 4. 水泵扬程（依赖 pump_inlet_pressure, main_pipeline_outlet_pressure, pump_flow_rate）
        "pump_efficiency",  # 5. 水泵效率（依赖 pump_flow_rate, pump_head）
        "pump_speed",  # 6. 水泵转速（基础指标）
        "pump_shaft_power",  # 7. 水泵轴功率（依赖 pump_active_power）
        "pump_torque",  # 8. 水泵扭矩（依赖 pump_active_power, pump_speed）
        "main_pipeline_outlet_pressure",  # 9. 总管出口压力（依赖 pump_outlet_pressure）

    ]

    _instance = None

    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, max_workers: int = 10, enable_adaptive_chunk: bool = True):
        """
        初始化调度器

        Args:
            max_workers: 最大并行工作线程数
            enable_adaptive_chunk: 是否启用自适应分片
        """
        if hasattr(self, "_initialized"):
            return

        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.logger = logging.getLogger(__name__)

        # 初始化自适应分片管理器
        self.adaptive_chunk = None
        if enable_adaptive_chunk:
            self.adaptive_chunk = AdaptiveChunkManager({
                'enabled': True,
                'initial_hours': 24,
                'min_hours': 1,
                'max_hours': 168,  # 7天
                'target_rows_per_task': 100000,
                'target_duration_seconds': 60,
                'estimated_rows_per_hour': 3600,  # 1秒1条数据
            })
            self.logger.info("[调度] 自适应分片已启用")

        self._initialized = True

    def create_tasks(
        self,
        metric_key: str,
        device_ids: List[int],
        start_time: datetime,
        end_time: datetime,
        time_chunk_hours: Optional[int] = None,
    ) -> List[Task]:
        """
        创建任务列表

        注意：不在此处过滤设备类型，因为不同指标需要计算的设备类型不同。
        设备类型检查由各指标的DataLoader负责。

        Args:
            metric_key: 指标键
            device_ids: 设备ID列表
            start_time: 开始时间
            end_time: 结束时间
            time_chunk_hours: 时间分片大小（小时），None则使用自适应分片

        Returns:
            任务列表
        """
        # 计算总时间跨度
        total_hours = (end_time - start_time).total_seconds() / 3600

        # 使用自适应分片计算最优分片大小
        if time_chunk_hours is None and self.adaptive_chunk and self.adaptive_chunk.is_enabled():
            time_chunk_hours = self.adaptive_chunk.calculate_optimal_chunk_hours(
                device_count=len(device_ids),
                total_hours=total_hours,
                metric_key=metric_key
            )
            self.logger.info(
                f"[调度] 使用自适应分片: {time_chunk_hours}小时",
                extra={
                    "extra_data": {
                        "指标键": metric_key,
                        "设备数量": len(device_ids),
                        "总小时数": round(total_hours, 2),
                        "自适应分片小时数": time_chunk_hours,
                    }
                }
            )
        elif time_chunk_hours is None:
            # 如果未启用自适应分片，使用默认值
            time_chunk_hours = 24

        tasks = []
        tasks_by_device = {device_id: [] for device_id in device_ids}

        # 时间分片
        current_time = start_time
        while current_time < end_time:
            chunk_end = min(current_time + timedelta(hours=time_chunk_hours), end_time)

            # 为每个设备创建任务
            for device_id in device_ids:
                task = Task(
                    task_id=str(uuid.uuid4()),
                    metric_key=metric_key,
                    station_id=self._get_station_id(device_id),
                    device_id=device_id,
                    start_time=current_time,
                    end_time=chunk_end,
                )
                tasks.append(task)
                tasks_by_device[device_id].append(task.task_id)

            current_time = chunk_end

        # 增强日志：输出详细的任务创建信息
        time_range_str = f"{start_time.strftime('%Y-%m-%d %H:%M:%S')} ~ {end_time.strftime('%Y-%m-%d %H:%M:%S')}"
        time_chunks = int(total_hours / time_chunk_hours) if time_chunk_hours > 0 else 0

        # 获取前5个任务ID作为示例
        sample_task_ids = [task.task_id for task in tasks[:5]]

        self.logger.info(
            f"[调度] 创建任务: {len(tasks)}个",
            extra={
                "extra_data": {
                    "指标键": metric_key,
                    "设备ID列表": device_ids,
                    "设备数量": len(device_ids),
                    "时间范围": time_range_str,
                    "总小时数": round(total_hours, 2),
                    "时间分片小时数": time_chunk_hours,
                    "时间分片数": time_chunks,
                    "每设备任务数": {device_id: len(task_ids) for device_id, task_ids in tasks_by_device.items()},
                    "示例任务ID": sample_task_ids,
                    "自适应已启用": self.adaptive_chunk is not None and self.adaptive_chunk.is_enabled(),
                }
            },
        )

        return tasks

    def schedule_all_metrics(
        self,
        device_ids: List[int],
        start_time: datetime,
        end_time: datetime,
        time_chunk_hours: Optional[int] = None,
        metrics: Optional[List[str]] = None,
    ) -> Dict[str, Dict]:
        """
        调度所有指标的计算（按 METRIC_ORDER 顺序）

        执行策略：
        - 指标间串行：先计算所有设备的 pump_flow_rate，完成后再计算 pump_head
        - 设备间并行：同一指标的不同设备并行计算

        Args:
            device_ids: 设备ID列表
            start_time: 开始时间
            end_time: 结束时间
            time_chunk_hours: 时间分片大小（小时），None则使用自适应分片
            metrics: 要计算的指标列表（None表示计算所有指标）

        Returns:
            所有指标的执行结果汇总
        """
        # 确定要计算的指标列表
        metrics_to_calculate = metrics if metrics else self.METRIC_ORDER

        # 过滤：只保留在 METRIC_ORDER 中的指标，并按顺序排序
        ordered_metrics = [m for m in self.METRIC_ORDER if m in metrics_to_calculate]

        self.logger.info(
            f"[调度] 开始调度所有指标计算",
            extra={
                "extra_data": {
                    "指标数量": len(ordered_metrics),
                    "设备数量": len(device_ids),
                    "时间范围": f"{start_time} ~ {end_time}",
                    "指标顺序": ordered_metrics,
                }
            },
        )

        all_results = {}

        # 按指标顺序依次执行
        for metric_key in ordered_metrics:
            self.logger.info(
                f"[调度] 开始计算指标: {metric_key}",
                extra={"extra_data": {"指标键": metric_key, "设备数量": len(device_ids)}},
            )

            metric_start_time = time.time()

            # 计算当前指标的所有设备
            metric_result = self.schedule_single_metric(
                metric_key=metric_key,
                device_ids=device_ids,
                start_time=start_time,
                end_time=end_time,
                time_chunk_hours=time_chunk_hours,
            )

            metric_duration = time.time() - metric_start_time
            metric_result["duration_seconds"] = metric_duration

            all_results[metric_key] = metric_result

            self.logger.info(
                f"[调度] 指标 {metric_key} 计算完成",
                extra={
                    "extra_data": {
                        "指标键": metric_key,
                        "成功任务数": metric_result.get("success_count", 0),
                        "失败任务数": metric_result.get("failure_count", 0),
                        "总记录数": metric_result.get("total_points", 0),
                        "执行时长秒": metric_duration,
                    }
                },
            )

        self.logger.info(
            f"[调度] 所有指标计算完成",
            extra={
                "extra_data": {
                    "总指标数": len(ordered_metrics),
                    "成功指标": sum(1 for r in all_results.values() if r.get("failure_count", 0) == 0),
                    "失败指标": sum(1 for r in all_results.values() if r.get("failure_count", 0) > 0),
                }
            },
        )

        return all_results

    def schedule_single_metric(
        self,
        metric_key: str,
        device_ids: List[int],
        start_time: datetime,
        end_time: datetime,
        time_chunk_hours: Optional[int] = None,
    ) -> Dict:
        """
        调度单个指标的计算（所有设备并行）

        Args:
            metric_key: 指标键
            device_ids: 设备ID列表
            start_time: 开始时间
            end_time: 结束时间
            time_chunk_hours: 时间分片大小（小时），None则使用自适应分片

        Returns:
            执行结果汇总
        """
        # 增强日志：方法开始
        time_range_str = f"{start_time.strftime('%Y-%m-%d %H:%M:%S')} ~ {end_time.strftime('%Y-%m-%d %H:%M:%S')}"
        total_hours = (end_time - start_time).total_seconds() / 3600

        # 如果未指定分片大小，使用默认值24小时用于估算
        chunk_hours_for_estimate = time_chunk_hours if time_chunk_hours is not None else 24
        estimated_tasks = len(device_ids) * max(1, int(total_hours / chunk_hours_for_estimate))

        self.logger.info(
            f"[调度] 开始调度指标: {metric_key}",
            extra={
                "extra_data": {
                    "指标键": metric_key,
                    "设备ID列表": device_ids,
                    "设备数量": len(device_ids),
                    "时间范围": time_range_str,
                    "总小时数": round(total_hours, 2),
                    "时间分片小时数": time_chunk_hours,
                    "预估任务数": estimated_tasks,
                }
            },
        )

        metric_start_time = time.time()

        # 1. 创建任务列表
        tasks = self.create_tasks(
            metric_key=metric_key,
            device_ids=device_ids,
            start_time=start_time,
            end_time=end_time,
            time_chunk_hours=time_chunk_hours,
        )

        # 2. 定义计算函数（根据 metric_key 动态加载）
        calculator_func = self._get_calculator_func(metric_key)

        # 3. 并行执行任务
        results = self.execute_tasks(tasks, calculator_func)

        # 4. 汇总结果
        success_count = sum(1 for r in results if r.success)
        failure_count = sum(1 for r in results if not r.success)
        total_points = sum(r.results_count for r in results if r.success)
        total_duration = time.time() - metric_start_time
        avg_duration_per_task = total_duration / len(tasks) if tasks else 0

        # 增强日志：方法结束
        self.logger.info(
            f"[调度] 指标调度完成: {metric_key}",
            extra={
                "extra_data": {
                    "指标键": metric_key,
                    "总任务数": len(tasks),
                    "成功任务数": success_count,
                    "失败任务数": failure_count,
                    "成功率": f"{(success_count / len(tasks) * 100):.1f}%" if tasks else "0%",
                    "总记录数": total_points,
                    "总执行时长秒": round(total_duration, 2),
                    "平均任务时长秒": round(avg_duration_per_task, 2),
                }
            },
        )

        return {
            "total_tasks": len(tasks),
            "success_count": success_count,
            "failure_count": failure_count,
            "success_rate": f"{(success_count / len(tasks) * 100):.1f}%" if tasks else "0%",
            "total_points": total_points,
            "total_duration_seconds": round(total_duration, 2),
            "avg_duration_per_task_seconds": round(avg_duration_per_task, 2),
            "results": results,
        }

    def execute_tasks(self, tasks: List[Task], calculator_func: Callable[[Task], TaskResult]) -> List[TaskResult]:
        """
        并行执行任务（使用 ThreadPoolExecutor）

        Args:
            tasks: 任务列表
            calculator_func: 计算函数（接收 Task，返回 TaskResult）

        Returns:
            任务结果列表
        """
        results = []
        futures = {}

        # 提交所有任务
        for task in tasks:
            future = self.executor.submit(self._execute_single_task, task, calculator_func)
            futures[future] = task

        # 等待任务完成
        completed_count = 0
        total_count = len(tasks)
        batch_start_time = time.time()
        completed_durations = []

        for future in as_completed(futures):
            task = futures[future]
            try:
                result = future.result()
                results.append(result)
                completed_durations.append(result.duration_seconds)

                completed_count += 1
                progress = (completed_count / total_count) * 100

                # 计算预计剩余时间
                elapsed_time = time.time() - batch_start_time
                avg_time_per_task = elapsed_time / completed_count if completed_count > 0 else 0
                remaining_tasks = total_count - completed_count
                estimated_remaining_time = avg_time_per_task * remaining_tasks

                # 增强日志：包含时间范围、已用时间、预计剩余时间
                task_time_range = (
                    f"{task.start_time.strftime('%Y-%m-%d %H:%M:%S')} ~ {task.end_time.strftime('%Y-%m-%d %H:%M:%S')}"
                )

                self.logger.info(
                    f"[调度] 任务进度: {completed_count}/{total_count} ({progress:.1f}%)",
                    extra={
                        "extra_data": {
                            "任务ID": task.task_id,
                            "设备ID": task.device_id,
                            "指标键": task.metric_key,
                            "时间范围": task_time_range,
                            "成功": result.success,
                            "结果数量": result.results_count,
                            "任务时长秒": round(result.duration_seconds, 2),
                            "已用时长秒": round(elapsed_time, 2),
                            "预计剩余时长秒": round(estimated_remaining_time, 2),
                            "平均任务时长秒": round(avg_time_per_task, 2),
                        }
                    },
                )

            except Exception as e:
                self.logger.error(
                    f"[调度] 任务执行异常: {str(e)}",
                    extra={
                        "extra_data": {
                            "任务ID": task.task_id,
                            "设备ID": task.device_id,
                            "指标键": task.metric_key,
                            "时间范围": f"{task.start_time.strftime('%Y-%m-%d %H:%M:%S')} ~ {task.end_time.strftime('%Y-%m-%d %H:%M:%S')}",
                            "错误信息": str(e),
                        }
                    },
                )
                results.append(
                    TaskResult(
                        task_id=task.task_id,
                        device_id=task.device_id,
                        metric_key=task.metric_key,
                        success=False,
                        results_count=0,
                        error_message=str(e),
                    )
                )

        return results

    def _execute_single_task(self, task: Task, calculator_func: Callable[[Task], TaskResult]) -> TaskResult:
        """
        执行单个任务（带重试）

        Args:
            task: 任务
            calculator_func: 计算函数

        Returns:
            任务结果
        """
        max_retries = 3

        # 增强日志：任务开始
        task_time_range = (
            f"{task.start_time.strftime('%Y-%m-%d %H:%M:%S')} ~ {task.end_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.logger.info(
            f"[调度] 任务开始执行",
            extra={
                "extra_data": {
                    "任务ID": task.task_id,
                    "设备ID": task.device_id,
                    "指标键": task.metric_key,
                    "泵站ID": task.station_id,
                    "时间范围": task_time_range,
                    "优先级": task.priority,
                }
            },
        )

        for attempt in range(max_retries + 1):
            try:
                start_time = time.time()
                result = calculator_func(task)
                duration = time.time() - start_time
                result.duration_seconds = duration

                # 增强日志：任务结束
                self.logger.info(
                    f"[调度] 任务执行{'成功' if result.success else '失败'}",
                    extra={
                        "extra_data": {
                            "任务ID": task.task_id,
                            "设备ID": task.device_id,
                            "指标键": task.metric_key,
                            "时间范围": task_time_range,
                            "成功": result.success,
                            "结果数量": result.results_count,
                            "执行时长秒": round(duration, 2),
                            "错误信息": result.error_message if not result.success else None,
                        }
                    },
                )

                return result

            except Exception as e:
                if attempt < max_retries:
                    self.logger.warning(
                        f"[调度] 任务失败，重试 {attempt + 1}/{max_retries}",
                        extra={
                            "extra_data": {
                                "任务ID": task.task_id,
                                "设备ID": task.device_id,
                                "指标键": task.metric_key,
                                "时间范围": task_time_range,
                                "尝试次数": attempt + 1,
                                "最大重试次数": max_retries,
                                "错误信息": str(e),
                            }
                        },
                    )
                    time.sleep(2**attempt)  # 指数退避
                else:
                    raise

    def _get_calculator_func(self, metric_key: str) -> Callable[[Task], TaskResult]:
        """
        获取指标的计算函数

        Args:
            metric_key: 指标键

        Returns:
            计算函数
        """
        # 根据 metric_key 动态加载对应的计算器
        if metric_key == "pump_flow_rate":
            from app.services.calculation.metrics.pump_flow_rate import calculate_pump_flow_rate

            return calculate_pump_flow_rate
        elif metric_key == "pump_inlet_pressure":
            from app.services.calculation.metrics.pump_inlet_pressure import calculate_pump_inlet_pressure

            return calculate_pump_inlet_pressure
        elif metric_key == "pump_head":
            from app.services.calculation.metrics.pump_head import calculate_pump_head

            return calculate_pump_head
        elif metric_key == "pump_efficiency":
            from app.services.calculation.metrics.pump_efficiency import calculate_pump_efficiency

            return calculate_pump_efficiency
        elif metric_key == "pump_speed":
            from app.services.calculation.metrics.pump_speed import calculate_pump_speed

            return calculate_pump_speed
        elif metric_key == "pump_shaft_power":
            from app.services.calculation.metrics.pump_shaft_power import calculate_pump_shaft_power

            return calculate_pump_shaft_power
        elif metric_key == "pump_torque":
            from app.services.calculation.metrics.pump_torque import calculate_pump_torque

            return calculate_pump_torque
        elif metric_key == "main_pipeline_inlet_pressure":
            from app.services.calculation.metrics.main_pipeline_inlet_pressure import calculate_main_pipeline_inlet_pressure

            return calculate_main_pipeline_inlet_pressure
        elif metric_key == "pump_hydraulic_power":
            from app.services.calculation.metrics.pump_hydraulic_power import calculate_pump_hydraulic_power

            return calculate_pump_hydraulic_power
        else:
            raise NotImplementedError(f"指标 {metric_key} 的计算器尚未实现")

    def shutdown(self):
        """关闭调度器"""
        self.executor.shutdown(wait=True)
        self.logger.info("[调度] 调度器已关闭")

    @lru_cache(maxsize=1000)
    def _get_station_id(self, device_id: int) -> int:
        """
        获取设备所属泵站ID

        从 dim_devices 表查询设备所属泵站，使用 LRU 缓存避免重复查询。

        Args:
            device_id: 设备ID

        Returns:
            泵站ID

        Raises:
            ValueError: 设备不存在时
            DatabaseError: 数据库查询失败时

        Note:
            数据已在 DataFilter 阶段过滤（running=1），无需硬编码阈值过滤
        """
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    sql = "SELECT station_id FROM dim_devices WHERE id = %s"
                    cur.execute(sql, (device_id,))
                    result = cur.fetchone()

                    if result is None:
                        raise ValueError(f"设备不存在: device_id={device_id}")

                    station_id = result[0]
                    self.logger.debug(f"[调度] 查询设备所属泵站: device_id={device_id}, station_id={station_id}")
                    return station_id

        except ValueError:
            # 设备不存在，直接抛出
            raise
        except Exception as e:
            # 数据库查询失败
            self.logger.error(f"[调度] 查询设备所属泵站失败: device_id={device_id}, error={e}")
            raise
