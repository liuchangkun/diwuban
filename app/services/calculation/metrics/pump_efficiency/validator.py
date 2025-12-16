"""
pump_efficiency 结果验证模块
"""

import pandas as pd
import numpy as np
import logging
from typing import Tuple


class Validator:
    """结果验证器"""

    def __init__(self, shared_services):
        self.logger = logging.getLogger(__name__)
        self.shared_services = shared_services

    def validate(
        self,
        results: pd.DataFrame,
        device_id: int
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        验证计算结果

        Args:
            results: 计算结果（包含 pump_efficiency 列）
            device_id: 设备ID

        Returns:
            Tuple[pd.DataFrame, pd.Series]: (有效结果, 有效性标记)
        """
        if results.empty or 'pump_efficiency' not in results.columns:
            self.logger.warning("[结果验证] 结果为空或缺少 pump_efficiency 列")
            return results, pd.Series(dtype=bool)

        self.logger.info(
            "[结果验证] 开始验证",
            extra={'extra_data': {
                '设备ID': device_id,
                '结果数量': len(results)
            }}
        )

        # 加载验证参数
        params = self.shared_services.parameter_manager.get_parameters(
            metric_key='pump_efficiency',
            method_id='EFF_SIMPLE_V1',
            device_id=device_id
        )

        eta_min = params.get('eta_min')
        eta_max = params.get('eta_max')

        # 验证必需参数
        missing_params = []
        if eta_min is None:
            missing_params.append('eta_min')
        if eta_max is None:
            missing_params.append('eta_max')

        if missing_params:
            self.logger.error(
                f"[验证器] pump_efficiency validator缺少必需参数",
                extra={'extra_data': {
                    '设备ID': device_id,
                    '缺失参数': missing_params,
                    '当前参数': params,
                    '错误': '必须在calculation_parameters表中配置这些参数'
                }}
            )
            raise ValueError(
                f"pump_efficiency validator缺少必需参数: {', '.join(missing_params)}. "
                f"必须在calculation_parameters表中配置: metric_key='pump_efficiency'"
            )

        # 初始化有效性标记
        is_valid = pd.Series([True] * len(results), index=results.index)

        # 1. NaN/Inf 验证
        nan_inf_invalid = results['pump_efficiency'].isna() | results['pump_efficiency'].isin([np.inf, -np.inf])
        is_valid &= ~nan_inf_invalid

        # 2. 范围验证
        range_invalid = (results['pump_efficiency'] < eta_min) | (results['pump_efficiency'] > eta_max)
        is_valid &= ~range_invalid

        # 3. 非负验证
        negative_invalid = (results['pump_efficiency'] < 0)
        is_valid &= ~negative_invalid

        # 记录无效值
        invalid_count = (~is_valid).sum()
        if invalid_count > 0:
            self.logger.warning(
                "[结果验证] 发现无效值",
                extra={'extra_data': {
                    '设备ID': device_id,
                    '无效数量': invalid_count,
                    '无效比例': f"{invalid_count / len(results) * 100:.2f}%"
                }}
            )

            # 打印前10个无效值的详细信息
            invalid_indices = results[~is_valid].index[:10]
            for idx in invalid_indices:
                self.logger.debug(
                    "[结果验证] 无效值详情",
                    extra={'extra_data': {
                        '索引': int(idx),
                        '时间戳': results.loc[idx, 'ts_bucket'].isoformat() if 'ts_bucket' in results.columns else 'N/A',
                        '泵效率': float(results.loc[idx, 'pump_efficiency']),
                        '泵流量': float(results.loc[idx, 'pump_flow_rate']) if 'pump_flow_rate' in results.columns else None,
                        '泵扬程': float(results.loc[idx, 'pump_head']) if 'pump_head' in results.columns else None,
                        '泵有功功率': float(results.loc[idx, 'pump_active_power']) if 'pump_active_power' in results.columns else None
                    }}
                )

        # 创建有效结果（无效值设为NaN）
        valid_results = results.copy()
        valid_results.loc[~is_valid, 'pump_efficiency'] = np.nan

        self.logger.info(
            "[结果验证] 验证完成",
            extra={'extra_data': {
                '设备ID': device_id,
                '总数量': len(results),
                '有效数量': is_valid.sum(),
                '无效数量': invalid_count,
                '有效比例': f"{is_valid.sum() / len(results) * 100:.2f}%"
            }}
        )

        return valid_results, is_valid

