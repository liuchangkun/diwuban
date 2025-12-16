"""
数据过滤器（DataFilter）

职责：
- 过滤无效数据，确保计算输入的质量
- 过滤 NaN、Inf、负值、异常值
- 注意：pump_inlet_pressure 是静压计算，与泵运行状态无关，不过滤 running 状态
"""

from __future__ import annotations

from typing import Optional
import pandas as pd
import numpy as np
import logging


class DataFilter:
    """
    数据过滤器

    职责：
    - 过滤无效数据，确保计算输入的质量
    - 不过滤运行状态（静压计算与运行状态无关）
    - 不使用硬编码阈值
    """

    def __init__(
        self,
        max_liquid_level: Optional[float] = None,
        trace_id: Optional[str] = None
    ):
        """
        初始化数据过滤器

        Args:
            max_liquid_level: 液位上限（m），如果为None则从数据库加载
            trace_id: 追踪ID（用于日志关联）
        """
        self.logger = logging.getLogger(__name__)
        self.trace_id = trace_id

        # 异常值阈值（必须从数据库加载，不允许硬编码默认值）
        if max_liquid_level is None:
            # 从数据库加载默认参数
            params = self._load_default_parameters()
            self.max_liquid_level = params.get('max_liquid_level')

            # 验证必需参数
            if self.max_liquid_level is None:
                self.logger.error(
                    "[DataFilter] 缺少必需参数 'max_liquid_level'",
                    extra={'extra_data': {
                        '追踪ID': self.trace_id,
                        '错误': '必须在 calculation_parameters 表中配置该参数',
                        '指标键': 'pump_inlet_pressure',
                        '方法ID': 'pump_inlet_pressure_method_b',
                        'param_name': 'max_liquid_level'
                    }}
                )
                raise ValueError(
                    "缺少必需参数 'max_liquid_level'. "
                    "请在 calculation_parameters 表中添加该参数: "
                    "metric_key='pump_inlet_pressure', method_id='pump_inlet_pressure_method_b', "
                    "param_name='max_liquid_level'"
                )
        else:
            self.max_liquid_level = max_liquid_level

    def _load_default_parameters(self) -> dict:
        """
        从数据库加载默认参数（全局参数，station_id=NULL, device_id=NULL）

        Returns:
            参数字典
        """
        from app.adapters.db.pool import get_connection

        params = {}

        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT param_name, param_value
                    FROM calculation_parameters
                    WHERE metric_key = 'pump_inlet_pressure'
                        AND method_id = 'pump_inlet_pressure_method_b'
                        AND param_name = 'max_liquid_level'
                        AND station_id IS NULL
                        AND device_id IS NULL
                """)

                for row in cursor.fetchall():
                    params[row[0]] = float(row[1])

                cursor.close()
        except Exception as e:
            self.logger.error(
                f"[DataFilter] 从数据库加载参数失败: {e}",
                extra={'extra_data': {
                    '追踪ID': self.trace_id,
                    '错误': '数据库连接或查询失败',
                    '异常': str(e)
                }}
            )
            # 不再使用默认值，而是抛出异常
            raise ValueError(
                f"从数据库加载参数失败: {e}. "
                "请检查数据库连接和 calculation_parameters 表配置"
            )

        return params

    def filter_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        过滤无效数据

        Args:
            data: 原始数据（包含 pool_liquid_level）

        Returns:
            过滤后的数据

        注意：
        - 不过滤 running 状态（静压计算与泵运行状态无关）
        - 不过滤 pump_flow_rate（与静压计算无关）
        """
        if data.empty:
            self.logger.warning(
                "[数据过滤] 输入数据为空",
                extra={'extra_data': {'追踪ID': self.trace_id}}
            )
            return data

        original_count = len(data)

        self.logger.info(
            "[数据过滤] 开始过滤数据",
            extra={'extra_data': {
                '追踪ID': self.trace_id,
                '原始行数': original_count
            }}
        )

        # 1. NaN/Inf 过滤（只过滤计算依赖的字段）
        before_nan = len(data)
        data = data.dropna(subset=['pool_liquid_level'])
        data = data[~data['pool_liquid_level'].isin([np.inf, -np.inf])]
        nan_count = before_nan - len(data)

        # 2. 负值过滤（液位不能为负）
        before_negative = len(data)
        data = data[data['pool_liquid_level'] >= 0]
        negative_count = before_negative - len(data)

        # 3. 异常值过滤（液位上限）
        before_outlier = len(data)
        data = data[data['pool_liquid_level'] <= self.max_liquid_level]
        outlier_count = before_outlier - len(data)

        final_count = len(data)

        self.logger.info(
            "[数据过滤] 过滤完成",
            extra={'extra_data': {
                '追踪ID': self.trace_id,
                '原始行数': original_count,
                '移除NaN数量': nan_count,
                '移除负值数量': negative_count,
                '移除异常值数量': outlier_count,
                '最终行数': final_count,
                '过滤比例': f"{(original_count - final_count) / original_count * 100:.2f}%" if original_count > 0 else "0%"
            }}
        )

        return data

