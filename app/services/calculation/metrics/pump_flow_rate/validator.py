"""
结果验证器（Validator）

职责：
- 验证计算结果的合理性
- 检查数据质量
- 返回验证结果和质量代码
"""

from __future__ import annotations

from typing import Dict, Any, Tuple
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
        self.min_flow = params.get('min_flow')
        self.max_flow = params.get('max_flow')
        self.max_ratio = params.get('max_ratio')

        # 验证必需参数，缺失时记录错误并抛出异常
        missing_params = []
        if self.min_flow is None:
            missing_params.append('min_flow')
        if self.max_flow is None:
            missing_params.append('max_flow')
        if self.max_ratio is None:
            missing_params.append('max_ratio')

        if missing_params:
            self.logger.error(
                f"[验证器] pump_flow_rate validator缺少必需参数",
                extra={'extra_data': {
                    '缺失参数': missing_params,
                    '当前参数': params,
                    '错误': '必须在calculation_parameters表中配置这些参数'
                }}
            )
            raise ValueError(
                f"pump_flow_rate validator缺少必需参数: {', '.join(missing_params)}. "
                f"必须在calculation_parameters表中配置: metric_key='pump_flow_rate', method_id='data_filter'"
            )

    def validate(
        self,
        results: pd.DataFrame,
        data: pd.DataFrame = None
    ) -> Dict[str, Any]:
        """
        验证计算结果

        Args:
            results: 计算结果（包含 pump_flow_rate 列）
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
        if 'pump_flow_rate' not in results.columns:
            raise ValueError("结果中缺少 pump_flow_rate 列")

        flow_values = results['pump_flow_rate']

        self.logger.info(
            "[结果验证] 开始验证",
            extra={'extra_data': {
                '结果数量': len(flow_values),
                '验证规则': ['范围', '非负', 'NaN/Inf', '物理约束']
            }}
        )

        # 初始化有效性标记
        is_valid = pd.Series([True] * len(flow_values), index=flow_values.index)

        # 1. NaN/Inf 验证（优先检查）
        nan_inf_invalid = flow_values.isna() | flow_values.isin([np.inf, -np.inf])
        is_valid &= ~nan_inf_invalid

        # 2. 非负验证
        negative_invalid = (flow_values < 0)
        is_valid &= ~negative_invalid

        # 3. 范围验证
        range_invalid = (flow_values < self.min_flow) | (flow_values > self.max_flow)
        is_valid &= ~range_invalid

        # 4. 物理约束验证（单泵流量不应超过总管流量）
        if data is not None and 'main_pipeline_flow_rate' in data.columns:
            main_flow = data['main_pipeline_flow_rate'].astype(float)
            physical_invalid = (flow_values > main_flow * self.max_ratio)
            is_valid &= ~physical_invalid

        # 统计无效值
        invalid_count = (~is_valid).sum()
        valid_count = is_valid.sum()
        total_count = len(flow_values)
        valid_ratio = valid_count / total_count if total_count > 0 else 0.0

        # 记录无效值（最多记录前10个）
        if invalid_count > 0:
            invalid_indices = flow_values[~is_valid].index[:10]
            for idx in invalid_indices:
                self.logger.warning(
                    "[结果验证] 发现无效值",
                    extra={'extra_data': {
                        '索引': int(idx) if isinstance(idx, (int, np.integer)) else str(idx),
                        '值': float(flow_values.loc[idx]) if not pd.isna(flow_values.loc[idx]) else None,
                        '总管流量': float(data.loc[idx, 'main_pipeline_flow_rate']) if data is not None and 'main_pipeline_flow_rate' in data.columns else None,
                        '失败原因': self._get_failure_reason(flow_values.loc[idx], data.loc[idx] if data is not None else None)
                    }}
                )

        # 创建有效结果（无效值设为NaN）
        valid_results = results.copy()
        valid_results.loc[~is_valid, 'pump_flow_rate'] = np.nan

        # 计算质量代码
        quality_code = self._calculate_quality_code(valid_ratio)

        self.logger.info(
            "[结果验证] 验证完成",
            extra={'extra_data': {
                '原始数量': total_count,
                '有效数量': valid_count,
                '无效数量': invalid_count,
                '有效比例': f"{valid_ratio * 100:.2f}%",
                '质量代码': quality_code
            }}
        )

        return {
            'valid_results': valid_results,
            'is_valid': is_valid,
            'valid_count': valid_count,
            'invalid_count': invalid_count,
            'valid_ratio': valid_ratio,
            '质量代码': quality_code
        }

    def _get_failure_reason(self, value: float, row: pd.Series = None) -> str:
        """
        获取验证失败原因

        Args:
            value: 流量值
            row: 数据行（可选）

        Returns:
            失败原因字符串
        """
        reasons = []

        # 检查 NaN/Inf
        if pd.isna(value):
            reasons.append("NaN")
        elif value == np.inf:
            reasons.append("Inf")
        elif value == -np.inf:
            reasons.append("-Inf")

        # 检查范围
        if not pd.isna(value):
            if value < self.min_flow:
                reasons.append(f"低于最小值({self.min_flow})")
            if value > self.max_flow:
                reasons.append(f"超过最大值({self.max_flow})")
            if value < 0:
                reasons.append("负值")

        # 检查物理约束
        if row is not None and 'main_pipeline_flow_rate' in row:
            main_flow = float(row['main_pipeline_flow_rate'])
            if not pd.isna(value) and not pd.isna(main_flow):
                if value > main_flow * self.max_ratio:
                    reasons.append(f"超过总管流量{self.max_ratio}倍")

        return ", ".join(reasons) if reasons else "未知原因"

    def _calculate_quality_code(self, valid_ratio: float) -> int:
        """
        计算质量代码

        Args:
            valid_ratio: 有效比例（0.0-1.0）

        Returns:
            质量代码：
            - 0: 优秀（≥95%）
            - 1: 良好（≥80%）
            - 2: 可用（≥60%）
            - 3: 差（<60%）
        """
        if valid_ratio >= 0.95:
            return 0  # 优秀
        elif valid_ratio >= 0.80:
            return 1  # 良好
        elif valid_ratio >= 0.60:
            return 2  # 可用
        else:
            return 3  # 差

