"""泵组数据提取器 (app.services.characteristic_curves.pump_group.group_data_extractor)

从fact_measurements表提取泵组运行工况点。

核心功能：
- 提取泵组运行工况点（extract_group_operating_points）
- 提取完整工况点含功率/效率/频率（extract_full_operating_points）
- 按泵组合分组（group_by_pump_combination）
- 频率归一化处理（normalize_by_frequency）

版本: v2.0
创建日期: 2025-12-13
更新日期: 2025-12-14

v2.0更新：
- 新增 extract_full_operating_points 方法，支持P_total、eta_total、频率提取
- 支持Q-P、Q-η曲线拟合所需数据
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from app.adapters.db import get_connection
from app.services.characteristic_curves.core.data_structures import GroupOperatingPoint


logger = logging.getLogger(__name__)


class GroupDataExtractor:
    """泵组数据提取器

    从fact_measurements表提取泵组运行工况点
    """

    def __init__(self):
        """初始化"""
        self._logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}")

    def extract_group_operating_points(
        self,
        station_id: int,
        start_time: datetime,
        end_time: datetime,
        min_running_pumps: int = 1
    ) -> List[GroupOperatingPoint]:
        """提取泵组运行工况点

        数据来源:
        - Q_total: main_pipeline_flow_rate指标
        - H_system: main_pipeline_outlet_pressure × 10.2
        - n_running: 统计各泵running状态

        Args:
            station_id: 泵站ID
            start_time: 开始时间
            end_time: 结束时间
            min_running_pumps: 最少运行泵数量

        Returns:
            List[GroupOperatingPoint]: 工况点列表
        """
        self._logger.info(
            f"[泵组数据提取] 开始提取: station_id={station_id}",
            extra={"extra_data": {
                "station_id": station_id,
                "start_time": start_time,
                "end_time": end_time
            }}
        )

        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    # 查询泵组工况点
                    # 注意：fact_measurements 表使用 metric_id 而非 metric_key
                    # 需要先通过 dim_metric_config 获取 metric_id
                    cur.execute("""
                        WITH metric_ids AS (
                            SELECT
                                id,
                                metric_key
                            FROM dim_metric_config
                            WHERE metric_key IN (
                                'running',
                                'pump_flow_rate',
                                'main_pipeline_outlet_pressure'
                            )
                        ),
                        pump_metrics AS (
                            SELECT
                                fm.ts_bucket,
                                fm.device_id,
                                MAX(CASE WHEN m.metric_key = 'running' THEN fm.value END) AS running,
                                MAX(CASE WHEN m.metric_key = 'pump_flow_rate' THEN fm.value END) AS flow
                            FROM fact_measurements fm
                            JOIN metric_ids m ON fm.metric_id = m.id
                            WHERE fm.ts_bucket >= %s AND fm.ts_bucket < %s
                            GROUP BY fm.ts_bucket, fm.device_id
                        ),
                        station_head AS (
                            SELECT
                                fm.ts_bucket,
                                fm.value * 10.2 AS H_system
                            FROM fact_measurements fm
                            JOIN metric_ids m ON fm.metric_id = m.id
                            WHERE m.metric_key = 'main_pipeline_outlet_pressure'
                              AND fm.ts_bucket >= %s AND fm.ts_bucket < %s
                        ),
                        aggregated AS (
                            SELECT
                                pm.ts_bucket,
                                array_agg(pm.device_id ORDER BY pm.device_id)
                                    FILTER (WHERE pm.running = 1) AS running_pumps,
                                SUM(pm.flow) FILTER (WHERE pm.running = 1) AS Q_total,
                                sh.H_system
                            FROM pump_metrics pm
                            JOIN station_head sh ON pm.ts_bucket = sh.ts_bucket
                            GROUP BY pm.ts_bucket, sh.H_system
                        )
                        SELECT
                            ts_bucket,
                            running_pumps,
                            Q_total,
                            H_system
                        FROM aggregated
                        WHERE array_length(running_pumps, 1) >= %s
                          AND Q_total > 0
                          AND H_system > 0
                        ORDER BY ts_bucket
                    """, (start_time, end_time, start_time, end_time, min_running_pumps))

                    rows = cur.fetchall()

                    points = [
                        GroupOperatingPoint(
                            ts_bucket=row[0],
                            station_id=station_id,
                            Q_total=float(row[2]),
                            H_system=float(row[3]),
                            n_running=len(row[1]) if row[1] else 0,
                            running_pump_ids=tuple(
                                sorted(row[1])) if row[1] else tuple()
                        )
                        for row in rows
                    ]

                    self._logger.info(
                        f"[泵组数据提取] 提取完成: {len(points)}个工况点",
                        extra={"extra_data": {
                            "station_id": station_id,
                            "points_count": len(points)
                        }}
                    )

                    return points

        except Exception as e:
            self._logger.error(
                f"[泵组数据提取] 提取失败: {e}",
                extra={"extra_data": {"error": str(e)}},
                exc_info=True
            )
            raise

    def group_by_pump_combination(
        self,
        points: List[GroupOperatingPoint]
    ) -> Dict[str, List[GroupOperatingPoint]]:
        """按泵组合分组（支持任意组合）

        Args:
            points: 工况点列表

        Returns:
            Dict[str, List[GroupOperatingPoint]]: 按组合分组的工况点
                key: "1,2,3" (排序后的泵ID组合)
                value: 对应的工况点列表
        """
        grouped = {}
        for point in points:
            if point.running_pump_ids:
                # 使用 pump_combination_key 属性（已在 GroupOperatingPoint 中定义）
                key = point.pump_combination_key
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append(point)

        self._logger.info(
            f"[泵组数据提取] 分组完成: {len(grouped)}个组合",
            extra={"extra_data": {
                "combinations": list(grouped.keys()),
                "points_per_combination": {k: len(v) for k, v in grouped.items()}
            }}
        )

        return grouped

    def extract_full_operating_points(
        self,
        station_id: int,
        start_time: datetime,
        end_time: datetime,
        min_running_pumps: int = 1
    ) -> List[GroupOperatingPoint]:
        """提取完整泵组运行工况点（含P_total、eta_total、频率）

        用于Q-P曲线和Q-η曲线拟合。

        数据来源:
        - Q_total: 各泵flow_rate之和
        - H_system: main_pipeline_outlet_pressure × 10.2
        - P_total: 各泵power之和
        - eta_total: (ρgQH) / P_total（ρ=1000, g=9.81）
        - pump_frequencies: 各泵pump_frequency

        Args:
            station_id: 泵站ID
            start_time: 开始时间
            end_time: 结束时间
            min_running_pumps: 最少运行泵数量

        Returns:
            List[GroupOperatingPoint]: 完整工况点列表
        """
        self._logger.info(
            f"[泵组数据提取] 开始提取完整工况点: station_id={station_id}",
            extra={"extra_data": {
                "station_id": station_id,
                "start_time": start_time,
                "end_time": end_time
            }}
        )

        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    # 提取完整工况点（含功率、效率、频率）
                    # 注意：fact_measurements 表使用 metric_id 而非 metric_key
                    cur.execute("""
                        WITH metric_ids AS (
                            SELECT
                                id,
                                metric_key
                            FROM dim_metric_config
                            WHERE metric_key IN (
                                'running',
                                'pump_flow_rate',
                                'pump_active_power',
                                'pump_frequency',
                                'main_pipeline_outlet_pressure'
                            )
                        ),
                        pump_metrics AS (
                            SELECT
                                fm.ts_bucket,
                                fm.device_id,
                                MAX(CASE WHEN m.metric_key = 'running' THEN fm.value END) AS running,
                                MAX(CASE WHEN m.metric_key = 'pump_flow_rate' THEN fm.value END) AS flow,
                                MAX(CASE WHEN m.metric_key = 'pump_active_power' THEN fm.value END) AS power,
                                MAX(CASE WHEN m.metric_key = 'pump_frequency' THEN fm.value END) AS frequency
                            FROM fact_measurements fm
                            JOIN metric_ids m ON fm.metric_id = m.id
                            WHERE fm.ts_bucket >= %s AND fm.ts_bucket < %s
                            GROUP BY fm.ts_bucket, fm.device_id
                        ),
                        station_head AS (
                            SELECT
                                fm.ts_bucket,
                                fm.value * 10.2 AS H_system
                            FROM fact_measurements fm
                            JOIN metric_ids m ON fm.metric_id = m.id
                            WHERE m.metric_key = 'main_pipeline_outlet_pressure'
                              AND fm.ts_bucket >= %s AND fm.ts_bucket < %s
                        ),
                        aggregated AS (
                            SELECT
                                pm.ts_bucket,
                                array_agg(pm.device_id ORDER BY pm.device_id)
                                    FILTER (WHERE pm.running = 1) AS running_pumps,
                                SUM(pm.flow) FILTER (WHERE pm.running = 1) AS Q_total,
                                SUM(pm.power) FILTER (WHERE pm.running = 1) AS P_total,
                                jsonb_object_agg(
                                    pm.device_id::text, pm.frequency
                                ) FILTER (WHERE pm.running = 1 AND pm.frequency IS NOT NULL) AS frequencies,
                                -- 功率加权平均频率（物理意义：大功率泵对特性影响更大）
                                -- 使用实际功率而非额定功率，反映当前工况贡献
                                CASE 
                                    WHEN SUM(pm.power) FILTER (WHERE pm.running = 1 AND pm.power > 0) > 0 
                                    THEN SUM(pm.power * pm.frequency) FILTER (WHERE pm.running = 1 AND pm.power > 0)
                                         / SUM(pm.power) FILTER (WHERE pm.running = 1 AND pm.power > 0)
                                    ELSE AVG(pm.frequency) FILTER (WHERE pm.running = 1)
                                END AS avg_frequency,
                                sh.H_system
                            FROM pump_metrics pm
                            JOIN station_head sh ON pm.ts_bucket = sh.ts_bucket
                            GROUP BY pm.ts_bucket, sh.H_system
                        )
                        SELECT
                            ts_bucket,
                            running_pumps,
                            Q_total,
                            H_system,
                            P_total,
                            frequencies,
                            avg_frequency
                        FROM aggregated
                        WHERE array_length(running_pumps, 1) >= %s
                          AND Q_total > 0
                          AND H_system > 0
                        ORDER BY ts_bucket
                    """, (start_time, end_time, start_time, end_time, min_running_pumps))

                    rows = cur.fetchall()

                    points = []
                    for row in rows:
                        ts_bucket = row[0]
                        running_pumps = row[1]
                        Q_total = float(row[2]) if row[2] else 0.0
                        H_system = float(row[3]) if row[3] else 0.0
                        P_total = float(row[4]) if row[4] else None
                        frequencies = row[5]  # jsonb
                        avg_frequency = float(row[6]) if row[6] else None

                        # 计算效率: η = (ρgQH) / P
                        # ρ = 1000 kg/m³, g = 9.81 m/s², Q 需转为 m³/s
                        eta_total = None
                        if P_total and P_total > 0 and Q_total > 0 and H_system > 0:
                            # Q_total: m³/h → m³/s
                            Q_m3s = Q_total / 3600
                            # 水力功率: kW
                            hydraulic_power = 1000 * 9.81 * Q_m3s * H_system / 1000
                            eta_total = hydraulic_power / P_total
                            # 限制效率范围
                            eta_total = min(max(eta_total, 0.0), 1.0)

                        # 解析频率字典
                        pump_frequencies = None
                        if frequencies:
                            pump_frequencies = {
                                int(k): float(v) for k, v in frequencies.items()
                            }

                        points.append(GroupOperatingPoint(
                            ts_bucket=ts_bucket,
                            station_id=station_id,
                            Q_total=Q_total,
                            H_system=H_system,
                            P_total=P_total,
                            eta_total=eta_total,
                            n_running=len(
                                running_pumps) if running_pumps else 0,
                            running_pump_ids=tuple(
                                sorted(running_pumps)) if running_pumps else tuple(),
                            pump_frequencies=pump_frequencies,
                            avg_frequency=avg_frequency
                        ))

                    self._logger.info(
                        f"[泵组数据提取] 完整工况点提取完成: {len(points)}个",
                        extra={"extra_data": {
                            "station_id": station_id,
                            "points_count": len(points),
                            "has_power": sum(1 for p in points if p.P_total is not None),
                            "has_efficiency": sum(1 for p in points if p.eta_total is not None)
                        }}
                    )

                    return points

        except Exception as e:
            self._logger.error(
                f"[泵组数据提取] 完整工况点提取失败: {e}",
                extra={"extra_data": {"error": str(e)}},
                exc_info=True
            )
            raise

    def normalize_by_frequency(
        self,
        points: List[GroupOperatingPoint],
        target_freq: float = 50.0
    ) -> List[GroupOperatingPoint]:
        """频率归一化（用于VFD_HETEROGENEOUS_FREQ场景）

        将所有工况点归一化到目标频率（通常为50Hz）。

        Args:
            points: 工况点列表
            target_freq: 目标频率（Hz），默认50Hz

        Returns:
            List[GroupOperatingPoint]: 归一化后的工况点列表
        """
        normalized = []
        for point in points:
            if point.avg_frequency and point.avg_frequency != target_freq:
                normalized.append(point.to_normalized(target_freq))
            else:
                normalized.append(point)

        self._logger.info(
            f"[泵组数据提取] 频率归一化完成: {len(normalized)}个工况点 → {target_freq}Hz",
            extra={"extra_data": {
                "original_count": len(points),
                "normalized_count": sum(1 for p in points if p.avg_frequency and p.avg_frequency != target_freq)
            }}
        )

        return normalized

    def validate_data_coverage(
        self,
        points: List[GroupOperatingPoint],
        min_points: int = 20,
        q_range_ratio: float = 0.5
    ) -> Tuple[bool, Dict[str, any]]:
        """验证数据覆盖度

        检查数据点数量和流量范围是否满足拟合要求。

        Args:
            points: 工况点列表
            min_points: 最少数据点数量
            q_range_ratio: 最小流量范围比例（Q_max/Q_min应大于此值的倒数）

        Returns:
            Tuple[bool, Dict]: (是否满足要求, 详细报告)
        """
        if not points:
            return False, {"reason": "no_data", "count": 0}

        count = len(points)
        q_values = [p.Q_total for p in points]
        q_min, q_max = min(q_values), max(q_values)
        q_range = q_max - q_min
        q_ratio = q_max / q_min if q_min > 0 else 0

        report = {
            "count": count,
            "q_min": q_min,
            "q_max": q_max,
            "q_range": q_range,
            "q_ratio": q_ratio,
            "min_points_required": min_points,
            "q_range_ratio_required": q_range_ratio
        }

        is_valid = count >= min_points and q_ratio >= (
            1 / q_range_ratio if q_range_ratio > 0 else 0)
        report["is_valid"] = is_valid

        if not is_valid:
            if count < min_points:
                report["reason"] = "insufficient_points"
            else:
                report["reason"] = "insufficient_q_range"

        return is_valid, report
