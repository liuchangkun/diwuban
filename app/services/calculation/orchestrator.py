"""
CalculationOrchestrator - 主流程编排器

⚠️ **DEPRECATED**: 此模块正在逐步废弃，请迁移到新的流水线架构
    - 新架构位置: app/services/calculation/shared/ 和 app/services/calculation/metrics/
    - 迁移指南: 见 缺失指标计算改造/pump_flow_rate/11-pump_flow_rate重构任务跟踪.md
    - 废弃原因:
      1. 文件过大（2659行，违反≤600行规则）
      2. 包含硬编码阈值逻辑（已在新架构中移除）
      3. 缺乏完整的日志追踪（新架构支持 trace_id/span_id）
    - 废弃时间: 2025-01-14
    - 计划删除: 2025-02-14（30天后）

协调所有组件，完成缺失指标的计算流程。

核心流程:
1. 加载数据
2. 分析依赖关系
3. 选择计算方法
4. 执行计算
5. 验证结果
6. 批量写入

使用示例:
    from app.services.calculation.orchestrator import CalculationOrchestrator

    orchestrator = CalculationOrchestrator()
    result = orchestrator.calculate_missing_metrics(
        station_id=1,
        device_id=1,
        start_time='2025-01-01 00:00:00',
        end_time='2025-01-01 01:00:00',
        metrics=['pump_flow_rate', 'pump_head']
    )
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict

import numpy as np

from app.adapters.db import get_connection
from app.services.calculation.calculators import get_calculator
from app.services.calculation.dependency_analyzer import DependencyAnalyzer
from app.services.calculation.method_selector import MethodSelector
from app.services.calculation.metric_mapper import metric_mapper
from app.services.calculation.validator import PhysicsValidator
from app.services.calculation.performance_monitor import PerformanceMonitor
from app.services.calculation.adaptive_batch import AdaptiveBatchManager
from app.services.calculation.domain import CalculationContext, MethodDescriptor
from app.services.calculation.stats_collector import StatsCollector
from app.services.calculation.calculators import get_calculator_unified
from app.services.calculation.validation_reporter import ValidationReporter
from app.services.calculation.parameter_optimizer import ParameterOptimizer
from app.services.calculation.audit import generate_source_hint


logger = logging.getLogger(__name__)


class CalculationOrchestrator:
    """
    主流程编排器

    协调所有组件，完成缺失指标的计算流程。

    Attributes:
        dependency_analyzer: 依赖分析器
        method_selector: 方法选择器
        validator: 验证器
        parameter_optimizer: 参数优化器（可选）
    """

    def __init__(self, enable_adaptive: bool = True, enable_optimization: bool = False):
        """
        初始化编排器

        Args:
            enable_adaptive: 是否启用自适应性能优化（默认True）
            enable_optimization: 是否启用参数优化（默认False）
        """
        logger.info(
            "[流程-开始] [计算编排器初始化]",
            extra={"extra_data": {
                "enable_adaptive": enable_adaptive,
                "enable_optimization": enable_optimization
            }},
        )

        self.dependency_analyzer = DependencyAnalyzer()
        self.method_selector = MethodSelector()
        self.validator = PhysicsValidator()

        # 验证报告生成器
        self.validation_reporter = ValidationReporter()

        # 参数优化器（可选）
        self.parameter_optimizer: Optional[ParameterOptimizer] = None
        self.enable_optimization = enable_optimization

        if enable_optimization:
            self.parameter_optimizer = ParameterOptimizer(forgetting_factor=0.98)
            logger.info("[核心-初始化] 参数优化器已启用")

        # 性能监控和自适应管理（延迟初始化）
        self.performance_monitor: Optional[PerformanceMonitor] = None
        self.adaptive_batch: Optional[AdaptiveBatchManager] = None
        self.enable_adaptive = enable_adaptive

        if enable_adaptive:
            # 初始化自适应批量管理器
            self.adaptive_batch = AdaptiveBatchManager({
                'enabled': True,
                'initial_size': 10000,
                'min_size': 1000,
                'max_size': 50000,
                'memory_limit_mb': 1000,
                'target_throughput': 10000
            })
            logger.info("[核心-初始化] 自适应性能优化已启用")

        logger.info("[核心-初始化] CalculationOrchestrator 初始化完成")
        # caches for device type and metric allowances
        self._device_type_cache: Dict[Tuple[int, int], Optional[str]] = {}
        self._allowed_map_cache: Dict[str, Set[str]] = {}

    def _get_device_type(self, station_id: int, device_id: int) -> Optional[str]:
        key = (station_id, device_id)
        if key in self._device_type_cache:
            return self._device_type_cache[key]
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT type FROM public.dim_devices WHERE station_id=%s AND id=%s",
                        (station_id, device_id),
                    )
                    row = cur.fetchone()
                    dtype = row[0] if row else None
        except Exception:
            dtype = None
        self._device_type_cache[key] = dtype
        return dtype

    def _metric_allowed_for_device(self, metric_key: str, device_type: str) -> bool:
        allowed = self._allowed_map_cache.get(metric_key)
        if allowed is None:
            try:
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            SELECT allowed_device_types
                            FROM public.calculation_method_registry
                            WHERE metric_key=%s AND is_enabled
                            ORDER BY priority DESC
                            LIMIT 1
                            """,
                            (metric_key,),
                        )
                        row = cur.fetchone()
                        allowed = set(row[0]) if row and row[0] else set()
            except Exception:
                allowed = set()
            self._allowed_map_cache[metric_key] = allowed
        # if not configured, be permissive
        if not allowed:
            return True
        return device_type in allowed


    def load_data(
        self,
        station_id: int,
        device_id: int,
        start_time: str,
        end_time: str,
        metric_keys: List[str],
        filter_running: bool = True,
        filter_quality: bool = True,
    ) -> tuple[Dict[str, np.ndarray], np.ndarray]:
        """Load aligned time-series data for a device, including upstream dependencies."""
        logger.info(
            "[流程-开始] [加载设备数据]",
            extra={
                "extra_data": {
                    "station_id": station_id,
                    "device_id": device_id,
                    "start_time": start_time,
                    "end_time": end_time,
                    "metric_count": len(metric_keys),
                    "filter_running": filter_running,
                    "filter_quality": filter_quality,
                }
            },
        )

        device_metrics, station_metrics = self._collect_metric_requirements(metric_keys)
        required_metric_keys = sorted(device_metrics | station_metrics | set(metric_keys))

        logger.info(
            "[流程-阶段] [依赖分析完成]",
            extra={
                "extra_data": {
                    "requested_metrics": len(metric_keys),
                    "device_metrics": len(device_metrics),
                    "station_metrics": len(station_metrics),
                    "total_required": len(required_metric_keys),
                }
            },
        )

        metric_ids = metric_mapper.keys_to_ids(required_metric_keys)
        if not metric_ids:
            logger.warning(
                "[流程-错误] [指标ID映射失败]",
                extra={"extra_data": {"metric_keys": required_metric_keys}},
            )
            return {}, np.array([])

        logger.info(
            "[流程-阶段] [开始查询数据库]",
            extra={"extra_data": {"metric_ids_count": len(metric_ids)}},
        )

        timestamp_set: Set[datetime] = set()
        device_rows = []
        station_rows = []

        with get_connection() as conn:
            with conn.cursor() as cur:
                if filter_running:
                    query_device = """
                        SELECT fm.ts_bucket, fm.metric_id, fm.value
                        FROM fact_measurements fm
                        INNER JOIN mv_device_running_1s dr
                            ON fm.station_id = dr.station_id
                            AND fm.device_id = dr.device_id
                            AND fm.ts_bucket = dr.ts_bucket
                        WHERE fm.station_id = %s
                          AND fm.device_id = %s
                          AND fm.ts_bucket >= %s::timestamptz
                          AND fm.ts_bucket < %s::timestamptz
                          AND fm.metric_id = ANY(%s)
                          AND fm.value IS NOT NULL
                          AND dr.running = 1
                    """
                else:
                    query_device = """
                        SELECT ts_bucket, metric_id, value
                        FROM fact_measurements
                        WHERE station_id = %s
                          AND device_id = %s
                          AND ts_bucket >= %s::timestamptz
                          AND ts_bucket < %s::timestamptz
                          AND metric_id = ANY(%s)
                          AND value IS NOT NULL
                    """

                query_device += " ORDER BY ts_bucket, metric_id" if not filter_running else " ORDER BY fm.ts_bucket, fm.metric_id"

                cur.execute(query_device, (station_id, device_id, start_time, end_time, metric_ids))
                device_rows = cur.fetchall()
                timestamp_set.update(row[0] for row in device_rows)

                logger.info(
                    "[流程-阶段] [设备数据查询完成]",
                    extra={"extra_data": {"device_rows": len(device_rows)}},
                )

                if station_metrics:
                    station_metric_ids = metric_mapper.keys_to_ids(sorted(station_metrics))
                    if station_metric_ids:
                        query_station = """
                            SELECT ts_bucket, metric_id, value
                            FROM fact_measurements
                            WHERE station_id = %s
                              AND ts_bucket >= %s::timestamptz
                              AND ts_bucket < %s::timestamptz
                              AND metric_id = ANY(%s)
                              AND value IS NOT NULL
                        """
                        query_station += " ORDER BY ts_bucket, metric_id"
                        cur.execute(query_station, (station_id, start_time, end_time, station_metric_ids))
                        station_rows = cur.fetchall()
                        timestamp_set.update(row[0] for row in station_rows)

                        logger.info(
                            "[流程-阶段] [泵站数据查询完成]",
                            extra={"extra_data": {"station_rows": len(station_rows)}},
                        )

        if not timestamp_set:
            logger.warning(
                "[流程-跳过] [无有效数据点]",
                extra={
                    "extra_data": {
                        "station_id": station_id,
                        "device_id": device_id,
                    }
                },
            )
            return {}, np.array([])

        timestamps = np.array(sorted(timestamp_set))

        device_data: Dict[str, np.ndarray] = {
            key: np.full(len(timestamps), np.nan, dtype=float) for key in required_metric_keys
        }

        by_metric_device: dict[int, dict[datetime, float]] = defaultdict(dict)
        for ts_bucket, metric_id, value in device_rows:
            try:
                by_metric_device[metric_id][ts_bucket] = float(value)
            except (TypeError, ValueError):
                continue

        for metric_key in required_metric_keys:
            metric_id = metric_mapper.key_to_id(metric_key)
            if metric_id is None:
                continue
            ts_map = by_metric_device.get(metric_id)
            if not ts_map:
                continue
            arr = device_data[metric_key]
            for idx, ts_val in enumerate(timestamps):
                if ts_val in ts_map:
                    arr[idx] = ts_map[ts_val]

        if station_rows:
            by_metric_station: dict[int, dict[datetime, float]] = defaultdict(dict)
            for ts_bucket, metric_id, value in station_rows:
                try:
                    by_metric_station[metric_id][ts_bucket] = float(value)
                except (TypeError, ValueError):
                    continue

            for metric_key in station_metrics:
                metric_id = metric_mapper.key_to_id(metric_key)
                if metric_id is None:
                    continue
                ts_map = by_metric_station.get(metric_id)
                if not ts_map:
                    continue
                arr = device_data[metric_key]
                for idx, ts_val in enumerate(timestamps):
                    if ts_val in ts_map and np.isnan(arr[idx]):
                        arr[idx] = ts_map[ts_val]

        # 记录加载的指标详情（用于调试）
        loaded_metrics = {k: np.sum(~np.isnan(v)) for k, v in device_data.items() if not np.all(np.isnan(v))}
        logger.info(
            "[流程-完成] [数据加载完成]",
            extra={
                "extra_data": {
                    "station_id": station_id,
                    "device_id": device_id,
                    "timestamps": len(timestamps),
                    "metrics_loaded": len(loaded_metrics),
                    "loaded_metrics_detail": loaded_metrics,
                }
            },
        )

        return device_data, timestamps

    @staticmethod
    def _is_station_metric(metric_key: str) -> bool:
        prefixes = ("main_pipeline_", "pool_", "station_", "ambient_", "weather_", "pump_group_")
        exact = {"pool_liquid_level", "pump_group_outlet_pressure", "station_pressure", "station_flow_rate"}
        if metric_key in exact:
            return True
        return metric_key.startswith(prefixes)

    def _collect_metric_requirements(self, metric_keys: List[str]) -> tuple[Set[str], Set[str]]:
        required: Set[str] = set(metric_keys)
        queue: List[str] = list(metric_keys)

        while queue:
            current = queue.pop()
            dependencies = self.method_selector.get_union_dependencies(current)
            for dep in dependencies:
                if dep not in required:
                    required.add(dep)
                    if self.method_selector.get_all_methods(dep):
                        queue.append(dep)

        station_metrics = {key for key in required if self._is_station_metric(key)}
        device_metrics = required - station_metrics
        return device_metrics, station_metrics

    def load_station_data(
        self,
        station_id: int,
        start_time: str,
        end_time: str,
        metric_keys: List[str],
        filter_running: bool = True,
        filter_quality: bool = True
    ) -> tuple[Dict[int, Dict[str, np.ndarray]], np.ndarray]:
        """
        加载泵站级数据（所有设备的数据）

        Args:
            station_id: 泵站ID
            start_time: 开始时间
            end_time: 结束时间
            metric_keys: 需要加载的指标列表
            filter_running: 是否过滤停机数据（默认True）
            filter_quality: 是否过滤异常数据（默认True）

        Returns:
            (设备数据字典, 时间戳数组)
            - 设备数据字典：{device_id: {metric_key: numpy数组}}
            - 时间戳数组：基准时间序列
        """
        logger.info(
            f"加载泵站级数据：station_id={station_id}, "
            f"time=[{start_time}, {end_time}], metrics={metric_keys}"
        )

        # 转换metric_key到metric_id
        metric_ids = metric_mapper.keys_to_ids(metric_keys)

        if not metric_ids:
            logger.warning(f"没有找到有效的metric_id: {metric_keys}")
            return {}, np.array([])

        with get_connection() as conn:
            with conn.cursor() as cur:
                # 步骤1：获取该泵站所有设备
                query_devices = """
                    SELECT DISTINCT fm.device_id
                    FROM fact_measurements fm
                    JOIN public.dim_devices dd ON dd.id = fm.device_id
                    WHERE fm.station_id = %s
                      AND fm.ts_bucket >= %s::timestamptz
                      AND fm.ts_bucket < %s::timestamptz
                      AND COALESCE(dd.is_active, TRUE) = TRUE
                      AND COALESCE(NULLIF(dd.type,''),'') NOT IN ('clear_water_pool','other')
                    ORDER BY fm.device_id
                """
                cur.execute(query_devices, (station_id, start_time, end_time))
                device_rows = cur.fetchall()
                device_ids = [row[0] for row in device_rows]

                if not device_ids:
                    logger.warning(f"没有找到任何设备数据")
                    return {}, np.array([])

                logger.info(f"找到 {len(device_ids)} 个设备: {device_ids}")

                # 步骤2：获取基准时间序列（使用第一个设备的时间戳）
                if filter_running:
                    query_timestamps = """
                        SELECT DISTINCT fm.ts_bucket
                        FROM fact_measurements fm
                        INNER JOIN mv_device_running_1s dr
                            ON fm.station_id = dr.station_id
                            AND fm.device_id = dr.device_id
                            AND fm.ts_bucket = dr.ts_bucket
                        WHERE fm.station_id = %s
                          AND fm.ts_bucket >= %s::timestamptz
                          AND fm.ts_bucket < %s::timestamptz
                          AND dr.running = 1
                        ORDER BY fm.ts_bucket
                    """
                    cur.execute(query_timestamps, (station_id, start_time, end_time))
                else:
                    query_timestamps = """
                        SELECT DISTINCT ts_bucket
                        FROM fact_measurements
                        WHERE station_id = %s
                          AND ts_bucket >= %s::timestamptz
                          AND ts_bucket < %s::timestamptz
                        ORDER BY ts_bucket
                    """
                    cur.execute(query_timestamps, (station_id, start_time, end_time))

                timestamp_rows = cur.fetchall()

                if not timestamp_rows:
                    logger.warning(f"没有找到任何时间戳数据")
                    return {}, np.array([])

                # 创建基准时间序列
                timestamps = np.array([row[0] for row in timestamp_rows])
                logger.info(f"基准时间序列：{len(timestamps)} 个时间点")

                # 额外：站级（main_pipeline_*）一次性加载并对齐到基准时间轴
                station_level_keys = [k for k in metric_keys if k.startswith('main_pipeline_')]
                station_level_arrays = {}
                if station_level_keys:
                    station_metric_ids = metric_mapper.keys_to_ids(station_level_keys)
                    if station_metric_ids:
                        query_station = """
                            SELECT ts_bucket, metric_id, value
                            FROM fact_measurements
                            WHERE station_id = %s
                              AND ts_bucket >= %s::timestamptz
                              AND ts_bucket < %s::timestamptz
                              AND metric_id = ANY(%s)
                              AND value IS NOT NULL
                        """
                        query_station += " ORDER BY ts_bucket, metric_id"
                        cur.execute(query_station, (station_id, start_time, end_time, station_metric_ids))
                        rows = cur.fetchall()
                        # 构造每个 station-level 指标的对齐数组
                        by_mid = {}
                        for ts, mid, val in rows:
                            by_mid.setdefault(mid, {})[ts] = float(val)
                        for k in station_level_keys:
                            mid = metric_mapper.key_to_id(k)
                            arr = np.full(len(timestamps), np.nan, dtype=float)
                            if mid in by_mid:
                                mp = by_mid[mid]
                                for i, ts in enumerate(timestamps):
                                    if ts in mp:
                                        arr[i] = mp[ts]
                            station_level_arrays[k] = arr

                # 步骤3：为每个设备加载数据
                station_data = {}
                for device_id in device_ids:
                    # 查询该设备的数据
                    if filter_running:

                        query_data = """
                            SELECT fm.ts_bucket, fm.metric_id, fm.value
                            FROM fact_measurements fm
                            INNER JOIN mv_device_running_1s dr
                                ON fm.station_id = dr.station_id
                                AND fm.device_id = dr.device_id
                                AND fm.ts_bucket = dr.ts_bucket
                            WHERE fm.station_id = %s
                              AND fm.device_id = %s
                              AND fm.ts_bucket >= %s::timestamptz
                              AND fm.ts_bucket < %s::timestamptz
                              AND fm.metric_id = ANY(%s)
                              AND fm.value IS NOT NULL
                              AND dr.running = 1
                        """
                    else:
                        query_data = """
                            SELECT ts_bucket, metric_id, value
                            FROM fact_measurements
                            WHERE station_id = %s
                              AND device_id = %s
                              AND ts_bucket >= %s::timestamptz
                              AND ts_bucket < %s::timestamptz
                              AND metric_id = ANY(%s)
                              AND value IS NOT NULL
                        """

                    query_data += " ORDER BY ts_bucket, metric_id" if not filter_running else " ORDER BY fm.ts_bucket, fm.metric_id"

                    cur.execute(query_data, (station_id, device_id, start_time, end_time, metric_ids))
                    data_rows = cur.fetchall()

                    # 组织数据并进行时间对齐
                    device_data = {}
                    for metric_key in metric_keys:
                        metric_id = metric_mapper.key_to_id(metric_key)
                        if metric_id is None:
                            continue

                        # 创建一个与基准时间序列长度相同的数组，初始值为NaN
                        aligned_values = np.full(len(timestamps), np.nan, dtype=float)

                        # 提取该指标的所有数据点
                        metric_data = [(row[0], row[2]) for row in data_rows if row[1] == metric_id]

                        # 将数据点对齐到基准时间序列
                        for ts, value in metric_data:
                            # 找到该时间戳在基准时间序列中的索引
                            idx = np.where(timestamps == ts)[0]
                            if len(idx) > 0:
                                aligned_values[idx[0]] = value

                        device_data[metric_key] = aligned_values

                        # 统计有效数据点数量
                        valid_count = np.sum(~np.isnan(aligned_values))
                        logger.debug(
                            f"设备 {device_id} 指标 {metric_key}: {valid_count}/{len(aligned_values)} 个有效数据点"
                        )


                        # 注入站级指标数组（已按基准时间轴对齐）
                        if station_level_arrays:
                            for k, arr in station_level_arrays.items():
                                device_data[k] = arr.copy()


                    station_data[device_id] = device_data

                logger.info(
                    f"泵站级数据加载完成：{len(station_data)} 个设备，"
                    f"{len(metric_keys)} 个指标，{len(timestamps)} 个时间点"
                )

        return station_data, timestamps

    def _get_running_device_count(
        self,
        station_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> int:
        """
        获取实际运行设备数量

        从mv_device_running_1s表查询指定时间范围内运行状态为1的设备数量。

        Args:
            station_id: 泵站ID
            start_time: 开始时间
            end_time: 结束时间


        Returns:
            运行设备数量，查询失败时返回默认值2
        """
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    # 查询时间范围内运行状态为1的设备数量（取众数）
                    query = """
                        SELECT COUNT(DISTINCT device_id) as running_count
                        FROM mv_device_running_1s
                        WHERE station_id = %s
                          AND ts_bucket >= %s
                          AND ts_bucket < %s
                          AND running = 1
                    """

                    cur.execute(query, (station_id, start_time, end_time))
                    row = cur.fetchone()

                    if row and row[0] is not None:
                        running_count = int(row[0])

                        # 如果查询到的运行设备数为0，使用默认值2（可能是数据问题）
                        if running_count == 0:
                            logger.warning(
                                f"查询到运行设备数量为0，使用默认值2（可能是设备运行状态数据缺失）",
                                extra={
                                    "station_id": station_id,
                                    "start_time": start_time,
                                    "end_time": end_time
                                }
                            )
                            return 2

                        logger.debug(
                            f"查询到运行设备数量: {running_count}",
                            extra={
                                "station_id": station_id,
                                "start_time": start_time,
                                "end_time": end_time
                            }
                        )
                        return running_count
                    else:
                        logger.warning(
                            f"未查询到运行设备数据，使用默认值2",
                            extra={"station_id": station_id}
                        )
                        return 2

        except Exception as e:
            logger.error(
                f"查询运行设备数量失败: {e}，使用默认值2",
                exc_info=True,
                extra={"station_id": station_id}
            )
            return 2

    def load_parameters(
        self,
        device_id: int,
        method_id: str,
        station_id: Optional[int] = None
    ) -> Dict[str, any]:
        """
        加载计算参数（6层参数优先级）

        参数来源优先级（从低到高）：
        1. 全局计算参数（calculation_parameters, device_id=NULL, station_id=NULL）
        2. 全局默认额定参数（global_default_rated_params）
        3. 设备额定参数（device_rated_params, device_id=X）
        3.5. 泵站级额定参数（device_rated_params, station_id=X, device_id=NULL）
        4. 泵站级计算参数（calculation_parameters, station_id=X, device_id=NULL）
        5. 设备级计算参数（calculation_parameters, device_id=X）

        Args:
            device_id: 设备ID
            method_id: 方法ID
            station_id: 泵站ID（可选）

        Returns:
            参数字典（值可以是float或str）
        """
        params = {}
        param_sources = {}  # 记录参数来源（用于调试）

        with get_connection() as conn:
            with conn.cursor() as cur:
                # 层级1：加载全局计算参数（最低优先级）
                query = """
                    SELECT param_name, param_value, param_value_text, param_type
                    FROM calculation_parameters
                    WHERE device_id IS NULL
                      AND station_id IS NULL
                      AND method_id = %s
                """
                cur.execute(query, (method_id,))
                for row in cur.fetchall():
                    param_name, param_value, param_value_text, param_type = row
                    # 根据param_type选择使用param_value或param_value_text
                    if param_type == 'string' and param_value_text is not None:
                        params[param_name] = param_value_text
                    else:
                        params[param_name] = float(param_value)
                    param_sources[param_name] = 'global'

                # 层级2：加载全局默认额定参数（如果设备没有额定参数）
                # 先检查设备是否有额定参数
                query = """
                    SELECT COUNT(*)
                    FROM device_rated_params
                    WHERE device_id = %s AND value_numeric IS NOT NULL
                """
                cur.execute(query, (device_id,))
                has_rated_params = cur.fetchone()[0] > 0

                if not has_rated_params:
                    # 使用全局默认额定参数
                    query = """
                        SELECT param_key, default_value
                        FROM global_default_rated_params
                    """
                    cur.execute(query)
                    for row in cur.fetchall():
                        params[row[0]] = float(row[1])
                        param_sources[row[0]] = 'global_default_rated'

                    logger.warning(
                        f"设备{device_id}没有额定参数，使用全局默认值",
                        extra={"device_id": device_id, "method_id": method_id}
                    )

                # 层级3：加载设备额定参数
                query = """
                    SELECT param_key, value_numeric
                    FROM device_rated_params
                    WHERE device_id = %s AND value_numeric IS NOT NULL
                """
                cur.execute(query, (device_id,))
                for row in cur.fetchall():
                    params[row[0]] = float(row[1])
                    param_sources[row[0]] = 'device_rated'

                # 层级3.5：加载泵站级额定参数（新增）
                if station_id is not None:
                    query = """
                        SELECT param_key, value_numeric
                        FROM device_rated_params
                        WHERE station_id = %s
                          AND device_id IS NULL
                          AND value_numeric IS NOT NULL
                    """
                    cur.execute(query, (station_id,))
                    for row in cur.fetchall():
                        params[row[0]] = float(row[1])
                        param_sources[row[0]] = 'station_rated'

                # 层级4：加载泵站级计算参数
                if station_id is not None:
                    query = """
                        SELECT param_name, param_value, param_value_text, param_type
                        FROM calculation_parameters
                        WHERE station_id = %s
                          AND device_id IS NULL
                          AND method_id = %s
                    """
                    cur.execute(query, (station_id, method_id))
                    for row in cur.fetchall():
                        param_name, param_value, param_value_text, param_type = row
                        if param_type == 'string' and param_value_text is not None:
                            params[param_name] = param_value_text
                        else:
                            params[param_name] = float(param_value)
                        param_sources[param_name] = 'station'

                # 层级5：加载设备级计算参数（最高优先级）
                query = """
                    SELECT param_name, param_value, param_value_text, param_type
                    FROM calculation_parameters
                    WHERE device_id = %s AND method_id = %s
                """
                cur.execute(query, (device_id, method_id))
                for row in cur.fetchall():
                    param_name, param_value, param_value_text, param_type = row
                    if param_type == 'string' and param_value_text is not None:
                        params[param_name] = param_value_text
                    else:
                        params[param_name] = float(param_value)
                    param_sources[param_name] = 'device'

        logger.debug(
            f"[参数加载] device_id={device_id}, method_id={method_id}, "
            f"params_count={len(params)}, sources={param_sources}"
        )

        return params

    def _get_measured_data(
        self,
        station_id: int,
        device_id: int,
        metric_key: str,
        timestamps: np.ndarray
    ) -> Optional[np.ndarray]:
        """
        获取实测数据用于参数优化

        Args:
            station_id: 泵站ID
            device_id: 设备ID
            metric_key: 指标键
            timestamps: 时间戳数组

        Returns:
            实测数据数组，如果没有数据则返回None
        """
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    # 查询实测数据
                    cur.execute(
                        """
                        SELECT fm.ts_bucket, fm.value
                        FROM fact_measurements fm
                        JOIN dim_metric_config mc ON mc.id = fm.metric_id
                        WHERE fm.station_id = %s
                          AND fm.device_id = %s
                          AND mc.metric_key = %s
                          AND fm.ts_bucket = ANY(%s)
                          AND fm.value IS NOT NULL
                        ORDER BY fm.ts_bucket
                        """,
                        (station_id, device_id, metric_key, list(timestamps))
                    )
                    rows = cur.fetchall()

                    if not rows:
                        return None

                    # 构建时间戳到值的映射
                    ts_to_value = {row[0]: float(row[1]) for row in rows}

                    # 按照timestamps顺序构建数组
                    measured_values = []
                    for ts in timestamps:
                        if ts in ts_to_value:
                            measured_values.append(ts_to_value[ts])
                        else:
                            measured_values.append(np.nan)

                    return np.array(measured_values)

        except Exception as e:
            logger.warning(
                f"获取实测数据失败: {e}",
                extra={
                    "extra_data": {
                        "station_id": station_id,
                        "device_id": device_id,
                        "metric_key": metric_key
                    }
                }
            )
            return None

    def _get_current_parameters(
        self,
        method_id: str,
        device_id: Optional[int] = None,
        station_id: Optional[int] = None
    ) -> Dict[str, float]:
        """
        获取当前计算参数

        Args:
            method_id: 方法ID
            device_id: 设备ID（可选）
            station_id: 泵站ID（可选）

        Returns:
            参数字典
        """
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    # 优先查询设备特定参数
                    if device_id is not None:
                        cur.execute(
                            """
                            SELECT param_name, param_value
                            FROM calculation_parameters
                            WHERE method_id = %s
                              AND device_id = %s
                              AND (station_id IS NULL OR station_id = %s)
                            """,
                            (method_id, device_id, station_id)
                        )
                        rows = cur.fetchall()

                        if rows:
                            return {row[0]: float(row[1]) for row in rows}

                    # 查询全局默认参数
                    cur.execute(
                        """
                        SELECT param_name, param_value
                        FROM calculation_parameters
                        WHERE method_id = %s
                          AND device_id IS NULL
                          AND station_id IS NULL
                        """,
                        (method_id,)
                    )
                    rows = cur.fetchall()

                    return {row[0]: float(row[1]) for row in rows}

        except Exception as e:
            logger.warning(
                f"获取当前参数失败: {e}",
                extra={
                    "extra_data": {
                        "method_id": method_id,
                        "device_id": device_id,
                        "station_id": station_id
                    }
                }
            )
            return {}

    def write_results(
        self,
        station_id: int,
        device_id: int,
        metric_key: str,
        timestamps: np.ndarray,
        values: np.ndarray,
        method_id: Optional[str] = None,
        is_cyclic: bool = False
    ) -> int:
        """
        批量写入计算结果到fact_measurements表

        Args:
            station_id: 泵站ID
            device_id: 设备ID
            metric_key: 指标键
            timestamps: 时间戳数组
            values: 值数组
            method_id: 计算方法ID，用于构造 source_hint（可选）
            is_cyclic: 是否为循环依赖指标，默认False

        Returns:
            实际写入的数据点数量

        Note:
            - source_hint 构造规则：
              * 循环指标：calculation_cyclic_{metric_key}
              * 非循环指标：calculation_{method_id}
              * 其他情况：calculation_orchestrator
        """
        logger.info(
            "[流程-开始] [批量写入计算结果]",
            extra={
                "extra_data": {
                    "station_id": station_id,
                    "device_id": device_id,
                    "metric_key": metric_key,
                    "total_points": len(values),
                    "is_cyclic": is_cyclic,
                }
            },
        )

        # 获取metric_id
        metric_id = metric_mapper.key_to_id(metric_key)
        if metric_id is None:
            logger.error(
                "[流程-错误] [指标ID映射失败]",
                extra={"extra_data": {"metric_key": metric_key}},
            )
            return 0

        # 检查 timestamps 和 values 长度是否一致
        if len(timestamps) != len(values):
            logger.warning(
                "[流程-警告] [数组长度不一致，尝试对齐]",
                extra={
                    "extra_data": {
                        "metric_key": metric_key,
                        "timestamps_len": len(timestamps),
                        "values_len": len(values),
                    }
                },
            )
            # 对齐到较短的长度
            min_len = min(len(timestamps), len(values))
            timestamps = timestamps[:min_len]
            values = values[:min_len]

        # 过滤掉NaN值
        valid_mask = ~np.isnan(values)
        valid_timestamps = timestamps[valid_mask]
        valid_values = values[valid_mask]

        if len(valid_values) == 0:
            logger.warning(
                "[流程-跳过] [无有效数据点]",
                extra={
                    "extra_data": {
                        "metric_key": metric_key,
                        "total_points": len(values),
                    }
                },
            )
            return 0

        logger.info(
            "[流程-阶段] [数据准备完成]",
            extra={
                "extra_data": {
                    "metric_key": metric_key,
                    "metric_id": metric_id,
                    "valid_points": len(valid_values),
                    "total_points": len(values),
                }
            },
        )

        # 准备批量插入数据
        # 使用ON CONFLICT DO UPDATE处理重复数据
        # 注意：fact_measurements表没有updated_at字段，只有inserted_at字段
        # id字段使用随机生成的大整数（类似现有数据的id值）
        insert_query = """
            INSERT INTO fact_measurements (
                id, station_id, device_id, metric_id, ts_raw, ts_bucket,
                value, source_hint
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (station_id, device_id, metric_id, ts_bucket)
            DO UPDATE SET
                value = EXCLUDED.value,
                source_hint = EXCLUDED.source_hint
        """

        # 准备数据

        # 根据计算类型构造 source_hint（使用审计模块生成扩展格式）
        if is_cyclic:
            source_hint = f"calculation:cyclic_{metric_key}"
        elif method_id:
            # 使用审计模块生成扩展格式的 source_hint
            # 包含：method_id, params_version, priority, duration_ms
            params_version = datetime.now().strftime("%Y%m%d")  # 当前日期作为参数版本
            # 注意：priority 和 duration_ms 需要从上下文获取，这里暂时不包含
            source_hint = generate_source_hint(
                method_id=method_id,
                params_version=params_version
            )
        else:
            source_hint = "calculation:orchestrator"  # 兼容旧逻辑

        # 生成随机ID（使用时间戳的哈希值）
        import random
        rows = [
            (
                random.randint(1000000000000, 9999999999999999),  # 随机生成大整数作为id
                station_id,
                device_id,
                metric_id,
                ts,  # ts_raw
                ts,  # ts_bucket
                float(val),
                source_hint,
            )
            for ts, val in zip(valid_timestamps, valid_values)
        ]

        # 初始化性能监控（如果启用）
        if self.enable_adaptive and self.performance_monitor is None:
            self.performance_monitor = PerformanceMonitor(
                station_id=station_id,
                device_id=device_id
            )

        # 批量写入（自适应批量大小）
        written_count = 0
        batch_number = 0

        # 获取初始批量大小
        if self.adaptive_batch and self.adaptive_batch.is_enabled():
            batch_size = self.adaptive_batch.get_initial_size()
        else:
            batch_size = 10000  # 默认批量大小

        try:
            write_start = time.time()

            with get_connection() as conn:
                with conn.cursor() as cur:
                    # 分批写入
                    i = 0
                    while i < len(rows):
                        batch_number += 1

                        # 开始批次监控
                        if self.performance_monitor:
                            self.performance_monitor.start_batch(
                                batch_number=batch_number,
                                time_window_minutes=60  # 固定值，实际应从参数传入
                            )

                        batch_start = time.time()
                        batch = rows[i:i + batch_size]

                        # 使用executemany批量插入
                        cur.executemany(insert_query, batch)
                        written_count += len(batch)

                        batch_time = time.time() - batch_start

                        # 结束批次监控并获取性能指标
                        if self.performance_monitor:
                            performance = self.performance_monitor.end_batch(
                                batch_size=len(batch),
                                data_points=len(batch)
                            )

                            # 自适应调整批量大小
                            if self.adaptive_batch and self.adaptive_batch.is_enabled():
                                new_batch, reason = self.adaptive_batch.adjust(
                                    batch_size,
                                    performance
                                )

                                if new_batch != batch_size:
                                    # 记录调整
                                    performance['adjustment_type'] = 'batch'
                                    performance['adjustment_reason'] = reason
                                    performance['old_value'] = batch_size
                                    performance['new_value'] = new_batch

                                    logger.info(
                                        f"调整批量大小: {batch_size} → {new_batch}, "
                                        f"原因: {reason}"
                                    )

                                    batch_size = new_batch

                            # 保存性能指标到数据库（每10个批次保存一次）
                            if batch_number % 10 == 0:
                                self.performance_monitor.save_to_db(performance)
                        else:
                            # 旧的简单自适应逻辑（向后兼容）
                            if batch_time > 0:
                                write_speed = len(batch) / batch_time
                                min_batch_size = 1000
                                max_batch_size = 50000

                                if write_speed < 5000 and batch_size > min_batch_size:
                                    batch_size = max(min_batch_size, batch_size // 2)
                                    logger.debug(f"写入速度慢({write_speed:.0f}条/秒)，减小批量至{batch_size}")
                                elif write_speed > 20000 and batch_size < max_batch_size:
                                    batch_size = min(max_batch_size, batch_size * 2)
                                    logger.debug(f"写入速度快({write_speed:.0f}条/秒)，增大批量至{batch_size}")

                        logger.debug(f"已写入 {written_count}/{len(rows)} 条数据")

                        # 移动到下一批
                        i += len(batch)

                    # 提交事务
                    conn.commit()

            total_time = time.time() - write_start
            avg_speed = written_count / total_time if total_time > 0 else 0

            logger.info(
                f"✅ 成功写入 {written_count} 条数据到fact_measurements表，"
                f"耗时 {total_time:.2f}秒，"
                f"平均速度 {avg_speed:.0f}条/秒，"
                f"批次数 {batch_number}"
            )

            # 更新 metrics_presence_per_second_device 表
            try:
                updated_count = self.update_metrics_presence(
                    station_id=station_id,
                    device_id=device_id,
                    metric_keys=[metric_key],
                    timestamps=valid_timestamps
                )
                logger.info(
                    f"✅ 成功更新 presence 表 {updated_count} 条记录，"
                    f"指标 {metric_key} 已标记为可用"
                )
            except Exception as e:
                # 不影响主流程，仅记录警告
                logger.warning(
                    f"⚠️ 更新 presence 表失败（不影响数据写入）: {e}",
                    extra={"extra_data": {
                        "metric_key": metric_key,
                        "station_id": station_id,
                        "device_id": device_id,
                        "error": str(e)
                    }}
                )

        except Exception as e:
            logger.error(f"❌ 写入数据失败: {e}", exc_info=True)
            return 0

        return written_count

    def update_metrics_presence(
        self,
        station_id: int,
        device_id: int,
        metric_keys: List[str],
        timestamps: np.ndarray
    ) -> int:
        """
        更新metrics_presence_per_second_device表，标记指标可用性

        在成功写入计算结果后调用此方法，更新指标在各时间点的可用性状态。

        Args:
            station_id: 泵站ID
            device_id: 设备ID
            metric_keys: 成功计算的指标键列表
            timestamps: 时间戳数组

        Returns:
            更新的记录数量
        """
        if not metric_keys or len(timestamps) == 0:
            logger.warning("没有需要更新的指标或时间点")
            return 0

        # 修复说明（2025-11-04）：
        # 原代码错误地将 metric_key 转换为 metric_id 字符串后写入数据库
        # 但 metrics_presence_per_second_device 表的 available_metrics 字段应该存储 metric_key（如 "pump_flow_rate"）
        # 而不是 metric_id（如 "14"）
        # 因此删除了转换逻辑，直接使用 metric_keys 参数

        logger.info(
            f"更新指标可用性：station_id={station_id}, device_id={device_id}, "
            f"metrics={len(metric_keys)}, timepoints={len(timestamps)}"
        )

        # 使用UPSERT语法批量更新
        # 对于每个时间点，将新计算的指标添加到available_metrics数组中
        upsert_query = """
            INSERT INTO metrics_presence_per_second_device (
                station_id, device_id, ts_second, available_metrics, need_compute_metrics
            ) VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (station_id, device_id, ts_second)
            DO UPDATE SET
                available_metrics = array(
                    SELECT DISTINCT unnest(
                        metrics_presence_per_second_device.available_metrics || EXCLUDED.available_metrics
                    )
                ),
                need_compute_metrics = array(
                    SELECT unnest(metrics_presence_per_second_device.need_compute_metrics)
                    EXCEPT
                    SELECT unnest(EXCLUDED.available_metrics)
                )
        """

        # 准备数据：每个时间点一条记录
        rows = [
            (
                station_id,
                device_id,
                ts,
                metric_keys,  # 新增的可用指标（使用 metric_key 而非 metric_id）
                []  # need_compute_metrics初始为空，会在UPDATE时自动计算
            )
            for ts in timestamps
        ]

        updated_count = 0
        batch_size = 5000  # 批量大小

        try:
            update_start = time.time()

            with get_connection() as conn:
                with conn.cursor() as cur:
                    # 分批更新
                    for i in range(0, len(rows), batch_size):
                        batch = rows[i:i + batch_size]
                        cur.executemany(upsert_query, batch)
                        updated_count += len(batch)
                        logger.debug(f"已更新 {updated_count}/{len(rows)} 条记录")

                    # 提交事务
                    conn.commit()

            total_time = time.time() - update_start
            avg_speed = updated_count / total_time if total_time > 0 else 0

            logger.info(
                f"✅ 成功更新 {updated_count} 条指标可用性记录，"
                f"耗时 {total_time:.2f}秒，"
                f"平均速度 {avg_speed:.0f}条/秒"
            )

        except Exception as e:
            logger.error(f"❌ 更新指标可用性失败: {e}", exc_info=True)
            return 0

        return updated_count

    def solve_circular_dependencies(
        self,
        circular_group: List[str],
        data: Dict[str, np.ndarray],
        timestamps: np.ndarray,
        station_id: int,
        device_id: int,
        start_time: str,
        end_time: str,
        max_iterations: int = 10,
        convergence_threshold: float = 0.01
    ) -> Dict[str, np.ndarray]:
        """
        迭代求解循环依赖组

        使用不动点迭代法求解循环依赖的指标。

        Args:
            circular_group: 循环依赖组的指标列表
            data: 已有数据字典
            timestamps: 时间戳数组
            station_id: 站点ID
            device_id: 设备ID
            max_iterations: 最大迭代次数（默认10）
            convergence_threshold: 收敛阈值（相对误差，默认0.01即1%）

        Returns:
            计算结果字典
        """
        logger.info(
            f"开始迭代求解循环依赖组: {' ↔ '.join(circular_group)}",
            extra={
                "group": circular_group,
                "max_iterations": max_iterations,
                "threshold": convergence_threshold
            }
        )

        # 1. 初始化：使用零值或上一次计算结果
        results = {}
        for metric in circular_group:
            if metric in data and data[metric] is not None:
                # 使用已有数据作为初始值
                results[metric] = data[metric].copy()
            else:
                # 使用零值初始化
                results[metric] = np.zeros(len(timestamps))

        # 2. 迭代求解
        converged = False
        iteration = 0

        for iteration in range(max_iterations):
            logger.debug(f"迭代 {iteration + 1}/{max_iterations}")

            # 保存上一次迭代的结果
            prev_results = {k: v.copy() for k, v in results.items()}

            # 更新data字典（包含当前迭代的结果）
            current_data = {**data, **results}

            # 对组内每个指标进行计算（统一签名 + 正确的方法选择）
            for metric in circular_group:
                try:
                    # 构造可用指标列表与上下文（含运行台数，用于方法条件）
                    available_metrics = list(current_data.keys())
                    running_count = self._get_running_device_count(
                        station_id=station_id, start_time=start_time, end_time=end_time
                    )
                    device_type = self._get_device_type(station_id, device_id)
                    ctx2 = CalculationContext(
                        station_id=station_id,
                        device_id=device_id,
                        start_ts=start_time,
                        end_ts=end_time,
                        bucket_size_sec=None,
                        run_id=getattr(self, "_run_id", None),
                        batch_no=getattr(self, "_batch_no", None),
                        strict_mode=False,
                        quality_filters=None,
                        extra={"running_count": running_count, "device_type": device_type},
                    )

                    method_desc = self.method_selector.select_method_ctx(
                        ctx2, metric, available_metrics, current_data
                    )
                    if method_desc is None:
                        logger.warning(f"指标 {metric} 没有可用的计算方法")
                        continue

                    # 加载计算参数（6层优先级）
                    params = self.load_parameters(
                        device_id=ctx2.device_id,
                        method_id=method_desc.method_id,
                        station_id=ctx2.station_id
                    )

                    # 将参数设置到 method_desc 中（MethodDescriptor 是 frozen dataclass，需要创建新实例）
                    method_desc_with_params = MethodDescriptor(
                        method_id=method_desc.method_id,
                        method_code=method_desc.method_code,
                        metric_key=method_desc.metric_key,
                        priority=method_desc.priority,
                        dependencies=method_desc.dependencies,
                        conditions=method_desc.conditions,
                        params=params,  # 设置加载的参数
                        validator_hint=method_desc.validator_hint
                    )

                    # 统一签名计算器
                    calculator = get_calculator_unified(method_desc.method_id)
                    values, _meta = calculator(ctx2, method_desc_with_params, current_data)

                    # 更新结果
                    results[metric] = values
                    current_data[metric] = values

                except Exception as e:
                    logger.error(
                        f"迭代 {iteration + 1} 计算 {metric} 失败: {e}",
                        exc_info=True
                    )

            # 3. 检查收敛性
            max_relative_error = 0.0
            converged = True

            for metric in circular_group:
                if metric not in results or metric not in prev_results:
                    continue

                # 计算相对误差
                current = results[metric]
                previous = prev_results[metric]

                # 避免除以零
                denominator = np.where(
                    np.abs(previous) > 1e-10,
                    np.abs(previous),
                    1.0
                )

                relative_error = np.abs(current - previous) / denominator

                # 忽略NaN值
                valid_errors = relative_error[~np.isnan(relative_error)]

                if len(valid_errors) > 0:
                    metric_max_error = valid_errors.max()
                    max_relative_error = max(max_relative_error, metric_max_error)

                    if metric_max_error > convergence_threshold:
                        converged = False

            logger.debug(
                f"迭代 {iteration + 1}: 最大相对误差 = {max_relative_error:.4f}"
            )

            # 如果收敛，提前退出
            if converged:
                logger.info(
                    f"迭代求解收敛！迭代次数: {iteration + 1}, "
                    f"最大相对误差: {max_relative_error:.4f}"
                )
                break

        # 4. 检查是否收敛
        if not converged:
            logger.warning(
                f"迭代求解未收敛！达到最大迭代次数 {max_iterations}, "
                f"最大相对误差: {max_relative_error:.4f} > {convergence_threshold}"
            )

        return results


    # ====================== 私有辅助方法（提炼以降低复杂度） ======================
    def _process_cyclic_group(
        self,
        group_id: str,
        group_members: List[str],
        data: Dict[str, np.ndarray],
        timestamps: np.ndarray,
        station_id: int,
        device_id: int,
        ctx: "CalculationContext",
        stats: "StatsCollector",
        start_time: str,
        end_time: str,
        write_to_db: bool,
        result: Dict,
    ) -> Dict[str, np.ndarray]:
        """处理循环依赖组：统一接入组级统计事件。

        Args:
            group_id: 循环组ID
            group_members: 组内指标
            data: 数据字典
            timestamps: 时间戳
            station_id: 站点ID
            device_id: 设备ID
            ctx: 统一上下文
            stats: 统计器
        Returns:
            组内各指标最新结果
        """
        # 组级统计：开始
        try:
            stats.on_group_start(group_id, getattr(ctx, "run_id", ""), station_id, device_id)
        except Exception:
            pass

        iterations = 0
        converged = False
        succeeded = False
        try:
            circular_results = self.solve_circular_dependencies(
                group_members, data, timestamps, station_id, device_id, start_time, end_time
            )

            # 逐成员：验证/统计/写库/计时
            for member, values in circular_results.items():
                metric_start = time.time()
                # 指标级：开始
                stats.on_metric_start(
                    run_id=getattr(ctx, "run_id", ""),
                    station_id=station_id,
                    device_id=device_id,
                    metric_key=member,
                    bucket=(str(start_time), str(end_time)),
                    path_type="cyclic",
                    method_id=None,
                    total_points=len(timestamps),
                )
                # 验证（统一签名）
                is_valid, mask, errors, warnings = self.validator.validate_ctx(member, values, ctx)
                if not is_valid and mask is not None:
                    logger.warning(f"循环依赖指标 {member} 验证失败: {errors}")
                    values = values[mask]
                # 保存结果
                data[member] = values
                result['metrics_calculated'].append(member)
                result['total_points'] += len(values)
                result['valid_points'] += int(mask.sum()) if mask is not None and hasattr(mask, 'sum') else len(values)
                # 可选写库
                if write_to_db:
                    write_start = time.time()
                    # 修复：当过滤后长度变化时，按mask对齐timestamps
                    # 参考 lines 2042-2047 的正确实现
                    write_ts = timestamps
                    try:
                        if mask is not None and hasattr(mask, '__len__') and len(mask) == len(timestamps):
                            if len(values) != len(timestamps):
                                write_ts = timestamps[mask]
                    except Exception:
                        write_ts = timestamps

                    # 设备类型校验（循环组场景）
                    dtype = self._get_device_type(station_id, device_id)
                    if dtype and not self._metric_allowed_for_device(member, dtype):
                        logger.info(
                            f"skip write: metric={member} not allowed for device_type={dtype}")
                    else:
                        written = self.write_results(
                            station_id=station_id,
                            device_id=device_id,
                            metric_key=member,
                            timestamps=write_ts,  # 修复：使用对齐后的 timestamps
                            values=values,
                            is_cyclic=True,  # 标记为循环指标
                        )
                        result['written_points'] += written
                        result['performance_stats']['write_time'] += time.time() - write_start
                    stats.on_write(
                        run_id=getattr(ctx, "run_id", ""),
                        station_id=station_id,
                        device_id=device_id,
                        metric_key=member,
                        bucket=(str(start_time), str(end_time)),
                        written_points=int(written),
                        write_duration_ms=int((time.time() - write_start) * 1000),
                    )
                # 指标级：结束
                stats.on_metric_end(
                    run_id=getattr(ctx, "run_id", ""),
                    station_id=station_id,
                    device_id=device_id,
                    metric_key=member,
                    bucket=(str(start_time), str(end_time)),
                    valid_points=len(values),
                    calc_duration_ms=int((time.time() - metric_start) * 1000),
                    validate_duration_ms=0,
                    method_id=None,
                )
                result['performance_stats']['metric_times'][member] = time.time() - metric_start

            succeeded = True
            return circular_results
        finally:
            try:
                stats.on_group_end(group_id, succeeded, iterations, converged)
            except Exception:
                pass

    def _prepare_flow_rate_share(
        self,
        data: Dict[str, np.ndarray],
        timestamps: np.ndarray,
        station_id: int,
        device_id: int,
        start_time: str,
        end_time: str,
        method: "MethodDescriptor",
        filter_running: bool = True,
    ) -> None:
        """
        预计算功率×频率分摊法所需的归一化权重份额，避免单泵独占总流量。

        Args:
            filter_running: 是否只使用运行中的设备数据（默认True）
        """
        if (
            "main_pipeline_flow_rate" not in data
            or "pump_active_power" not in data
            or "pump_frequency" not in data
        ):
            return

        if timestamps.size == 0:
            return

        Q_total = np.asarray(data.get("main_pipeline_flow_rate"), dtype=float)
        power = np.asarray(data.get("pump_active_power"), dtype=float)
        freq = np.asarray(data.get("pump_frequency"), dtype=float)

        if Q_total.size == 0 or power.size == 0 or freq.size == 0:
            return

        params_cfg = self.load_parameters(device_id, method.method_id)
        alpha = float(params_cfg.get("alpha", 1.0))
        beta = float(params_cfg.get("beta", 1.0))
        f_thr = float(params_cfg.get("f_thr", 3.0))
        p_thr = float(params_cfg.get("p_thr", 0.5))

        weight_i = np.zeros_like(power, dtype=float)
        valid_mask = (
            ~np.isnan(power)
            & ~np.isnan(freq)
            & (freq >= f_thr)
            & (power >= p_thr)
        )
        if np.any(valid_mask):
            weight_i[valid_mask] = np.power(power[valid_mask], alpha) * np.power(
                freq[valid_mask], beta
            )

        share = np.full_like(Q_total, np.nan, dtype=float)

        # 如果没有有效权重，则直接返回（保持 NaN 代表无法计算）
        if not np.any(weight_i > 0):
            data["__pump_flow_rate_share"] = share
            return

        ts_list: List[datetime] = []
        for ts in timestamps:
            value = ts
            if hasattr(ts, "item"):
                try:
                    value = ts.item()
                except Exception:
                    value = ts
            if hasattr(value, "to_pydatetime"):
                try:
                    value = value.to_pydatetime()
                except Exception:
                    pass
            ts_list.append(value)

        if not ts_list:
            data["__pump_flow_rate_share"] = share
            return

        unique_ts = list({ts: None for ts in ts_list}.keys())

        weight_totals: Dict[datetime, float] = defaultdict(float)
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    # 根据filter_running参数决定是否JOIN运行状态表
                    if filter_running:
                        cur.execute(
                            """
                            SELECT fm.ts_bucket,
                                   fm.device_id,
                                   MAX(CASE WHEN mc.metric_key = 'pump_active_power' THEN fm.value::float8 END) AS power,
                                   MAX(CASE WHEN mc.metric_key = 'pump_frequency' THEN fm.value::float8 END) AS freq
                            FROM fact_measurements fm
                            JOIN dim_metric_config mc ON mc.id = fm.metric_id
                            JOIN mv_device_running_1s dr
                              ON dr.station_id = fm.station_id
                             AND dr.device_id = fm.device_id
                             AND dr.ts_bucket = fm.ts_bucket
                            WHERE fm.station_id = %s
                              AND fm.ts_bucket = ANY(%s)
                              AND mc.metric_key IN ('pump_active_power', 'pump_frequency')
                              AND dr.running = 1
                            GROUP BY fm.ts_bucket, fm.device_id
                            """,
                            (station_id, unique_ts),
                        )
                    else:
                        # 不过滤运行状态，使用所有设备数据
                        cur.execute(
                            """
                            SELECT fm.ts_bucket,
                                   fm.device_id,
                                   MAX(CASE WHEN mc.metric_key = 'pump_active_power' THEN fm.value::float8 END) AS power,
                                   MAX(CASE WHEN mc.metric_key = 'pump_frequency' THEN fm.value::float8 END) AS freq
                            FROM fact_measurements fm
                            JOIN dim_metric_config mc ON mc.id = fm.metric_id
                            WHERE fm.station_id = %s
                              AND fm.ts_bucket = ANY(%s)
                              AND mc.metric_key IN ('pump_active_power', 'pump_frequency')
                            GROUP BY fm.ts_bucket, fm.device_id
                            """,
                            (station_id, unique_ts),
                        )
                    rows = cur.fetchall()
        except Exception as exc:
            logger.warning(
                "获取泵流量分摊权重失败，采用保守结果（NaN）",
                exc_info=True,
                extra={"station_id": station_id, "device_id": device_id},
            )
            data["__pump_flow_rate_share"] = share
            return

        for ts_bucket, dev_id, power_val, freq_val in rows:
            if power_val is None or freq_val is None:
                continue
            try:
                p_val = float(power_val)
                f_val = float(freq_val)
            except (TypeError, ValueError):
                continue
            if f_val < f_thr or p_val < p_thr:
                continue
            weight = (p_val ** alpha) * (f_val ** beta)
            if np.isfinite(weight) and weight > 0:
                weight_totals[ts_bucket] += weight

        for idx, ts in enumerate(ts_list):
            total_weight = weight_totals.get(ts)
            if total_weight and total_weight > 0 and valid_mask[idx]:
                share[idx] = weight_i[idx] / total_weight

        data["__pump_flow_rate_share"] = share

    def _process_acyclic_metric(
        self,
        metric_key: str,
        data: Dict[str, np.ndarray],
        timestamps: np.ndarray,
        station_id: int,
        device_id: int,
        start_time: str,
        end_time: str,
        write_to_db: bool,
        ctx: "CalculationContext",
        stats: "StatsCollector",
        result: Dict,
    ) -> None:
        """处理非循环指标（统一签名 + 集中统计 + 可选写库）。"""
        metric_start = time.time()
        available_metrics = list(data.keys())

        running_count = self._get_running_device_count(
            station_id=station_id, start_time=start_time, end_time=end_time
        )
        device_type = self._get_device_type(station_id, device_id)
        ctx2 = CalculationContext(
            station_id=ctx.station_id,
            device_id=ctx.device_id,
            start_ts=ctx.start_ts,
            end_ts=ctx.end_ts,
            bucket_size_sec=ctx.bucket_size_sec,
            run_id=ctx.run_id,
            batch_no=ctx.batch_no,
            strict_mode=ctx.strict_mode,
            quality_filters=ctx.quality_filters,
            extra={**(getattr(ctx, "extra", {}) or {}), "running_count": running_count, "device_type": device_type},
        )

        method_desc = self.method_selector.select_method_ctx(
            ctx2, metric_key, available_metrics, data
        )
        if method_desc is None:
            logger.error(
                f"指标 {metric_key} 没有可用的计算方法",
                extra={
                    "extra_data": {
                        "\u6cf5\u7ad9ID": station_id,
                        "\u8bbe\u5907ID": device_id,
                        "\u6307\u6807\u952e": metric_key,
                        "\u5f00\u59cb\u65f6\u95f4": start_time,
                        "\u7ed3\u675f\u65f6\u95f4": end_time,
                        "\u53ef\u7528\u6307\u6807": available_metrics,
                    }
                },
            )
            result['metrics_failed'].append(metric_key)
            result['errors'].append(f"{metric_key}: 没有可用的计算方法")
            result['performance_stats']['metric_times'][metric_key] = 0
            return

        if method_desc.method_id == "pump_flow_rate_method_a":
            self._prepare_flow_rate_share(
                data=data,
                timestamps=timestamps,
                station_id=station_id,
                device_id=device_id,
                start_time=start_time,
                end_time=end_time,
                method=method_desc,
            )

        stats.on_metric_start(
            run_id=getattr(ctx2, "run_id", ""),
            station_id=station_id,
            device_id=device_id,
            metric_key=metric_key,
            bucket=(str(start_time), str(end_time)),
            path_type="acyclic",
            method_id=method_desc.method_id,
            total_points=len(timestamps),
        )

        input_data: Dict[str, np.ndarray] = {}
        for dep in getattr(method_desc, "dependencies", []) or []:
            if dep not in data:
                logger.error(f"依赖数据 {dep} 不存在")
                result['metrics_failed'].append(metric_key)
                result['errors'].append(f"{metric_key}: 依赖数据 {dep} 不存在")
                result['performance_stats']['metric_times'][metric_key] = time.time() - metric_start
                return
            input_data[dep] = data[dep]

        if (
            method_desc.method_id == "pump_flow_rate_method_a"
            and "__pump_flow_rate_share" in data
        ):
            input_data["__pump_flow_rate_share"] = data["__pump_flow_rate_share"]

        try:
            # 加载计算参数（6层优先级）
            params = self.load_parameters(
                device_id=ctx2.device_id,
                method_id=method_desc.method_id,
                station_id=ctx2.station_id
            )

            # 将参数设置到 method_desc 中（MethodDescriptor 是 frozen dataclass，需要创建新实例）
            method_desc_with_params = MethodDescriptor(
                method_id=method_desc.method_id,
                method_code=method_desc.method_code,
                metric_key=method_desc.metric_key,
                priority=method_desc.priority,
                dependencies=method_desc.dependencies,
                conditions=method_desc.conditions,
                params=params,  # 设置加载的参数
                validator_hint=method_desc.validator_hint
            )

            calculator = get_calculator_unified(method_desc.method_id)
            values, meta = calculator(ctx2, method_desc_with_params, input_data)

            val_start = time.time()
            is_valid, mask, errors, warnings = self.validator.validate_ctx(metric_key, values, ctx2)
            validate_duration = time.time() - val_start

            # 记录验证结果到reporter
            self.validation_reporter.add_result(
                metric_key=metric_key,
                is_valid=is_valid,
                total_count=len(values),
                valid_count=int(mask.sum()) if mask is not None and hasattr(mask, 'sum') else len(values),
                errors=errors,
                warnings=warnings,
                duration=validate_duration,
                context={
                    "station_id": ctx2.station_id,
                    "device_id": ctx2.device_id,
                    "start_ts": str(ctx2.start_ts),
                    "end_ts": str(ctx2.end_ts),
                    "method_id": method_desc.method_id
                }
            )

            if not is_valid:
                logger.warning(f"验证失败：{errors}")
                filtered_values = values[mask]
            else:
                filtered_values = values

            # 参数优化（如果启用）
            if self.enable_optimization and self.parameter_optimizer is not None:
                try:
                    # 获取实测数据
                    measured_data = self._get_measured_data(
                        station_id=station_id,
                        device_id=device_id,
                        metric_key=metric_key,
                        timestamps=timestamps
                    )

                    # 如果有实测数据，进行参数优化
                    if measured_data is not None and not np.all(np.isnan(measured_data)):
                        # 获取当前参数
                        current_params = self._get_current_parameters(
                            method_id=method_desc.method_id,
                            device_id=device_id,
                            station_id=station_id
                        )

                        if current_params:
                            logger.info(
                                "[流程-开始] [参数优化]",
                                extra={
                                    "extra_data": {
                                        "metric_key": metric_key,
                                        "method_id": method_desc.method_id,
                                        "station_id": station_id,
                                        "device_id": device_id,
                                        "param_count": len(current_params)
                                    }
                                }
                            )

                            # 准备优化数据
                            # 移除NaN值
                            valid_mask = ~(np.isnan(measured_data) | np.isnan(values))
                            n_valid = np.sum(valid_mask)

                            # 数据质量检查
                            if n_valid >= 10:  # 至少需要10个有效数据点（包含边界值）
                                # 检查数据方差（避免常数数据）
                                data_var_ok = True
                                if np.var(measured_data[valid_mask]) < 1e-10 or np.var(values[valid_mask]) < 1e-10:
                                    logger.warning(
                                        "[流程-跳过] [参数优化] 数据方差过小，无法优化",
                                        extra={
                                            "extra_data": {
                                                "metric_key": metric_key,
                                                "measured_var": float(np.var(measured_data[valid_mask])),
                                                "calculated_var": float(np.var(values[valid_mask]))
                                            }
                                        }
                                    )
                                    data_var_ok = False

                                # 检查观测矩阵秩（避免线性相关）
                                data_rank_ok = True
                                if data_var_ok:
                                    X_test = np.column_stack([measured_data[valid_mask], np.ones(n_valid)])
                                    if np.linalg.matrix_rank(X_test) < X_test.shape[1]:
                                        logger.warning(
                                            "[流程-跳过] [参数优化] 观测矩阵秩不足，数据线性相关",
                                            extra={
                                                "extra_data": {
                                                    "metric_key": metric_key,
                                                    "rank": int(np.linalg.matrix_rank(X_test)),
                                                    "expected_rank": X_test.shape[1]
                                                }
                                            }
                                        )
                                        data_rank_ok = False

                                # 只有数据质量检查通过才继续优化
                                if data_var_ok and data_rank_ok:
                                    measured_dict = {metric_key: measured_data[valid_mask]}
                                    calculated_dict = {metric_key: values[valid_mask]}

                                    # 从数据库加载参数约束
                                    param_bounds = {}
                                    try:
                                        with get_connection() as conn:
                                            with conn.cursor() as cur:
                                                for param_name in current_params.keys():
                                                    cur.execute("""
                                                        SELECT param_min, param_max
                                                        FROM calculation_parameters
                                                        WHERE method_id = %s
                                                          AND param_name = %s
                                                          AND (device_id IS NOT DISTINCT FROM %s)
                                                          AND (station_id IS NOT DISTINCT FROM %s)
                                                    """, (method_desc.method_id, param_name, device_id, station_id))

                                                    row = cur.fetchone()
                                                    if row and row[0] is not None and row[1] is not None:
                                                        param_bounds[param_name] = (float(row[0]), float(row[1]))
                                                        logger.debug(
                                                            f"加载参数约束: {param_name} ∈ [{row[0]}, {row[1]}]",
                                                            extra={
                                                                "param_name": param_name,
                                                                "min": float(row[0]),
                                                                "max": float(row[1])
                                                            }
                                                        )

                                        if param_bounds:
                                            logger.info(
                                                f"已加载{len(param_bounds)}个参数约束",
                                                extra={"param_count": len(param_bounds), "params": list(param_bounds.keys())}
                                            )
                                    except Exception as e:
                                        logger.warning(f"加载参数约束失败: {e}", exc_info=True)
                                        param_bounds = None

                                    # 执行优化
                                    new_params, metrics = self.parameter_optimizer.optimize_parameters(
                                        method_id=method_desc.method_id,
                                        measured_data=measured_dict,
                                        calculated_data=calculated_dict,
                                        current_params=current_params,
                                        param_bounds=param_bounds if param_bounds else None,
                                        device_id=device_id,
                                        station_id=station_id
                                    )

                                    logger.info(
                                        "[流程-完成] [参数优化]",
                                        extra={
                                            "extra_data": {
                                                "metric_key": metric_key,
                                                "method_id": method_desc.method_id,
                                                "old_params": current_params,
                                                "new_params": new_params,
                                                "metrics": metrics
                                            }
                                        }
                                    )
                            else:
                                logger.info(
                                    "[流程-跳过] [参数优化] 有效数据点不足",
                                    extra={
                                        "extra_data": {
                                            "metric_key": metric_key,
                                            "valid_points": int(np.sum(valid_mask))
                                        }
                                    }
                                )
                        else:
                            logger.debug(f"指标 {metric_key} 方法 {method_desc.method_id} 没有可优化的参数")
                    else:
                        logger.debug(f"指标 {metric_key} 没有实测数据，跳过参数优化")

                except Exception as e:
                    # 参数优化失败不应该影响计算流程
                    logger.warning(
                        f"参数优化失败: {e}",
                        extra={
                            "extra_data": {
                                "metric_key": metric_key,
                                "method_id": method_desc.method_id,
                                "station_id": station_id,
                                "device_id": device_id
                            }
                        },
                        exc_info=True
                    )

            data[metric_key] = filtered_values
            if metric_key == "main_pipeline_inlet_pressure":
                existing = data.get("pump_inlet_pressure")
                if existing is None:
                    data["pump_inlet_pressure"] = filtered_values.copy()
                else:
                    combined = existing.copy()
                    mask_replace = np.isnan(combined)
                    combined[mask_replace] = filtered_values[mask_replace]
                    data["pump_inlet_pressure"] = combined

            result['metrics_calculated'].append(metric_key)
            result['total_points'] += len(filtered_values)
            result['valid_points'] += int(mask.sum()) if mask is not None and hasattr(mask, 'sum') else len(filtered_values)

            if write_to_db:
                write_start = time.time()
                # 当过滤后长度变化时，按mask对齐timestamps
                write_ts = timestamps
                try:
                    if mask is not None and hasattr(mask, '__len__') and len(mask) == len(timestamps):
                        if len(filtered_values) != len(timestamps):
                            write_ts = timestamps[mask]
                except Exception:
                    write_ts = timestamps

                # 设备类型校验（非循环指标场景）
                dtype = self._get_device_type(station_id, device_id)
                if dtype and not self._metric_allowed_for_device(metric_key, dtype):
                    logger.info(
                        f"skip write: metric={metric_key} not allowed for device_type={dtype}")
                else:
                    written = self.write_results(
                        station_id=station_id,
                        device_id=device_id,
                        metric_key=metric_key,
                        timestamps=write_ts,
                        values=filtered_values,
                        method_id=method_desc.method_id,  # 传递方法ID
                    )
                    result['written_points'] += written
                    result['performance_stats']['write_time'] += time.time() - write_start
                stats.on_write(
                    run_id=getattr(ctx2, "run_id", ""),
                    station_id=station_id,
                    device_id=device_id,
                    metric_key=metric_key,
                    bucket=(str(start_time), str(end_time)),
                    written_points=int(written),
                    write_duration_ms=int((time.time() - write_start) * 1000),
                )

            stats.on_metric_end(
                run_id=getattr(ctx2, "run_id", ""),
                station_id=station_id,
                device_id=device_id,
                metric_key=metric_key,
                bucket=(str(start_time), str(end_time)),
                valid_points=len(values),
                calc_duration_ms=int((time.time() - metric_start) * 1000),
                validate_duration_ms=int(validate_duration * 1000),
                method_id=method_desc.method_id,
            )

            # 将新计算的数据添加到 data 字典中，以便后续指标可以使用
            # 这对于自动扩展的依赖链非常重要
            data[metric_key] = values
            logger.debug(
                f"已将计算结果添加到数据字典: {metric_key} ({len(values)} 个数据点)",
                extra={"extra_data": {
                    "metric_key": metric_key,
                    "data_points": len(values),
                    "valid_points": len(values),
                }}
            )

            result['performance_stats']['metric_times'][metric_key] = time.time() - metric_start
        except Exception as e:
            logger.error(f"计算失败：{e}", exc_info=True)
            result['metrics_failed'].append(metric_key)
            result['errors'].append(f"{metric_key}: 计算失败 - {str(e)}")
            result['performance_stats']['metric_times'][metric_key] = time.time() - metric_start

    def calculate_missing_metrics(
        self,
        station_id: int,
        device_id: int,
        start_time: str,
        end_time: str,
        metrics: List[str],
        write_to_db: bool = False,
        filter_running: bool | None = None,
        filter_quality: bool | None = None,
    ) -> Dict:
        """
        计算缺失指标

        ⚠️ **DEPRECATED**: 此函数正在逐步废弃，请迁移到新的流水线架构
            - 新架构: app/services/calculation/metrics/pump_flow_rate/pipeline.py
            - 迁移指南: 见 缺失指标计算改造/pump_flow_rate/11-pump_flow_rate重构任务跟踪.md
            - 废弃时间: 2025-01-14
            - 计划删除: 2025-02-14

        Args:
            station_id: 泵站ID
            device_id: 设备ID
            start_time: 开始时间
            end_time: 结束时间
            metrics: 需要计算的指标列表
            write_to_db: 是否写入数据库（默认False，只计算不写入）

        Returns:
            计算结果字典
        """
        logger.info(
            f"开始计算缺失指标：station_id={station_id}, device_id={device_id}, "
            f"time=[{start_time}, {end_time}], metrics={metrics}"
        )

        result = {
            'success': False,
            'metrics_calculated': [],
            'metrics_failed': [],
            'total_points': 0,
            'valid_points': 0,
            'written_points': 0,
            'errors': [],
            'performance_stats': {
                'total_time': 0,
                'load_data_time': 0,
                'calculation_time': 0,
                'write_time': 0,
                'metric_times': {},
            }
        }

        # 性能计时
        start_total = time.time()

        try:
            # 1. 分析依赖关系，生成计算顺序
            # 传递上下文给依赖分析器，使其 WARNING/ERROR 日志具备 station/device/time
            self.dependency_analyzer.set_context({
                "\u6cf5\u7ad9ID": station_id,
                "\u8bbe\u5907ID": device_id,
                "\u5f00\u59cb\u65f6\u95f4": start_time,
                "\u7ed3\u675f\u65f6\u95f4": end_time,
                "requested_metrics": list(metrics or []),
            })
            calculation_order = self.dependency_analyzer.get_calculation_order(metrics)
            logger.info(
                f"计算顺序：{' → '.join(calculation_order)}",
                extra={"extra_data": {
                    "\u6cf5\u7ad9ID": station_id,
                    "\u8bbe\u5907ID": device_id,
                    "\u5f00\u59cb\u65f6\u95f4": start_time,
                    "\u7ed3\u675f\u65f6\u95f4": end_time,
                    "requested_metrics": list(metrics or []),
                    "order": list(calculation_order or []),
                }}
            )

            # 1.1 获取循环依赖组信息
            circular_group_info = self.dependency_analyzer.get_circular_group_info(metrics)
            has_circular = len(circular_group_info) > 0

            if has_circular:
                logger.info(
                    f"检测到 {len(circular_group_info)} 个循环依赖组",
                    extra={"groups": circular_group_info}
                )

            # 2. 加载所有可能需要的数据（并集：所有候选方法的依赖）
            all_dependencies: set[str] = set()
            for metric in metrics:
                try:
                    # 使用方法选择器的注册表，取所有启用方法的依赖并集
                    union_deps = set(self.method_selector.get_union_dependencies(metric))
                except Exception:
                    # 回退：使用依赖分析器的“最高优先级方法”的依赖
                    union_deps = set(self.dependency_analyzer.get_dependencies(metric))
                all_dependencies.update(union_deps)

            # 加载依赖数据
            load_start = time.time()
            # 允许通过可选开关覆盖缺省过滤策略（仅用于验证/排障场景）
            _fr = True if filter_running is None else bool(filter_running)
            _fq = True if filter_quality is None else bool(filter_quality)
            data, timestamps = self.load_data(
                station_id, device_id, start_time, end_time, sorted(all_dependencies),
                filter_running=_fr, filter_quality=_fq
            )
            result['performance_stats']['load_data_time'] = time.time() - load_start

            # 3. 按顺序计算每个指标（处理循环依赖）
            calc_start = time.time()

            # 统一上下文与统计器
            ctx = CalculationContext(
                station_id=station_id,
                device_id=device_id,
                start_ts=start_time,
                end_ts=end_time,
            )
            stats = StatsCollector()

            # 3.1 识别已处理的循环依赖组
            processed_groups = set()

            # 3.2 按顺序处理指标
            for metric_key in calculation_order:
                # 检查是否属于循环依赖组
                metric_group = None
                for group_id, group_members in circular_group_info.items():
                    if metric_key in group_members:
                        metric_group = group_id
                        break

                # 如果属于循环依赖组且该组未处理
                if metric_group and metric_group not in processed_groups:
                    logger.info(f"开始迭代求解循环依赖组：{metric_group}")

                    # 获取组成员
                    group_members = circular_group_info[metric_group]

                    # 迭代求解
                    try:
                        circular_results = self._process_cyclic_group(
                            metric_group,
                            group_members,
                            data,
                            timestamps,
                            station_id,
                            device_id,
                            ctx,
                            stats,
                            start_time,
                            end_time,
                            write_to_db,
                            result,
                        )

                        # 循环组内成员的验证/写库/统计已在 _process_cyclic_group 内完成
                        processed_groups.add(metric_group)

                    except Exception as e:
                        logger.error(f"循环依赖组 {metric_group} 求解失败: {e}", exc_info=True)
                        for member in group_members:
                            result['metrics_failed'].append(member)
                            result['errors'].append(f"{member}: 循环依赖求解失败 - {str(e)}")

                    continue

                # 如果已经在循环依赖组中处理过，跳过
                if metric_group and metric_group in processed_groups:
                    continue

                # 非循环依赖指标：在同一循环内直接处理（统一签名 + 集中统计）
                self._process_acyclic_metric(
                    metric_key,
                    data,
                    timestamps,
                    station_id,
                    device_id,
                    start_time,
                    end_time,
                    write_to_db,
                    ctx,
                    stats,
                    result,
                )
                continue

            # 记录总计算时间
            result['performance_stats']['calculation_time'] = time.time() - calc_start

            # 4. 判断整体成功
            result['success'] = len(result['metrics_calculated']) > 0

            # 5. 计算总体性能统计
            result['performance_stats']['total_time'] = time.time() - start_total
            if result['total_points'] > 0 and result['performance_stats']['total_time'] > 0:
                result['performance_stats']['throughput'] = (
                    result['total_points'] / result['performance_stats']['total_time']
                )
            else:
                result['performance_stats']['throughput'] = 0

            # 6. 日志输出
            log_msg = (
                f"计算完成：成功 {len(result['metrics_calculated'])} 个，"
                f"失败 {len(result['metrics_failed'])} 个，"
                f"有效数据点 {result['valid_points']}/{result['total_points']}，"
                f"总耗时 {result['performance_stats']['total_time']:.2f}秒，"
                f"吞吐量 {result['performance_stats']['throughput']:.0f} 数据点/秒"
            )
            if write_to_db:
                log_msg += f"，已写入 {result['written_points']} 条数据"
            logger.info(log_msg)

            # 7. 附加诊断信息，便于外部报告生成
            try:
                result['calculation_order'] = calculation_order
                result['circular_groups'] = circular_group_info
                # 输出统一统计快照，供诊断报告消费
                result['stats'] = stats.flush()
            except Exception:
                # 忽略诊断信息附加失败
                pass

        except Exception as e:
            logger.error(f"计算流程失败：{e}", exc_info=True)
            result['errors'].append(f"计算流程失败: {str(e)}")

        # 确保返回结构包含 stats 键（异常路径也兼容）
        if 'stats' not in result:
            result['stats'] = {}

        return result

    def calculate_missing_metrics_batch(
        self,
        devices: List[Tuple[int, int]],
        start_time: str,
        end_time: str,
        metrics: List[str],
        write_to_db: bool = False,
        max_workers: int = 4,
        auto_parallel: bool = True
    ) -> Dict:
        """
        批量并行计算多个设备的缺失指标

        Args:
            devices: 设备列表 [(station_id, device_id), ...]
            start_time: 开始时间
            end_time: 结束时间
            metrics: 需要计算的指标列表
            write_to_db: 是否写入数据库
            max_workers: 最大并行工作线程数
            auto_parallel: 是否自动选择串行/并行（默认True）

        Returns:
            批量计算结果汇总
        """
        start_total = time.time()

        # 智能并行策略：根据数据量和设备数量自动选择串行/并行
        use_parallel = True
        parallel_reason = ""

        if auto_parallel:
            # 估算数据量（假设每分钟1个数据点）
            from datetime import datetime
            def _parse_ts(value: str) -> datetime:
                try:
                    return datetime.fromisoformat(value)
                except ValueError:
                    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")

            start_dt = _parse_ts(start_time)
            end_dt = _parse_ts(end_time)
            time_diff_minutes = (end_dt - start_dt).total_seconds() / 60
            estimated_points_per_device = int(time_diff_minutes)
            total_estimated_points = estimated_points_per_device * len(devices)

            # 判断策略：
            # 1. 总数据点 > 10000 且 设备数 > 2 → 并行
            # 2. 单设备数据点 > 5000 → 并行
            # 3. 否则 → 串行

            if total_estimated_points > 10000 and len(devices) > 2:
                use_parallel = True
                parallel_reason = (
                    f"总数据点({total_estimated_points}) > 10000 且 "
                    f"设备数({len(devices)}) > 2，使用并行计算"
                )
            elif estimated_points_per_device > 5000:
                use_parallel = True
                parallel_reason = (
                    f"单设备数据点({estimated_points_per_device}) > 5000，使用并行计算"
                )
            else:
                use_parallel = False
                parallel_reason = (
                    f"数据量较小（总数据点={total_estimated_points}, "
                    f"单设备={estimated_points_per_device}, 设备数={len(devices)}），"
                    f"使用串行计算以避免线程开销"
                )

            logger.info(f"🤖 智能并行策略: {parallel_reason}")

        logger.info(
            f"开始批量{'并行' if use_parallel else '串行'}计算：{len(devices)} 个设备，"
            f"时间范围 [{start_time}, {end_time}]，"
            f"指标 {metrics}，"
            f"{'并行度 ' + str(max_workers) if use_parallel else '串行模式'}"
        )

        # 结果汇总
        batch_result = {
            'success': True,
            'total_devices': len(devices),
            'successful_devices': 0,
            'failed_devices': 0,
            'device_results': {},
            'total_points': 0,
            'total_valid_points': 0,
            'total_written_points': 0,
            'errors': [],
            'performance_stats': {
                'total_time': 0,
                'avg_time_per_device': 0,
                'throughput': 0,  # 数据点/秒
            }
        }

        # 定义单个设备的计算任务
        def calculate_device(station_id: int, device_id: int) -> Tuple[int, int, Dict]:
            """计算单个设备的缺失指标"""
            try:
                device_start = time.time()

                result = self.calculate_missing_metrics(
                    station_id=station_id,
                    device_id=device_id,
                    start_time=start_time,
                    end_time=end_time,
                    metrics=metrics,
                    write_to_db=write_to_db
                )

                device_time = time.time() - device_start
                result['performance_stats'] = {
                    'time': device_time,
                    'throughput': result['total_points'] / device_time if device_time > 0 else 0
                }

                return station_id, device_id, result

            except Exception as e:
                logger.error(
                    f"设备 (station={station_id}, device={device_id}) 计算失败: {e}",
                    exc_info=True
                )
                return station_id, device_id, {
                    'success': False,
                    'errors': [str(e)],
                    'metrics_calculated': [],
                    'metrics_failed': metrics,
                    'total_points': 0,
                    'valid_points': 0,
                    'written_points': 0,
                }

        # 根据策略选择串行或并行计算
        if use_parallel:
            # 并行计算
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有任务
                futures = {
                    executor.submit(calculate_device, station_id, device_id): (station_id, device_id)
                    for station_id, device_id in devices
                }

                # 收集结果
                completed = 0
                for future in as_completed(futures):
                    station_id, device_id = futures[future]
                    completed += 1

                    try:
                        station_id, device_id, result = future.result()

                        # 记录结果
                        device_key = f"station_{station_id}_device_{device_id}"
                        batch_result['device_results'][device_key] = result

                        # 更新统计
                        if result['success']:
                            batch_result['successful_devices'] += 1
                        else:
                            batch_result['failed_devices'] += 1
                            batch_result['errors'].append(
                                f"设备 {device_key}: {', '.join(result.get('errors', []))}"
                            )

                        batch_result['total_points'] += result.get('total_points', 0)
                        batch_result['total_valid_points'] += result.get('valid_points', 0)
                        batch_result['total_written_points'] += result.get('written_points', 0)

                        # 进度日志
                        logger.info(
                            f"进度: {completed}/{len(devices)} - "
                            f"设备 {device_key}: "
                            f"{'成功' if result['success'] else '失败'}, "
                            f"有效数据点 {result.get('valid_points', 0)}/{result.get('total_points', 0)}"
                        )

                    except Exception as e:
                        logger.error(f"获取设备结果失败: {e}", exc_info=True)
                        batch_result['failed_devices'] += 1
                        batch_result['errors'].append(f"设备 station_{station_id}_device_{device_id}: {str(e)}")
        else:
            # 串行计算
            completed = 0
            for station_id, device_id in devices:
                completed += 1

                try:
                    station_id, device_id, result = calculate_device(station_id, device_id)

                    # 记录结果
                    device_key = f"station_{station_id}_device_{device_id}"
                    batch_result['device_results'][device_key] = result

                    # 更新统计
                    if result['success']:
                        batch_result['successful_devices'] += 1
                    else:
                        batch_result['failed_devices'] += 1
                        batch_result['errors'].append(
                            f"设备 {device_key}: {', '.join(result.get('errors', []))}"
                        )

                    batch_result['total_points'] += result.get('total_points', 0)
                    batch_result['total_valid_points'] += result.get('valid_points', 0)
                    batch_result['total_written_points'] += result.get('written_points', 0)

                    # 进度日志
                    logger.info(
                        f"进度: {completed}/{len(devices)} - "
                        f"设备 {device_key}: "
                        f"{'成功' if result['success'] else '失败'}, "
                        f"有效数据点 {result.get('valid_points', 0)}/{result.get('total_points', 0)}"
                    )

                except Exception as e:
                    logger.error(f"设备计算失败: {e}", exc_info=True)
                    batch_result['failed_devices'] += 1
                    batch_result['errors'].append(f"设备 station_{station_id}_device_{device_id}: {str(e)}")

        # 计算总体性能统计
        total_time = time.time() - start_total
        batch_result['performance_stats']['total_time'] = total_time
        batch_result['performance_stats']['avg_time_per_device'] = (
            total_time / len(devices) if len(devices) > 0 else 0
        )
        batch_result['performance_stats']['throughput'] = (
            batch_result['total_points'] / total_time if total_time > 0 else 0
        )

        # 判断整体成功
        batch_result['success'] = batch_result['failed_devices'] == 0

        logger.info(
            f"批量计算完成：成功 {batch_result['successful_devices']} 个，"
            f"失败 {batch_result['failed_devices']} 个，"
            f"总耗时 {total_time:.2f}秒，"
            f"吞吐量 {batch_result['performance_stats']['throughput']:.0f} 数据点/秒"
        )

        return batch_result
