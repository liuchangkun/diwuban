"""
泵组数据提取器

本模块负责从数据库提取泵组运行工况点数据：
- 提取历史运行数据（流量、扬程、运行状态）
- 按泵组合分组
- 频率归一化（VFD场景）
- 数据验证和清洗

版本: v1.0
创建日期: 2025-12-09
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.services.characteristic_curves.pump_group.models import (
    GroupFitData,
    GroupOperatingPoint,
)
from app.services.characteristic_curves.models import GroupProcessingStrategy
from app.services.characteristic_curves.shared.exceptions import (
    CurveFittingError,
    InsufficientDataError,
)


class GroupDataExtractor:
    """泵组数据提取器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化数据提取器

        Args:
            config: 配置字典（可选）
        """
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._config = config or self._load_default_config()

    def extract_group_operating_points(
        self,
        station_id: int,
        pump_ids: List[int],
        start_time: datetime,
        end_time: datetime,
    ) -> List[GroupOperatingPoint]:
        """
        提取泵组运行工况点

        Args:
            station_id: 站点ID
            pump_ids: 泵ID列表
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            List[GroupOperatingPoint]: 工况点列表

        Raises:
            InsufficientDataError: 数据不足
            CurveFittingError: 数据提取失败
        """
        from app.adapters.db import get_connection

        sql = """
        WITH metric_ids AS (
            SELECT
                MAX(CASE WHEN metric_key = 'device_running' THEN id END) AS running_id,
                MAX(CASE WHEN metric_key = 'main_pipeline_flow_rate' THEN id END) AS flow_id,
                MAX(CASE WHEN metric_key = 'main_pipeline_outlet_pressure' THEN id END) AS pressure_id,
                MAX(CASE WHEN metric_key = 'main_pipeline_inlet_pressure' THEN id END) AS inlet_pressure_id,
                MAX(CASE WHEN metric_key = 'device_frequency' THEN id END) AS freq_id
            FROM dim_metric_config
        ),
        pump_data AS (
            SELECT
                time_bucket(INTERVAL '5 minutes', fm.ts) AS ts_bucket,
                fm.device_id,
                MAX(CASE WHEN fm.metric_id = mi.running_id THEN fm.value END) AS running,
                AVG(CASE WHEN fm.metric_id = mi.flow_id THEN fm.value END) AS flow,
                AVG(CASE WHEN fm.metric_id = mi.freq_id THEN fm.value END) AS frequency
            FROM fact_measurements fm
            CROSS JOIN metric_ids mi
            JOIN dim_devices dd ON fm.device_id = dd.id
            WHERE dd.station_id = %(station_id)s
              AND fm.device_id = ANY(%(pump_ids)s)
              AND fm.ts >= %(start_time)s
              AND fm.ts < %(end_time)s
              AND fm.metric_id IN (mi.running_id, mi.flow_id, mi.freq_id)
            GROUP BY ts_bucket, fm.device_id
        ),
        station_pressure AS (
            SELECT
                time_bucket(INTERVAL '5 minutes', fm.ts) AS ts_bucket,
                AVG(CASE WHEN fm.metric_id = mi.pressure_id THEN fm.value END) AS outlet_pressure,
                AVG(CASE WHEN fm.metric_id = mi.inlet_pressure_id THEN fm.value END) AS inlet_pressure
            FROM fact_measurements fm
            CROSS JOIN metric_ids mi
            JOIN dim_devices dd ON fm.device_id = dd.id
            WHERE dd.station_id = %(station_id)s
              AND dd.device_type = 'station'
              AND fm.ts >= %(start_time)s
              AND fm.ts < %(end_time)s
              AND fm.metric_id IN (mi.pressure_id, mi.inlet_pressure_id)
            GROUP BY ts_bucket
        ),
        aggregated AS (
            SELECT
                pd.ts_bucket,
                ARRAY_AGG(pd.device_id ORDER BY pd.device_id) FILTER (WHERE pd.running = 1) AS running_pumps,
                COALESCE(SUM(pd.flow) FILTER (WHERE pd.running = 1), 0) AS Q_total,
                COALESCE(sp.outlet_pressure - sp.inlet_pressure, 0) AS H_system,
                jsonb_object_agg(pd.device_id::text, pd.frequency) FILTER (WHERE pd.running = 1 AND pd.frequency IS NOT NULL) AS pump_frequencies
            FROM pump_data pd
            LEFT JOIN station_pressure sp ON pd.ts_bucket = sp.ts_bucket
            GROUP BY pd.ts_bucket, sp.outlet_pressure, sp.inlet_pressure
            HAVING COUNT(*) FILTER (WHERE pd.running = 1) >= 1
        )
        SELECT ts_bucket, running_pumps, Q_total, H_system, pump_frequencies
        FROM aggregated
        WHERE Q_total > 0 AND H_system > 0
        ORDER BY ts_bucket
        """

        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        sql,
                        {
                            "station_id": station_id,
                            "pump_ids": pump_ids,
                            "start_time": start_time,
                            "end_time": end_time,
                        },
                    )
                    rows = cur.fetchall()

            if len(rows) < self._config.get("min_data_points", 100):
                raise InsufficientDataError(
                    f"泵组数据不足：实际{len(rows)}个，要求至少{self._config.get('min_data_points', 100)}个"
                )

            # 转换为GroupOperatingPoint对象
            points = []
            for row in rows:
                ts_bucket, running_pumps, Q_total, H_system, pump_frequencies = row

                # 解析pump_frequencies（JSON格式）
                freq_dict = None
                if pump_frequencies:
                    import json

                    freq_dict = {
                        int(k): float(v) for k, v in json.loads(pump_frequencies).items()
                    }

                point = GroupOperatingPoint(
                    ts_bucket=ts_bucket,
                    Q_total=float(Q_total),
                    H_system=float(H_system),
                    running_pumps=tuple(running_pumps),
                    pump_frequencies=freq_dict,
                )
                points.append(point)

            self._logger.info(
                f"[数据提取] 成功提取{len(points)}个泵组工况点 "
                f"(station_id={station_id}, pumps={pump_ids})"
            )

            return points

        except InsufficientDataError:
            raise
        except Exception as e:
            self._logger.error(f"[数据提取] 提取泵组数据失败: {e}")
            raise CurveFittingError(f"提取泵组数据失败: {e}") from e

    def group_by_pump_combination(
        self, points: List[GroupOperatingPoint]
    ) -> Dict[Tuple[int, ...], List[GroupOperatingPoint]]:
        """
        按泵组合分组

        Args:
            points: 工况点列表

        Returns:
            Dict[Tuple[int, ...], List[GroupOperatingPoint]]:
                {泵组合: 工况点列表}
        """
        groups: Dict[Tuple[int, ...], List[GroupOperatingPoint]] = {}

        for point in points:
            combo = point.running_pumps
            if combo not in groups:
                groups[combo] = []
            groups[combo].append(point)

        self._logger.info(
            f"[数据分组] 按泵组合分组: {len(groups)}个组合, "
            f"组合详情: {[(combo, len(pts)) for combo, pts in groups.items()]}"
        )

        return groups

    def normalize_by_frequency(
        self,
        points: List[GroupOperatingPoint],
        scenario_type: GroupProcessingStrategy,
    ) -> List[GroupOperatingPoint]:
        """
        频率归一化（仅VFD_HETEROGENEOUS_FREQ场景）

        Args:
            points: 工况点列表
            scenario_type: 场景类型

        Returns:
            List[GroupOperatingPoint]: 归一化后的工况点

        Raises:
            CurveFittingError: 频率数据缺失
        """
        # 只有VFD_HETEROGENEOUS_FREQ场景需要频率归一化
        if scenario_type != GroupProcessingStrategy.VFD_HETEROGENEOUS_FREQ:
            return points

        normalized_points = []
        target_freq = 50.0  # 归一化到50Hz

        for point in points:
            if not point.pump_frequencies:
                raise CurveFittingError(
                    f"VFD频率异构场景缺少频率数据: ts={point.ts_bucket}"
                )

            # 计算平均频率
            avg_freq = sum(point.pump_frequencies.values()) / len(
                point.pump_frequencies
            )

            # 频率归一化：Q' = Q × (f_target / f_avg)
            freq_ratio = target_freq / avg_freq
            Q_normalized = point.Q_total * freq_ratio

            normalized_point = GroupOperatingPoint(
                ts_bucket=point.ts_bucket,
                Q_total=Q_normalized,
                H_system=point.H_system,  # 扬程不变
                running_pumps=point.running_pumps,
                pump_frequencies=point.pump_frequencies,
            )
            normalized_points.append(normalized_point)

        self._logger.info(
            f"[频率归一化] 完成归一化: {len(normalized_points)}个点归一化到{target_freq}Hz"
        )

        return normalized_points

    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "min_data_points": 100,  # 最小数据点数
            "time_bucket_interval": "5 minutes",  # 时间桶间隔
            "outlier_threshold": 3.0,  # 异常值阈值（标准差倍数）
        }

    def _validate_data_coverage(
        self, points: List[GroupOperatingPoint], min_points: int
    ) -> None:
        """
        验证数据覆盖率

        Args:
            points: 工况点列表
            min_points: 最小数据点数

        Raises:
            InsufficientDataError: 数据点不足
        """
        if len(points) < min_points:
            raise InsufficientDataError(
                f"数据点不足：实际{len(points)}个，要求至少{min_points}个"
            )

