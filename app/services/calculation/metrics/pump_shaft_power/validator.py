"""
结果验证器（Validator）

职责：
- 验证计算结果的有效性
- 范围检查
- 效率检查（P_shaft > P_active）
- 添加 quality_code 列
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
    - 范围检查（0 <= P_shaft <= max_shaft_power）
    - 效率检查（P_shaft > P_active）
    - NaN/Inf 检查
    - 添加 quality_code 列（0=有效, 2=范围异常, 3=效率违反）
    - 过滤无效数据
    """
    
    def __init__(self, params: Dict[str, Any], trace_id: Optional[str] = None):
        """
        初始化结果验证器
        
        Args:
            params: 参数字典（包含 max_shaft_power）
            trace_id: 追踪ID（用于日志关联）
        """
        self.params = params
        self.trace_id = trace_id
        self.logger = logging.getLogger(__name__)
    
    def validate(self, data: pd.DataFrame, method_id: str) -> pd.DataFrame:
        """
        验证计算结果
        
        Args:
            data: 计算结果
            method_id: 方法ID
        
        Returns:
            验证后的数据（仅包含有效数据，quality_code=0）
        """
        if data.empty:
            return data
        
        self.logger.info(
            "[结果验证] 开始验证",
            extra={'extra_data': {
                '追踪ID': self.trace_id,
                '方法ID': method_id,
                'row_count': len(data)
            }}
        )
        
        result = data.copy()

        # 获取验证参数
        max_shaft_power = self.params.get('max_shaft_power')
        if max_shaft_power is None:
            self.logger.error(
                "[参数错误] 缺少必需参数 'max_shaft_power'",
                extra={'extra_data': {
                    '追踪ID': self.trace_id,
                    'missing_param': 'max_shaft_power',
                    'fix': '请在 calculation_parameters 表中添加该参数'
                }}
            )
            raise ValueError("缺少必需参数 'max_shaft_power'")

        # 初始化 quality_code（默认为0=高质量）
        result['quality_code'] = 0
        
        # 1. 范围检查
        result.loc[
            (result['pump_shaft_power'] < 0) | 
            (result['pump_shaft_power'] > max_shaft_power),
            'quality_code'
        ] = 2  # 范围异常
        
        # 2. 效率检查（关键）：P_shaft 必须 < P_active（能量守恒）
        result.loc[
            result['pump_shaft_power'] >= result['pump_active_power'],
            'quality_code'
        ] = 3  # 效率违反
        
        # 3. NaN/Inf 检查
        result.loc[
            result['pump_shaft_power'].isna() | 
            result['pump_shaft_power'].isin([np.inf, -np.inf]),
            'quality_code'
        ] = 2  # 数据异常
        
        # 统计质量分布
        quality_dist = result['quality_code'].value_counts().to_dict()
        
        # 过滤无效数据（仅保留 quality_code=0）
        valid_data = result[result['quality_code'] == 0].copy()
        
        invalid_count = len(result) - len(valid_data)
        
        self.logger.info(
            "[结果验证] 验证完成",
            extra={'extra_data': {
                '追踪ID': self.trace_id,
                '方法ID': method_id,
                'total_count': len(result),
                'valid_count': len(valid_data),
                'invalid_count': invalid_count,
                'quality_distribution': quality_dist
            }}
        )
        
        return valid_data

