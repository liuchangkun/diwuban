"""
pump_head 结果验证模块
"""

import pandas as pd
import numpy as np
import logging
from typing import Tuple


class Validator:
    """结果验证器"""

    def __init__(self, params: dict = None):
        """
        初始化结果验证器

        Args:
            params: 验证参数配置
        """
        self.logger = logging.getLogger(__name__)

        # 从参数中读取验证范围
        params = params or {}
        self.min_pump_outlet_pressure = params.get('min_pump_outlet_pressure')
        self.max_pump_outlet_pressure = params.get('max_pump_outlet_pressure')
        self.min_pump_head = params.get('min_pump_head')
        self.max_pump_head = params.get('max_pump_head')

        # 验证必需参数
        missing_params = []
        if self.min_pump_outlet_pressure is None:
            missing_params.append('min_pump_outlet_pressure')
        if self.max_pump_outlet_pressure is None:
            missing_params.append('max_pump_outlet_pressure')
        if self.min_pump_head is None:
            missing_params.append('min_pump_head')
        if self.max_pump_head is None:
            missing_params.append('max_pump_head')

        if missing_params:
            self.logger.error(
                f"[验证器] pump_head validator缺少必需参数",
                extra={'extra_data': {
                    '缺失参数': missing_params,
                    '当前参数': params,
                    '错误': '必须在calculation_parameters表中配置这些参数'
                }}
            )
            raise ValueError(
                f"pump_head validator缺少必需参数: {', '.join(missing_params)}. "
                f"必须在calculation_parameters表中配置: metric_key='pump_head'"
            )

    def validate(
        self,
        pump_outlet_pressure_result: pd.DataFrame,
        pump_head_result: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame, int, int]:
        """
        验证计算结果

        Args:
            pump_outlet_pressure_result: pump_outlet_pressure计算结果
            pump_head_result: pump_head计算结果

        Returns:
            Tuple[pd.DataFrame, pd.DataFrame, int, int]: 
                (验证后的pump_outlet_pressure, 验证后的pump_head, 有效pump_outlet_pressure数量, 有效pump_head数量)
        """
        self.logger.info(
            "[结果验证] 开始验证",
            extra={'extra_data': {
                'pump_outlet_pressure_rows': len(pump_outlet_pressure_result),
                'pump_head_rows': len(pump_head_result)
            }}
        )

        # 验证 pump_outlet_pressure
        validated_outlet_pressure = self._validate_pump_outlet_pressure(pump_outlet_pressure_result)
        valid_outlet_count = len(validated_outlet_pressure)

        # 验证 pump_head
        validated_head = self._validate_pump_head(pump_head_result)
        valid_head_count = len(validated_head)

        self.logger.info(
            "[结果验证] 验证完成",
            extra={'extra_data': {
                'valid_pump_outlet_pressure': valid_outlet_count,
                'valid_pump_head': valid_head_count
            }}
        )

        return validated_outlet_pressure, validated_head, valid_outlet_count, valid_head_count

    def _validate_pump_outlet_pressure(self, data: pd.DataFrame) -> pd.DataFrame:
        """验证 pump_outlet_pressure"""
        if data.empty:
            return data

        initial_count = len(data)

        # 过滤NaN和Inf
        data = data.replace([np.inf, -np.inf], np.nan)
        data = data.dropna(subset=['pump_outlet_pressure'])

        # 范围验证（使用配置参数）
        data = data[
            (data['pump_outlet_pressure'] >= self.min_pump_outlet_pressure) &
            (data['pump_outlet_pressure'] <= self.max_pump_outlet_pressure)
        ].copy()

        # 添加质量码
        data['quality_code'] = 0

        final_count = len(data)

        self.logger.info(
            "[结果验证] pump_outlet_pressure验证完成",
            extra={'extra_data': {
                'initial': initial_count,
                'valid': final_count,
                'removed': initial_count - final_count
            }}
        )

        return data

    def _validate_pump_head(self, data: pd.DataFrame) -> pd.DataFrame:
        """验证 pump_head"""
        if data.empty:
            return data

        initial_count = len(data)

        # 过滤NaN和Inf
        data = data.replace([np.inf, -np.inf], np.nan)
        data = data.dropna(subset=['pump_head'])

        # 范围验证（使用配置参数）
        data = data[
            (data['pump_head'] >= self.min_pump_head) &
            (data['pump_head'] <= self.max_pump_head)
        ].copy()

        # 添加质量码
        data['quality_code'] = 0

        final_count = len(data)

        self.logger.info(
            "[结果验证] pump_head验证完成",
            extra={'extra_data': {
                'initial': initial_count,
                'valid': final_count,
                'removed': initial_count - final_count
            }}
        )

        return data

