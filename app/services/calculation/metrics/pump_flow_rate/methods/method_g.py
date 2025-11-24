"""
方法G: 待机状态检测

适用场景: running=1 但 pump_active_power ≈ 0 且 pump_frequency ≈ 0
判定: 设备处于待机状态，流量 = 0

依赖: pump_active_power, pump_frequency
"""

from __future__ import annotations

from typing import Dict, Any
import pandas as pd
import logging


def calculate_method_g(data: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    """
    方法G: 待机状态检测
    
    适用场景:
    - running=1（设备标记为运行中）
    - pump_active_power < standby_power_threshold（功率接近0）
    - pump_frequency < standby_freq_threshold（频率接近0）
    
    判定: 设备处于待机状态，流量 = 0.0
    
    Args:
        data: 输入数据（已过滤 running=1）
        params: 参数配置，必须包含:
            - standby_power_threshold: 待机功率阈值（kW）
            - standby_freq_threshold: 待机频率阈值（Hz）
    
    Returns:
        计算结果（包含 pump_flow_rate 列）
        
    Raises:
        ValueError: 如果缺少必需参数
    """
    logger = logging.getLogger(__name__)
    
    # 验证必需参数（禁止使用默认值）
    standby_power_threshold = params.get('standby_power_threshold')
    standby_freq_threshold = params.get('standby_freq_threshold')
    
    missing_params = []
    if standby_power_threshold is None:
        missing_params.append('standby_power_threshold')
    if standby_freq_threshold is None:
        missing_params.append('standby_freq_threshold')
    
    if missing_params:
        logger.error(
            f"[方法G] 缺少必需参数",
            extra={'extra_data': {
                '缺失参数': missing_params,
                '当前参数': params,
                '错误': '必须在calculation_parameters表中配置这些参数'
            }}
        )
        raise ValueError(
            f"方法G缺少必需参数: {', '.join(missing_params)}. "
            f"必须在calculation_parameters表中配置: metric_key='pump_flow_rate', method_id='data_filter'"
        )
    
    # 验证必需列
    required_columns = ['pump_active_power', 'pump_frequency', 'ts_bucket', 'device_id']
    missing_columns = [col for col in required_columns if col not in data.columns]
    
    if missing_columns:
        logger.error(
            f"[方法G] 缺少必需列",
            extra={'extra_data': {
                '缺失列': missing_columns,
                '可用列': list(data.columns)
            }}
        )
        raise ValueError(f"方法G缺少必需列: {', '.join(missing_columns)}")
    
    # 复制数据
    df_result = data.copy()
    
    # 检测待机状态并设置流量为0
    standby_mask = (
        (df_result['pump_active_power'] < standby_power_threshold) & 
        (df_result['pump_frequency'] < standby_freq_threshold)
    )
    
    # 设置流量为0
    df_result['pump_flow_rate'] = 0.0
    
    # 添加备注信息
    df_result['note'] = df_result.apply(
        lambda row: (
            f"待机状态(P={row['pump_active_power']:.2f}kW, f={row['pump_frequency']:.2f}Hz)"
            if (row['pump_active_power'] < standby_power_threshold and 
                row['pump_frequency'] < standby_freq_threshold)
            else ""
        ),
        axis=1
    )
    
    # 统计待机状态数据点
    standby_count = standby_mask.sum()
    total_count = len(df_result)
    standby_ratio = standby_count / total_count if total_count > 0 else 0
    
    logger.info(
        f"[方法G] 待机状态检测完成",
        extra={'extra_data': {
            '总数据点': total_count,
            '待机数据点': standby_count,
            '待机比例': f"{standby_ratio:.2%}",
            '平均功率': f"{df_result['pump_active_power'].mean():.2f} kW",
            '平均频率': f"{df_result['pump_frequency'].mean():.2f} Hz",
            'standby_power_threshold': standby_power_threshold,
            'standby_freq_threshold': standby_freq_threshold
        }}
    )
    
    return df_result

