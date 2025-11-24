"""
结果验证器（Validator）

职责：
- 验证计算结果的合理性
- 检查数据质量
- 返回验证结果和质量代码
"""

from __future__ import annotations

from typing import Dict, Any
import pandas as pd
import numpy as np
import logging


class Validator:
    """结果验证器"""

    def __init__(self, params: Dict[str, Any] = None):
        """
        初始化结果验证器

        Args:
            params: 验证参数配置
        """
        self.logger = logging.getLogger(__name__)

        # 验证阈值（必须从参数传入，禁止使用默认值）
        params = params or {}
        self.min_speed = params.get('min_speed')
        self.max_speed = params.get('max_speed')

        # 验证必需参数，缺失时记录错误并抛出异常
        missing_params = []
        if self.min_speed is None:
            missing_params.append('min_speed')
        if self.max_speed is None:
            missing_params.append('max_speed')

        if missing_params:
            self.logger.error(
                f"[验证器] pump_speed validator缺少必需参数",
                extra={'extra_data': {
                    '缺失参数': missing_params,
                    '当前参数': params,
                    '错误': '必须在calculation_parameters表中配置这些参数'
                }}
            )
            raise ValueError(
                f"pump_speed validator缺少必需参数: {', '.join(missing_params)}. "
                f"必须在calculation_parameters表中配置: metric_key='pump_speed', method_id='validation'"
            )

    def validate(
        self,
        results: pd.DataFrame,
        data: pd.DataFrame = None
    ) -> Dict[str, Any]:
        """
        验证计算结果

        Args:
            results: 计算结果（包含 pump_speed 列）
            data: 原始数据（用于物理约束验证，可选）

        Returns:
            验证结果字典，包含：
            - valid_results: 有效结果（DataFrame，无效值设为NaN）
            - is_valid: 布尔Series，标记每个值是否有效
            - valid_count: 有效数量
            - invalid_count: 无效数量
            - valid_ratio: 有效比例
            - quality_code: 质量代码（0=优秀, 1=良好, 2=可用, 3=差）
        """
        if 'pump_speed' not in results.columns:
            raise ValueError("结果中缺少 pump_speed 列")

        speed_values = results['pump_speed']

        self.logger.info(
            "[结果验证] 开始验证",
            extra={'extra_data': {
                '结果数量': len(speed_values),
                '验证规则': ['范围', '非负', 'NaN/Inf']
            }}
        )

        # 初始化有效性标记
        is_valid = pd.Series([True] * len(speed_values), index=speed_values.index)

        # 1. NaN/Inf 验证（优先检查）
        nan_inf_invalid = speed_values.isna() | speed_values.isin([np.inf, -np.inf])
        is_valid &= ~nan_inf_invalid

        # 2. 非负验证
        negative_invalid = speed_values < 0
        is_valid &= ~negative_invalid

        # 3. 范围验证
        range_invalid = (speed_values < self.min_speed) | (speed_values > self.max_speed)
        is_valid &= ~range_invalid

        # 统计
        valid_count = is_valid.sum()
        invalid_count = len(is_valid) - valid_count
        valid_ratio = valid_count / len(is_valid) if len(is_valid) > 0 else 0.0

        # 质量代码
        if valid_ratio >= 0.95:
            quality_code = 0  # 优秀
        elif valid_ratio >= 0.90:
            quality_code = 1  # 良好
        elif valid_ratio >= 0.80:
            quality_code = 2  # 可用
        else:
            quality_code = 3  # 差

        # 创建有效结果（无效值设为NaN）
        valid_results = results.copy()
        valid_results.loc[~is_valid, 'pump_speed'] = np.nan

        self.logger.info(
            "[结果验证] 验证完成",
            extra={'extra_data': {
                '有效数量': int(valid_count),
                '无效数量': int(invalid_count),
                '有效比例': f"{valid_ratio * 100:.1f}%",
                '质量代码': quality_code,
                'NaN/Inf无效': int(nan_inf_invalid.sum()),
                '负值无效': int(negative_invalid.sum()),
                '范围无效': int(range_invalid.sum())
            }}
        )

        return {
            'valid_results': valid_results,
            'is_valid': is_valid,
            'valid_count': int(valid_count),
            'invalid_count': int(invalid_count),
            'valid_ratio': valid_ratio,
            'quality_code': quality_code
        }

