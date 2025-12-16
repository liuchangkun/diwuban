"""频率数据提供器 (app.services.characteristic_curves.pump_group.frequency_data_provider)

变频泵频率数据提供器，用于获取泵的运行频率。

核心功能：
- 获取最新频率（get_latest_frequencies）
- 计算频率标准差（calculate_freq_std）
- 获取频率历史（get_frequency_history）

版本: v1.0
创建日期: 2025-12-14
参考文档: 07_泵组处理层.md 2.6节
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np

from app.adapters.db import get_connection
from app.services.characteristic_curves.shared.exceptions import FrequencyQueryError


logger = logging.getLogger(__name__)


class FrequencyDataProvider:
    """变频泵频率数据提供器

    职责：
    1. 从数据库查询历史频率数据（用于离线分析）
    2. 验证频率数据的有效性
    3. 计算频率统计指标
    """

    def __init__(self):
        """初始化"""
        self._logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}")
        self._freq_config = self._load_frequency_config()

    def _load_frequency_config(self) -> Dict:
        """从配置加载频率参数"""
        try:
            from app.core.config import get_config
            config = get_config()
            curve_fitting = config.get('curve_fitting', {})
            return curve_fitting.get('frequency_normalization', {
                'reference_freq': 50.0,
                'min_freq': 25.0,
                'max_freq': 60.0,
                'default_freq': 50.0
            })
        except Exception:
            # 使用默认配置
            return {
                'reference_freq': 50.0,
                'min_freq': 25.0,
                'max_freq': 60.0,
                'default_freq': 50.0
            }

    def get_latest_frequencies(
        self,
        pump_ids: List[int],
        timestamp: Optional[datetime] = None
    ) -> Dict[int, float]:
        """获取各泵的最新运行频率

        Args:
            pump_ids: 泵ID列表
            timestamp: 时间点（None表示最新）

        Returns:
            Dict[int, float]: 泵ID → 频率 映射

        Raises:
            FrequencyQueryError: 当无法获取某泵频率时抛出
        """
        if not pump_ids:
            return {}

        frequencies = {}

        try:
            with get_connection() as conn:
                with conn.cursor() as cursor:
                    for pump_id in pump_ids:
                        # 使用metric_key='pump_frequency'查询频率
                        # 注意: 只查询有效的非零频率值，避免返回0Hz
                        if timestamp:
                            sql = """
                                SELECT fm.value AS freq
                                FROM fact_measurements fm
                                WHERE fm.device_id = %s
                                  AND fm.metric_id = (
                                      SELECT id FROM dim_metric_config
                                      WHERE metric_key = 'pump_frequency'
                                  )
                                  AND fm.ts_bucket <= %s
                                  AND fm.value > 0
                                ORDER BY fm.ts_bucket DESC LIMIT 1
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
                                  AND fm.value > 0
                                ORDER BY fm.ts_bucket DESC LIMIT 1
                            """
                            cursor.execute(sql, (pump_id,))

                        row = cursor.fetchone()

                        # 查询失败直接抛异常，不使用默认值
                        if row is None or row[0] is None:
                            error = FrequencyQueryError(
                                message=f"无法获取泵{pump_id}的运行频率",
                                pump_id=pump_id,
                                timestamp=str(
                                    timestamp) if timestamp else "latest"
                            )
                            self._logger.error(error.to_log_format())
                            raise error

                        freq = float(row[0])

                        # 验证频率范围
                        min_f = self._freq_config.get('min_freq', 25.0)
                        max_f = self._freq_config.get('max_freq', 60.0)

                        if not (min_f <= freq <= max_f):
                            error = FrequencyQueryError(
                                message=f"泵{pump_id}频率{freq}Hz超出有效范围[{min_f},{max_f}]",
                                pump_id=pump_id,
                                timestamp=str(
                                    timestamp) if timestamp else "latest"
                            )
                            self._logger.error(error.to_log_format())
                            raise error

                        frequencies[pump_id] = freq

            self._logger.info(
                f"[频率] 成功获取 {len(frequencies)} 台泵的频率",
                extra={"extra_data": {"frequencies": frequencies}}
            )
            return frequencies

        except FrequencyQueryError:
            raise
        except Exception as e:
            self._logger.error(f"[频率] 查询失败: {e}", exc_info=True)
            raise

    def calculate_freq_std(
        self,
        pump_ids: List[int],
        timestamp: Optional[datetime] = None
    ) -> float:
        """计算泵组频率标准差

        用于判断是否需要执行频率归一化。

        Args:
            pump_ids: 泵ID列表
            timestamp: 时间点（None表示最新）

        Returns:
            float: 频率标准差（Hz）

        Raises:
            FrequencyQueryError: 当无法获取频率时抛出
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
        self,
        pump_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict]:
        """获取泵的频率历史数据

        Args:
            pump_id: 泵ID
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            List[Dict]: [{"ts": datetime, "freq": float}, ...]
        """
        try:
            with get_connection() as conn:
                with conn.cursor() as cursor:
                    sql = """
                        SELECT fm.ts_bucket AS ts, fm.value AS freq
                        FROM fact_measurements fm
                        WHERE fm.device_id = %s
                          AND fm.metric_id = (
                              SELECT id FROM dim_metric_config
                              WHERE metric_key = 'pump_frequency'
                          )
                          AND fm.ts_bucket BETWEEN %s AND %s
                        ORDER BY fm.ts_bucket
                    """
                    cursor.execute(sql, (pump_id, start_time, end_time))
                    return [{"ts": row[0], "freq": float(row[1])} for row in cursor.fetchall()]
        except Exception as e:
            self._logger.error(f"[频率历史] 查询失败: {e}", exc_info=True)
            return []

    def get_frequency_diff_ratio(
        self,
        pump_ids: List[int],
        timestamp: Optional[datetime] = None
    ) -> float:
        """计算泵组频率差异比例

        Args:
            pump_ids: 泵ID列表
            timestamp: 时间点

        Returns:
            float: 频率差异比例 (max-min)/max
        """
        if len(pump_ids) < 2:
            return 0.0

        frequencies = self.get_latest_frequencies(pump_ids, timestamp)
        freq_values = list(frequencies.values())

        if not freq_values or max(freq_values) == 0:
            return 0.0

        return (max(freq_values) - min(freq_values)) / max(freq_values)

    # 别名方法，保持接口兼容
    def get_frequency_data(
        self,
        pump_ids: List[int],
        timestamp: Optional[datetime] = None
    ) -> Dict[int, float]:
        """get_latest_frequencies 的别名方法"""
        return self.get_latest_frequencies(pump_ids, timestamp)
