"""
频率数据提供器 (app.services.characteristic_curves.pump_group.frequency_data_provider)

本模块提供变频泵频率数据查询功能：
- 从数据库查询历史频率数据（用于离线分析）
- 验证频率数据的有效性
- 计算泵组频率标准差（用于判断是否需要频率归一化）

版本: v1.0
更新日期: 2025-12-09
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import logging

import numpy as np

from app.services.characteristic_curves.shared.exceptions import FrequencyQueryError


class FrequencyDataProvider:
    """
    变频泵频率数据提供器

    职责：
    1. 从数据库查询历史频率数据（用于离线分析）
    2. 验证频率数据的有效性
    3. 计算泵组频率标准差
    """

    def __init__(self):
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._freq_config = self._load_frequency_config()

    def _load_frequency_config(self) -> Dict[str, Any]:
        """从配置加载频率参数"""
        try:
            from app.services.characteristic_curves.shared.config_loader import (
                load_curve_fitting_config,
            )

            config = load_curve_fitting_config()
            return config.get(
                "frequency_normalization",
                {
                    "reference_freq": 50.0,
                    "min_freq": 25.0,
                    "max_freq": 60.0,
                    "default_freq": 50.0,
                },
            )
        except ImportError:
            self._logger.warning(
                "[频率配置] config_loader未找到，使用默认配置"
            )
            return {
                "reference_freq": 50.0,
                "min_freq": 25.0,
                "max_freq": 60.0,
                "default_freq": 50.0,
            }

    @property
    def reference_freq(self) -> float:
        """参考频率（归一化基准）"""
        return self._freq_config.get("reference_freq", 50.0)

    @property
    def min_freq(self) -> float:
        """最小有效频率"""
        return self._freq_config.get("min_freq", 25.0)

    @property
    def max_freq(self) -> float:
        """最大有效频率"""
        return self._freq_config.get("max_freq", 60.0)

    def get_latest_frequencies(
        self, pump_ids: List[int], timestamp: Optional[datetime] = None
    ) -> Dict[int, float]:
        """
        获取各泵的最新运行频率（v2.0: 不使用默认值，查询失败直接抛异常）

        Args:
            pump_ids: 泵ID列表
            timestamp: 时间点（None表示最新）

        Returns:
            Dict[int, float]: 泵ID → 频率 映射

        Raises:
            FrequencyQueryError: 当无法获取某泵频率时抛出

        Note:
            ✅ v2.0修复问题#2：不使用default_freq降级，直接抛异常
            ✅ v3.14修复：使用metric_key='pump_frequency'查询
        """
        frequencies: Dict[int, float] = {}

        try:
            from app.adapters.db.pool import get_connection

            with get_connection() as conn:
                with conn.cursor() as cursor:
                    for pump_id in pump_ids:
                        # ✅ v3.14修复：使用metric_key='pump_frequency'查询频率
                        if timestamp:
                            sql = """
                                SELECT fm.value AS freq
                                FROM fact_measurements fm
                                WHERE fm.device_id = %s
                                  AND fm.metric_id = (
                                      SELECT id FROM dim_metric_config
                                      WHERE metric_key = 'pump_frequency'
                                  )
                                  AND fm.ts_raw <= %s
                                ORDER BY fm.ts_raw DESC
                                LIMIT 1
                            """
                            cursor.execute(sql, (pump_id, timestamp))
                        else:
                            sql = """
                                SELECT fm.value AS freq
                                FROM fact_measurements fm
                                WHERE fm.device_id = %s
                                  AND fm.metric_id = (
                                      SELECT id FROM dim_metric_config
                                      WHERE metric_key = 'pump_frequency'
                                  )
                                ORDER BY fm.ts_raw DESC
                                LIMIT 1
                            """
                            cursor.execute(sql, (pump_id,))

                        row = cursor.fetchone()

                        if row is None:
                            # ✅ v2.0: 直接抛异常，不使用默认值
                            raise FrequencyQueryError(
                                message=f"无法获取泵 {pump_id} 的频率数据",
                                pump_id=pump_id,
                                reason="no_data",
                            )

                        freq = float(row[0])

                        # 验证频率范围
                        if not (self.min_freq <= freq <= self.max_freq):
                            raise FrequencyQueryError(
                                message=(
                                    f"泵 {pump_id} 频率 {freq}Hz "
                                    f"超出有效范围 [{self.min_freq}, {self.max_freq}]"
                                ),
                                pump_id=pump_id,
                                reason="out_of_range",
                                actual_freq=freq,
                            )

                        frequencies[pump_id] = freq

        except FrequencyQueryError:
            raise
        except Exception as e:
            self._logger.error(f"[频率查询] 数据库错误: {e}")
            raise FrequencyQueryError(
                message=f"频率查询失败: {e}",
                pump_id=pump_ids[0] if pump_ids else 0,
                reason="db_error",
            )

        return frequencies

    def calculate_freq_std(
        self, pump_ids: List[int], timestamp: Optional[datetime] = None
    ) -> float:
        """
        计算泵组频率标准差

        用于判断是否需要执行相似定律归一化。
        如果标准差 > 2Hz，建议执行频率归一化。

        Args:
            pump_ids: 泵ID列表
            timestamp: 时间点（None表示最新）

        Returns:
            float: 频率标准差 (Hz)

        Raises:
            FrequencyQueryError: 当无法获取频率时抛出

        Example:
            >>> provider = FrequencyDataProvider()
            >>> freq_std = provider.calculate_freq_std([101, 102, 103])
            >>> if freq_std > 2.0:  # 频率变化超过2Hz
            ...     # 执行相似定律归一化
            ...     pass
        """
        frequencies = self.get_latest_frequencies(pump_ids, timestamp)
        freq_values = list(frequencies.values())

        if len(freq_values) < 2:
            return 0.0

        freq_std = float(np.std(freq_values))

        self._logger.debug(
            f"[频率标准差] pumps={pump_ids}, "
            f"frequencies={freq_values}, std={freq_std:.2f}Hz"
        )

        return freq_std

    def get_frequency_history(
        self, pump_id: int, start_time: datetime, end_time: datetime
    ) -> List[Dict[str, Any]]:
        """
        获取泵的频率历史数据（v3.14修复：使用metric_key查询）

        Args:
            pump_id: 泵ID
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            List[Dict]: [{"ts": datetime, "freq": float}, ...]
        """
        try:
            from app.adapters.db.pool import get_connection

            with get_connection() as conn:
                with conn.cursor() as cursor:
                    # ✅ v3.14修复：使用metric_key='pump_frequency'查询频率
                    sql = """
                        SELECT fm.ts_raw AS ts, fm.value AS freq
                        FROM fact_measurements fm
                        WHERE fm.device_id = %s
                          AND fm.metric_id = (
                              SELECT id FROM dim_metric_config
                              WHERE metric_key = 'pump_frequency'
                          )
                          AND fm.ts_raw BETWEEN %s AND %s
                        ORDER BY fm.ts_raw
                    """
                    cursor.execute(sql, (pump_id, start_time, end_time))
                    results = [
                        {"ts": row[0], "freq": float(row[1])}
                        for row in cursor.fetchall()
                    ]

                    self._logger.debug(
                        f"[频率历史] pump={pump_id}, "
                        f"range=[{start_time}, {end_time}], "
                        f"records={len(results)}"
                    )
                    return results

        except Exception as e:
            self._logger.error(f"[频率历史] 查询失败: {e}")
            return []

    def validate_frequencies(
        self, pump_ids: List[int], frequencies: Dict[int, float]
    ) -> Dict[str, Any]:
        """
        验证频率数据的有效性

        Args:
            pump_ids: 泵ID列表
            frequencies: 频率字典

        Returns:
            Dict: {
                'is_valid': bool,
                'missing_pumps': List[int],
                'out_of_range_pumps': List[int],
                'warnings': List[str]
            }
        """
        missing_pumps = [pid for pid in pump_ids if pid not in frequencies]
        out_of_range_pumps = [
            pid
            for pid, freq in frequencies.items()
            if not (self.min_freq <= freq <= self.max_freq)
        ]

        warnings = []
        if missing_pumps:
            warnings.append(f"缺少频率数据的泵: {missing_pumps}")
        if out_of_range_pumps:
            warnings.append(f"频率超出范围的泵: {out_of_range_pumps}")

        is_valid = len(missing_pumps) == 0 and len(out_of_range_pumps) == 0

        return {
            "is_valid": is_valid,
            "missing_pumps": missing_pumps,
            "out_of_range_pumps": out_of_range_pumps,
            "warnings": warnings,
        }

    def get_avg_frequency(
        self,
        pump_id: int,
        start_time: datetime,
        end_time: datetime,
        min_freq_threshold: Optional[float] = None,
    ) -> Optional[float]:
        """
        获取泵在指定时间段的平均运行频率

        Args:
            pump_id: 泵ID
            start_time: 开始时间
            end_time: 结束时间
            min_freq_threshold: 最小频率阈值（过滤停机状态）

        Returns:
            Optional[float]: 平均频率，无数据时返回None
        """
        history = self.get_frequency_history(pump_id, start_time, end_time)

        if not history:
            return None

        # 过滤低于阈值的数据（可能是停机状态）
        threshold = min_freq_threshold or self.min_freq
        valid_freqs = [h["freq"] for h in history if h["freq"] >= threshold]

        if not valid_freqs:
            return None

        avg_freq = float(np.mean(valid_freqs))
        self._logger.debug(
            f"[平均频率] pump={pump_id}, avg={avg_freq:.2f}Hz, "
            f"samples={len(valid_freqs)}"
        )
        return avg_freq

    def needs_frequency_normalization(
        self, pump_ids: List[int], threshold: float = 2.0
    ) -> bool:
        """
        判断是否需要频率归一化

        Args:
            pump_ids: 泵ID列表
            threshold: 频率标准差阈值 (Hz)

        Returns:
            bool: True表示需要归一化
        """
        try:
            freq_std = self.calculate_freq_std(pump_ids)
            needs_norm = freq_std > threshold

            self._logger.info(
                f"[归一化判断] pumps={pump_ids}, "
                f"freq_std={freq_std:.2f}Hz, threshold={threshold}Hz, "
                f"needs_normalization={needs_norm}"
            )
            return needs_norm

        except FrequencyQueryError as e:
            self._logger.warning(f"[归一化判断] 无法判断: {e}")
            # 保守策略：无法获取频率时假设需要归一化
            return True

