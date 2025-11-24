"""
泵 k 系数学习器（app.services.calculation.metrics.pump_flow_rate.pump_k_coefficient.learner）

本模块实现从高频运行数据自动学习泵的 k 系数。

核心原理：
    当泵在高频（f > 40Hz）运行时，假设一定在出水，此时：
    H_pump ≈ H_system（稳态平衡）
    k × f² ≈ P_outlet × 102

    解得：k = P_outlet × 102 / f²

使用方式：
    from app.services.calculation.metrics.pump_flow_rate.pump_k_coefficient import PumpKCoefficientLearner

    learner = PumpKCoefficientLearner()
    result = learner.learn_k_for_station(station_id=1, start_time=..., end_time=...)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
import statistics

from app.adapters.db.pool import get_connection
from app.services.calculation.shared.parameter_manager import ParameterManager
from .constants import (
    PRESSURE_TO_HEAD,
    CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, CONFIDENCE_LOW,
    PARAM_NAME_K_COEFFICIENT, METRIC_KEY,
    PARAM_NAME_H_RATED_DEFAULT, PARAM_NAME_F_RATED,
    PARAM_NAME_K_DEFAULT, PARAM_NAME_K_MIN, PARAM_NAME_K_MAX,
    PARAM_NAME_HIGH_FREQ_THRESHOLD, PARAM_NAME_MIN_SAMPLES,
)

_log = logging.getLogger(__name__)


class PumpKCoefficientLearner:
    """
    泵 k 系数学习器

    从高频运行数据自动学习每台泵的 k 系数，并保存到 calculation_parameters 表。
    所有配置参数从数据库 calculation_parameters 表读取。
    """

    def __init__(self, trace_id: Optional[str] = None):
        """
        初始化学习器

        Args:
            trace_id: 追踪ID，用于日志关联
        """
        self.trace_id = trace_id or "pump_k_learning"
        self.logger = _log
        self._param_manager = ParameterManager()
        self._params: Dict[str, float] = {}

    def _load_params(self, station_id: int) -> None:
        """加载参数（从数据库，使用 ParameterManager 三级合并）"""
        if self._params:
            return  # 已加载
        self._params = self._param_manager.get_parameters(
            metric_key=METRIC_KEY, station_id=station_id
        )

    def _get_param(self, name: str) -> float:
        """获取参数值"""
        if name not in self._params:
            raise ValueError(f"参数 {name} 未在数据库中配置")
        return float(self._params[name])

    def learn_k_for_device(
        self,
        station_id: int,
        device_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """
        从高频数据学习单个设备的 k 值

        Args:
            station_id: 泵站ID
            device_id: 设备ID
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            Dict: {
                'k_value': float,
                'sample_count': int,
                'confidence': str,
                'source': str,
                'k_values_stats': dict  # 统计信息
            }
        """
        # 加载参数
        self._load_params(station_id)
        min_samples = int(self._get_param(PARAM_NAME_MIN_SAMPLES))
        k_min = self._get_param(PARAM_NAME_K_MIN)
        k_max = self._get_param(PARAM_NAME_K_MAX)
        k_default = self._get_param(PARAM_NAME_K_DEFAULT)

        self.logger.info(
            f"[k系数学习] 开始学习设备 k 值",
            extra={'extra_data': {
                'trace_id': self.trace_id,
                'station_id': station_id,
                'device_id': device_id,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
            }}
        )

        # 从数据库查询高频运行数据
        k_samples = self._query_high_freq_data(station_id, device_id, start_time, end_time)

        if len(k_samples) >= min_samples:
            # 样本充足，使用中位数
            k_value = statistics.median(k_samples)
            k_mean = statistics.mean(k_samples)
            k_std = statistics.stdev(k_samples) if len(k_samples) > 1 else 0.0
            source = "learned_from_data"
            confidence = CONFIDENCE_HIGH if len(k_samples) >= 1000 else CONFIDENCE_MEDIUM

            self.logger.info(
                f"[k系数学习] 从数据学习 k 值成功",
                extra={'extra_data': {
                    'device_id': device_id,
                    'k_value': k_value,
                    'k_mean': k_mean,
                    'k_std': k_std,
                    'sample_count': len(k_samples),
                    'confidence': confidence,
                }}
            )
        else:
            # 样本不足，使用回退值
            k_value, source = self._get_fallback_k(station_id, device_id)
            k_mean = k_value
            k_std = 0.0
            confidence = CONFIDENCE_LOW

            self.logger.warning(
                f"[k系数学习] 样本不足，使用回退值",
                extra={'extra_data': {
                    'device_id': device_id,
                    'sample_count': len(k_samples),
                    'min_required': min_samples,
                    'k_value': k_value,
                    'source': source,
                }}
            )

        # 验证 k 值范围
        if k_value < k_min or k_value > k_max:
            self.logger.warning(
                f"[k系数学习] k 值超出合理范围，使用默认值",
                extra={'extra_data': {
                    'device_id': device_id,
                    'original_k': k_value,
                    'k_min': k_min,
                    'k_max': k_max,
                    'default_k': k_default,
                }}
            )
            k_value = k_default
            source = "default_out_of_range"
            confidence = CONFIDENCE_LOW

        return {
            'k_value': k_value,
            'sample_count': len(k_samples),
            'confidence': confidence,
            'source': source,
            'k_values_stats': {
                'mean': k_mean,
                'std': k_std,
                'min': min(k_samples) if k_samples else None,
                'max': max(k_samples) if k_samples else None,
            }
        }

    def learn_k_for_station(
        self,
        station_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[int, Dict[str, Any]]:
        """
        批量学习泵站所有泵的 k 值

        Args:
            station_id: 泵站ID
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            Dict[int, Dict]: {device_id: {k_value, sample_count, ...}}
        """
        self.logger.info(
            f"[k系数学习] 开始批量学习泵站 k 值",
            extra={'extra_data': {
                'trace_id': self.trace_id,
                'station_id': station_id,
            }}
        )

        # 查询泵站所有泵设备
        pump_devices = self._get_pump_devices(station_id)

        results = {}
        for device_id in pump_devices:
            result = self.learn_k_for_device(station_id, device_id, start_time, end_time)
            results[device_id] = result

        self.logger.info(
            f"[k系数学习] 批量学习完成",
            extra={'extra_data': {
                'station_id': station_id,
                'device_count': len(results),
                'summary': {
                    did: {'k': r['k_value'], 'conf': r['confidence']}
                    for did, r in results.items()
                }
            }}
        )

        return results

    def save_k_to_db(
        self,
        station_id: int,
        device_id: int,
        k_value: float,
        sample_count: int,
        source: str,
        confidence: str
    ) -> bool:
        """
        保存 k 值到数据库

        Args:
            station_id: 泵站ID
            device_id: 设备ID
            k_value: k 系数值
            sample_count: 样本数量
            source: 数据来源
            confidence: 置信度

        Returns:
            bool: 是否保存成功
        """
        # 置信度分数映射
        confidence_score = {
            CONFIDENCE_HIGH: 0.9,
            CONFIDENCE_MEDIUM: 0.7,
            CONFIDENCE_LOW: 0.3
        }.get(confidence, 0.5)

        # 元数据文本
        meta_text = f"source={source};samples={sample_count};confidence={confidence}"

        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    # 检查是否已存在
                    cur.execute("""
                        SELECT id FROM calculation_parameters
                        WHERE station_id = %s AND device_id = %s
                          AND metric_key = %s AND param_name = %s
                    """, [station_id, device_id, METRIC_KEY, PARAM_NAME_K_COEFFICIENT])

                    existing = cur.fetchone()

                    if existing:
                        # 更新已存在的记录
                        cur.execute("""
                            UPDATE calculation_parameters
                            SET param_value = %s,
                                confidence_score = %s,
                                param_value_text = %s,
                                updated_at = NOW(),
                                updated_by = 'pump_k_learner'
                            WHERE id = %s
                        """, [k_value, confidence_score, meta_text, existing[0]])
                    else:
                        # 插入新记录
                        cur.execute("""
                            INSERT INTO calculation_parameters (
                                station_id, device_id, metric_key, param_name, param_value,
                                param_type, is_optimizable, confidence_score, param_value_text
                            ) VALUES (
                                %s, %s, %s, %s, %s,
                                'float', true, %s, %s
                            )
                        """, [
                            station_id, device_id, METRIC_KEY, PARAM_NAME_K_COEFFICIENT,
                            k_value, confidence_score, meta_text
                        ])

                conn.commit()

            self.logger.info(
                f"[k系数学习] k 值已保存到数据库",
                extra={'extra_data': {
                    'device_id': device_id,
                    'k_value': k_value,
                    'confidence': confidence,
                }}
            )
            return True

        except Exception as e:
            self.logger.error(
                f"[k系数学习] 保存 k 值失败",
                extra={'extra_data': {
                    'device_id': device_id,
                    'error': str(e),
                }}
            )
            return False

    def _query_high_freq_data(
        self,
        station_id: int,
        device_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> List[float]:
        """
        查询高频运行数据并计算 k 值样本

        Returns:
            List[float]: k 值样本列表
        """
        # 从数据库参数获取阈值
        high_freq_threshold = self._get_param(PARAM_NAME_HIGH_FREQ_THRESHOLD)
        k_min = self._get_param(PARAM_NAME_K_MIN)
        k_max = self._get_param(PARAM_NAME_K_MAX)

        sql = """
            WITH freq_data AS (
                SELECT fm.ts_bucket, fm.value AS frequency
                FROM fact_measurements fm
                JOIN dim_metric_config dmc ON fm.metric_id = dmc.id
                WHERE fm.device_id = %s
                  AND dmc.metric_key = 'pump_frequency'
                  AND fm.ts_bucket >= %s
                  AND fm.ts_bucket < %s
                  AND fm.value > %s  -- 高频阈值
            ),
            pressure_data AS (
                SELECT fm.ts_bucket, fm.value AS pressure
                FROM fact_measurements fm
                JOIN dim_metric_config dmc ON fm.metric_id = dmc.id
                JOIN dim_devices dd ON fm.device_id = dd.id
                WHERE dd.type = 'main_pipeline'
                  AND dd.station_id = %s
                  AND dmc.metric_key = 'main_pipeline_outlet_pressure'
                  AND fm.ts_bucket >= %s
                  AND fm.ts_bucket < %s
            )
            SELECT f.frequency, p.pressure
            FROM freq_data f
            JOIN pressure_data p ON f.ts_bucket = p.ts_bucket
            WHERE p.pressure > 0.01  -- 排除无效压力数据
        """

        k_samples = []
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, [
                        device_id, start_time, end_time, high_freq_threshold,
                        station_id, start_time, end_time
                    ])
                    rows = cur.fetchall()

                    for freq, pressure in rows:
                        freq_f = float(freq)
                        pressure_f = float(pressure)
                        if freq_f > 0:
                            # k = P_outlet × 102 / f²
                            k = pressure_f * PRESSURE_TO_HEAD / (freq_f ** 2)
                            if k_min <= k <= k_max:  # 过滤异常值
                                k_samples.append(k)

            self.logger.debug(
                f"[k系数学习] 高频数据查询完成",
                extra={'extra_data': {
                    'device_id': device_id,
                    'raw_count': len(rows) if 'rows' in dir() else 0,
                    'valid_count': len(k_samples),
                }}
            )

        except Exception as e:
            self.logger.error(
                f"[k系数学习] 查询高频数据失败",
                extra={'extra_data': {
                    'device_id': device_id,
                    'error': str(e),
                }}
            )

        return k_samples

    def _get_fallback_k(self, station_id: int, device_id: int) -> Tuple[float, str]:
        """
        获取回退 k 值

        优先从 device_rated_params 表读取 rated_head，
        计算 k = rated_head / f_rated²；
        如无，则使用数据库中的 k_default。

        Returns:
            Tuple[float, str]: (k_value, source)
        """
        f_rated = self._get_param(PARAM_NAME_F_RATED)
        k_default = self._get_param(PARAM_NAME_K_DEFAULT)

        sql = """
            SELECT value_numeric
            FROM device_rated_params
            WHERE device_id = %s AND param_key = 'rated_head'
            LIMIT 1
        """

        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, [device_id])
                    row = cur.fetchone()

                    if row and row[0]:
                        rated_head = float(row[0])
                        k = rated_head / (f_rated ** 2)
                        return k, "from_rated_head"

        except Exception as e:
            self.logger.warning(
                f"[k系数学习] 查询额定扬程失败",
                extra={'extra_data': {'device_id': device_id, 'error': str(e)}}
            )

        # 使用数据库配置的默认值
        return k_default, "default"

    def _get_pump_devices(self, station_id: int) -> List[int]:
        """
        获取泵站所有泵设备ID

        Args:
            station_id: 泵站ID

        Returns:
            List[int]: 泵设备ID列表
        """
        sql = """
            SELECT id FROM dim_devices
            WHERE station_id = %s AND type = 'pump'
            ORDER BY id
        """

        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, [station_id])
                    return [row[0] for row in cur.fetchall()]

        except Exception as e:
            self.logger.error(
                f"[k系数学习] 查询泵设备失败",
                extra={'extra_data': {'station_id': station_id, 'error': str(e)}}
            )
            return []

