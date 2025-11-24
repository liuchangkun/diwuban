"""
pump_hydraulic_power Validator模块

职责：验证计算结果的合理性
"""

import pandas as pd
import numpy as np
from typing import Dict, Any


class Validator:
    """验证器"""

    def __init__(self, params: Dict[str, Any], trace_id: str = ""):
        """
        初始化Validator

        Args:
            params: 参数字典
            trace_id: 追踪ID
        """
        self.params = params
        self.trace_id = trace_id

    def validate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        验证计算结果

        Args:
            data: 计算结果

        Returns:
            pd.DataFrame: 验证后的数据（添加quality列）
        """
        print(f"[{self.trace_id}] [Validator] 开始验证...")
        print(f"  - 输入数据行数: {len(data)}")

        if data.empty:
            print(f"  - ⚠️ 输入数据为空")
            return data

        # 获取验证参数
        min_power = self.params.get('min_power')
        max_power = self.params.get('max_power')

        # 验证必需参数
        if min_power is None:
            print(f"  - ❌ 缺少必需参数 'min_power'")
            raise ValueError(
                "缺少必需参数 'min_power'. "
                "请在 calculation_parameters 表中添加该参数"
            )
        if max_power is None:
            print(f"  - ❌ 缺少必需参数 'max_power'")
            raise ValueError(
                "缺少必需参数 'max_power'. "
                "请在 calculation_parameters 表中添加该参数"
            )

        print(f"  - 验证参数:")
        print(f"    - min_power: {min_power} kW")
        print(f"    - max_power: {max_power} kW")

        # 初始化quality列
        data['quality'] = 'valid'

        # 验证1：范围检查
        invalid_range = (data['pump_hydraulic_power'] < min_power) | \
                       (data['pump_hydraulic_power'] > max_power)
        data.loc[invalid_range, 'quality'] = 'out_of_range'

        # 验证2：负值检查
        invalid_negative = data['pump_hydraulic_power'] < 0
        data.loc[invalid_negative, 'quality'] = 'negative'

        # 验证3：NaN检查
        invalid_nan = data['pump_hydraulic_power'].isna()
        data.loc[invalid_nan, 'quality'] = 'nan'

        # 统计验证结果
        valid_count = (data['quality'] == 'valid').sum()
        invalid_count = len(data) - valid_count

        print(f"  - 验证结果:")
        print(f"    - 有效记录: {valid_count}")
        print(f"    - 无效记录: {invalid_count}")

        if invalid_count > 0:
            quality_counts = data['quality'].value_counts()
            for quality, count in quality_counts.items():
                if quality != 'valid':
                    print(f"      - {quality}: {count}")

        # 显示统计信息
        if valid_count > 0:
            valid_data = data[data['quality'] == 'valid']['pump_hydraulic_power']
            print(f"  - 有效数据统计:")
            print(f"    - 最小值: {valid_data.min():.2f} kW")
            print(f"    - 最大值: {valid_data.max():.2f} kW")
            print(f"    - 平均值: {valid_data.mean():.2f} kW")
            print(f"    - 标准差: {valid_data.std():.2f} kW")

        return data

