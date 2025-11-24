"""
结果验证器（Validator）

职责：
- 验证计算结果的合理性
- 范围检查
- 交叉验证（如果有多个方法）
- 质量标记
"""

from __future__ import annotations

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
import logging


class Validator:
    """
    结果验证器

    职责：
    - 验证计算结果的合理性
    - 范围检查（0 <= T <= max_torque）
    - 质量标记
    """

    def __init__(self, params: Dict[str, Any], trace_id: Optional[str] = None):
        """
        初始化结果验证器

        Args:
            params: 参数字典（包含 max_torque 等）
            trace_id: 追踪ID（用于日志关联）
        """
        self.logger = logging.getLogger(__name__)
        self.trace_id = trace_id
        self.params = params

    def validate(self, data: pd.DataFrame, method_id: str) -> pd.DataFrame:
        """
        验证计算结果

        Args:
            data: 计算结果数据（包含 pump_torque 列）
            method_id: 使用的计算方法

        Returns:
            验证后的数据（包含 quality_code 列）
        """
        if data.empty:
            self.logger.warning(
                "[结果验证] 输入数据为空",
                extra={'extra_data': {'trace_id': self.trace_id}}
            )
            return data

        self.logger.info(
            "[结果验证] 开始验证",
            extra={'extra_data': {
                'trace_id': self.trace_id,
                'method_id': method_id,
                'data_rows': len(data)
            }}
        )

        result = data.copy()
        max_torque = self.params.get('max_torque')

        # 验证必需参数
        if max_torque is None:
            self.logger.error(
                "[参数错误] 缺少必需参数 'max_torque'",
                extra={'extra_data': {
                    'trace_id': self.trace_id,
                    'missing_param': 'max_torque',
                    'fix': '请在 calculation_parameters 表中添加该参数'
                }}
            )
            raise ValueError("缺少必需参数 'max_torque'")

        # 1. 范围检查
        result['quality_code'] = 0  # 默认高质量

        # 标记范围异常
        result.loc[
            (result['pump_torque'] < 0) | (result['pump_torque'] > max_torque),
            'quality_code'
        ] = 2  # 范围异常

        # 标记 NaN/Inf
        result.loc[
            result['pump_torque'].isna() | result['pump_torque'].isin([np.inf, -np.inf]),
            'quality_code'
        ] = 2  # 无效值

        # 2. 统计验证结果
        valid_count = len(result[result['quality_code'] == 0])
        invalid_count = len(result[result['quality_code'] == 2])

        self.logger.info(
            "[结果验证] 验证完成",
            extra={'extra_data': {
                'trace_id': self.trace_id,
                'method_id': method_id,
                'total_rows': len(result),
                'valid_rows': valid_count,
                'invalid_rows': invalid_count,
                'valid_ratio': f"{valid_count / len(result) * 100:.2f}%" if len(result) > 0 else "0%",
                'avg_torque': round(result[result['quality_code'] == 0]['pump_torque'].mean(), 2) if valid_count > 0 else 0,
                'min_torque': round(result[result['quality_code'] == 0]['pump_torque'].min(), 2) if valid_count > 0 else 0,
                'max_torque': round(result[result['quality_code'] == 0]['pump_torque'].max(), 2) if valid_count > 0 else 0
            }}
        )

        # 3. 过滤无效数据
        valid_data = result[result['quality_code'] == 0].copy()

        return valid_data

