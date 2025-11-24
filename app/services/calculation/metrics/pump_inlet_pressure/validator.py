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
        self.min_pressure = params.get('min_pressure')
        self.max_pressure = params.get('max_pressure')
        self.v_max_warning = params.get('v_max_warning')

        # 验证必需参数，缺失时记录错误并抛出异常
        missing_params = []
        if self.min_pressure is None:
            missing_params.append('min_pressure')
        if self.max_pressure is None:
            missing_params.append('max_pressure')

        if missing_params:
            self.logger.error(
                f"[验证器] pump_inlet_pressure validator缺少必需参数",
                extra={'extra_data': {
                    '缺失参数': missing_params,
                    '当前参数': params,
                    '错误': '必须在calculation_parameters表中配置这些参数'
                }}
            )
            raise ValueError(
                f"pump_inlet_pressure validator缺少必需参数: {', '.join(missing_params)}. "
                f"必须在calculation_parameters表中配置: metric_key='pump_inlet_pressure', method_id='pump_inlet_pressure_method_b'"
            )

        # v_max_warning是可选参数，如果没有则不检查流速
        if self.v_max_warning is None:
            self.logger.info("[验证器] v_max_warning参数未设置，将跳过流速检查")

    def validate(
        self,
        results: pd.DataFrame,
        data: pd.DataFrame = None
    ) -> Dict[str, Any]:
        """
        验证计算结果

        Args:
            results: 计算结果（包含 pump_inlet_pressure 列）
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
        if 'pump_inlet_pressure' not in results.columns:
            raise ValueError("结果中缺少 pump_inlet_pressure 列")

        pressure_values = results['pump_inlet_pressure']

        self.logger.info(
            "[结果验证] 开始验证",
            extra={'extra_data': {
                '结果数量': len(pressure_values),
                '验证规则': ['范围', '非负', 'NaN/Inf', '物理约束']
            }}
        )

        # 初始化有效性标记
        is_valid = pd.Series([True] * len(pressure_values), index=pressure_values.index)

        # 1. NaN/Inf 验证（优先检查）
        nan_inf_invalid = pressure_values.isna() | pressure_values.isin([np.inf, -np.inf])
        is_valid &= ~nan_inf_invalid

        # 2. 非负验证
        negative_invalid = (pressure_values < 0)
        is_valid &= ~negative_invalid

        # 3. 范围验证
        range_invalid = (pressure_values < self.min_pressure) | (pressure_values > self.max_pressure)
        is_valid &= ~range_invalid

        # 4. 物理约束验证（压力应大于等于大气压）
        # P_in 应该 >= 0.00 MPa（大气压以上）
        physical_invalid = (pressure_values < 0.00)  # 低于0.00 MPa认为异常
        is_valid &= ~physical_invalid

        # 统计无效值
        invalid_count = (~is_valid).sum()
        valid_count = is_valid.sum()
        total_count = len(pressure_values)
        valid_ratio = valid_count / total_count if total_count > 0 else 0.0

        # 记录无效值（最多记录前10个）
        if invalid_count > 0:
            print(f"\n{'='*100}")
            print(f"[结果验证] 发现 {invalid_count} 个无效值，显示前10个：")
            print(f"{'='*100}")

            invalid_indices = pressure_values[~is_valid].index[:10]
            for i, idx in enumerate(invalid_indices, 1):
                # 获取该行的所有输入数据
                row_data = results.loc[idx]
                pressure_val = pressure_values.loc[idx]

                print(f"\n  无效值 #{i}:")
                print(f"    时间戳: {row_data.get('ts_bucket', 'N/A')}")
                print(f"    设备ID: {row_data.get('device_id', 0)}")
                print(f"    计算结果: {float(pressure_val) if not pd.isna(pressure_val) else 'NaN'}")
                print(f"    输入-pool_liquid_level: {float(row_data.get('pool_liquid_level', np.nan)) if not pd.isna(row_data.get('pool_liquid_level', np.nan)) else 'NaN'}")
                print(f"    输入-pump_flow_rate: {float(row_data.get('pump_flow_rate', np.nan)) if not pd.isna(row_data.get('pump_flow_rate', np.nan)) else 'NaN'}")
                print(f"    输入-running: {row_data.get('running', 0)}")
                print(f"    失败原因: {self._get_failure_reason(pressure_val)}")
                print(f"    是否NaN: {pd.isna(pressure_val)}")
                if not pd.isna(pressure_val):
                    print(f"    是否负值: {pressure_val < 0}")
                    print(f"    是否超范围: {(pressure_val < self.min_pressure) or (pressure_val > self.max_pressure)}")
                    print(f"    是否低于物理约束(0.00MPa): {pressure_val < 0.00}")

                self.logger.warning(
                    "[结果验证] 发现无效值",
                    extra={'extra_data': {
                        '索引': int(idx) if isinstance(idx, (int, np.integer)) else str(idx),
                        '时间戳': str(row_data.get('ts_bucket', 'N/A')),
                        '设备ID': int(row_data.get('device_id', 0)),
                        '计算结果': float(pressure_val) if not pd.isna(pressure_val) else None,
                        '输入-pool_liquid_level': float(row_data.get('pool_liquid_level', np.nan)) if not pd.isna(row_data.get('pool_liquid_level', np.nan)) else None,
                        '输入-pump_flow_rate': float(row_data.get('pump_flow_rate', np.nan)) if not pd.isna(row_data.get('pump_flow_rate', np.nan)) else None,
                        '输入-running': int(row_data.get('running', 0)),
                        '失败原因': self._get_failure_reason(pressure_val)
                    }}
                )

            print(f"{'='*100}\n")

        # 创建有效结果（无效值设为NaN）
        valid_results = results.copy()
        valid_results.loc[~is_valid, 'pump_inlet_pressure'] = np.nan

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
            'quality_code': quality_code
        }

    def _get_failure_reason(self, value: float) -> str:
        """
        获取验证失败原因

        Args:
            value: 压力值

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
            if value < self.min_pressure:
                reasons.append(f"低于最小值({self.min_pressure})")
            if value > self.max_pressure:
                reasons.append(f"超过最大值({self.max_pressure})")
            if value < 0:
                reasons.append("负值")
            if value < 0.00:
                reasons.append("低于物理下限(0.00 MPa)")

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

