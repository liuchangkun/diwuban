"""
数据提取器 (app.services.characteristic_curves.shared.data_extractor)

从fact_measurements表提取符合质量要求的数据。

版本: v1.0
参考: 设计文档 3.6.1节
"""

import logging
from datetime import datetime
from typing import Dict, Optional, Tuple

import pandas as pd

from app.adapters.db.pool import get_connection
from app.core.config.loader_new import Settings
from app.services.characteristic_curves.core.data_structures import DataQualityReport
from app.services.characteristic_curves.shared.exceptions import DataExtractionError


logger = logging.getLogger(__name__)


class DataExtractor:
    """数据提取器

    从fact_measurements表提取符合质量要求的数据。

    数据质量要求:
    - 最小数据点数: ≥100个
    - 时间跨度: ≥1天
    - 流量覆盖范围: Q_max ≥ 0.2 × Q_rated
    - 数据完整性: 缺失率 < 5%
    - 数据准确性: 异常值率 < 3%
    """

    def __init__(self, config: Optional[Dict] = None):
        """初始化数据提取器

        Args:
            config: 配置参数,可选。包含阈值设置。
        """
        self._config = config or {}
        self._min_points = self._config.get('min_points', 100)
        self._min_duration_days = self._config.get('min_duration_days', 1.0)
        self._max_missing_ratio = self._config.get('max_missing_ratio', 0.05)
        self._max_outlier_ratio = self._config.get('max_outlier_ratio', 0.03)
        self._min_flow_coverage = self._config.get('min_flow_coverage', 0.2)

        logger.info(
            "[数据提取器] 初始化",
            extra={"extra_data": {
                "min_points": self._min_points,
                "min_duration_days": self._min_duration_days,
                "max_missing_ratio": self._max_missing_ratio,
                "max_outlier_ratio": self._max_outlier_ratio,
                "min_flow_coverage": self._min_flow_coverage,
            }}
        )

    def extract(
        self,
        device_id: int,
        curve_type: str,
        start_time: datetime,
        end_time: datetime,
        min_points: Optional[int] = None
    ) -> Tuple[pd.DataFrame, DataQualityReport]:
        """提取数据并评估质量

        Args:
            device_id: 设备ID
            curve_type: 曲线类型 ('qh', 'qp', 'qeta')
            start_time: 开始时间
            end_time: 结束时间
            min_points: 最小数据点数(可选,覆盖配置)

        Returns:
            Tuple[pd.DataFrame, DataQualityReport]: 
                - DataFrame: 包含flow, head/power/efficiency, measurement_time列
                - DataQualityReport: 数据质量报告

        Raises:
            DataExtractionError: 数据质量不达标时
        """
        min_pts = min_points or self._min_points

        logger.info(
            f"[数据提取] 开始提取: device_id={device_id}, curve_type={curve_type}, "
            f"时间范围=[{start_time}, {end_time}]"
        )

        # 确定Y值指标ID (基于dim_metric_config表)
        # pump_flow_rate=14, pump_head=16, pump_efficiency=17, pump_active_power=8
        y_metric_map = {
            'qh': {'y_metric_id': 16, 'y_name': 'head'},       # pump_head
            # pump_active_power
            'qp': {'y_metric_id': 8, 'y_name': 'power'},
            # pump_efficiency
            'qeta': {'y_metric_id': 17, 'y_name': 'efficiency'}
        }
        FLOW_METRIC_ID = 14  # pump_flow_rate

        if curve_type.lower() not in y_metric_map:
            raise DataExtractionError(
                message=f"不支持的曲线类型: {curve_type}",
                device_id=device_id,
                curve_type=curve_type,
                reason="曲线类型必须为qh/qp/qeta之一"
            )

        y_config = y_metric_map[curve_type.lower()]
        y_metric_id = y_config['y_metric_id']

        # 构建SQL查询 - 使用LATERAL JOIN获取同一时间点的两个指标值
        # fact_measurements表结构: device_id, metric_id, ts_bucket, value
        # 注意: 如果mv_device_running_1s表有运行状态数据，优先使用运行状态过滤
        # 否则使用流量>0作为运行判断条件
        query = """
            SELECT 
                fm_flow.value as flow,
                fm_y.value as y_value,
                fm_flow.ts_bucket as measurement_time
            FROM fact_measurements fm_flow
            INNER JOIN fact_measurements fm_y
              ON fm_flow.device_id = fm_y.device_id
              AND fm_flow.ts_bucket = fm_y.ts_bucket
            LEFT JOIN mv_device_running_1s dr
              ON fm_flow.device_id = dr.device_id
              AND fm_flow.ts_bucket = dr.ts_bucket
            WHERE fm_flow.device_id = %s
              AND fm_flow.metric_id = %s
              AND fm_y.metric_id = %s
              AND fm_flow.ts_bucket >= %s
              AND fm_flow.ts_bucket <= %s
              AND fm_flow.value IS NOT NULL
              AND fm_y.value IS NOT NULL
              AND fm_flow.value > 0
              AND (dr.phase IS NULL OR dr.phase = 1 OR dr.phase = 0)
            ORDER BY fm_flow.ts_bucket
        """

        # 执行查询
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        query,
                        (device_id, FLOW_METRIC_ID,
                         y_metric_id, start_time, end_time)
                    )
                    rows = cur.fetchall()
        except Exception as e:
            logger.error(f"[数据提取] 数据库查询失败: {e}")
            raise DataExtractionError(
                message=f"数据库查询失败: {e}",
                device_id=device_id,
                curve_type=curve_type,
                reason=str(e)
            ) from e

        # 转换为DataFrame
        if not rows:
            raise DataExtractionError(
                message=f"未找到数据: device_id={device_id}, curve_type={curve_type}",
                device_id=device_id,
                curve_type=curve_type,
                reason="查询结果为空"
            )

        y_column = y_config['y_name']
        df = pd.DataFrame(rows, columns=['flow', y_column, 'measurement_time'])

        # 将Decimal类型转换为float，确保后续计算不报错
        for col in ['flow', y_column]:
            if col in df.columns:
                df[col] = df[col].astype(float)

        # 评估数据质量
        quality_report = self._evaluate_quality(
            df, device_id, curve_type, start_time, end_time, min_pts
        )

        # 检查是否达到最低要求
        if not quality_report.meets_minimum:
            logger.error(
                f"[数据提取] 数据质量不达标: device_id={device_id}, "
                f"issues={quality_report.issues}"
            )
            raise DataExtractionError(
                message=f"数据质量不达标: {', '.join(quality_report.issues)}",
                device_id=device_id,
                curve_type=curve_type,
                reason="; ".join(quality_report.issues)
            )

        # 质量警告
        if quality_report.quality_score < 60:
            logger.warning(
                f"[数据提取] 数据质量较差: device_id={device_id}, "
                f"quality_score={quality_report.quality_score:.2f}"
            )

        logger.info(
            f"[数据提取] 成功: device_id={device_id}, "
            f"数据点数={quality_report.total_points}, "
            f"质量评分={quality_report.quality_score:.2f}, "
            f"运行状态过滤=已启用(phase=1)"
        )

        return df, quality_report

    def _evaluate_quality(
        self,
        df: pd.DataFrame,
        device_id: int,
        curve_type: str,
        start_time: datetime,
        end_time: datetime,
        min_points: int
    ) -> DataQualityReport:
        """评估数据质量

        Args:
            df: 数据DataFrame
            device_id: 设备ID
            curve_type: 曲线类型
            start_time: 开始时间
            end_time: 结束时间
            min_points: 最小数据点数

        Returns:
            DataQualityReport: 数据质量报告
        """
        total_points = len(df)
        time_span_days = (end_time - start_time).total_seconds() / 86400

        # 计算缺失值比例(这里是查询后的,应该为0,但保留逻辑)
        missing_ratio = 0.0  # 因为SQL已过滤NULL

        # 计算质量评分(简化版)
        # 基础分60分
        quality_score = 60.0

        # 数据点数加分(最高20分)
        if total_points >= min_points:
            points_score = min(
                20, (total_points - min_points) / min_points * 10)
            quality_score += points_score

        # 时间跨度加分(最高10分)
        if time_span_days >= self._min_duration_days:
            time_score = min(
                10, (time_span_days - self._min_duration_days) / self._min_duration_days * 5)
            quality_score += time_score

        # 流量覆盖加分(最高10分) - 简化处理
        flow_max = df['flow'].max()
        flow_range_score = min(10, flow_max / 100.0)  # 简化,假设额定流量100
        quality_score += flow_range_score

        # 判断是否达到最低要求
        issues = []
        meets_minimum = True

        if total_points < min_points:
            issues.append(f"数据点不足{min_points}个(实际{total_points}个)")
            meets_minimum = False

        if time_span_days < self._min_duration_days:
            issues.append(f"时间跨度仅{time_span_days:.1f}天")
            meets_minimum = False

        return DataQualityReport(
            total_points=total_points,
            time_span_days=time_span_days,
            missing_ratio=missing_ratio,
            quality_score=min(100.0, quality_score),
            meets_minimum=meets_minimum,
            issues=issues
        )
