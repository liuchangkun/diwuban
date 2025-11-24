"""
结果验证器（Validator）

职责：
- 验证计算结果的合理性
- 标记数据质量
- 返回验证后的数据
"""

from __future__ import annotations

from typing import Dict, Any
import pandas as pd
import numpy as np
import logging


class Validator:
    """
    结果验证器
    
    职责：
    - 验证计算结果的合理性（范围、物理约束、异常值）
    - 标记数据质量
    """
    
    def __init__(self, params: Dict[str, Any] = None, trace_id: str = None):
        """
        初始化验证器
        
        Args:
            params: 验证参数
            trace_id: 追踪ID
        """
        self.logger = logging.getLogger(__name__)
        self.trace_id = trace_id
        self.params = params or {}
    
    def validate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        验证计算结果
        
        Args:
            data: 计算结果（包含main_pipeline_inlet_pressure列）
        
        Returns:
            验证后的数据（添加质量标记列）
        """
        if data.empty:
            self.logger.info(
                "[结果验证] 输入数据为空，跳过验证",
                extra={'extra_data': {'trace_id': self.trace_id}}
            )
            return data
        
        if 'main_pipeline_inlet_pressure' not in data.columns:
            self.logger.warning(
                "[结果验证] 缺少main_pipeline_inlet_pressure列，跳过验证",
                extra={'extra_data': {'trace_id': self.trace_id}}
            )
            return data
        
        self.logger.info(
            f"[结果验证] 开始验证: 数据量={len(data)}",
            extra={'extra_data': {'trace_id': self.trace_id}}
        )
        
        result = data.copy()

        # 1. 范围检查
        min_pressure = self.params.get('min_pressure')
        max_pressure = self.params.get('max_pressure')

        # 验证必需参数
        if min_pressure is None:
            self.logger.error(
                "[参数错误] 缺少必需参数 'min_pressure'",
                extra={'extra_data': {
                    'trace_id': self.trace_id,
                    'missing_param': 'min_pressure',
                    'fix': '请在 calculation_parameters 表中添加该参数'
                }}
            )
            raise ValueError("缺少必需参数 'min_pressure'")
        if max_pressure is None:
            self.logger.error(
                "[参数错误] 缺少必需参数 'max_pressure'",
                extra={'extra_data': {
                    'trace_id': self.trace_id,
                    'missing_param': 'max_pressure',
                    'fix': '请在 calculation_parameters 表中添加该参数'
                }}
            )
            raise ValueError("缺少必需参数 'max_pressure'")
        
        result['valid_range'] = (
            (result['main_pipeline_inlet_pressure'] >= min_pressure) &
            (result['main_pipeline_inlet_pressure'] <= max_pressure)
        )
        
        # 2. 物理约束检查（P_in ≈ P_atm + ρ×g×h/1e6）
        if 'pool_liquid_level' in result.columns:
            P_atm = self.params.get('P_atm')
            rho = self.params.get('rho')
            g = self.params.get('g')
            max_deviation = self.params.get('max_deviation')

            # 验证物理常数参数（这些是全局参数，应该总是存在）
            if P_atm is None or rho is None or g is None:
                self.logger.warning(
                    "[参数警告] 缺少物理常数参数，跳过物理约束检查",
                    extra={'extra_data': {
                        'trace_id': self.trace_id,
                        'P_atm': P_atm,
                        'rho': rho,
                        'g': g
                    }}
                )
                result['valid_physics'] = True
            elif max_deviation is None:
                self.logger.warning(
                    "[参数警告] 缺少 max_deviation 参数，跳过物理约束检查",
                    extra={'extra_data': {'trace_id': self.trace_id}}
                )
                result['valid_physics'] = True
            else:
                # 转换pool_liquid_level为float（避免Decimal类型问题）
                h = result['pool_liquid_level'].astype(float)
                expected_P = P_atm + rho * g * h / 1e6
                deviation = np.abs(result['main_pipeline_inlet_pressure'] - expected_P) / expected_P
                result['valid_physics'] = deviation <= max_deviation
        else:
            result['valid_physics'] = True
        
        # 3. 异常值检查（相邻时刻压力变化）
        max_change_rate = self.params.get('max_change_rate')
        if max_change_rate is None:
            self.logger.warning(
                "[参数警告] 缺少 max_change_rate 参数，跳过异常值检查",
                extra={'extra_data': {'trace_id': self.trace_id}}
            )
            result['valid_outlier'] = True
        else:
            diff = result['main_pipeline_inlet_pressure'].diff().abs()
            result['valid_outlier'] = (diff <= max_change_rate) | diff.isna()
        
        # 4. NaN/Inf检查
        result['valid_nan'] = ~(
            result['main_pipeline_inlet_pressure'].isna() |
            np.isinf(result['main_pipeline_inlet_pressure'])
        )
        
        # 5. 综合质量标记
        result['quality'] = 'valid'
        result.loc[~result['valid_range'], 'quality'] = 'out_of_range'
        result.loc[~result['valid_physics'], 'quality'] = 'physics_violation'
        result.loc[~result['valid_outlier'], 'quality'] = 'outlier'
        result.loc[~result['valid_nan'], 'quality'] = 'invalid'

        # 6. 添加quality_code列（0=有效，1=无效）
        result['quality_code'] = 0
        result.loc[result['quality'] != 'valid', 'quality_code'] = 1

        # 统计
        total = len(result)
        valid_count = (result['quality'] == 'valid').sum()
        invalid_count = total - valid_count

        self.logger.info(
            f"[结果验证] 验证完成: 总数={total}, 有效={valid_count}, 无效={invalid_count}",
            extra={'extra_data': {
                'trace_id': self.trace_id,
                'valid_ratio': f"{valid_count/total*100:.1f}%" if total > 0 else "0%"
            }}
        )

        return result

